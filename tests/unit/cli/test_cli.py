import asyncio
from unittest.mock import AsyncMock, MagicMock, patch
import pytest
import pytest_asyncio
from forge.cli import main as cli
from forge.controller.state.state import State
from forge.core.config.llm_config import LLMConfig
from forge.events import EventSource
from forge.events.action import MessageAction


@pytest_asyncio.fixture
def mock_agent():
    agent = AsyncMock()
    agent.reset = MagicMock()
    return agent


@pytest_asyncio.fixture
def mock_runtime():
    runtime = AsyncMock()
    runtime.close = MagicMock()
    runtime.event_stream = MagicMock()
    return runtime


@pytest_asyncio.fixture
def mock_controller():
    controller = AsyncMock()
    controller.close = AsyncMock()
    mock_state = MagicMock()
    mock_state.save_to_session = MagicMock()
    controller.get_state = MagicMock(return_value=mock_state)
    return controller


@pytest.mark.asyncio
async def test_cleanup_session_closes_resources(mock_agent, mock_runtime, mock_controller):
    """Test that cleanup_session calls close methods on agent, runtime, and controller."""
    loop = asyncio.get_running_loop()
    await cli.cleanup_session(loop, mock_agent, mock_runtime, mock_controller)
    mock_agent.reset.assert_called_once()
    mock_runtime.close.assert_called_once()
    mock_controller.close.assert_called_once()


@pytest.mark.asyncio
async def test_cleanup_session_cancels_pending_tasks(mock_agent, mock_runtime, mock_controller):
    """Test that cleanup_session cancels other pending tasks."""
    loop = asyncio.get_running_loop()
    other_task_ran = False
    other_task_cancelled = False

    async def _other_task_func():
        nonlocal other_task_ran, other_task_cancelled
        try:
            other_task_ran = True
            await asyncio.sleep(5)
        except asyncio.CancelledError:
            other_task_cancelled = True
            raise

    other_task = loop.create_task(_other_task_func())
    await asyncio.sleep(0)
    assert other_task_ran
    await cli.cleanup_session(loop, mock_agent, mock_runtime, mock_controller)
    await asyncio.sleep(0)
    assert other_task.cancelled() or other_task_cancelled
    try:
        await other_task
    except asyncio.CancelledError:
        pass
    mock_agent.reset.assert_called_once()
    mock_runtime.close.assert_called_once()
    mock_controller.close.assert_called_once()


@pytest.mark.asyncio
async def test_cleanup_session_handles_exceptions(mock_agent, mock_runtime, mock_controller):
    """Test that cleanup_session handles exceptions during cleanup gracefully."""
    loop = asyncio.get_running_loop()
    mock_controller.close.side_effect = Exception("Test cleanup error")
    with patch("forge.cli.main.logger.error") as mock_log_error:
        await cli.cleanup_session(loop, mock_agent, mock_runtime, mock_controller)
        mock_agent.reset.assert_called_once()
        mock_runtime.close.assert_called_once()
        mock_log_error.assert_called_once()
        assert "Test cleanup error" in mock_log_error.call_args[0][0]


@pytest_asyncio.fixture
def mock_config():
    config = MagicMock()
    config.runtime = "local"
    config.cli_multiline_input = False
    config.workspace_base = "/test/dir"
    search_api_key_mock = MagicMock()
    search_api_key_mock.get_secret_value.return_value = ""
    config.search_api_key = search_api_key_mock
    config.get_llm_config_from_agent.return_value = LLMConfig(model="model")
    config.sandbox = MagicMock()
    config.sandbox.volumes = None
    config.model_name = "model"
    return config


@pytest_asyncio.fixture
def mock_settings_store():
    return AsyncMock()


