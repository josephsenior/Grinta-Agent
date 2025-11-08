import os
import sys
import tempfile
import time
from pathlib import Path
from unittest.mock import MagicMock, patch
import pytest
from forge.events.action import CmdRunAction
from forge.events.observation import ErrorObservation
from forge.events.observation.commands import CmdOutputObservation
from forge.runtime.utils.bash_constants import TIMEOUT_MESSAGE_TEMPLATE


def get_timeout_suffix(timeout_seconds):
    """Helper function to generate the expected timeout suffix."""
    return f"[The command timed out after {timeout_seconds} seconds. {TIMEOUT_MESSAGE_TEMPLATE}]"


pytestmark = pytest.mark.skipif(sys.platform != "win32", reason="WindowsPowershellSession tests require Windows")


@pytest.fixture
def temp_work_dir():
    """Create a temporary directory for testing."""
    with tempfile.TemporaryDirectory() as temp_dir:
        yield temp_dir


@pytest.fixture
def windows_bash_session(temp_work_dir):
    """Create a WindowsPowershellSession instance for testing."""
    try:
        session = WindowsPowershellSession(work_dir=temp_work_dir, username=None)
    except Exception as e:
        pytest.skip(f"PowerShell runspace unavailable: {e}")
    assert session._initialized
    yield session
    session.close()


if sys.platform == "win32":
    from forge.runtime.utils.windows_bash import WindowsPowershellSession


def test_command_execution(windows_bash_session):
    """Test basic command execution."""
    action = CmdRunAction(command="Write-Output 'Hello World'")
    result = windows_bash_session.execute(action)
    assert isinstance(result, CmdOutputObservation)
    content = result.content.strip()
    assert content == "Hello World"
    assert result.exit_code == 0
    action = CmdRunAction(command="Write-Output `\n    ('hello ' + `\n    'world')")
    result = windows_bash_session.execute(action)
    assert isinstance(result, CmdOutputObservation)
    content = result.content.strip()
    assert content == "hello world"
    assert result.exit_code == 0
    action = CmdRunAction(command='Write-Output "Hello\\n World"')
    result = windows_bash_session.execute(action)
    assert isinstance(result, CmdOutputObservation)
    content = result.content.strip()
    assert content == "Hello\\n World"
    assert result.exit_code == 0


def test_command_with_error(windows_bash_session):
    """Test command execution with an error reported via Write-Error."""
    action = CmdRunAction(command="Write-Error 'Test Error'")
    result = windows_bash_session.execute(action)
    assert isinstance(result, CmdOutputObservation)
    assert "ERROR" in result.content
    assert result.exit_code == 1


def test_command_failure_exit_code(windows_bash_session):
    """Test command execution that results in a non-zero exit code."""
    action = CmdRunAction(command="Get-NonExistentCmdlet")
    result = windows_bash_session.execute(action)
    assert isinstance(result, CmdOutputObservation)
    assert "ERROR" in result.content
    assert "is not recognized" in result.content or "CommandNotFoundException" in result.content
    assert result.exit_code == 1


def test_control_commands(windows_bash_session):
    """Test handling of control commands (not supported)."""
    action_c = CmdRunAction(command="C-c", is_input=True)
    result_c = windows_bash_session.execute(action_c)
    assert isinstance(result_c, ErrorObservation)
    assert "No previous running command to interact with" in result_c.content
    action_long_running = CmdRunAction(command="Start-Sleep -Seconds 100")
    result_long_running = windows_bash_session.execute(action_long_running)
    assert isinstance(result_long_running, CmdOutputObservation)
    assert result_long_running.exit_code == -1
    action_d = CmdRunAction(command="C-d", is_input=True)
    result_d = windows_bash_session.execute(action_d)
    assert "Your input command 'C-d' was NOT processed" in result_d.metadata.suffix
    assert (
        "Direct input to running processes (is_input=True) is not supported by this PowerShell session implementation."
        in result_d.metadata.suffix
    )
    assert "You can use C-c to stop the process" in result_d.metadata.suffix
    action_c = CmdRunAction(command="C-c", is_input=True)
    result_c = windows_bash_session.execute(action_c)
    assert isinstance(result_c, CmdOutputObservation)
    assert result_c.exit_code == 0


def test_command_timeout(windows_bash_session):
    """Test command timeout handling."""
    test_timeout_sec = 1
    action = CmdRunAction(command="Start-Sleep -Seconds 5")
    action.set_hard_timeout(test_timeout_sec)
    start_time = time.monotonic()
    result = windows_bash_session.execute(action)
    duration = time.monotonic() - start_time
    assert isinstance(result, CmdOutputObservation)
    assert "timed out" in result.metadata.suffix.lower()
    assert result.exit_code == -1
    assert abs(duration - test_timeout_sec) < 0.5


