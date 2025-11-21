"""Pydantic schemas for all Forge action types."""

from __future__ import annotations

from typing import Any, Literal, Optional, Union

from pydantic import Field

from forge.core.schemas.base import EventSchemaV1
from forge.core.schemas.enums import ActionType


class ActionSchemaV1(EventSchemaV1):
    """Base schema for all action types."""

    action_type: str = Field(..., description="Type of action")
    runnable: bool = Field(False, description="Whether action can be executed")
    confirmation_state: Optional[str] = Field(
        None, description="Action confirmation status"
    )
    security_risk: Optional[int] = Field(
        None, description="Security risk level for this action"
    )
    thought: Optional[str] = Field(None, description="Agent's reasoning for this action")


class FileReadActionSchema(ActionSchemaV1):
    """Schema for FileReadAction."""

    action_type: Literal[ActionType.READ] = Field(ActionType.READ, frozen=True)
    runnable: bool = Field(True, frozen=True)
    path: str = Field(..., description="Path to file to read")
    start: int = Field(0, description="Starting line number (0-indexed)")
    end: int = Field(-1, description="Ending line number (-1 for end of file)")
    impl_source: Optional[str] = Field(None, description="Implementation source")
    view_range: Optional[list[int]] = Field(None, description="View range for file reading")


class FileWriteActionSchema(ActionSchemaV1):
    """Schema for FileWriteAction."""

    action_type: Literal[ActionType.WRITE] = Field(ActionType.WRITE, frozen=True)
    runnable: bool = Field(True, frozen=True)
    path: str = Field(..., description="Path to file to write")
    content: str = Field(..., description="Content to write to file")
    start: int = Field(0, description="Starting line number (0-indexed)")
    end: int = Field(-1, description="Ending line number (-1 for end of file)")


class FileEditActionSchema(ActionSchemaV1):
    """Schema for FileEditAction."""

    action_type: Literal[ActionType.EDIT] = Field(ActionType.EDIT, frozen=True)
    runnable: bool = Field(True, frozen=True)
    path: str = Field(..., description="Path to file to edit")
    command: Optional[str] = Field(None, description="Editing command (OH_ACI mode)")
    file_text: Optional[str] = Field(None, description="File content for create command")
    old_str: Optional[str] = Field(None, description="String to replace (str_replace command)")
    new_str: Optional[str] = Field(None, description="Replacement string")
    insert_line: Optional[int] = Field(None, description="Line number for insert command")
    content: Optional[str] = Field(None, description="Content to write (LLM-based editing)")
    start: int = Field(1, description="Starting line number (1-indexed)")
    end: int = Field(-1, description="Ending line number (-1 for end of file)")
    impl_source: Optional[str] = Field(None, description="Implementation source (LLM_BASED_EDIT or OH_ACI)")


class CmdRunActionSchema(ActionSchemaV1):
    """Schema for CmdRunAction."""

    action_type: Literal[ActionType.RUN] = Field(ActionType.RUN, frozen=True)
    runnable: bool = Field(True, frozen=True)
    command: str = Field(..., description="Shell command to execute")
    is_input: bool = Field(False, description="Whether command is user input (for stdin)")
    blocking: bool = Field(False, description="Whether to wait for command to complete")
    is_static: bool = Field(False, description="Whether command is static (from static analysis)")
    cwd: Optional[str] = Field(None, description="Working directory for command")
    hidden: bool = Field(False, description="Whether to hide command from user")


class IPythonRunCellActionSchema(ActionSchemaV1):
    """Schema for IPythonRunCellAction."""

    action_type: Literal[ActionType.RUN_IPYTHON] = Field(ActionType.RUN_IPYTHON, frozen=True)
    runnable: bool = Field(True, frozen=True)
    code: str = Field(..., description="Python code to execute")
    include_extra: bool = Field(True, description="Whether to include extra output (plots, etc.)")
    kernel_init_code: Optional[str] = Field(None, description="Code to run before executing main code")


class MessageActionSchema(ActionSchemaV1):
    """Schema for MessageAction."""

    action_type: Literal[ActionType.MESSAGE] = Field(ActionType.MESSAGE, frozen=True)
    runnable: bool = Field(False, frozen=True)
    content: str = Field(..., description="Message content")


class SystemMessageActionSchema(ActionSchemaV1):
    """Schema for SystemMessageAction."""

    action_type: Literal[ActionType.SYSTEM] = Field(ActionType.SYSTEM, frozen=True)
    runnable: bool = Field(False, frozen=True)
    content: str = Field(..., description="System message content")


class BrowseInteractiveActionSchema(ActionSchemaV1):
    """Schema for BrowseInteractiveAction."""

    action_type: Literal[ActionType.BROWSE_INTERACTIVE] = Field(
        ActionType.BROWSE_INTERACTIVE, frozen=True
    )
    runnable: bool = Field(True, frozen=True)
    browser_actions: str = Field(..., description="Browser actions to perform (BrowserGym action code)")
    browsergym_send_msg_to_user: Optional[str] = Field(None, description="Message to display to user")
    return_axtree: bool = Field(False, description="Whether to return accessibility tree")


class AgentFinishActionSchema(ActionSchemaV1):
    """Schema for AgentFinishAction."""

    action_type: Literal[ActionType.FINISH] = Field(ActionType.FINISH, frozen=True)
    runnable: bool = Field(False, frozen=True)
    message: Optional[str] = Field(None, description="Finish message")


class AgentRejectActionSchema(ActionSchemaV1):
    """Schema for AgentRejectAction."""

    action_type: Literal[ActionType.REJECT] = Field(ActionType.REJECT, frozen=True)
    runnable: bool = Field(False, frozen=True)
    message: Optional[str] = Field(None, description="Rejection message")


class AgentDelegateActionSchema(ActionSchemaV1):
    """Schema for AgentDelegateAction."""

    action_type: Literal[ActionType.DELEGATE] = Field(ActionType.DELEGATE, frozen=True)
    runnable: bool = Field(False, frozen=True)
    message: Optional[str] = Field(None, description="Delegation message")
    agent: Optional[str] = Field(None, description="Agent to delegate to")


class ChangeAgentStateActionSchema(ActionSchemaV1):
    """Schema for ChangeAgentStateAction."""

    action_type: Literal[ActionType.CHANGE_AGENT_STATE] = Field(
        ActionType.CHANGE_AGENT_STATE, frozen=True
    )
    runnable: bool = Field(False, frozen=True)
    state: str = Field(..., description="New agent state")


class NullActionSchema(ActionSchemaV1):
    """Schema for NullAction."""

    action_type: Literal[ActionType.NULL] = Field(ActionType.NULL, frozen=True)
    runnable: bool = Field(False, frozen=True)


# Union type for all action schemas
ActionSchemaUnion = Union[
    FileReadActionSchema,
    FileWriteActionSchema,
    FileEditActionSchema,
    CmdRunActionSchema,
    IPythonRunCellActionSchema,
    MessageActionSchema,
    SystemMessageActionSchema,
    BrowseInteractiveActionSchema,
    AgentFinishActionSchema,
    AgentRejectActionSchema,
    AgentDelegateActionSchema,
    ChangeAgentStateActionSchema,
    NullActionSchema,
]
