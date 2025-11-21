from __future__ import annotations

import asyncio
import math
from datetime import datetime, timedelta
from typing import Any, Dict, List

import pytest

from forge.prompt_optimization.advanced.config import (
    AdvancedOptimizationConfig,
    AdvancedOptimizationMode,
    BASIC_CONFIG,
    CONTEXT_AWARE_CONFIG,
    EFFICIENCY_FOCUSED_CONFIG,
    FULL_CONFIG,
    HIERARCHICAL_CONFIG,
    PERFORMANCE_FOCUSED_CONFIG,
)
from forge.prompt_optimization.advanced.context_aware import (
    ContextAwareOptimizer,
    ContextualStrategy,
    Domain,
    ExecutionContext,
    OptimizationContext,
    TaskType,
)
from forge.prompt_optimization.advanced.hierarchical import (
    BALANCED_HIERARCHICAL_STRATEGY,
    HierarchicalOptimizer,
    LevelConfiguration,
    OptimizationLevel,
)
from forge.prompt_optimization.advanced.multi_objective import (
    BALANCED_STRATEGY,
    EFFICIENCY_FOCUSED_STRATEGY,
    INNOVATION_FOCUSED_STRATEGY,
    MultiObjectiveOptimizer,
    OptimizationObjective,
    OptimizationStrategy,
    ObjectiveWeight,
    PERFORMANCE_FOCUSED_STRATEGY,
)
from forge.prompt_optimization.models import (
    PromptCategory,
    PromptMetrics,
    PromptVariant,
)
from forge.prompt_optimization.optimizer import PromptOptimizer
from forge.prompt_optimization.registry import PromptRegistry
from forge.prompt_optimization.tracker import PerformanceTracker


# ---------------------------------------------------------------------------
# AdvancedOptimizationConfig
# ---------------------------------------------------------------------------


def test_advanced_config_defaults_and_roundtrip() -> None:
    config = AdvancedOptimizationConfig()
    strategy = config.get_multi_objective_strategy()

    assert isinstance(strategy, OptimizationStrategy)
    assert len(strategy.objectives) == len(config.default_objectives)
    assert math.isclose(strategy.exploration_rate, config.exploration_rate)

    config_dict = config.to_dict()
    restored = AdvancedOptimizationConfig.from_dict(config_dict)
    assert restored.mode == config.mode
    assert restored.objective_weights == config.objective_weights

    # Validate helper presets
    assert BASIC_CONFIG.mode == AdvancedOptimizationMode.BASIC
    assert CONTEXT_AWARE_CONFIG.context_aware_enabled is True
    assert HIERARCHICAL_CONFIG.hierarchical_enabled is True
    assert FULL_CONFIG.enable_ensemble is True
    assert PERFORMANCE_FOCUSED_CONFIG.objective_weights["performance"] > 0.5
    assert EFFICIENCY_FOCUSED_CONFIG.max_optimization_time == 10


def test_advanced_config_validation_paths() -> None:
    config = AdvancedOptimizationConfig(
        mode=AdvancedOptimizationMode.DISABLED,
        multi_objective_enabled=True,
        exploration_rate=1.5,
        adaptation_rate=-0.1,
        learning_rate=2.0,
        min_performance_threshold=0.9,
        high_performance_threshold=0.5,
        max_memory_usage=-1,
        max_optimization_time=0,
        max_concurrent_optimizations=0,
        performance_history_size=0,
        adaptation_frequency=0,
    )

    errors = config.validate()
    assert any("Mode is disabled" in err for err in errors)
    assert any("Exploration rate" in err for err in errors)
    assert any("Adaptation rate" in err for err in errors)
    assert any("Learning rate" in err for err in errors)
    assert any("Min performance threshold" in err for err in errors)
    assert any("Max memory usage" in err for err in errors)
    assert any("Performance history size" in err for err in errors)

    config.hierarchical_enabled = True
    levels = config.get_hierarchical_strategy()
    assert set(levels.keys()) == {
        OptimizationLevel.SYSTEM,
        OptimizationLevel.ROLE,
        OptimizationLevel.TOOL,
    }

    config.hierarchical_enabled = True
    config.objective_weights = {}
    strategy = config.get_multi_objective_strategy()
    # When weights missing they should fall back to 0.25
    assert all(math.isclose(obj.weight, 0.25) for obj in strategy.objectives)


