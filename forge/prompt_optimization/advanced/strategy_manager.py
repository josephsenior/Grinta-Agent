"""Advanced Strategy Manager.

Orchestrates multiple optimization strategies and intelligently selects
the best approach based on context, performance history, and objectives.
"""

from __future__ import annotations

import json
import random
from collections.abc import Sequence
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Optional, cast
from datetime import datetime, timedelta

from forge.core.logger import forge_logger as logger
from forge.prompt_optimization.models import (
    PromptVariant,
    PromptMetrics,
    PromptCategory,
)
from forge.prompt_optimization.advanced.multi_objective import (
    MultiObjectiveOptimizer,
    OptimizationStrategy,
    BALANCED_STRATEGY,
    PERFORMANCE_FOCUSED_STRATEGY,
    EFFICIENCY_FOCUSED_STRATEGY,
    INNOVATION_FOCUSED_STRATEGY,
)
from forge.prompt_optimization.advanced.context_aware import (
    ContextAwareOptimizer,
    OptimizationContext,
    TaskType,
    Domain,
    ExecutionContext,
)
from forge.prompt_optimization.advanced.hierarchical import (
    HierarchicalOptimizer,
    HierarchicalStrategy,
    OptimizationLevel,
    BALANCED_HIERARCHICAL_STRATEGY,
)


class StrategyType(Enum):
    """Types of optimization strategies."""

    MULTI_OBJECTIVE = "multi_objective"
    CONTEXT_AWARE = "context_aware"
    HIERARCHICAL = "hierarchical"
    ENSEMBLE = "ensemble"
    ADAPTIVE = "adaptive"


@dataclass
class StrategyPerformance:
    """Performance metrics for a strategy."""

    strategy_name: str
    success_rate: float
    avg_score: float
    efficiency: float
    reliability: float
    cost_effectiveness: float
    sample_count: int
    last_updated: datetime
    context_success_rates: dict[str, float] = field(default_factory=dict)


@dataclass
class StrategySelection:
    """Strategy selection decision."""

    selected_strategy: str
    strategy_type: StrategyType
    confidence: float
    reasoning: str
    alternatives: list[tuple[str, float]] = field(default_factory=list)
    context_factors: dict[str, Any] = field(default_factory=dict)


