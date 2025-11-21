"""Action event definitions emitted by Forge agents."""

from __future__ import annotations

from forge.events.action._canonical import canonicalize

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
from forge.events.action.message import (
    MessageAction,
    StreamingChunkAction,
    SystemMessageAction,
)

canonicalize("Action", Action)
canonicalize("ActionConfirmationStatus", ActionConfirmationStatus)
canonicalize("ActionSecurityRisk", ActionSecurityRisk)
canonicalize("AgentDelegateAction", AgentDelegateAction)
canonicalize("AgentFinishAction", AgentFinishAction)
canonicalize("AgentRejectAction", AgentRejectAction)
canonicalize("AgentThinkAction", AgentThinkAction)
canonicalize("BrowseInteractiveAction", BrowseInteractiveAction)
canonicalize("BrowseURLAction", BrowseURLAction)
canonicalize("ChangeAgentStateAction", ChangeAgentStateAction)
canonicalize("CmdRunAction", CmdRunAction)
canonicalize("FileEditAction", FileEditAction)
canonicalize("FileReadAction", FileReadAction)
canonicalize("FileWriteAction", FileWriteAction)
canonicalize("IPythonRunCellAction", IPythonRunCellAction)
canonicalize("MCPAction", MCPAction)
canonicalize("MessageAction", MessageAction)
canonicalize("NullAction", NullAction)
canonicalize("RecallAction", RecallAction)
canonicalize("StreamingChunkAction", StreamingChunkAction)
canonicalize("SystemMessageAction", SystemMessageAction)
canonicalize("TaskTrackingAction", TaskTrackingAction)

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
