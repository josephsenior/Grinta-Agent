"""This file contains the function calling implementation for different actions.

This is similar to the functionality of `CodeActResponseParser`.
"""

from __future__ import annotations

import json
from typing import TYPE_CHECKING

from openhands.agenthub.codeact_agent.tools import (
    BrowserTool,
    CondensationRequestTool,
    FinishTool,
    IPythonTool,
    LLMBasedFileEditTool,
    ThinkTool,
    create_cmd_run_tool,
    create_str_replace_editor_tool,
    create_ultimate_editor_tool,
)
from openhands.agenthub.codeact_agent.tools.security_utils import RISK_LEVELS
from openhands.core.exceptions import (
    FunctionCallNotExistsError,
    FunctionCallValidationError,
)
from openhands.core.logger import openhands_logger as logger
from openhands.events.action import (
    Action,
    ActionSecurityRisk,
    AgentDelegateAction,
    AgentFinishAction,
    AgentThinkAction,
    BrowseInteractiveAction,
    CmdRunAction,
    FileEditAction,
    FileReadAction,
    IPythonRunCellAction,
    MessageAction,
    TaskTrackingAction,
)
from openhands.events.action.agent import CondensationRequestAction
from openhands.events.action.mcp import MCPAction
from openhands.events.event import FileEditSource, FileReadSource
from openhands.events.tool import ToolCallMetadata
from openhands.llm.tool_names import TASK_TRACKER_TOOL_NAME

if TYPE_CHECKING:
    from litellm import ModelResponse


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
                action.security_risk = getattr(ActionSecurityRisk, arguments["security_risk"])
        else:
            logger.warning("Invalid security_risk value: %s", arguments["security_risk"])


def _handle_cmd_run_tool(arguments: dict) -> CmdRunAction:
    """Handle CmdRunTool (Bash) tool call."""
    if "command" not in arguments:
        msg = f'Missing required argument "command" in tool call {
            create_cmd_run_tool()['function']['name']}'
        raise FunctionCallValidationError(
            msg,
        )
    is_input = arguments.get("is_input", "false") == "true"
    action = CmdRunAction(command=arguments["command"], is_input=is_input)
    if "timeout" in arguments:
        try:
            action.set_hard_timeout(float(arguments["timeout"]))
        except ValueError as e:
            msg = f"Invalid float passed to 'timeout' argument: {
                arguments['timeout']}"
            raise FunctionCallValidationError(
                msg,
            ) from e
    set_security_risk(action, arguments)
    return action


def _handle_ipython_tool(arguments: dict) -> IPythonRunCellAction:
    """Handle IPythonTool tool call."""
    if "code" not in arguments:
        msg = f'Missing required argument "code" in tool call {
            IPythonTool['function']['name']}'
        raise FunctionCallValidationError(
            msg,
        )
    action = IPythonRunCellAction(code=arguments["code"])
    set_security_risk(action, arguments)
    return action


def _handle_delegate_to_browsing_agent(arguments: dict) -> AgentDelegateAction:
    """Handle delegate_to_browsing_agent tool call."""
    return AgentDelegateAction(agent="BrowsingAgent", inputs=arguments)


def _handle_finish_tool(arguments: dict) -> AgentFinishAction:
    """Handle FinishTool tool call."""
    return AgentFinishAction(final_thought=arguments.get("message", ""))


def _handle_llm_based_file_edit_tool(arguments: dict) -> FileEditAction:
    """Handle LLMBasedFileEditTool tool call."""
    if "path" not in arguments:
        msg = f'Missing required argument "path" in tool call {
            LLMBasedFileEditTool['function']['name']}'
        raise FunctionCallValidationError(
            msg,
        )
    if "content" not in arguments:
        msg = f'Missing required argument "content" in tool call {
            LLMBasedFileEditTool['function']['name']}'
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
    valid_params = set(str_replace_editor_tool["function"]["parameters"]["properties"].keys())
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
        return FileReadAction(path=path, impl_source=FileReadSource.OH_ACI, view_range=other_kwargs.get("view_range"))

    # Remove view_range for edit commands
    other_kwargs.pop("view_range", None)

    # Filter valid editor kwargs
    valid_kwargs_for_editor = _filter_valid_editor_kwargs(other_kwargs)

    # Create and configure action
    action = FileEditAction(path=path, command=command, impl_source=FileEditSource.OH_ACI, **valid_kwargs_for_editor)
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
            BrowserTool['function']['name']}'
        raise FunctionCallValidationError(
            msg,
        )
    action = BrowseInteractiveAction(browser_actions=arguments["code"])
    set_security_risk(action, arguments)
    return action