def test_long_running_command(windows_bash_session):
    action = CmdRunAction(command="python -u -m http.server 8081")
    action.set_hard_timeout(1)
    result = windows_bash_session.execute(action)
    assert isinstance(result, CmdOutputObservation)
    assert "Serving HTTP on" in result.content
    assert get_timeout_suffix(1.0) in result.metadata.suffix
    assert result.exit_code == -1
    action = CmdRunAction(command="C-c", is_input=True)
    action.set_hard_timeout(30)
    result = windows_bash_session.execute(action)
    assert isinstance(result, CmdOutputObservation)
    assert result.exit_code == 0
    action = CmdRunAction(command="python -u -m http.server 8081")
    action.set_hard_timeout(1)
    result = windows_bash_session.execute(action)
    assert isinstance(result, CmdOutputObservation)
    assert "Serving HTTP on" in result.content
    assert result.exit_code == -1
    action = CmdRunAction(command="C-c", is_input=True)
    action.set_hard_timeout(30)
    result = windows_bash_session.execute(action)
    assert result.exit_code == 0


def test_multiple_commands_rejected_and_individual_execution(windows_bash_session):
    """Test that executing multiple commands separated by newline is rejected,.

    but individual commands (including multiline) execute correctly.
    """
    cmds = [
        "Get-ChildItem",
        'Write-Output "hello`nworld"',
        'Write-Output "hello it\'s me"',
        "Write-Output `\n    'hello' `\n    -NoNewline",
        "Write-Output 'hello`nworld`nare`nyou`nthere?'",
        "Write-Output 'hello`nworld`nare`nyou`n`nthere?'",
        "Write-Output 'hello`nworld `\"'",
    ]
    joined_cmds = "\n".join(cmds)
    action_multi = CmdRunAction(command=joined_cmds)
    result_multi = windows_bash_session.execute(action_multi)
    assert isinstance(result_multi, ErrorObservation)
    assert "ERROR: Cannot execute multiple commands at once" in result_multi.content
    results = []
    for cmd in cmds:
        action_single = CmdRunAction(command=cmd)
        obs = windows_bash_session.execute(action_single)
        assert isinstance(obs, CmdOutputObservation)
        assert obs.exit_code == 0
        results.append(obs.content.strip())


def test_working_directory(windows_bash_session, temp_work_dir):
    """Test working directory handling."""
    initial_cwd = windows_bash_session._cwd
    abs_temp_work_dir = os.path.abspath(temp_work_dir)
    assert initial_cwd == abs_temp_work_dir
    sub_dir_path = Path(abs_temp_work_dir) / "subdir"
    sub_dir_path.mkdir()
    assert sub_dir_path.is_dir()
    action_cd = CmdRunAction(command="Set-Location subdir")
    result_cd = windows_bash_session.execute(action_cd)
    assert isinstance(result_cd, CmdOutputObservation)
    assert result_cd.exit_code == 0
    assert windows_bash_session._cwd.lower().endswith("\\subdir")
    assert result_cd.metadata.working_dir.lower().endswith("\\subdir")
    action_pwd = CmdRunAction(command="(Get-Location).Path")
    result_pwd = windows_bash_session.execute(action_pwd)
    assert isinstance(result_pwd, CmdOutputObservation)
    assert result_pwd.exit_code == 0
    assert result_pwd.content.strip().lower().endswith("\\subdir")
    assert result_pwd.metadata.working_dir.lower().endswith("\\subdir")
    action_cd_back = CmdRunAction(command=f"Set-Location '{abs_temp_work_dir}'")
    result_cd_back = windows_bash_session.execute(action_cd_back)
    assert isinstance(result_cd_back, CmdOutputObservation)
    assert result_cd_back.exit_code == 0
    temp_dir_basename = os.path.basename(abs_temp_work_dir)
    assert windows_bash_session._cwd.lower().endswith(temp_dir_basename.lower())
    assert result_cd_back.metadata.working_dir.lower().endswith(temp_dir_basename.lower())


def test_cleanup(windows_bash_session):
    """Test proper cleanup of resources (runspace)."""
    assert windows_bash_session._initialized
    assert windows_bash_session.runspace is not None
    windows_bash_session.close()
    assert not windows_bash_session._initialized
    assert windows_bash_session.runspace is None
    assert windows_bash_session._closed


def test_syntax_error_handling(windows_bash_session):
    """Test handling of syntax errors in PowerShell commands."""
    action = CmdRunAction(command="Write-Output 'Missing Quote")
    result = windows_bash_session.execute(action)
    assert isinstance(result, ErrorObservation)
    assert "missing" in result.content.lower() or "terminator" in result.content.lower()


