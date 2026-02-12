"""Event system for agent actions and observations.

Classes:
    ActionConfirmationStatus
    ActionSecurityRisk
    Action
"""

from dataclasses import dataclass
from enum import Enum
from typing import ClassVar

from backend.core.schemas import ActionConfirmationStatus, ActionSecurityRisk
from backend.events.event import Event
from backend._canonical import CanonicalMeta


@dataclass
class Action(Event, metaclass=CanonicalMeta):
    """Base class for all agent actions.

    Actions represent things the agent wants to do (edit files, run commands, etc.).
    They are executed by the runtime and produce Observations.
    """

    action: ClassVar[str] = ""
    runnable: ClassVar[bool] = False
    __test__: ClassVar[bool] = False

    def __post_init__(self) -> None:
        if not hasattr(self, "confirmation_state"):
            self.confirmation_state = ActionConfirmationStatus.CONFIRMED
