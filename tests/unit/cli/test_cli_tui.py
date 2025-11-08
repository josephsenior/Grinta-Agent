from unittest.mock import MagicMock, Mock, patch
import pytest
from forge.cli.tui import (
    CustomDiffLexer,
    UsageMetrics,
    UserCancelledError,
    _render_basic_markdown,
    display_banner,
    display_command,
    display_event,
    display_mcp_action,
    display_mcp_errors,
    display_mcp_observation,
    display_message,
    display_runtime_initialization_message,
    display_shutdown_message,
    display_status,
    display_usage_metrics,
    display_welcome_message,
    get_session_duration,
    read_confirmation_input,
)
from forge.core.config import ForgeConfig
from forge.events import EventSource
from forge.events.action import Action, ActionConfirmationStatus, CmdRunAction, MCPAction, MessageAction
from forge.events.observation import CmdOutputObservation, FileEditObservation, FileReadObservation, MCPObservation
from forge.llm.metrics import Metrics
from forge.mcp_client.error_collector import MCPError


class TestDisplayFunctions:

    @patch("forge.cli.tui.print_formatted_text")
    def test_display_runtime_initialization_message_local(self, mock_print):
        display_runtime_initialization_message("local")
        assert mock_print.call_count == 3
        args, kwargs = mock_print.call_args_list[1]
        assert "Starting local runtime" in str(args[0])

    @patch("forge.cli.tui.print_formatted_text")
    def test_display_runtime_initialization_message_docker(self, mock_print):
        display_runtime_initialization_message("docker")
        assert mock_print.call_count == 3
        args, kwargs = mock_print.call_args_list[1]
        assert "Starting Docker runtime" in str(args[0])

    @patch("forge.cli.tui.print_formatted_text")
    def test_display_banner(self, mock_print):
        session_id = "test-session-id"
        display_banner(session_id)
        assert mock_print.call_count >= 3
        args, kwargs = mock_print.call_args_list[-2]
        assert session_id in str(args[0])
        assert "Initialized conversation" in str(args[0])

    @patch("forge.cli.tui.print_formatted_text")
    def test_display_welcome_message(self, mock_print):
        display_welcome_message()
        assert mock_print.call_count == 2
        args, kwargs = mock_print.call_args_list[0]
        assert "Let's start building" in str(args[0])

    @patch("forge.cli.tui.print_formatted_text")
    def test_display_welcome_message_with_message(self, mock_print):
        message = "Test message"
        display_welcome_message(message)
        assert mock_print.call_count == 2
        args, kwargs = mock_print.call_args_list[0]
        message_text = str(args[0])
        assert "Let's start building" in message_text
        args, kwargs = mock_print.call_args_list[1]
        message_text = str(args[0])
        assert "Test message" in message_text
        assert "Type /help for help" in message_text

    @patch("forge.cli.tui.print_formatted_text")
    def test_display_welcome_message_without_message(self, mock_print):
        display_welcome_message()
        assert mock_print.call_count == 2
        args, kwargs = mock_print.call_args_list[0]
        message_text = str(args[0])
        assert "Let's start building" in message_text
        args, kwargs = mock_print.call_args_list[1]
        message_text = str(args[0])
        assert "What do you want to build?" in message_text
        assert "Type /help for help" in message_text

    def test_display_event_message_action(self):
        config = MagicMock(spec=ForgeConfig)
        message = MessageAction(content="Test message")
        message._source = EventSource.AGENT
        display_event(message, config)

    @patch("forge.cli.tui.display_command")
    def test_display_event_cmd_action(self, mock_display_command):
        config = MagicMock(spec=ForgeConfig)
        cmd_action = CmdRunAction(command="echo test")
        cmd_action.confirmation_state = ActionConfirmationStatus.AWAITING_CONFIRMATION
        display_event(cmd_action, config)
        mock_display_command.assert_called_once_with(cmd_action)

    @patch("forge.cli.tui.display_command")
    @patch("forge.cli.tui.initialize_streaming_output")
    def test_display_event_cmd_action_confirmed(self, mock_init_streaming, mock_display_command):
        config = MagicMock(spec=ForgeConfig)
        cmd_action = CmdRunAction(command="echo test")
        cmd_action.confirmation_state = ActionConfirmationStatus.CONFIRMED
        display_event(cmd_action, config)
        mock_display_command.assert_not_called()
        mock_init_streaming.assert_called_once()

    @patch("forge.cli.tui.display_command_output")
    def test_display_event_cmd_output(self, mock_display_output):
        config = MagicMock(spec=ForgeConfig)
        cmd_output = CmdOutputObservation(content="Test output", command="echo test")
        display_event(cmd_output, config)
        mock_display_output.assert_called_once_with("Test output")

    @patch("forge.cli.tui.display_file_edit")
    def test_display_event_file_edit_observation(self, mock_display_file_edit):
        config = MagicMock(spec=ForgeConfig)
        file_edit_obs = FileEditObservation(path="test.py", content="print('hello')")
        display_event(file_edit_obs, config)
        mock_display_file_edit.assert_called_once_with(file_edit_obs)

    @patch("forge.cli.tui.display_file_read")
    def test_display_event_file_read(self, mock_display_file_read):
        config = MagicMock(spec=ForgeConfig)
        file_read = FileReadObservation(path="test.py", content="print('hello')")
        display_event(file_read, config)
        mock_display_file_read.assert_called_once_with(file_read)

    def test_display_event_thought(self):
        config = MagicMock(spec=ForgeConfig)
        action = Action()
        action.thought = "Thinking about this..."
        display_event(action, config)

    @patch("forge.cli.tui.display_mcp_action")
    def test_display_event_mcp_action(self, mock_display_mcp_action):
        config = MagicMock(spec=ForgeConfig)
        mcp_action = MCPAction(name="test_tool", arguments={"param": "value"})
        display_event(mcp_action, config)
        mock_display_mcp_action.assert_called_once_with(mcp_action)

    @patch("forge.cli.tui.display_mcp_observation")
    def test_display_event_mcp_observation(self, mock_display_mcp_observation):
        config = MagicMock(spec=ForgeConfig)
        mcp_observation = MCPObservation(content="Tool result", name="test_tool", arguments={"param": "value"})
        display_event(mcp_observation, config)
        mock_display_mcp_observation.assert_called_once_with(mcp_observation)

    @patch("forge.cli.tui.print_container")
    def test_display_mcp_action(self, mock_print_container):
        mcp_action = MCPAction(name="test_tool", arguments={"param": "value"})
        display_mcp_action(mcp_action)
        mock_print_container.assert_called_once()
        container = mock_print_container.call_args[0][0]
        assert "test_tool" in container.body.text
        assert "param" in container.body.text

    @patch("forge.cli.tui.print_container")
    def test_display_mcp_action_no_args(self, mock_print_container):
        mcp_action = MCPAction(name="test_tool")
        display_mcp_action(mcp_action)
        mock_print_container.assert_called_once()
        container = mock_print_container.call_args[0][0]
        assert "test_tool" in container.body.text
        assert "Arguments" not in container.body.text

    @patch("forge.cli.tui.print_container")
    def test_display_mcp_observation(self, mock_print_container):
        mcp_observation = MCPObservation(content="Tool result", name="test_tool", arguments={"param": "value"})
        display_mcp_observation(mcp_observation)
        mock_print_container.assert_called_once()
        container = mock_print_container.call_args[0][0]
        assert "test_tool" in container.body.text
        assert "Tool result" in container.body.text

    @patch("forge.cli.tui.print_container")
    def test_display_mcp_observation_no_content(self, mock_print_container):
        mcp_observation = MCPObservation(content="", name="test_tool")
        display_mcp_observation(mcp_observation)
        mock_print_container.assert_called_once()
        container = mock_print_container.call_args[0][0]
        assert "No output" in container.body.text

    @patch("forge.cli.tui.print_formatted_text")
    def test_display_message(self, mock_print):
        message = "Test message"
        display_message(message)
        mock_print.assert_called()
        args, kwargs = mock_print.call_args
        assert message in str(args[0])

    @patch("forge.cli.tui.print_container")
    def test_display_command_awaiting_confirmation(self, mock_print_container):
        cmd_action = CmdRunAction(command="echo test")
        cmd_action.confirmation_state = ActionConfirmationStatus.AWAITING_CONFIRMATION
        display_command(cmd_action)
        mock_print_container.assert_called_once()
        container = mock_print_container.call_args[0][0]
        assert "echo test" in container.body.text


