from forge.events.utils import get_pairs_from_events
from forge.events.serialization import event_from_dict
import argparse
import glob
import json
import logging
import os
import random
from collections import Counter
import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)
ERROR_KEYWORDS = [
    "Agent encountered an error while processing the last action",
    "APIError",
    "Action execution failed",
    "litellm.Timeout: APITimeoutError",
]


def get_bootstrap_accuracy_error_bars(
    values: float | int | bool, num_samples: int = 1000, p_value=0.05
) -> tuple[float, float]:
    sorted_vals = np.sort([np.mean(random.sample(values, len(values) // 2)) for _ in range(num_samples)])
    bottom_idx = int(num_samples * p_value / 2)
    top_idx = int(num_samples * (1.0 - p_value / 2))
    return (sorted_vals[bottom_idx], sorted_vals[top_idx])


def _calculate_costs_from_metrics(metrics: dict) -> tuple[float, float]:
    """Calculate main agent and editor costs from metrics."""
    costs = metrics.get("costs", [])
    main_agent_cost = 0
    editor_cost = 0

    for cost in costs:
        if isinstance(cost, float):
            main_agent_cost += cost
        elif "draft_editor" in cost["model"]:
            editor_cost += cost["cost"]
        else:
            main_agent_cost += cost["cost"]

    return main_agent_cost, editor_cost


def _process_error_handling(error: str | None, error_counter: Counter, line: str) -> tuple[int, int]:
    """Process error handling and return error counts."""
    num_error_lines = 0
    num_agent_stuck_in_loop = 0

    if error is not None and isinstance(error, str):
        agent_stuck_in_loop = "Agent got stuck in a loop" in error
        contains_error = bool(error) and (not agent_stuck_in_loop)

        if agent_stuck_in_loop:
            error_counter["Agent got stuck in a loop"] += 1
            num_agent_stuck_in_loop += 1
        elif contains_error:
            error_counter[error] += 1
    else:
        # Check for error keywords in line
        for keyword in ERROR_KEYWORDS:
            if keyword in line:
                error_counter[keyword] += 1
                num_error_lines += 1
                break

    return num_error_lines, num_agent_stuck_in_loop


def _process_instance_data(
    instance_data: dict, line: str, error_counter: Counter
) -> tuple[bool, int, int, int, int, float, float, int]:
    """Process a single instance and return relevant metrics."""
    # Check for unfinished runs
    if "metrics" not in instance_data or instance_data["metrics"] is None:
        return False, 0, 0, 0, 0, 0.0, 0.0, 0

    # Calculate costs
    main_agent_cost, editor_cost = _calculate_costs_from_metrics(instance_data["metrics"])

    # Calculate turns
    history = instance_data.get("history", [])
    events = [event_from_dict(event) for event in history]
    pairs = get_pairs_from_events(events)
    num_turns = len(pairs)

    # Check for empty patch
    patch = instance_data.get("test_result", {}).get("git_patch", "")
    if patch == "":
        return True, 0, 0, 0, 0, main_agent_cost, editor_cost, num_turns

    # Check resolution status
    report = instance_data.get("report", {}) or {}
    resolved = report.get("resolved", False)
    resolved_count = 1 if resolved else 0

    # Process errors
    error = instance_data.get("error")
    num_error_lines, num_agent_stuck_in_loop = _process_error_handling(error, error_counter, line)

    return True, resolved_count, 0, num_error_lines, num_agent_stuck_in_loop, main_agent_cost, editor_cost, num_turns


def _build_result_dict(
    file_path: str,
    num_lines: int,
    num_resolved: int,
    resolved_arr: list,
    num_empty_patch: int,
    num_unfinished_runs: int,
    num_error_lines: int,
    num_agent_stuck_in_loop: int,
    error_counter: Counter,
    main_agent_cost: list,
    editor_cost: list,
    num_turns: list,
) -> dict:
    """Build the final result dictionary."""
    return {
        "file_path": file_path,
        "total_instances": num_lines,
        "resolved": _build_resolved_section(num_resolved, num_lines, resolved_arr),
        "empty_patches": _build_percentage_section(num_empty_patch, num_lines),
        "unfinished_runs": _build_percentage_section(num_unfinished_runs, num_lines),
        "errors": _build_errors_section(num_error_lines, num_agent_stuck_in_loop, error_counter, num_lines),
        "costs": _build_costs_section(main_agent_cost, editor_cost),
        "statistics": _build_statistics_section(main_agent_cost, editor_cost, num_turns, num_lines),
    }


def _build_resolved_section(num_resolved: int, num_lines: int, resolved_arr: list) -> dict:
    """Build resolved section with confidence intervals."""
    return {
        "count": num_resolved,
        "percentage": num_resolved / num_lines * 100 if num_lines > 0 else 0,
        "ci": tuple((x * 100 for x in get_bootstrap_accuracy_error_bars(resolved_arr))),
    }


def _build_percentage_section(count: int, num_lines: int) -> dict:
    """Build a section with count and percentage."""
    return {"count": count, "percentage": count / num_lines * 100 if num_lines > 0 else 0}


def _build_errors_section(
    num_error_lines: int, num_agent_stuck_in_loop: int, error_counter: Counter, num_lines: int
) -> dict:
    """Build errors section with breakdown."""
    return {
        "total": num_error_lines,
        "percentage": num_error_lines / num_lines * 100 if num_lines > 0 else 0,
        "stuck_in_loop": _build_percentage_section(num_agent_stuck_in_loop, num_lines),
        "breakdown": {
            str(error): _build_percentage_section(count, num_lines) for error, count in error_counter.items()
        },
    }


def _build_costs_section(main_agent_cost: list, editor_cost: list) -> dict:
    """Build costs section."""
    total_main = sum(main_agent_cost)
    total_editor = sum(editor_cost)
    return {"main_agent": total_main, "editor": total_editor, "total": total_main + total_editor}


def _build_statistics_section(main_agent_cost: list, editor_cost: list, num_turns: list, num_lines: int) -> dict:
    """Build statistics section."""
    if num_lines == 0:
        return {"avg_turns": 0, "costs": {"main_agent": 0, "editor": 0, "total": 0}}

    total_main = sum(main_agent_cost)
    total_editor = sum(editor_cost)
    return {
        "avg_turns": sum(num_turns) / num_lines,
        "costs": {
            "main_agent": total_main / num_lines,
            "editor": total_editor / num_lines,
            "total": (total_main + total_editor) / num_lines,
        },
    }


def process_file(file_path):
    """Process a file and extract statistics."""
    with open(file_path, "r", encoding='utf-8') as file:
        lines = file.readlines()

    num_lines = len(lines)
    num_error_lines = 0
    num_agent_stuck_in_loop = 0
    num_resolved = 0
    resolved_arr = []
    num_empty_patch = 0
    num_unfinished_runs = 0
    error_counter = Counter()
    main_agent_cost = []
    editor_cost = []
    num_turns = []

    for line in lines:
        instance_data = json.loads(line)
        is_valid, resolved_count, empty_patch_count, error_count, stuck_count, main_cost, edit_cost, turns = (
            _process_instance_data(instance_data, line, error_counter)
        )

        if not is_valid:
            num_unfinished_runs += 1
            continue

        # Update counters
        num_resolved += resolved_count
        resolved_arr.append(resolved_count)
        num_empty_patch += empty_patch_count
        num_error_lines += error_count
        num_agent_stuck_in_loop += stuck_count

        # Store costs and turns
        main_agent_cost.append(main_cost)
        editor_cost.append(edit_cost)
        num_turns.append(turns)

    return _build_result_dict(
        file_path,
        num_lines,
        num_resolved,
        resolved_arr,
        num_empty_patch,
        num_unfinished_runs,
        num_error_lines,
        num_agent_stuck_in_loop,
        error_counter,
        main_agent_cost,
        editor_cost,
        num_turns,
    )


def aggregate_directory(input_path) -> pd.DataFrame:
    pattern = os.path.join(input_path, "**/output.jsonl")
    files = glob.glob(pattern, recursive=True)
    logger.info("Processing %s files from directory %s", len(files), input_path)
    results = []
    for file_path in files:
        try:
            result = process_file(file_path)
            results.append(result)
        except Exception as e:
            logger.exception("Error processing %s: %s", file_path, e)
            continue
    df = pd.DataFrame(results)
    df["directory"] = df["file_path"].apply(lambda x: os.path.basename(os.path.dirname(x)))
    df["resolve_rate"] = df["resolved"].apply(lambda x: x["percentage"])
    df["resolve_rate_ci"] = df["resolved"].apply(lambda x: x["ci"])
    df["empty_patch_rate"] = df["empty_patches"].apply(lambda x: x["percentage"])
    df["unfinished_rate"] = df["unfinished_runs"].apply(lambda x: x["percentage"])
    df["avg_turns"] = df["statistics"].apply(lambda x: x["avg_turns"])
    df["error_rate"] = df["errors"].apply(lambda x: x["percentage"])
    df["avg_cost"] = df["statistics"].apply(lambda x: x["costs"]["total"])
    df = df.sort_values("resolve_rate", ascending=False)
    return df


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("input_path", type=str, help="The file or directory to summarize")
    parser.add_argument("--output", type=str, help="Output JSONL file for results", default="summary_results.jsonl")
    args = parser.parse_args()
    if os.path.isdir(args.input_path):
        df = aggregate_directory(args.input_path)
        columns = [
            "directory",
            "resolve_rate",
            "empty_patch_rate",
            "unfinished_rate",
            "error_rate",
            "avg_turns",
            "avg_cost",
            "total_instances",
        ]
        summary_str = df[columns].to_string(
            float_format=lambda x: "{:.2f}".format(x), formatters={"directory": lambda x: x[:90]}, index=False
        )
        logger.info("\nResults summary (sorted by resolve rate):")
        logger.info("\n%s", summary_str)
        txt_output = args.output.rsplit(".", 1)[0] + ".txt"
        with open(txt_output, "w", encoding='utf-8') as f:
            f.write("Results summary (sorted by resolve rate):\n")
            f.write(summary_str)
        df.to_json(args.output, lines=True, orient="records")
        df[columns].to_csv(args.output.rsplit(".", 1)[0] + ".csv", index=False)
    else:
        results = []
        try:
            result = process_file(args.input_path)
            results.append(result)
            logger.info("\nResults for %s:", args.input_path)
            logger.info(
                "Number of resolved: %d / %d (%.2f%% [%.2f%%, %.2f%%])",
                result["resolved"]["count"],
                result["total_instances"],
                result["resolved"]["percentage"],
                result["resolved"]["ci"][0],
                result["resolved"]["ci"][1],
            )
            logger.info(
                "Number of empty patch: %d / %d (%.2f%%)",
                result["empty_patches"]["count"],
                result["total_instances"],
                result["empty_patches"]["percentage"],
            )
            logger.info(
                "Number of error lines: %d / %d (%.2f%%)",
                result["errors"]["total"],
                result["total_instances"],
                result["errors"]["percentage"],
            )
            logger.info(
                "Number of agent stuck in loop: %d / %d (%.2f%%)",
                result["errors"]["stuck_in_loop"]["count"],
                result["total_instances"],
                result["errors"]["stuck_in_loop"]["percentage"],
            )
            logger.info(
                "Number of unfinished runs: %d / %d (%.2f%%)",
                result["unfinished_runs"]["count"],
                result["total_instances"],
                result["unfinished_runs"]["percentage"],
            )
            logger.info("Total cost: %.2f USD", result["costs"]["total"])
            logger.info("## Statistics")
            logger.info("Avg. num of turns per instance: %.2f", result["statistics"]["avg_turns"])
            logger.info("Avg. agent cost per instance: %.2f USD", result["statistics"]["costs"]["main_agent"])
            logger.info("Avg. editor cost per instance: %.2f USD", result["statistics"]["costs"]["editor"])
            logger.info("Avg. total cost per instance: %.2f USD", result["statistics"]["costs"]["total"])
            logger.info("## Detailed error breakdown:")
            for error, data in result["errors"]["breakdown"].items():
                logger.info("%s: %d (%.2f%%)", error, data["count"], data["percentage"])
        except Exception as e:
            logger.exception("Error processing %s: %s", args.input_path, e)
