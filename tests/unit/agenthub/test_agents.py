from typing import Union
from unittest.mock import Mock
import pytest
from litellm import ChatCompletionMessageToolCall
from forge.agenthub.codeact_agent.codeact_agent import CodeActAgent
from forge.agenthub.codeact_agent.function_calling import response_to_actions as codeact_response_to_actions
from forge.agenthub.codeact_agent.tools import (
    BrowserTool,
    IPythonTool,
    LLMBasedFileEditTool,
    ThinkTool,
    create_cmd_run_tool,
    create_str_replace_editor_tool,
)
from forge.agenthub.codeact_agent.tools.browser import _BROWSER_DESCRIPTION, _BROWSER_TOOL_DESCRIPTION
from forge.agenthub.readonly_agent.function_calling import response_to_actions as readonly_response_to_actions
from forge.agenthub.readonly_agent.readonly_agent import ReadOnlyAgent
from forge.agenthub.readonly_agent.tools import GlobTool, GrepTool
from forge.controller.state.state import State
from forge.core.config import AgentConfig, LLMConfig
from forge.core.config.forge_config import ForgeConfig
from forge.core.exceptions import FunctionCallNotExistsError
from forge.core.message import ImageContent, Message, TextContent
from forge.events.action import CmdRunAction, MessageAction
from forge.events.action.message import SystemMessageAction
from forge.events.event import EventSource
from forge.events.observation.commands import CmdOutputObservation
from forge.events.tool import ToolCallMetadata
from forge.llm.llm_registry import LLMRegistry
from forge.memory.condenser import View


@pytest.fixture
def create_llm_registry():

    def _get_registry(llm_config):
        config = ForgeConfig()
        config.set_llm_config(llm_config)
        return LLMRegistry(config=config)

    return _get_registry


@pytest.fixture(params=["CodeActAgent", "ReadOnlyAgent"])
def agent_class(request):
    if request.param == "CodeActAgent":
        return CodeActAgent
    from forge.agenthub.readonly_agent.readonly_agent import ReadOnlyAgent

    return ReadOnlyAgent


@pytest.fixture
def agent(agent_class, create_llm_registry) -> Union[CodeActAgent, ReadOnlyAgent]:
    llm_config = LLMConfig(model="gpt-4o", api_key="test_key")
    config = AgentConfig()
    agent = agent_class(config=config, llm_registry=create_llm_registry(llm_config))
    agent.llm = Mock()
    agent.llm.config = Mock()
    agent.llm.config.max_message_chars = 1000
    return agent


def test_agent_with_default_config_has_default_tools(create_llm_registry):
    llm_config = LLMConfig(model="gpt-4o", api_key="test_key")
    config = AgentConfig()
    codeact_agent = CodeActAgent(config=config, llm_registry=create_llm_registry(llm_config))
    assert len(codeact_agent.tools) > 0
    default_tool_names = [tool["function"]["name"] for tool in codeact_agent.tools]
    required_tools = {"execute_bash", "execute_ipython_cell", "finish", "str_replace_editor", "think"}
    import platform

    if platform.system() != "Windows":
        required_tools.add("browser")
    assert required_tools.issubset(default_tool_names)


@pytest.fixture
def mock_state() -> State:
    state = Mock(spec=State)
    state.history = []
    state.extra_data = {}
    return state


def test_reset(agent):
    action = MessageAction(content="test")
    action._source = EventSource.AGENT
    agent.pending_actions.append(action)
    mock_state = Mock(spec=State)
    initial_user_message = MessageAction(content="Initial user message")
    initial_user_message._source = EventSource.USER
    mock_state.history = [initial_user_message]
    agent.reset()
    assert len(agent.pending_actions) == 0


def test_step_with_pending_actions(agent):
    pending_action = MessageAction(content="test")
    pending_action._source = EventSource.AGENT
    agent.pending_actions.append(pending_action)
    mock_state = Mock(spec=State)
    initial_user_message = MessageAction(content="Initial user message")
    initial_user_message._source = EventSource.USER
    mock_state.history = [initial_user_message]
    result = agent.step(mock_state)
    assert result == pending_action
    assert len(agent.pending_actions) == 0


