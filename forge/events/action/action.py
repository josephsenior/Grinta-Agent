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


@dataclass
class Action(Event):
    """Base class for all agent actions.
    
    Actions represent things the agent wants to do (edit files, run commands, etc.).
    They are executed by the runtime and produce Observations.
    """
    runnable: ClassVar[bool] = False
    __test__ = False
