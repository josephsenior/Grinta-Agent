import glob
import json
import logging
import os
import re
import sys
from typing import Callable

logger = logging.getLogger("forge.eval.the_agent_company.summarise_results")


def calculate_cost(model: str, prompt_tokens: int, completion_tokens: int) -> float:
    """Calculate the cost of the model call."""
    model_lower = model.lower()
    for signature, calculator in _MODEL_COST_CALCULATORS:
        if signature in model_lower:
            return calculator(prompt_tokens, completion_tokens)
    raise ValueError(f"Unknown model: {model}")


_MODEL_COST_CALCULATORS: tuple[tuple[str, Callable[[int, int], float]], ...] = (
    ("claude-3-5-sonnet", _calculate_claude_cost),
    ("gpt-4o", _calculate_gpt4o_cost),
    ("gemini-1.5-pro", _calculate_gemini_15_pro_cost),
    ("gemini-2.0-flash-exp", _calculate_gemini_20_flash_cost),
    ("qwen2-72b", _calculate_qwen2_72b_cost),
    ("qwen2p5-72b", _calculate_qwen2p5_72b_cost),
    ("llama-v3p1-405b-instruct", _calculate_llama_405b_cost),
    ("llama-v3p1-70b-instruct", _calculate_llama_70b_cost),
    ("llama-v3p3-70b-instruct", _calculate_llama_70b_cost),
    ("amazon.nova-pro-v1:0", _calculate_nova_pro_cost),
)


def _calculate_claude_cost(prompt_tokens: int, completion_tokens: int) -> float:
    """Calculate Claude 3.5 Sonnet cost."""
    return 3e-06 * prompt_tokens + 1.5e-05 * completion_tokens


def _calculate_gpt4o_cost(prompt_tokens: int, completion_tokens: int) -> float:
    """Calculate GPT-4o cost."""
    return 2.5e-06 * prompt_tokens + 1e-05 * completion_tokens


def _calculate_gemini_15_pro_cost(prompt_tokens: int, completion_tokens: int) -> float:
    """Calculate Gemini 1.5 Pro cost with high token multiplier."""
    cost = 1.25e-06 * prompt_tokens + 5e-06 * completion_tokens
    if prompt_tokens > 128000:
        cost *= 2
    return cost


def _calculate_gemini_20_flash_cost(
    prompt_tokens: int, completion_tokens: int
) -> float:
    """Calculate Gemini 2.0 Flash cost with high token multiplier."""
    cost = 7.5e-08 * prompt_tokens + 3e-07 * completion_tokens
    if prompt_tokens > 128000:
        cost *= 2
    return cost


def _calculate_qwen2_72b_cost(prompt_tokens: int, completion_tokens: int) -> float:
    """Calculate Qwen2 72B cost."""
    return 9e-07 * (prompt_tokens + completion_tokens)


def _calculate_qwen2p5_72b_cost(prompt_tokens: int, completion_tokens: int) -> float:
    """Calculate Qwen2.5 72B cost."""
    return 1.2e-06 * (prompt_tokens + completion_tokens)


def _calculate_llama_405b_cost(prompt_tokens: int, completion_tokens: int) -> float:
    """Calculate Llama 405B cost."""
    return 3e-06 * (prompt_tokens + completion_tokens)


def _calculate_llama_70b_cost(prompt_tokens: int, completion_tokens: int) -> float:
    """Calculate Llama 70B cost."""
    return 9e-07 * (prompt_tokens + completion_tokens)


def _calculate_nova_pro_cost(prompt_tokens: int, completion_tokens: int) -> float:
    """Calculate Amazon Nova Pro cost."""
    return 8e-07 * prompt_tokens + 3.2e-06 * completion_tokens


def analyze_eval_json_file(filepath: str) -> tuple[int, int]:
    """Analyze a single eval JSON file and extract the total and result from final_score.

    Args:
        filepath: Path to the JSON file

    Returns:
        Tuple containing (total, result) from final_score
    """
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            data = json.load(f)
        final_score = data.get("final_score", {})
        return (final_score.get("total", 0), final_score.get("result", 0))
    except json.JSONDecodeError as e:
        logger.exception("Error decoding JSON in %s: %s", filepath, e)
        return (0, 0)
    except Exception as e:
        logger.exception("Error processing %s: %s", filepath, e)
        return (0, 0)