def test_cmd_run_tool():
    CmdRunTool = create_cmd_run_tool()
    assert CmdRunTool["type"] == "function"
    assert CmdRunTool["function"]["name"] == "execute_bash"
    assert "command" in CmdRunTool["function"]["parameters"]["properties"]
    assert "security_risk" in CmdRunTool["function"]["parameters"]["properties"]
    assert CmdRunTool["function"]["parameters"]["required"] == ["command", "security_risk"]


def test_ipython_tool():
    assert IPythonTool["type"] == "function"
    assert IPythonTool["function"]["name"] == "execute_ipython_cell"
    assert "code" in IPythonTool["function"]["parameters"]["properties"]
    assert "security_risk" in IPythonTool["function"]["parameters"]["properties"]
    assert IPythonTool["function"]["parameters"]["required"] == ["code", "security_risk"]


def test_llm_based_file_edit_tool():
    assert LLMBasedFileEditTool["type"] == "function"
    assert LLMBasedFileEditTool["function"]["name"] == "edit_file"
    properties = LLMBasedFileEditTool["function"]["parameters"]["properties"]
    assert "path" in properties
    assert "content" in properties
    assert "start" in properties
    assert "end" in properties
    assert "security_risk" in properties
    assert LLMBasedFileEditTool["function"]["parameters"]["required"] == ["path", "content", "security_risk"]


def test_str_replace_editor_tool():
    StrReplaceEditorTool = create_str_replace_editor_tool()
    assert StrReplaceEditorTool["type"] == "function"
    assert StrReplaceEditorTool["function"]["name"] == "str_replace_editor"
    properties = StrReplaceEditorTool["function"]["parameters"]["properties"]
    assert "command" in properties
    assert "path" in properties
    assert "file_text" in properties
    assert "old_str" in properties
    assert "new_str" in properties
    assert "insert_line" in properties
    assert "security_risk" in properties
    assert StrReplaceEditorTool["function"]["parameters"]["required"] == ["command", "path", "security_risk"]


def _validate_browser_tool_basic_structure():
    """Validate basic structure of browser tool."""
    assert BrowserTool["type"] == "function"
    assert BrowserTool["function"]["name"] == "browser"
    assert "code" in BrowserTool["function"]["parameters"]["properties"]
    assert "security_risk" in BrowserTool["function"]["parameters"]["properties"]
    assert BrowserTool["function"]["parameters"]["required"] == ["code", "security_risk"]


def _validate_browser_tool_description():
    """Validate browser tool description contains all required methods."""
    description = _BROWSER_TOOL_DESCRIPTION
    required_methods = [
        "goto(",
        "go_back()",
        "go_forward()",
        "noop(",
        "scroll(",
        "fill(",
        "select_option(",
        "click(",
        "dblclick(",
        "hover(",
        "press(",
        "focus(",
        "clear(",
        "drag_and_drop(",
        "upload_file(",
    ]
    for method in required_methods:
        assert method in description


def _validate_browser_tool_parameters():
    """Validate browser tool parameters structure."""
    assert BrowserTool["function"]["description"] == _BROWSER_DESCRIPTION
    assert BrowserTool["function"]["parameters"]["type"] == "object"
    assert "code" in BrowserTool["function"]["parameters"]["properties"]
    assert BrowserTool["function"]["parameters"]["required"] == ["code", "security_risk"]
    assert BrowserTool["function"]["parameters"]["properties"]["code"]["type"] == "string"
    assert "description" in BrowserTool["function"]["parameters"]["properties"]["code"]


def test_browser_tool():
    """Test browser tool structure and description."""
    # Validate basic structure
    _validate_browser_tool_basic_structure()

    # Validate description contains all required methods
    _validate_browser_tool_description()

    # Validate parameters structure
    _validate_browser_tool_parameters()


def test_response_to_actions_invalid_tool():
    mock_response = Mock()
    mock_response.choices = [Mock()]
    mock_response.choices[0].message = Mock()
    mock_response.choices[0].message.content = "Invalid tool"
    mock_response.choices[0].message.tool_calls = [Mock()]
    mock_response.choices[0].message.tool_calls[0].id = "tool_call_10"
    mock_response.choices[0].message.tool_calls[0].function = Mock()
    mock_response.choices[0].message.tool_calls[0].function.name = "invalid_tool"
    mock_response.choices[0].message.tool_calls[0].function.arguments = "{}"
    with pytest.raises(FunctionCallNotExistsError):
        codeact_response_to_actions(mock_response)
    with pytest.raises(FunctionCallNotExistsError):
        readonly_response_to_actions(mock_response)


