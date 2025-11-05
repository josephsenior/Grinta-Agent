"""Server-related observations for automatic app rendering."""

from dataclasses import dataclass

from openhands.core.schema import ObservationType
from openhands.events.observation.observation import Observation


@dataclass
class ServerReadyObservation(Observation):
    """Observation sent when a server is detected and ready.

    This observation is emitted when:
    1. A server start command is detected in terminal output
    2. The port is verified to be listening
    3. (Optional) HTTP health check passes

    The frontend uses this to automatically navigate the browser tab.
    """

    port: int
    url: str
    protocol: str = "http"
    health_status: str = "unknown"
    observation: str = ObservationType.SERVER_READY

    @property
    def message(self) -> str:
        """Human-readable message about the server."""
        status_emoji = "✅" if self.health_status == "healthy" else "🔄"
        return f"{status_emoji} Server detected and ready at {self.url}"
