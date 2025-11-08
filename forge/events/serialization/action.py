"""Serialization helpers for converting actions to and from dictionaries."""

from __future__ import annotations

from typing import Any

from forge.core.exceptions import LLMMalformedActionError
from forge.events.action.action import Action, ActionSecurityRisk
from forge.events.action.agent import (
    AgentDelegateAction,
    AgentFinishAction,
    AgentRejectAction,
    AgentThinkAction,
    ChangeAgentStateAction,
    CondensationAction,
    CondensationRequestAction,
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

actions = (
    NullAction,
    CmdRunAction,
    IPythonRunCellAction,
    BrowseURLAction,
    BrowseInteractiveAction,
    FileReadAction,
    FileWriteAction,
    FileEditAction,
    AgentThinkAction,
    AgentFinishAction,
    AgentRejectAction,
    AgentDelegateAction,
    RecallAction,
    ChangeAgentStateAction,
    MessageAction,
    StreamingChunkAction,  # ⚡ CRITICAL: Register streaming chunks for real-time LLM responses!
    SystemMessageAction,
    CondensationAction,
    CondensationRequestAction,
    MCPAction,
    TaskTrackingAction,
)
ACTION_TYPE_TO_CLASS = {action_class.action: action_class for action_class in actions}


def handle_action_deprecated_args(args: dict[str, Any]) -> dict[str, Any]:
    """Handle deprecated arguments in action serialization.

    This function removes deprecated arguments from action args and handles
    special cases like translating deprecated ipython code format.

    Args:
        args: Dictionary of action arguments that may contain deprecated keys.

    Returns:
        dict[str, Any]: The cleaned arguments dictionary with deprecated keys removed.

    """
    if "keep_prompt" in args:
        args.pop("keep_prompt")
    if "task_completed" in args:
        args.pop("task_completed")
    if "translated_ipython_code" in args:
        code = args.pop("translated_ipython_code")
        file_editor_prefix = "print(file_editor(**"
        if code is not None and code.startswith(file_editor_prefix) and code.endswith("))"):
            try:
                import ast

                dict_str = code[len(file_editor_prefix): -2]
                file_args = ast.literal_eval(dict_str)
                args |= file_args
            except (ValueError, SyntaxError):
                pass
        if args.get("command") == "view":
            args.pop("command")
    return args


def _validate_action_dict(action: dict) -> None:
    """Validate that action dict is valid and has required keys."""
    if not isinstance(action, dict):
        msg = "action must be a dictionary"
        raise LLMMalformedActionError(msg)
    if "action" not in action:
        msg = f"'action' key is not found in action={action!r}"
        raise LLMMalformedActionError(msg)
    if not isinstance(action["action"], str):
        msg = f"'action['action']={
            action['action']!r}' is not defined. Available actions: {
            ACTION_TYPE_TO_CLASS.keys()}"
        raise LLMMalformedActionError(
            msg,
        )


def _get_action_class(action_type: str):
    """Get action class from action type."""
    action_class = ACTION_TYPE_TO_CLASS.get(action_type)
    if action_class is None:
        msg = f"'action['action']={
            action_type!r}' is not defined. Available actions: {
            ACTION_TYPE_TO_CLASS.keys()}"
        raise LLMMalformedActionError(
            msg,
        )
    return action_class


def _process_action_args(args: dict) -> tuple[dict, str | None]:
    """Process and normalize action arguments."""
    timestamp = args.pop("timestamp", None)
    is_confirmed = args.pop("is_confirmed", None)
    if is_confirmed is not None:
        args["confirmation_state"] = is_confirmed
    if "images_urls" in args:
        args["image_urls"] = args.pop("images_urls")
    _normalize_security_risk(args)
    args = handle_action_deprecated_args(args)
    return args, timestamp


def _normalize_security_risk(args: dict) -> None:
    """Normalize security_risk argument."""
    if "security_risk" in args and args["security_risk"] is not None:
        try:
            args["security_risk"] = ActionSecurityRisk(args["security_risk"])
        except (ValueError, TypeError):
            args.pop("security_risk")


def _create_action_instance(action_class, args: dict, action: dict, timestamp: str | None) -> Action:
    """Create action instance with timeout and timestamp if specified."""
    try:
        decoded_action = action_class(**args)
        if "timeout" in action:
            blocking = args.get("blocking", False)
            decoded_action.set_hard_timeout(action["timeout"], blocking=blocking)
        if timestamp:
            decoded_action._timestamp = timestamp
        return decoded_action
    except TypeError as e:
        msg = f"action={action} has the wrong arguments: {e!s}"
        raise LLMMalformedActionError(msg) from e


def action_from_dict(action: dict) -> Action:
    """Deserialize action from dictionary representation.
    
    Converts a dictionary containing action data into an Action instance,
    validating the structure and handling argument processing.
    
    Args:
        action: Dictionary with action type and arguments
        
    Returns:
        Deserialized Action instance
        
    Raises:
        LLMMalformedActionError: If action dict is invalid

    """
    _validate_action_dict(action)
    action = action.copy()
    action_class = _get_action_class(action["action"])
    args = action.get("args", {})
    args, timestamp = _process_action_args(args)
    decoded_action = _create_action_instance(action_class, args, action, timestamp)
    assert isinstance(decoded_action, Action)
    return decoded_action
