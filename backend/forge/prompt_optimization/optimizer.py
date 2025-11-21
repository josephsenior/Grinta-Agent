"""Prompt Optimizer for Dynamic Prompt Optimization.

Implements A/B testing, variant selection, and automatic optimization
based on performance metrics.
"""

from __future__ import annotations

import random
from typing import Any, Optional

from .models import PromptCategory, PromptVariant, OptimizationConfig
from .registry import PromptRegistry
from .tracker import PerformanceTracker


class PromptOptimizer:
    """Main optimizer that handles A/B testing and variant selection."""

    def __init__(
        self,
        registry: PromptRegistry,
        tracker: PerformanceTracker,
        config: Optional[OptimizationConfig] = None,
    ):
        """Initialize the prompt optimizer.

        Args:
            registry: Prompt registry for managing variants
            tracker: Performance tracker for metrics
            config: Optimization configuration

        """
        self.registry = registry
        self.tracker = tracker
        self.config = config or OptimizationConfig()

        # Track optimization state
        self._optimization_state: dict[str, dict[str, Any]] = {}
        self._update_counter = 0

    def select_variant(
        self, prompt_id: str, category: PromptCategory
    ) -> Optional[PromptVariant]:
        """Select a variant for execution using A/B testing strategy.

        Args:
            prompt_id: ID of the prompt to select variant for
            category: Category of the prompt

        Returns:
            Selected prompt variant or None if no variants available

        """
        # Get all variants for this prompt
        variants = self.registry.get_variants_for_prompt(prompt_id)
        if not variants:
            return None

        # Get active and testing variants
        active_variant = self.registry.get_active_variant(prompt_id)
        testing_variants = self.registry.get_testing_variants(prompt_id)

        # If no active variant, set the best one as active
        if not active_variant:
            best_variant = self._get_best_variant(prompt_id)
            if best_variant:
                self.registry.set_active_variant(prompt_id, best_variant.id)
                active_variant = best_variant

        # If no testing variants, start testing the best available
        if not testing_variants and len(variants) > 1:
            self._start_testing_best_variant(prompt_id)
            testing_variants = self.registry.get_testing_variants(prompt_id)

        # A/B testing selection: 80% active, 20% testing
        if testing_variants and random.random() > self.config.ab_split_ratio:
            # Select from testing variants (weighted by performance)
            return self._select_testing_variant(testing_variants)
        else:
            # Use active variant
            return active_variant

    def _get_best_variant(self, prompt_id: str) -> Optional[PromptVariant]:
        """Get the best performing variant for a prompt."""
        best_result = self.tracker.get_best_variant(prompt_id)
        if best_result:
            variant_id, _ = best_result
            return self.registry.get_variant(variant_id)
        return None

    def _start_testing_best_variant(self, prompt_id: str):
        """Start testing the best available variant."""
        variants = self.registry.get_variants_for_prompt(prompt_id)
        if not variants:
            return

        # Find the best variant that's not currently active or testing
        active_variant = self.registry.get_active_variant(prompt_id)
        testing_variants = self.registry.get_testing_variants(prompt_id)

        available_variants = [
            v
            for v in variants
            if v.id != (active_variant.id if active_variant else None)
            and v.id not in [tv.id for tv in testing_variants]
        ]

        if available_variants:
            # Sort by performance and select the best
            available_variants.sort(key=self._variant_score_key, reverse=True)
            best_variant = available_variants[0]
            self.registry.add_testing_variant(prompt_id, best_variant.id)

    def _select_testing_variant(
        self, testing_variants: list[PromptVariant]
    ) -> Optional[PromptVariant]:
        """Select a variant from testing variants using weighted selection."""
        if not testing_variants:
            return None

        # Weight selection by composite score
        scores = [self._get_variant_score(variant) for variant in testing_variants]
        total_score = sum(scores)

        if total_score == 0:
            # If all scores are 0, select randomly
            return random.choice(testing_variants)

        # Weighted random selection
        weights = [score / total_score for score in scores]
        return random.choices(testing_variants, weights=weights)[0]

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
        """Record execution results and update optimization state."""
        # Record in tracker
        self.tracker.record_execution(
            variant_id=variant_id,
            prompt_id=prompt_id,
            category=category,
            success=success,
            execution_time=execution_time,
            token_cost=token_cost,
            error_message=error_message,
        metadata=metadata,
        )

        # Update registry metrics
        self.registry.update_variant_metrics(
            variant_id, success, execution_time, token_cost
        )

        # Check if we should switch variants
        self._check_variant_switch(prompt_id)

        # Increment update counter
        self._update_counter += 1

    def _check_variant_switch(self, prompt_id: str):
        """Check if we should switch the active variant based on performance."""
        active_variant = self.registry.get_active_variant(prompt_id)
        testing_variants = self.registry.get_testing_variants(prompt_id)

        if not active_variant or not testing_variants:
            return

        # Check each testing variant
        for testing_variant in testing_variants:
            if self._should_switch_to_variant(active_variant, testing_variant):
                self._switch_to_variant(prompt_id, testing_variant)
                break

    def _should_switch_to_variant(
        self, current_variant: PromptVariant, candidate_variant: PromptVariant
    ) -> bool:
        """Check if we should switch to a candidate variant."""
        # Need minimum samples for both variants
        if (
            current_variant.total_executions < self.config.min_samples_for_switch
            or candidate_variant.total_executions < self.config.min_samples_for_switch
        ):
            return False

        # Check if candidate is significantly better
        is_better = self.tracker.is_significantly_better(
            candidate_variant.id, current_variant.id, self.config.confidence_threshold
        )

        return is_better is True

    def _switch_to_variant(self, prompt_id: str, new_variant: PromptVariant):
        """Switch the active variant to a new one."""
        # Remove from testing
        self.registry.remove_testing_variant(prompt_id, new_variant.id)

        # Set as active
        self.registry.set_active_variant(prompt_id, new_variant.id)

        # Update optimization state
        if prompt_id not in self._optimization_state:
            self._optimization_state[prompt_id] = {}

        self._optimization_state[prompt_id].update(
            {
                "last_switch": new_variant.id,
                "switch_count": self._optimization_state[prompt_id].get(
                    "switch_count", 0
                )
                + 1,
            }
        )

    def _get_variant_score(self, variant: PromptVariant) -> float:
        """Return the composite score for the variant based on tracked metrics."""
        metrics = self.tracker.get_variant_metrics(variant.id)
        return metrics.composite_score if metrics else 0.0

    def _variant_score_key(self, variant: PromptVariant) -> float:
        """Key function for sorting variants by performance."""
        return self._get_variant_score(variant)

    def add_variant(
        self,
        prompt_id: str,
        content: str,
        category: PromptCategory,
        parent_id: Optional[str] = None,
        metadata: Optional[dict[str, Any]] = None,
    ) -> str:
        """Add a new variant to a prompt."""
        # Find the next version number
        existing_variants = self.registry.get_variants_for_prompt(prompt_id)
        next_version = max([v.version for v in existing_variants], default=0) + 1

        # Create new variant
        variant = PromptVariant(
            content=content,
            version=next_version,
            parent_id=parent_id,
            category=category,
            prompt_id=prompt_id,
            metadata=metadata or {},
        )

        # Register the variant
        variant_id = self.registry.register_variant(variant)

        # If this is the first variant, set it as active
        if len(existing_variants) == 0:
            self.registry.set_active_variant(prompt_id, variant_id)

        return variant_id

    def get_optimization_status(self, prompt_id: str) -> dict[str, Any]:
        """Get optimization status for a prompt."""
        active_variant = self.registry.get_active_variant(prompt_id)
        testing_variants = self.registry.get_testing_variants(prompt_id)
        all_variants = self.registry.get_variants_for_prompt(prompt_id)

        status = {
            "prompt_id": prompt_id,
            "total_variants": len(all_variants),
            "active_variant": active_variant.id if active_variant else None,
            "testing_variants": [v.id for v in testing_variants],
            "optimization_state": self._optimization_state.get(prompt_id, {}),
        }

        # Add performance metrics
        if active_variant:
            active_metrics = self.tracker.get_variant_metrics(active_variant.id)
            if active_metrics:
                status["active_metrics"] = active_metrics.to_dict()

        if testing_variants:
            testing_metrics = []
            for variant in testing_variants:
                metrics = self.tracker.get_variant_metrics(variant.id)
                if metrics:
                    testing_metrics.append(
                        {"variant_id": variant.id, "metrics": metrics.to_dict()}
                    )
            status["testing_metrics"] = testing_metrics

        return status

    def get_all_optimization_status(self) -> dict[str, dict[str, Any]]:
        """Get optimization status for all prompts."""
        prompt_ids = self.registry.get_prompt_ids()
        return {
            prompt_id: self.get_optimization_status(prompt_id)
            for prompt_id in prompt_ids
        }

    def force_switch_variant(self, prompt_id: str, variant_id: str) -> bool:
        """Force switch to a specific variant (for manual control)."""
        variant = self.registry.get_variant(variant_id)
        if not variant or variant.prompt_id != prompt_id:
            return False

        # Remove from testing if it was there
        self.registry.remove_testing_variant(prompt_id, variant_id)

        # Set as active
        return self.registry.set_active_variant(prompt_id, variant_id)

    def start_testing_variant(self, prompt_id: str, variant_id: str) -> bool:
        """Start testing a specific variant."""
        return self.registry.add_testing_variant(prompt_id, variant_id)

    def stop_testing_variant(self, prompt_id: str, variant_id: str) -> bool:
        """Stop testing a specific variant."""
        return self.registry.remove_testing_variant(prompt_id, variant_id)

    def get_performance_summary(self) -> dict[str, Any]:
        """Get overall performance summary."""
        overall_stats = self.tracker.get_overall_statistics()
        category_stats = self.tracker.get_category_statistics()
        registry_stats = self.registry.get_statistics()

        return {
            "overall_performance": overall_stats,
            "category_performance": category_stats,
            "registry_stats": registry_stats,
            "optimization_state": self._optimization_state,
            "update_count": self._update_counter,
        }

    def should_evolve_prompt(self, prompt_id: str) -> bool:
        """Check if a prompt should be evolved based on performance."""
        if not self.config.enable_evolution:
            return False

        active_variant = self.registry.get_active_variant(prompt_id)
        if not active_variant:
            return False

        # Check if performance is below threshold
        active_metrics = self.tracker.get_variant_metrics(active_variant.id)
        if not active_metrics:
            return False

        return active_metrics.composite_score < self.config.evolution_threshold

    def get_candidates_for_evolution(self, prompt_id: str) -> list[PromptVariant]:
        """Get variants that are candidates for evolution."""
        variants = self.registry.get_variants_for_prompt(prompt_id)

        # Filter variants below evolution threshold
        candidates = []
        for variant in variants:
            metrics = self.tracker.get_variant_metrics(variant.id)
            if metrics and metrics.composite_score < self.config.evolution_threshold:
                candidates.append(variant)

        # Sort by performance (worst first)
        candidates.sort(key=self._variant_score_key)

        return candidates

    def cleanup_old_variants(self, prompt_id: str, keep_count: Optional[int] = None):
        """Clean up old variants, keeping only the best ones."""
        if keep_count is None:
            keep_count = self.config.max_variants_per_prompt

        variants = self.registry.get_variants_for_prompt(prompt_id)
        if len(variants) <= keep_count:
            return

        # Sort by composite score (best first)
        variants.sort(key=self._variant_score_key, reverse=True)

        # Keep the best variants
        variants_to_keep = variants[:keep_count]
        variants_to_remove = variants[keep_count:]

        # Remove old variants
        for variant in variants_to_remove:
            self.registry.remove_variant(variant.id)

    def reset_optimization(self, prompt_id: str):
        """Reset optimization state for a prompt."""
        # Clear optimization state
        if prompt_id in self._optimization_state:
            del self._optimization_state[prompt_id]

        # Reset all variants to inactive
        variants = self.registry.get_variants_for_prompt(prompt_id)
        for variant in variants:
            variant.is_active = False
            variant.is_testing = False

        # Clear testing variants
        testing_variants = self.registry.get_testing_variants(prompt_id)
        for variant in testing_variants:
            self.registry.remove_testing_variant(prompt_id, variant.id)