@pytest.mark.asyncio
@patch("forge.cli.main.display_runtime_initialization_message")
@patch("forge.cli.main.display_initialization_animation")
@patch("forge.cli.main.create_agent")
@patch("forge.cli.main.add_mcp_tools_to_agent")
@patch("forge.cli.main.create_runtime")
@patch("forge.cli.main.create_controller")
@patch("forge.cli.main.create_memory")
@patch("forge.cli.main.run_agent_until_done")
@patch("forge.cli.main.cleanup_session")
@patch("forge.cli.main.initialize_repository_for_runtime")
async def test_run_session_without_initial_action(
    mock_initialize_repo,
    mock_cleanup_session,
    mock_run_agent_until_done,
    mock_create_memory,
    mock_create_controller,
    mock_create_runtime,
    mock_add_mcp_tools,
    mock_create_agent,
    mock_display_animation,
    mock_display_runtime_init,
    mock_config,
    mock_settings_store,
):
    """Test run_session function with no initial user action."""
    loop = asyncio.get_running_loop()
    mock_initialize_repo.return_value = "/test/dir"
    mock_agent = AsyncMock()
    mock_create_agent.return_value = mock_agent
    mock_runtime = AsyncMock()
    mock_runtime.event_stream = MagicMock()
    mock_create_runtime.return_value = mock_runtime
    mock_controller = AsyncMock()
    mock_controller_task = MagicMock()
    mock_create_controller.return_value = (mock_controller, mock_controller_task)
    mock_memory = MagicMock()
    mock_create_memory.return_value = mock_memory
    with patch("forge.cli.main.read_prompt_input", new_callable=AsyncMock) as mock_read_prompt:
        mock_read_prompt.return_value = "/exit"
        with patch("forge.cli.main.handle_commands", new_callable=AsyncMock) as mock_handle_commands:
            mock_handle_commands.return_value = (True, False, False)
            result = await cli.run_session(loop, mock_config, mock_settings_store, "/test/dir")
    mock_display_runtime_init.assert_called_once_with("local")
    mock_display_animation.assert_called_once()
    mock_create_agent.assert_called_once()
    assert mock_create_agent.call_args[0][0] == mock_config, "First parameter to create_agent should be mock_config"
    mock_add_mcp_tools.assert_called_once_with(mock_agent, mock_runtime, mock_memory)
    mock_create_runtime.assert_called_once()
    mock_create_controller.assert_called_once()
    mock_create_memory.assert_called_once()
    mock_run_agent_until_done.assert_called_once()
    mock_cleanup_session.assert_called_once()
    assert result is False


@pytest.mark.asyncio
@patch("forge.cli.main.display_runtime_initialization_message")
@patch("forge.cli.main.display_initialization_animation")
@patch("forge.cli.main.create_agent")
@patch("forge.cli.main.add_mcp_tools_to_agent")
@patch("forge.cli.main.create_runtime")
@patch("forge.cli.main.create_controller")
@patch("forge.cli.main.create_memory", new_callable=AsyncMock)
@patch("forge.cli.main.run_agent_until_done")
@patch("forge.cli.main.cleanup_session")
@patch("forge.cli.main.initialize_repository_for_runtime")
async def test_run_session_with_initial_action(
    mock_initialize_repo,
    mock_cleanup_session,
    mock_run_agent_until_done,
    mock_create_memory,
    mock_create_controller,
    mock_create_runtime,
    mock_add_mcp_tools,
    mock_create_agent,
    mock_display_animation,
    mock_display_runtime_init,
    mock_config,
    mock_settings_store,
):
    """Test run_session function with an initial user action."""
    loop = asyncio.get_running_loop()
    mock_initialize_repo.return_value = "/test/dir"
    mock_agent = AsyncMock()
    mock_create_agent.return_value = mock_agent
    mock_runtime = AsyncMock()
    mock_runtime.event_stream = MagicMock()
    mock_create_runtime.return_value = mock_runtime
    mock_controller = AsyncMock()
    mock_create_controller.return_value = (mock_controller, None)
    mock_memory = AsyncMock()
    mock_create_memory.return_value = mock_memory
    initial_action_content = "Test initial message"
    with patch("forge.cli.main.read_prompt_input", new_callable=AsyncMock) as mock_read_prompt:
        mock_read_prompt.return_value = "/exit"
        with patch("forge.cli.main.handle_commands", new_callable=AsyncMock) as mock_handle_commands:
            mock_handle_commands.return_value = (True, False, False)
            result = await cli.run_session(loop, mock_config, mock_settings_store, "/test/dir", initial_action_content)
    mock_runtime.event_stream.add_event.assert_called_once()
    call_args = mock_runtime.event_stream.add_event.call_args[0]
    assert isinstance(call_args[0], MessageAction)
    assert call_args[0].content == initial_action_content
    assert call_args[1] == EventSource.USER
    mock_run_agent_until_done.assert_called_once()
    mock_cleanup_session.assert_called_once()
    assert result is False