# ---------------------------------------------------------------------------
# ContextAwareOptimizer
# ---------------------------------------------------------------------------


def _make_metrics(
    success_rate: float = 0.8,
    execution_time: float = 2.0,
    error_rate: float = 0.1,
    token_cost: float = 10.0,
    sample_count: int = 25,
) -> PromptMetrics:
    metrics = PromptMetrics(
        success_rate=success_rate,
        avg_execution_time=execution_time,
        error_rate=error_rate,
        avg_token_cost=token_cost,
        sample_count=sample_count,
    )
    metrics.composite_score = metrics._calculate_composite_score()
    return metrics


def test_context_aware_analysis_and_selection() -> None:
    optimizer = ContextAwareOptimizer()
    context_data = {
        "content": "Please generate code for a web React dashboard and explain edge cases.",
        "metadata": {"domain": "web_development"},
        "environment": {"name": "production"},
        "urgency": "critical",
        "historical_performance": {"urgent_production_performance": 0.9},
    }

    context = optimizer.analyze_context(context_data)
    assert context.task_type == TaskType.CODE_GENERATION
    assert context.domain == Domain.WEB_DEVELOPMENT
    assert context.execution_context == ExecutionContext.PRODUCTION
    assert context.complexity_level in {"low", "medium", "high"}

    strategy = optimizer.select_strategy(context)
    assert strategy.name in optimizer.context_strategies or strategy.name == "fallback"

    # Fallback path
    fallback_context = OptimizationContext(
        task_type=TaskType.GENERAL,
        domain=Domain.GENERAL,
        execution_context=ExecutionContext.DEBUG,
        complexity_level="low",
        urgency="low",
        user_preferences={},
        historical_performance={},
        available_resources={},
        constraints={},
    )
    fallback = optimizer.select_strategy(fallback_context)
    assert fallback.name in {"fallback", "urgent_production"}


def test_context_aware_adaptation_and_insights() -> None:
    optimizer = ContextAwareOptimizer()
    sample_strategy = ContextualStrategy(
        name="test_strategy",
        description="A synthetic strategy for tests",
        applicable_contexts=[
            (TaskType.REASONING, Domain.GENERAL, ExecutionContext.DEVELOPMENT)
        ],
        optimization_weights={
            "performance": 0.3,
            "efficiency": 0.3,
            "reliability": 0.4,
        },
        prompt_modifications={},
        performance_expectations={
            "min_success_rate": 0.8,
            "max_execution_time": 5.0,
            "max_error_rate": 0.1,
        },
        adaptation_rules=[
            {"condition": "success_rate < 0.9", "action": "increase_technical_depth"},
            {"condition": "execution_time > 2", "action": "simplify_approach"},
            {"condition": "error_rate > 0.05", "action": "add_validation"},
            {
                "condition": "innovation_score < 0.5",
                "action": "increase_creativity_prompts",
            },
            {"condition": "execution_time > 1", "action": "optimize_for_speed"},
            {"condition": "unsupported", "action": "no_op"},
        ],
    )

    context = OptimizationContext(
        task_type=TaskType.REASONING,
        domain=Domain.GENERAL,
        execution_context=ExecutionContext.DEVELOPMENT,
        complexity_level="high",
        urgency="critical",
        user_preferences={},
        historical_performance={"test_strategy_performance": 0.8},
        available_resources={},
        constraints={},
    )

    performance_data = {
        "success_rate": 0.5,
        "execution_time": 3.0,
        "error_rate": 0.2,
        "innovation_score": 0.4,
    }

    adapted = optimizer.adapt_strategy(sample_strategy, context, performance_data)
    assert adapted.name.endswith("_adapted")
    assert adapted.prompt_modifications["add_technical_depth"] is True
    assert adapted.prompt_modifications["add_validation"] is True
    assert (
        adapted.optimization_weights["efficiency"]
        > sample_strategy.optimization_weights["efficiency"]
    )

    optimizer.context_history.append(
        {
            "task_type": TaskType.REASONING,
            "domain": Domain.GENERAL,
            "strategy_name": "test_strategy",
        }
    )
    insights = optimizer.get_context_insights()
    assert insights["total_contexts_analyzed"] == 1
    assert "available_strategies" in insights


