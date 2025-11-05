"""Unit tests for the setup script functionality."""

from unittest.mock import MagicMock, patch
from openhands.events.action import CmdRunAction, FileReadAction
from openhands.events.event import EventSource
from openhands.events.observation import ErrorObservation, FileReadObservation
from openhands.runtime.base import Runtime


def test_maybe_run_setup_script_executes_action():
    """Test that maybe_run_setup_script executes the action after adding it to the event stream."""
    runtime = MagicMock(spec=Runtime)
    runtime.read.return_value = FileReadObservation(content="#!/bin/bash\necho 'test'", path=".openhands/setup.sh")
    runtime.event_stream = MagicMock()
    runtime.status_callback = None
    with patch.object(Runtime, "maybe_run_setup_script", Runtime.maybe_run_setup_script):
        Runtime.maybe_run_setup_script(runtime)
    runtime.read.assert_called_once_with(FileReadAction(path=".openhands/setup.sh"))
    runtime.event_stream.add_event.assert_called_once()
    args, kwargs = runtime.event_stream.add_event.call_args
    action, source = args
    assert isinstance(action, CmdRunAction)
    assert source == EventSource.ENVIRONMENT
    runtime.run_action.assert_called_once()
    args, kwargs = runtime.run_action.call_args
    action = args[0]
    assert isinstance(action, CmdRunAction)
    assert action.command == "chmod +x .openhands/setup.sh && source .openhands/setup.sh"


def test_maybe_run_setup_script_skips_when_file_not_found():
    """Test that maybe_run_setup_script skips execution when the setup script is not found."""
    runtime = MagicMock(spec=Runtime)
    runtime.read.return_value = ErrorObservation(content="File not found", error_id="")
    runtime.event_stream = MagicMock()
    with patch.object(Runtime, "maybe_run_setup_script", Runtime.maybe_run_setup_script):
        Runtime.maybe_run_setup_script(runtime)
    runtime.read.assert_called_once_with(FileReadAction(path=".openhands/setup.sh"))
    runtime.event_stream.add_event.assert_not_called()
    runtime.run_action.assert_not_called()