@pytest.mark.asyncio
@patch("forge.cli.main.setup_config_from_args")
@patch("forge.cli.main.FileSettingsStore.get_instance")
@patch("forge.cli.main.check_folder_security_agreement")
@patch("forge.cli.main.read_task")
@patch("forge.cli.main.run_session")
@patch("forge.cli.main.LLMSummarizingCondenserConfig")
@patch("forge.cli.main.NoOpCondenserConfig")
@patch("forge.cli.main.finalize_config")
@patch("forge.cli.main.aliases_exist_in_shell_config")
async def test_main_without_task(
    mock_aliases_exist,
    mock_finalize_config,
    mock_noop_condenser,
    mock_llm_condenser,
    mock_run_session,
    mock_read_task,
    mock_check_security,
    mock_get_settings_store,
    mock_setup_config,
):
    """Test main function without a task."""
    loop = asyncio.get_running_loop()
    mock_aliases_exist.return_value = True
    mock_args = MagicMock()
    mock_args.agent_cls = None
    mock_args.llm_config = None
    mock_args.name = None
    mock_args.file = None
    mock_args.conversation = None
    mock_args.log_level = None
    mock_args.config_file = "config.toml"
    mock_args.override_cli_mode = None
    mock_config = MagicMock()
    mock_config.workspace_base = "/test/dir"
    mock_config.cli_multiline_input = False
    mock_setup_config.return_value = mock_config
    mock_settings_store = AsyncMock()
    mock_settings = MagicMock()
    mock_settings.agent = "test-agent"
    mock_settings.llm_model = "test-model"
    mock_settings.llm_api_key = "test-api-key"
    mock_settings.llm_base_url = "test-base-url"
    mock_settings.confirmation_mode = True
    mock_settings.enable_default_condenser = True
    mock_settings_store.load.return_value = mock_settings
    mock_get_settings_store.return_value = mock_settings_store
    mock_llm_condenser_instance = MagicMock()
    mock_llm_condenser.return_value = mock_llm_condenser_instance
    mock_check_security.return_value = True
    mock_read_task.return_value = None
    mock_run_session.return_value = False
    await cli.main_with_loop(loop, mock_args)
    mock_setup_config.assert_called_once_with(mock_args)
    mock_get_settings_store.assert_called_once()
    mock_settings_store.load.assert_called_once()
    mock_check_security.assert_called_once_with(mock_config, "/test/dir")
    mock_read_task.assert_called_once()
    mock_run_session.assert_called_once_with(
        loop,
        mock_config,
        mock_settings_store,
        "/test/dir",
        None,
        session_name=None,
        skip_banner=False,
        conversation_id=None,
    )