def analyze_traj_json_file(filepath: str) -> tuple[int, float]:
    """Analyze a single trajectory JSON file and extract the steps and tokens.

    for each step. Then estimate the cost based on the tokens and the model type.
    Note: this is assuming there's no prompt caching at all.
    """
    steps: int = 0
    cost: float = 0.0
    with open(filepath, "r", encoding="utf-8") as f:
        data = json.load(f)
        response_id = None
        for action in data:
            if "tool_call_metadata" in action:
                if action["tool_call_metadata"]["model_response"]["id"] != response_id:
                    response_id = action["tool_call_metadata"]["model_response"]["id"]
                else:
                    continue
                steps += 1
                usage = action["tool_call_metadata"]["model_response"]["usage"]
                model: str = action["tool_call_metadata"]["model_response"]["model"]
                prompt_tokens = usage["prompt_tokens"]
                completion_tokens = usage["completion_tokens"]
                cost += calculate_cost(model, prompt_tokens, completion_tokens)
    return (steps, cost)


def analyze_folder(
    folder_path: str,
) -> tuple[dict[str, tuple[int, int]], dict[str, tuple[int, float]]]:
    """Analyze all eval_*.json & traj_*.json files in the specified folder.

    Args:
        folder_path: Path to the folder containing JSON files

    Returns:
        dictionaries:
        - eval_results: Dictionary with filename as key and (total, result) tuple as value
        - traj_results: Dictionary with filename as key and (steps, cost) tuple as value
    """
    eval_results = {}
    traj_results = {}
    eval_pattern = os.path.join(folder_path, "eval_*.json")
    traj_pattern = os.path.join(folder_path, "traj_*.json")
    for filepath in glob.glob(eval_pattern):
        filename = os.path.basename(filepath)
        total, result = analyze_eval_json_file(filepath)
        key = re.search("eval_(.+)\\.json", filename)[1]
        eval_results[key] = (total, result)
    for filepath in glob.glob(traj_pattern):
        filename = os.path.basename(filepath)
        steps, cost = analyze_traj_json_file(filepath)
        key = re.search("traj_(.+)\\.json", filename)[1]
        traj_results[key] = (steps, cost)
    return (eval_results, traj_results)


def get_task_nature_category(task_name: str) -> str:
    """Get the nature category of the task."""
    task_nature = task_name.split("-")[0]
    if task_nature.lower() in ["sde", "pm", "ds", "admin", "hr", "finance"]:
        return task_nature
    else:
        return "other"


def calculate_score(total: int, result: int) -> float:
    """Calculate the score as a number between 0 and 1.

    Formula: score = (result / total) * 0.5 + (result // total) * 0.5
    Explanation:
    - (result / total) * 0.5: This is the completion ratio, scaled down to a 0-0.5 range.
    - (result // total) * 0.5: This is a binary score indicating whether the task was completed or not.

    Args:
        total: Total possible points
        result: Actual points achieved

    Returns:
        Score as a number between 0 and 1
    """
    return result / total * 0.5 + result // total * 0.5


def is_perfect_completion(total: int, result: int) -> bool:
    """Check if the task achieved perfect completion.

    Args:
        total: Total possible points
        result: Actual points achieved

    Returns:
        True if result equals total, False otherwise
    """
    return total > 0 and total == result


def _validate_arguments() -> str:
    """Validate command line arguments and return folder path."""
    if len(sys.argv) != 2:
        logger.error("Usage: poetry run python summarise_results.py <folder_path>")
        sys.exit(1)

    folder_path = sys.argv[1]
    if not os.path.isdir(folder_path):
        logger.error("Error: '%s' is not a valid directory", folder_path)
        sys.exit(1)

    return folder_path


def _prepare_detailed_results(eval_results: dict) -> list:
    """Prepare detailed results with all calculated metrics."""
    detailed_results = [
        (
            task_name,
            total,
            result,
            calculate_score(total, result),
            is_perfect_completion(total, result),
            get_task_nature_category(task_name),
        )
        for task_name, (total, result) in eval_results.items()
    ]
    detailed_results.sort(key=lambda x: (-x[3], x[0]))
    return detailed_results


