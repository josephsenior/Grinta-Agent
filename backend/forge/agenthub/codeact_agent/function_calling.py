"""This file contains the function calling implementation for different actions.

This is similar to the functionality of `CodeActResponseParser`.
"""

from __future__ import annotations

import json
from typing import TYPE_CHECKING, Any, Callable, Mapping

from forge.agenthub.codeact_agent.tools import (
    BrowserTool,
    CondensationRequestTool,
    FinishTool,
    LLMBasedFileEditTool,
    ThinkTool,
    create_cmd_run_tool,
    create_str_replace_editor_tool,
    create_ultimate_editor_tool,
)
from forge.agenthub.codeact_agent.tools.security_utils import RISK_LEVELS
from forge.core.exceptions import (
    FunctionCallNotExistsError,
    FunctionCallValidationError,
)
from forge.core.logger import forge_logger as logger
from forge.events.action import (
    Action,
    ActionSecurityRisk,
    AgentFinishAction,
    AgentThinkAction,
    BrowseInteractiveAction,
    CmdRunAction,
    FileEditAction,
    FileReadAction,
    MessageAction,
    TaskTrackingAction,
)
from forge.events.action.agent import CondensationRequestAction
from forge.events.action.mcp import MCPAction
from forge.events.event import FileEditSource, FileReadSource
from forge.events.tool import ToolCallMetadata, build_tool_call_metadata
from forge.llm.tool_names import TASK_TRACKER_TOOL_NAME

ToolHandler = Callable[[dict[str, Any]], Action]

if TYPE_CHECKING:
    ModelResponse = Any


def combine_thought(action: Action, thought: str) -> Action:
    """Combine a thought with an existing action's thought.

    Args:
        action: The action to combine the thought with.
        thought: The thought to combine.

    Returns:
        Action: The action with the combined thought.

    """
    if not hasattr(action, "thought"):
        return action
    if thought:
        action.thought = f"{thought}\n{action.thought}" if action.thought else thought
    return action


def set_security_risk(action: Action, arguments: dict) -> None:
    """Set the security risk level for the action."""
    if "security_risk" in arguments:
        if arguments["security_risk"] in RISK_LEVELS:
            if hasattr(action, "security_risk"):
                action.security_risk = getattr(
                    ActionSecurityRisk, arguments["security_risk"]
                )
        else:
            logger.warning(
                "Invalid security_risk value: %s", arguments["security_risk"]
            )


def _handle_cmd_run_tool(arguments: dict) -> CmdRunAction:
    """Handle CmdRunTool (Bash) tool call."""
    if "command" not in arguments:
        msg = f'Missing required argument "command" in tool call {
            create_cmd_run_tool()["function"]["name"]
        }'
        raise FunctionCallValidationError(
            msg,
        )
    is_input = arguments.get("is_input", "false") == "true"
    action = CmdRunAction(command=arguments["command"], is_input=is_input)
    if "timeout" in arguments:
        try:
            action.set_hard_timeout(float(arguments["timeout"]))
        except ValueError as e:
            msg = f"Invalid float passed to 'timeout' argument: {arguments['timeout']}"
            raise FunctionCallValidationError(
                msg,
            ) from e
    set_security_risk(action, arguments)
    return action


def _handle_delegate_to_browsing_agent(arguments: dict) -> Action:
    """Handle delegate_to_browsing_agent tool call."""
    from forge.events.action import MessageAction
    return MessageAction(content=f"Delegation to BrowsingAgent with inputs {arguments} is not supported anymore.")


def _handle_finish_tool(arguments: dict) -> AgentFinishAction:
    """Handle FinishTool tool call."""
    return AgentFinishAction(final_thought=arguments.get("message", ""))


