import sys
from typing import Any, cast
from unittest.mock import patch

import pytest
from pydantic import SecretStr

from forge.agenthub.codeact_agent.codeact_agent import CodeActAgent
from forge.core.config import AgentConfig, LLMConfig
from forge.core.config.forge_config import ForgeConfig
from forge.llm.llm import LLM
from forge.llm.llm_registry import LLMRegistry

pytestmark = pytest.mark.skipif(
    sys.platform != "win32", reason="Windows prompt refinement tests require Windows"
)


@pytest.fixture
def mock_llm():
    """Create a mock LLM for testing."""
    cfg = LLMConfig(model="gpt-4", api_key=SecretStr("test_key"))
    return LLM(config=cfg, service_id="test-service")


@pytest.fixture
def agent_config():
    """Create a basic agent config for testing."""
    return AgentConfig()


def test_codeact_agent_system_prompt_no_bash_on_windows(mock_llm, agent_config):
    """Test that CodeActAgent's system prompt doesn't contain 'bash' on Windows."""
    forge_config = ForgeConfig()
    forge_config.set_llm_config(LLMConfig())
    llm_registry = LLMRegistry(config=forge_config)
    agent = CodeActAgent(config=agent_config, llm_registry=llm_registry)
    agent.llm = mock_llm
    system_prompt = agent.prompt_manager.get_system_message()
    assert "bash" not in system_prompt.lower(), (
        f"System prompt contains 'bash' on Windows platform. It should be replaced with 'powershell'. System prompt: {system_prompt}"
    )
    assert "powershell" in system_prompt.lower(), (
        f"System prompt should contain 'powershell' on Windows platform. System prompt: {system_prompt}"
    )


def test_codeact_agent_tool_descriptions_no_bash_on_windows(mock_llm, agent_config):
    """Test that CodeActAgent's tool descriptions don't contain 'bash' on Windows."""
    forge_config = ForgeConfig()
    forge_config.set_llm_config(LLMConfig())
    llm_registry = LLMRegistry(config=forge_config)
    agent = CodeActAgent(config=agent_config, llm_registry=llm_registry)
    agent.llm = mock_llm
    tools = agent.tools
    for tool in tools:
        if tool["type"] == "function":
            function_info = tool["function"]
            description = function_info.get("description", "")
            assert "bash" not in description.lower(), f"Tool '{
                function_info['name']
            }' description contains 'bash' on Windows. Description: {description}"
            parameters = function_info.get("parameters", {})
            properties = parameters.get("properties", {})
            for param_name, param_info in properties.items():
                param_description = param_info.get("description", "")
                assert "bash" not in param_description.lower(), f"Tool '{
                    function_info['name']
                }' parameter '{
                    param_name
                }' description contains 'bash' on Windows. Parameter description: {
                    param_description
                }"


def test_in_context_learning_example_no_bash_on_windows():
    """Test that in-context learning examples don't contain 'bash' on Windows."""
    from forge.agenthub.codeact_agent.tools.bash import create_cmd_run_tool
    from forge.agenthub.codeact_agent.tools.finish import FinishTool
    from forge.agenthub.codeact_agent.tools.str_replace_editor import (
        create_str_replace_editor_tool,
    )
    from forge.llm.fn_call_converter import get_example_for_tools

    tools = cast(
        list[dict[str, Any]],
        [create_cmd_run_tool(), create_str_replace_editor_tool(), FinishTool],
    )
    example = get_example_for_tools(tools)
    assert "bash" not in example.lower(), (
        f"In-context learning example contains 'bash' on Windows platform. It should be replaced with 'powershell'. Example: {example}"
    )
    if example:
        assert "powershell" in example.lower(), (
            f"In-context learning example should contain 'powershell' on Windows platform. Example: {example}"
        )


def test_refine_prompt_function_works():
    """Test that the refine_prompt function correctly replaces 'bash' with 'powershell'."""
    from forge.agenthub.codeact_agent.tools.bash import refine_prompt

    test_prompt = "Execute a bash command to list files"
    refined_prompt = refine_prompt(test_prompt)
    assert "bash" not in refined_prompt.lower()
    assert "powershell" in refined_prompt.lower()
    assert refined_prompt == "Execute a powershell command to list files"
    test_prompt = "Use bash to run bash commands in the bash shell"
    refined_prompt = refine_prompt(test_prompt)
    assert "bash" not in refined_prompt.lower()
    assert (
        refined_prompt
        == "Use powershell to run powershell commands in the powershell shell"
    )
    test_prompt = "BASH and Bash and bash should all be replaced"
    refined_prompt = refine_prompt(test_prompt)
    assert "bash" not in refined_prompt.lower()
    assert (
        refined_prompt
        == "powershell and powershell and powershell should all be replaced"
    )
    test_prompt = "Use the execute_bash tool to run commands"
    refined_prompt = refine_prompt(test_prompt)
    assert "execute_bash" not in refined_prompt.lower()
    assert "execute_powershell" in refined_prompt.lower()
    assert refined_prompt == "Use the execute_powershell tool to run commands"
    test_prompt = "The bashful person likes bash-like syntax"
    refined_prompt = refine_prompt(test_prompt)
    assert "bashful" in refined_prompt
    assert "powershell-like" in refined_prompt
    assert refined_prompt == "The bashful person likes powershell-like syntax"


def test_refine_prompt_function_on_non_windows():
    """Test that the refine_prompt function doesn't change anything on non-Windows platforms."""
    from forge.agenthub.codeact_agent.tools.bash import refine_prompt

    with patch("forge.agenthub.codeact_agent.tools.prompt.sys.platform", "linux"):
        test_prompt = "Execute a bash command to list files"
        refined_prompt = refine_prompt(test_prompt)
        assert refined_prompt == test_prompt
        assert "bash" in refined_prompt.lower()
