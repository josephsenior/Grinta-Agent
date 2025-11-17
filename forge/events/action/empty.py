"""Placeholder action used when no operation is required."""

from dataclasses import dataclass
from typing import ClassVar

from forge.core.schemas import ActionType
from forge.events.action.action import Action
from forge.events.action._canonical import canonicalize


@dataclass
class NullAction(Action):
    """An action that does nothing."""

    action: ClassVar[str] = ActionType.NULL

    @property
    def message(self) -> str:
        """Get null action message."""
        return "No action"

    __test__ = False


canonicalize("NullAction", NullAction)
