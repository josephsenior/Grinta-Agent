"""Formal Pydantic schemas for Forge events, actions, and observations.

This module provides versioned, type-safe schemas for all event types,
enabling explicit contracts, versioning, testing, and multi-agent expansion.
"""

from forge.core.schemas.base import (
    BaseEventSchema,
    EventMetadata,
    EventSchemaV1,
    EventVersion,
)
from forge.core.schemas.enums import ActionType, AgentState, ObservationType
from forge.core.schemas.actions import (
    ActionSchemaV1,
    FileEditActionSchema,
    FileReadActionSchema,
    FileWriteActionSchema,
    CmdRunActionSchema,
    MessageActionSchema,
    SystemMessageActionSchema,
    BrowseInteractiveActionSchema,
    AgentFinishActionSchema,
    AgentRejectActionSchema,
    ChangeAgentStateActionSchema,
    NullActionSchema,
    ActionSchemaUnion,
)
from forge.core.schemas.observations import (
    ObservationSchemaV1,
    CmdOutputObservationSchema,
    FileReadObservationSchema,
    FileEditObservationSchema,
    ErrorObservationSchema,
    MessageObservationSchema,
    ObservationSchemaUnion,
)
from forge.core.schemas.serialization import (
    serialize_event,
    deserialize_event,
    migrate_schema_version,
    validate_event_schema,
)

__all__ = [
    # Base schemas
    "BaseEventSchema",
    "EventMetadata",
    "EventSchemaV1",
    "EventVersion",
    # Action schemas
    "ActionSchemaV1",
    "ActionType",
    "FileEditActionSchema",
    "FileReadActionSchema",
    "FileWriteActionSchema",
    "CmdRunActionSchema",
    "MessageActionSchema",
    "SystemMessageActionSchema",
    "BrowseInteractiveActionSchema",
    "AgentFinishActionSchema",
    "AgentRejectActionSchema",
    "ChangeAgentStateActionSchema",
    "NullActionSchema",
    "ActionSchemaUnion",
    # Observation schemas
    "ObservationSchemaV1",
    "CmdOutputObservationSchema",
    "ObservationType",
    "FileReadObservationSchema",
    "FileEditObservationSchema",
    "ErrorObservationSchema",
    "MessageObservationSchema",
    "ObservationSchemaUnion",
    # Serialization
    "serialize_event",
    "deserialize_event",
    "migrate_schema_version",
    "validate_event_schema",
    # Agent lifecycle
    "AgentState",
]