def test_special_characters_handling(windows_bash_session):
    """Test handling of commands containing special characters."""
    special_chars_cmd = 'Write-Output "Special Chars: \\`& \\`| \\`< \\`> \\`\\` \\`\' \\`" \\`! \\`$ \\`% \\`^ \\`( \\`) \\`- \\`= \\`+ \\`[ \\`] \\`{ \\`} \\`; \\`: \\`, \\`. \\`? \\`/ \\`~"'
    action = CmdRunAction(command=special_chars_cmd)
    result = windows_bash_session.execute(action)
    assert isinstance(result, CmdOutputObservation)
    assert "Special Chars:" in result.content
    assert "&" in result.content and "|" in result.content
    assert result.exit_code == 0


def test_empty_command(windows_bash_session):
    """Test handling of empty command string when no command is running."""
    action = CmdRunAction(command="")
    result = windows_bash_session.execute(action)
    assert isinstance(result, CmdOutputObservation)
    assert "ERROR: No previous running command to retrieve logs from." in result.content
    assert result.exit_code == 0


def test_exception_during_execution(windows_bash_session):
    """Test handling of exceptions during command execution."""
    patch_target = "forge.runtime.utils.windows_bash.PowerShell"
    mock_powershell_class = MagicMock()
    mock_powershell_class.Create.side_effect = Exception("Test exception from mocked Create")
    with patch(patch_target, mock_powershell_class):
        action = CmdRunAction(command="Write-Output 'Test'")
        result = windows_bash_session.execute(action)
        assert isinstance(result, ErrorObservation)
        assert "Failed to start PowerShell job" in result.content
        assert "Test exception from mocked Create" in result.content


def test_streaming_output(windows_bash_session):
    """Test handling of streaming output from commands."""
    command = '\n    1..3 | ForEach-Object {\n        Write-Output "Line $_"\n        Start-Sleep -Milliseconds 100\n    }\n    '
    action = CmdRunAction(command=command)
    result = windows_bash_session.execute(action)
    assert isinstance(result, CmdOutputObservation)
    assert "Line 1" in result.content
    assert "Line 2" in result.content
    assert "Line 3" in result.content
    assert result.exit_code == 0


def test_shutdown_signal_handling(windows_bash_session):
    """Test handling of shutdown signal during command execution."""
    command = "Start-Sleep -Seconds 1"
    action = CmdRunAction(command=command)
    result = windows_bash_session.execute(action)
    assert isinstance(result, CmdOutputObservation)
    assert result.exit_code == 0


def test_runspace_state_after_error(windows_bash_session):
    """Test that the runspace remains usable after a command error."""
    error_action = CmdRunAction(command="NonExistentCommand")
    error_result = windows_bash_session.execute(error_action)
    assert isinstance(error_result, CmdOutputObservation)
    assert error_result.exit_code == 1
    valid_action = CmdRunAction(command="Write-Output 'Still working'")
    valid_result = windows_bash_session.execute(valid_action)
    assert isinstance(valid_result, CmdOutputObservation)
    assert "Still working" in valid_result.content
    assert valid_result.exit_code == 0


def test_stateful_file_operations(windows_bash_session, temp_work_dir):
    """Test file operations to verify runspace state persistence.

    This test verifies that:
    1. The working directory state persists between commands
    2. File operations work correctly relative to the current directory
    3. The runspace maintains state for path-dependent operations
    """
    abs_temp_work_dir = os.path.abspath(temp_work_dir)
    sub_dir_name = "file_test_dir"
    sub_dir_path = Path(abs_temp_work_dir) / sub_dir_name
    create_dir_action = CmdRunAction(command=f'New-Item -Path "{sub_dir_name}" -ItemType Directory')
    result = windows_bash_session.execute(create_dir_action)
    assert result.exit_code == 0
    assert sub_dir_path.is_dir()
    cd_action = CmdRunAction(command=f"Set-Location '{sub_dir_name}'")
    result = windows_bash_session.execute(cd_action)
    assert result.exit_code == 0
    assert windows_bash_session._cwd.lower().endswith(f"\\{sub_dir_name.lower()}")
    test_content = "This is a test file created by PowerShell"
    create_file_action = CmdRunAction(command=f'Set-Content -Path "test_file.txt" -Value "{test_content}"')
    result = windows_bash_session.execute(create_file_action)
    assert result.exit_code == 0
    expected_file_path = sub_dir_path / "test_file.txt"
    assert expected_file_path.is_file()
    read_file_action = CmdRunAction(command='Get-Content -Path "test_file.txt"')
    result = windows_bash_session.execute(read_file_action)
    assert result.exit_code == 0
    assert test_content in result.content
    cd_parent_action = CmdRunAction(command="Set-Location ..")
    result = windows_bash_session.execute(cd_parent_action)
    assert result.exit_code == 0
    temp_dir_basename = os.path.basename(abs_temp_work_dir)
    assert windows_bash_session._cwd.lower().endswith(temp_dir_basename.lower())
    read_from_parent_action = CmdRunAction(command=f'Get-Content -Path "{sub_dir_name}/test_file.txt"')
    result = windows_bash_session.execute(read_from_parent_action)
    assert result.exit_code == 0
    assert test_content in result.content
    remove_file_action = CmdRunAction(command=f'Remove-Item -Path "{sub_dir_name}/test_file.txt" -Force')
    result = windows_bash_session.execute(remove_file_action)
    assert result.exit_code == 0


