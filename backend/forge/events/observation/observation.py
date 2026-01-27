"""Event system for agent actions and observations.

Classes:
    Observation
"""

from dataclasses import dataclass
from typing import ClassVar

from forge.events.event import Event
from forge._canonical import canonicalize


class _ObservationCanonicalMeta(type):
    """Metaclass guarding against duplicate class definitions across reloads."""

    def __instancecheck__(cls, instance: object) -> bool:  # pragma: no cover - plumbing
        if super().__instancecheck__(instance):
            return True
        inst_type = type(instance)
        if getattr(inst_type, "__name__", None) != getattr(cls, "__name__", None):
            # If checking against base Observation class, allow subclasses from other reloads
            if cls.__name__ == "Observation":
                return any(b.__name__ == "Observation" for b in inst_type.__mro__)
            return False
        cls_observation = getattr(cls, "observation", None)
        inst_observation = getattr(instance, "observation", None)
        return cls_observation is not None and cls_observation == inst_observation


@dataclass
class Observation(Event, metaclass=_ObservationCanonicalMeta):
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