def test_step_with_no_pending_actions(mock_state: State, create_llm_registry):
    mock_response = Mock()
    mock_response.id = "mock_id"
    mock_response.total_calls_in_response = 1
    mock_response.choices = [Mock()]
    mock_response.choices[0].message = Mock()
    mock_response.choices[0].message.content = "Task completed"
    mock_response.choices[0].message.tool_calls = []
    mock_config = Mock()
    mock_config.model = "mock_model"
    llm = Mock()
    llm.config = mock_config
    llm.completion = Mock(return_value=mock_response)
    llm.is_function_calling_active = Mock(return_value=True)
    llm.is_caching_prompt_active = Mock(return_value=False)
    llm.format_messages_for_llm = Mock(return_value=[])
    llm_config = LLMConfig(model="gpt-4o", api_key="test_key")
    config = AgentConfig()
    config.enable_prompt_extensions = False
    agent = CodeActAgent(config=config, llm_registry=create_llm_registry(llm_config))
    agent.llm = llm
    mock_state.latest_user_message = None
    mock_state.latest_user_message_id = None
    mock_state.latest_user_message_timestamp = None
    mock_state.latest_user_message_cause = None
    mock_state.latest_user_message_timeout = None
    mock_state.latest_user_message_llm_metrics = None
    mock_state.latest_user_message_tool_call_metadata = None
    initial_user_message = MessageAction(content="Initial user message")
    initial_user_message._source = EventSource.USER
    mock_state.history = [initial_user_message]
    mock_view = View(events=mock_state.history)
    mock_state.view = mock_view
    action = agent.step(mock_state)
    assert isinstance(action, MessageAction)
    assert action.content == "Task completed"


@pytest.mark.parametrize("agent_type", ["CodeActAgent", "ReadOnlyAgent"])
def test_correct_tool_description_loaded_based_on_model_name(agent_type, create_llm_registry):
    """Tests that the simplified tool descriptions are loaded for specific models."""
    o3_mock_config = LLMConfig(model="mock_o3_model", api_key="test_key")
    if agent_type == "CodeActAgent":
        from forge.agenthub.codeact_agent.codeact_agent import CodeActAgent

        agent_class = CodeActAgent
    else:
        from forge.agenthub.readonly_agent.readonly_agent import ReadOnlyAgent

        agent_class = ReadOnlyAgent
    agent = agent_class(config=AgentConfig(), llm_registry=create_llm_registry(o3_mock_config))
    for tool in agent.tools:
        assert len(tool["function"]["description"]) < 2048
    sonnect_mock_config = LLMConfig(model="mock_sonnet_model", api_key="test_key")
    agent = agent_class(config=AgentConfig(), llm_registry=create_llm_registry(sonnect_mock_config))
    if agent_type == "CodeActAgent":
        assert any((len(tool["function"]["description"]) > 1024 for tool in agent.tools))


def test_mismatched_tool_call_events_and_auto_add_system_message(agent, mock_state: State):
    """Tests that the agent can convert mismatched tool call events (i.e., an observation with no corresponding action) into messages.

    This also tests that the system message is automatically added to the event stream if SystemMessageAction is not present.
    """
    tool_call_metadata = Mock(
        spec=ToolCallMetadata,
        model_response=Mock(
            id="model_response_0",
            choices=[
                Mock(
                    message=Mock(
                        role="assistant",
                        content="",
                        tool_calls=[Mock(spec=ChatCompletionMessageToolCall, id="tool_call_0")],
                    )
                )
            ],
        ),
        tool_call_id="tool_call_0",
        function_name="foo",
    )
    action = CmdRunAction("foo")
    action._source = EventSource.AGENT
    action.tool_call_metadata = tool_call_metadata
    observation = CmdOutputObservation(content="", command_id=0, command="foo")
    observation.tool_call_metadata = tool_call_metadata
    initial_user_message = MessageAction(content="Initial user message")
    initial_user_message._source = EventSource.USER
    mock_state.history = [initial_user_message, action, observation]
    messages = agent._get_messages(mock_state.history, initial_user_message)
    assert len(messages) == 4
    assert messages[0].role == "system"
    assert messages[1].role == "user"
    assert messages[2].role == "assistant"
    assert messages[3].role == "tool"
    mock_state.history = [initial_user_message, observation, action]
    messages = agent._get_messages(mock_state.history, initial_user_message)
    assert len(messages) == 4
    assert messages[0].role == "system"
    assert messages[1].role == "user"
    mock_state.history = [initial_user_message, action]
    messages = agent._get_messages(mock_state.history, initial_user_message)
    assert len(messages) == 2
    assert messages[0].role == "system"
    assert messages[1].role == "user"
    mock_state.history = [initial_user_message, observation]
    messages = agent._get_messages(mock_state.history, initial_user_message)
    assert len(messages) == 2
    assert messages[0].role == "system"
    assert messages[1].role == "user"


