"""Placeholder action used when no operation is required."""

from dataclasses import dataclass

from forge.core.schema import ActionType
from forge.events.action.action import Action


@dataclass
class NullAction(Action):
    """An action that does nothing."""

    action: str = ActionType.NULL

    @property
    def message(self) -> str:
        """Get null action message."""
        return "No action"

    __test__ = False