def test_command_output_continuation(windows_bash_session):
    """Test retrieving continued output using empty command after timeout."""
    action = CmdRunAction("1..5 | ForEach-Object { Write-Output $_; Start-Sleep 3 }")
    action.set_hard_timeout(2.5)
    obs = windows_bash_session.execute(action)
    assert obs.content.strip() == "1"
    assert obs.metadata.prefix == ""
    assert "[The command timed out after 2.5 seconds." in obs.metadata.suffix
    action = CmdRunAction("")
    action.set_hard_timeout(2.5)
    obs = windows_bash_session.execute(action)
    assert "[Below is the output of the previous command.]" in obs.metadata.prefix
    assert obs.content.strip() == "2"
    assert "[The command timed out after 2.5 seconds." in obs.metadata.suffix
    for expected in ["3", "4", "5"]:
        action = CmdRunAction("")
        action.set_hard_timeout(2.5)
        obs = windows_bash_session.execute(action)
        assert "[Below is the output of the previous command.]" in obs.metadata.prefix
        assert obs.content.strip() == expected
        assert "[The command timed out after 2.5 seconds." in obs.metadata.suffix
    action = CmdRunAction("")
    obs = windows_bash_session.execute(action)
    assert "[The command completed with exit code 0.]" in obs.metadata.suffix


def test_long_running_command_followed_by_execute(windows_bash_session):
    """Tests behavior when a new command is sent while another is running after timeout."""
    action = CmdRunAction("1..3 | ForEach-Object { Write-Output $_; Start-Sleep 3 }")
    action.set_hard_timeout(2.5)
    obs = windows_bash_session.execute(action)
    assert "1" in obs.content
    assert obs.metadata.exit_code == -1
    assert "[The command timed out after 2.5 seconds." in obs.metadata.suffix
    assert obs.metadata.prefix == ""
    action = CmdRunAction("")
    action.set_hard_timeout(2.5)
    obs = windows_bash_session.execute(action)
    assert "2" in obs.content
    assert obs.metadata.prefix == "[Below is the output of the previous command.]\n"
    assert "[The command timed out after 2.5 seconds." in obs.metadata.suffix
    assert obs.metadata.exit_code == -1
    action = CmdRunAction("sleep 15")
    action.set_hard_timeout(2.5)
    obs = windows_bash_session.execute(action)
    assert "3" not in obs.content
    assert obs.metadata.prefix == "[Below is the output of the previous command.]\n"
    assert "The previous command is still running" in obs.metadata.suffix
    assert obs.metadata.exit_code == -1
    action = CmdRunAction("")
    obs = windows_bash_session.execute(action)
    assert "3" in obs.content
    assert "[The command completed with exit code 0.]" in obs.metadata.suffix


def test_command_non_existent_file(windows_bash_session):
    """Test command execution for a non-existent file returns non-zero exit code."""
    action = CmdRunAction(command="Get-Content non_existent_file.txt")
    result = windows_bash_session.execute(action)
    assert isinstance(result, CmdOutputObservation)
    assert result.exit_code == 1
    assert "Cannot find path" in result.content or "does not exist" in result.content


def test_interactive_input(windows_bash_session):
    """Test interactive input attempt reflects implementation limitations."""
    action = CmdRunAction('$name = Read-Host "Enter name"')
    result = windows_bash_session.execute(action)
    assert isinstance(result, CmdOutputObservation)
    assert (
        "A command that prompts the user failed because the host program or the command type does not support user interaction. The host was attempting to request confirmation with the following message"
        in result.content
    )
    assert result.exit_code == 1


def test_windows_path_handling(windows_bash_session, temp_work_dir):
    """Test that os.chdir works with both forward slashes and escaped backslashes on Windows."""
    test_dir = Path(temp_work_dir) / "test_dir"
    test_dir.mkdir()
    path_formats = [str(test_dir).replace("\\", "/"), str(test_dir).replace("\\", "\\\\")]
    for path in path_formats:
        action = CmdRunAction(command=f'''python -c "import os; os.chdir('{path}')"''')
        result = windows_bash_session.execute(action)
        assert isinstance(result, CmdOutputObservation)
        assert result.exit_code == 0, f"Failed with path format: {path}"