class TestInteractiveCommandFunctions:

    @patch("forge.cli.tui.print_container")
    def test_display_usage_metrics(self, mock_print_container):
        metrics = UsageMetrics()
        metrics.total_cost = 1.25
        metrics.total_input_tokens = 1000
        metrics.total_output_tokens = 2000
        display_usage_metrics(metrics)
        mock_print_container.assert_called_once()

    def test_get_session_duration(self):
        import time

        current_time = time.time()
        one_hour_ago = current_time - 3600
        duration = get_session_duration(one_hour_ago)
        assert "1h" in duration
        assert "0m" in duration
        assert "0s" in duration

    @patch("forge.cli.tui.print_formatted_text")
    @patch("forge.cli.tui.get_session_duration")
    def test_display_shutdown_message(self, mock_get_duration, mock_print):
        mock_get_duration.return_value = "1 hour 5 minutes"
        metrics = UsageMetrics()
        metrics.total_cost = 1.25
        session_id = "test-session-id"
        display_shutdown_message(metrics, session_id)
        assert mock_print.call_count >= 3
        assert mock_get_duration.call_count == 1

    @patch("forge.cli.tui.display_usage_metrics")
    def test_display_status(self, mock_display_metrics):
        metrics = UsageMetrics()
        session_id = "test-session-id"
        display_status(metrics, session_id)
        mock_display_metrics.assert_called_once_with(metrics)