def _handle_llm_based_file_edit_tool(arguments: dict) -> FileEditAction:
    """Handle LLMBasedFileEditTool tool call."""
    if "path" not in arguments:
        msg = f'Missing required argument "path" in tool call {
            LLMBasedFileEditTool["function"]["name"]
        }'
        raise FunctionCallValidationError(
            msg,
        )
    if "content" not in arguments:
        msg = f'Missing required argument "content" in tool call {
            LLMBasedFileEditTool["function"]["name"]
        }'
        raise FunctionCallValidationError(
            msg,
        )
    return FileEditAction(
        path=arguments["path"],
        content=arguments["content"],
        start=arguments.get("start", 1),
        end=arguments.get("end", -1),
        impl_source=arguments.get("impl_source", FileEditSource.LLM_BASED_EDIT),
    )


def _validate_str_replace_editor_args(arguments: dict) -> tuple[str, str]:
    """Validate required arguments for str_replace_editor tool."""
    tool_name = create_str_replace_editor_tool()["function"]["name"]
    if "command" not in arguments:
        msg = f'Missing required argument "command" in tool call {tool_name}'
        raise FunctionCallValidationError(msg)
    if "path" not in arguments:
        msg = f'Missing required argument "path" in tool call {tool_name}'
        raise FunctionCallValidationError(msg)
    return arguments["path"], arguments["command"]


def _filter_valid_editor_kwargs(other_kwargs: dict) -> dict:
    """Filter and validate kwargs for file editor."""
    str_replace_editor_tool = create_str_replace_editor_tool()
    valid_params = set(
        str_replace_editor_tool["function"]["parameters"]["properties"].keys()
    )
    valid_kwargs_for_editor = {}
    tool_name = str_replace_editor_tool["function"]["name"]

    for key, value in other_kwargs.items():
        if key not in valid_params:
            msg = f"Unexpected argument {key} in tool call {tool_name}. Allowed arguments are: {valid_params}"
            raise FunctionCallValidationError(
                msg,
            )
        if key != "security_risk":
            valid_kwargs_for_editor[key] = value
    return valid_kwargs_for_editor


def _handle_str_replace_editor_tool(arguments: dict) -> Action:
    """Handle str_replace_editor tool call."""
    path, command = _validate_str_replace_editor_args(arguments)
    other_kwargs = {k: v for k, v in arguments.items() if k not in ["command", "path"]}

    # Handle view command separately
    if command == "view":
        return FileReadAction(
            path=path,
            impl_source=FileReadSource.FILE_EDITOR,
            view_range=other_kwargs.get("view_range"),
        )

    # Remove view_range for edit commands
    other_kwargs.pop("view_range", None)

    # Filter valid editor kwargs
    valid_kwargs_for_editor = _filter_valid_editor_kwargs(other_kwargs)

    # Create and configure action
    action = FileEditAction(
        path=path,
        command=command,
        impl_source=FileEditSource.FILE_EDITOR,
        **valid_kwargs_for_editor,
    )
    set_security_risk(action, arguments)
    return action


def _handle_think_tool(arguments: dict) -> AgentThinkAction:
    """Handle ThinkTool tool call."""
    return AgentThinkAction(thought=arguments.get("thought", ""))


def _handle_condensation_request_tool(arguments: dict) -> CondensationRequestAction:
    """Handle CondensationRequestTool tool call."""
    return CondensationRequestAction()


def _handle_browser_tool(arguments: dict) -> BrowseInteractiveAction:
    """Handle BrowserTool tool call."""
    if "code" not in arguments:
        msg = f'Missing required argument "code" in tool call {
            BrowserTool["function"]["name"]
        }'
        raise FunctionCallValidationError(
            msg,
        )
    action = BrowseInteractiveAction(browser_actions=arguments["code"])
    set_security_risk(action, arguments)
    return action


