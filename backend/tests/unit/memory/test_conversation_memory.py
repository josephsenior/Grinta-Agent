import os
import shutil
from types import SimpleNamespace
from unittest.mock import MagicMock, Mock
import pytest
from litellm import ChatCompletionMessageToolCall
from forge.controller.state.state import State
from forge.core.config.agent_config import AgentConfig
from forge.core.message import ImageContent, Message, TextContent
from forge.events.action import (
    AgentFinishAction,
    AgentThinkAction,
    CmdRunAction,
    MessageAction,
)
from forge.events.action.message import SystemMessageAction
from forge.events.event import (
    Event,
    EventSource,
    FileEditSource,
    FileReadSource,
    RecallType,
)
from forge.events.observation import CmdOutputObservation
from forge.events.observation.agent import MicroagentKnowledge, RecallObservation
from forge.events.observation.browse import BrowserOutputObservation
from forge.events.observation.commands import (
    CmdOutputMetadata,
    IPythonRunCellObservation,
)
from forge.events.observation.delegate import AgentDelegateObservation
from forge.events.observation.error import ErrorObservation
from forge.events.observation.files import FileEditObservation, FileReadObservation
from forge.events.observation.reject import UserRejectObservation
from forge.events.tool import ToolCallMetadata
from forge.memory.conversation_memory import ConversationMemory
from forge.utils.prompt import (
    ConversationInstructions,
    PromptManager,
    RepositoryInfo,
    RuntimeInfo,
)


@pytest.fixture
def agent_config():
    return AgentConfig(
        enable_prompt_extensions=True,
        enable_som_visual_browsing=True,
        disabled_microagents=["disabled_agent"],
    )


@pytest.fixture
def conversation_memory(agent_config):
    prompt_manager = MagicMock(spec=PromptManager)
    prompt_manager.get_system_message.return_value = "System message"
    prompt_manager.build_workspace_context.return_value = (
        "Formatted repository and runtime info"
    )

    def build_microagent_info(triggered_agents):
        if not triggered_agents:
            return ""
        return "\n".join((agent.content for agent in triggered_agents))

    prompt_manager.build_microagent_info.side_effect = build_microagent_info
    return ConversationMemory(agent_config, prompt_manager)


@pytest.fixture
def prompt_dir(tmp_path):
    shutil.copytree(
        "Forge/agenthub/codeact_agent/prompts", tmp_path, dirs_exist_ok=True
    )
    return tmp_path


@pytest.fixture
def mock_state():
    state = MagicMock(spec=State)
    state.history = []
    return state


@pytest.fixture
def mock_prompt_manager():
    return MagicMock()


def _make_memory(config_overrides=None):
    base_config = {
        "enable_vector_memory": False,
        "enable_hybrid_retrieval": False,
        "enable_prompt_extensions": True,
        "enable_prompt_caching": True,
        "enable_som_visual_browsing": True,
        "disabled_microagents": [],
        "cli_mode": False,
    }
    if config_overrides:
        base_config.update(config_overrides)
    config = SimpleNamespace(**base_config)
    prompt_manager = MagicMock(spec=PromptManager)
    prompt_manager.get_system_message.return_value = "System message"
    prompt_manager.build_workspace_context.return_value = "context"
    prompt_manager.build_microagent_info.return_value = "microagents"
    return ConversationMemory(config, prompt_manager)


def test_conversation_memory_initializes_vector_store(monkeypatch):
    config = SimpleNamespace(
        enable_vector_memory=True,
        enable_hybrid_retrieval=False,
        enable_prompt_extensions=True,
        enable_som_visual_browsing=False,
        disabled_microagents=[],
    )
    prompt_manager = MagicMock(spec=PromptManager)
    stub_store = SimpleNamespace(stats=lambda: {"backend": "stub"})
    calls = {}

    def factory(*args, **kwargs):
        calls["called"] = True
        return stub_store

    monkeypatch.setattr(
        "forge.memory.enhanced_vector_store.EnhancedVectorStore", factory
    )
    memory = ConversationMemory(config, prompt_manager)
    assert calls["called"]
    assert memory.vector_store is stub_store


def test_conversation_memory_vector_store_failure(monkeypatch):
    config = SimpleNamespace(
        enable_vector_memory=True,
        enable_hybrid_retrieval=True,
        enable_prompt_extensions=True,
        enable_som_visual_browsing=False,
        disabled_microagents=[],
    )
    prompt_manager = MagicMock(spec=PromptManager)

    def failing(*args, **kwargs):
        raise RuntimeError("boom")

    monkeypatch.setattr(
        "forge.memory.enhanced_vector_store.EnhancedVectorStore", failing
    )
    memory = ConversationMemory(config, prompt_manager)
    assert memory.vector_store is None


def test_apply_prompt_caching_disabled():
    memory = _make_memory({"enable_prompt_caching": False})
    messages = [Message(role="user", content=[TextContent(text="hello")])]
    memory.apply_prompt_caching(messages)
    assert messages[0].content[0].cache_prompt is False


def test_process_events_with_message_action(conversation_memory):
    """Test that MessageAction is processed correctly."""
    system_message = SystemMessageAction(content="System message")
    system_message._source = EventSource.AGENT
    user_message = MessageAction(content="Hello")
    user_message._source = EventSource.USER
    assistant_message = MessageAction(content="Hi there")
    assistant_message._source = EventSource.AGENT
    messages = conversation_memory.process_events(
        condensed_history=[system_message, user_message, assistant_message],
        initial_user_action=user_message,
        max_message_chars=None,
        vision_is_active=False,
    )
    assert len(messages) == 3
    assert messages[0].role == "system"
    assert messages[0].content[0].text == "System message"


def test_ensure_system_message_adds_if_missing(conversation_memory):
    """Test that _ensure_system_message adds a system message if none exists."""
    user_message = MessageAction(content="User message")
    user_message._source = EventSource.USER
    events = [user_message]
    conversation_memory._ensure_system_message(events)
    assert len(events) == 2
    assert isinstance(events[0], SystemMessageAction)
    assert events[0].content == "System message"
    assert isinstance(events[1], MessageAction)


def test_ensure_system_message_does_nothing_if_present(conversation_memory):
    """Test that _ensure_system_message does nothing if a system message is already present."""
    original_system_message = SystemMessageAction(content="Existing system message")
    user_message = MessageAction(content="User message")
    user_message._source = EventSource.USER
    events = [original_system_message, user_message]
    original_events = list(events)
    conversation_memory._ensure_system_message(events)
    assert events == original_events


@pytest.fixture
def initial_user_action():
    msg = MessageAction(content="Initial User Message")
    msg._source = EventSource.USER
    return msg


def test_ensure_initial_user_message_adds_if_only_system(
    conversation_memory, initial_user_action
):
    """Test adding the initial user message when only the system message exists."""
    system_message = SystemMessageAction(content="System")
    system_message._source = EventSource.AGENT
    events = [system_message]
    conversation_memory._ensure_initial_user_message(events, initial_user_action)
    assert len(events) == 2
    assert events[0] == system_message
    assert events[1] == initial_user_action