def _handle_task_tracker_tool(arguments: dict) -> TaskTrackingAction:
    """Handle TASK_TRACKER_TOOL tool call."""
    if "command" not in arguments:
        msg = f'Missing required argument "command" in tool call {TASK_TRACKER_TOOL_NAME}'
        raise FunctionCallValidationError(msg)
    if arguments["command"] == "plan" and "task_list" not in arguments:
        msg = f'Missing required argument "task_list" for "plan" command in tool call {TASK_TRACKER_TOOL_NAME}'
        raise FunctionCallValidationError(
            msg,
        )
    raw_task_list = arguments.get("task_list", [])
    if not isinstance(raw_task_list, list):
        msg = f'Invalid format for "task_list". Expected a list but got {
            type(raw_task_list)}.'
        raise FunctionCallValidationError(
            msg,
        )
    normalized_task_list = []
    for i, task in enumerate(raw_task_list):
        if isinstance(task, dict):
            normalized_task = {
                "id": task.get(
                    "id",
                    f"task-{
                        i + 1}",
                ),
                "title": task.get("title", "Untitled task"),
                "status": task.get("status", "todo"),
                "notes": task.get("notes", ""),
            }
        else:
            logger.warning("Unexpected task format in task_list: %s - %s", type(task), task)
            msg = f"Unexpected task format in task_list: {
                type(task)}. Each task shoud be a dictionary."
            raise FunctionCallValidationError(
                msg,
            )
        normalized_task_list.append(normalized_task)
    return TaskTrackingAction(command=arguments["command"], task_list=normalized_task_list)


def _handle_mcp_tool(tool_call_name: str, arguments: dict) -> MCPAction:
    """Handle MCP tool call."""
    logger.debug("Creating MCP action for tool: %s with arguments: %s", tool_call_name, arguments)
    
    # Basic validation - ensure arguments is a dict
    if not isinstance(arguments, dict):
        logger.warning("MCP tool arguments is not a dict, got: %s", type(arguments))
        arguments = {}
    
    return MCPAction(name=tool_call_name, arguments=arguments)


def _handle_database_connect_tool(arguments: dict) -> IPythonRunCellAction:
    """Handle database_connect tool call by generating IPython code."""
    connection_name = arguments.get("connection_name")
    db_type = arguments.get("db_type")
    env_prefix = arguments.get("env_prefix")

    if not all([connection_name, db_type, env_prefix]):
        msg = "Missing required arguments: connection_name, db_type, env_prefix"
        raise FunctionCallValidationError(msg)

    # Generate Python code to connect to database in sandbox
    code = f"""
import sys
sys.path.insert(0, '/openhands/plugins/agent_skills')

from database import connect_{db_type}

# Connect to database using environment variables
result = await connect_{db_type}('{env_prefix}', '{connection_name}')
print('Database connection established:')
print(f"  Name: {{result['connection_name']}}")
print(f"  Type: {{result['db_type']}}")
if 'host' in result:
    print(f"  Host: {{result['host']}}")
if 'database' in result:
    print(f"  Database: {{result['database']}}")
"""

    action = IPythonRunCellAction(code=code.strip())
    set_security_risk(action, arguments)
    return action


def _handle_database_schema_tool(arguments: dict) -> IPythonRunCellAction:
    """Handle database_schema tool call by generating IPython code."""
    connection_name = arguments.get("connection_name")

    if not connection_name:
        msg = "Missing required argument: connection_name"
        raise FunctionCallValidationError(msg)

    # Generate Python code to fetch schema
    code = f"""
import sys
sys.path.insert(0, '/openhands/plugins/agent_skills')

from database import get_schema
import json

# Fetch database schema
schema = await get_schema('{connection_name}')
print(json.dumps(schema, indent=2))
"""

    action = IPythonRunCellAction(code=code.strip())
    set_security_risk(action, arguments)
    return action