@pytest.mark.asyncio
@patch("forge.cli.main.setup_config_from_args")
@patch("forge.cli.main.FileSettingsStore.get_instance")
@patch("forge.cli.main.check_folder_security_agreement")
@patch("forge.cli.main.read_task")
@patch("forge.cli.main.run_session")
@patch("forge.cli.main.LLMSummarizingCondenserConfig")
@patch("forge.cli.main.NoOpCondenserConfig")
@patch("forge.cli.main.finalize_config")
@patch("forge.cli.main.aliases_exist_in_shell_config")
async def test_main_with_task(
    mock_aliases_exist,
    mock_finalize_config,
    mock_noop_condenser,
    mock_llm_condenser,
    mock_run_session,
    mock_read_task,
    mock_check_security,
    mock_get_settings_store,
    mock_setup_config,
):
    """Test main function with a task."""
    loop = asyncio.get_running_loop()
    mock_aliases_exist.return_value = True
    mock_args = MagicMock()
    mock_args.agent_cls = "custom-agent"
    mock_args.llm_config = "custom-config"
    mock_args.file = None
    mock_args.name = None
    mock_args.conversation = None
    mock_args.log_level = None
    mock_args.config_file = "config.toml"
    mock_args.override_cli_mode = None
    mock_config = MagicMock()
    mock_config.workspace_base = "/test/dir"
    mock_config.cli_multiline_input = False
    mock_setup_config.return_value = mock_config
    mock_settings_store = AsyncMock()
    mock_settings = MagicMock()
    mock_settings.agent = "test-agent"
    mock_settings.llm_model = "test-model"
    mock_settings.llm_api_key = "test-api-key"
    mock_settings.llm_base_url = "test-base-url"
    mock_settings.confirmation_mode = True
    mock_settings.enable_default_condenser = False
    mock_settings_store.load.return_value = mock_settings
    mock_get_settings_store.return_value = mock_settings_store
    mock_noop_condenser_instance = MagicMock()
    mock_noop_condenser.return_value = mock_noop_condenser_instance
    mock_check_security.return_value = True
    task_str = "Build a simple web app"
    mock_read_task.return_value = task_str
    mock_run_session.side_effect = [True, False]
    await cli.main_with_loop(loop, mock_args)
    mock_setup_config.assert_called_once_with(mock_args)
    mock_get_settings_store.assert_called_once()
    mock_settings_store.load.assert_called_once()
    mock_check_security.assert_called_once_with(mock_config, "/test/dir")
    mock_read_task.assert_called_once()
    assert mock_run_session.call_count == 2
    first_call_args = mock_run_session.call_args_list[0][0]
    assert first_call_args[0] == loop
    assert first_call_args[1] == mock_config
    assert first_call_args[2] == mock_settings_store
    assert first_call_args[3] == "/test/dir"
    assert isinstance(first_call_args[4], str)
    assert first_call_args[4] == task_str
    second_call_args = mock_run_session.call_args_list[1][0]
    assert second_call_args[0] == loop
    assert second_call_args[1] == mock_config
    assert second_call_args[2] == mock_settings_store
    assert second_call_args[3] == "/test/dir"
    assert second_call_args[4] is None


@pytest.mark.asyncio
@patch("forge.cli.main.setup_config_from_args")
@patch("forge.cli.main.FileSettingsStore.get_instance")
@patch("forge.cli.main.check_folder_security_agreement")
@patch("forge.cli.main.read_task")
@patch("forge.cli.main.run_session")
@patch("forge.cli.main.LLMSummarizingCondenserConfig")
@patch("forge.cli.main.NoOpCondenserConfig")
@patch("forge.cli.main.finalize_config")
@patch("forge.cli.main.aliases_exist_in_shell_config")
async def test_main_with_session_name_passes_name_to_run_session(
    mock_aliases_exist,
    mock_finalize_config,
    mock_noop_condenser,
    mock_llm_condenser,
    mock_run_session,
    mock_read_task,
    mock_check_security,
    mock_get_settings_store,
    mock_setup_config,
):
    """Test main function with a session name passes it to run_session."""
    loop = asyncio.get_running_loop()
    test_session_name = "my_named_session"
    mock_aliases_exist.return_value = True
    mock_args = MagicMock()
    mock_args.agent_cls = None
    mock_args.llm_config = None
    mock_args.name = test_session_name
    mock_args.file = None
    mock_args.conversation = None
    mock_args.log_level = None
    mock_args.config_file = "config.toml"
    mock_args.override_cli_mode = None
    mock_config = MagicMock()
    mock_config.workspace_base = "/test/dir"
    mock_config.cli_multiline_input = False
    mock_setup_config.return_value = mock_config
    mock_settings_store = AsyncMock()
    mock_settings = MagicMock()
    mock_settings.agent = "test-agent"
    mock_settings.llm_model = "test-model"
    mock_settings.llm_api_key = "test-api-key"
    mock_settings.llm_base_url = "test-base-url"
    mock_settings.confirmation_mode = True
    mock_settings.enable_default_condenser = True
    mock_settings_store.load.return_value = mock_settings
    mock_get_settings_store.return_value = mock_settings_store
    mock_llm_condenser_instance = MagicMock()
    mock_llm_condenser.return_value = mock_llm_condenser_instance
    mock_check_security.return_value = True
    mock_read_task.return_value = None
    mock_run_session.return_value = False
    await cli.main_with_loop(loop, mock_args)
    mock_setup_config.assert_called_once_with(mock_args)
    mock_get_settings_store.assert_called_once()
    mock_settings_store.load.assert_called_once()
    mock_check_security.assert_called_once_with(mock_config, "/test/dir")
    mock_read_task.assert_called_once()
    mock_run_session.assert_called_once_with(
        loop,
        mock_config,
        mock_settings_store,
        "/test/dir",
        None,
        session_name=test_session_name,
        skip_banner=False,
        conversation_id=None,
    )


