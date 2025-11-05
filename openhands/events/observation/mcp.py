from dataclasses import dataclass, field
from typing import Any

from openhands.core.schema import ObservationType
from openhands.events.observation.observation import Observation


@dataclass
class MCPObservation(Observation):
    """This data class represents the result of a MCP Server operation."""

    observation: str = ObservationType.MCP
    name: str = ""
    arguments: dict[str, Any] = field(default_factory=dict)

    @property
    def message(self) -> str:
        return self.content

    __test__ = False
