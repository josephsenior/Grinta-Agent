import argparse
import json
import logging
from collections import Counter
from openhands.events.serialization import event_from_dict
from openhands.events.utils import get_pairs_from_events

logger = logging.getLogger(__name__)
ERROR_KEYWORDS = ["Agent encountered an error while processing the last action", "APIError", "Action execution failed"]
if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("output_file", type=str, help="The file to summarize")
    args = parser.parse_args()
    with open(args.output_file, "r", encoding='utf-8') as file:
        lines = file.readlines()
    num_lines = len(lines)
    num_error_lines = 0
    num_agent_stuck_in_loop = 0
    coverage = 0
    mutation_score = 0
    num_empty_suite = 0
    error_counter = Counter()
    main_agent_cost = []
    editor_cost = []
    num_turns = []
    for line in lines:
        _d = json.loads(line)
        costs = _d["metrics"].get("costs", [])
        _cur_main_agent_cost = 0
        _cur_editor_cost = 0
        for cost in costs:
            if isinstance(cost, float):
                _cur_main_agent_cost += cost
            elif "draft_editor" in cost["model"]:
                _cur_editor_cost += cost["cost"]
            else:
                _cur_main_agent_cost += cost["cost"]
        main_agent_cost.append(_cur_main_agent_cost)
        editor_cost.append(_cur_editor_cost)
        history = _d.get("history", [])
        events = [event_from_dict(event) for event in history]
        pairs = get_pairs_from_events(events)
        num_turns.append(len(pairs))
        suite = _d.get("test_result", {}).get("test_suite", "")
        if suite == "":
            num_empty_suite += 1
            continue
        report = _d.get("report", {}) or {}
        coverage += report.get("coverage", 0)
        mutation_score += report.get("mutation_score", 0)
        error = _d.get("error", None)
        if error is not None and isinstance(error, str):
            agent_stuck_in_loop = "Agent got stuck in a loop" in error
            contains_error = bool(error) and (not agent_stuck_in_loop)
            if agent_stuck_in_loop:
                error_counter["Agent got stuck in a loop"] += 1
                num_agent_stuck_in_loop += 1
            elif contains_error:
                error_counter[error] += 1
            continue
        for keyword in ERROR_KEYWORDS:
            if keyword in line:
                error_counter[keyword] += 1
                num_error_lines += 1
                break
    logger.info("Average coverage for %d (%.2f%%)", num_lines, coverage / num_lines * 100)
    logger.info("Average mutation score for %d (%.2f%%)", num_lines, mutation_score / num_lines * 100)
    logger.info(
        "Number of empty suite: %d / %d (%.2f%%)", num_empty_suite, num_lines, num_empty_suite / num_lines * 100
    )
    logger.info(
        "Number of error lines: %d / %d (%.2f%%)", num_error_lines, num_lines, num_error_lines / num_lines * 100
    )
    logger.info(
        "Number of agent stuck in loop: %d / %d (%.2f%%)",
        num_agent_stuck_in_loop,
        num_lines,
        num_agent_stuck_in_loop / num_lines * 100,
    )
    assert len(num_turns) == num_lines
    assert len(main_agent_cost) == num_lines
    assert len(editor_cost) == num_lines
    logger.info("## Statistics")
    logger.info("Avg. num of turns per instance: %.2f", sum(num_turns) / num_lines)
    logger.info("Avg. agent cost per instance: %.2f USD", sum(main_agent_cost) / num_lines)
    logger.info("Avg. editor cost per instance: %.2f USD", sum(editor_cost) / num_lines)
    logger.info("Avg. total cost per instance: %.2f USD", (sum(main_agent_cost) + sum(editor_cost)) / num_lines)
    logger.info("## Detailed error breakdown:")
    for error, count in error_counter.items():
        logger.info("%s: %d (%.2f%%)", error, count, count / num_lines * 100)
