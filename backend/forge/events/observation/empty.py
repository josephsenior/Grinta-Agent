"""Placeholder observation used when no data is produced."""

from dataclasses import dataclass

from forge.core.schemas import ObservationType
from forge.events.observation.observation import Observation


@dataclass
class NullObservation(Observation):
    """This data class represents a null observation.

    This is used when the produced action is NOT executable.
    """

    observation: str = ObservationType.NULL

    @property
    def message(self) -> str:
        """Get null observation message."""
        return "No observation"

    __test__ = False
