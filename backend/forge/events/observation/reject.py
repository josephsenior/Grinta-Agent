"""Observation emitted when the user rejects an agent action."""

from dataclasses import dataclass

from forge.core.schemas import ObservationType
from forge.events.observation.observation import Observation


@dataclass
class UserRejectObservation(Observation):
    """This data class represents the result of a rejected action."""

    observation: str = ObservationType.USER_REJECTED

    @property
    def message(self) -> str:
        """Get rejection reason message."""
        return self.content

    __test__ = False
