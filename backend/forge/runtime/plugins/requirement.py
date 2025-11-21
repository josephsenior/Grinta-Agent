"""Abstract plugin interfaces and requirement metadata for runtime extensions."""

from abc import abstractmethod
from dataclasses import dataclass

from forge.events.action import Action
from forge.events.observation import Observation


class Plugin:
    """Base class for a plugin.

    This will be initialized by the runtime client, which will run inside docker.
    """

    name: str

    @abstractmethod
    async def initialize(self, username: str) -> None:
        """Initialize the plugin."""

    @abstractmethod
    async def run(self, action: Action) -> Observation:
        """Run the plugin for a given action."""


@dataclass
class PluginRequirement:
    """Requirement for a plugin."""

    name: str
