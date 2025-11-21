from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest
from prompt_toolkit.formatted_text import HTML

from forge.cli.commands import (
    display_mcp_servers,
    handle_commands,
    handle_exit_command,
    handle_help_command,
    handle_init_command,
    handle_mcp_command,
    handle_new_command,
    handle_resume_command,
    handle_settings_command,
    handle_status_command,
)
from forge.cli.tui import UsageMetrics
from forge.core.config import ForgeConfig
from forge.core.config.mcp_config import MCPConfig
from forge.core.schemas import AgentState
from forge.events import EventSource
from forge.events.action import ChangeAgentStateAction, MessageAction
from forge.events.stream import EventStream
from forge.storage.settings.file_settings_store import FileSettingsStore


def _build_config(runtime: str = "local", mcp_config: MCPConfig | None = None):
    config = MagicMock(spec=ForgeConfig)
    config.cli = SimpleNamespace(vi_mode=False)
    config.runtime = runtime
    config.default_agent = "codeact-agent"
    config.default_model = "claude-3-5-sonnet"
    config.security = SimpleNamespace(confirmation_mode=False)
    config.enable_default_condenser = False
    config.file_store_path = "/tmp"
    config.get_llm_config.return_value = SimpleNamespace(
        model=config.default_model, api_key=""
    )
    config.mcp = mcp_config or MCPConfig()
    return config


def _build_usage_metrics():
    metrics = MagicMock(spec=UsageMetrics)
    metrics.session_init_time = 0
    metrics.session_duration = 0
    metrics.session_inputs = 0
    metrics.session_tokens = 0
    return metrics