@pytest.mark.asyncio
@patch("forge.cli.main.generate_sid")
@patch("forge.cli.main.create_agent")
@patch("forge.cli.main.create_runtime")
@patch("forge.cli.main.create_memory")
@patch("forge.cli.main.add_mcp_tools_to_agent")
@patch("forge.cli.main.run_agent_until_done")
@patch("forge.cli.main.cleanup_session")
@patch("forge.cli.main.read_prompt_input", new_callable=AsyncMock)
@patch("forge.cli.main.handle_commands", new_callable=AsyncMock)
@patch("forge.core.setup.State.restore_from_session")
@patch("forge.controller.AgentController.__init__")
@patch("forge.cli.main.display_runtime_initialization_message")
@patch("forge.cli.main.display_initialization_animation")
@patch("forge.cli.main.initialize_repository_for_runtime")
@patch("forge.cli.main.display_initial_user_prompt")
@patch("forge.cli.main.finalize_config")
async def test_run_session_with_name_attempts_state_restore(
    mock_finalize_config,
    mock_display_initial_user_prompt,
    mock_initialize_repo,
    mock_display_init_anim,
    mock_display_runtime_init,
    mock_agent_controller_init,
    mock_restore_from_session,
    mock_handle_commands,
    mock_read_prompt_input,
    mock_cleanup_session,
    mock_run_agent_until_done,
    mock_add_mcp_tools,
    mock_create_memory,
    mock_create_runtime,
    mock_create_agent,
    mock_generate_sid,
    mock_config,
    mock_settings_store,
):
    """Test run_session with a session_name attempts to restore state and passes it to AgentController."""
    loop = asyncio.get_running_loop()
    test_session_name = "my_restore_test_session"
    expected_sid = f"sid_for_{test_session_name}"
    mock_generate_sid.return_value = expected_sid
    mock_agent = AsyncMock()
    mock_create_agent.return_value = mock_agent
    mock_runtime = AsyncMock()
    mock_runtime.event_stream = MagicMock()
    mock_runtime.event_stream.sid = expected_sid
    mock_runtime.event_stream.file_store = MagicMock()
    mock_create_runtime.return_value = mock_runtime
    mock_loaded_state = MagicMock(spec=State)
    mock_restore_from_session.return_value = mock_loaded_state
    mock_agent_controller_init.return_value = None
    mock_read_prompt_input.return_value = "/exit"
    mock_handle_commands.return_value = (True, False, False)
    mock_initialize_repo.return_value = "/mocked/repo/dir"
    mock_create_memory.return_value = AsyncMock()
    await cli.run_session(
        loop, mock_config, mock_settings_store, "/test/dir", task_content=None, session_name=test_session_name
    )
    mock_generate_sid.assert_called_once_with(mock_config, test_session_name)
    mock_restore_from_session.assert_called_once_with(expected_sid, mock_runtime.event_stream.file_store)
    mock_agent_controller_init.assert_called_once()
    args, kwargs = mock_agent_controller_init.call_args
    assert kwargs.get("initial_state") == mock_loaded_state


