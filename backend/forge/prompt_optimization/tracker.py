"""Performance Tracker for Dynamic Prompt Optimization.

Collects and analyzes performance metrics for prompt variants,
calculates composite scores, and provides statistical analysis.
"""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any, Optional, Sequence

from .history_store import PromptHistoryStore, JsonPromptHistoryStore
from .models import PromptCategory, PromptMetrics, PromptPerformance
from .performance_analytics import (
    CategoryStats,
    DailyMetrics,
    OverallMetrics,
    VariantStats,
    calculate_category_statistics,
    calculate_daily_metrics,
    calculate_overall_metrics,
    calculate_variant_statistics,
    group_performances_by_day,
)


class PerformanceTracker:
    """Tracks and analyzes performance metrics for prompt variants."""

    def __init__(
        self,
        config: Optional[dict[str, float]] = None,
        store: PromptHistoryStore | None = None,
        history_path: str | None = None,
        history_auto_flush: bool = False,
    ):
        """Initialize the performance tracker.

        Args:
            config: Configuration for composite score weights
            store: Backing store for performance history (optional)

        """
        if store is not None:
            self.store = store
        elif history_path:
            self.store = JsonPromptHistoryStore(
                history_path, auto_flush=history_auto_flush
            )
        else:
            self.store = PromptHistoryStore()

        # Default weights for composite score
        self.weights = {
            "success": config.get("success_weight", 0.4) if config else 0.4,
            "time": config.get("time_weight", 0.2) if config else 0.2,
            "error": config.get("error_weight", 0.2) if config else 0.2,
            "cost": config.get("cost_weight", 0.2) if config else 0.2,
        }

        # Ensure weights sum to 1.0
        total_weight = sum(self.weights.values())
        if total_weight > 0:
            for key in self.weights:
                self.weights[key] /= total_weight

    def record_performance(self, performance: PromptPerformance):
        """Record a performance data point."""
        self.store.add_performance(performance)
        self._update_variant_metrics(performance)
        self.store.on_record()

    def record_execution(
        self,
        variant_id: str,
        prompt_id: str,
        category: PromptCategory,
        success: bool,
        execution_time: float,
        token_cost: float = 0.0,
        error_message: Optional[str] = None,
        metadata: Optional[dict[str, Any]] = None,
    ):
        """Record a single execution performance."""
        performance = PromptPerformance(
            variant_id=variant_id,
            prompt_id=prompt_id,
            category=category,
            success=success,
            execution_time=execution_time,
            token_cost=token_cost,
            error_message=error_message,
            metadata=metadata or {},
        )

        self.record_performance(performance)

    def _calculate_variant_statistics(
        self, variant_performances: Sequence[PromptPerformance]
    ) -> VariantStats:
        """Calculate statistics from variant performances.

        Args:
            variant_performances: List of performances

        Returns:
            Dictionary of calculated metrics

        """
        return calculate_variant_statistics(variant_performances)

    def _update_variant_metrics(self, performance: PromptPerformance):
        """Update metrics for a specific variant."""
        variant_id = performance.variant_id

        metrics = self.store.ensure_variant_metrics(variant_id, self.weights)
        variant_performances = self.store.get_variant_performances(variant_id)

        if not variant_performances:
            return

        # Calculate and update metrics
        stats = self._calculate_variant_statistics(variant_performances)

        metrics.success_rate = stats["success_rate"]
        metrics.avg_execution_time = stats["avg_execution_time"]
        metrics.error_rate = stats["error_rate"]
        metrics.avg_token_cost = stats["avg_token_cost"]
        metrics.sample_count = stats["sample_count"]
        metrics.composite_score = metrics._calculate_composite_score()

    def get_variant_metrics(self, variant_id: str) -> Optional[PromptMetrics]:
        """Get metrics for a specific variant."""
        return self.store.get_variant_metrics(variant_id)

    def get_prompt_metrics(self, prompt_id: str) -> list[tuple[str, PromptMetrics]]:
        """Get metrics for all variants of a prompt."""
        variant_ids = self.store.get_variant_ids_for_prompt(prompt_id)
        results: list[tuple[str, PromptMetrics]] = []
        for vid in variant_ids:
            metrics = self.store.get_variant_metrics(vid)
            if metrics:
                results.append((vid, metrics))
        return results

    def get_category_metrics(
        self, category: PromptCategory
    ) -> list[tuple[str, PromptMetrics]]:
        """Get metrics for all variants in a category."""
        variant_ids = self.store.get_variant_ids_for_category(category.value)
        results: list[tuple[str, PromptMetrics]] = []
        for vid in variant_ids:
            metrics = self.store.get_variant_metrics(vid)
            if metrics:
                results.append((vid, metrics))
        return results

    def get_best_variant(self, prompt_id: str) -> Optional[tuple[str, PromptMetrics]]:
        """Get the best performing variant for a prompt."""
        prompt_metrics = self.get_prompt_metrics(prompt_id)
        if not prompt_metrics:
            return None

        # Sort by composite score (highest first)
        prompt_metrics.sort(key=lambda x: x[1].composite_score, reverse=True)
        return prompt_metrics[0]

    def get_worst_variant(self, prompt_id: str) -> Optional[tuple[str, PromptMetrics]]:
        """Get the worst performing variant for a prompt."""
        prompt_metrics = self.get_prompt_metrics(prompt_id)
        if not prompt_metrics:
            return None

        # Sort by composite score (lowest first)
        prompt_metrics.sort(key=lambda x: x[1].composite_score)
        return prompt_metrics[0]

    def compare_variants(
        self, variant_id1: str, variant_id2: str
    ) -> Optional[dict[str, Any]]:
        """Compare two variants and return detailed comparison."""
        metrics1 = self.store.get_variant_metrics(variant_id1)
        metrics2 = self.store.get_variant_metrics(variant_id2)

        if not metrics1 or not metrics2:
            return None

        return {
            "variant1": {"id": variant_id1, "metrics": metrics1.to_dict()},
            "variant2": {"id": variant_id2, "metrics": metrics2.to_dict()},
            "comparison": {
                "success_rate_diff": metrics1.success_rate - metrics2.success_rate,
                "execution_time_diff": metrics1.avg_execution_time
                - metrics2.avg_execution_time,
                "error_rate_diff": metrics1.error_rate - metrics2.error_rate,
                "token_cost_diff": metrics1.avg_token_cost - metrics2.avg_token_cost,
                "composite_score_diff": metrics1.composite_score
                - metrics2.composite_score,
                "sample_count_diff": metrics1.sample_count - metrics2.sample_count,
            },
        }

    def is_significantly_better(
        self, variant_id1: str, variant_id2: str, confidence_level: float = 0.95
    ) -> Optional[bool]:
        """Check if variant1 is significantly better than variant2.

        Uses statistical significance testing based on sample sizes and variance.
        """
        metrics1 = self.store.get_variant_metrics(variant_id1)
        metrics2 = self.store.get_variant_metrics(variant_id2)

        if not metrics1 or not metrics2:
            return None

        # Need minimum samples for significance testing
        if metrics1.sample_count < 5 or metrics2.sample_count < 5:
            return None

        # Simple significance test based on composite score difference
        score_diff = metrics1.composite_score - metrics2.composite_score

        # Calculate confidence based on sample sizes
        # Larger sample sizes = higher confidence
        min_samples = min(metrics1.sample_count, metrics2.sample_count)
        confidence_factor = min(
            1.0, min_samples / 20.0
        )  # Full confidence at 20+ samples

        # Threshold for significance (adjust based on confidence level)
        significance_threshold = 0.1 * confidence_factor

        return score_diff > significance_threshold

    def get_performance_trend(
        self, variant_id: str, days: int = 7
    ) -> list[dict[str, Any]]:
        """Get performance trend for a variant over time."""
        cutoff_date = datetime.now() - timedelta(days=days)

        variant_performances = [
            p
            for p in self.store.get_variant_performances(variant_id)
            if p.timestamp >= cutoff_date
        ]

        if not variant_performances:
            return []

        daily_data = group_performances_by_day(variant_performances)

        # Calculate daily metrics
        trend_data: list[dict[str, Any]] = []
        for day, performances in sorted(daily_data.items()):
            metrics = calculate_daily_metrics(performances)
            trend_data.append({"date": day, **metrics})

        return trend_data

    def _calculate_overall_metrics(self) -> OverallMetrics:
        """Calculate overall performance metrics.

        Returns:
            Dictionary of overall metrics

        """
        return calculate_overall_metrics(self.store.get_all_performances())

    def get_overall_statistics(self) -> OverallMetrics:
        """Get overall performance statistics."""
        performances = self.store.get_all_performances()
        if not performances:
            return OverallMetrics(
                total_executions=0,
                overall_success_rate=0.0,
                overall_avg_execution_time=0.0,
                overall_avg_token_cost=0.0,
                total_variants=0,
                total_prompts=0,
            )

        return self._calculate_overall_metrics()

    def get_category_statistics(self) -> dict[str, CategoryStats]:
        """Get performance statistics by category."""
        return calculate_category_statistics(self.store.get_all_performances())

    def clear_data(self):
        """Clear all performance data."""
        self.store.clear()

    def export_data(self) -> dict[str, Any]:
        """Export all performance data for persistence."""
        payload = self.store.export_payload()
        payload["weights"] = self.weights
        return payload

    def import_data(self, data: dict[str, Any]):
        """Import performance data from persistence."""
        self.store.import_payload(data)
        if "weights" in data:
            self.weights.update(data["weights"])

    # ------------------------------------------------------------------ #
    # Advanced accessors for downstream tooling/tests
    # ------------------------------------------------------------------ #
    @property
    def performance_records(self) -> list[PromptPerformance]:
        """Expose raw performance records (primarily for debugging/tests)."""
        return self.store.get_all_performances()

    def get_all_performances(self) -> list[PromptPerformance]:
        """Return a shallow copy of all performances."""
        return list(self.store.get_all_performances())

    def get_performances_for_variant(
        self, variant_id: str, limit: int | None = None
    ) -> list[PromptPerformance]:
        """Return recorded performances for a variant."""
        return self.store.get_variant_performances(variant_id, limit=limit)

    def flush_store(self) -> None:
        """Force flushing the underlying history store if supported."""
        self.store.flush()

    def get_health_snapshot(self) -> dict[str, Any]:
        """Return tracker and store statistics for health reporting."""
        total_performances = len(self.performance_records)
        variant_metrics = len(list(self.store.iter_metrics()))
        store_stats = self.store.get_stats(total_performances)
        return {
            "total_performances": total_performances,
            "variants_tracked": variant_metrics,
            "store": store_stats,
        }
