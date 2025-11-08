"""Test for MCP tool timeout causing agent to stall indefinitely."""

import asyncio
import json
from unittest import mock
import pytest
from mcp import McpError
from forge.controller.agent import Agent
from forge.controller.agent_controller import AgentController
from forge.core.schema import AgentState
from forge.events.action.mcp import MCPAction
from forge.events.action.message import SystemMessageAction
from forge.events.event import EventSource
from forge.events.observation.mcp import MCPObservation
from forge.events.stream import EventStream
from forge.mcp_client.client import MCPClient
from forge.mcp_client.tool import MCPClientTool
from forge.mcp_client.utils import call_tool_mcp
from forge.server.services.conversation_stats import ConversationStats
from forge.storage.memory import InMemoryFileStore


class MockConfig:
    """Mock config for testing."""

    def __init__(self):
        self.max_message_chars = 10000


class MockLLM:
    """Mock LLM for testing."""

    def __init__(self):
        self.metrics = None
        self.config = MockConfig()


@pytest.fixture
def conversation_stats():
    """Create a ConversationStats fixture for testing.

    Returns:
        ConversationStats: A mock conversation stats instance.
    """
    return ConversationStats(None, "convo-id", None)


class MockAgent(Agent):
    """Mock agent for testing."""

    def __init__(self):
        self.step_called = False
        self.next_action = None
        self.llm = MockLLM()

    def step(self, *args, **kwargs):
        """Mock step method."""
        self.step_called = True
        return self.next_action

    def get_system_message(self):
        """Mock get_system_message method."""
        return SystemMessageAction(content="System message")


@pytest.mark.asyncio
async def test_mcp_tool_timeout_error_handling(conversation_stats):
    """Test that verifies MCP tool timeout errors are properly handled and returned as observations."""
    mock_client = mock.MagicMock(spec=MCPClient)

    async def mock_call_tool(*args, **kwargs):
        await asyncio.sleep(0.1)
        error = mock.MagicMock()
        error.message = "Timed out while waiting for response to ClientRequest. Waited 30.0 seconds."
        raise McpError(error)

    mock_client.call_tool.side_effect = mock_call_tool
    mock_tool = MCPClientTool(
        name="test_tool", description="Test tool", inputSchema={"type": "object", "properties": {}}, session=None
    )
    mock_client.tools = [mock_tool]
    mock_client.tool_map = {"test_tool": mock_tool}
    mock_file_store = InMemoryFileStore({})
    event_stream = EventStream(sid="test-session", file_store=mock_file_store)
    agent = MockAgent()
    controller = AgentController(
        agent=agent,
        event_stream=event_stream,
        conversation_stats=conversation_stats,
        iteration_delta=10,
        budget_per_task_delta=None,
        sid="test-session",
    )
    await controller.set_agent_state_to(AgentState.RUNNING)
    mcp_action = MCPAction(name="test_tool", arguments={"param": "value"}, thought="Testing MCP timeout handling")
    event_stream.add_event(mcp_action, EventSource.AGENT)
    controller._pending_action = mcp_action
    with mock.patch("sys.platform", "linux"):
        result = await call_tool_mcp([mock_client], mcp_action)
    assert isinstance(result, MCPObservation)
    content = json.loads(result.content)
    assert content["isError"] is True
    assert "timed out" in content["error"].lower()
    assert controller.get_agent_state() == AgentState.RUNNING
    agent.next_action = MCPAction(
        name="another_tool", arguments={"param": "value"}, thought="Another action after timeout"
    )


@pytest.mark.asyncio
async def test_mcp_tool_timeout_agent_continuation(conversation_stats):
    """Test that verifies the agent can continue processing after an MCP tool timeout."""
    mock_client = mock.MagicMock(spec=MCPClient)

    async def mock_call_tool(*args, **kwargs):
        await asyncio.sleep(0.1)
        error = mock.MagicMock()
        error.message = "Timed out while waiting for response to ClientRequest. Waited 30.0 seconds."
        raise McpError(error)

    mock_client.call_tool.side_effect = mock_call_tool
    mock_tool = MCPClientTool(
        name="test_tool", description="Test tool", inputSchema={"type": "object", "properties": {}}, session=None
    )
    mock_client.tools = [mock_tool]
    mock_client.tool_map = {"test_tool": mock_tool}
    mock_file_store = InMemoryFileStore({})
    event_stream = EventStream(sid="test-session", file_store=mock_file_store)
    agent = MockAgent()
    controller = AgentController(
        agent=agent,
        event_stream=event_stream,
        conversation_stats=conversation_stats,
        iteration_delta=10,
        budget_per_task_delta=None,
        sid="test-session",
    )
    await controller.set_agent_state_to(AgentState.RUNNING)
    mcp_action = MCPAction(name="test_tool", arguments={"param": "value"}, thought="Testing MCP timeout handling")
    event_stream.add_event(mcp_action, EventSource.AGENT)
    controller._pending_action = mcp_action

    async def fixed_call_tool_mcp(clients, action):
        try:
            await mock_client.call_tool(action.name, action.arguments)
        except McpError as e:
            error_content = json.dumps({"isError": True, "error": str(e), "content": []})
            observation = MCPObservation(content=error_content, name=action.name, arguments=action.arguments)
            setattr(observation, "_cause", action.id)
            return observation

    with mock.patch("forge.mcp_client.utils.call_tool_mcp", side_effect=fixed_call_tool_mcp):
        result = await fixed_call_tool_mcp([mock_client], mcp_action)
        assert isinstance(result, MCPObservation)
        content = json.loads(result.content)
        assert content["isError"] is True
        assert "timed out" in content["error"].lower()
        event_stream.add_event(result, EventSource.ENVIRONMENT)
        controller._pending_action = None
        assert controller.get_agent_state() == AgentState.RUNNING
        agent.next_action = MCPAction(
            name="another_tool", arguments={"param": "value"}, thought="Another action after timeout"
        )
        await controller._step()
        assert agent.step_called
