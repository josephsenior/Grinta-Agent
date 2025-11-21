from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional

import pytest

from forge.prompt_optimization.advanced.strategy_manager import (
    AdvancedStrategyManager,
    EnsembleStrategy,
    StrategyPerformance,
    StrategySelection,
    StrategyType,
)
from forge.prompt_optimization.evolver import PromptEvolver
from forge.prompt_optimization.models import (
    OptimizationConfig,
    PromptCategory,
    PromptMetrics,
    PromptPerformance,
    PromptVariant,
)
from forge.prompt_optimization.optimizer import PromptOptimizer
from forge.prompt_optimization.registry import PromptRegistry
from forge.prompt_optimization.tracker import PerformanceTracker


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


class _StubLLM:
    def __init__(self, responses: Optional[List[str]] = None) -> None:
        self.responses = responses or ['["variant one", "variant two"]']
        self.calls = 0

    def generate(self, prompt: str, max_tokens: int, temperature: float) -> str:
        response = self.responses[min(self.calls, len(self.responses) - 1)]
        self.calls += 1
        return response


class _StubOptimizer:
    def __init__(self, variants: List[PromptVariant]) -> None:
        self._variants = variants
        self.added: List[str] = []

    def get_candidates_for_evolution(self, prompt_id: str) -> List[PromptVariant]:
        return self._variants

    def add_variant(
        self,
        prompt_id: str,
        content: str,
        category: PromptCategory,
        parent_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> str:
        variant_id = f"{prompt_id}_{len(self.added)}"
        self.added.append(content)
        return variant_id


class _StubStrategy:
    def __init__(self, name: str, result_score: float) -> None:
        self.name = name
        self.result_score = result_score

    def optimize(self, context: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "score": self.result_score,
            "confidence": context.get("confidence", 0.5),
            "recommendations": [f"recommendation from {self.name}"],
            "metadata": {"context": context},
        }


# ---------------------------------------------------------------------------
# PromptEvolver
# ---------------------------------------------------------------------------


def _setup_registry_tracker_optimizer() -> tuple[
    PromptRegistry, PerformanceTracker, PromptOptimizer
]:
    registry = PromptRegistry()
    tracker = PerformanceTracker()
    config = OptimizationConfig(
        enable_evolution=True, evolution_threshold=0.0, min_samples_for_switch=1
    )
    optimizer = PromptOptimizer(registry, tracker, config)
    return registry, tracker, optimizer


def test_prompt_evolver_generates_variants(monkeypatch: pytest.MonkeyPatch) -> None:
    registry, tracker, optimizer = _setup_registry_tracker_optimizer()

    base_variant = PromptVariant(
        content="Initial prompt content",
        category=PromptCategory.CUSTOM,
        prompt_id="prompt-test",
        metadata={},
    )
    registry.register_variant(base_variant)

    # Prime tracker with metrics and errors
    for idx in range(5):
        tracker.record_execution(
            variant_id=base_variant.id,
            prompt_id=base_variant.prompt_id,
            category=base_variant.category,
            success=idx % 2 == 0,
            execution_time=2.0 + idx,
            token_cost=5.0,
            error_message="JSON parse failure" if idx % 2 else None,
        )

    # Provide metrics for variant
    tracker.record_performance(
        PromptPerformance(
            variant_id=base_variant.id,
            prompt_id=base_variant.prompt_id,
            category=base_variant.category,
            success=False,
            execution_time=3.0,
            error_message="Validation error: missing field",
        )
    )

    stub_optimizer = _StubOptimizer([base_variant])
    evolver = PromptEvolver(_StubLLM(), registry, tracker, optimizer=stub_optimizer)

    monkeypatch.setattr(
        optimizer,
        "get_candidates_for_evolution",
        lambda prompt_id: [base_variant],
    )

    variant_ids = evolver.evolve_prompt(base_variant.prompt_id, max_variants=2)
    assert len(variant_ids) == 2
    assert stub_optimizer.added


def test_prompt_evolver_helper_methods() -> None:
    registry, tracker, optimizer = _setup_registry_tracker_optimizer()
    variant = PromptVariant(
        content="Prompt", category=PromptCategory.CUSTOM, prompt_id="prompt"
    )
    registry.register_variant(variant)

    tracker.record_performance(
        PromptPerformance(
            variant_id=variant.id,
            prompt_id=variant.prompt_id,
            category=variant.category,
            success=False,
            execution_time=5.0,
            error_message="Timeout occurred",
        )
    )

    evolver = PromptEvolver(_StubLLM(), registry, tracker, optimizer=optimizer)
    analysis = evolver._analyze_prompt_performance(variant)
    assert analysis["recommended_strategy"] in {
        "refinement",
        "simplification",
        "specialization",
        "expansion",
    }

    errors, issues = evolver._categorize_errors(
        [
            PromptPerformance(
                variant_id=variant.id,
                prompt_id=variant.prompt_id,
                category=variant.category,
                success=False,
                execution_time=1.0,
                error_message="JSON parse error",
            ),
            PromptPerformance(
                variant_id=variant.id,
                prompt_id=variant.prompt_id,
                category=variant.category,
                success=False,
                execution_time=1.0,
                error_message="Validation failure",
            ),
        ]
    )
    assert errors["parsing_error"] >= 1
    assert "JSON parse error"[:100] in issues

    json_variants = evolver._try_parse_json_array(
        'Here is output: ["one", "two"] and more'
    )
    assert json_variants == ["one", "two"]

    text_variants = evolver._parse_text_variants(
        "- Variant 1 with extended description text\n- Variant 2 with more details\n"
    )
    assert any("Variant 1" in variant for variant in text_variants)


def test_prompt_evolver_prompt_generation_and_fallback() -> None:
    registry, tracker, optimizer = _setup_registry_tracker_optimizer()
    variant = PromptVariant(
        content="Original prompt content with detailed instructions.",
        category=PromptCategory.CUSTOM,
        prompt_id="prompt-generated",
    )
    registry.register_variant(variant)

    evolver = PromptEvolver(_StubLLM(), registry, tracker, optimizer=optimizer)

    prompt = evolver._create_evolution_prompt(
        original_prompt=variant.content,
        strategy="expansion",
        error_patterns={"error_type": "none", "common_issues": [], "failure_rate": 0.0},
        metrics={
            "success_rate": 0.6,
            "avg_execution_time": 2.0,
            "error_rate": 0.3,
            "composite_score": 0.5,
        },
        category=variant.category,
    )
    assert "You are an expert prompt engineer" in prompt

    fallback_simplified = evolver._fallback_evolution(variant, "simplification")
    fallback_expanded = evolver._fallback_evolution(variant, "expansion")
    fallback_refined = evolver._fallback_evolution(variant, "refinement")
    fallback_default = evolver._fallback_evolution(variant, "other")
    assert all(fallback_simplified)
    assert all(fallback_expanded)
    assert all(fallback_refined)
    assert all(fallback_default)

    parsed_json = evolver._parse_evolution_response(
        '{"variants": ["keep"]}', "refinement"
    )
    assert isinstance(parsed_json, list)


def test_strategy_manager_historical_analysis() -> None:
    manager = AdvancedStrategyManager()
    context = {
        "complexity": "high",
        "domain": "software",
        "task_type": "generation",
        "urgency": "medium",
    }

    manager.strategy_performance["balanced_multi"] = StrategyPerformance(
        strategy_name="balanced_multi",
        success_rate=0.8,
        avg_score=0.8,
        efficiency=0.7,
        reliability=0.75,
        cost_effectiveness=0.6,
        sample_count=10,
        last_updated=datetime.now(),
    )

    manager.selection_history.extend(
        [
            StrategySelection(
                selected_strategy="balanced_multi",
                strategy_type=StrategyType.MULTI_OBJECTIVE,
                confidence=0.9,
                reasoning="historical success",
                context_factors=context,
            )
            for _ in range(3)
        ]
    )

    patterns = manager._analyze_historical_patterns(context)
    assert patterns["best_strategy"] == "balanced_multi"
    assert manager._contexts_similar(context, context) is True


def test_prompt_evolver_history_and_statistics(monkeypatch: pytest.MonkeyPatch) -> None:
    registry, tracker, optimizer = _setup_registry_tracker_optimizer()
    prompt_id = "history-prompt"

    base_variant = PromptVariant(
        content="Base", category=PromptCategory.CUSTOM, prompt_id=prompt_id
    )
    registry.register_variant(base_variant)
    tracker.record_execution(
        base_variant.id,
        prompt_id,
        PromptCategory.CUSTOM,
        success=True,
        execution_time=2.0,
        token_cost=1.0,
    )
    tracker.record_execution(
        base_variant.id,
        prompt_id,
        PromptCategory.CUSTOM,
        success=False,
        execution_time=3.0,
        token_cost=1.5,
    )

    evolver = PromptEvolver(_StubLLM(), registry, tracker, optimizer=optimizer)

    evolved_variant = PromptVariant(
        content="Evolved",
        category=PromptCategory.CUSTOM,
        prompt_id=prompt_id,
        parent_id=base_variant.id,
        metadata={"generated_at": "evolver", "evolution_strategy": "expansion"},
    )
    evolved_variant.total_executions = 10
    evolved_variant.successful_executions = 7
    evolved_variant.failed_executions = 3
    registry.register_variant(evolved_variant)
    tracker.record_execution(
        evolved_variant.id,
        prompt_id,
        PromptCategory.CUSTOM,
        success=True,
        execution_time=1.5,
        token_cost=0.8,
    )

    history = evolver.get_evolution_history(prompt_id)
    assert history

    strategy_counts = evolver._count_strategies([evolved_variant])
    assert strategy_counts["expansion"] == 1
    success_rate = evolver._calculate_strategy_success_rate(
        "expansion", [evolved_variant]
    )
    assert (
        success_rate
        == evolved_variant.successful_executions / evolved_variant.total_executions
    )
    evolver._calculate_strategy_success_rates(strategy_counts, [evolved_variant])

    monkeypatch.setattr(optimizer, "should_evolve_prompt", lambda pid: True)
    monkeypatch.setattr(evolver, "evolve_prompt", lambda pid: ["new variant content"])
    evolved = evolver.evolve_all_underperforming()
    assert prompt_id in evolved


@pytest.mark.asyncio
async def test_prompt_evolver_fallback(monkeypatch: pytest.MonkeyPatch) -> None:
    registry, tracker, optimizer = _setup_registry_tracker_optimizer()
    base_variant = PromptVariant(
        content="Fallback prompt content",
        category=PromptCategory.CUSTOM,
        prompt_id="prompt-fallback",
        metadata={},
    )
    registry.register_variant(base_variant)
    tracker.record_execution(
        variant_id=base_variant.id,
        prompt_id=base_variant.prompt_id,
        category=base_variant.category,
        success=True,
        execution_time=1.0,
        token_cost=1.0,
    )

    failing_llm = _StubLLM(responses=["{malformed json"])
    stub_optimizer = _StubOptimizer([base_variant])
    evolver = PromptEvolver(failing_llm, registry, tracker, optimizer=stub_optimizer)

    monkeypatch.setattr(
        optimizer,
        "get_candidates_for_evolution",
        lambda prompt_id: [base_variant],
    )

    # Force LLM generate to raise to trigger fallback within _generate_improved_variants
    def _raise_generate(*_, **__):
        raise RuntimeError("LLM failure")

    monkeypatch.setattr(failing_llm, "generate", _raise_generate)

    variant_ids = evolver.evolve_prompt(base_variant.prompt_id, max_variants=1)
    assert variant_ids
    assert stub_optimizer.added


# ---------------------------------------------------------------------------
# AdvancedStrategyManager & EnsembleStrategy
# ---------------------------------------------------------------------------


def test_strategy_manager_selection_and_insights(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    manager = AdvancedStrategyManager()
    # Deterministic exploration behaviour
    monkeypatch.setattr(
        "forge.prompt_optimization.advanced.strategy_manager.random.random", lambda: 0.0
    )

    context = {
        "content": "Generate optimized code quickly with high accuracy and low latency.",
        "performance_requirements": {"high_accuracy": True},
        "resource_constraints": {"limited_resources": True},
        "requirements": {"multi_level": True},
    }
    objectives = {"performance": 0.6, "efficiency": 0.4}
    constraints = {"max_memory": 2048, "max_time": 10, "min_accuracy": 0.4}

    selection = manager.select_strategy(context, objectives, constraints)
    assert selection.selected_strategy in manager.strategies
    assert selection.confidence >= 0.0
    assert selection.strategy_type in StrategyType

    manager.update_strategy_performance(
        selection.selected_strategy, success=True, score=0.9, context=context
    )

    insights = manager.get_strategy_insights()
    assert insights["total_selections"] == 1
    assert selection.selected_strategy in insights["strategy_usage"]


def test_ensemble_strategy_combines_results(monkeypatch: pytest.MonkeyPatch) -> None:
    manager = AdvancedStrategyManager()
    # Replace strategies with controllable stubs
    manager.strategies.clear()
    manager.strategies["strategy_a"] = _StubStrategy("strategy_a", result_score=0.8)
    manager.strategies["strategy_b"] = _StubStrategy("strategy_b", result_score=0.6)

    weights = {"strategy_a": 0.7, "strategy_b": 0.3}
    ensemble = manager.create_ensemble_strategy(strategy_weights=weights)

    variants = [
        PromptVariant(content="Variant A", category=PromptCategory.CUSTOM),
        PromptVariant(content="Variant B", category=PromptCategory.CUSTOM),
    ]
    metrics = {
        variants[0].id: PromptMetrics(
            success_rate=0.8,
            avg_execution_time=1.5,
            error_rate=0.1,
            avg_token_cost=10.0,
            sample_count=10,
        ),
        variants[1].id: PromptMetrics(
            success_rate=0.7,
            avg_execution_time=1.0,
            error_rate=0.05,
            avg_token_cost=8.0,
            sample_count=8,
        ),
    }

    result = ensemble.optimize({"confidence": 0.9}, variants, metrics)
    assert result["ensemble_result"]["score"] > 0
    assert result["strategy_count"] == 2
    assert set(result["weights"]) == {"strategy_a", "strategy_b"}


def test_strategy_manager_internal_helpers(monkeypatch: pytest.MonkeyPatch) -> None:
    manager = AdvancedStrategyManager()
    context_analysis = {
        "complexity": "high",
        "urgency": "high",
        "domain": "software",
        "task_type": "generation",
        "performance_requirements": {"high_accuracy": True},
        "resource_constraints": {"limited_resources": True},
        "historical_patterns": {"similar_contexts": 0},
    }
    score = manager._calculate_strategy_score(
        "balanced_multi",
        manager.strategies["balanced_multi"],
        context_analysis,
        {"performance": 0.7},
        {"max_time": 20, "max_memory": 2000, "min_accuracy": 0.1},
    )
    assert 0 <= score <= 1

    assert manager._satisfies_constraints("hierarchical", {"max_memory": 900}) is False
    assert (
        manager._satisfies_constraints("multi_objective_custom", {"max_time": 1})
        is False
    )
    assert (
        manager._satisfies_constraints("balanced_multi", {"min_accuracy": 0.9}) is False
    )

    alternatives = manager._get_alternatives({"a": 0.1, "b": 0.2}, "a")
    assert alternatives[0][0] == "b"

    reasoning = manager._generate_selection_reasoning(
        "context_aware", {"context_aware": 0.9}, context_analysis
    )
    assert "context-aware" in reasoning.lower()

    similar = manager._contexts_similar(
        {
            "complexity": "high",
            "domain": "software",
            "task_type": "generation",
            "urgency": "high",
        },
        {
            "complexity": "high",
            "domain": "software",
            "task_type": "generation",
            "urgency": "high",
        },
    )
    assert similar is True

    manager.update_strategy_performance(
        "balanced_multi", success=False, score=0.1, context=context_analysis
    )
    create_default = manager.create_ensemble_strategy()
    assert isinstance(create_default, EnsembleStrategy)