def test_ensure_initial_user_message_correct_already_present(
    conversation_memory, initial_user_action
):
    """Test that nothing changes if the correct initial user message is at index 1."""
    system_message = SystemMessageAction(content="System")
    agent_message = MessageAction(content="Assistant")
    agent_message._source = EventSource.USER
    events = [system_message, initial_user_action, agent_message]
    original_events = list(events)
    conversation_memory._ensure_initial_user_message(events, initial_user_action)
    assert events == original_events


def test_ensure_initial_user_message_incorrect_at_index_1(
    conversation_memory, initial_user_action
):
    """Test inserting the correct initial user message when an incorrect message is at index 1."""
    system_message = SystemMessageAction(content="System")
    incorrect_second_message = MessageAction(content="Assistant")
    incorrect_second_message._source = EventSource.AGENT
    events = [system_message, incorrect_second_message]
    conversation_memory._ensure_initial_user_message(events, initial_user_action)
    assert len(events) == 3
    assert events[0] == system_message
    assert events[1] == initial_user_action
    assert events[2] == incorrect_second_message


def test_ensure_initial_user_message_correct_present_later(
    conversation_memory, initial_user_action
):
    """Test inserting the correct initial user message at index 1 even if it exists later."""
    system_message = SystemMessageAction(content="System")
    incorrect_second_message = MessageAction(content="Assistant")
    incorrect_second_message._source = EventSource.AGENT
    events = [system_message, incorrect_second_message]
    conversation_memory._ensure_system_message(events)
    conversation_memory._ensure_initial_user_message(events, initial_user_action)
    assert len(events) == 3
    assert events[0] == system_message
    assert events[1] == initial_user_action
    assert events[2] == incorrect_second_message


def test_ensure_initial_user_message_different_user_msg_at_index_1(
    conversation_memory, initial_user_action
):
    """Test inserting the correct initial user message when a *different* user message is at index 1."""
    system_message = SystemMessageAction(content="System")
    different_user_message = MessageAction(content="Different User Message")
    different_user_message._source = EventSource.USER
    events = [system_message, different_user_message]
    conversation_memory._ensure_initial_user_message(events, initial_user_action)
    assert len(events) == 2
    assert events[0] == system_message
    assert events[1] == different_user_message


def test_ensure_initial_user_message_different_user_msg_at_index_1_and_orphaned_obs(
    conversation_memory, initial_user_action
):
    """Test process_events when an incorrect user message is at index 1 AND.

    an orphaned observation (with tool_call_metadata but no matching action) exists.
    Expect: System msg, CORRECT initial user msg, the incorrect user msg (shifted).
            The orphaned observation should be filtered out.
    """
    system_message = SystemMessageAction(content="System")
    different_user_message = MessageAction(content="Different User Message")
    different_user_message._source = EventSource.USER
    mock_response = {
        "id": "mock_response_id",
        "choices": [{"message": {"content": None, "tool_calls": []}}],
        "created": 0,
        "model": "",
        "object": "",
        "usage": {"completion_tokens": 0, "prompt_tokens": 0, "total_tokens": 0},
    }
    orphaned_obs = CmdOutputObservation(
        command="orphan_cmd", content="Orphaned output", command_id=99, exit_code=0
    )
    orphaned_obs.tool_call_metadata = ToolCallMetadata(
        tool_call_id="orphan_call_id",
        function_name="execute_bash",
        model_response=mock_response,
        total_calls_in_response=1,
    )
    events = [system_message, different_user_message, orphaned_obs]
    messages = conversation_memory.process_events(
        condensed_history=events,
        initial_user_action=initial_user_action,
        max_message_chars=None,
        vision_is_active=False,
    )
    assert len(messages) == 2
    assert messages[0].role == "system"
    assert messages[0].content[0].text == "System"
    assert messages[1].role == "user"
    assert messages[1].content[0].text == different_user_message.content


def test_process_events_with_cmd_output_observation(conversation_memory):
    obs = CmdOutputObservation(
        command="echo hello",
        content="Command output",
        metadata=CmdOutputMetadata(
            exit_code=0, prefix="[THIS IS PREFIX]", suffix="[THIS IS SUFFIX]"
        ),
    )
    initial_user_message = MessageAction(content="Initial user message")
    initial_user_message._source = EventSource.USER
    messages = conversation_memory.process_events(
        condensed_history=[obs],
        initial_user_action=initial_user_message,
        max_message_chars=None,
        vision_is_active=False,
    )
    assert len(messages) == 3
    result = messages[2]
    assert result.role == "user"
    assert len(result.content) == 1
    assert isinstance(result.content[0], TextContent)
    assert "Observed result of command executed by user:" in result.content[0].text
    assert "[Command finished with exit code 0]" in result.content[0].text
    assert "[THIS IS PREFIX]" in result.content[0].text
    assert "[THIS IS SUFFIX]" in result.content[0].text


def test_process_events_with_ipython_run_cell_observation(conversation_memory):
    obs = IPythonRunCellObservation(
        code="plt.plot()",
        content="IPython output\n![image](data:image/png;base64,ABC123)",
    )
    initial_user_message = MessageAction(content="Initial user message")
    initial_user_message._source = EventSource.USER
    messages = conversation_memory.process_events(
        condensed_history=[obs],
        initial_user_action=initial_user_message,
        max_message_chars=None,
        vision_is_active=False,
    )
    assert len(messages) == 3
    result = messages[2]
    assert result.role == "user"
    assert len(result.content) == 1
    assert isinstance(result.content[0], TextContent)
    assert "IPython output" in result.content[0].text
    assert (
        "![image](data:image/png;base64, ...) already displayed to user"
        in result.content[0].text
    )
    assert "ABC123" not in result.content[0].text


def test_process_events_with_agent_delegate_observation(conversation_memory):
    obs = AgentDelegateObservation(
        content="Content", outputs={"content": "Delegated agent output"}
    )
    initial_user_message = MessageAction(content="Initial user message")
    initial_user_message._source = EventSource.USER
    messages = conversation_memory.process_events(
        condensed_history=[obs],
        initial_user_action=initial_user_message,
        max_message_chars=None,
        vision_is_active=False,
    )
    assert len(messages) == 3
    result = messages[2]
    assert result.role == "user"
    assert len(result.content) == 1
    assert isinstance(result.content[0], TextContent)
    assert "Delegated agent output" in result.content[0].text


def test_process_events_with_error_observation(conversation_memory):
    obs = ErrorObservation("Error message")
    initial_user_message = MessageAction(content="Initial user message")
    initial_user_message._source = EventSource.USER
    messages = conversation_memory.process_events(
        condensed_history=[obs],
        initial_user_action=initial_user_message,
        max_message_chars=None,
        vision_is_active=False,
    )
    assert len(messages) == 3
    result = messages[2]
    assert result.role == "user"
    assert len(result.content) == 1
    assert isinstance(result.content[0], TextContent)
    assert "Error message" in result.content[0].text
    assert "Error occurred in processing last action" in result.content[0].text


def test_process_events_with_unknown_observation(conversation_memory):
    obs = Mock(spec=Event)
    initial_user_message = MessageAction(content="Initial user message")
    initial_user_message._source = EventSource.USER
    with pytest.raises(ValueError, match="Unknown event type"):
        conversation_memory.process_events(
            condensed_history=[obs],
            initial_user_action=initial_user_message,
            max_message_chars=None,
            vision_is_active=False,
        )