def test_context_aware_internal_helpers() -> None:
    optimizer = ContextAwareOptimizer()
    context = OptimizationContext(
        task_type=TaskType.REASONING,
        domain=Domain.SOFTWARE_DEVELOPMENT,
        execution_context=ExecutionContext.DEVELOPMENT,
        complexity_level="high",
        urgency="critical",
        user_preferences={},
        historical_performance={"reasoning_software_performance": 0.8},
        available_resources={},
        constraints={},
    )
    strategy = optimizer.context_strategies["reasoning_software"]
    score = optimizer._score_strategy_fit(strategy, context)
    assert score > 1.0

    fallback = optimizer._create_fallback_strategy(context)
    assert fallback.name == "fallback"

    # Exercise action helpers directly
    optimizer._apply_action("increase_technical_depth", strategy, context)
    optimizer._apply_action("simplify_approach", strategy, context)
    optimizer._apply_action("add_validation", strategy, context)
    optimizer._apply_action("increase_creativity_prompts", strategy, context)
    optimizer._apply_action("optimize_for_speed", strategy, context)
    optimizer._apply_action("no_op", strategy, context)

    # Invalid condition should return False without raising
    assert optimizer._evaluate_condition("unsupported", {}) is False


def test_context_aware_detection_variations() -> None:
    optimizer = ContextAwareOptimizer()

    # Domain detection via content keywords
    domain = optimizer._detect_domain(
        {}, "We should use pandas and numpy for data analysis in python."
    )
    assert domain == Domain.DATA_SCIENCE

    # Invalid metadata falls back to general
    domain_fallback = optimizer._detect_domain({"domain": "unknown_space"}, "")
    assert domain_fallback == Domain.GENERAL

    # Execution context detection variations
    assert (
        optimizer._detect_execution_context({"name": "debug-environment"})
        == ExecutionContext.DEBUG
    )
    assert (
        optimizer._detect_execution_context({"name": "prod env"})
        == ExecutionContext.PRODUCTION
    )
    assert (
        optimizer._detect_execution_context({"name": "Staging Area"})
        == ExecutionContext.STAGING
    )

    # Complexity levels
    high_complexity = optimizer._analyze_complexity("complex task " * 200)
    medium_complexity = optimizer._analyze_complexity("word " * 150)
    low_complexity = optimizer._analyze_complexity("Simple task.")
    assert high_complexity == "high"
    assert medium_complexity == "medium"
    assert low_complexity == "low"

    # Select strategy with fallback when no matches
    fallback_context = OptimizationContext(
        task_type=TaskType.GENERAL,
        domain=Domain.HEALTHCARE,
        execution_context=ExecutionContext.PERFORMANCE,
        complexity_level="medium",
        urgency="low",
        user_preferences={},
        historical_performance={},
        available_resources={},
        constraints={},
    )
    fallback_strategy = optimizer.select_strategy(fallback_context)
    assert fallback_strategy.name == "fallback"

    # Ensure historical performance adjusts scoring
    context = OptimizationContext(
        task_type=TaskType.REASONING,
        domain=Domain.SOFTWARE_DEVELOPMENT,
        execution_context=ExecutionContext.PRODUCTION,
        complexity_level="high",
        urgency="critical",
        user_preferences={},
        historical_performance={"reasoning_software_performance": 0.7},
        available_resources={},
        constraints={},
    )
    optimizer.context_strategies["custom_match"] = ContextualStrategy(
        name="custom_match",
        description="Custom strategy",
        applicable_contexts=[
            (
                TaskType.REASONING,
                Domain.SOFTWARE_DEVELOPMENT,
                ExecutionContext.PRODUCTION,
            )
        ],
        optimization_weights={"performance": 0.5},
        prompt_modifications={},
        performance_expectations={
            "min_success_rate": 0.6,
            "max_execution_time": 3.0,
            "max_error_rate": 0.1,
        },
        adaptation_rules=[],
    )
    selected = optimizer.select_strategy(context)
    assert selected.name in {"reasoning_software", "custom_match"}


