"""Event system for agent actions and observations.

Classes:
    ActionConfirmationStatus
    ActionSecurityRisk
    Action
"""

from dataclasses import dataclass
from enum import Enum
from typing import ClassVar

from forge.events.event import Event
from forge._canonical import canonicalize


class ActionConfirmationStatus(str, Enum):
    """Status of action confirmation in confirmation mode."""

    CONFIRMED = "confirmed"
    REJECTED = "rejected"
    AWAITING_CONFIRMATION = "awaiting_confirmation"


class ActionSecurityRisk(int, Enum):
    """Security risk level for actions (from security analyzer)."""

    UNKNOWN = -1
    LOW = 0
    MEDIUM = 1
    HIGH = 2


class _ActionCanonicalMeta(type):
    """Metaclass guarding against duplicate class definitions across reloads."""

    def __instancecheck__(cls, instance: object) -> bool:  # pragma: no cover - plumbing
        if super().__instancecheck__(instance):
            return True
        inst_type = type(instance)
        if getattr(inst_type, "__name__", None) != getattr(cls, "__name__", None):
            # If checking against base Action class, allow subclasses from other reloads
            if cls.__name__ == "Action":
                return any(b.__name__ == "Action" for b in inst_type.__mro__)
            return False
        cls_action = getattr(cls, "action", None)
        inst_action = getattr(instance, "action", None)
        return cls_action is not None and cls_action == inst_action


@dataclass
class Action(Event, metaclass=_ActionCanonicalMeta):
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