class TestHandleCommands:
    @pytest.fixture
    def mock_dependencies(self):
        event_stream = MagicMock(spec=EventStream)
        usage_metrics = _build_usage_metrics()
        sid = "test-session-id"
        config = _build_config()
        current_dir = "/test/dir"
        settings_store = MagicMock(spec=FileSettingsStore)
        agent_state = AgentState.RUNNING
        return {
            "event_stream": event_stream,
            "usage_metrics": usage_metrics,
            "sid": sid,
            "config": config,
            "current_dir": current_dir,
            "settings_store": settings_store,
            "agent_state": agent_state,
        }

    @pytest.mark.asyncio
    @patch("forge.cli.commands.handle_exit_command")
    async def test_handle_exit_command(self, mock_handle_exit, mock_dependencies):
        mock_handle_exit.return_value = True
        close_repl, reload_microagents, new_session, _ = await handle_commands(
            "/exit", **mock_dependencies
        )
        mock_handle_exit.assert_called_once_with(
            mock_dependencies["config"],
            mock_dependencies["event_stream"],
            mock_dependencies["usage_metrics"],
            mock_dependencies["sid"],
        )
        assert close_repl is True
        assert reload_microagents is False
        assert new_session is False

    @pytest.mark.asyncio
    @patch("forge.cli.commands.handle_help_command")
    async def test_handle_help_command(self, mock_handle_help, mock_dependencies):
        mock_handle_help.return_value = (False, False, False)
        close_repl, reload_microagents, new_session, _ = await handle_commands(
            "/help", **mock_dependencies
        )
        mock_handle_help.assert_called_once()
        assert close_repl is False
        assert reload_microagents is False
        assert new_session is False

    @pytest.mark.asyncio
    @patch("forge.cli.commands.handle_init_command")
    async def test_handle_init_command(self, mock_handle_init, mock_dependencies):
        mock_handle_init.return_value = (True, True)
        close_repl, reload_microagents, new_session, _ = await handle_commands(
            "/init", **mock_dependencies
        )
        mock_handle_init.assert_called_once_with(
            mock_dependencies["config"],
            mock_dependencies["event_stream"],
            mock_dependencies["current_dir"],
        )
        assert close_repl is True
        assert reload_microagents is True
        assert new_session is False

    @pytest.mark.asyncio
    @patch("forge.cli.commands.handle_status_command")
    async def test_handle_status_command(self, mock_handle_status, mock_dependencies):
        mock_handle_status.return_value = (False, False, False)
        close_repl, reload_microagents, new_session, _ = await handle_commands(
            "/status", **mock_dependencies
        )
        mock_handle_status.assert_called_once_with(
            mock_dependencies["usage_metrics"], mock_dependencies["sid"]
        )
        assert close_repl is False
        assert reload_microagents is False
        assert new_session is False

    @pytest.mark.asyncio
    @patch("forge.cli.commands.handle_new_command")
    async def test_handle_new_command(self, mock_handle_new, mock_dependencies):
        mock_handle_new.return_value = (True, True)
        close_repl, reload_microagents, new_session, _ = await handle_commands(
            "/new", **mock_dependencies
        )
        mock_handle_new.assert_called_once_with(
            mock_dependencies["config"],
            mock_dependencies["event_stream"],
            mock_dependencies["usage_metrics"],
            mock_dependencies["sid"],
        )
        assert close_repl is True
        assert reload_microagents is False
        assert new_session is True

    @pytest.mark.asyncio
    @patch("forge.cli.commands.handle_settings_command")
    async def test_handle_settings_command(
        self, mock_handle_settings, mock_dependencies
    ):
        close_repl, reload_microagents, new_session, _ = await handle_commands(
            "/settings", **mock_dependencies
        )
        mock_handle_settings.assert_called_once_with(
            mock_dependencies["config"], mock_dependencies["settings_store"]
        )
        assert close_repl is False
        assert reload_microagents is False
        assert new_session is False

    @pytest.mark.asyncio
    @patch("forge.cli.commands.handle_mcp_command")
    async def test_handle_mcp_command(self, mock_handle_mcp, mock_dependencies):
        close_repl, reload_microagents, new_session, _ = await handle_commands(
            "/mcp", **mock_dependencies
        )
        mock_handle_mcp.assert_called_once_with(mock_dependencies["config"])
        assert close_repl is False
        assert reload_microagents is False
        assert new_session is False

    @pytest.mark.asyncio
    async def test_handle_unknown_command(self, mock_dependencies):
        user_message = "Hello, this is not a command"
        close_repl, reload_microagents, new_session, _ = await handle_commands(
            user_message, **mock_dependencies
        )
        mock_dependencies["event_stream"].add_event.assert_called_once()
        args, kwargs = mock_dependencies["event_stream"].add_event.call_args
        assert isinstance(args[0], MessageAction)
        assert args[0].content == user_message
        assert args[1] == EventSource.USER
        assert close_repl is True
        assert reload_microagents is False
        assert new_session is False


class TestHandleExitCommand:
    @patch("forge.cli.commands.cli_confirm")
    @patch("forge.cli.commands.display_shutdown_message")
    def test_exit_with_confirmation(self, mock_display_shutdown, mock_cli_confirm):
        config = _build_config()
        event_stream = MagicMock(spec=EventStream)
        usage_metrics = _build_usage_metrics()
        sid = "test-session-id"
        mock_cli_confirm.return_value = 0
        result = handle_exit_command(config, event_stream, usage_metrics, sid)
        mock_cli_confirm.assert_called_once()
        event_stream.add_event.assert_called_once()
        args, kwargs = event_stream.add_event.call_args
        assert isinstance(args[0], ChangeAgentStateAction)
        assert args[0].agent_state == AgentState.STOPPED
        assert args[1] == EventSource.ENVIRONMENT
        mock_display_shutdown.assert_called_once_with(usage_metrics, sid)
        assert result is True

    @patch("forge.cli.commands.cli_confirm")
    @patch("forge.cli.commands.display_shutdown_message")
    def test_exit_without_confirmation(self, mock_display_shutdown, mock_cli_confirm):
        config = _build_config()
        event_stream = MagicMock(spec=EventStream)
        usage_metrics = _build_usage_metrics()
        sid = "test-session-id"
        mock_cli_confirm.return_value = 1
        result = handle_exit_command(config, event_stream, usage_metrics, sid)
        mock_cli_confirm.assert_called_once()
        event_stream.add_event.assert_not_called()
        mock_display_shutdown.assert_not_called()
        assert result is False


