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

from openhands.events.tool import ToolCallMetadata
from openhands.llm.metrics import Metrics


class EventSource(str, Enum):
    AGENT = "agent"
    USER = "user"
    ENVIRONMENT = "environment"
    __test__ = False


class FileEditSource(str, Enum):
    LLM_BASED_EDIT = "llm_based_edit"
    OH_ACI = "oh_aci"
    __test__ = False


class FileReadSource(str, Enum):
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
    INVALID_ID = -1

    @property
    def message(self) -> str | None:
        if hasattr(self, "_message"):
            msg = self._message
            return str(msg) if msg is not None else None
        return ""

    @property
    def id(self) -> int:
        if hasattr(self, "_id"):
            id_val = self._id
            return int(id_val) if id_val is not None else Event.INVALID_ID
        return Event.INVALID_ID

    @property
    def sequence(self) -> int:
        """Sequence number for guaranteed event ordering.
        
        Events are assigned sequence numbers when added to the event stream.
        This ensures correct ordering even if network delays cause out-of-order delivery.
        """
        if hasattr(self, "_sequence"):
            seq_val = self._sequence
            return int(seq_val) if seq_val is not None else Event.INVALID_ID
        return Event.INVALID_ID

    @property
    def timestamp(self) -> str | None:
        if hasattr(self, "_timestamp") and isinstance(self._timestamp, str):
            ts = self._timestamp
            return str(ts) if ts is not None else None
        return None

    @timestamp.setter
    def timestamp(self, value: datetime) -> None:
        if isinstance(value, datetime):
            self._timestamp = value.isoformat()

    @property
    def source(self) -> EventSource | None:
        if hasattr(self, "_source"):
            src = self._source
            return EventSource(src) if src is not None else None
        return None

    @property
    def cause(self) -> int | None:
        if hasattr(self, "_cause"):
            cause_val = self._cause
            return int(cause_val) if cause_val is not None else None
        return None

    @property
    def timeout(self) -> float | None:
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
        if hasattr(self, "_llm_metrics"):
            metrics = self._llm_metrics
            return metrics if isinstance(metrics, Metrics) else None
        return None

    @llm_metrics.setter
    def llm_metrics(self, value: Metrics) -> None:
        self._llm_metrics = value

    @property
    def tool_call_metadata(self) -> ToolCallMetadata | None:
        if hasattr(self, "_tool_call_metadata"):
            metadata = self._tool_call_metadata
            return metadata if isinstance(metadata, ToolCallMetadata) else None
        return None

    @tool_call_metadata.setter
    def tool_call_metadata(self, value: ToolCallMetadata) -> None:
        self._tool_call_metadata = value

    @property
    def response_id(self) -> str | None:
        return self._response_id if hasattr(self, "_response_id") else None

    @response_id.setter
    def response_id(self, value: str) -> None:
        self._response_id = value
