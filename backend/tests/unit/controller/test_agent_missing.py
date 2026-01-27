"""Tests for missing coverage in agent.py."""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import Mock, patch

import pytest

from forge.controller.agent import Agent
from forge.core.exceptions import AgentAlreadyRegisteredError, AgentNotRegisteredError
from forge.events.action import Action


class _TestAgent(Agent):
    def __init__(self, prompt_manager=None):
        llm_registry = SimpleNamespace(
            get_llm_from_agent_config=lambda *_: SimpleNamespace(
                config=SimpleNamespace()
            )
        )
        config = SimpleNamespace(cli_mode=False)
        super().__init__(config=config, llm_registry=llm_registry)
        self._prompt_manager = prompt_manager
        self._step_called = False

    def step(self, state):
        self._step_called = True
        return Action(content="test", thought="")


def test_prompt_manager_property_raises_error():
    """Test that prompt_manager property raises ValueError when not initialized."""
    agent = _TestAgent(prompt_manager=None)
    with pytest.raises(ValueError, match="Prompt manager not initialized"):
        _ = agent.prompt_manager


def test_get_system_message_no_prompt_manager():
    """Test get_system_message when prompt_manager is falsy but not None."""
    agent = _TestAgent()
    # To test lines 104-108, we need prompt_manager to be falsy but not None.
    # The property getter only checks for None, so if we set _prompt_manager to False,
    # it will return False, and the check `if not self.prompt_manager:` will be True.
    agent._prompt_manager = False  # Falsy but not None
    result = agent.get_system_message()
    assert result is None


def test_get_system_message_exception():
    """Test get_system_message when an exception occurs."""
    agent = _TestAgent(prompt_manager=Mock())
    agent.prompt_manager.get_system_message.side_effect = Exception("test error")
    result = agent.get_system_message()
    assert result is None


def test_get_system_message_logger_exception():
    """Test get_system_message when logger.debug raises an exception."""
    agent = _TestAgent(prompt_manager=Mock())
    agent.prompt_manager.get_system_message.return_value = "test message"
    with patch("forge.controller.agent.logger.debug", side_effect=Exception("logger error")):
        result = agent.get_system_message()
        # Should still return the system message action despite logger error
        assert result is not None
        assert result.content == "test message"


def test_complete_property():
    """Test the complete property."""
    agent = _TestAgent()
    assert agent.complete is False
    agent._complete = True
    assert agent.complete is True


def test_reset():
    """Test the reset method."""
    agent = _TestAgent()
    agent._complete = True
    agent.reset()
    assert agent.complete is False


def test_register_duplicate_agent():
    """Test registering a duplicate agent raises error."""
    Agent._registry.clear()
    Agent.register("test_agent", _TestAgent)
    with pytest.raises(AgentAlreadyRegisteredError):
        Agent.register("test_agent", _TestAgent)
    Agent._registry.clear()


def test_get_cls_not_registered():
    """Test get_cls when agent is not registered."""
    Agent._registry.clear()
    with pytest.raises(AgentNotRegisteredError):
        Agent.get_cls("nonexistent")
    Agent._registry.clear()


def test_list_agents_empty_registry():
    """Test list_agents when registry is empty."""
    Agent._registry.clear()
    with pytest.raises(AgentNotRegisteredError):
        Agent.list_agents()
    Agent._registry.clear()


def test_set_mcp_tools_built_tool_none():
    """Test set_mcp_tools when _build_tool returns None."""
    agent = _TestAgent()
    tool = {
        "type": "function",
        "function": "invalid",  # This will cause _build_tool to return None
    }
    agent.set_mcp_tools([tool])
    assert len(agent.tools) == 0


def test_log_tool_update_start_exception():
    """Test _log_tool_update_start when exception occurs."""
    agent = _TestAgent()
    # Pass invalid mcp_tools to trigger exception
    invalid_tools = [object()]  # Not a dict, will cause exception
    agent._log_tool_update_start(invalid_tools)
    # Should not raise, just log with "<unavailable>"


def test_build_tool_no_function_payload():
    """Test _build_tool when function payload is not a dict."""
    agent = _TestAgent()
    tool = {
        "type": "function",
        "function": "not a dict",
    }
    result = agent._build_tool(tool)
    assert result is None


def test_build_tool_chunk_args_none():
    """Test _build_tool when _chunk_args_from_payload returns None."""
    agent = _TestAgent()
    tool = {
        "type": "function",
        "function": {
            "name": "",  # Empty name will cause _chunk_args_from_payload to return None
        },
    }
    result = agent._build_tool(tool)
    assert result is None


def test_build_tool_function_chunk_none():
    """Test _build_tool when _make_function_chunk returns None."""
    agent = _TestAgent()
    # Create a tool that will cause _make_function_chunk to fail
    tool = {
        "type": "function",
        "function": {
            "name": "test_tool",
            "description": "test",
            "parameters": {"type": "object"},
            "strict": "not a bool",  # This might cause issues
        },
    }
    # Mock make_function_chunk to return None or raise TypeError
    with patch("forge.controller.agent.make_function_chunk", side_effect=TypeError("invalid")):
        result = agent._build_tool(tool)
        assert result is None


