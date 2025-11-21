from __future__ import annotations

from typing import TYPE_CHECKING

from forge.controller.stuck import StuckDetector

if TYPE_CHECKING:
    from forge.controller.agent_controller import AgentController
    from forge.controller.state.state import State


class StuckDetectionService:
    """Provides stuck detection utilities for the agent controller."""

    def __init__(self, controller: "AgentController") -> None:
        self._controller = controller
        self._detector: StuckDetector | None = None

    def initialize(self, state: "State") -> None:
        """Initialize detector for the given state."""

        self._detector = StuckDetector(state)

    def is_stuck(self) -> bool:
        """Return True if the controller (or any delegate) appears stuck."""

        delegate = getattr(self._controller, "delegate", None)
        if delegate and hasattr(delegate, "stuck_service"):
            if delegate.stuck_service.is_stuck():
                return True

        if not self._detector:
            return False
        return bool(self._detector.is_stuck(self._controller.headless_mode))


