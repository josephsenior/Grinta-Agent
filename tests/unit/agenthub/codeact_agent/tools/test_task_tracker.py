"""Tests for task tracker tool builder."""

from __future__ import annotations

from forge.agenthub.codeact_agent.tools.task_tracker import create_task_tracker_tool
from forge.llm.tool_names import TASK_TRACKER_TOOL_NAME


def test_create_task_tracker_tool_detailed_description() -> None:
    tool = create_task_tracker_tool()
    assert tool["type"] == "function"
    assert tool["function"]["name"] == TASK_TRACKER_TOOL_NAME
    assert "structured task management" in tool["function"]["description"]
    assert "plan" in tool["function"]["parameters"]["properties"]["command"]["enum"]


def test_create_task_tracker_tool_short_description() -> None:
    tool = create_task_tracker_tool(use_short_description=True)
    assert "structured task management" in tool["function"]["description"]
    # Short description should be shorter than detailed one
    detailed = create_task_tracker_tool()
    assert len(tool["function"]["description"]) < len(detailed["function"]["description"])

