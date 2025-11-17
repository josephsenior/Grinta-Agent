from __future__ import annotations

import json
import pytest

from forge.prompt_optimization.models import (
    OptimizationConfig,
    PromptCategory,
    PromptPerformance,
    PromptVariant,
)
from forge.prompt_optimization.optimizer import PromptOptimizer
from forge.prompt_optimization.registry import PromptRegistry
from forge.prompt_optimization.tracker import PerformanceTracker


def _make_variant(
    prompt_id: str = "prompt-test",
    *,
    content: str = "variant content",
    category: PromptCategory = PromptCategory.CUSTOM,
) -> PromptVariant:
    return PromptVariant(content=content, prompt_id=prompt_id, category=category)


def test_prompt_variant_metric_helpers_round_trip() -> None:
    variant = _make_variant()
    variant.update_metrics(success=True, execution_time=1.5, token_cost=10)
    variant.update_metrics(success=False, execution_time=2.5, token_cost=20)

    assert variant.total_executions == 2
    assert variant.success_rate == pytest.approx(0.5)
    assert variant.error_rate == pytest.approx(0.5)
    assert variant.avg_execution_time == pytest.approx((1.5 + 2.5) / 2)
    assert variant.avg_token_cost == pytest.approx((10 + 20) / 2)

    dumped = variant.to_dict()
    restored = PromptVariant.from_dict(dumped)
    assert restored.id == variant.id
    assert restored.metadata == variant.metadata
    assert restored.to_dict()["is_active"] is False


def test_registry_registers_testing_and_exports() -> None:
    registry = PromptRegistry()
    first = _make_variant()
    second = _make_variant(content="second", prompt_id=first.prompt_id)

    first_id = registry.register_variant(first)
    second_id = registry.register_variant(second)

    assert registry.get_active_variant(first.prompt_id).id == first_id
    assert registry.set_active_variant(first.prompt_id, second_id) is True
    assert registry.get_active_variant(first.prompt_id).id == second_id

    assert registry.add_testing_variant(first.prompt_id, first_id) is True
    testing = registry.get_testing_variants(first.prompt_id)
    assert [variant.id for variant in testing] == [first_id]

    registry.update_variant_metrics(
        first_id, success=True, execution_time=1.0, token_cost=3.5
    )
    updated_variant = registry.get_variant(first_id)
    assert updated_variant.successful_executions == 1

    stats = registry.get_statistics()
    assert stats["total_variants"] == 2
    assert stats["testing_variants"] == 1

    exported = registry.export_data()
    clone = PromptRegistry()
    clone.import_data(exported)
    assert clone.get_variant(first_id).content == first.content
    assert clone.get_active_variant(first.prompt_id).id == second_id

    assert registry.remove_testing_variant(first.prompt_id, first_id) is True
    assert registry.remove_testing_variant(first.prompt_id, first_id) is False
    registry.get_variant(first_id).composite_score = 0.3  # type: ignore[attr-defined]
    registry.get_variant(second_id).composite_score = 0.8  # type: ignore[attr-defined]
    assert registry.get_best_variant(first.prompt_id) is not None
    assert registry.get_variants_by_category(PromptCategory.CUSTOM)

    assert registry.remove_variant(first_id) is True
    assert registry.remove_variant("missing") is False
    registry.clear()
    assert registry.get_prompt_ids() == []


def _prime_tracker_with_variant(
    tracker: PerformanceTracker,
    variant_id: str,
    *,
    prompt_id: str,
    successes: int = 1,
    failures: int = 0,
    category: PromptCategory = PromptCategory.CUSTOM,
) -> None:
    for _ in range(successes):
        tracker.record_execution(
            variant_id=variant_id,
            prompt_id=prompt_id,
            category=category,
            success=True,
            execution_time=1.0,
            token_cost=2.0,
        )
    for _ in range(failures):
        tracker.record_execution(
            variant_id=variant_id,
            prompt_id=prompt_id,
            category=category,
            success=False,
            execution_time=3.0,
            token_cost=5.0,
        )


def test_tracker_best_variant_and_comparison() -> None:
    tracker = PerformanceTracker()
    prompt_id = "prompt-core"
    tracker.record_performance(
        PromptPerformance(
            variant_id="a",
            prompt_id=prompt_id,
            category=PromptCategory.CUSTOM,
            success=True,
            execution_time=2.0,
        )
    )
    tracker.record_performance(
        PromptPerformance(
            variant_id="b",
            prompt_id=prompt_id,
            category=PromptCategory.CUSTOM,
            success=False,
            execution_time=10.0,
            token_cost=4.0,
        )
    )

    best = tracker.get_best_variant(prompt_id)
    assert best is not None
    assert best[0] == "a"

    comparison = tracker.compare_variants("a", "b")
    assert comparison is not None
    assert comparison["comparison"]["success_rate_diff"] > 0

    assert tracker.is_significantly_better("a", "b") is None  # not enough samples yet


