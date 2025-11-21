"""Prompt Registry for managing prompt variants and tracking.

Central registry that manages all prompt variants, handles A/B testing,
and provides thread-safe access to prompt variants.
"""

from __future__ import annotations

import threading
from collections import defaultdict
from typing import Any, Optional
from uuid import uuid4

from .models import PromptCategory, PromptMetrics, PromptVariant


class PromptRegistry:
    """Central registry for managing prompt variants and A/B testing."""

    def __init__(self):
        """Initialize the prompt registry."""
        self._variants: dict[str, PromptVariant] = {}  # variant_id -> PromptVariant
        self._prompt_variants: dict[str, list[str]] = defaultdict(
            list
        )  # prompt_id -> [variant_ids]
        self._active_variants: dict[str, str] = {}  # prompt_id -> active_variant_id
        self._testing_variants: dict[str, list[str]] = defaultdict(
            list
        )  # prompt_id -> [testing_variant_ids]
        self._lock = threading.RLock()

    def register_variant(self, variant: PromptVariant) -> str:
        """Register a new prompt variant."""
        with self._lock:
            # Ensure unique ID
            if variant.id in self._variants:
                variant.id = str(uuid4())

            # Store variant
            self._variants[variant.id] = variant

            # Add to prompt variants list
            if variant.id not in self._prompt_variants[variant.prompt_id]:
                self._prompt_variants[variant.prompt_id].append(variant.id)

            # Set as active if it's the first variant for this prompt
            if variant.prompt_id not in self._active_variants:
                self._active_variants[variant.prompt_id] = variant.id
                variant.is_active = True

            return variant.id

    def get_variant(self, variant_id: str) -> Optional[PromptVariant]:
        """Get a specific variant by ID."""
        with self._lock:
            return self._variants.get(variant_id)

    def get_active_variant(self, prompt_id: str) -> Optional[PromptVariant]:
        """Get the currently active variant for a prompt."""
        with self._lock:
            active_id = self._active_variants.get(prompt_id)
            if active_id:
                return self._variants.get(active_id)
            return None

    def get_variants_for_prompt(self, prompt_id: str) -> list[PromptVariant]:
        """Get all variants for a specific prompt."""
        with self._lock:
            variant_ids = self._prompt_variants.get(prompt_id, [])
            return [self._variants[vid] for vid in variant_ids if vid in self._variants]

    def get_testing_variants(self, prompt_id: str) -> list[PromptVariant]:
        """Get all testing variants for a specific prompt."""
        with self._lock:
            testing_ids = self._testing_variants.get(prompt_id, [])
            return [self._variants[vid] for vid in testing_ids if vid in self._variants]

    def set_active_variant(self, prompt_id: str, variant_id: str) -> bool:
        """Set the active variant for a prompt."""
        with self._lock:
            if variant_id not in self._variants:
                return False

            variant = self._variants[variant_id]
            if variant.prompt_id != prompt_id:
                return False

            # Deactivate current active variant
            current_active = self._active_variants.get(prompt_id)
            if current_active and current_active in self._variants:
                self._variants[current_active].is_active = False

            # Activate new variant
            self._active_variants[prompt_id] = variant_id
            variant.is_active = True

            return True

    def add_testing_variant(self, prompt_id: str, variant_id: str) -> bool:
        """Add a variant to testing for A/B testing."""
        with self._lock:
            if variant_id not in self._variants:
                return False

            variant = self._variants[variant_id]
            if variant.prompt_id != prompt_id:
                return False

            # Add to testing variants
            if variant_id not in self._testing_variants[prompt_id]:
                self._testing_variants[prompt_id].append(variant_id)
                variant.is_testing = True

            return True

    def remove_testing_variant(self, prompt_id: str, variant_id: str) -> bool:
        """Remove a variant from testing."""
        with self._lock:
            if variant_id in self._testing_variants[prompt_id]:
                self._testing_variants[prompt_id].remove(variant_id)
                if variant_id in self._variants:
                    self._variants[variant_id].is_testing = False
                return True
            return False

    def get_best_variant(self, prompt_id: str) -> Optional[PromptVariant]:
        """Get the best performing variant for a prompt."""
        with self._lock:
            variants = self.get_variants_for_prompt(prompt_id)
            if not variants:
                return None

            def variant_score(variant: PromptVariant) -> float:
                metrics = PromptMetrics()
                metrics.update_from_variant(variant)
                return metrics.composite_score

            variants.sort(key=variant_score, reverse=True)
            return variants[0]

    def get_variants_by_category(self, category: PromptCategory) -> list[PromptVariant]:
        """Get all variants for a specific category."""
        with self._lock:
            return [v for v in self._variants.values() if v.category == category]

    def update_variant_metrics(
        self,
        variant_id: str,
        success: bool,
        execution_time: float,
        token_cost: float = 0.0,
    ):
        """Update metrics for a variant after execution."""
        with self._lock:
            variant = self._variants.get(variant_id)
            if variant:
                variant.update_metrics(success, execution_time, token_cost)

    def get_prompt_ids(self) -> list[str]:
        """Get all registered prompt IDs."""
        with self._lock:
            return list(self._prompt_variants.keys())

    def get_variant_count(self, prompt_id: str) -> int:
        """Get the number of variants for a prompt."""
        with self._lock:
            return len(self._prompt_variants.get(prompt_id, []))

    def remove_variant(self, variant_id: str) -> bool:
        """Remove a variant from the registry."""
        with self._lock:
            if variant_id not in self._variants:
                return False

            variant = self._variants[variant_id]
            prompt_id = variant.prompt_id

            # Remove from prompt variants list
            if variant_id in self._prompt_variants[prompt_id]:
                self._prompt_variants[prompt_id].remove(variant_id)

            # Remove from testing variants
            if variant_id in self._testing_variants[prompt_id]:
                self._testing_variants[prompt_id].remove(variant_id)

            # If it was active, set a new active variant
            if self._active_variants.get(prompt_id) == variant_id:
                remaining_variants = self._prompt_variants[prompt_id]
                if remaining_variants:
                    self._active_variants[prompt_id] = remaining_variants[0]
                    self._variants[remaining_variants[0]].is_active = True
                else:
                    del self._active_variants[prompt_id]

            # Remove the variant
            del self._variants[variant_id]

            return True

    def get_statistics(self) -> dict[str, Any]:
        """Get registry statistics."""
        with self._lock:
            total_variants = len(self._variants)
            total_prompts = len(self._prompt_variants)

            # Count by category
            category_counts: dict[str, int] = {}
            for variant in self._variants.values():
                category = variant.category.value
                category_counts[category] = category_counts.get(category, 0) + 1

            # Count active and testing variants
            active_count = len(self._active_variants)
            testing_count = sum(
                len(variants) for variants in self._testing_variants.values()
            )

            return {
                "total_variants": total_variants,
                "total_prompts": total_prompts,
                "active_variants": active_count,
                "testing_variants": testing_count,
                "category_counts": dict(category_counts),
            }

    def export_data(self) -> dict[str, Any]:
        """Export all registry data for persistence."""
        with self._lock:
            return {
                "variants": {
                    vid: variant.to_dict() for vid, variant in self._variants.items()
                },
                "prompt_variants": {pid: list(vids) for pid, vids in self._prompt_variants.items()},
                "active_variants": dict(self._active_variants),
                "testing_variants": {
                    pid: list(vids) for pid, vids in self._testing_variants.items()
                },
            }

    def import_data(self, data: dict[str, Any]):
        """Import registry data from persistence."""
        with self._lock:
            # Clear existing data
            self._variants.clear()
            self._prompt_variants.clear()
            self._active_variants.clear()
            self._testing_variants.clear()

            # Import variants
            variants_data = data.get("variants", {})
            if isinstance(variants_data, dict):
                for vid, variant_data in variants_data.items():
                    variant = PromptVariant.from_dict(variant_data)
                    self._variants[vid] = variant

            # Import prompt variants mapping
            prompt_variants = data.get("prompt_variants", {})
            if isinstance(prompt_variants, dict):
                for pid, vids in prompt_variants.items():
                    self._prompt_variants[pid] = list(vids)

            # Import active variants
            active_variants = data.get("active_variants", {})
            if isinstance(active_variants, dict):
                for pid, vid in active_variants.items():
                    self._active_variants[pid] = vid

            # Import testing variants
            testing_variants = data.get("testing_variants", {})
            if isinstance(testing_variants, dict):
                for pid, vids in testing_variants.items():
                    self._testing_variants[pid] = list(vids)

    def clear(self):
        """Clear all registry data."""
        with self._lock:
            self._variants.clear()
            self._prompt_variants.clear()
            self._active_variants.clear()
            self._testing_variants.clear()
