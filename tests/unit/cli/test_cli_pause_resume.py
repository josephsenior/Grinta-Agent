import asyncio
from unittest.mock import MagicMock, call, patch
import pytest
from prompt_toolkit.formatted_text import HTML
from prompt_toolkit.keys import Keys
from openhands.cli.tui import process_agent_pause
from openhands.core.schema import AgentState
from openhands.events import EventSource
from openhands.events.action import ChangeAgentStateAction
from openhands.events.observation import AgentStateChangedObservation


class TestProcessAgentPause:

    @pytest.mark.asyncio
    @patch("openhands.cli.tui.create_input")
    @patch("openhands.cli.tui.print_formatted_text")
    async def test_process_agent_pause_ctrl_p(self, mock_print, mock_create_input):
        """Test that process_agent_pause sets the done event when Ctrl+P is pressed."""
        done = asyncio.Event()
        mock_input = MagicMock()
        mock_create_input.return_value = mock_input
        mock_raw_mode = MagicMock()
        mock_input.raw_mode.return_value = mock_raw_mode
        mock_raw_mode.__enter__ = MagicMock()
        mock_raw_mode.__exit__ = MagicMock()
        mock_attach = MagicMock()
        mock_input.attach.return_value = mock_attach
        mock_attach.__enter__ = MagicMock()
        mock_attach.__exit__ = MagicMock()
        keys_ready_func = None

        def fake_attach(callback):
            nonlocal keys_ready_func
            keys_ready_func = callback
            return mock_attach

        mock_input.attach.side_effect = fake_attach
        task = asyncio.create_task(process_agent_pause(done, event_stream=MagicMock()))
        await asyncio.sleep(0.1)
        assert keys_ready_func is not None
        key_press = MagicMock()
        key_press.key = Keys.ControlP
        mock_input.read_keys.return_value = [key_press]
        keys_ready_func()
        assert done.is_set()
        assert mock_print.call_count == 2
        assert mock_print.call_args_list[0] == call("")
        second_call = mock_print.call_args_list[1][0][0]
        assert isinstance(second_call, HTML)
        assert "Pausing the agent" in str(second_call)
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass


class TestCliPauseResumeInRunSession:

    @pytest.mark.asyncio
    async def test_on_event_async_pause_processing(self):
        """Test that on_event_async processes the pause event when is_paused is set."""
        event = MagicMock()
        event_stream = MagicMock()
        is_paused = asyncio.Event()
        reload_microagents = False
        config = MagicMock()
        with patch("openhands.cli.main.display_event") as mock_display_event, patch(
            "openhands.cli.main.update_usage_metrics"
        ) as mock_update_metrics:

            async def test_func():
                is_paused.set()

                async def on_event_async_test(event):
                    nonlocal reload_microagents, is_paused
                    mock_display_event(event, config)
                    mock_update_metrics(event, usage_metrics=MagicMock())
                    if is_paused.is_set():
                        event_stream.add_event(ChangeAgentStateAction(AgentState.PAUSED), EventSource.USER)

                await on_event_async_test(event)
                event_stream.add_event.assert_called_once()
                args, kwargs = event_stream.add_event.call_args
                action, source = args
                assert isinstance(action, ChangeAgentStateAction)
                assert action.agent_state == AgentState.PAUSED
                assert source == EventSource.USER
                assert is_paused.is_set()

            await test_func()

    @pytest.mark.asyncio
    async def test_awaiting_user_input_paused_skip(self):
        """Test that when is_paused is set, awaiting user input events do not trigger prompting."""
        event = MagicMock()
        event.observation = AgentStateChangedObservation(
            agent_state=AgentState.AWAITING_USER_INPUT, content="Agent awaiting input"
        )
        is_paused = asyncio.Event()
        reload_microagents = False
        mock_prompt_task = MagicMock()

        async def test_func():
            is_paused.set()

            async def on_event_async_test(event):
                nonlocal reload_microagents, is_paused
                if isinstance(event.observation, AgentStateChangedObservation) and event.observation.agent_state in [
                    AgentState.AWAITING_USER_INPUT,
                    AgentState.FINISHED,
                ]:
                    if is_paused.is_set():
                        return
                    mock_prompt_task()

            await on_event_async_test(event)
            mock_prompt_task.assert_not_called()

        await test_func()

    @pytest.mark.asyncio
    async def test_awaiting_confirmation_paused_skip(self):
        """Test that when is_paused is set, awaiting confirmation events do not trigger prompting."""
        event = MagicMock()
        event.observation = AgentStateChangedObservation(
            agent_state=AgentState.AWAITING_USER_CONFIRMATION, content="Agent awaiting confirmation"
        )
        is_paused = asyncio.Event()
        mock_confirmation = MagicMock()

        async def test_func():
            is_paused.set()

            async def on_event_async_test(event):
                nonlocal is_paused
                if (
                    isinstance(event.observation, AgentStateChangedObservation)
                    and event.observation.agent_state == AgentState.AWAITING_USER_CONFIRMATION
                ):
                    if is_paused.is_set():
                        return
                    mock_confirmation()

            await on_event_async_test(event)
            mock_confirmation.assert_not_called()

        await test_func()