def test_process_events_with_file_edit_observation(conversation_memory):
    obs = FileEditObservation(
        path="/test/file.txt",
        prev_exist=True,
        old_content="old content",
        new_content="new content",
        content="diff content",
        impl_source=FileEditSource.LLM_BASED_EDIT,
    )
    initial_user_message = MessageAction(content="Initial user message")
    initial_user_message._source = EventSource.USER
    messages = conversation_memory.process_events(
        condensed_history=[obs],
        initial_user_action=initial_user_message,
        max_message_chars=None,
        vision_is_active=False,
    )
    assert len(messages) == 3
    result = messages[2]
    assert result.role == "user"
    assert len(result.content) == 1
    assert isinstance(result.content[0], TextContent)
    assert "[Existing file /test/file.txt is edited with" in result.content[0].text


def test_process_events_with_file_read_observation(conversation_memory):
    obs = FileReadObservation(
        path="/test/file.txt",
        content="File content",
        impl_source=FileReadSource.DEFAULT,
    )
    initial_user_message = MessageAction(content="Initial user message")
    initial_user_message._source = EventSource.USER
    messages = conversation_memory.process_events(
        condensed_history=[obs],
        initial_user_action=initial_user_message,
        max_message_chars=None,
        vision_is_active=False,
    )
    assert len(messages) == 3
    result = messages[2]
    assert result.role == "user"
    assert len(result.content) == 1
    assert isinstance(result.content[0], TextContent)
    assert result.content[0].text == "\n\nFile content"


def test_process_events_with_browser_output_observation(conversation_memory):
    formatted_content = "[Current URL: http://example.com]\n\n============== BEGIN webpage content ==============\nPage loaded\n============== END webpage content =============="
    obs = BrowserOutputObservation(
        url="http://example.com",
        trigger_by_action="browse",
        screenshot="",
        content=formatted_content,
        error=False,
    )
    initial_user_message = MessageAction(content="Initial user message")
    initial_user_message._source = EventSource.USER
    messages = conversation_memory.process_events(
        condensed_history=[obs],
        initial_user_action=initial_user_message,
        max_message_chars=None,
        vision_is_active=False,
    )
    assert len(messages) == 3
    result = messages[2]
    assert result.role == "user"
    assert len(result.content) == 1
    assert isinstance(result.content[0], TextContent)
    assert "[Current URL: http://example.com]" in result.content[0].text


def test_process_events_with_user_reject_observation(conversation_memory):
    obs = UserRejectObservation("Action rejected")
    initial_user_message = MessageAction(content="Initial user message")
    initial_user_message._source = EventSource.USER
    messages = conversation_memory.process_events(
        condensed_history=[obs],
        initial_user_action=initial_user_message,
        max_message_chars=None,
        vision_is_active=False,
    )
    assert len(messages) == 3
    result = messages[2]
    assert result.role == "user"
    assert len(result.content) == 1
    assert isinstance(result.content[0], TextContent)
    assert "Action rejected" in result.content[0].text
    assert "[Last action has been rejected by the user]" in result.content[0].text


def test_process_events_with_empty_environment_info(conversation_memory):
    """Test that empty environment info observations return an empty list of messages without calling build_workspace_context."""
    empty_obs = RecallObservation(
        recall_type=RecallType.WORKSPACE_CONTEXT,
        repo_name="",
        repo_directory="",
        repo_instructions="",
        runtime_hosts={},
        additional_agent_instructions="",
        microagent_knowledge=[],
        content="Retrieved environment info",
    )
    initial_user_message = MessageAction(content="Initial user message")
    initial_user_message._source = EventSource.USER
    messages = conversation_memory.process_events(
        condensed_history=[empty_obs],
        initial_user_action=initial_user_message,
        max_message_chars=None,
        vision_is_active=False,
    )
    assert len(messages) == 2
    conversation_memory.prompt_manager.build_workspace_context.assert_not_called()


def test_process_events_with_function_calling_observation(conversation_memory):
    mock_response = {
        "id": "mock_id",
        "total_calls_in_response": 1,
        "choices": [{"message": {"content": "Task completed"}}],
    }
    obs = CmdOutputObservation(
        command="echo hello", content="Command output", command_id=1, exit_code=0
    )
    obs.tool_call_metadata = ToolCallMetadata(
        tool_call_id="123",
        function_name="execute_bash",
        model_response=mock_response,
        total_calls_in_response=1,
    )
    initial_user_action = MessageAction(content="Initial user message")
    initial_user_action._source = EventSource.USER
    messages = conversation_memory.process_events(
        condensed_history=[obs],
        initial_user_action=initial_user_action,
        max_message_chars=None,
        vision_is_active=False,
    )
    assert len(messages) == 2


def test_process_events_with_message_action_with_image(conversation_memory):
    action = MessageAction(
        content="Message with image", image_urls=["http://example.com/image.jpg"]
    )
    action._source = EventSource.AGENT
    initial_user_action = MessageAction(content="Initial user message")
    initial_user_action._source = EventSource.USER
    messages = conversation_memory.process_events(
        condensed_history=[action],
        initial_user_action=initial_user_action,
        max_message_chars=None,
        vision_is_active=True,
    )
    assert len(messages) == 3
    result = messages[2]
    assert result.role == "assistant"
    assert len(result.content) == 2
    assert isinstance(result.content[0], TextContent)
    assert isinstance(result.content[1], ImageContent)
    assert result.content[0].text == "Message with image"
    assert result.content[1].image_urls == ["http://example.com/image.jpg"]


def test_process_events_with_user_cmd_action(conversation_memory):
    action = CmdRunAction(command="ls -l")
    action._source = EventSource.USER
    initial_user_action = MessageAction(content="Initial user message")
    initial_user_action._source = EventSource.USER
    messages = conversation_memory.process_events(
        condensed_history=[action],
        initial_user_action=initial_user_action,
        max_message_chars=None,
        vision_is_active=False,
    )
    assert len(messages) == 3
    result = messages[2]
    assert result.role == "user"
    assert len(result.content) == 1
    assert isinstance(result.content[0], TextContent)
    assert "User executed the command" in result.content[0].text
    assert "ls -l" in result.content[0].text


def test_process_events_with_agent_finish_action_with_tool_metadata(
    conversation_memory,
):
    mock_response = {
        "id": "mock_id",
        "total_calls_in_response": 1,
        "choices": [{"message": {"content": "Task completed"}}],
    }
    action = AgentFinishAction(thought="Initial thought")
    action._source = EventSource.AGENT
    action.tool_call_metadata = ToolCallMetadata(
        tool_call_id="123",
        function_name="finish",
        model_response=mock_response,
        total_calls_in_response=1,
    )
    initial_user_action = MessageAction(content="Initial user message")
    initial_user_action._source = EventSource.USER
    messages = conversation_memory.process_events(
        condensed_history=[action],
        initial_user_action=initial_user_action,
        max_message_chars=None,
        vision_is_active=False,
    )
    assert len(messages) == 3
    result = messages[2]
    assert result.role == "assistant"
    assert len(result.content) == 1
    assert isinstance(result.content[0], TextContent)
    assert "Initial thought\nTask completed" in result.content[0].text


