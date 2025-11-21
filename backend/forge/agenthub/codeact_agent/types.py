from __future__ import annotations

from typing import TYPE_CHECKING, TypedDict

if TYPE_CHECKING:
    from forge.prompt_optimization.models import OptimizationConfig
    from forge.prompt_optimization.optimizer import PromptOptimizer
    from forge.prompt_optimization.registry import PromptRegistry
    from forge.prompt_optimization.storage import PromptStorage
    from forge.prompt_optimization.tool_optimizer import ToolOptimizer
    from forge.prompt_optimization.tracker import PerformanceTracker


class PromptOptimizerBundle(TypedDict):
    """Typed bundle of prompt optimization components."""

    registry: "PromptRegistry"
    tracker: "PerformanceTracker"
    optimizer: "PromptOptimizer"
    storage: "PromptStorage"
    config: "OptimizationConfig"

