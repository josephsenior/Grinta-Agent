"""Central location for Forge action/agent/observation enums.

These enums were historically defined in ``forge.core.schema``; they now live here
alongside the Pydantic schema models so there is a single source of truth.
"""

from __future__ import annotations

from enum import Enum


class ActionType(str, Enum):
    """Enum defining all possible agent action types."""

    MESSAGE = "message"
    SYSTEM = "system"
    START = "start"
    READ = "read"
    WRITE = "write"
    EDIT = "edit"
    RUN = "run"
    BROWSE = "browse"
    BROWSE_INTERACTIVE = "browse_interactive"
    MCP = "call_tool_mcp"
    THINK = "think"
    FINISH = "finish"
    REJECT = "reject"
    NULL = "null"
    PAUSE = "pause"
    RESUME = "resume"
    STOP = "stop"
    CHANGE_AGENT_STATE = "change_agent_state"
    PUSH = "push"
    SEND_PR = "send_pr"
    RECALL = "recall"
    CONDENSATION = "condensation"
    CONDENSATION_REQUEST = "condensation_request"
    TASK_TRACKING = "task_tracking"
    STREAMING_CHUNK = "streaming_chunk"


class AgentState(str, Enum):
    """Enum defining all possible agent lifecycle states."""

    LOADING = "loading"
    RUNNING = "running"
    AWAITING_USER_INPUT = "awaiting_user_input"
    PAUSED = "paused"
    STOPPED = "stopped"
    FINISHED = "finished"
    REJECTED = "rejected"
    ERROR = "error"
    AWAITING_USER_CONFIRMATION = "awaiting_user_confirmation"
    USER_CONFIRMED = "user_confirmed"
    USER_REJECTED = "user_rejected"
    RATE_LIMITED = "rate_limited"


class ObservationType(str, Enum):
    """Enum defining all possible observation types."""

    READ = "read"
    WRITE = "write"
    EDIT = "edit"
    BROWSE = "browse"
    RUN = "run"
    CHAT = "chat"
    MESSAGE = "message"
    ERROR = "error"
    SUCCESS = "success"
    NULL = "null"
    THINK = "think"
    AGENT_STATE_CHANGED = "agent_state_changed"
    USER_REJECTED = "user_rejected"
    CONDENSE = "condense"
    RECALL = "recall"
    MCP = "mcp"
    DOWNLOAD = "download"
    TASK_TRACKING = "task_tracking"
    SERVER_READY = "server_ready"
    RECALL_FAILURE = "recall_failure"