class TestCliCommandsPauseResume:

    @pytest.mark.asyncio
    @patch("openhands.cli.commands.handle_resume_command")
    async def test_handle_commands_resume(self, mock_handle_resume):
        """Test that the handle_commands function properly calls handle_resume_command."""
        from openhands.cli.commands import handle_commands

        message = "/resume"
        event_stream = MagicMock()
        usage_metrics = MagicMock()
        sid = "test-session-id"
        config = MagicMock()
        current_dir = "/test/dir"
        settings_store = MagicMock()
        agent_state = AgentState.PAUSED
        mock_handle_resume.return_value = (False, False)
        close_repl, reload_microagents, new_session_requested, _ = await handle_commands(
            message, event_stream, usage_metrics, sid, config, current_dir, settings_store, agent_state
        )
        mock_handle_resume.assert_called_once_with(event_stream, agent_state)
        assert close_repl is False
        assert reload_microagents is False
        assert new_session_requested is False


class TestAgentStatePauseResume:

    @pytest.mark.asyncio
    @patch("openhands.cli.main.display_agent_running_message")
    @patch("openhands.cli.tui.process_agent_pause")
    async def test_agent_running_enables_pause(self, mock_process_agent_pause, mock_display_message):
        """Test that when the agent is running, pause functionality is enabled."""
        event = MagicMock()
        event.observation = AgentStateChangedObservation(agent_state=AgentState.RUNNING, content="Agent is running")
        event_stream = MagicMock()
        is_paused = asyncio.Event()
        loop = MagicMock()
        reload_microagents = False

        async def test_func():

            async def on_event_async_test(event):
                nonlocal reload_microagents
                if (
                    isinstance(event.observation, AgentStateChangedObservation)
                    and event.observation.agent_state == AgentState.RUNNING
                ):
                    mock_display_message()
                    loop.create_task(mock_process_agent_pause(is_paused, event_stream))

            await on_event_async_test(event)
            mock_display_message.assert_called_once()
            loop.create_task.assert_called_once()

        await test_func()

    @pytest.mark.asyncio
    @patch("openhands.cli.main.display_event")
    @patch("openhands.cli.main.update_usage_metrics")
    async def test_pause_event_changes_agent_state(self, mock_update_metrics, mock_display_event):
        """Test that when is_paused is set, a PAUSED state change event is added to the stream."""
        event = MagicMock()
        event_stream = MagicMock()
        is_paused = asyncio.Event()
        config = MagicMock()
        reload_microagents = False
        is_paused.set()

        async def test_func():

            async def on_event_async_test(event):
                nonlocal reload_microagents
                mock_display_event(event, config)
                mock_update_metrics(event, MagicMock())
                if is_paused.is_set():
                    event_stream.add_event(ChangeAgentStateAction(AgentState.PAUSED), EventSource.USER)
                    is_paused.clear()

            await on_event_async_test(event)
            event_stream.add_event.assert_called_once()
            args, kwargs = event_stream.add_event.call_args
            action, source = args
            assert isinstance(action, ChangeAgentStateAction)
            assert action.agent_state == AgentState.PAUSED
            assert source == EventSource.USER
            assert not is_paused.is_set()

        await test_func()

    @pytest.mark.asyncio
    async def test_paused_agent_awaits_input(self):
        """Test that when the agent is paused, it awaits user input."""
        event = MagicMock()
        event.observation = AgentStateChangedObservation(
            agent_state=AgentState.PAUSED, content="Agent state changed to PAUSED"
        )
        is_paused = asyncio.Event()
        mock_prompt_task = MagicMock()

        async def test_func():

            async def on_event_async_test(event):
                nonlocal is_paused
                if (
                    isinstance(event.observation, AgentStateChangedObservation)
                    and event.observation.agent_state == AgentState.PAUSED
                ):
                    is_paused.clear()
                    mock_prompt_task(event.observation.agent_state)

            is_paused.set()
            await on_event_async_test(event)
            assert not is_paused.is_set()
            mock_prompt_task.assert_called_once_with(AgentState.PAUSED)

        await test_func()
