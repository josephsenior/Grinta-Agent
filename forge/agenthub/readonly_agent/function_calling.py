"""This file contains the function calling implementation for different actions.

This is similar to the functionality of `CodeActResponseParser`.
"""

from __future__ import annotations

import json
import shlex
from typing import TYPE_CHECKING

from forge.agenthub.codeact_agent.function_calling import combine_thought
from forge.agenthub.codeact_agent.tools import FinishTool, ThinkTool
from forge.agenthub.readonly_agent.tools import GlobTool, GrepTool, ViewTool
from forge.core.exceptions import (
    FunctionCallNotExistsError,
    FunctionCallValidationError,
)
from forge.core.logger import forge_logger as logger
from forge.events.action import (
    Action,
    AgentFinishAction,
    AgentThinkAction,
    CmdRunAction,
    FileReadAction,
    MCPAction,
    MessageAction,
)
from forge.events.event import FileReadSource
from forge.events.tool import ToolCallMetadata, build_tool_call_metadata

if TYPE_CHECKING:
    from litellm import ChatCompletionToolParam, ModelResponse


def grep_to_cmdrun(
    pattern: str, path: str | None = None, include: str | None = None
) -> str:
    """Convert grep tool arguments to a shell command string.

    Args:
        pattern: The regex pattern to search for in file contents
        path: The directory to search in (optional)
        include: Optional file pattern to filter which files to search (e.g., "*.js")

    Returns:
        A properly escaped shell command string for ripgrep

    """
    quoted_pattern = shlex.quote(pattern)
    path_arg = shlex.quote(path) if path else "."
    rg_cmd = f"rg -li {quoted_pattern} --sortr=modified"
    if include:
        quoted_include = shlex.quote(include)
        rg_cmd += f" --glob {quoted_include}"
    complete_cmd = f"{rg_cmd} {path_arg} | head -n 100"
    echo_cmd = f'echo "Below are the execution results of the search command: {complete_cmd}\n"; '
    return echo_cmd + complete_cmd


def glob_to_cmdrun(pattern: str, path: str = ".") -> str:
    """Convert glob tool arguments to a shell command string.

    Args:
        pattern: The glob pattern to match files (e.g., "**/*.js")
        path: The directory to search in (defaults to current directory)

    Returns:
        A properly escaped shell command string for ripgrep implementing glob

    """
    quoted_path = shlex.quote(path)
    quoted_pattern = shlex.quote(pattern)
    rg_cmd = f"rg --files {quoted_path} -g {quoted_pattern} --sortr=modified"
    sort_and_limit_cmd = " | head -n 100"
    complete_cmd = f"{rg_cmd}{sort_and_limit_cmd}"
    echo_cmd = f'echo "Below are the execution results of the glob command: {complete_cmd}\n"; '
    return echo_cmd + complete_cmd


def _extract_thought_from_content(content) -> str:
    """Extract thought text from assistant message content."""
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        return "".join(msg["text"] for msg in content if msg["type"] == "text")
    return ""


def _parse_tool_call_arguments(tool_call) -> dict:
    """Parse tool call arguments from JSON."""
    try:
        return json.loads(tool_call.function.arguments)
    except json.decoder.JSONDecodeError as e:
        msg = f"Failed to parse tool call arguments: {tool_call.function.arguments}"
        raise FunctionCallValidationError(msg) from e


def _create_finish_action(arguments: dict) -> Action:
    """Create a finish action from arguments."""
    return AgentFinishAction(final_thought=arguments.get("message", ""))


def _create_view_action(arguments: dict) -> Action:
    """Create a view action from arguments."""
    if "path" not in arguments:
        msg = f'Missing required argument "path" in tool call {
            ViewTool["function"]["name"]
        }'
        raise FunctionCallValidationError(
            msg,
        )
    return FileReadAction(
        path=arguments["path"],
        impl_source=FileReadSource.OH_ACI,
        view_range=arguments.get("view_range"),
    )


def _create_think_action(arguments: dict) -> Action:
    """Create a think action from arguments."""
    return AgentThinkAction(thought=arguments.get("thought", ""))