def test_chunk_args_from_payload_invalid_name():
    """Test _chunk_args_from_payload with invalid name."""
    agent = _TestAgent()
    function_payload = {
        "name": None,  # Invalid name
    }
    result = agent._chunk_args_from_payload(function_payload, {})
    assert result is None


def test_chunk_args_from_payload_strict():
    """Test _chunk_args_from_payload with strict parameter."""
    agent = _TestAgent()
    function_payload = {
        "name": "test_tool",
        "strict": True,
    }
    result = agent._chunk_args_from_payload(function_payload, {})
    assert result is not None
    assert result.get("strict") is True


def test_make_function_chunk_typeerror():
    """Test _make_function_chunk when make_function_chunk raises TypeError."""
    agent = _TestAgent()
    chunk_kwargs = {
        "name": "test_tool",
        "strict": "invalid",  # This might cause TypeError
    }
    with patch("forge.controller.agent.make_function_chunk", side_effect=TypeError("invalid")):
        result = agent._make_function_chunk(chunk_kwargs, {})
        assert result is None


def test_get_cls_success():
    """Test get_cls when agent is registered."""
    Agent._registry.clear()
    Agent.register("test_agent", _TestAgent)
    cls = Agent.get_cls("test_agent")
    assert cls is _TestAgent
    Agent._registry.clear()


def test_list_agents_success():
    """Test list_agents when registry has agents."""
    Agent._registry.clear()
    Agent.register("test_agent1", _TestAgent)
    Agent.register("test_agent2", _TestAgent)
    agents = Agent.list_agents()
    assert "test_agent1" in agents
    assert "test_agent2" in agents
    Agent._registry.clear()


def test_set_mcp_tools_register_tool():
    """Test set_mcp_tools successfully registers a tool."""
    agent = _TestAgent()
    tool = {
        "type": "function",
        "function": {
            "name": "test_tool",
            "description": "test description",
            "parameters": {"type": "object"},
        },
    }
    agent.set_mcp_tools([tool])
    assert "test_tool" in agent.mcp_tools
    assert len(agent.tools) == 1
    assert agent.tools[0]["function"]["name"] == "test_tool"


def test_set_mcp_tools_duplicate_tool():
    """Test set_mcp_tools skips duplicate tools."""
    agent = _TestAgent()
    tool = {
        "type": "function",
        "function": {
            "name": "test_tool",
            "description": "test description",
            "parameters": {"type": "object"},
        },
    }
    # Register tool first
    agent.set_mcp_tools([tool])
    assert len(agent.tools) == 1
    # Try to register same tool again
    agent.set_mcp_tools([tool])
    # Should still be only 1 tool
    assert len(agent.tools) == 1


def test_tool_exists():
    """Test _tool_exists method."""
    agent = _TestAgent()
    tool = {
        "type": "function",
        "function": {
            "name": "test_tool",
            "description": "test description",
            "parameters": {"type": "object"},
        },
    }
    agent.set_mcp_tools([tool])
    assert agent._tool_exists("test_tool") is True
    assert agent._tool_exists("nonexistent") is False


def test_register_tool():
    """Test _register_tool method."""
    agent = _TestAgent()
    tool_param = {
        "function": {
            "name": "test_tool",
        },
    }
    agent._register_tool(tool_param, "test_tool")
    assert "test_tool" in agent.mcp_tools
    assert agent.mcp_tools["test_tool"] is tool_param
    assert tool_param in agent.tools


def test_build_tool_success():
    """Test _build_tool successfully builds a tool."""
    agent = _TestAgent()
    tool = {
        "type": "function",
        "function": {
            "name": "test_tool",
            "description": "test description",
            "parameters": {"type": "object", "properties": {}},
        },
        "extra_field": "extra_value",
    }
    # Mock make_tool_param to return an object that supports setattr
    mock_tool_param = SimpleNamespace()
    with patch("forge.controller.agent.make_tool_param", return_value=mock_tool_param):
        result = agent._build_tool(tool)
        assert result is not None
        assert hasattr(result, "extra_field")
        assert result.extra_field == "extra_value"


def test_attach_additional_fields():
    """Test _attach_additional_fields sets additional fields."""
    tool_param = SimpleNamespace()
    normalized_tool = {
        "type": "function",
        "function": {},
        "extra_field": "extra_value",
        "another_field": 123,
    }
    Agent._attach_additional_fields(tool_param, normalized_tool)
    assert hasattr(tool_param, "extra_field")
    assert tool_param.extra_field == "extra_value"
    assert hasattr(tool_param, "another_field")
    assert tool_param.another_field == 123
    # type and function should not be set
    assert not hasattr(tool_param, "type")
    assert not hasattr(tool_param, "function")