def _handle_task_tracker_tool(arguments: dict) -> TaskTrackingAction:
    """Handle TASK_TRACKER_TOOL tool call."""
    if "command" not in arguments:
        msg = (
            f'Missing required argument "command" in tool call {TASK_TRACKER_TOOL_NAME}'
        )
        raise FunctionCallValidationError(msg)
    if arguments["command"] == "plan" and "task_list" not in arguments:
        msg = f'Missing required argument "task_list" for "plan" command in tool call {TASK_TRACKER_TOOL_NAME}'
        raise FunctionCallValidationError(
            msg,
        )
    raw_task_list = arguments.get("task_list", [])
    if not isinstance(raw_task_list, list):
        msg = f'Invalid format for "task_list". Expected a list but got {
            type(raw_task_list)
        }.'
        raise FunctionCallValidationError(
            msg,
        )
    normalized_task_list = []
    for i, task in enumerate(raw_task_list):
        if isinstance(task, dict):
            normalized_task = {
                "id": task.get(
                    "id",
                    f"task-{i + 1}",
                ),
                "title": task.get("title", "Untitled task"),
                "status": task.get("status", "todo"),
                "notes": task.get("notes", ""),
            }
        else:
            logger.warning(
                "Unexpected task format in task_list: %s - %s", type(task), task
            )
            msg = f"Unexpected task format in task_list: {
                type(task)
            }. Each task shoud be a dictionary."
            raise FunctionCallValidationError(
                msg,
            )
        normalized_task_list.append(normalized_task)
    return TaskTrackingAction(
        command=arguments["command"], task_list=normalized_task_list
    )


def _handle_mcp_tool(
    tool_call_name: str, arguments: Mapping[str, Any] | None
) -> MCPAction:
    """Handle MCP tool call."""
    logger.debug(
        "Creating MCP action for tool: %s with arguments: %s", tool_call_name, arguments
    )

    # Basic validation - ensure arguments is a dict
    if isinstance(arguments, Mapping):
        normalized_args = dict(arguments)
    else:
        logger.warning(
            "MCP tool arguments is not a mapping, got: %s", type(arguments)
        )
        normalized_args = {}

    return MCPAction(name=tool_call_name, arguments=normalized_args)


def _validate_ultimate_editor_args(arguments: dict, tool_name: str) -> tuple[str, str]:
    """Validate required arguments for ultimate editor.

    Args:
        arguments: Tool call arguments
        tool_name: Name of the tool

    Returns:
        Tuple of (command, file_path)

    Raises:
        FunctionCallValidationError: If validation fails

    """
    if "command" not in arguments:
        raise FunctionCallValidationError(
            f'Missing required argument "command" in tool call {tool_name}'
        )

    if "file_path" not in arguments:
        raise FunctionCallValidationError(
            f'Missing required argument "file_path" in tool call {tool_name}'
        )

    return arguments["command"], arguments["file_path"]


def _handle_edit_function_command(editor, file_path: str, arguments: dict) -> Action:
    """Handle edit_function command."""
    function_name = arguments.get("function_name")
    new_body = arguments.get("new_body")

    if not function_name or not new_body:
        raise FunctionCallValidationError(
            "edit_function requires 'function_name' and 'new_body' arguments"
        )

    result = editor.edit_function(file_path, function_name, new_body)

    if result.success:
        return FileReadAction(
            path=file_path, impl_source=FileReadSource.DEFAULT, thought=result.message
        )
    else:
        return MessageAction(content=f"❌ Edit failed: {result.message}")


def _handle_rename_symbol_command(editor, file_path: str, arguments: dict) -> Action:
    """Handle rename_symbol command."""
    old_name = arguments.get("old_name")
    new_name = arguments.get("new_name")

    if not old_name or not new_name:
        raise FunctionCallValidationError(
            "rename_symbol requires 'old_name' and 'new_name' arguments"
        )

    result = editor.rename_symbol(file_path, old_name, new_name)

    if result.success:
        return FileReadAction(
            path=file_path, impl_source=FileReadSource.DEFAULT, thought=result.message
        )
    else:
        return MessageAction(content=f"❌ Rename failed: {result.message}")


