"""Pydantic schemas for all Forge observation types."""

from __future__ import annotations

from typing import Literal, Optional, Union

from pydantic import Field

from forge.core.schemas.base import EventSchemaV1
from forge.core.schemas.enums import ObservationType

# Reuse CmdOutputMetadata from the observation module to avoid duplication
try:
    from forge.events.observation.commands import CmdOutputMetadata
except ImportError:
    # Fallback if not available
    from pydantic import BaseModel

    class CmdOutputMetadata(BaseModel):  # type: ignore
        """Metadata for command output observations."""

        exit_code: int = Field(-1, description="Command exit code")
        pid: int = Field(-1, description="Process ID")
        username: Optional[str] = Field(None, description="Username")
        hostname: Optional[str] = Field(None, description="Hostname")
        working_dir: Optional[str] = Field(None, description="Working directory")
        py_interpreter_path: Optional[str] = Field(None, description="Python interpreter path")
        prefix: str = Field("", description="Output prefix")
        suffix: str = Field("", description="Output suffix")


class ObservationSchemaV1(EventSchemaV1):
    """Base schema for all observation types."""

    observation_type: str = Field(..., description="Type of observation")
    content: str = Field(..., description="Observation content")


class CmdOutputObservationSchema(ObservationSchemaV1):
    """Schema for CmdOutputObservation."""

    observation_type: Literal[ObservationType.RUN] = Field(ObservationType.RUN, frozen=True)
    command: str = Field(..., description="Command that was executed")
    content: str = Field(..., description="Command output")
    cmd_metadata: Optional[dict] = Field(
        None, description="Command metadata (CmdOutputMetadata as dict)"
    )
    hidden: bool = Field(False, description="Whether observation is hidden")


class IPythonRunCellObservationSchema(ObservationSchemaV1):
    """Schema for IPythonRunCellObservation."""

    observation_type: Literal[ObservationType.RUN_IPYTHON] = Field(
        ObservationType.RUN_IPYTHON, frozen=True
    )
    code: str = Field(..., description="Python code that was executed")
    content: str = Field(..., description="IPython output")
    image_urls: Optional[list[str]] = Field(None, description="URLs of generated images")


class FileReadObservationSchema(ObservationSchemaV1):
    """Schema for FileReadObservation."""

    observation_type: Literal[ObservationType.READ] = Field(ObservationType.READ, frozen=True)
    path: str = Field(..., description="Path to file that was read")
    content: str = Field(..., description="File content")


class FileEditObservationSchema(ObservationSchemaV1):
    """Schema for FileEditObservation."""

    observation_type: Literal[ObservationType.EDIT] = Field(ObservationType.EDIT, frozen=True)
    path: str = Field(..., description="Path to file that was edited")
    content: str = Field(..., description="Edit result content")


class ErrorObservationSchema(ObservationSchemaV1):
    """Schema for ErrorObservation."""

    observation_type: Literal[ObservationType.ERROR] = Field(ObservationType.ERROR, frozen=True)
    content: str = Field(..., description="Error message")
    error_id: Optional[str] = Field(None, description="Error identifier")


class MessageObservationSchema(ObservationSchemaV1):
    """Schema for MessageObservation."""

    observation_type: Literal[ObservationType.MESSAGE] = Field(
        ObservationType.MESSAGE, frozen=True
    )
    content: str = Field(..., description="Message content")


# Union type for all observation schemas
ObservationSchemaUnion = Union[
    CmdOutputObservationSchema,
    IPythonRunCellObservationSchema,
    FileReadObservationSchema,
    FileEditObservationSchema,
    ErrorObservationSchema,
    MessageObservationSchema,
]
