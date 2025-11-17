"""Multi-Objective Optimization Engine.

Implements advanced optimization strategies that balance multiple objectives
simultaneously (performance, cost, speed, reliability) using Pareto optimization
and weighted scoring approaches.
"""

from __future__ import annotations

import json
import math
from dataclasses import dataclass
from enum import Enum
from typing import Any, Optional
from datetime import datetime

from forge.core.logger import forge_logger as logger
from forge.prompt_optimization.models import (
    PromptVariant,
    PromptMetrics,
    PromptCategory,
)


class OptimizationObjective(Enum):
    """Optimization objectives that can be balanced."""

    PERFORMANCE = "performance"  # Success rate, accuracy
    EFFICIENCY = "efficiency"  # Speed, response time
    COST = "cost"  # Token usage, API costs
    RELIABILITY = "reliability"  # Consistency, error rate
    INNOVATION = "innovation"  # Novelty, creativity


@dataclass
class ObjectiveWeight:
    """Weight configuration for multi-objective optimization."""

    objective: OptimizationObjective
    weight: float
    min_value: float = 0.0
    max_value: float = 1.0
    is_higher_better: bool = True

    def normalize_value(self, value: float) -> float:
        """Normalize value to [0, 1] range."""
        if self.max_value == self.min_value:
            return 0.5
        normalized = (value - self.min_value) / (self.max_value - self.min_value)
        return max(0.0, min(1.0, normalized))


@dataclass
class OptimizationStrategy:
    """Configuration for optimization strategy."""

    name: str
    description: str
    objectives: list[ObjectiveWeight]
    pareto_threshold: float = 0.1
    exploration_rate: float = 0.2
    exploitation_rate: float = 0.8
    adaptation_rate: float = 0.1