def test_apply_prompt_caching(conversation_memory):
    messages = [
        Message(role="system", content=[TextContent(text="System message")]),
        Message(role="user", content=[TextContent(text="User message")]),
        Message(role="assistant", content=[TextContent(text="Assistant message")]),
        Message(role="user", content=[TextContent(text="Another user message")]),
    ]
    conversation_memory.apply_prompt_caching(messages)
    assert messages[0].content[0].cache_prompt is True
    assert messages[1].content[0].cache_prompt is False
    assert messages[2].content[0].cache_prompt is False
    assert messages[3].content[0].cache_prompt is True


def test_process_events_with_environment_microagent_observation(conversation_memory):
    """Test processing a RecallObservation with ENVIRONMENT info type."""
    obs = RecallObservation(
        recall_type=RecallType.WORKSPACE_CONTEXT,
        repo_name="test-repo",
        repo_directory="/path/to/repo",
        repo_instructions="# Test Repository\nThis is a test repository.",
        runtime_hosts={"localhost": 8080},
        content="Retrieved environment info",
    )
    initial_user_action = MessageAction(content="Initial user message")
    initial_user_action._source = EventSource.USER
    messages = conversation_memory.process_events(
        condensed_history=[obs],
        initial_user_action=initial_user_action,
        max_message_chars=None,
        vision_is_active=False,
    )
    assert len(messages) == 3
    result = messages[2]
    assert result.role == "user"
    assert len(result.content) == 1
    assert isinstance(result.content[0], TextContent)
    assert result.content[0].text == "\n\nFormatted repository and runtime info"
    conversation_memory.prompt_manager.build_workspace_context.assert_called_once()
    call_args = conversation_memory.prompt_manager.build_workspace_context.call_args[1]
    assert isinstance(call_args["repository_info"], RepositoryInfo)
    assert call_args["repository_info"].repo_name == "test-repo"
    assert call_args["repository_info"].repo_directory == "/path/to/repo"
    assert isinstance(call_args["runtime_info"], RuntimeInfo)
    assert call_args["runtime_info"].available_hosts == {"localhost": 8080}
    assert (
        call_args["repo_instructions"]
        == "# Test Repository\nThis is a test repository."
    )


def test_process_events_with_knowledge_microagent_microagent_observation(
    conversation_memory,
):
    """Test processing a RecallObservation with KNOWLEDGE type."""
    microagent_knowledge = [
        MicroagentKnowledge(
            name="test_agent", trigger="test", content="This is test agent content"
        ),
        MicroagentKnowledge(
            name="another_agent",
            trigger="another",
            content="This is another agent content",
        ),
        MicroagentKnowledge(
            name="disabled_agent",
            trigger="disabled",
            content="This is disabled agent content",
        ),
    ]
    obs = RecallObservation(
        recall_type=RecallType.KNOWLEDGE,
        microagent_knowledge=microagent_knowledge,
        content="Retrieved knowledge from microagents",
    )
    initial_user_action = MessageAction(content="Initial user message")
    initial_user_action._source = EventSource.USER
    messages = conversation_memory.process_events(
        condensed_history=[obs],
        initial_user_action=initial_user_action,
        max_message_chars=None,
        vision_is_active=False,
    )
    assert len(messages) == 3
    result = messages[2]
    assert result.role == "user"
    assert len(result.content) == 1
    assert isinstance(result.content[0], TextContent)
    assert "This is test agent content" in result.content[0].text
    assert "This is another agent content" in result.content[0].text
    assert "This is disabled agent content" not in result.content[0].text
    conversation_memory.prompt_manager.build_microagent_info.assert_called_once()
    call_args = conversation_memory.prompt_manager.build_microagent_info.call_args[1]
    triggered_agents = call_args["triggered_agents"]
    assert len(triggered_agents) == 2
    agent_names = [agent.name for agent in triggered_agents]
    assert "test_agent" in agent_names
    assert "another_agent" in agent_names
    assert "disabled_agent" not in agent_names


def test_process_events_with_microagent_observation_extensions_disabled(
    agent_config, conversation_memory
):
    """Test processing a RecallObservation when prompt extensions are disabled."""
    agent_config.enable_prompt_extensions = False
    obs = RecallObservation(
        recall_type=RecallType.WORKSPACE_CONTEXT,
        repo_name="test-repo",
        repo_directory="/path/to/repo",
        content="Retrieved environment info",
    )
    initial_user_action = MessageAction(content="Initial user message")
    initial_user_action._source = EventSource.USER
    messages = conversation_memory.process_events(
        condensed_history=[obs],
        initial_user_action=initial_user_action,
        max_message_chars=None,
        vision_is_active=False,
    )
    assert len(messages) == 2
    conversation_memory.prompt_manager.build_workspace_context.assert_not_called()
    conversation_memory.prompt_manager.build_microagent_info.assert_not_called()


def test_process_events_with_empty_microagent_knowledge(conversation_memory):
    """Test processing a RecallObservation with empty microagent knowledge."""
    obs = RecallObservation(
        recall_type=RecallType.KNOWLEDGE,
        microagent_knowledge=[],
        content="Retrieved knowledge from microagents",
    )
    initial_user_action = MessageAction(content="Initial user message")
    initial_user_action._source = EventSource.USER
    messages = conversation_memory.process_events(
        condensed_history=[obs],
        initial_user_action=initial_user_action,
        max_message_chars=None,
        vision_is_active=False,
    )
    assert len(messages) == 2
    conversation_memory.prompt_manager.build_microagent_info.assert_not_called()


def test_conversation_memory_processes_microagent_observation(prompt_dir):
    """Test that ConversationMemory processes RecallObservations correctly."""
    template_path = os.path.join(prompt_dir, "microagent_info.j2")
    if not os.path.exists(template_path):
        with open(template_path, "w", encoding="utf-8") as f:
            f.write(
                '{% for agent_info in triggered_agents %}\n<EXTRA_INFO>\nThe following information has been included based on a keyword match for "{{ agent_info.trigger_word }}".\nIt may or may not be relevant to the user\'s request.\n\n    # Verify the template was correctly rendered\n{{ agent_info.content }}\n</EXTRA_INFO>\n{% endfor %}\n'
            )
    agent_config = MagicMock(spec=AgentConfig)
    agent_config.enable_prompt_extensions = True
    agent_config.disabled_microagents = []
    prompt_manager = PromptManager(prompt_dir=prompt_dir)
    conversation_memory = ConversationMemory(
        config=agent_config, prompt_manager=prompt_manager
    )
    microagent_observation = RecallObservation(
        recall_type=RecallType.KNOWLEDGE,
        microagent_knowledge=[
            MicroagentKnowledge(
                name="test_agent",
                trigger="test_trigger",
                content="This is triggered content for testing.",
            )
        ],
        content="Retrieved knowledge from microagents",
    )
    messages = conversation_memory._process_observation(
        obs=microagent_observation, tool_call_id_to_message={}, max_message_chars=None
    )
    assert len(messages) == 1
    message = messages[0]
    assert message.role == "user"
    assert len(message.content) == 1
    assert isinstance(message.content[0], TextContent)
    expected_text = '<EXTRA_INFO>\nThe following information has been included based on a keyword match for "test_trigger".\nIt may or may not be relevant to the user\'s request.\n\nThis is triggered content for testing.\n</EXTRA_INFO>'
    assert message.content[0].text.strip() == expected_text.strip()
    os.remove(os.path.join(prompt_dir, "microagent_info.j2"))