def _print_results_table(detailed_results: list, traj_results: dict) -> None:
    """Print the results table."""
    logger.info("\n# Evaluation Results Report")
    logger.info("\n## Results per File")
    logger.info("\n*Sorted by score (⭐ indicates perfect completion)*\n")
    logger.info(
        "| Filename | Total | Result | Score | Steps | Cost (assuming no prompt caching)|"
    )
    logger.info("|----------|--------|---------|-------|-------|------|")

    for task_name, total, result, score, is_perfect, task_nature in detailed_results:
        perfect_marker = " ⭐" if is_perfect else ""
        logger.info(
            "%s",
            f"| {task_name} | {total:,    } | {result:,        } | {score:.2f}{
                perfect_marker
            } | {traj_results[task_name][0]} | {traj_results[task_name][1]:.2f} |",
        )


def _print_summary(
    detailed_results: list, eval_results: dict, traj_results: dict
) -> None:
    """Print summary statistics."""
    perfect_completions = sum(
        (bool(is_perfect) for _, _, _, _, is_perfect, _ in detailed_results)
    )
    overall_score = (
        sum((score for _, _, _, score, _, _ in detailed_results))
        / len(detailed_results)
        * 100
    )
    avg_steps = sum((steps for steps, _ in traj_results.values())) / len(traj_results)
    avg_cost = sum((cost for _, cost in traj_results.values())) / len(traj_results)

    logger.info("\n## Summary\n")
    logger.info("**Tasks Evaluated:** %d\n", len(eval_results))
    logger.info(
        "**Perfect Completions:** %d/%d (%.2f%%)\n",
        perfect_completions,
        len(eval_results),
        perfect_completions / len(eval_results) * 100,
    )
    logger.info("**Overall Score:** %.2f%%\n", overall_score)
    logger.info("**Average Steps:** %.2f\n", avg_steps)
    logger.info("**Average Cost (USD):** %.2f\n", avg_cost)


def _print_statistics(detailed_results: list) -> None:
    """Print detailed statistics."""
    if not detailed_results:
        return

    highest_score = max((score for _, _, _, score, _, _ in detailed_results))
    lowest_score = min((score for _, _, _, score, _, _ in detailed_results))
    median_score = detailed_results[len(detailed_results) // 2][3]
    avg_score = sum((score for _, _, _, score, _, _ in detailed_results)) / len(
        detailed_results
    )

    logger.info("\n## Statistics\n")
    logger.info("| Metric | Value |")
    logger.info("|---------|--------|")
    logger.info("| Highest Task Score | %.2f%% |", highest_score * 100)
    logger.info("| Lowest Task Score | %.2f%% |", lowest_score * 100)
    logger.info("| Median Task Score | %.2f%% |", median_score * 100)
    logger.info("| Average Task Score | %.2f%% |", avg_score * 100)


def _print_nature_category_stats(detailed_results: list) -> None:
    """Print statistics per nature category."""
    logger.info("\n## Statistics per Nature Category\n")
    logger.info("| Metric | Value |")
    logger.info("|---------|--------|")

    for task_nature in ["sde", "pm", "ds", "admin", "hr", "finance", "other"]:
        num_of_tasks = sum(
            nature_category == task_nature
            for _, _, _, _, _, nature_category in detailed_results
        )
        if num_of_tasks == 0:
            continue

        task_nature_score = (
            sum(
                (
                    score
                    for _, _, _, score, _, nature_category in detailed_results
                    if nature_category == task_nature
                )
            )
            / num_of_tasks
        )
        perfect_completions = sum(
            (
                bool(nature_category == task_nature and is_perfect)
                for _, _, _, _, is_perfect, nature_category in detailed_results
            )
        )

        logger.info(
            "| Perfect Completions for %s | %d/%d (%.2f%%) |",
            task_nature,
            perfect_completions,
            num_of_tasks,
            perfect_completions / num_of_tasks * 100,
        )
        logger.info(
            "| Average Score for %s | %.2f%% |", task_nature, task_nature_score * 100
        )


def main():
    """Main function to analyze and report evaluation results."""
    folder_path = _validate_arguments()

    eval_results, traj_results = analyze_folder(folder_path)
    if not eval_results:
        logger.info("No eval_*.json files found in %s", folder_path)
        return

    detailed_results = _prepare_detailed_results(eval_results)

    _print_results_table(detailed_results, traj_results)
    _print_summary(detailed_results, eval_results, traj_results)
    _print_statistics(detailed_results)
    _print_nature_category_stats(detailed_results)


if __name__ == "__main__":
    main()
