"""Event system for agent actions and observations.

Classes:
    EventSource
    FileEditSource
    FileReadSource
    RecallType
    Event

Functions:
    message
    id
    timestamp
    timestamp
    source
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import Enum

from forge.events.tool import ToolCallMetadata
from forge.llm.metrics import Metrics


class EventSource(str, Enum):
    """Canonical originator categories for events."""
    AGENT = "agent"
    USER = "user"
    ENVIRONMENT = "environment"
    __test__ = False


class FileEditSource(str, Enum):
    """Enumerates subsystems that can perform file edit operations."""
    LLM_BASED_EDIT = "llm_based_edit"
    OH_ACI = "oh_aci"
    __test__ = False


class FileReadSource(str, Enum):
    """Enumerates subsystems that can read files during execution."""
    OH_ACI = "oh_aci"
    DEFAULT = "default"
    __test__ = False


class RecallType(str, Enum):
    """The type of information that can be retrieved from microagents."""

    WORKSPACE_CONTEXT = "workspace_context"
    "Workspace context (repo instructions, runtime, etc.)"
    KNOWLEDGE = "knowledge"
    "A knowledge microagent."
    __test__ = False


@dataclass
class Event:
    """Base dataclass for stream events emitted by the runtime."""
    INVALID_ID = -1

    @property
    def message(self) -> str | None:
        """Get human-readable message for this event."""
        if hasattr(self, "_message"):
            msg = self._message
            return str(msg) if msg is not None else None
        return ""

    @property
    def id(self) -> int:
        """Get event ID (assigned when added to event stream)."""
        if hasattr(self, "_id"):
            id_val = self._id
            return int(id_val) if id_val is not None else Event.INVALID_ID
        return Event.INVALID_ID

    @property
    def sequence(self) -> int:
        """Sequence number for guaranteed event ordering."""
        if hasattr(self, "_sequence"):
            seq_val = self._sequence
            return int(seq_val) if seq_val is not None else Event.INVALID_ID
        return Event.INVALID_ID

    @property
    def timestamp(self) -> str | None:
        """Get event timestamp in ISO format."""
        if hasattr(self, "_timestamp") and isinstance(self._timestamp, str):
            ts = self._timestamp
            return str(ts) if ts is not None else None
        return None

    @timestamp.setter
    def timestamp(self, value: datetime) -> None:
        """Set event timestamp from datetime object."""
        if isinstance(value, datetime):
            self._timestamp = value.isoformat()

    @property
    def source(self) -> EventSource | None:
        """Get event source (USER, AGENT, ENVIRONMENT, etc.)."""
        if hasattr(self, "_source"):
            src = self._source
            return EventSource(src) if src is not None else None
        return None

    @property
    def cause(self) -> int | None:
        """Get ID of event that caused this event."""
        if hasattr(self, "_cause"):
            cause_val = self._cause
            return int(cause_val) if cause_val is not None else None
        return None

    @property
    def timeout(self) -> float | None:
        """Get timeout value in seconds."""
        if hasattr(self, "_timeout"):
            timeout_val = self._timeout
            return float(timeout_val) if timeout_val is not None else None
        return None

    def set_hard_timeout(self, value: float | None, blocking: bool = True) -> None:
        """Set the timeout for the event.

        NOTE, this is a hard timeout, meaning that the event will be blocked
        until the timeout is reached.
        """
        self._timeout = value
        if hasattr(self, "blocking"):
            self.blocking = blocking

    @property
    def llm_metrics(self) -> Metrics | None:
        """Get LLM metrics attached to this event."""
        if hasattr(self, "_llm_metrics"):
            metrics = self._llm_metrics
            return metrics if isinstance(metrics, Metrics) else None
        return None

    @llm_metrics.setter
    def llm_metrics(self, value: Metrics) -> None:
        """Set LLM metrics for this event."""
        self._llm_metrics = value

    @property
    def tool_call_metadata(self) -> ToolCallMetadata | None:
        """Get tool call metadata if this event involved tool calls."""
        if hasattr(self, "_tool_call_metadata"):
            metadata = self._tool_call_metadata
            return metadata if isinstance(metadata, ToolCallMetadata) else None
        return None

    @tool_call_metadata.setter
    def tool_call_metadata(self, value: ToolCallMetadata) -> None:
        """Set tool call metadata."""
        self._tool_call_metadata = value

    @property
    def response_id(self) -> str | None:
        """Get LLM response ID for this event."""
        return self._response_id if hasattr(self, "_response_id") else None

    @response_id.setter
    def response_id(self, value: str) -> None:
        """Set LLM response ID."""
        self._response_id = value