def test_conversation_memory_processes_environment_microagent_observation(prompt_dir):
    """Test that ConversationMemory processes environment info RecallObservations correctly."""
    template_path = os.path.join(prompt_dir, "additional_info.j2")
    if not os.path.exists(template_path):
        with open(template_path, "w", encoding="utf-8") as f:
            f.write(
                "\n{% if repository_info %}\n<REPOSITORY_INFO>\nAt the user's request, repository {{ repository_info.repo_name }} has been cloned to directory {{ repository_info.repo_directory }}.\n</REPOSITORY_INFO>\n{% endif %}\n\n{% if repository_instructions %}\n<REPOSITORY_INSTRUCTIONS>\n{{ repository_instructions }}\n</REPOSITORY_INSTRUCTIONS>\n{% endif %}\n\n{% if runtime_info and runtime_info.available_hosts %}\n<RUNTIME_INFORMATION>\nThe user has access to the following hosts for accessing a web application,\neach of which has a corresponding port:\n{% for host, port in runtime_info.available_hosts.items() %}\n* {{ host }} (port {{ port }})\n{% endfor %}\n</RUNTIME_INFORMATION>\n{% endif %}\n"
            )
    agent_config = MagicMock(spec=AgentConfig)
    agent_config.enable_prompt_extensions = True
    prompt_manager = PromptManager(prompt_dir=prompt_dir)
    conversation_memory = ConversationMemory(
        config=agent_config, prompt_manager=prompt_manager
    )
    microagent_observation = RecallObservation(
        recall_type=RecallType.WORKSPACE_CONTEXT,
        repo_name="owner/repo",
        repo_directory="/workspace/repo",
        repo_instructions="This repository contains important code.",
        runtime_hosts={"example.com": 8080},
        content="Retrieved environment info",
    )
    messages = conversation_memory._process_observation(
        obs=microagent_observation, tool_call_id_to_message={}, max_message_chars=None
    )
    assert len(messages) == 1
    message = messages[0]
    assert message.role == "user"
    assert len(message.content) == 1
    assert isinstance(message.content[0], TextContent)
    assert "<REPOSITORY_INFO>" in message.content[0].text
    assert "owner/repo" in message.content[0].text
    assert "/workspace/repo" in message.content[0].text
    assert "<REPOSITORY_INSTRUCTIONS>" in message.content[0].text
    assert "This repository contains important code." in message.content[0].text
    assert "<RUNTIME_INFORMATION>" in message.content[0].text
    assert "example.com (port 8080)" in message.content[0].text


def test_process_events_with_microagent_observation_deduplication(conversation_memory):
    """Test that RecallObservations are properly deduplicated based on agent name.

    The deduplication logic should keep the FIRST occurrence of each microagent
    and filter out later occurrences to avoid redundant information.
    """
    obs1 = RecallObservation(
        recall_type=RecallType.KNOWLEDGE,
        microagent_knowledge=[
            MicroagentKnowledge(
                name="python_agent",
                trigger="python",
                content="Python best practices v1",
            ),
            MicroagentKnowledge(
                name="git_agent", trigger="git", content="Git best practices v1"
            ),
            MicroagentKnowledge(
                name="image_agent", trigger="image", content="Image best practices v1"
            ),
        ],
        content="First retrieval",
    )
    obs2 = RecallObservation(
        recall_type=RecallType.KNOWLEDGE,
        microagent_knowledge=[
            MicroagentKnowledge(
                name="python_agent",
                trigger="python",
                content="Python best practices v2",
            )
        ],
        content="Second retrieval",
    )
    obs3 = RecallObservation(
        recall_type=RecallType.KNOWLEDGE,
        microagent_knowledge=[
            MicroagentKnowledge(
                name="git_agent", trigger="git", content="Git best practices v3"
            )
        ],
        content="Third retrieval",
    )
    initial_user_action = MessageAction(content="Initial user message")
    initial_user_action._source = EventSource.USER
    messages = conversation_memory.process_events(
        condensed_history=[obs1, obs2, obs3],
        initial_user_action=initial_user_action,
        max_message_chars=None,
        vision_is_active=False,
    )
    assert len(messages) == 3
    assert "Image best practices v1" in messages[2].content[0].text
    assert "Git best practices v1" in messages[2].content[0].text
    assert "Python best practices v1" in messages[2].content[0].text


def test_process_events_with_microagent_observation_deduplication_disabled_agents(
    conversation_memory,
):
    """Test that disabled agents are filtered out and deduplication keeps the first occurrence."""
    obs1 = RecallObservation(
        recall_type=RecallType.KNOWLEDGE,
        microagent_knowledge=[
            MicroagentKnowledge(
                name="disabled_agent",
                trigger="disabled",
                content="Disabled agent content",
            ),
            MicroagentKnowledge(
                name="enabled_agent",
                trigger="enabled",
                content="Enabled agent content v1",
            ),
        ],
        content="First retrieval",
    )
    obs2 = RecallObservation(
        recall_type=RecallType.KNOWLEDGE,
        microagent_knowledge=[
            MicroagentKnowledge(
                name="enabled_agent",
                trigger="enabled",
                content="Enabled agent content v2",
            )
        ],
        content="Second retrieval",
    )
    initial_user_action = MessageAction(content="Initial user message")
    initial_user_action._source = EventSource.USER
    messages = conversation_memory.process_events(
        condensed_history=[obs1, obs2],
        initial_user_action=initial_user_action,
        max_message_chars=None,
        vision_is_active=False,
    )
    assert len(messages) == 3
    assert "Disabled agent content" not in messages[2].content[0].text
    assert "Enabled agent content v1" in messages[2].content[0].text


def test_process_events_with_microagent_observation_deduplication_empty(
    conversation_memory,
):
    """Test that empty RecallObservations are handled correctly."""
    obs = RecallObservation(
        recall_type=RecallType.KNOWLEDGE,
        microagent_knowledge=[],
        content="Empty retrieval",
    )
    initial_user_action = MessageAction(content="Initial user message")
    initial_user_action._source = EventSource.USER
    messages = conversation_memory.process_events(
        condensed_history=[obs],
        initial_user_action=initial_user_action,
        max_message_chars=None,
        vision_is_active=False,
    )
    assert len(messages) == 2
    assert messages[0].role == "system"
    assert messages[1].role == "user"


