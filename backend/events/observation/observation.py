"""Event system for agent actions and observations.

Classes:
    Observation
"""

from dataclasses import dataclass
from typing import ClassVar

from backend.events.event import Event
from backend._canonical import CanonicalMeta


@dataclass
class Observation(Event, metaclass=CanonicalMeta):
    """Base class for observations from the environment.

    Attributes:
        content: The content of the observation. For large observations,
                this might be truncated when stored.

    """

    content: str
    observation: ClassVar[str] = ""
    __test__: ClassVar[bool] = False

    @property
    def exit_code(self) -> int | None:
        """Return generic exit code when available."""
        if hasattr(self, "_exit_code"):
            exit_val = self._exit_code
            return int(exit_val) if exit_val is not None else None
        return None

    @exit_code.setter
    def exit_code(self, value: int | None) -> None:
        """Set generic exit code metadata."""
        self._exit_code = value