class TestHandleHelpCommand:
    @patch("forge.cli.commands.display_help")
    def test_help_command(self, mock_display_help):
        handle_help_command()
        mock_display_help.assert_called_once()


class TestDisplayMcpServers:
    @patch("forge.cli.commands.print_formatted_text")
    def test_display_mcp_servers_no_servers(self, mock_print):
        from forge.core.config.mcp_config import MCPConfig

        config = _build_config(mcp_config=MCPConfig())
        display_mcp_servers(config)
        mock_print.assert_called_once()
        call_args = mock_print.call_args[0][0]
        assert "No custom MCP servers configured" in call_args
        assert (
            "https://docs.all-hands.dev/usage/how-to/cli-mode#using-mcp-servers"
            in call_args
        )

    @patch("forge.cli.commands.print_formatted_text")
    def test_display_mcp_servers_with_servers(self, mock_print):
        from forge.core.config.mcp_config import (
            MCPConfig,
            MCPSHTTPServerConfig,
            MCPSSEServerConfig,
            MCPStdioServerConfig,
        )

        config = _build_config(
            mcp_config=MCPConfig(
            sse_servers=[MCPSSEServerConfig(url="https://example.com/sse")],
            stdio_servers=[MCPStdioServerConfig(name="duckduckgo", command="npx")],
            shttp_servers=[MCPSHTTPServerConfig(url="http://localhost:3000/mcp")],
            )
        )
        display_mcp_servers(config)
        assert mock_print.call_count >= 4
        first_call = mock_print.call_args_list[0][0][0]
        assert "Configured MCP servers:" in first_call
        assert "SSE servers: 1" in first_call
        assert "Stdio servers: 1" in first_call
        assert "SHTTP servers: 1" in first_call
        assert "Total: 3" in first_call


class TestHandleMcpCommand:
    @pytest.mark.asyncio
    @patch("forge.cli.commands.cli_confirm")
    @patch("forge.cli.commands.display_mcp_servers")
    async def test_handle_mcp_command_list_action(self, mock_display, mock_cli_confirm):
        config = _build_config()
        mock_cli_confirm.return_value = 0
        await handle_mcp_command(config)
        mock_cli_confirm.assert_called_once_with(
            config,
            "MCP Server Configuration",
            [
                "List configured servers",
                "Add new server",
                "Remove server",
                "View errors",
                "Go back",
            ],
        )
        mock_display.assert_called_once_with(config)


class TestHandleStatusCommand:
    @patch("forge.cli.commands.display_status")
    def test_status_command(self, mock_display_status):
        usage_metrics = _build_usage_metrics()
        sid = "test-session-id"
        handle_status_command(usage_metrics, sid)
        mock_display_status.assert_called_once_with(usage_metrics, sid)


class TestHandleNewCommand:
    @patch("forge.cli.commands.cli_confirm")
    @patch("forge.cli.commands.display_shutdown_message")
    def test_new_with_confirmation(self, mock_display_shutdown, mock_cli_confirm):
        config = _build_config()
        event_stream = MagicMock(spec=EventStream)
        usage_metrics = _build_usage_metrics()
        sid = "test-session-id"
        mock_cli_confirm.return_value = 0
        close_repl, new_session = handle_new_command(
            config, event_stream, usage_metrics, sid
        )
        mock_cli_confirm.assert_called_once()
        event_stream.add_event.assert_called_once()
        args, kwargs = event_stream.add_event.call_args
        assert isinstance(args[0], ChangeAgentStateAction)
        assert args[0].agent_state == AgentState.STOPPED
        assert args[1] == EventSource.ENVIRONMENT
        mock_display_shutdown.assert_called_once_with(usage_metrics, sid)
        assert close_repl is True
        assert new_session is True

    @patch("forge.cli.commands.cli_confirm")
    @patch("forge.cli.commands.display_shutdown_message")
    def test_new_without_confirmation(self, mock_display_shutdown, mock_cli_confirm):
        config = _build_config()
        event_stream = MagicMock(spec=EventStream)
        usage_metrics = _build_usage_metrics()
        sid = "test-session-id"
        mock_cli_confirm.return_value = 1
        close_repl, new_session = handle_new_command(
            config, event_stream, usage_metrics, sid
        )
        mock_cli_confirm.assert_called_once()
        event_stream.add_event.assert_not_called()
        mock_display_shutdown.assert_not_called()
        assert close_repl is False
        assert new_session is False