def _handle_find_symbol_command(editor, file_path: str, arguments: dict) -> Action:
    """Handle find_symbol command."""
    symbol_name = arguments.get("symbol_name")
    if not symbol_name:
        raise FunctionCallValidationError("find_symbol requires 'symbol_name' argument")

    symbol_type = arguments.get("symbol_type")
    result = editor.find_symbol(file_path, symbol_name, symbol_type)

    if result:
        message = (
            f"✓ Found '{symbol_name}' in {file_path}:\n"
            f"  Type: {result.node_type}\n"
            f"  Lines: {result.line_start}-{result.line_end}"
        )
        if result.parent_name:
            message += f"\n  Parent: {result.parent_name}"
        return MessageAction(content=message)
    else:
        return MessageAction(
            content=f"❌ Symbol '{symbol_name}' not found in {file_path}"
        )


def _handle_replace_range_command(editor, file_path: str, arguments: dict) -> Action:
    """Handle replace_range command."""
    start_line = arguments.get("start_line")
    end_line = arguments.get("end_line")
    new_code = arguments.get("new_code")

    if start_line is None or end_line is None or new_code is None:
        raise FunctionCallValidationError(
            "replace_range requires 'start_line', 'end_line', and 'new_code' arguments"
        )

    result = editor.replace_code_range(file_path, start_line, end_line, new_code)

    if result.success:
        return FileReadAction(
            path=file_path, impl_source=FileReadSource.DEFAULT, thought=result.message
        )
    else:
        return MessageAction(content=f"❌ Replace failed: {result.message}")


def _handle_normalize_indent_command(editor, file_path: str, arguments: dict) -> Action:
    """Handle normalize_indent command."""
    style = arguments.get("style")
    size = arguments.get("size")
    result = editor.normalize_file_indent(file_path, style, size)

    if result.success:
        return FileReadAction(
            path=file_path, impl_source=FileReadSource.DEFAULT, thought=result.message
        )
    else:
        return MessageAction(content=f"❌ Normalization failed: {result.message}")


def _handle_ultimate_editor_tool(arguments: dict) -> Action:
    """Handle UltimateEditor tool call."""
    tool_name = create_ultimate_editor_tool()["function"]["name"]

    # Validate arguments
    command, file_path = _validate_ultimate_editor_args(arguments, tool_name)

    # Initialize editor
    try:
        from forge.agenthub.codeact_agent.tools.ultimate_editor import UltimateEditor

        editor = UltimateEditor()
    except Exception as e:
        raise FunctionCallValidationError(f"Failed to initialize Ultimate Editor: {e}")

    # Command dispatch map
    command_handlers = {
        "edit_function": _handle_edit_function_command,
        "rename_symbol": _handle_rename_symbol_command,
        "find_symbol": _handle_find_symbol_command,
        "replace_range": _handle_replace_range_command,
        "normalize_indent": _handle_normalize_indent_command,
    }

    # Execute command
    try:
        if command not in command_handlers:
            raise FunctionCallValidationError(
                f"Unknown command '{command}' for ultimate_editor tool"
            )

        handler = command_handlers[command]
        return handler(editor, file_path, arguments)

    except Exception as e:
        return MessageAction(content=f"❌ Ultimate Editor error: {str(e)}")


def _create_tool_dispatch_map() -> dict[str, ToolHandler]:
    """Create dispatch map for tool handlers."""
    return {
        create_cmd_run_tool()["function"]["name"]: _handle_cmd_run_tool,
        "delegate_to_browsing_agent": _handle_delegate_to_browsing_agent,
        FinishTool["function"]["name"]: _handle_finish_tool,
        LLMBasedFileEditTool["function"]["name"]: _handle_llm_based_file_edit_tool,
        create_str_replace_editor_tool()["function"][
            "name"
        ]: _handle_str_replace_editor_tool,
        create_ultimate_editor_tool()["function"]["name"]: _handle_ultimate_editor_tool,
        ThinkTool["function"]["name"]: _handle_think_tool,
        CondensationRequestTool["function"]["name"]: _handle_condensation_request_tool,
        BrowserTool["function"]["name"]: _handle_browser_tool,
        TASK_TRACKER_TOOL_NAME: _handle_task_tracker_tool,
    }