class AdvancedStrategyManager:
    """Strategic orchestrator for multiple optimization strategies.

    Intelligently selects the best approach based on context and performance.
    """

    def __init__(self):
        """Initialize strategy registries, performance tracking, and ensemble defaults."""
        self.strategies: dict[str, Any] = {}
        self.strategy_performance: dict[str, StrategyPerformance] = {}
        self.selection_history: list[StrategySelection] = []
        self.ensemble_weights: dict[str, float] = {}
        self.adaptive_learning_rate = 0.1
        self.exploration_rate = 0.2

        # Initialize default strategies
        self._initialize_default_strategies()

    def _initialize_default_strategies(self) -> None:
        """Initialize default optimization strategies."""
        # Multi-objective strategies
        self.strategies["balanced_multi"] = MultiObjectiveOptimizer(BALANCED_STRATEGY)
        self.strategies["performance_multi"] = MultiObjectiveOptimizer(
            PERFORMANCE_FOCUSED_STRATEGY
        )
        self.strategies["efficiency_multi"] = MultiObjectiveOptimizer(
            EFFICIENCY_FOCUSED_STRATEGY
        )
        self.strategies["innovation_multi"] = MultiObjectiveOptimizer(
            INNOVATION_FOCUSED_STRATEGY
        )

        # Context-aware strategy
        self.strategies["context_aware"] = ContextAwareOptimizer()

        # Hierarchical strategy
        self.strategies["hierarchical"] = HierarchicalOptimizer(
            BALANCED_HIERARCHICAL_STRATEGY
        )

        # Initialize performance tracking
        for strategy_name in self.strategies.keys():
            self.strategy_performance[strategy_name] = StrategyPerformance(
                strategy_name=strategy_name,
                success_rate=0.5,  # Start with neutral performance
                avg_score=0.5,
                efficiency=0.5,
                reliability=0.5,
                cost_effectiveness=0.5,
                sample_count=0,
                last_updated=datetime.now(),
            )

    def select_strategy(
        self,
        context: dict[str, Any],
        objectives: Optional[dict[str, float]] = None,
        constraints: Optional[dict[str, Any]] = None,
    ) -> StrategySelection:
        """Select the best optimization strategy for the given context.

        Args:
            context: Context information for strategy selection
            objectives: Optimization objectives and weights
            constraints: Constraints that must be satisfied

        Returns:
            StrategySelection with the selected strategy and reasoning

        """
        # Analyze context
        context_analysis = self._analyze_context(context)

        # Score available strategies
        strategy_scores = self._score_strategies(
            context_analysis, objectives or {}, constraints or {}
        )

        # Select best strategy
        selected_strategy, confidence = self._select_best_strategy(strategy_scores)

        # Generate reasoning
        reasoning = self._generate_selection_reasoning(
            selected_strategy, strategy_scores, context_analysis
        )

        # Create selection record
        selection = StrategySelection(
            selected_strategy=selected_strategy,
            strategy_type=self._get_strategy_type(selected_strategy),
            confidence=confidence,
            reasoning=reasoning,
            alternatives=self._get_alternatives(strategy_scores, selected_strategy),
            context_factors=context_analysis,
        )

        # Record selection
        self.selection_history.append(selection)

        return selection

    def _detect_complexity(self, content: str) -> str:
        """Detect content complexity level.

        Args:
            content: Content to analyze

        Returns:
            Complexity level

        """
        if not content:
            return "medium"

        word_count = len(content.split())
        if word_count > 200:
            return "high"
        elif word_count < 50:
            return "low"
        return "medium"

    def _detect_urgency(self, content: str) -> str:
        """Detect urgency level from content.

        Args:
            content: Content to analyze

        Returns:
            Urgency level

        """
        urgency_indicators = ["urgent", "critical", "asap", "immediately"]
        if any(indicator in content.lower() for indicator in urgency_indicators):
            return "high"
        return "medium"

    def _detect_domain_from_content(self, content: str) -> str:
        """Detect domain from content.

        Args:
            content: Content to analyze

        Returns:
            Domain name

        """
        domain_indicators = {
            "software": ["code", "programming", "development", "api"],
            "data": ["analysis", "data", "statistics", "ml"],
            "web": ["web", "html", "css", "javascript", "react"],
            "creative": ["creative", "design", "innovative", "brainstorm"],
        }

        content_lower = content.lower()
        for domain, indicators in domain_indicators.items():
            if any(indicator in content_lower for indicator in indicators):
                return domain

        return "general"

    def _detect_task_type_from_content(self, content: str) -> str:
        """Detect task type from content.

        Args:
            content: Content to analyze

        Returns:
            Task type

        """
        task_indicators = {
            "reasoning": ["think", "reason", "analyze", "evaluate"],
            "generation": ["generate", "create", "write", "build"],
            "debugging": ["debug", "fix", "error", "problem"],
            "optimization": ["optimize", "improve", "enhance", "refine"],
        }

        content_lower = content.lower()
        for task_type, indicators in task_indicators.items():
            if any(indicator in content_lower for indicator in indicators):
                return task_type

        return "general"

    def _analyze_context(self, context: dict[str, Any]) -> dict[str, Any]:
        """Analyze context to extract relevant factors for strategy selection."""
        content = context.get("content", "")

        analysis = {
            "complexity": self._detect_complexity(content),
            "urgency": self._detect_urgency(content),
            "domain": self._detect_domain_from_content(content),
            "task_type": self._detect_task_type_from_content(content),
            "performance_requirements": context.get("performance_requirements", {}),
            "resource_constraints": context.get("resource_constraints", {}),
            "historical_patterns": self._analyze_historical_patterns(context),
        }

        return analysis

    def _analyze_historical_patterns(self, context: dict[str, Any]) -> dict[str, Any]:
        """Analyze historical performance patterns for similar contexts."""
        patterns = {
            "similar_contexts": 0,
            "avg_success_rate": 0.5,
            "best_strategy": None,
            "performance_trend": "stable",
        }

        # Find similar contexts in history
        similar_selections = []
        for selection in self.selection_history[-50:]:  # Last 50 selections
            if self._contexts_similar(context, selection.context_factors or {}):
                similar_selections.append(selection)

        patterns["similar_contexts"] = len(similar_selections)

        if similar_selections:
            # Calculate average success rate
            success_rates: list[float] = []
            strategy_performance_by_name: dict[str, list[float]] = {}

            for selection in similar_selections:
                strategy_name = selection.selected_strategy
                if strategy_name in self.strategy_performance:
                    perf = self.strategy_performance[strategy_name]
                    success_rates.append(perf.success_rate)

                    strategy_performance_by_name.setdefault(strategy_name, []).append(
                        perf.success_rate
                    )

            if success_rates:
                patterns["avg_success_rate"] = sum(success_rates) / len(success_rates)

            # Find best performing strategy
            if strategy_performance_by_name:
                best_strategy = max(
                    strategy_performance_by_name.items(),
                    key=lambda item: sum(item[1]) / len(item[1]),
                )
                patterns["best_strategy"] = best_strategy[0]

        return patterns

    def _contexts_similar(
        self, context1: dict[str, Any], context2: dict[str, Any]
    ) -> bool:
        """Check if two contexts are similar."""
        # Simple similarity check - can be made more sophisticated
        similarity_score = 0.0

        # Check complexity similarity
        if context1.get("complexity") == context2.get("complexity"):
            similarity_score += 0.3

        # Check domain similarity
        if context1.get("domain") == context2.get("domain"):
            similarity_score += 0.3

        # Check task type similarity
        if context1.get("task_type") == context2.get("task_type"):
            similarity_score += 0.3

        # Check urgency similarity
        if context1.get("urgency") == context2.get("urgency"):
            similarity_score += 0.1

        return similarity_score >= 0.6

    def _score_strategies(
        self,
        context_analysis: dict[str, Any],
        objectives: dict[str, float],
        constraints: dict[str, Any],
    ) -> dict[str, float]:
        """Score all available strategies based on context and objectives."""
        scores = {}

        for strategy_name, strategy in self.strategies.items():
            score = self._calculate_strategy_score(
                strategy_name, strategy, context_analysis, objectives, constraints
            )
            scores[strategy_name] = score

        return scores

    def _calculate_strategy_score(
        self,
        strategy_name: str,
        strategy: Any,
        context_analysis: dict[str, Any],
        objectives: dict[str, float],
        constraints: dict[str, Any],
    ) -> float:
        """Calculate score for a specific strategy."""
        base_score = 0.5  # Start with neutral score

        # Get strategy performance
        perf = self.strategy_performance.get(strategy_name)
        if perf:
            # Weight recent performance more heavily
            recency_weight = min(1.0, perf.sample_count / 100.0)
            base_score = (1 - recency_weight) * 0.5 + recency_weight * perf.success_rate

        # Adjust based on context fit
        context_fit = self._calculate_context_fit(strategy_name, context_analysis)
        base_score = 0.7 * base_score + 0.3 * context_fit

        # Adjust based on objectives alignment
        objectives_alignment = self._calculate_objectives_alignment(
            strategy_name, objectives
        )
        base_score = 0.6 * base_score + 0.4 * objectives_alignment

        # Apply constraints
        if not self._satisfies_constraints(strategy_name, constraints):
            base_score *= 0.5  # Penalize strategies that don't satisfy constraints

        # Add exploration bonus for under-explored strategies
        if perf and perf.sample_count < 10:
            base_score += 0.1  # Exploration bonus

        return max(0.0, min(1.0, base_score))

    def _score_multi_objective_fit(self, context_analysis: dict[str, Any]) -> float:
        """Score multi-objective strategy fitness.

        Args:
            context_analysis: Context analysis

        Returns:
            Fitness score

        """
        score = 0.0
        if context_analysis.get("complexity") == "high":
            score += 0.2
        if context_analysis.get("urgency") == "high":
            score += 0.1
        return score

    def _score_context_aware_fit(self, context_analysis: dict[str, Any]) -> float:
        """Score context-aware strategy fitness.

        Args:
            context_analysis: Context analysis

        Returns:
            Fitness score

        """
        score = 0.0
        if context_analysis.get("domain") != "general":
            score += 0.3
        if context_analysis.get("task_type") != "general":
            score += 0.2
        return score

    def _score_hierarchical_fit(self, context_analysis: dict[str, Any]) -> float:
        """Score hierarchical strategy fitness.

        Args:
            context_analysis: Context analysis

        Returns:
            Fitness score

        """
        score = 0.0
        if context_analysis.get("complexity") == "high":
            score += 0.3
        if "multi_level" in context_analysis.get("requirements", {}):
            score += 0.2
        return score

    def _calculate_context_fit(
        self, strategy_name: str, context_analysis: dict[str, Any]
    ) -> float:
        """Calculate how well a strategy fits the context."""
        fit_score = 0.5  # Default fit

        # Strategy-specific scoring
        if "multi" in strategy_name:
            fit_score += self._score_multi_objective_fit(context_analysis)
        elif strategy_name == "context_aware":
            fit_score += self._score_context_aware_fit(context_analysis)
        elif strategy_name == "hierarchical":
            fit_score += self._score_hierarchical_fit(context_analysis)

        # General strategy scoring
        if "performance" in strategy_name:
            if context_analysis.get("performance_requirements", {}).get(
                "high_accuracy"
            ):
                fit_score += 0.2

        if "efficiency" in strategy_name:
            if context_analysis.get("resource_constraints", {}).get(
                "limited_resources"
            ):
                fit_score += 0.2

        return max(0.0, min(1.0, fit_score))

    def _calculate_objective_score(
        self, objective: str, strategy_name: str, weight: float
    ) -> float:
        """Calculate score for a single objective.

        Args:
            objective: Objective name
            strategy_name: Strategy being evaluated
            weight: Objective weight

        Returns:
            Weighted score

        """
        # Objective-strategy alignment mapping
        alignments = {
            ("performance", "performance"): 0.9,
            ("efficiency", "efficiency"): 0.9,
            ("cost", "efficiency"): 0.8,
            ("reliability", "performance"): 0.8,
            ("innovation", "innovation"): 0.9,
        }

        for (obj, strat), score in alignments.items():
            if objective == obj and strat in strategy_name:
                return weight * score

        return weight * 0.5  # Neutral alignment

    def _calculate_objectives_alignment(
        self, strategy_name: str, objectives: dict[str, float]
    ) -> float:
        """Calculate how well a strategy aligns with objectives."""
        if not objectives:
            return 0.5

        alignment_score = sum(
            self._calculate_objective_score(objective, strategy_name, weight)
            for objective, weight in objectives.items()
        )
        total_weight = sum(objectives.values())

        return alignment_score / max(total_weight, 1.0)

    def _check_memory_constraint(self, strategy_name: str, max_memory: int) -> bool:
        """Check if strategy satisfies memory constraint.

        Args:
            strategy_name: Name of strategy
            max_memory: Maximum memory constraint

        Returns:
            True if constraint satisfied

        """
        if "hierarchical" in strategy_name and max_memory < 1000:
            return False
        return True

    def _check_time_constraint(self, strategy_name: str, max_time: int) -> bool:
        """Check if strategy satisfies time constraint.

        Args:
            strategy_name: Name of strategy
            max_time: Maximum time constraint

        Returns:
            True if constraint satisfied

        """
        if "multi_objective" in strategy_name and max_time < 5:
            return False
        return True

    def _check_accuracy_constraint(
        self, strategy_name: str, min_accuracy: float
    ) -> bool:
        """Check if strategy satisfies accuracy constraint.

        Args:
            strategy_name: Name of strategy
            min_accuracy: Minimum accuracy constraint

        Returns:
            True if constraint satisfied

        """
        perf = self.strategy_performance.get(strategy_name)
        if perf and perf.success_rate < min_accuracy:
            return False
        return True

    def _satisfies_constraints(
        self, strategy_name: str, constraints: dict[str, Any]
    ) -> bool:
        """Check if strategy satisfies given constraints."""
        if not constraints:
            return True

        if "max_memory" in constraints:
            if not self._check_memory_constraint(
                strategy_name, constraints["max_memory"]
            ):
                return False

        if "max_time" in constraints:
            if not self._check_time_constraint(strategy_name, constraints["max_time"]):
                return False

        if "min_accuracy" in constraints:
            if not self._check_accuracy_constraint(
                strategy_name, constraints["min_accuracy"]
            ):
                return False

        return True

    def _select_best_strategy(
        self, strategy_scores: dict[str, float]
    ) -> tuple[str, float]:
        """Select the best strategy from scored strategies."""
        if not strategy_scores:
            return "balanced_multi", 0.5  # Fallback

        # Sort by score
        sorted_strategies = sorted(
            strategy_scores.items(), key=lambda x: x[1], reverse=True
        )

        best_strategy, best_score = sorted_strategies[0]

        # Add some exploration
        if random.random() < self.exploration_rate and len(sorted_strategies) > 1:
            # Sometimes select second-best for exploration
            second_best = sorted_strategies[1]
            if second_best[1] > best_score * 0.8:  # If second-best is close
                return second_best[0], second_best[1]

        return best_strategy, best_score

    def _get_strategy_type(self, strategy_name: str) -> StrategyType:
        """Get the type of a strategy."""
        if "multi" in strategy_name:
            return StrategyType.MULTI_OBJECTIVE
        elif strategy_name == "context_aware":
            return StrategyType.CONTEXT_AWARE
        elif strategy_name == "hierarchical":
            return StrategyType.HIERARCHICAL
        else:
            return StrategyType.ADAPTIVE

    def _get_alternatives(
        self, strategy_scores: dict[str, float], selected_strategy: str
    ) -> list[tuple[str, float]]:
        """Get alternative strategies with their scores."""
        alternatives = []
        for strategy, score in strategy_scores.items():
            if strategy != selected_strategy:
                alternatives.append((strategy, score))

        # Sort by score descending
        alternatives.sort(key=lambda x: x[1], reverse=True)
        return alternatives[:3]  # Top 3 alternatives

    def _generate_selection_reasoning(
        self,
        selected_strategy: str,
        strategy_scores: dict[str, float],
        context_analysis: dict[str, Any],
    ) -> str:
        """Generate human-readable reasoning for strategy selection."""
        reasoning_parts = []

        # Add context-based reasoning
        if context_analysis.get("complexity") == "high":
            reasoning_parts.append(
                "High complexity task requires sophisticated optimization"
            )

        if context_analysis.get("urgency") == "high":
            reasoning_parts.append("Urgent task requires fast, reliable optimization")

        if context_analysis.get("domain") != "general":
            reasoning_parts.append(
                f"Domain-specific task ({context_analysis['domain']}) benefits from specialized approach"
            )

        # Add strategy-specific reasoning
        if "multi" in selected_strategy:
            reasoning_parts.append(
                "Multi-objective optimization balances multiple performance criteria"
            )
        elif selected_strategy == "context_aware":
            reasoning_parts.append(
                "Context-aware optimization adapts to specific task requirements"
            )
        elif selected_strategy == "hierarchical":
            reasoning_parts.append(
                "Hierarchical optimization coordinates across multiple levels"
            )

        # Add performance-based reasoning
        selected_score = strategy_scores.get(selected_strategy, 0)
        if selected_score > 0.8:
            reasoning_parts.append(
                "Strategy shows excellent performance for this context"
            )
        elif selected_score > 0.6:
            reasoning_parts.append("Strategy shows good performance for this context")

        return (
            ". ".join(reasoning_parts)
            if reasoning_parts
            else "Strategy selected based on available options"
        )

    def update_strategy_performance(
        self,
        strategy_name: str,
        success: bool,
        score: float,
        context: Optional[dict[str, Any]] = None,
    ) -> None:
        """Update performance metrics for a strategy."""
        if strategy_name not in self.strategy_performance:
            self.strategy_performance[strategy_name] = StrategyPerformance(
                strategy_name=strategy_name,
                success_rate=0.5,
                avg_score=0.5,
                efficiency=0.5,
                reliability=0.5,
                cost_effectiveness=0.5,
                sample_count=0,
                last_updated=datetime.now(),
            )

        perf = self.strategy_performance[strategy_name]

        # Update with exponential moving average
        alpha = self.adaptive_learning_rate

        # Update success rate
        new_success_rate = 1.0 if success else 0.0
        perf.success_rate = (1 - alpha) * perf.success_rate + alpha * new_success_rate

        # Update average score
        perf.avg_score = (1 - alpha) * perf.avg_score + alpha * score

        # Update sample count
        perf.sample_count += 1

        # Update timestamp
        perf.last_updated = datetime.now()

        # Update context-specific success rates
        if context:
            context_key = (
                f"{context.get('domain', 'general')}_{context.get('task_type', 'general')}"
            )
            current_rate = perf.context_success_rates.get(context_key, 0.5)
            perf.context_success_rates[context_key] = (
                (1 - alpha) * current_rate + alpha * new_success_rate
            )

    def get_strategy_insights(self) -> dict[str, Any]:
        """Get insights about strategy performance and selection patterns."""
        total_selections = len(self.selection_history)

        if total_selections == 0:
            return {"message": "No strategy selections recorded yet"}

        # Strategy usage statistics
        strategy_usage: dict[str, int] = {}
        for selection in self.selection_history:
            strategy = selection.selected_strategy
            strategy_usage[strategy] = strategy_usage.get(strategy, 0) + 1

        # Performance statistics
        strategy_performance_data: dict[str, dict[str, Any]] = {}
        for strategy_name, perf in self.strategy_performance.items():
            strategy_performance_data[strategy_name] = {
                "success_rate": perf.success_rate,
                "avg_score": perf.avg_score,
                "sample_count": perf.sample_count,
                "last_updated": perf.last_updated.isoformat(),
            }

        # Context pattern analysis
        context_patterns: dict[str, dict[str, int]] = {
            "complexity_distribution": {},
            "domain_distribution": {},
            "task_type_distribution": {},
            "urgency_distribution": {},
        }

        for selection in self.selection_history:
            factors = selection.context_factors or {}

            for pattern_type, distribution in context_patterns.items():
                key = pattern_type.replace("_distribution", "")
                value = factors.get(key, "unknown")
                distribution[value] = distribution.get(value, 0) + 1

        return {
            "total_selections": total_selections,
            "strategy_usage": strategy_usage,
            "strategy_performance": strategy_performance_data,
            "context_patterns": context_patterns,
            "avg_confidence": sum(s.confidence for s in self.selection_history)
            / total_selections,
            "exploration_rate": self.exploration_rate,
            "adaptive_learning_rate": self.adaptive_learning_rate,
        }

    def create_ensemble_strategy(
        self, strategy_weights: Optional[dict[str, float]] = None
    ) -> "EnsembleStrategy":
        """Create an ensemble strategy combining multiple approaches."""
        if strategy_weights is None:
            # Use performance-based weights
            strategy_weights = dict[str, float]()
            total_performance = 0.0

            for strategy_name, perf in self.strategy_performance.items():
                performance_score = perf.success_rate * perf.avg_score
                strategy_weights[strategy_name] = performance_score
                total_performance += performance_score

            # Normalize weights
            if total_performance > 0:
                for strategy_name in strategy_weights:
                    strategy_weights[strategy_name] /= total_performance

        return EnsembleStrategy(
            strategies=self.strategies, weights=strategy_weights, manager=self
        )