@pytest.mark.asyncio
@patch("forge.cli.main.setup_config_from_args")
@patch("forge.cli.main.FileSettingsStore.get_instance")
@patch("forge.cli.main.check_folder_security_agreement")
@patch("forge.cli.main.read_task")
@patch("forge.cli.main.run_session")
@patch("forge.cli.main.LLMSummarizingCondenserConfig")
@patch("forge.cli.main.NoOpCondenserConfig")
@patch("forge.cli.main.finalize_config")
@patch("forge.cli.main.aliases_exist_in_shell_config")
async def test_main_security_check_fails(
    mock_aliases_exist,
    mock_finalize_config,
    mock_noop_condenser,
    mock_llm_condenser,
    mock_run_session,
    mock_read_task,
    mock_check_security,
    mock_get_settings_store,
    mock_setup_config,
):
    """Test main function when security check fails."""
    loop = asyncio.get_running_loop()
    mock_aliases_exist.return_value = True
    mock_args = MagicMock()
    mock_args.agent_cls = None
    mock_args.llm_config = None
    mock_args.name = None
    mock_args.file = None
    mock_args.conversation = None
    mock_args.log_level = None
    mock_args.config_file = "config.toml"
    mock_args.override_cli_mode = None
    mock_config = MagicMock()
    mock_config.workspace_base = "/test/dir"
    mock_setup_config.return_value = mock_config
    mock_settings_store = AsyncMock()
    mock_settings = MagicMock()
    mock_settings.enable_default_condenser = False
    mock_settings_store.load.return_value = mock_settings
    mock_get_settings_store.return_value = mock_settings_store
    mock_noop_condenser_instance = MagicMock()
    mock_noop_condenser.return_value = mock_noop_condenser_instance
    mock_check_security.return_value = False
    await cli.main_with_loop(loop, mock_args)
    mock_setup_config.assert_called_once_with(mock_args)
    mock_get_settings_store.assert_called_once()
    mock_settings_store.load.assert_called_once()
    mock_check_security.assert_called_once_with(mock_config, "/test/dir")


@pytest.mark.asyncio
@patch("forge.cli.main.setup_config_from_args")
@patch("forge.cli.main.FileSettingsStore.get_instance")
@patch("forge.cli.main.check_folder_security_agreement")
@patch("forge.cli.main.read_task")
@patch("forge.cli.main.run_session")
@patch("forge.cli.main.LLMSummarizingCondenserConfig")
@patch("forge.cli.main.NoOpCondenserConfig")
@patch("forge.cli.main.finalize_config")
@patch("forge.cli.main.aliases_exist_in_shell_config")
async def test_config_loading_order(
    mock_aliases_exist,
    mock_finalize_config,
    mock_noop_condenser,
    mock_llm_condenser,
    mock_run_session,
    mock_read_task,
    mock_check_security,
    mock_get_settings_store,
    mock_setup_config,
):
    """Test the order of configuration loading in the main function.

    This test verifies:
    1. Command line arguments override settings store values
    2. Settings from store are used when command line args are not provided
    3. Default condenser is configured correctly based on settings
    """
    loop = asyncio.get_running_loop()
    mock_aliases_exist.return_value = True
    mock_args = MagicMock()
    mock_args.agent_cls = "cmd-line-agent"
    mock_args.llm_config = None
    mock_args.file = None
    mock_args.log_level = "INFO"
    mock_args.name = None
    mock_args.conversation = None
    mock_args.config_file = "config.toml"
    mock_args.override_cli_mode = None
    mock_read_task.return_value = "Test task"
    mock_config = MagicMock()
    mock_config.workspace_base = "/test/dir"
    mock_config.cli_multiline_input = False
    mock_llm_config = MagicMock()
    mock_llm_config.model = None
    mock_llm_config.api_key = None
    mock_config.get_llm_config = MagicMock(return_value=mock_llm_config)
    mock_config.set_llm_config = MagicMock()
    mock_config.get_agent_config = MagicMock(return_value=MagicMock())
    mock_config.set_agent_config = MagicMock()
    mock_setup_config.return_value = mock_config
    mock_settings_store = AsyncMock()
    mock_settings = MagicMock()
    mock_settings.agent = "settings-agent"
    mock_settings.llm_model = "settings-model"
    mock_settings.llm_api_key = "settings-api-key"
    mock_settings.llm_base_url = "settings-base-url"
    mock_settings.confirmation_mode = True
    mock_settings.enable_default_condenser = True
    mock_settings_store.load.return_value = mock_settings
    mock_get_settings_store.return_value = mock_settings_store
    mock_llm_condenser_instance = MagicMock()
    mock_llm_condenser.return_value = mock_llm_condenser_instance
    mock_check_security.return_value = True
    mock_run_session.return_value = False
    await cli.main_with_loop(loop, mock_args)
    mock_setup_config.assert_called_once_with(mock_args)
    mock_get_settings_store.assert_called_once()
    mock_settings_store.load.assert_called_once()
    mock_config.default_agent = "cmd-line-agent"
    assert mock_config.set_llm_config.called
    llm_config_call = mock_config.set_llm_config.call_args[0][0]
    assert llm_config_call.model == "settings-model"
    assert llm_config_call.api_key == "settings-api-key"
    assert llm_config_call.base_url == "settings-base-url"
    assert mock_config.security.confirmation_mode is True
    assert mock_config.set_agent_config.called
    assert mock_llm_condenser.called
    assert mock_config.enable_default_condenser is True
    mock_run_session.assert_called_once()


