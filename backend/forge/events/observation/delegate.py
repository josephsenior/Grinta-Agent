"""Observation capturing results returned by delegated agents."""

from dataclasses import dataclass

from forge.core.schemas import ObservationType
from forge.events.observation.observation import Observation
from forge.events.tool import ToolCallMetadata


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
    tool_call_metadata: ToolCallMetadata | None = None

    @property
    def message(self) -> str:
        """Get message (empty for delegate observations)."""
        return ""

    __test__ = False