def response_to_actions(
    response: ModelResponse, mcp_tool_names: list[str] | None = None
) -> list[Action]:
    """Convert model response to actions."""
    actions: list[Action] = []
    _validate_response_choices(response)

    choice = response.choices[0]
    assistant_msg = getattr(choice, "message", None)
    if assistant_msg is None:
        raise FunctionCallValidationError(
            "Model response choice is missing a message payload"
        )

    tool_calls = getattr(assistant_msg, "tool_calls", None)
    if tool_calls:
        actions = _process_tool_calls_to_actions(
            assistant_msg, response, mcp_tool_names
        )
    else:
        message_content = getattr(assistant_msg, "content", None)
        actions = _create_message_action_from_content(message_content)

    _set_response_id_for_actions(actions, response)
    return actions


def _validate_response_choices(response: ModelResponse) -> None:
    """Validate that response has exactly one choice."""
    assert len(response.choices) == 1, "Only one choice is supported for now"


def _process_tool_calls_to_actions(
    assistant_msg,
    response: ModelResponse,
    mcp_tool_names: list[str] | None,
) -> list[Action]:
    """Process tool calls and convert them to actions."""
    actions: list[Action] = []
    thought = _extract_thought_from_content(assistant_msg.content)
    tool_dispatch = _create_tool_dispatch_map()

    for i, tool_call in enumerate(assistant_msg.tool_calls):
        action = _process_single_tool_call(tool_call, tool_dispatch, mcp_tool_names)

        if i == 0:
            action = combine_thought(action, thought)

        _set_tool_call_metadata(
            action, tool_call, response, len(assistant_msg.tool_calls)
        )
        actions.append(action)

    return actions


def _extract_thought_from_content(content) -> str:
    """Extract thought from assistant message content."""
    thought = ""
    if isinstance(content, str):
        thought = content
    elif isinstance(content, list):
        for msg in content:
            if msg["type"] == "text":
                thought += msg["text"]
    return thought


def _process_single_tool_call(
    tool_call, tool_dispatch: dict, mcp_tool_names: list[str] | None
) -> Action:
    """Process a single tool call and return the corresponding action."""
    logger.debug("Tool call in function_calling.py: %s", tool_call)

    try:
        arguments = json.loads(tool_call.function.arguments)
    except json.decoder.JSONDecodeError as e:
        args_preview = (
            tool_call.function.arguments[:100] + "..."
            if len(tool_call.function.arguments) > 100
            else tool_call.function.arguments
        )
        msg = f"Failed to parse tool call arguments for '{tool_call.function.name}': JSON decode error: {e}. Arguments: {args_preview}"
        logger.error("JSON decode error in tool call: %s", msg)
        raise FunctionCallValidationError(msg) from e

    tool_name = tool_call.function.name

    if tool_name in tool_dispatch:
        return tool_dispatch[tool_name](arguments)
    if mcp_tool_names and tool_name in mcp_tool_names:
        return _handle_mcp_tool(tool_name, arguments)
    msg = f"Tool {tool_name} is not registered. (arguments: {arguments}). Please check the tool name and retry with an existing tool."
    raise FunctionCallNotExistsError(
        msg,
    )


def _set_tool_call_metadata(
    action: Action, tool_call, response: ModelResponse, total_calls: int
) -> None:
    """Set tool call metadata for the action.

    Falls back to direct construction if the patched ToolCallMetadata lacks
    the `from_sdk` classmethod (used in certain unit tests that monkeypatch
    the class).
    """
    action.tool_call_metadata = build_tool_call_metadata(
        function_name=tool_call.function.name,
        tool_call_id=tool_call.id,
        response_obj=response,
        total_calls_in_response=total_calls,
    )


def _create_message_action_from_content(content) -> list[Action]:
    """Create message action from content when no tool calls are present."""
    content_str = str(content) if content else ""
    return [MessageAction(content=content_str, wait_for_response=True)]


def _set_response_id_for_actions(
    actions: list[Action], response: ModelResponse
) -> None:
    """Set response ID for all actions."""
    for action in actions:
        action.response_id = response.id