class MultiObjectiveOptimizer:
    """Advanced multi-objective optimization engine.

    Balances multiple performance criteria simultaneously.
    """

    def __init__(self, strategy: OptimizationStrategy):
        """Store the optimization strategy and initialize pareto/history structures."""
        self.strategy = strategy
        self.pareto_front: list[tuple[PromptVariant, dict[str, float]]] = []
        self.performance_history: list[dict[str, Any]] = []
        self.adaptation_weights: dict[OptimizationObjective, float] = {
            obj.objective: obj.weight for obj in strategy.objectives
        }

    def calculate_composite_score(
        self,
        variant: PromptVariant,
        metrics: PromptMetrics,
        context: Optional[dict[str, Any]] = None,
    ) -> tuple[float, dict[str, float]]:
        """Calculate composite score balancing multiple objectives.

        Returns:
            Tuple of (composite_score, objective_scores)

        """
        objective_scores: dict[str, float] = {}

        # Calculate individual objective scores
        for obj_weight in self.strategy.objectives:
            score = 0.0
            if obj_weight.objective == OptimizationObjective.PERFORMANCE:
                score = self._calculate_performance_score(metrics)
            elif obj_weight.objective == OptimizationObjective.EFFICIENCY:
                score = self._calculate_efficiency_score(metrics)
            elif obj_weight.objective == OptimizationObjective.COST:
                score = self._calculate_cost_score(metrics)
            elif obj_weight.objective == OptimizationObjective.RELIABILITY:
                score = self._calculate_reliability_score(metrics)
            elif obj_weight.objective == OptimizationObjective.INNOVATION:
                score = self._calculate_innovation_score(variant, context)

            # Normalize and store
            normalized_score = obj_weight.normalize_value(score)
            if not obj_weight.is_higher_better:
                normalized_score = 1.0 - normalized_score

            objective_scores[obj_weight.objective.value] = normalized_score

        # Calculate weighted composite score
        composite_score = sum(
            objective_scores[obj.objective.value] * obj.weight
            for obj in self.strategy.objectives
        )

        # Apply adaptation based on historical performance
        composite_score = self._apply_adaptation(composite_score, objective_scores)

        return composite_score, objective_scores

    def _calculate_performance_score(self, metrics: PromptMetrics) -> float:
        """Calculate performance-based score."""
        # Weighted combination of success rate and composite score
        success_weight = 0.7
        composite_weight = 0.3

        return (
            success_weight * metrics.success_rate
            + composite_weight * metrics.composite_score
        )

    def _calculate_efficiency_score(self, metrics: PromptMetrics) -> float:
        """Calculate efficiency-based score (speed)."""
        # Inverse of execution time (faster = better)
        if metrics.avg_execution_time <= 0:
            return 0.0

        # Normalize to reasonable range (0-10 seconds)
        max_time = 10.0
        normalized_time = min(metrics.avg_execution_time / max_time, 1.0)
        return 1.0 - normalized_time

    def _calculate_cost_score(self, metrics: PromptMetrics) -> float:
        """Calculate cost-based score (lower cost = better)."""
        # Inverse of token cost
        if metrics.avg_token_cost <= 0:
            return 1.0

        # Normalize to reasonable range (0-1000 tokens)
        max_cost = 1000.0
        normalized_cost = min(metrics.avg_token_cost / max_cost, 1.0)
        return 1.0 - normalized_cost

    def _calculate_reliability_score(self, metrics: PromptMetrics) -> float:
        """Calculate reliability-based score (consistency)."""
        # Higher sample count and lower error rate = more reliable
        sample_score = min(metrics.sample_count / 100.0, 1.0)  # Normalize sample count
        error_score = 1.0 - metrics.error_rate

        return (sample_score + error_score) / 2.0

    def _calculate_innovation_score(
        self, variant: PromptVariant, context: Optional[dict[str, Any]] = None
    ) -> float:
        """Calculate innovation score (novelty, creativity)."""
        # Simple heuristic based on variant metadata and content
        innovation_score = 0.0

        # Check for creative indicators in content
        content = variant.content.lower()
        creative_indicators = [
            "creative",
            "innovative",
            "novel",
            "unique",
            "original",
            "breakthrough",
            "cutting-edge",
            "advanced",
            "sophisticated",
        ]

        for indicator in creative_indicators:
            if indicator in content:
                innovation_score += 0.1

        # Check metadata for innovation flags
        if variant.metadata.get("is_evolved", False):
            innovation_score += 0.3

        if variant.metadata.get("strategy", "") in ["expansion", "restructuring"]:
            innovation_score += 0.2

        # Check for content diversity (simplified)
        if len(set(content.split())) > 50:  # Diverse vocabulary
            innovation_score += 0.2

        return min(innovation_score, 1.0)

    def _apply_adaptation(
        self, base_score: float, objective_scores: dict[str, float]
    ) -> float:
        """Apply adaptive learning to the composite score."""
        if not self.performance_history:
            return base_score

        # Calculate recent performance trends
        recent_history = self.performance_history[-10:]  # Last 10 iterations

        # Adapt weights based on what's been working
        for obj_weight in self.strategy.objectives:
            obj_name = obj_weight.objective.value
            recent_scores = [
                h.get("objective_scores", {}).get(obj_name, 0) for h in recent_history
            ]

            if recent_scores:
                avg_recent_score = sum(recent_scores) / len(recent_scores)
                # Increase weight for objectives that have been performing well
                if avg_recent_score > 0.7:
                    self.adaptation_weights[obj_weight.objective] *= 1.1
                elif avg_recent_score < 0.3:
                    self.adaptation_weights[obj_weight.objective] *= 0.9

                # Keep weights in reasonable bounds
                self.adaptation_weights[obj_weight.objective] = max(
                    0.1, min(2.0, self.adaptation_weights[obj_weight.objective])
                )

        # Recalculate with adapted weights
        adapted_score = sum(
            objective_scores[obj.objective.value]
            * self.adaptation_weights[obj.objective]
            for obj in self.strategy.objectives
        )

        # Blend original and adapted scores
        return (
            1 - self.strategy.adaptation_rate
        ) * base_score + self.strategy.adaptation_rate * adapted_score

    def update_pareto_front(
        self, variant: PromptVariant, objective_scores: dict[str, float]
    ) -> bool:
        """Update Pareto front with new variant.

        Returns:
            True if variant was added to Pareto front

        """
        # Check if variant dominates any existing Pareto solutions
        dominated_indices = []
        for i, (_, scores) in enumerate(self.pareto_front):
            if self._dominates(objective_scores, scores):
                dominated_indices.append(i)

        # Remove dominated solutions
        for i in reversed(dominated_indices):
            del self.pareto_front[i]

        # Check if this variant is dominated by any Pareto solution
        is_dominated = any(
            self._dominates(scores, objective_scores) for _, scores in self.pareto_front
        )

        if not is_dominated:
            self.pareto_front.append((variant, objective_scores))
            return True

        return False

    def _dominates(self, scores1: dict[str, float], scores2: dict[str, float]) -> bool:
        """Check if scores1 dominates scores2 (Pareto dominance)."""
        better_in_at_least_one = False

        for obj_weight in self.strategy.objectives:
            obj_name = obj_weight.objective.value
            score1 = scores1.get(obj_name, 0)
            score2 = scores2.get(obj_name, 0)

            if obj_weight.is_higher_better:
                if score1 < score2:
                    return False  # Not dominated
                elif score1 > score2:
                    better_in_at_least_one = True
            else:
                if score1 > score2:
                    return False  # Not dominated
                elif score1 < score2:
                    better_in_at_least_one = True

        return better_in_at_least_one

    def get_pareto_optimal_variants(
        self,
    ) -> list[tuple[PromptVariant, dict[str, float]]]:
        """Get all Pareto optimal variants."""
        return self.pareto_front.copy()

    def select_exploration_variant(
        self, available_variants: list[PromptVariant], metrics: dict[str, PromptMetrics]
    ) -> Optional[PromptVariant]:
        """Select a variant for exploration (trying new approaches).

        Uses Upper Confidence Bound (UCB) for exploration-exploitation balance.
        """
        if not available_variants:
            return None

        # Calculate UCB scores for each variant
        ucb_scores: list[tuple[PromptVariant, float]] = []
        for variant in available_variants:
            variant_metrics = metrics.get(variant.id)
            if not variant_metrics:
                # High UCB for unexplored variants
                ucb_scores.append((variant, 1.0))
                continue

            # Calculate UCB: mean + confidence_bound
            mean_score = variant_metrics.composite_score
            confidence_bound = math.sqrt(
                2
                * math.log(sum(m.sample_count for m in metrics.values()))
                / max(variant_metrics.sample_count, 1)
            )

            ucb_score = mean_score + self.strategy.exploration_rate * confidence_bound
            ucb_scores.append((variant, ucb_score))

        # Select variant with highest UCB score
        ucb_scores.sort(key=lambda x: x[1], reverse=True)
        return ucb_scores[0][0]

    def select_variant_for_exploitation(
        self, available_variants: list[PromptVariant], metrics: dict[str, PromptMetrics]
    ) -> Optional[PromptVariant]:
        """Select variant for exploitation (using known good approaches)."""
        if not available_variants:
            return None

        # Select variant with highest composite score
        scored_variants: list[tuple[PromptVariant, float]] = []
        for variant in available_variants:
            variant_metrics = metrics.get(variant.id)
            if variant_metrics:
                scored_variants.append((variant, variant_metrics.composite_score))

        if not scored_variants:
            return available_variants[0]  # Fallback to first available

        scored_variants.sort(key=lambda x: x[1], reverse=True)
        return scored_variants[0][0]

    def record_performance(
        self,
        variant: PromptVariant,
        metrics: PromptMetrics,
        objective_scores: dict[str, float],
    ) -> None:
        """Record performance for learning and adaptation."""
        self.performance_history.append(
            {
                "timestamp": datetime.now().isoformat(),
                "variant_id": variant.id,
                "metrics": {
                    "success_rate": metrics.success_rate,
                    "avg_execution_time": metrics.avg_execution_time,
                    "error_rate": metrics.error_rate,
                    "avg_token_cost": metrics.avg_token_cost,
                    "composite_score": metrics.composite_score,
                },
                "objective_scores": objective_scores,
                "adaptation_weights": self.adaptation_weights.copy(),
            }
        )

        # Keep only recent history (last 100 records)
        if len(self.performance_history) > 100:
            self.performance_history = self.performance_history[-100:]

    def get_optimization_insights(self) -> dict[str, Any]:
        """Get insights about optimization performance."""
        if not self.performance_history:
            return {"message": "No performance data available"}

        recent_history = self.performance_history[-20:]  # Last 20 records

        # Calculate trends
        success_rates = [h["metrics"]["success_rate"] for h in recent_history]
        avg_success_rate = (
            sum(success_rates) / len(success_rates) if success_rates else 0
        )

        # Calculate objective performance
        objective_performance = {}
        for obj_weight in self.strategy.objectives:
            obj_name = obj_weight.objective.value
            scores = [h["objective_scores"].get(obj_name, 0) for h in recent_history]
            objective_performance[obj_name] = {
                "avg_score": sum(scores) / len(scores) if scores else 0,
                "trend": "improving"
                if len(scores) > 1 and scores[-1] > scores[0]
                else "stable",
            }

        return {
            "pareto_front_size": len(self.pareto_front),
            "avg_success_rate": avg_success_rate,
            "objective_performance": objective_performance,
            "adaptation_weights": self.adaptation_weights,
            "total_evaluations": len(self.performance_history),
        }