def _create_grep_action(arguments: dict) -> Action:
    """Create a grep action from arguments."""
    if "pattern" not in arguments:
        msg = f'Missing required argument "pattern" in tool call {
            GrepTool["function"]["name"]
        }'
        raise FunctionCallValidationError(
            msg,
        )

    pattern = arguments["pattern"]
    path = arguments.get("path")
    include = arguments.get("include")
    grep_cmd = grep_to_cmdrun(pattern, path, include)
    return CmdRunAction(command=grep_cmd, is_input=False)


def _create_glob_action(arguments: dict) -> Action:
    """Create a glob action from arguments."""
    if "pattern" not in arguments:
        msg = f'Missing required argument "pattern" in tool call {
            GlobTool["function"]["name"]
        }'
        raise FunctionCallValidationError(
            msg,
        )

    pattern = arguments["pattern"]
    path = arguments.get("path", ".")
    glob_cmd = glob_to_cmdrun(pattern, path)
    return CmdRunAction(command=glob_cmd, is_input=False)


def _create_mcp_action(tool_call, arguments: dict) -> Action:
    """Create an MCP action from tool call and arguments."""
    return MCPAction(name=tool_call.function.name, arguments=arguments)


def _create_action_from_tool_call(
    tool_call, mcp_tool_names: list[str] | None
) -> Action:
    """Create an action from a tool call."""
    arguments = _parse_tool_call_arguments(tool_call)
    function_name = tool_call.function.name

    if function_name == FinishTool["function"]["name"]:
        return _create_finish_action(arguments)
    if function_name == ViewTool["function"]["name"]:
        return _create_view_action(arguments)
    if function_name == ThinkTool["function"]["name"]:
        return _create_think_action(arguments)
    if function_name == GrepTool["function"]["name"]:
        return _create_grep_action(arguments)
    if function_name == GlobTool["function"]["name"]:
        return _create_glob_action(arguments)
    if mcp_tool_names and function_name in mcp_tool_names:
        return _create_mcp_action(tool_call, arguments)
    msg = f"Tool {function_name} is not registered. (arguments: {arguments}). Please check the tool name and retry with an existing tool."
    raise FunctionCallNotExistsError(
        msg,
    )


def _process_tool_calls(
    assistant_msg, response: ModelResponse, mcp_tool_names: list[str] | None
) -> list[Action]:
    """Process tool calls and return actions."""
    actions: list[Action] = []
    thought = _extract_thought_from_content(assistant_msg.content)

    for i, tool_call in enumerate(assistant_msg.tool_calls):
        logger.debug("Tool call in function_calling.py: %s", tool_call)

        action = _create_action_from_tool_call(tool_call, mcp_tool_names)

        # Add thought to first action
        if i == 0:
            action = combine_thought(action, thought)

        # Add tool call metadata
        action.tool_call_metadata = build_tool_call_metadata(
            function_name=tool_call.function.name,
            tool_call_id=tool_call.id,
            response_obj=response,
            total_calls_in_response=len(assistant_msg.tool_calls),
        )

        actions.append(action)

    return actions


def response_to_actions(
    response: ModelResponse, mcp_tool_names: list[str] | None = None
) -> list[Action]:
    """Convert model response to actions."""
    _validate_response_choices(response)

    choice = response.choices[0]
    assistant_msg = getattr(choice, "message", None)
    if assistant_msg is None:
        raise FunctionCallValidationError(
            "Model response choice is missing a message payload"
        )

    tool_calls = getattr(assistant_msg, "tool_calls", None)
    if tool_calls:
        actions = _process_tool_calls(assistant_msg, response, mcp_tool_names)
    else:
        content = getattr(assistant_msg, "content", None)
        text_content = str(content) if content else ""
        actions = [MessageAction(content=text_content, wait_for_response=True)]

    for action in actions:
        action.response_id = response.id

    assert actions
    return actions


def _validate_response_choices(response: ModelResponse) -> None:
    """Validate that response has exactly one choice."""
    assert len(response.choices) == 1, "Only one choice is supported for now"


def get_tools() -> list[ChatCompletionToolParam]:
    """Get available tools for readonly agent.

    Returns:
        List of tool definitions including Think, Finish, Grep, Glob, and View tools

    """
    return [ThinkTool, FinishTool, GrepTool, GlobTool, ViewTool]
