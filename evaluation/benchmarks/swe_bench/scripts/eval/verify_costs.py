import argparse
import pandas as pd
from forge.core.logger import forge_logger as logger


def _validate_metrics_data(row: pd.Series) -> tuple[dict, float, list] | tuple[None, None, None]:
    """Validate and extract metrics data from row."""
    metrics = row.get("metrics")
    if not metrics:
        logger.warning("Instance %s: No metrics found", row["instance_id"])
        return None, None, None

    accumulated = metrics.get("accumulated_cost")
    costs = metrics.get("costs", [])
    if accumulated is None:
        logger.warning("Instance %s: No accumulated_cost in metrics", row["instance_id"])
        return None, None, None

    return metrics, accumulated, costs


def _check_duplicate_costs(costs: list, instance_id: str) -> tuple[bool, bool]:
    """Check for duplicate consecutive costs and whether all pairs match."""
    has_duplicate = False
    all_pairs_match = True

    for i in range(0, len(costs) - 1, 2):
        if abs(costs[i]["cost"] - costs[i + 1]["cost"]) < 1e-06:
            has_duplicate = True
            logger.debug(
                "Instance %s: Possible buggy double-counting detected! Steps %s and %s have identical costs: %s",
                instance_id,
                i,
                i + 1,
                costs[i]["cost"],
            )
        else:
            all_pairs_match = False
            break

    return has_duplicate, all_pairs_match


def _calculate_corrected_cost(costs: list, has_duplicate: bool, all_pairs_match: bool) -> float:
    """Calculate total cost with potential correction for duplicate counting."""
    if len(costs) < 2 or not has_duplicate or not all_pairs_match:
        # Normal case - sum all costs
        return sum((cost_entry["cost"] for cost_entry in costs))
    # Handle buggy double-counting case
    paired_steps_cost = sum((cost_entry["cost"] for cost_entry in costs[: -1 if len(costs) % 2 else None]))
    real_paired_cost = paired_steps_cost / 2
    unpaired_cost = costs[-1]["cost"] if len(costs) % 2 else 0
    return real_paired_cost + unpaired_cost


def _validate_cost_consistency(total_cost: float, accumulated: float, instance_id: str) -> None:
    """Validate that calculated cost matches accumulated cost."""
    if abs(total_cost - accumulated) >= 1e-06:
        logger.warning(
            "Instance %s: Cost mismatch: accumulated: %s, sum of costs: %s, ", instance_id, accumulated, total_cost
        )


def verify_instance_costs(row: pd.Series) -> float:
    """Verifies that the accumulated_cost matches the sum of individual costs in metrics.

    Also checks for duplicate consecutive costs which might indicate buggy counting.
    If the consecutive costs are identical, the file is affected by this bug:
    https://github.com/All-Hands-AI/Forge/issues/5383.

    Args:
        row: DataFrame row containing instance data with metrics
    Returns:
        float: The verified total cost for this instance (corrected if needed)
    """
    try:
        # Validate and extract metrics data
        metrics_data = _validate_metrics_data(row)
        if metrics_data[0] is None:
            return 0.0

        metrics, accumulated, costs = metrics_data

        # Check for duplicate costs
        has_duplicate, all_pairs_match = _check_duplicate_costs(costs, row["instance_id"])

        # Calculate total cost with potential correction
        total_cost = _calculate_corrected_cost(costs, has_duplicate, all_pairs_match)

        # Validate cost consistency
        _validate_cost_consistency(total_cost, accumulated, row["instance_id"])

        return total_cost
    except Exception as e:
        logger.error("Error verifying costs for instance %s: %s", row.get("instance_id", "UNKNOWN"), e)
        return 0.0


def main():
    parser = argparse.ArgumentParser(description="Verify costs in SWE-bench output file")
    parser.add_argument("input_filepath", type=str, help="Path to the output.jsonl file")
    args = parser.parse_args()
    try:
        df = pd.read_json(args.input_filepath, lines=True)
        logger.info("Loaded %s instances from %s", len(df), args.input_filepath)
        total_cost = df.apply(verify_instance_costs, axis=1).sum()
        logger.info("Total verified cost across all instances: $%s", total_cost)
    except Exception as e:
        logger.error("Failed to process file: %s", e)
        raise


if __name__ == "__main__":
    main()
