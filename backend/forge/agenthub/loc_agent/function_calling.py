"""This file contains the function calling implementation for different actions.

This is similar to the functionality of `CodeActResponseParser`.
"""

from __future__ import annotations

import json
from typing import TYPE_CHECKING

from forge.agenthub.codeact_agent.function_calling import combine_thought
from forge.agenthub.codeact_agent.tools import FinishTool
from forge.agenthub.loc_agent.tools import (
    SearchEntityTool,
    SearchRepoTool,
    create_explore_tree_structure_tool,
)
from forge.core.exceptions import FunctionCallNotExistsError
from forge.core.logger import forge_logger as logger
from forge.events.action import (
    Action,
    AgentFinishAction,
    IPythonRunCellAction,
    MessageAction,
)
from forge.events.tool import ToolCallMetadata, build_tool_call_metadata

if TYPE_CHECKING:
    from litellm import ChatCompletionToolParam, ModelResponse


def _extract_thought_from_message(assistant_msg) -> str:
    """Extract thought text from assistant message."""
    thought = ""
    if isinstance(assistant_msg.content, str):
        thought = assistant_msg.content
    elif isinstance(assistant_msg.content, list):
        for msg in assistant_msg.content:
            if msg["type"] == "text":
                thought += msg["text"]
    return thought


def _parse_tool_arguments(tool_call) -> dict:
    """Parse and validate tool call arguments."""
    try:
        return json.loads(tool_call.function.arguments)
    except json.decoder.JSONDecodeError as e:
        msg = f"Failed to parse tool call arguments: {tool_call.function.arguments}"
        raise RuntimeError(msg) from e


def _create_action_from_tool_call(tool_call, arguments: dict) -> Action:
    """Create appropriate action from tool call."""
    ALL_FUNCTIONS = [
        "explore_tree_structure",
        "search_code_snippets",
        "get_entity_contents",
    ]

    if tool_call.function.name in ALL_FUNCTIONS:
        func_name = tool_call.function.name
        code = f"print({func_name}(**{arguments}))"
        logger.debug("TOOL CALL: %s with code: %s", func_name, code)
        return IPythonRunCellAction(code=code)
    if tool_call.function.name == FinishTool["function"]["name"]:
        return AgentFinishAction(final_thought=arguments.get("message", ""))
    msg = f"Tool {tool_call.function.name} is not registered. (arguments: {
        arguments
    }). Please check the tool name and retry with an existing tool."
    raise FunctionCallNotExistsError(
        msg,
    )


def _process_tool_calls(
    assistant_msg, response: ModelResponse, thought: str
) -> list[Action]:
    """Process all tool calls from assistant message."""
    actions: list[Action] = []
    for i, tool_call in enumerate(assistant_msg.tool_calls):
        logger.debug("Tool call in function_calling.py: %s", tool_call)
        arguments = _parse_tool_arguments(tool_call)
        action = _create_action_from_tool_call(tool_call, arguments)

        if i == 0:
            action = combine_thought(action, thought)

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
    """Convert LLM response to agent actions.

    Processes tool calls from the model response and converts them to executable
    actions. If no tool calls present, creates a message action.

    Args:
        response: Model response from LLM
        mcp_tool_names: Optional list of MCP tool names (unused currently)

    Returns:
        List of actions to execute

    """
    actions: list[Action] = []
    _validate_response_choices(response)
    choice = response.choices[0]
    assistant_msg = getattr(choice, "message", None)
    if assistant_msg is None:
        raise RuntimeError("Model response choice is missing a message payload")

    tool_calls = getattr(assistant_msg, "tool_calls", None)
    if tool_calls:
        thought = _extract_thought_from_message(assistant_msg)
        actions = _process_tool_calls(assistant_msg, response, thought)
    else:
        actions.append(
            MessageAction(
                content=str(assistant_msg.content) if assistant_msg.content else "",
                wait_for_response=True,
            ),
        )

    for action in actions:
        action.response_id = response.id
    assert actions
    return actions


def _validate_response_choices(response: ModelResponse) -> None:
    """Validate that response has exactly one choice."""
    assert len(response.choices) == 1, "Only one choice is supported for now"


def get_tools() -> list[ChatCompletionToolParam]:
    """Get available tools for LOC agent.

    Returns:
        List of tool definitions for function calling

    """
    return [
        FinishTool,
        SearchRepoTool,
        SearchEntityTool,
        create_explore_tree_structure_tool(use_simplified_description=True),
    ]