def _handle_database_query_tool(arguments: dict) -> IPythonRunCellAction:
    """Handle database_query tool call by generating IPython code."""
    connection_name = arguments.get("connection_name")
    query = arguments.get("query", "")
    limit = arguments.get("limit", 100)

    if not connection_name or not query:
        msg = "Missing required arguments: connection_name, query"
        raise FunctionCallValidationError(msg)

    # Escape query string for Python
    query.replace("'", "\\'").replace('"', '\\"')

    # Generate Python code to execute query
    code = f"""
import sys
sys.path.insert(0, '/openhands/plugins/agent_skills')

from database import execute_query
import json

# Execute database query
result = await execute_query('{connection_name}', '''{query}''', limit={limit})

if result['success']:
    print(f"Query executed successfully in {{result['execution_time_ms']}}ms")
    print(f"Rows returned: {{result['row_count']}}")
    print()
    print("Results:")
    print(json.dumps(result['data'], indent=2))
else:
    print(f"Query failed: {{result['error']}}")
"""

    action = IPythonRunCellAction(code=code.strip())
    set_security_risk(action, arguments)
    return action


def _handle_ultimate_editor_tool(arguments: dict) -> Action:
    """Handle UltimateEditor tool call."""
    tool_name = create_ultimate_editor_tool()["function"]["name"]
    
    if "command" not in arguments:
        msg = f'Missing required argument "command" in tool call {tool_name}'
        raise FunctionCallValidationError(msg)
    
    if "file_path" not in arguments:
        msg = f'Missing required argument "file_path" in tool call {tool_name}'
        raise FunctionCallValidationError(msg)
    
    command = arguments["command"]
    file_path = arguments["file_path"]
    
    # Import the ultimate editor here to avoid circular imports
    try:
        from openhands.agenthub.codeact_agent.tools.ultimate_editor import UltimateEditor
        editor = UltimateEditor()
    except Exception as e:
        msg = f"Failed to initialize Ultimate Editor: {e}"
        raise FunctionCallValidationError(msg)
    
    # Execute the command and convert result to appropriate Action
    try:
        if command == "edit_function":
            function_name = arguments.get("function_name")
            new_body = arguments.get("new_body")
            if not function_name or not new_body:
                msg = "edit_function requires 'function_name' and 'new_body' arguments"
                raise FunctionCallValidationError(msg)
            
            result = editor.edit_function(file_path, function_name, new_body)
            # Return a FileEditAction to represent the change
            if result.success:
                return FileReadAction(path=file_path, impl_source=FileReadSource.AGENT, thought=result.message)
            else:
                return MessageAction(content=f"❌ Edit failed: {result.message}")
        
        elif command == "rename_symbol":
            old_name = arguments.get("old_name")
            new_name = arguments.get("new_name")
            if not old_name or not new_name:
                msg = "rename_symbol requires 'old_name' and 'new_name' arguments"
                raise FunctionCallValidationError(msg)
            
            result = editor.rename_symbol(file_path, old_name, new_name)
            if result.success:
                return FileReadAction(path=file_path, impl_source=FileReadSource.AGENT, thought=result.message)
            else:
                return MessageAction(content=f"❌ Rename failed: {result.message}")
        
        elif command == "find_symbol":
            symbol_name = arguments.get("symbol_name")
            if not symbol_name:
                msg = "find_symbol requires 'symbol_name' argument"
                raise FunctionCallValidationError(msg)
            
            symbol_type = arguments.get("symbol_type")
            result = editor.find_symbol(file_path, symbol_name, symbol_type)
            
            if result:
                message = f"✓ Found '{symbol_name}' in {file_path}:\n" \
                         f"  Type: {result.node_type}\n" \
                         f"  Lines: {result.line_start}-{result.line_end}"
                if result.parent_name:
                    message += f"\n  Parent: {result.parent_name}"
                return MessageAction(content=message)
            else:
                return MessageAction(content=f"❌ Symbol '{symbol_name}' not found in {file_path}")
        
        elif command == "replace_range":
            start_line = arguments.get("start_line")
            end_line = arguments.get("end_line")
            new_code = arguments.get("new_code")
            if start_line is None or end_line is None or new_code is None:
                msg = "replace_range requires 'start_line', 'end_line', and 'new_code' arguments"
                raise FunctionCallValidationError(msg)
            
            result = editor.replace_code_range(file_path, start_line, end_line, new_code)
            if result.success:
                return FileReadAction(path=file_path, impl_source=FileReadSource.AGENT, thought=result.message)
            else:
                return MessageAction(content=f"❌ Replace failed: {result.message}")
        
        elif command == "normalize_indent":
            style = arguments.get("style")
            size = arguments.get("size")
            result = editor.normalize_file_indent(file_path, style, size)
            
            if result.success:
                return FileReadAction(path=file_path, impl_source=FileReadSource.AGENT, thought=result.message)
            else:
                return MessageAction(content=f"❌ Normalization failed: {result.message}")
        
        else:
            msg = f"Unknown command '{command}' for ultimate_editor tool"
            raise FunctionCallValidationError(msg)
    
    except Exception as e:
        return MessageAction(content=f"❌ Ultimate Editor error: {str(e)}")