# ---------------------------------------------------------------------------
# MultiObjectiveOptimizer
# ---------------------------------------------------------------------------


def test_multi_objective_scoring_and_pareto(monkeypatch: pytest.MonkeyPatch) -> None:
    # Ensure deterministic adaptation by disabling history-based adjustments
    strategy = BALANCED_STRATEGY
    optimizer = MultiObjectiveOptimizer(strategy)

    variant = PromptVariant(
        content="A highly innovative and creative approach with detailed reasoning.",
        metadata={"is_evolved": True, "strategy": "expansion"},
        category=PromptCategory.CUSTOM,
    )

    metrics = _make_metrics(
        success_rate=0.85,
        execution_time=1.5,
        error_rate=0.05,
        token_cost=20.0,
        sample_count=50,
    )
    composite, objective_scores = optimizer.calculate_composite_score(variant, metrics)
    assert 0.0 < composite <= 1.0
    assert "performance" in objective_scores

    optimizer.record_performance(variant, metrics, objective_scores)
    assert optimizer.performance_history

    adapted_composite, _ = optimizer.calculate_composite_score(variant, metrics)
    assert adapted_composite <= 1.0

    added = optimizer.update_pareto_front(variant, objective_scores)
    assert added is True

    # Exploration vs exploitation
    other_variant = PromptVariant(
        content="Stable baseline", metadata={}, category=PromptCategory.CUSTOM
    )
    other_metrics = _make_metrics(
        success_rate=0.7,
        execution_time=2.5,
        error_rate=0.1,
        token_cost=30.0,
        sample_count=40,
    )
    metric_map = {
        variant.id: metrics,
        other_variant.id: other_metrics,
    }

    selected_explore = optimizer.select_exploration_variant(
        [variant, other_variant], metric_map
    )
    assert selected_explore.id in {variant.id, other_variant.id}

    selected_exploit = optimizer.select_variant_for_exploitation(
        [variant, other_variant], metric_map
    )
    assert selected_exploit.id in {variant.id, other_variant.id}

    insights = optimizer.get_optimization_insights()
    assert "pareto_front_size" in insights
    assert insights["total_evaluations"] >= 1


def test_multi_objective_internal_behaviour() -> None:
    strategy = PERFORMANCE_FOCUSED_STRATEGY
    optimizer = MultiObjectiveOptimizer(strategy)
    variant = PromptVariant(
        content="Creative and innovative solution with breakthrough ideas.",
        metadata={"is_evolved": True, "strategy": "expansion"},
        category=PromptCategory.CUSTOM,
    )
    metrics = _make_metrics(
        success_rate=0.4,
        execution_time=40.0,
        error_rate=0.4,
        token_cost=200.0,
        sample_count=20,
    )

    innovation = optimizer._calculate_innovation_score(variant, {})
    assert innovation > 0.0

    composite, scores = optimizer.calculate_composite_score(variant, metrics)
    optimizer.record_performance(variant, metrics, scores)

    # Add history with high scores to adjust adaptation weights
    optimizer.performance_history.extend(
        [
            {
                "objective_scores": {"performance": 0.9, "reliability": 0.9},
                "metrics": {"success_rate": 0.9},
            }
            for _ in range(5)
        ]
    )
    adapter = optimizer._apply_adaptation(composite, scores)
    assert adapter <= 1.0

    optimizer.update_pareto_front(variant, scores)
    better_variant = PromptVariant(content="Superior", category=PromptCategory.CUSTOM)
    better_scores = {
        "performance": 0.95,
        "reliability": 0.95,
        "efficiency": 0.8,
        "cost": 0.7,
    }
    optimizer.update_pareto_front(better_variant, better_scores)
    front_ids = {entry.id for entry, _ in optimizer.pareto_front}
    assert better_variant.id in front_ids

    # Fallback branch in exploit selection when metrics missing
    selected = optimizer.select_variant_for_exploitation([variant], {})
    assert selected == variant

    # Ensure insights available even when model has history
    insights = optimizer.get_optimization_insights()
    assert "objective_performance" in insights


