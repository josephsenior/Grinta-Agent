"""Abstract plugin interfaces and requirement metadata for runtime extensions."""

from abc import abstractmethod
from dataclasses import dataclass

from backend.events.action import Action
from backend.events.observation import Observation


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

    async def shutdown(self) -> None:
        """Shutdown the plugin, releasing any held resources.

        Override in subclasses that allocate resources during
        ``initialize()`` or ``run()``.  The default is a no-op.
        """


@dataclass
class PluginRequirement:
    """Requirement for a plugin."""

    name: str
