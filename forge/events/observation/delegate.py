"""Observation capturing results returned by delegated agents."""

from dataclasses import dataclass

from forge.core.schema import ObservationType
from forge.events.observation.observation import Observation


@dataclass
class AgentDelegateObservation(Observation):
    """This data class represents the result from delegating to another agent.

    Attributes:
        content (str): The content of the observation.
        outputs (dict): The outputs of the delegated agent.
        observation (str): The type of observation.

    """

    outputs: dict
    observation: str = ObservationType.DELEGATE

    @property
    def message(self) -> str:
        """Get message (empty for delegate observations)."""
        return ""

    __test__ = False