class TestCustomDiffLexer:

    def test_custom_diff_lexer_plus_line(self):
        lexer = CustomDiffLexer()
        document = Mock()
        document.lines = ["+added line"]
        line_style = lexer.lex_document(document)(0)
        assert line_style[0][0] == "ansigreen"
        assert line_style[0][1] == "+added line"

    def test_custom_diff_lexer_minus_line(self):
        lexer = CustomDiffLexer()
        document = Mock()
        document.lines = ["-removed line"]
        line_style = lexer.lex_document(document)(0)
        assert line_style[0][0] == "ansired"
        assert line_style[0][1] == "-removed line"

    def test_custom_diff_lexer_metadata_line(self):
        lexer = CustomDiffLexer()
        document = Mock()
        document.lines = ["[Existing file]"]
        line_style = lexer.lex_document(document)(0)
        assert line_style[0][0] == "bold"
        assert line_style[0][1] == "[Existing file]"

    def test_custom_diff_lexer_normal_line(self):
        lexer = CustomDiffLexer()
        document = Mock()
        document.lines = ["normal line"]
        line_style = lexer.lex_document(document)(0)
        assert line_style[0][0] == ""
        assert line_style[0][1] == "normal line"


class TestUsageMetrics:

    def test_usage_metrics_initialization(self):
        metrics = UsageMetrics()
        assert isinstance(metrics.metrics, Metrics)
        assert metrics.session_init_time > 0


class TestUserCancelledError:

    def test_user_cancelled_error(self):
        error = UserCancelledError()
        assert isinstance(error, Exception)


