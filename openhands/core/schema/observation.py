"""Core functionality for the OpenHands agent framework.

Classes:
    ObservationType
"""

from enum import Enum


class ObservationType(str, Enum):
    READ = "read"
    "The content of a file\n    "
    WRITE = "write"
    EDIT = "edit"
    BROWSE = "browse"
    "The HTML content of a URL\n    "
    RUN = "run"
    "The output of a command\n    "
    RUN_IPYTHON = "run_ipython"
    "Runs a IPython cell.\n    "
    CHAT = "chat"
    "A message from the user\n    "
    DELEGATE = "delegate"
    "The result of a task delegated to another agent\n    "
    MESSAGE = "message"
    ERROR = "error"
    SUCCESS = "success"
    NULL = "null"
    THINK = "think"
    AGENT_STATE_CHANGED = "agent_state_changed"
    USER_REJECTED = "user_rejected"
    CONDENSE = "condense"
    "Result of a condensation operation."
    RECALL = "recall"
    "Result of a recall operation. This can be the workspace context, a microagent, or other types of information."
    MCP = "mcp"
    "Result of a MCP Server operation"
    DOWNLOAD = "download"
    "Result of downloading/opening a file via the browser"
    TASK_TRACKING = "task_tracking"
    "Result of a task tracking operation"
    SERVER_READY = "server_ready"
    "Notification that a server has started and is ready to accept connections"