def test_grep_tool():
    assert GrepTool["type"] == "function"
    assert GrepTool["function"]["name"] == "grep"
    properties = GrepTool["function"]["parameters"]["properties"]
    assert "pattern" in properties
    assert "path" in properties
    assert "include" in properties
    assert GrepTool["function"]["parameters"]["required"] == ["pattern"]


def test_glob_tool():
    assert GlobTool["type"] == "function"
    assert GlobTool["function"]["name"] == "glob"
    properties = GlobTool["function"]["parameters"]["properties"]
    assert "pattern" in properties
    assert "path" in properties
    assert GlobTool["function"]["parameters"]["required"] == ["pattern"]


def test_think_tool():
    assert ThinkTool["type"] == "function"
    assert ThinkTool["function"]["name"] == "think"
    properties = ThinkTool["function"]["parameters"]["properties"]
    assert "thought" in properties
    assert ThinkTool["function"]["parameters"]["required"] == ["thought"]


def test_enhance_messages_adds_newlines_between_consecutive_user_messages(agent: CodeActAgent):
    """Test that _enhance_messages adds newlines between consecutive user messages."""
    messages = [
        Message(role="user", content=[TextContent(text="First user message")]),
        Message(role="user", content=[TextContent(text="Second user message")]),
        Message(role="assistant", content=[TextContent(text="Assistant response")]),
        Message(role="user", content=[TextContent(text="Third user message")]),
        Message(
            role="user",
            content=[
                ImageContent(image_urls=["https://example.com/image.jpg"]),
                TextContent(text="Fourth user message with image"),
            ],
        ),
        Message(role="user", content=[ImageContent(image_urls=["https://example.com/another-image.jpg"])]),
    ]
    enhanced_messages = agent.conversation_memory._apply_user_message_formatting(messages)
    assert enhanced_messages[1].content[0].text.startswith("\n\n")
    assert enhanced_messages[1].content[0].text == "\n\nSecond user message"
    assert not enhanced_messages[3].content[0].text.startswith("\n\n")
    assert enhanced_messages[3].content[0].text == "Third user message"
    assert enhanced_messages[4].content[1].text.startswith("\n\n")
    assert enhanced_messages[4].content[1].text == "\n\nFourth user message with image"
    assert len(enhanced_messages[5].content) == 1
    assert isinstance(enhanced_messages[5].content[0], ImageContent)


def test_get_system_message(create_llm_registry):
    """Test that the Agent.get_system_message method returns a SystemMessageAction."""
    config = AgentConfig()
    llm_config = LLMConfig(model="gpt-4o", api_key="test_key")
    agent = CodeActAgent(config=config, llm_registry=create_llm_registry(llm_config))
    result = agent.get_system_message()
    assert isinstance(result, SystemMessageAction)
    assert "You are Forge agent" in result.content
    assert len(result.tools) > 0
    assert any((tool["function"]["name"] == "execute_bash" for tool in result.tools))
    assert result._source == EventSource.AGENT


def test_step_raises_error_if_no_initial_user_message(agent: CodeActAgent, mock_state: State):
    """Tests that step raises ValueError if the initial user message is not found."""
    assistant_message = MessageAction(content="Assistant message")
    assistant_message._source = EventSource.AGENT
    mock_state.history = [assistant_message]
    agent.condenser = Mock()
    agent.condenser.condensed_history.return_value = View(events=mock_state.history)
    with pytest.raises(ValueError, match="Initial user message not found"):
        agent.step(mock_state)
