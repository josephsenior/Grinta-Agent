"""Action event definitions emitted by Forge agents."""

from forge.events.action.action import (
    Action,
    ActionConfirmationStatus,
    ActionSecurityRisk,
)
from forge.events.action.agent import (
    AgentDelegateAction,
    AgentFinishAction,
    AgentRejectAction,
    AgentThinkAction,
    ChangeAgentStateAction,
    RecallAction,
    TaskTrackingAction,
)
from forge.events.action.browse import BrowseInteractiveAction, BrowseURLAction
from forge.events.action.commands import CmdRunAction, IPythonRunCellAction
from forge.events.action.empty import NullAction
from forge.events.action.files import (
    FileEditAction,
    FileReadAction,
    FileWriteAction,
)
from forge.events.action.mcp import MCPAction
from forge.events.action.message import MessageAction, StreamingChunkAction, SystemMessageAction

__all__ = [
    "Action",
    "ActionConfirmationStatus",
    "ActionSecurityRisk",
    "AgentDelegateAction",
    "AgentFinishAction",
    "AgentRejectAction",
    "AgentThinkAction",
    "BrowseInteractiveAction",
    "BrowseURLAction",
    "ChangeAgentStateAction",
    "CmdRunAction",
    "FileEditAction",
    "FileReadAction",
    "FileWriteAction",
    "IPythonRunCellAction",
    "MCPAction",
    "MessageAction",
    "NullAction",
    "RecallAction",
    "StreamingChunkAction",  # ⚡ CRITICAL FIX: Enable real-time LLM streaming!
    "SystemMessageAction",
    "TaskTrackingAction",
]