def test_multi_objective_weight_and_dominance_logic() -> None:
    weight = ObjectiveWeight(
        OptimizationObjective.PERFORMANCE, 0.4, min_value=1.0, max_value=1.0
    )
    assert weight.normalize_value(5.0) == 0.5

    optimizer = MultiObjectiveOptimizer(BALANCED_STRATEGY)
    variant_a = PromptVariant(
        content="Variant A creative innovative", category=PromptCategory.CUSTOM
    )
    variant_b = PromptVariant(
        content="Variant B efficient reliable", category=PromptCategory.CUSTOM
    )

    metrics_a = _make_metrics(
        success_rate=0.6,
        execution_time=3.0,
        error_rate=0.2,
        token_cost=150.0,
        sample_count=30,
    )
    metrics_b = _make_metrics(
        success_rate=0.9,
        execution_time=1.0,
        error_rate=0.05,
        token_cost=50.0,
        sample_count=40,
    )

    scores_a = optimizer.calculate_composite_score(variant_a, metrics_a)[1]
    scores_b = optimizer.calculate_composite_score(variant_b, metrics_b)[1]

    optimizer.update_pareto_front(variant_a, scores_a)
    optimizer.update_pareto_front(variant_b, scores_b)
    assert optimizer._dominates(scores_b, scores_a) is True

    # Shorten history to trigger slice logic
    optimizer.performance_history = [
        {"metrics": {"success_rate": 0.8}, "objective_scores": scores_a}
        for _ in range(120)
    ]
    optimizer.record_performance(variant_a, metrics_a, scores_a)


def test_multi_objective_predefined_strategies() -> None:
    strategies = [
        BALANCED_STRATEGY,
        PERFORMANCE_FOCUSED_STRATEGY,
        EFFICIENCY_FOCUSED_STRATEGY,
        INNOVATION_FOCUSED_STRATEGY,
    ]
    for strategy in strategies:
        assert sum(weight.weight for weight in strategy.objectives) > 0
        objectives = {weight.objective for weight in strategy.objectives}
        assert OptimizationObjective.PERFORMANCE in objectives


# ---------------------------------------------------------------------------
# HierarchicalOptimizer
# ---------------------------------------------------------------------------


class _DummyLevelOptimizer:
    def __init__(self, recommendation: str, score: float) -> None:
        self.recommendation = recommendation
        self.score = score

    def optimize(self, context: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "recommendation": self.recommendation,
            "score": self.score,
            "success_rate": context.get("success_rate", 0.7),
            "efficiency": context.get("efficiency", 0.6),
        }


def test_hierarchical_optimizer_end_to_end(monkeypatch: pytest.MonkeyPatch) -> None:
    optimizer = HierarchicalOptimizer(BALANCED_HIERARCHICAL_STRATEGY)
    # Deterministic optimization decision
    monkeypatch.setattr("random.random", lambda: 0.0)

    optimizer.initialize_level_optimizer(
        OptimizationLevel.SYSTEM, _DummyLevelOptimizer("increase", 0.6)
    )
    optimizer.initialize_level_optimizer(
        OptimizationLevel.ROLE, _DummyLevelOptimizer("increase", 0.65)
    )
    optimizer.initialize_level_optimizer(
        OptimizationLevel.TOOL, _DummyLevelOptimizer("decrease_cost", 0.55)
    )

    request = {
        "context": {"user": "tester"},
        "system_variants": ["system_a"],
        "system_metrics": {"success_rate": 0.7},
        "role_variants": ["role_a"],
        "role_metrics": {"success_rate": 0.6},
        "tool_variants": ["tool_a"],
        "tool_metrics": {"success_rate": 0.5},
    }

    results = optimizer.optimize_hierarchically(request)
    assert results
    for level in (
        OptimizationLevel.SYSTEM,
        OptimizationLevel.ROLE,
        OptimizationLevel.TOOL,
    ):
        assert level in results
        assert "global_coordination_score" in results[level]

    insights = optimizer.get_hierarchical_insights()
    assert insights["active_levels"]
    assert insights["coordination_history_size"] >= 1
    assert insights["strategy_name"] == BALANCED_HIERARCHICAL_STRATEGY.name
