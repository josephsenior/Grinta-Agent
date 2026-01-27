"""Pydantic schemas for all Forge observation types."""

from __future__ import annotations

from typing import Literal, Optional, Union

from pydantic import Field, field_validator

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

    observation_type: str = Field(
        ...,
        min_length=1,
        description="Type of observation"
    )
    content: str = Field(
        ...,
        description="Observation content"
    )

    @field_validator("observation_type")
    @classmethod
    def validate_observation_type(cls, v: str) -> str:
        """Validate observation type is non-empty."""
        from forge.core.security.type_safety import validate_non_empty_string
        return validate_non_empty_string(v, name="observation_type")


class CmdOutputObservationSchema(ObservationSchemaV1):
    """Schema for CmdOutputObservation."""

    observation_type: Literal["run"] = Field(ObservationType.RUN.value, frozen=True)
    command: str = Field(
        ...,
        min_length=1,
        description="Command that was executed"
    )
    content: str = Field(
        ...,
        description="Command output"
    )
    cmd_metadata: Optional[dict] = Field(
        default=None,
        description="Command metadata (CmdOutputMetadata as dict)"
    )
    hidden: bool = Field(
        default=False,
        description="Whether observation is hidden"
    )

    @field_validator("command")
    @classmethod
    def validate_command(cls, v: str) -> str:
        """Validate command is non-empty."""
        from forge.core.security.type_safety import validate_non_empty_string
        return validate_non_empty_string(v, name="command")


class FileReadObservationSchema(ObservationSchemaV1):
    """Schema for FileReadObservation."""

    observation_type: Literal["read"] = Field(ObservationType.READ.value, frozen=True)
    path: str = Field(
        ...,
        min_length=1,
        description="Path to file that was read"
    )
    content: str = Field(
        ...,
        description="File content"
    )

    @field_validator("path")
    @classmethod
    def validate_path(cls, v: str) -> str:
        """Validate path is non-empty."""
        from forge.core.security.type_safety import validate_non_empty_string
        return validate_non_empty_string(v, name="path")


class FileEditObservationSchema(ObservationSchemaV1):
    """Schema for FileEditObservation."""

    observation_type: Literal["edit"] = Field(ObservationType.EDIT.value, frozen=True)
    path: str = Field(
        ...,
        min_length=1,
        description="Path to file that was edited"
    )
    content: str = Field(
        ...,
        description="Edit result content"
    )

    @field_validator("path")
    @classmethod
    def validate_path(cls, v: str) -> str:
        """Validate path is non-empty."""
        from forge.core.security.type_safety import validate_non_empty_string
        return validate_non_empty_string(v, name="path")


class ErrorObservationSchema(ObservationSchemaV1):
    """Schema for ErrorObservation."""

    observation_type: Literal["error"] = Field(ObservationType.ERROR.value, frozen=True)
    content: str = Field(
        ...,
        min_length=1,
        description="Error message"
    )
    error_id: Optional[str] = Field(
        default=None,
        description="Error identifier"
    )

    @field_validator("content")
    @classmethod
    def validate_content(cls, v: str) -> str:
        """Validate content is non-empty."""
        from forge.core.security.type_safety import validate_non_empty_string
        return validate_non_empty_string(v, name="content")


class MessageObservationSchema(ObservationSchemaV1):
    """Schema for MessageObservation."""

    observation_type: Literal["message"] = Field(
        ObservationType.MESSAGE.value, frozen=True
    )
    content: str = Field(
        ...,
        min_length=1,
        description="Message content"
    )

    @field_validator("content")
    @classmethod
    def validate_content(cls, v: str) -> str:
        """Validate content is non-empty."""
        from forge.core.security.type_safety import validate_non_empty_string
        return validate_non_empty_string(v, name="content")


# Union type for all observation schemas
ObservationSchemaUnion = Union[
    CmdOutputObservationSchema,
    FileReadObservationSchema,
    FileEditObservationSchema,
    ErrorObservationSchema,
    MessageObservationSchema,
]
