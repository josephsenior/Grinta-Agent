"""Observation representing successful completion of an action."""

from dataclasses import dataclass

from forge.core.schemas import ObservationType
from forge.events.observation.observation import Observation


@dataclass
class SuccessObservation(Observation):
    """This data class represents the result of a successful action."""

    observation: str = ObservationType.SUCCESS

    @property
    def message(self) -> str:
        """Get success message content."""
        return self.content

    __test__ = False