class TestReadConfirmationInput:

    @pytest.mark.asyncio
    @patch("forge.cli.tui.cli_confirm")
    async def test_read_confirmation_input_yes(self, mock_confirm):
        mock_confirm.return_value = 0
        cfg = MagicMock()
        cfg.cli = MagicMock(vi_mode=False)
        result = await read_confirmation_input(config=cfg, security_risk="LOW")
        assert result == "yes"

    @pytest.mark.asyncio
    @patch("forge.cli.tui.cli_confirm")
    async def test_read_confirmation_input_no(self, mock_confirm):
        mock_confirm.return_value = 1
        cfg = MagicMock()
        cfg.cli = MagicMock(vi_mode=False)
        result = await read_confirmation_input(config=cfg, security_risk="MEDIUM")
        assert result == "no"

    @pytest.mark.asyncio
    @patch("forge.cli.tui.cli_confirm")
    async def test_read_confirmation_input_smart(self, mock_confirm):
        mock_confirm.return_value = 2


class TestMarkdownRendering:

    def test_empty_string(self):
        assert _render_basic_markdown("") == ""

    def test_plain_text(self):
        assert _render_basic_markdown("hello world") == "hello world"

    def test_bold(self):
        assert _render_basic_markdown("**bold**") == "<b>bold</b>"

    def test_underline(self):
        assert _render_basic_markdown("__under__") == "<u>under</u>"

    def test_combined(self):
        assert _render_basic_markdown("mix **bold** and __under__ here") == "mix <b>bold</b> and <u>under</u> here"

    def test_html_is_escaped(self):
        assert _render_basic_markdown("<script>alert(1)</script>") == "&lt;script&gt;alert(1)&lt;/script&gt;"

    def test_bold_with_special_chars(self):
        assert _render_basic_markdown("**a < b & c > d**") == "<b>a &lt; b &amp; c &gt; d</b>"


"Tests for CLI TUI MCP functionality."


class TestMCPTUIDisplay:
    """Test MCP TUI display functions."""

    @patch("forge.cli.tui.print_container")
    def test_display_mcp_action_with_arguments(self, mock_print_container):
        """Test displaying MCP action with arguments."""
        mcp_action = MCPAction(name="test_tool", arguments={"param1": "value1", "param2": 42})
        display_mcp_action(mcp_action)
        mock_print_container.assert_called_once()
        container = mock_print_container.call_args[0][0]
        assert "test_tool" in container.body.text
        assert "param1" in container.body.text
        assert "value1" in container.body.text

    @patch("forge.cli.tui.print_container")
    def test_display_mcp_observation_with_content(self, mock_print_container):
        """Test displaying MCP observation with content."""
        mcp_observation = MCPObservation(
            content="Tool execution successful", name="test_tool", arguments={"param": "value"}
        )
        display_mcp_observation(mcp_observation)
        mock_print_container.assert_called_once()
        container = mock_print_container.call_args[0][0]
        assert "test_tool" in container.body.text
        assert "Tool execution successful" in container.body.text

    @patch("forge.cli.tui.print_formatted_text")
    @patch("forge.cli.tui.mcp_error_collector")
    def test_display_mcp_errors_no_errors(self, mock_collector, mock_print):
        """Test displaying MCP errors when none exist."""
        mock_collector.get_errors.return_value = []
        display_mcp_errors()
        mock_print.assert_called_once()
        call_args = mock_print.call_args[0][0]
        assert "No MCP errors detected" in str(call_args)

    @patch("forge.cli.tui.print_container")
    @patch("forge.cli.tui.print_formatted_text")
    @patch("forge.cli.tui.mcp_error_collector")
    def test_display_mcp_errors_with_errors(self, mock_collector, mock_print, mock_print_container):
        """Test displaying MCP errors when some exist."""
        error1 = MCPError(
            timestamp=1234567890.0,
            server_name="test-server-1",
            server_type="stdio",
            error_message="Connection failed",
            exception_details="Socket timeout",
        )
        error2 = MCPError(
            timestamp=1234567891.0, server_name="test-server-2", server_type="sse", error_message="Server unreachable"
        )
        mock_collector.get_errors.return_value = [error1, error2]
        display_mcp_errors()
        assert mock_print.call_count >= 1
        header_call = mock_print.call_args_list[0][0][0]
        assert "2 MCP error(s) detected" in str(header_call)
        assert mock_print_container.call_count == 2