class TestHandleInitCommand:
    @pytest.mark.asyncio
    @patch("forge.cli.commands.init_repository")
    async def test_init_local_runtime_successful(self, mock_init_repository):
        config = _build_config(runtime="local")
        event_stream = MagicMock(spec=EventStream)
        current_dir = "/test/dir"
        mock_init_repository.return_value = True
        close_repl, reload_microagents = await handle_init_command(
            config, event_stream, current_dir
        )
        mock_init_repository.assert_called_once_with(config, current_dir)
        event_stream.add_event.assert_called_once()
        args, kwargs = event_stream.add_event.call_args
        assert isinstance(args[0], MessageAction)
        assert "Please explore this repository" in args[0].content
        assert args[1] == EventSource.USER
        assert close_repl is True
        assert reload_microagents is True

    @pytest.mark.asyncio
    @patch("forge.cli.commands.init_repository")
    async def test_init_local_runtime_unsuccessful(self, mock_init_repository):
        config = _build_config(runtime="local")
        event_stream = MagicMock(spec=EventStream)
        current_dir = "/test/dir"
        mock_init_repository.return_value = False
        close_repl, reload_microagents = await handle_init_command(
            config, event_stream, current_dir
        )
        mock_init_repository.assert_called_once_with(config, current_dir)
        event_stream.add_event.assert_not_called()
        assert close_repl is False
        assert reload_microagents is False

    @pytest.mark.asyncio
    @patch("forge.cli.commands.print_formatted_text")
    @patch("forge.cli.commands.init_repository")
    async def test_init_non_local_runtime(self, mock_init_repository, mock_print):
        config = _build_config(runtime="remote")
        event_stream = MagicMock(spec=EventStream)
        current_dir = "/test/dir"
        close_repl, reload_microagents = await handle_init_command(
            config, event_stream, current_dir
        )
        mock_init_repository.assert_not_called()
        mock_print.assert_called_once()
        event_stream.add_event.assert_not_called()
        assert close_repl is False
        assert reload_microagents is False