class EnsembleStrategy:
    """Ensemble strategy that combines multiple optimization approaches."""

    def __init__(
        self,
        strategies: dict[str, Any],
        weights: dict[str, float],
        manager: AdvancedStrategyManager,
    ):
        """Store the participating strategies, their weights, and the managing coordinator."""
        self.strategies = strategies
        self.weights = weights
        self.manager = manager

    def optimize(
        self,
        context: dict[str, Any],
        variants: list[PromptVariant],
        metrics: dict[str, PromptMetrics],
    ) -> dict[str, Any]:
        """Perform ensemble optimization."""
        results: dict[str, dict[str, Any]] = {}

        # Get results from each strategy
        for strategy_name, strategy in self.strategies.items():
            if strategy_name in self.weights and self.weights[strategy_name] > 0:
                try:
                    if hasattr(strategy, "optimize"):
                        result = strategy.optimize(context)
                    elif hasattr(strategy, "select_variant"):
                        result = strategy.select_variant(variants, metrics)
                    else:
                        continue

                    results[strategy_name] = {
                        "result": result,
                        "weight": self.weights[strategy_name],
                    }
                except Exception as e:
                    logger.warning(f"Strategy {strategy_name} failed: {e}")
                    continue

        # Combine results
        combined_result = self._combine_results(results)

        return {
            "ensemble_result": combined_result,
            "individual_results": results,
            "weights": self.weights,
            "strategy_count": len(results),
        }

    def _combine_results(self, results: dict[str, dict[str, Any]]) -> dict[str, Any]:
        """Combine results from multiple strategies."""
        if not results:
            return {}

        # Simple weighted combination - can be made more sophisticated
        combined_recommendations: list[Any] = []
        combined_metadata: dict[str, Any] = {}
        combined: dict[str, Any] = {
            "confidence": 0.0,
            "score": 0.0,
            "recommendations": combined_recommendations,
            "metadata": combined_metadata,
        }

        total_weight = 0.0

        for strategy_name, data in results.items():
            weight = data["weight"]
            result = data["result"]

            # Combine confidence scores
            if "confidence" in result:
                combined["confidence"] += result["confidence"] * weight

            # Combine scores
            if "score" in result:
                combined["score"] += result["score"] * weight

            # Collect recommendations
            if "recommendations" in result:
                recommendations = cast(Sequence[Any], result["recommendations"])
                combined_recommendations.extend(recommendations)

            # Collect metadata
            if "metadata" in result:
                combined_metadata[strategy_name] = result["metadata"]

            total_weight += weight

        # Normalize scores
        if total_weight > 0:
            combined["confidence"] /= total_weight
            combined["score"] /= total_weight

        return combined
