from __future__ import annotations

from datetime import datetime, timedelta

from forge.prompt_optimization.models import PromptCategory
from forge.prompt_optimization.tracker import PerformanceTracker


def test_record_execution_updates_metrics() -> None:
    tracker = PerformanceTracker()
    tracker.record_execution(
        variant_id="v1",
        prompt_id="p1",
        category=PromptCategory.CUSTOM,
        success=True,
        execution_time=2.0,
        token_cost=0.5,
    )

    metrics = tracker.get_variant_metrics("v1")
    assert metrics is not None
    assert metrics.success_rate == 1.0
    assert metrics.sample_count == 1
    assert metrics.composite_score > 0


def test_performance_trend_orders_days() -> None:
    tracker = PerformanceTracker()
    base_time = datetime.now() - timedelta(days=3)
    for offset in range(3):
        tracker.record_execution(
            variant_id="v-trend",
            prompt_id="p1",
            category=PromptCategory.CUSTOM,
            success=bool(offset % 2),
            execution_time=1.0 + offset,
        )
        tracker.performance_records[-1].timestamp = base_time + timedelta(days=offset)

    trend = tracker.get_performance_trend("v-trend", days=5)
    assert len(trend) == 3
    dates = [entry["date"] for entry in trend]
    assert dates == sorted(dates)


def test_export_import_round_trip() -> None:
    tracker = PerformanceTracker()
    tracker.record_execution(
        variant_id="v-export",
        prompt_id="p-export",
        category=PromptCategory.CUSTOM,
        success=False,
        execution_time=3.0,
    )

    exported = tracker.export_data()
    clone = PerformanceTracker()
    clone.import_data(exported)

    metrics = clone.get_variant_metrics("v-export")
    assert metrics is not None
    assert metrics.sample_count == 1
    assert metrics.success_rate == 0.0


def test_category_statistics_summary() -> None:
    tracker = PerformanceTracker()
    tracker.record_execution(
        variant_id="variant-a",
        prompt_id="prompt-a",
        category=PromptCategory.CUSTOM,
        success=True,
        execution_time=1.0,
        token_cost=0.2,
    )
    tracker.record_execution(
        variant_id="variant-b",
        prompt_id="prompt-b",
        category=PromptCategory.ANALYSIS,
        success=False,
        execution_time=2.0,
        token_cost=0.4,
    )

    stats = tracker.get_category_statistics()
    assert "custom" in stats
    assert stats["custom"]["total_executions"] == 1
    assert stats["custom"]["success_rate"] == 1.0


def test_json_history_store_persistence(tmp_path) -> None:
    store_path = tmp_path / "history.json"
    tracker = PerformanceTracker(
        history_path=store_path,
        history_auto_flush=True,
    )
    tracker.record_execution(
        variant_id="persisted",
        prompt_id="p-store",
        category=PromptCategory.CUSTOM,
        success=True,
        execution_time=1.23,
    )

    assert store_path.exists()

    # Reload from disk-backed store
    tracker_clone = PerformanceTracker(history_path=store_path)
    metrics = tracker_clone.get_variant_metrics("persisted")
    assert metrics is not None
    assert metrics.sample_count == 1