class TestHandleSettingsCommand:
    @pytest.mark.asyncio
    @patch("forge.cli.commands.display_settings")
    @patch("forge.cli.commands.cli_confirm")
    @patch("forge.cli.commands.modify_llm_settings_basic")
    async def test_settings_basic_with_changes(
        self, mock_modify_basic, mock_cli_confirm, mock_display_settings
    ):
        config = _build_config()
        settings_store = MagicMock(spec=FileSettingsStore)
        mock_cli_confirm.return_value = 0
        await handle_settings_command(config, settings_store)
        mock_display_settings.assert_called_once_with(config)
        mock_cli_confirm.assert_called_once()
        mock_modify_basic.assert_called_once_with(config, settings_store)

    @pytest.mark.asyncio
    @patch("forge.cli.commands.display_settings")
    @patch("forge.cli.commands.cli_confirm")
    @patch("forge.cli.commands.modify_llm_settings_basic")
    async def test_settings_basic_without_changes(
        self, mock_modify_basic, mock_cli_confirm, mock_display_settings
    ):
        config = _build_config()
        settings_store = MagicMock(spec=FileSettingsStore)
        mock_cli_confirm.return_value = 0
        await handle_settings_command(config, settings_store)
        mock_display_settings.assert_called_once_with(config)
        mock_cli_confirm.assert_called_once()
        mock_modify_basic.assert_called_once_with(config, settings_store)

    @pytest.mark.asyncio
    @patch("forge.cli.commands.display_settings")
    @patch("forge.cli.commands.cli_confirm")
    @patch("forge.cli.commands.modify_llm_settings_advanced")
    async def test_settings_advanced_with_changes(
        self, mock_modify_advanced, mock_cli_confirm, mock_display_settings
    ):
        config = _build_config()
        settings_store = MagicMock(spec=FileSettingsStore)
        mock_cli_confirm.return_value = 1
        await handle_settings_command(config, settings_store)
        mock_display_settings.assert_called_once_with(config)
        mock_cli_confirm.assert_called_once()
        mock_modify_advanced.assert_called_once_with(config, settings_store)

    @pytest.mark.asyncio
    @patch("forge.cli.commands.display_settings")
    @patch("forge.cli.commands.cli_confirm")
    @patch("forge.cli.commands.modify_llm_settings_advanced")
    async def test_settings_advanced_without_changes(
        self, mock_modify_advanced, mock_cli_confirm, mock_display_settings
    ):
        config = _build_config()
        settings_store = MagicMock(spec=FileSettingsStore)
        mock_cli_confirm.return_value = 1
        await handle_settings_command(config, settings_store)
        mock_display_settings.assert_called_once_with(config)
        mock_cli_confirm.assert_called_once()
        mock_modify_advanced.assert_called_once_with(config, settings_store)

    @pytest.mark.asyncio
    @patch("forge.cli.commands.display_settings")
    @patch("forge.cli.commands.cli_confirm")
    async def test_settings_go_back(self, mock_cli_confirm, mock_display_settings):
        config = _build_config()
        settings_store = MagicMock(spec=FileSettingsStore)
        mock_cli_confirm.return_value = 3
        await handle_settings_command(config, settings_store)
        mock_display_settings.assert_called_once_with(config)
        mock_cli_confirm.assert_called_once()


class TestHandleResumeCommand:
    @pytest.mark.asyncio
    @patch("forge.cli.commands.print_formatted_text")
    async def test_handle_resume_command_paused_state(self, mock_print):
        """Test that handle_resume_command works when agent is in PAUSED state."""
        event_stream = MagicMock(spec=EventStream)
        close_repl, new_session_requested = await handle_resume_command(
            event_stream, AgentState.PAUSED
        )
        event_stream.add_event.assert_called_once()
        args, kwargs = event_stream.add_event.call_args
        message_action, source = args
        assert isinstance(message_action, MessageAction)
        assert message_action.content == "continue"
        assert source == EventSource.USER
        assert close_repl is True
        assert new_session_requested is False
        mock_print.assert_not_called()

    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        "invalid_state", [AgentState.RUNNING, AgentState.FINISHED, AgentState.ERROR]
    )
    @patch("forge.cli.commands.print_formatted_text")
    async def test_handle_resume_command_invalid_states(
        self, mock_print, invalid_state
    ):
        """Test that handle_resume_command shows error for all non-PAUSED states."""
        event_stream = MagicMock(spec=EventStream)
        close_repl, new_session_requested = await handle_resume_command(
            event_stream, invalid_state
        )
        event_stream.add_event.assert_not_called()
        assert mock_print.call_count == 1
        error_call = mock_print.call_args_list[0][0][0]
        assert isinstance(error_call, HTML)
        assert "Error: Agent is not paused" in str(error_call)
        assert "/resume command is only available when agent is paused" in str(
            error_call
        )
        assert close_repl is False
        assert new_session_requested is False


class TestMCPErrorHandling:
    """Test MCP error handling in commands."""

    @patch("forge.cli.commands.display_mcp_errors")
    def test_handle_mcp_errors_command(self, mock_display_errors):
        """Test handling MCP errors command."""
        from forge.cli.commands import handle_mcp_errors_command

        handle_mcp_errors_command()
        mock_display_errors.assert_called_once()