def test_has_agent_in_earlier_events(conversation_memory):
    """Test the _has_agent_in_earlier_events helper method."""
    obs1 = RecallObservation(
        recall_type=RecallType.KNOWLEDGE,
        microagent_knowledge=[
            MicroagentKnowledge(name="agent1", trigger="trigger1", content="Content 1")
        ],
        content="First retrieval",
    )
    obs2 = RecallObservation(
        recall_type=RecallType.KNOWLEDGE,
        microagent_knowledge=[
            MicroagentKnowledge(name="agent2", trigger="trigger2", content="Content 2")
        ],
        content="Second retrieval",
    )
    obs3 = RecallObservation(
        recall_type=RecallType.WORKSPACE_CONTEXT, content="Environment info"
    )
    events = [obs1, MessageAction(content="User message"), obs2, obs3]
    assert conversation_memory._has_agent_in_earlier_events("agent1", 2, events) is True
    assert conversation_memory._has_agent_in_earlier_events("agent1", 3, events) is True
    assert conversation_memory._has_agent_in_earlier_events("agent1", 4, events) is True
    assert (
        conversation_memory._has_agent_in_earlier_events("agent2", 0, events) is False
    )
    assert (
        conversation_memory._has_agent_in_earlier_events("agent2", 1, events) is False
    )
    assert (
        conversation_memory._has_agent_in_earlier_events("non_existent", 3, events)
        is False
    )


def test_build_message_content_includes_microagent(conversation_memory):
    repo_info = RepositoryInfo(
        repo_name="repo", repo_directory="/repo", branch_name=None
    )
    runtime_info = RuntimeInfo(
        date="2025-01-01",
        available_hosts={},
        additional_agent_instructions="",
        custom_secrets_descriptions={},
        working_dir="/repo",
    )
    content = conversation_memory._build_message_content(
        repo_info,
        runtime_info,
        ConversationInstructions(content="instructions"),
        "Repo instructions",
        [MicroagentKnowledge(name="agent", trigger="x", content="info")],
    )
    texts = [item.text for item in content if isinstance(item, TextContent)]
    assert any("Formatted repository and runtime info" in text for text in texts)
    assert any("info" in text for text in texts)


def test_filter_agents_in_microagent_obs_non_knowledge(conversation_memory):
    obs = RecallObservation(
        recall_type=RecallType.WORKSPACE_CONTEXT,
        microagent_knowledge=[
            MicroagentKnowledge(name="agent", trigger="t", content="c")
        ],
        content="",
    )
    assert (
        conversation_memory._filter_agents_in_microagent_obs(obs, 0, [])
        == obs.microagent_knowledge
    )


def test_should_include_message_helpers():
    tool_message = Message(
        role="tool", content=[TextContent(text="Tool")], tool_call_id="call_1"
    )
    assistant_message = Message(
        role="assistant",
        content=[TextContent(text="Assistant")],
        tool_calls=[
            ChatCompletionMessageToolCall(
                id="call_1", type="function", function={"name": "fn", "arguments": ""}
            )
        ],
    )
    assert ConversationMemory._should_include_message(tool_message, {"call_1"}, set())
    assert ConversationMemory._should_include_message(
        assistant_message, set(), {"call_1"}
    )
    assistant_message.tool_calls[0] = ChatCompletionMessageToolCall(
        id="missing", type="function", function={"name": "fn", "arguments": ""}
    )
    assert (
        ConversationMemory._should_include_message(assistant_message, set(), {"call_1"})
        is False
    )


def test_all_tool_calls_match():
    assistant_message = Message(
        role="assistant",
        content=[TextContent(text="Assistant")],
        tool_calls=[
            ChatCompletionMessageToolCall(
                id="call_1", type="function", function={"name": "fn", "arguments": ""}
            )
        ],
    )
    assert ConversationMemory._all_tool_calls_match(assistant_message, {"call_1"})
    assert ConversationMemory._all_tool_calls_match(assistant_message, set()) is False


def test_store_and_recall_from_memory(monkeypatch):
    memory = _make_memory({"enable_vector_memory": True})
    add_calls = {}

    class StubVectorStore:
        def add(self, *args, **kwargs):
            add_calls["added"] = True

        def search(self, query, k):
            return [{"step_id": "1"}]

    memory.vector_store = StubVectorStore()
    memory.store_in_memory("event1", "user", "content")
    assert add_calls.get("added")

    results = memory.recall_from_memory("query")
    assert results == [{"step_id": "1"}]

    class FailingStore(StubVectorStore):
        def add(self, *args, **kwargs):
            raise RuntimeError("fail")

        def search(self, query, k):
            raise RuntimeError("fail")

    memory.vector_store = FailingStore()
    memory.store_in_memory("event2", "user", "content")
    assert memory.recall_from_memory("query") == []


class TestFilterUnmatchedToolCalls:
    @pytest.fixture
    def processor(self):
        return ConversationMemory()

    def test_empty_is_unchanged(self):
        assert not list(ConversationMemory._filter_unmatched_tool_calls([]))

    def test_no_tool_calls_is_unchanged(self):
        messages = [
            Message(role="user", content=[TextContent(text="Hello")]),
            Message(role="assistant", content=[TextContent(text="Hi there")]),
            Message(role="user", content=[TextContent(text="How are you?")]),
        ]
        assert (
            list(ConversationMemory._filter_unmatched_tool_calls(messages)) == messages
        )

    def test_matched_tool_calls_are_unchanged(self):
        messages = [
            Message(role="user", content=[TextContent(text="What's the weather?")]),
            Message(
                role="assistant",
                content=[],
                tool_calls=[
                    ChatCompletionMessageToolCall(
                        id="call_1",
                        type="function",
                        function={"name": "get_weather", "arguments": ""},
                    )
                ],
            ),
            Message(
                role="tool",
                tool_call_id="call_1",
                content=[TextContent(text="Sunny, 75°F")],
            ),
            Message(role="assistant", content=[TextContent(text="It's sunny today.")]),
        ]
        assert (
            list(ConversationMemory._filter_unmatched_tool_calls(messages)) == messages
        )

    def test_tool_call_without_response_is_removed(self):
        messages = [
            Message(role="user", content=[TextContent(text="Query")]),
            Message(
                role="tool",
                tool_call_id="missing_call",
                content=[TextContent(text="Response")],
            ),
            Message(role="assistant", content=[TextContent(text="Answer")]),
        ]
        expected_after_filter = [
            Message(role="user", content=[TextContent(text="Query")]),
            Message(role="assistant", content=[TextContent(text="Answer")]),
        ]
        result = list(ConversationMemory._filter_unmatched_tool_calls(messages))
        assert result == expected_after_filter

    def test_tool_response_without_call_is_removed(self):
        messages = [
            Message(role="user", content=[TextContent(text="Query")]),
            Message(
                role="assistant",
                content=[],
                tool_calls=[
                    ChatCompletionMessageToolCall(
                        id="unmatched_call",
                        type="function",
                        function={"name": "some_function", "arguments": ""},
                    )
                ],
            ),
            Message(role="assistant", content=[TextContent(text="Answer")]),
        ]
        expected_after_filter = [
            Message(role="user", content=[TextContent(text="Query")]),
            Message(role="assistant", content=[TextContent(text="Answer")]),
        ]
        result = list(ConversationMemory._filter_unmatched_tool_calls(messages))
        assert result == expected_after_filter

    def test_partial_matched_tool_calls_retains_matched(self):
        """When there are both matched and unmatched tools calls in a message, retain the message and only matched calls."""
        messages = [
            Message(role="user", content=[TextContent(text="Get data")]),
            Message(
                role="assistant",
                content=[],
                tool_calls=[
                    ChatCompletionMessageToolCall(
                        id="matched_call",
                        type="function",
                        function={"name": "function1", "arguments": ""},
                    ),
                    ChatCompletionMessageToolCall(
                        id="unmatched_call",
                        type="function",
                        function={"name": "function2", "arguments": ""},
                    ),
                ],
            ),
            Message(
                role="tool",
                tool_call_id="matched_call",
                content=[TextContent(text="Data")],
            ),
            Message(role="assistant", content=[TextContent(text="Result")]),
        ]
        expected = [
            Message(role="user", content=[TextContent(text="Get data")]),
            Message(
                role="assistant",
                content=[],
                tool_calls=[
                    ChatCompletionMessageToolCall(
                        id="matched_call",
                        type="function",
                        function={"name": "function1", "arguments": ""},
                    )
                ],
            ),
            Message(
                role="tool",
                tool_call_id="matched_call",
                content=[TextContent(text="Data")],
            ),
            Message(role="assistant", content=[TextContent(text="Result")]),
        ]
        result = list(ConversationMemory._filter_unmatched_tool_calls(messages))
        assert len(result) == len(expected)
        for i, msg in enumerate(result):
            assert msg == expected[i]