def test_optimizer_selection_switching_and_status(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    registry = PromptRegistry()
    tracker = PerformanceTracker()
    config = OptimizationConfig(
        ab_split_ratio=0.2, min_samples_for_switch=1, evolution_threshold=1.0
    )

    optimizer = PromptOptimizer(registry, tracker, config)
    prompt_id = "prompt-select"
    active_id = optimizer.add_variant(
        prompt_id, "Active variant", PromptCategory.CUSTOM
    )
    challenger_id = optimizer.add_variant(
        prompt_id, "Challenger", PromptCategory.CUSTOM
    )

    optimizer.start_testing_variant(prompt_id, challenger_id)
    registry.get_variant(active_id).composite_score = 0.5  # type: ignore[attr-defined]
    registry.get_variant(challenger_id).composite_score = 0.9  # type: ignore[attr-defined]

    monkeypatch.setattr(
        "forge.prompt_optimization.optimizer.random.random", lambda: 0.5
    )
    selected = optimizer.select_variant(prompt_id, PromptCategory.CUSTOM)
    assert selected is not None
    assert selected.id == challenger_id

    # Ensure both variants meet switch threshold
    registry.update_variant_metrics(active_id, success=True, execution_time=1.0)
    registry.update_variant_metrics(challenger_id, success=True, execution_time=0.5)
    _prime_tracker_with_variant(tracker, active_id, prompt_id=prompt_id, successes=1)
    _prime_tracker_with_variant(
        tracker, challenger_id, prompt_id=prompt_id, successes=5
    )

    monkeypatch.setattr(
        tracker,
        "is_significantly_better",
        lambda variant_id1, variant_id2, _: variant_id1 == challenger_id
        and variant_id2 == active_id,
    )

    optimizer.record_execution(
        variant_id=challenger_id,
        prompt_id=prompt_id,
        category=PromptCategory.CUSTOM,
        success=True,
        execution_time=0.4,
    )

    assert registry.get_active_variant(prompt_id).id == challenger_id
    status = optimizer.get_optimization_status(prompt_id)
    assert status["active_variant"] == challenger_id
    assert "active_metrics" in status

    summary = optimizer.get_performance_summary()
    assert summary["overall_performance"]["total_executions"] >= 1

    assert optimizer.should_evolve_prompt(prompt_id) is True
    assert optimizer.force_switch_variant(prompt_id, "missing") is False

    optimizer.reset_optimization(prompt_id)
    assert optimizer.get_optimization_status(prompt_id)["testing_variants"] == []


def test_tracker_statistics_and_persistence() -> None:
    tracker = PerformanceTracker()
    prompt_id = "prompt-stats"
    variant_a = "variant-a"
    variant_b = "variant-b"

    for _ in range(10):
        tracker.record_execution(
            variant_id=variant_a,
            prompt_id=prompt_id,
            category=PromptCategory.CUSTOM,
            success=True,
            execution_time=1.0,
            token_cost=1.0,
        )
    for idx in range(8):
        tracker.record_execution(
            variant_id=variant_b,
            prompt_id=prompt_id,
            category=PromptCategory.CUSTOM,
            success=idx % 2 == 0,
            execution_time=2.5,
            token_cost=2.0,
        )

    metrics_a = tracker.get_variant_metrics(variant_a)
    assert metrics_a is not None and metrics_a.sample_count == 10

    best_variant = tracker.get_best_variant(prompt_id)
    worst_variant = tracker.get_worst_variant(prompt_id)
    assert best_variant and best_variant[0] == variant_a
    assert worst_variant and worst_variant[0] == variant_b

    comparison = tracker.compare_variants(variant_a, variant_b)
    assert comparison is not None

    assert tracker.is_significantly_better(variant_a, variant_b) is True

    trend = tracker.get_performance_trend(variant_a)
    assert trend

    category_metrics = tracker.get_category_metrics(PromptCategory.CUSTOM)
    assert len(category_metrics) >= 2

    category_stats = tracker.get_category_statistics()
    assert "custom" in category_stats

    overall = tracker.get_overall_statistics()
    assert overall["total_executions"] == 18

    exported = tracker.export_data()
    clone = PerformanceTracker()
    clone.import_data(exported)
    assert clone.get_overall_statistics()["total_executions"] == 18

    clone.clear_data()
    assert clone.get_overall_statistics()["total_executions"] == 0


def test_optimizer_management_helpers(monkeypatch: pytest.MonkeyPatch) -> None:
    registry = PromptRegistry()
    tracker = PerformanceTracker()
    config = OptimizationConfig(max_variants_per_prompt=2, evolution_threshold=0.9)
    optimizer = PromptOptimizer(registry, tracker, config)
    prompt_id = "prompt-manage"

    variant_ids = [
        optimizer.add_variant(prompt_id, f"Variant {idx}", PromptCategory.CUSTOM)
        for idx in range(3)
    ]

    for index, variant_id in enumerate(variant_ids):
        registry.get_variant(variant_id).composite_score = 0.2 + index * 0.2  # type: ignore[attr-defined]
        optimizer.start_testing_variant(prompt_id, variant_id)
        optimizer.stop_testing_variant(prompt_id, variant_id)
        optimizer.start_testing_variant(prompt_id, variant_id)

        for _ in range(6):
            tracker.record_execution(
                variant_id=variant_id,
                prompt_id=prompt_id,
                category=PromptCategory.CUSTOM,
                success=index == 0,
                execution_time=2.0 + index,
                token_cost=1.5,
            )

    optimizer.stop_testing_variant(prompt_id, variant_ids[0])
    assert optimizer.force_switch_variant(prompt_id, variant_ids[1]) is True
    assert optimizer.get_all_optimization_status()[prompt_id]["prompt_id"] == prompt_id

    candidates = optimizer.get_candidates_for_evolution(prompt_id)
    assert candidates

    optimizer.cleanup_old_variants(prompt_id, keep_count=1)
    assert registry.get_variant_count(prompt_id) == 1

    optimizer.config.enable_evolution = False
    assert optimizer.should_evolve_prompt(prompt_id) is False


def test_optimizer_select_variant_without_variants() -> None:
    optimizer = PromptOptimizer(
        PromptRegistry(), PerformanceTracker(), OptimizationConfig()
    )
    assert optimizer.select_variant("missing", PromptCategory.CUSTOM) is None


def test_optimizer_start_testing_best_variant() -> None:
    registry = PromptRegistry()
    tracker = PerformanceTracker()
    optimizer = PromptOptimizer(registry, tracker, OptimizationConfig())
    prompt_id = "prompt-best"

    variant_active = optimizer.add_variant(prompt_id, "Active", PromptCategory.CUSTOM)
    variant_candidate = optimizer.add_variant(
        prompt_id, "Candidate", PromptCategory.CUSTOM
    )
    registry.get_variant(variant_active).composite_score = 0.1  # type: ignore[attr-defined]
    registry.get_variant(variant_candidate).composite_score = 0.9  # type: ignore[attr-defined]

    optimizer._start_testing_best_variant(prompt_id)
    testing_ids = [variant.id for variant in registry.get_testing_variants(prompt_id)]
    assert variant_candidate in testing_ids


def test_optimizer_select_testing_variant_zero_scores() -> None:
    registry = PromptRegistry()
    tracker = PerformanceTracker()
    optimizer = PromptOptimizer(
        registry, tracker, OptimizationConfig(ab_split_ratio=0.0)
    )
    prompt_id = "prompt-random"

    first = optimizer.add_variant(prompt_id, "First", PromptCategory.CUSTOM)
    second = optimizer.add_variant(prompt_id, "Second", PromptCategory.CUSTOM)
    for variant_id in (first, second):
        registry.get_variant(variant_id).composite_score = 0.0  # type: ignore[attr-defined]
        tracker.record_execution(
            variant_id=variant_id,
            prompt_id=prompt_id,
            category=PromptCategory.CUSTOM,
            success=True,
            execution_time=1.0,
        )
        registry.add_testing_variant(prompt_id, variant_id)

    selected = optimizer.select_variant(prompt_id, PromptCategory.CUSTOM)
    assert selected is not None
    assert selected.id in {first, second}


def test_optimizer_active_branch_selection(monkeypatch: pytest.MonkeyPatch) -> None:
    registry = PromptRegistry()
    tracker = PerformanceTracker()
    optimizer = PromptOptimizer(
        registry, tracker, OptimizationConfig(ab_split_ratio=1.0)
    )
    prompt_id = "prompt-active"
    active_id = optimizer.add_variant(prompt_id, "Only", PromptCategory.CUSTOM)

    monkeypatch.setattr(
        "forge.prompt_optimization.optimizer.random.random", lambda: 0.0
    )
    selected = optimizer.select_variant(prompt_id, PromptCategory.CUSTOM)
    assert selected is not None and selected.id == active_id


def test_optimizer_should_not_switch_without_samples() -> None:
    registry = PromptRegistry()
    tracker = PerformanceTracker()
    optimizer = PromptOptimizer(
        registry, tracker, OptimizationConfig(min_samples_for_switch=10)
    )
    prompt_id = "prompt-switch"
    active_id = optimizer.add_variant(prompt_id, "Active", PromptCategory.CUSTOM)
    challenger_id = optimizer.add_variant(
        prompt_id, "Challenger", PromptCategory.CUSTOM
    )

    registry.add_testing_variant(prompt_id, challenger_id)
    registry.get_variant(challenger_id).composite_score = 0.9  # type: ignore[attr-defined]
    optimizer.record_execution(
        variant_id=challenger_id,
        prompt_id=prompt_id,
        category=PromptCategory.CUSTOM,
        success=True,
        execution_time=0.2,
    )
    assert registry.get_active_variant(prompt_id).id == active_id


def test_optimizer_force_switch_variant_invalid() -> None:
    optimizer = PromptOptimizer(
        PromptRegistry(), PerformanceTracker(), OptimizationConfig()
    )
    assert optimizer.force_switch_variant("prompt", "missing") is False


def test_optimizer_performance_summary_tracks_updates() -> None:
    registry = PromptRegistry()
    tracker = PerformanceTracker()
    optimizer = PromptOptimizer(registry, tracker, OptimizationConfig())
    prompt_id = "prompt-summary"
    variant_id = optimizer.add_variant(prompt_id, "Variant", PromptCategory.CUSTOM)
    optimizer.record_execution(
        variant_id=variant_id,
        prompt_id=prompt_id,
        category=PromptCategory.CUSTOM,
        success=True,
        execution_time=1.0,
    )
    summary = optimizer.get_performance_summary()
    assert summary["update_count"] == 1
    assert "registry_stats" in summary


def test_optimizer_cleanup_old_variants_respects_keep_count() -> None:
    registry = PromptRegistry()
    tracker = PerformanceTracker()
    optimizer = PromptOptimizer(
        registry, tracker, OptimizationConfig(max_variants_per_prompt=1)
    )
    prompt_id = "prompt-cleanup"
    ids = [
        optimizer.add_variant(prompt_id, f"Variant {i}", PromptCategory.CUSTOM)
        for i in range(3)
    ]
    for idx, variant_id in enumerate(ids):
        registry.get_variant(variant_id).composite_score = idx  # type: ignore[attr-defined]

    optimizer.cleanup_old_variants(prompt_id, keep_count=2)
    assert registry.get_variant_count(prompt_id) == 2


def test_optimizer_auto_activates_best_variant_when_missing_active(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    registry = PromptRegistry()
    tracker = PerformanceTracker()
    optimizer = PromptOptimizer(registry, tracker, OptimizationConfig())
    prompt_id = "prompt-auto"
    variant_id = optimizer.add_variant(prompt_id, "Variant", PromptCategory.CUSTOM)
    registry._active_variants.pop(prompt_id, None)
    tracker.record_execution(
        variant_id=variant_id,
        prompt_id=prompt_id,
        category=PromptCategory.CUSTOM,
        success=True,
        execution_time=1.0,
    )
    selected = optimizer.select_variant(prompt_id, PromptCategory.CUSTOM)
    assert (
        selected is not None and registry.get_active_variant(prompt_id).id == variant_id
    )


def test_optimizer_get_best_variant_none() -> None:
    optimizer = PromptOptimizer(
        PromptRegistry(), PerformanceTracker(), OptimizationConfig()
    )
    assert optimizer._get_best_variant("unknown") is None


def test_optimizer_select_testing_variant_empty_list() -> None:
    optimizer = PromptOptimizer(
        PromptRegistry(), PerformanceTracker(), OptimizationConfig()
    )
    assert optimizer._select_testing_variant([]) is None


def test_optimizer_should_evolve_prompt_requires_active_variant() -> None:
    optimizer = PromptOptimizer(
        PromptRegistry(), PerformanceTracker(), OptimizationConfig()
    )
    assert optimizer.should_evolve_prompt("missing") is False


def test_optimizer_should_evolve_prompt_requires_metrics() -> None:
    registry = PromptRegistry()
    tracker = PerformanceTracker()
    optimizer = PromptOptimizer(registry, tracker, OptimizationConfig())
    prompt_id = "prompt-evolve"
    optimizer.add_variant(prompt_id, "Variant", PromptCategory.CUSTOM)
    tracker.clear_data()
    assert optimizer.should_evolve_prompt(prompt_id) is False


def test_optimizer_cleanup_old_variants_no_action_when_below_keep() -> None:
    registry = PromptRegistry()
    tracker = PerformanceTracker()
    optimizer = PromptOptimizer(
        registry, tracker, OptimizationConfig(max_variants_per_prompt=5)
    )
    prompt_id = "prompt-min"
    optimizer.add_variant(prompt_id, "Variant", PromptCategory.CUSTOM)
    optimizer.cleanup_old_variants(prompt_id, keep_count=5)
    assert registry.get_variant_count(prompt_id) == 1
