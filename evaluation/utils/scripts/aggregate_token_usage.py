"""Script to aggregate token usage metrics from LLM completion files.

Usage:
    python aggregate_token_usage.py <directory_path> [--input-cost <cost>] [--output-cost <cost>] [--cached-cost <cost>]

Arguments:
    directory_path: Path to the directory containing completion files
    --input-cost: Cost per input token (default: 0.0)
    --output-cost: Cost per output token (default: 0.0)
    --cached-cost: Cost per cached token (default: 0.0)
"""

import argparse
import json
import logging
import os
from pathlib import Path

logger = logging.getLogger(__name__)


def _extract_usage_data(data: dict) -> dict | None:
    """Extract usage data from JSON data."""
    if "response" in data and isinstance(data["response"], dict) and "usage" in data["response"]:
        return data["response"]["usage"]
    elif "fncall_response" in data and isinstance(data["fncall_response"], dict) and "usage" in data["fncall_response"]:
        return data["fncall_response"]["usage"]
    return None


def _get_cached_tokens(usage_data: dict) -> int:
    """Get cached tokens from usage data, checking details if needed."""
    cached_tokens = usage_data.get("cached_tokens", 0)

    if cached_tokens == 0 and "prompt_tokens_details" in usage_data:
        details = usage_data["prompt_tokens_details"]
        if isinstance(details, dict) and "cached_tokens" in details:
            cached_tokens = details.get("cached_tokens", 0) or 0

    return cached_tokens


def _process_usage_data(usage_data: dict, totals: dict) -> None:
    """Process usage data and update totals."""
    completion_tokens = usage_data.get("completion_tokens", 0)
    prompt_tokens = usage_data.get("prompt_tokens", 0)
    cached_tokens = _get_cached_tokens(usage_data)

    non_cached_input = prompt_tokens - cached_tokens
    totals["input_tokens"] += non_cached_input
    totals["output_tokens"] += completion_tokens
    totals["cached_tokens"] += cached_tokens
    totals["total_tokens"] += prompt_tokens + completion_tokens


def _process_json_file(json_file: Path, totals: dict) -> None:
    """Process a single JSON file and update totals."""
    try:
        with open(json_file, "r", encoding="utf-8") as f:
            data = json.load(f)

        if usage_data := _extract_usage_data(data):
            _process_usage_data(usage_data, totals)

        if "cost" in data:
            totals["cost"] += data["cost"]

        totals["files_processed"] += 1
        if totals["files_processed"] % 1000 == 0:
            logger.info("Processed %d files...", totals["files_processed"])

    except Exception as e:
        totals["files_with_errors"] += 1
        if totals["files_with_errors"] <= 5:
            logger.exception("Error processing %s: %s", json_file, e)


def _print_header() -> None:
    """Print the results header."""
    logger.info("\n" + "=" * 60)
    logger.info("TOKEN USAGE AGGREGATION RESULTS")
    logger.info("=" * 60)


def _print_basic_stats(totals: dict) -> None:
    """Print basic statistics."""
    logger.info("Files processed: %s", f"{totals['files_processed']:,}")
    logger.info("Files with errors: %s", f"{totals['files_with_errors']:,}")
    logger.info("")


def _print_token_counts(totals: dict) -> None:
    """Print token count statistics."""
    logger.info("TOKEN COUNTS:")
    logger.info("  Input tokens (non-cached):             %s", f"{totals['input_tokens']:,}")
    logger.info("  Output tokens:                         %s", f"{totals['output_tokens']:,}")
    logger.info("  Cached tokens:                         %s", f"{totals['cached_tokens']:,}")
    logger.info("  Total tokens:                          %s", f"{totals['total_tokens']:,}")
    logger.info("  Total costs (based on returned value): $%.6f", totals["cost"])
    logger.info("")


def _print_cost_breakdown(totals: dict, input_cost: float, output_cost: float, cached_cost: float) -> None:
    """Print cost breakdown if costs are provided."""
    if input_cost <= 0 and output_cost <= 0 and cached_cost <= 0:
        return

    input_cost_total = totals["input_tokens"] * input_cost
    output_cost_total = totals["output_tokens"] * output_cost
    cached_cost_total = totals["cached_tokens"] * cached_cost
    total_cost = input_cost_total + output_cost_total + cached_cost_total

    logger.info("COST CALCULATED BASED ON PROVIDED RATE:")
    logger.info("  Input cost:   $%.6f (%s × $%.6f)", input_cost_total, f"{totals['input_tokens']:,}", input_cost)
    logger.info("  Output cost:  $%.6f (%s × $%.6f)", output_cost_total, f"{totals['output_tokens']:,}", output_cost)
    logger.info("  Cached cost:  $%.6f (%s × $%.6f)", cached_cost_total, f"{totals['cached_tokens']:,}", cached_cost)
    logger.info("  Total cost:   $%.6f", total_cost)
    logger.info("")


def _print_summary(totals: dict) -> None:
    """Print final summary."""
    logger.info("SUMMARY:")
    logger.info("  Total input tokens:  %s", f"{totals['input_tokens'] + totals['cached_tokens']:,}")
    logger.info("  Total output tokens: %s", f"{totals['output_tokens']:,}")
    logger.info("  Grand total tokens:  %s", f"{totals['total_tokens']:,}")


def aggregate_token_usage(directory_path, input_cost=0.0, output_cost=0.0, cached_cost=0.0):
    """Aggregate token usage metrics from all JSON completion files in the directory.

    Args:
        directory_path (str): Path to directory containing completion files
        input_cost (float): Cost per input token
        output_cost (float): Cost per output token
        cached_cost (float): Cost per cached token
    """
    totals = {
        "input_tokens": 0,
        "output_tokens": 0,
        "cached_tokens": 0,
        "total_tokens": 0,
        "files_processed": 0,
        "files_with_errors": 0,
        "cost": 0,
    }

    json_files = list(Path(directory_path).rglob("*.json"))
    logger.info("Found %d JSON files to process...", len(json_files))

    for json_file in json_files:
        _process_json_file(json_file, totals)

    _print_header()
    _print_basic_stats(totals)
    _print_token_counts(totals)
    _print_cost_breakdown(totals, input_cost, output_cost, cached_cost)
    _print_summary(totals)

    return totals


def main():
    parser = argparse.ArgumentParser(
        description="Aggregate token usage metrics from LLM completion files",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="\nExamples:\n  python aggregate_token_usage.py /path/to/completions\n  python aggregate_token_usage.py /path/to/completions --input-cost 0.000001 --output-cost 0.000002\n  python aggregate_token_usage.py /path/to/completions --input-cost 0.000001 --output-cost 0.000002 --cached-cost 0.0000005\n        ",
    )
    parser.add_argument("directory_path", help="Path to directory containing completion files")
    parser.add_argument("--input-cost", type=float, default=0.0, help="Cost per input token (default: 0.0)")
    parser.add_argument("--output-cost", type=float, default=0.0, help="Cost per output token (default: 0.0)")
    parser.add_argument("--cached-cost", type=float, default=0.0, help="Cost per cached token (default: 0.0)")
    args = parser.parse_args()
    if not os.path.exists(args.directory_path):
        logger.error("Error: Directory '%s' does not exist.", args.directory_path)
        return 1
    if not os.path.isdir(args.directory_path):
        logger.error("Error: '%s' is not a directory.", args.directory_path)
        return 1
    try:
        aggregate_token_usage(args.directory_path, args.input_cost, args.output_cost, args.cached_cost)
        return 0
    except Exception as e:
        logger.exception("Error during aggregation: %s", e)
        return 1


if __name__ == "__main__":
    exit(main())