def test_system_message_in_events(conversation_memory):
    """Test that SystemMessageAction in condensed_history is processed correctly."""
    system_message = SystemMessageAction(content="System message", tools=["test_tool"])
    system_message._source = EventSource.AGENT
    initial_user_action = MessageAction(content="Initial user message")
    initial_user_action._source = EventSource.USER
    messages = conversation_memory.process_events(
        condensed_history=[system_message],
        initial_user_action=initial_user_action,
        max_message_chars=None,
        vision_is_active=False,
    )
    assert len(messages) == 2
    assert messages[0].role == "system"
    assert messages[0].content[0].text == "System message"
    assert messages[1].role == "user"


def _create_mock_tool_call_metadata(
    tool_call_id: str, function_name: str, response_id: str = "mock_response_id"
) -> ToolCallMetadata:
    mock_response = {
        "id": response_id,
        "choices": [
            {
                "message": {
                    "role": "assistant",
                    "content": None,
                    "tool_calls": [
                        {
                            "id": tool_call_id,
                            "type": "function",
                            "function": {"name": function_name, "arguments": "{}"},
                        }
                    ],
                }
            }
        ],
        "created": 0,
        "model": "mock_model",
        "object": "chat.completion",
        "usage": {"completion_tokens": 0, "prompt_tokens": 0, "total_tokens": 0},
    }
    return ToolCallMetadata(
        tool_call_id=tool_call_id,
        function_name=function_name,
        model_response=mock_response,
        total_calls_in_response=1,
    )


def _create_test_events() -> tuple[Event, Event, Event, Event, Event]:
    """Create test events for the partial history test."""
    system_message = SystemMessageAction(content="System message")
    system_message._source = EventSource.AGENT

    user_message = MessageAction(content="Initial user query")
    user_message._source = EventSource.USER

    recall_obs = RecallObservation(
        recall_type=RecallType.WORKSPACE_CONTEXT,
        repo_name="test-repo",
        repo_directory="/path/to/repo",
        content="Retrieved environment info",
    )
    recall_obs._source = EventSource.AGENT

    cmd_action = CmdRunAction(command="ls", thought="Running ls")
    cmd_action._source = EventSource.AGENT
    cmd_action.tool_call_metadata = _create_mock_tool_call_metadata(
        tool_call_id="call_ls_1", function_name="execute_bash", response_id="resp_ls_1"
    )

    cmd_obs = CmdOutputObservation(
        command_id=1, command="ls", content="file1.txt\nfile2.py", exit_code=0
    )
    cmd_obs._source = EventSource.AGENT
    cmd_obs.tool_call_metadata = _create_mock_tool_call_metadata(
        tool_call_id="call_ls_1", function_name="execute_bash", response_id="resp_ls_1"
    )

    return system_message, user_message, recall_obs, cmd_action, cmd_obs


def _assert_full_history_messages(messages: list) -> None:
    """Assert the structure and content of full history messages."""
    assert len(messages) == 5
    assert messages[0].role == "system"
    assert messages[0].content[0].text == "System message"
    assert messages[1].role == "user"
    assert messages[1].content[0].text == "Initial user query"
    assert messages[2].role == "user"
    assert "Formatted repository and runtime info" in messages[2].content[0].text
    assert messages[3].role == "assistant"
    assert messages[3].tool_calls is not None
    assert len(messages[3].tool_calls) == 1
    assert messages[3].tool_calls[0].id == "call_ls_1"
    assert messages[4].role == "tool"
    assert messages[4].tool_call_id == "call_ls_1"
    assert "file1.txt" in messages[4].content[0].text


def _assert_partial_action_obs_messages(messages: list) -> None:
    """Assert the structure and content of partial action+obs history messages."""
    assert len(messages) == 4
    assert messages[0].role == "system"
    assert messages[0].content[0].text == "System message"
    assert messages[1].role == "user"
    assert messages[1].content[0].text == "Initial user query"
    assert messages[2].role == "assistant"
    assert messages[2].tool_calls is not None
    assert len(messages[2].tool_calls) == 1
    assert messages[2].tool_calls[0].id == "call_ls_1"
    assert messages[3].role == "tool"
    assert messages[3].tool_call_id == "call_ls_1"
    assert "file1.txt" in messages[3].content[0].text


def _assert_partial_obs_only_messages(messages: list) -> None:
    """Assert the structure and content of partial obs-only history messages."""
    assert len(messages) == 2
    assert messages[0].role == "system"
    assert messages[0].content[0].text == "System message"
    assert messages[1].role == "user"
    assert messages[1].content[0].text == "Initial user query"


def test_process_events_partial_history(conversation_memory):
    """Tests process_events with full and partial histories to verify.

    _ensure_system_message, _ensure_initial_user_message, and tool call matching logic.
    """
    system_message, user_message, recall_obs, cmd_action, cmd_obs = (
        _create_test_events()
    )

    # Test with full history
    full_history: list[Event] = [
        system_message,
        user_message,
        recall_obs,
        cmd_action,
        cmd_obs,
    ]
    messages_full = conversation_memory.process_events(
        condensed_history=list(full_history),
        initial_user_action=user_message,
        max_message_chars=None,
        vision_is_active=False,
    )
    _assert_full_history_messages(messages_full)

    # Test with partial history (action + observation)
    partial_history_action_obs: list[Event] = [cmd_action, cmd_obs]
    messages_partial_action_obs = conversation_memory.process_events(
        condensed_history=list(partial_history_action_obs),
        initial_user_action=user_message,
        max_message_chars=None,
        vision_is_active=False,
    )
    _assert_partial_action_obs_messages(messages_partial_action_obs)

    # Test with partial history (observation only)
    partial_history_obs_only: list[Event] = [cmd_obs]
    messages_partial_obs_only = conversation_memory.process_events(
        condensed_history=list(partial_history_obs_only),
        initial_user_action=user_message,
        max_message_chars=None,
        vision_is_active=False,
    )
    _assert_partial_obs_only_messages(messages_partial_obs_only)


