"""Observation emitted when files finish downloading."""

from dataclasses import dataclass

from forge.core.schema import ObservationType
from forge.events.observation.observation import Observation


@dataclass
class FileDownloadObservation(Observation):
    """Observation for file download completion.
    
    Attributes:
        file_path: Path where the file was downloaded

    """
    file_path: str
    observation: str = ObservationType.DOWNLOAD

    @property
    def message(self) -> str:
        """Get file download completion message."""
        return f"Downloaded the file at location: {self.file_path}"

    def __str__(self) -> str:
        """Return a readable summary highlighting the download location."""
        return f"**FileDownloadObservation**\nLocation of downloaded file: {self.file_path}\n"

    __test__ = False