def _create_tool_dispatch_map() -> dict[str, callable]:
    """Create dispatch map for tool handlers."""
    return {
        create_cmd_run_tool()["function"]["name"]: _handle_cmd_run_tool,
        IPythonTool["function"]["name"]: _handle_ipython_tool,
        "delegate_to_browsing_agent": _handle_delegate_to_browsing_agent,
        FinishTool["function"]["name"]: _handle_finish_tool,
        LLMBasedFileEditTool["function"]["name"]: _handle_llm_based_file_edit_tool,
        create_str_replace_editor_tool()["function"]["name"]: _handle_str_replace_editor_tool,
        create_ultimate_editor_tool()["function"]["name"]: _handle_ultimate_editor_tool,
        ThinkTool["function"]["name"]: _handle_think_tool,
        CondensationRequestTool["function"]["name"]: _handle_condensation_request_tool,
        BrowserTool["function"]["name"]: _handle_browser_tool,
        TASK_TRACKER_TOOL_NAME: _handle_task_tracker_tool,
        "database_connect": _handle_database_connect_tool,
        "database_schema": _handle_database_schema_tool,
        "database_query": _handle_database_query_tool,
    }


def response_to_actions(response: ModelResponse, mcp_tool_names: list[str] | None = None) -> list[Action]:
    """Convert model response to actions."""
    actions: list[Action] = []
    _validate_response_choices(response)

    choice = response.choices[0]
    assistant_msg = choice.message

    if hasattr(assistant_msg, "tool_calls") and assistant_msg.tool_calls:
        actions = _process_tool_calls_to_actions(assistant_msg, response, mcp_tool_names)
    else:
        actions = _create_message_action_from_content(assistant_msg.content)

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

        _set_tool_call_metadata(action, tool_call, response, len(assistant_msg.tool_calls))
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


def _process_single_tool_call(tool_call, tool_dispatch: dict, mcp_tool_names: list[str] | None) -> Action:
    """Process a single tool call and return the corresponding action."""
    logger.debug("Tool call in function_calling.py: %s", tool_call)

    try:
        arguments = json.loads(tool_call.function.arguments)
    except json.decoder.JSONDecodeError as e:
        args_preview = tool_call.function.arguments[:100] + "..." if len(tool_call.function.arguments) > 100 else tool_call.function.arguments
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


def _set_tool_call_metadata(action: Action, tool_call, response: ModelResponse, total_calls: int) -> None:
    """Set tool call metadata for the action."""
    action.tool_call_metadata = ToolCallMetadata(
        tool_call_id=tool_call.id,
        function_name=tool_call.function.name,
        model_response=response,
        total_calls_in_response=total_calls,
    )


def _create_message_action_from_content(content) -> list[Action]:
    """Create message action from content when no tool calls are present."""
    content_str = str(content) if content else ""
    return [MessageAction(content=content_str, wait_for_response=True)]


def _set_response_id_for_actions(actions: list[Action], response: ModelResponse) -> None:
    """Set response ID for all actions."""
    for action in actions:
        action.response_id = response.id