@pytest.mark.asyncio
@patch("forge.cli.main.setup_config_from_args")
@patch("forge.cli.main.FileSettingsStore.get_instance")
@patch("forge.cli.main.check_folder_security_agreement")
@patch("forge.cli.main.read_task")
@patch("forge.cli.main.run_session")
@patch("forge.cli.main.LLMSummarizingCondenserConfig")
@patch("forge.cli.main.NoOpCondenserConfig")
@patch("forge.cli.main.finalize_config")
@patch("forge.cli.main.aliases_exist_in_shell_config")
@patch("builtins.open", new_callable=MagicMock)
async def test_main_with_file_option(
    mock_open,
    mock_aliases_exist,
    mock_finalize_config,
    mock_noop_condenser,
    mock_llm_condenser,
    mock_run_session,
    mock_read_task,
    mock_check_security,
    mock_get_settings_store,
    mock_setup_config,
):
    """Test main function with a file option."""
    loop = asyncio.get_running_loop()
    mock_aliases_exist.return_value = True
    mock_args = MagicMock()
    mock_args.agent_cls = None
    mock_args.llm_config = None
    mock_args.name = None
    mock_args.file = "/path/to/test/file.txt"
    mock_args.task = None
    mock_args.conversation = None
    mock_args.log_level = None
    mock_args.config_file = "config.toml"
    mock_args.override_cli_mode = None
    mock_config = MagicMock()
    mock_config.workspace_base = "/test/dir"
    mock_config.cli_multiline_input = False
    mock_setup_config.return_value = mock_config
    mock_settings_store = AsyncMock()
    mock_settings = MagicMock()
    mock_settings.agent = "test-agent"
    mock_settings.llm_model = "test-model"
    mock_settings.llm_api_key = "test-api-key"
    mock_settings.llm_base_url = "test-base-url"
    mock_settings.confirmation_mode = True
    mock_settings.enable_default_condenser = True
    mock_settings_store.load.return_value = mock_settings
    mock_get_settings_store.return_value = mock_settings_store
    mock_llm_condenser_instance = MagicMock()
    mock_llm_condenser.return_value = mock_llm_condenser_instance
    mock_check_security.return_value = True
    mock_file = MagicMock()
    mock_file.__enter__.return_value.read.return_value = "This is a test file content."
    mock_open.return_value = mock_file
    mock_run_session.return_value = False
    await cli.main_with_loop(loop, mock_args)
    mock_setup_config.assert_called_once_with(mock_args)
    mock_get_settings_store.assert_called_once()
    mock_settings_store.load.assert_called_once()
    mock_check_security.assert_called_once_with(mock_config, "/test/dir")
    mock_open.assert_called_once_with("/path/to/test/file.txt", "r", encoding="utf-8")
    mock_run_session.assert_called_once()
    task_str = mock_run_session.call_args[0][4]
    assert "The user has tagged a file '/path/to/test/file.txt'" in task_str
    assert "Please read and understand the following file content first:" in task_str
    assert "This is a test file content." in task_str
    assert "After reviewing the file, please ask the user what they would like to do with it." in task_str