# Predefined optimization strategies
BALANCED_STRATEGY = OptimizationStrategy(
    name="balanced",
    description="Balanced optimization across all objectives",
    objectives=[
        ObjectiveWeight(OptimizationObjective.PERFORMANCE, 0.3),
        ObjectiveWeight(OptimizationObjective.EFFICIENCY, 0.25),
        ObjectiveWeight(OptimizationObjective.COST, 0.25),
        ObjectiveWeight(OptimizationObjective.RELIABILITY, 0.2),
    ],
)

PERFORMANCE_FOCUSED_STRATEGY = OptimizationStrategy(
    name="performance_focused",
    description="Prioritizes performance and reliability",
    objectives=[
        ObjectiveWeight(OptimizationObjective.PERFORMANCE, 0.5),
        ObjectiveWeight(OptimizationObjective.RELIABILITY, 0.3),
        ObjectiveWeight(OptimizationObjective.EFFICIENCY, 0.15),
        ObjectiveWeight(OptimizationObjective.COST, 0.05),
    ],
)

EFFICIENCY_FOCUSED_STRATEGY = OptimizationStrategy(
    name="efficiency_focused",
    description="Prioritizes speed and cost efficiency",
    objectives=[
        ObjectiveWeight(OptimizationObjective.EFFICIENCY, 0.4),
        ObjectiveWeight(OptimizationObjective.COST, 0.3),
        ObjectiveWeight(OptimizationObjective.PERFORMANCE, 0.2),
        ObjectiveWeight(OptimizationObjective.RELIABILITY, 0.1),
    ],
)

INNOVATION_FOCUSED_STRATEGY = OptimizationStrategy(
    name="innovation_focused",
    description="Prioritizes creativity and novel approaches",
    objectives=[
        ObjectiveWeight(OptimizationObjective.INNOVATION, 0.4),
        ObjectiveWeight(OptimizationObjective.PERFORMANCE, 0.3),
        ObjectiveWeight(OptimizationObjective.EFFICIENCY, 0.2),
        ObjectiveWeight(OptimizationObjective.RELIABILITY, 0.1),
    ],
)
