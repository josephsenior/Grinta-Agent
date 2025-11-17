"""Budget/bandwidth guard utilities for AgentController."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from forge.controller.services.controller_context import ControllerContext


class BudgetGuardService:
    """Keeps budget control flags in sync with accumulated metrics."""

    def __init__(self, context: "ControllerContext") -> None:
        self._context = context

    def sync_with_metrics(self) -> None:
        """Update budget control flag based on conversation stats."""
        state_tracker = self._context.state_tracker
        if state_tracker and hasattr(state_tracker, "sync_budget_flag_with_metrics"):
            state_tracker.sync_budget_flag_with_metrics()


