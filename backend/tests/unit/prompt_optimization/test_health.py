from __future__ import annotations

from pathlib import Path

from forge.prompt_optimization.health import collect_health_snapshot
from forge.prompt_optimization.models import PromptVariant, PromptCategory
from forge.prompt_optimization.registry import PromptRegistry
from forge.prompt_optimization.tracker import PerformanceTracker


def test_collect_health_snapshot_memory_store() -> None:
    registry = PromptRegistry()
    tracker = PerformanceTracker()

    variant_id = registry.register_variant(
        PromptVariant(content="demo", prompt_id="prompt-1", category=PromptCategory.CUSTOM)
    )
    tracker.record_execution(
        variant_id=variant_id,
        prompt_id="prompt-1",
        category=PromptCategory.CUSTOM,
        success=True,
        execution_time=1.0,
    )

    snapshot = collect_health_snapshot(registry, tracker)
    assert snapshot["registry"]["total_variants"] == 1
    assert snapshot["tracker"]["total_performances"] == 1
    assert snapshot["tracker"]["store"]["backend"] == "memory"


def test_collect_health_snapshot_json_store(tmp_path) -> None:
    history_path = tmp_path / "history.json"
    tracker = PerformanceTracker(history_path=history_path.as_posix(), history_auto_flush=True)
    registry = PromptRegistry()

    variant_id = registry.register_variant(
        PromptVariant(content="json", prompt_id="prompt-json", category=PromptCategory.CUSTOM)
    )
    tracker.record_execution(
        variant_id=variant_id,
        prompt_id="prompt-json",
        category=PromptCategory.CUSTOM,
        success=False,
        execution_time=2.0,
    )

    snapshot = collect_health_snapshot(registry, tracker)
    assert snapshot["tracker"]["store"]["backend"] == "json"
    assert Path(snapshot["tracker"]["store"]["history_path"]) == history_path