def test_process_ipython_observation_with_vision_enabled(
    agent_config, mock_prompt_manager
):
    """Test that _process_observation correctly handles IPythonRunCellObservation with image_urls when vision is enabled."""
    memory = ConversationMemory(agent_config, mock_prompt_manager)
    obs = IPythonRunCellObservation(
        content="Test output",
        code="print('test')",
        image_urls=["data:image/png;base64,abc123"],
    )
    messages = memory._process_observation(
        obs=obs,
        tool_call_id_to_message={},
        max_message_chars=None,
        vision_is_active=True,
    )
    assert len(messages) == 1
    message = messages[0]
    assert len(message.content) == 2
    assert isinstance(message.content[0], TextContent)
    assert isinstance(message.content[1], ImageContent)
    assert message.content[1].image_urls == ["data:image/png;base64,abc123"]


def test_handle_tool_based_action_user_without_metadata(conversation_memory):
    class DummyAction:
        def __init__(self):
            self.source = "user"
            self.tool_call_metadata = None

        def __str__(self):
            return "dummy-action"

    result = conversation_memory._handle_tool_based_action(DummyAction(), {})
    assert result[0].role == "user"
    assert "dummy-action" in result[0].content[0].text


def test_handle_tool_based_action_agent_think(conversation_memory):
    action = AgentThinkAction(thought="considering options")
    action._source = "agent"
    messages = conversation_memory._handle_tool_based_action(action, {})
    assert messages[0].role == "assistant"
    assert "considering options" in messages[0].content[0].text


def test_handle_tool_based_action_empty_choices(conversation_memory):
    metadata = SimpleNamespace(model_response=SimpleNamespace(choices=[]))
    action = SimpleNamespace(source="agent", tool_call_metadata=metadata)
    assert conversation_memory._handle_tool_based_action(action, {}) == []


def test_handle_tool_based_action_missing_message(conversation_memory):
    metadata = SimpleNamespace(
        model_response=SimpleNamespace(choices=[SimpleNamespace()])
    )
    action = SimpleNamespace(source="agent", tool_call_metadata=metadata)
    assert conversation_memory._handle_tool_based_action(action, {}) == []


def test_handle_tool_based_action_populates_pending(conversation_memory):
    assistant_message = SimpleNamespace(
        content=" Trim me ", tool_calls=None, role="agent"
    )
    choice = SimpleNamespace(message=assistant_message)
    response = SimpleNamespace(id="response-1", choices=[choice])
    metadata = SimpleNamespace(model_response=response)
    action = SimpleNamespace(source="agent", tool_call_metadata=metadata)
    pending: dict[str, Message] = {}

    result = conversation_memory._handle_tool_based_action(action, pending)
    assert result == []
    assert "response-1" in pending
    stored = pending["response-1"]
    assert stored.role == "assistant"
    assert stored.content[0].text == "Trim me"


def test_handle_tool_based_action_non_string_content(conversation_memory):
    assistant_message = SimpleNamespace(
        content=["value"], tool_calls=None, role="invalid"
    )
    choice = SimpleNamespace(message=assistant_message)
    response = SimpleNamespace(id="response-2", choices=[choice])
    metadata = SimpleNamespace(model_response=response)
    action = SimpleNamespace(source="agent", tool_call_metadata=metadata)
    pending: dict[str, Message] = {}

    conversation_memory._handle_tool_based_action(action, pending)
    stored = pending["response-2"]
    assert stored.role == "assistant"
    assert stored.content[0].text == "['value']"


def test_handle_tool_based_action_missing_response_id(conversation_memory):
    assistant_message = SimpleNamespace(
        content="hello", tool_calls=None, role="assistant"
    )
    response = SimpleNamespace(
        id=None, choices=[SimpleNamespace(message=assistant_message)]
    )
    metadata = SimpleNamespace(model_response=response)
    action = SimpleNamespace(source="agent", tool_call_metadata=metadata)
    assert conversation_memory._handle_tool_based_action(action, {}) == []


def test_handle_agent_finish_action_sets_content(conversation_memory):
    action = AgentFinishAction(thought=None)
    action._source = EventSource.AGENT
    metadata = _create_mock_tool_call_metadata(
        tool_call_id="call", function_name="finish"
    )
    metadata.model_response["choices"][0]["message"]["content"] = "Result content"
    action.tool_call_metadata = metadata
    messages = conversation_memory._handle_agent_finish_action(action)
    assert messages[0].content[0].text == "Result content"
    assert action.tool_call_metadata is None


def test_handle_message_action_user_images_with_vision(conversation_memory):
    class UserImageMessage(MessageAction):
        @property
        def source(self):
            return "user"

    action = UserImageMessage(
        content="See image", image_urls=["http://example.com/img.png"]
    )
    messages = conversation_memory._handle_message_action(action, vision_is_active=True)
    assert len(messages[0].content) == 3
    assert isinstance(messages[0].content[1], TextContent)
    assert isinstance(messages[0].content[2], ImageContent)


def test_process_ipython_observation_with_vision_disabled(
    agent_config, mock_prompt_manager
):
    """Test that _process_observation correctly handles IPythonRunCellObservation with image_urls when vision is disabled."""
    memory = ConversationMemory(agent_config, mock_prompt_manager)
    obs = IPythonRunCellObservation(
        content="Test output",
        code="print('test')",
        image_urls=["data:image/png;base64,abc123"],
    )
    messages = memory._process_observation(
        obs=obs,
        tool_call_id_to_message={},
        max_message_chars=None,
        vision_is_active=False,
    )
    assert len(messages) == 1
    message = messages[0]
    assert len(message.content) == 2
    assert isinstance(message.content[0], TextContent)
    assert isinstance(message.content[1], ImageContent)
    assert "invalid or empty image(s) were filtered" not in message.content[0].text


def test_process_action_returns_empty(conversation_memory):
    assert (
        conversation_memory._process_action(SimpleNamespace(source="agent"), {}) == []
    )


def test_process_mcp_observation(conversation_memory):
    from forge.events.observation.mcp import MCPObservation

    obs = MCPObservation(content="MCP content")
    message = conversation_memory._process_mcp_observation(obs, max_message_chars=None)
    assert message.content[0].text == "MCP content"


def test_extract_browser_image_prefers_screenshot(conversation_memory):
    obs = BrowserOutputObservation(
        content="Browser output",
        url="",
        trigger_by_action="",
        screenshot="data:image",
        set_of_marks=None,
        error=False,
    )
    url, image_type = conversation_memory._extract_browser_image(obs)
    assert url == "data:image"
    assert image_type == "screenshot"


def test_add_browser_image_fallback_invalid_url(conversation_memory):
    content = [TextContent(text="Log")]
    conversation_memory._add_browser_image_fallback(
        content, "http://invalid", "screenshot"
    )
    assert "invalid or empty" in content[0].text


def test_add_browser_image_fallback_no_image(conversation_memory):
    content = [TextContent(text="Log")]
    conversation_memory._add_browser_image_fallback(content, None, None)
    assert "No visual information" in content[0].text


def test_process_recall_observation_prompt_extensions_disabled():
    memory = _make_memory({"enable_prompt_extensions": False})
    obs = RecallObservation(
        recall_type=RecallType.KNOWLEDGE, microagent_knowledge=[], content=""
    )
    assert memory._process_recall_observation(obs, current_index=0, events=[]) == []
