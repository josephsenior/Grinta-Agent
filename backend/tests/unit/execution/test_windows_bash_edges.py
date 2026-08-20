"""Edge-path tests for backend.execution.utils.shell.windows_bash.

Targets the branches not exercised by test_windows_bash_spawn_tracking.py:
executable discovery, session lifecycle, subprocess error handling, spawn
tracking registration, background-command fallback, and idle-detach metadata.
"""

from __future__ import annotations

import importlib
import subprocess
import sys
from types import SimpleNamespace
from typing import TYPE_CHECKING, cast
from unittest.mock import MagicMock, patch

import pytest

from backend.core.bounded_result import BoundedResult

if sys.platform != 'win32':
    pytest.skip(
        'windows_bash only imports on Windows.',
        allow_module_level=True,
    )


from backend.core.os_capabilities import (  # noqa: E402
    OSCapabilities,
    override_os_capabilities,
)
from backend.execution.utils.shell import windows_bash as wb  # noqa: E402
from backend.execution.utils.shell.windows_bash import (  # noqa: E402
    WindowsPowershellSession,
    _find_powershell_executable,
    _ps_single_quoted_literal,
)
from backend.ledger.action import CmdRunAction  # noqa: E402
from backend.ledger.observation import ErrorObservation  # noqa: E402
from backend.ledger.observation.commands import CmdOutputObservation  # noqa: E402

if TYPE_CHECKING:
    from backend.execution.utils.process.process_registry import TaskCancellationService


@pytest.fixture
def mock_cancellation() -> MagicMock:
    return MagicMock()


@pytest.fixture
def session(tmp_path, mock_cancellation: MagicMock) -> WindowsPowershellSession:
    return WindowsPowershellSession(
        work_dir=str(tmp_path),
        cancellation_service=cast('TaskCancellationService', mock_cancellation),
        powershell_exe='pwsh',
    )


class TestPlatformGuard:
    def test_non_windows_import_raises(self) -> None:
        caps = OSCapabilities(
            is_windows=False,
            is_posix=True,
            is_linux=True,
            is_macos=False,
            shell_kind='bash',
            supports_pty=True,
            signal_strategy='posix',
            path_sep='/',
            default_python_exec='python3',
            sys_platform='linux',
            os_name='posix',
        )
        with override_os_capabilities(caps):
            with pytest.raises(RuntimeError, match=r'windows_bash\.py.*linux'):
                importlib.reload(wb)
        importlib.reload(wb)


class TestFindPowershellExecutable:
    @patch('backend.execution.utils.shell.windows_bash.subprocess.run')
    def test_returns_pwsh_first(self, mock_run: MagicMock) -> None:
        mock_run.return_value = subprocess.CompletedProcess(['pwsh'], 0)
        with patch(
            'backend.execution.utils.shell.windows_bash.logger.info'
        ) as mock_info:
            assert _find_powershell_executable() == 'pwsh'
        assert mock_info.call_args.args[0] == 'Found PowerShell 7 (pwsh.exe)'

    @patch('backend.execution.utils.shell.windows_bash.subprocess.run')
    def test_falls_back_to_powershell_on_missing_pwsh(
        self, mock_run: MagicMock
    ) -> None:
        mock_run.side_effect = [
            FileNotFoundError,
            subprocess.CompletedProcess(['powershell'], 0),
        ]
        assert _find_powershell_executable() == 'powershell'

    @patch('backend.execution.utils.shell.windows_bash.subprocess.run')
    def test_falls_back_to_powershell_on_pwsh_timeout(
        self, mock_run: MagicMock
    ) -> None:
        mock_run.side_effect = [
            subprocess.TimeoutExpired('pwsh', 5),
            subprocess.CompletedProcess(['powershell'], 0),
        ]
        assert _find_powershell_executable() == 'powershell'

    @patch('backend.execution.utils.shell.windows_bash.subprocess.run')
    def test_falls_back_when_pwsh_fails(self, mock_run: MagicMock) -> None:
        mock_run.side_effect = [
            subprocess.CompletedProcess(['pwsh'], 1),
            subprocess.CompletedProcess(['powershell'], 0),
        ]
        assert _find_powershell_executable() == 'powershell'

    @patch('backend.execution.utils.shell.windows_bash.subprocess.run')
    def test_raises_when_neither_available(self, mock_run: MagicMock) -> None:
        mock_run.side_effect = [
            subprocess.CompletedProcess(['pwsh'], 1),
            subprocess.CompletedProcess(['powershell'], 1),
        ]
        with pytest.raises(RuntimeError, match='PowerShell is required'):
            _find_powershell_executable()

    @patch('backend.execution.utils.shell.windows_bash.subprocess.run')
    def test_raises_when_both_timeout(self, mock_run: MagicMock) -> None:
        mock_run.side_effect = [
            subprocess.TimeoutExpired('pwsh', 5),
            subprocess.TimeoutExpired('powershell', 5),
        ]
        with pytest.raises(RuntimeError, match='PowerShell is required'):
            _find_powershell_executable()


class TestPsSingleQuotedLiteral:
    def test_escapes_embedded_quotes(self) -> None:
        assert _ps_single_quoted_literal("C:\\a'b") == "'C:\\a''b'"

    def test_plain_value(self) -> None:
        assert _ps_single_quoted_literal('plain') == "'plain'"


class TestSessionLifecycle:
    def test_init_creates_missing_work_dir(
        self, tmp_path, mock_cancellation: MagicMock
    ) -> None:
        work_dir = tmp_path / 'deep' / 'nested'
        with patch(
            'backend.execution.utils.shell.windows_bash.logger.info'
        ) as mock_info:
            WindowsPowershellSession(
                work_dir=str(work_dir),
                cancellation_service=cast('TaskCancellationService', mock_cancellation),
                powershell_exe='pwsh',
            )
        assert work_dir.is_dir()
        assert any(
            c.args[0] == 'Created working directory: %s'
            for c in mock_info.call_args_list
        )

    def test_init_failure_closes_and_raises(
        self, tmp_path, mock_cancellation: MagicMock
    ) -> None:
        with (
            patch(
                'backend.execution.utils.shell.windows_bash._find_powershell_executable',
                side_effect=RuntimeError('no pwsh'),
            ),
            patch(
                'backend.execution.utils.shell.windows_bash.logger.error'
            ) as mock_err,
            pytest.raises(
                RuntimeError, match='Failed to initialize PowerShell session'
            ),
        ):
            WindowsPowershellSession(
                work_dir=str(tmp_path),
                cancellation_service=cast('TaskCancellationService', mock_cancellation),
            )
        assert (
            mock_err.call_args.args[0] == 'Failed to initialize PowerShell session: %s'
        )

    def test_initialize_raises_when_not_initialized(self) -> None:
        uninit = WindowsPowershellSession.__new__(WindowsPowershellSession)
        uninit._initialized = False
        with pytest.raises(RuntimeError, match='failed to initialize'):
            uninit.initialize()

    def test_write_input_logs_warning(self, session: WindowsPowershellSession) -> None:
        with patch(
            'backend.execution.utils.shell.windows_bash.logger.warning'
        ) as mock_warn:
            session.write_input('data')
        assert (
            mock_warn.call_args.args[0]
            == 'Terminal input not supported on Windows subprocess implementation'
        )


class TestRunBackgroundablePath:
    def test_no_pending_bg_returns_none(
        self, session: WindowsPowershellSession
    ) -> None:
        assert session._pending_bg_id is None
        with patch.object(session, '_run_backgroundable') as mock_rb:
            assert session._run_backgroundable_path(MagicMock(pid=1), None, 'x') is None
        mock_rb.assert_not_called()

    def test_returns_result_and_unregisters(
        self, session: WindowsPowershellSession
    ) -> None:
        proc = MagicMock(pid=42)
        session._pending_bg_id = 'bg-1'
        with patch.object(
            session, '_run_backgroundable', return_value=('o', 'e', 0)
        ) as mock_rb:
            result = session._run_backgroundable_path(proc, 5, 'echo hi')
        assert result == ('o', 'e', 0)
        mock_rb.assert_called_once_with(proc, 5, 'bg-1', blocking=False)
        session._cancellation.unregister_process.assert_called_once_with(42)

    def test_detached_code_skips_unregister(
        self, session: WindowsPowershellSession
    ) -> None:
        proc = MagicMock(pid=42)
        session._pending_bg_id = 'bg-1'
        with patch.object(session, '_run_backgroundable', return_value=('o', 'e', -2)):
            result = session._run_backgroundable_path(proc, 5, 'echo hi')
        assert result == ('o', 'e', -2)
        session._cancellation.unregister_process.assert_not_called()

    def test_cd_command_triggers_cwd_update(
        self, session: WindowsPowershellSession
    ) -> None:
        proc = MagicMock(pid=42)
        session._pending_bg_id = 'bg-1'
        with (
            patch.object(session, '_run_backgroundable', return_value=('o', 'e', 0)),
            patch.object(session, '_update_cwd_if_needed') as mock_cwd,
        ):
            session._run_backgroundable_path(proc, 5, 'cd somewhere')
        mock_cwd.assert_called_once()


class TestSpawnTrackingResult:
    def test_registers_new_pids_skipping_own(
        self, session: WindowsPowershellSession
    ) -> None:
        proc = MagicMock(pid=100)
        stdout = 'hello\n___GRINTA_SPAWNED___100,200___END___\n'
        with patch(
            'backend.execution.utils.shell.windows_bash.logger.info'
        ) as mock_info:
            result = session._handle_spawn_tracking_result(proc, stdout)
        assert result == 'hello\n'
        session._cancellation.register_pid.assert_called_once_with(200)
        assert mock_info.call_args.args[0].startswith(
            'Start-Process wrapper registered'
        )

    def test_no_pids_no_registration(self, session: WindowsPowershellSession) -> None:
        proc = MagicMock(pid=100)
        result = session._handle_spawn_tracking_result(proc, 'plain output')
        assert result == 'plain output'
        session._cancellation.register_pid.assert_not_called()


class TestRunStandardCommand:
    @patch('backend.execution.utils.shell.windows_bash.bounded_communicate')
    def test_happy_path(
        self, mock_bc: MagicMock, session: WindowsPowershellSession
    ) -> None:
        proc = MagicMock(pid=42)
        mock_bc.return_value = BoundedResult(
            stdout='out', stderr='err', returncode=0, truncated=False, timed_out=False
        )
        out, err, code = session._run_standard_command(proc, 5, None, 'echo hi', False)
        assert (out, err, code) == ('out', 'err', 0)
        mock_bc.assert_called_once()
        assert mock_bc.call_args.kwargs['stdin_data'] is None

    @patch('backend.execution.utils.shell.windows_bash.bounded_communicate')
    def test_with_stdin(
        self, mock_bc: MagicMock, session: WindowsPowershellSession
    ) -> None:
        proc = MagicMock(pid=42)
        mock_bc.return_value = BoundedResult(
            stdout='out', stderr='', returncode=0, truncated=False, timed_out=False
        )
        out, err, code = session._run_standard_command(proc, 5, 'data', 'cat', False)
        assert (out, err, code) == ('out', '', 0)
        assert mock_bc.call_args.kwargs['stdin_data'] == b'data'

    @patch('backend.execution.utils.shell.windows_bash.bounded_communicate')
    def test_cd_updates_cwd(
        self, mock_bc: MagicMock, tmp_path, session: WindowsPowershellSession
    ) -> None:
        new_dir = tmp_path / 'sub'
        new_dir.mkdir()
        proc = MagicMock(pid=42)
        mock_bc.return_value = BoundedResult(
            stdout='out', stderr='', returncode=0, truncated=False, timed_out=False
        )
        with patch('subprocess.run') as mock_run:
            mock_run.return_value = SimpleNamespace(returncode=0, stdout=str(new_dir))
            session._run_standard_command(proc, 5, None, 'cd sub', False)
        assert session._cwd == str(new_dir)

    @patch('backend.execution.utils.shell.windows_bash.bounded_communicate')
    def test_wrapped_spawn_tracking(
        self, mock_bc: MagicMock, session: WindowsPowershellSession
    ) -> None:
        proc = MagicMock(pid=42)
        mock_bc.return_value = BoundedResult(
            stdout='boot\n___GRINTA_SPAWNED___300___END___\n',
            stderr='',
            returncode=0,
            truncated=False,
            timed_out=False,
        )
        out, _err, _code = session._run_standard_command(
            proc, 5, None, 'Start-Process python', True
        )
        assert out == 'boot\n'
        session._cancellation.register_pid.assert_called_once_with(300)


class TestRunCommand:
    def test_closed_session_raises(self, session: WindowsPowershellSession) -> None:
        session._closed = True
        with pytest.raises(RuntimeError, match='closed'):
            session._run_command('echo hi')

    @patch('backend.execution.utils.shell.windows_bash.bounded_communicate')
    @patch('backend.execution.utils.shell.windows_bash.subprocess.Popen')
    def test_happy_path(
        self,
        mock_popen: MagicMock,
        mock_bc: MagicMock,
        session: WindowsPowershellSession,
    ) -> None:
        proc = MagicMock(pid=7)
        mock_popen.return_value = proc
        mock_bc.return_value = BoundedResult(
            stdout='hi', stderr='', returncode=0, truncated=False, timed_out=False
        )
        out, err, code = session._run_command('echo hi')
        assert (out, err, code) == ('hi', '', 0)
        assert mock_popen.call_args.kwargs['cwd'] == session.work_dir
        assert mock_popen.call_args.kwargs['stdin'] is subprocess.DEVNULL
        env = mock_popen.call_args.kwargs['env']
        assert 'PYTHONIOENCODING' in env
        assert 'PYTHONUTF8' in env
        assert mock_popen.call_args.args[0][0] == 'pwsh'
        session._cancellation.register_process.assert_called_once_with(proc)
        session._cancellation.unregister_process.assert_called_once_with(7)

    @patch('backend.execution.utils.shell.windows_bash.bounded_communicate')
    @patch('backend.execution.utils.shell.windows_bash.subprocess.Popen')
    def test_falls_back_to_work_dir_when_cwd_missing(
        self,
        mock_popen: MagicMock,
        mock_bc: MagicMock,
        tmp_path,
        session: WindowsPowershellSession,
    ) -> None:
        mock_popen.return_value = MagicMock(pid=7)
        mock_bc.return_value = BoundedResult(
            stdout='', stderr='', returncode=0, truncated=False, timed_out=False
        )
        session._cwd = str(tmp_path / 'gone')
        session._run_command('echo hi', cwd=None)
        assert mock_popen.call_args.kwargs['cwd'] == session.work_dir

    @patch('backend.execution.utils.shell.windows_bash.bounded_communicate')
    @patch('backend.execution.utils.shell.windows_bash.subprocess.Popen')
    def test_stdin_pipe_when_input_given(
        self,
        mock_popen: MagicMock,
        mock_bc: MagicMock,
        session: WindowsPowershellSession,
    ) -> None:
        mock_popen.return_value = MagicMock(pid=7)
        mock_bc.return_value = BoundedResult(
            stdout='', stderr='', returncode=0, truncated=False, timed_out=False
        )
        session._run_command('cat', input_text='data')
        assert mock_popen.call_args.kwargs['stdin'] is subprocess.PIPE

    @patch('backend.execution.utils.shell.windows_bash.subprocess.Popen')
    def test_timeout_returns_124(
        self, mock_popen: MagicMock, session: WindowsPowershellSession
    ) -> None:
        mock_popen.side_effect = subprocess.TimeoutExpired('pwsh', 5)
        out, err, code = session._run_command('echo hi', timeout=5)
        assert (out, err, code) == ('', 'Command timed out after 5 seconds', 124)

    @patch('backend.execution.utils.shell.windows_bash.subprocess.Popen')
    def test_generic_exception_returns_error(
        self, mock_popen: MagicMock, session: WindowsPowershellSession
    ) -> None:
        mock_popen.side_effect = RuntimeError('boom')
        out, err, code = session._run_command('echo hi')
        assert (out, err, code) == ('', 'boom', 1)

    def test_wraps_start_process_command(
        self, session: WindowsPowershellSession
    ) -> None:
        proc = MagicMock(pid=7)
        with (
            patch.object(
                session, '_run_standard_command', return_value=('o', 'e', 0)
            ) as mock_std,
            patch(
                'backend.execution.utils.shell.windows_bash.subprocess.Popen',
                return_value=proc,
            ) as mock_popen,
        ):
            session._run_command('Start-Process notepad')
        assert mock_std.call_args.args[3] == 'Start-Process notepad'
        assert mock_std.call_args.args[4] is True
        wrapped_argv = mock_popen.call_args.args[0]
        assert '___GRINTA_SPAWNED___' in wrapped_argv[4]

    def test_backgroundable_result_short_circuits(
        self, session: WindowsPowershellSession
    ) -> None:
        proc = MagicMock(pid=7)
        session._pending_bg_id = 'bg-9'
        with (
            patch.object(session, '_run_backgroundable', return_value=('o', 'e', 0)),
            patch.object(session, '_run_standard_command') as mock_std,
            patch(
                'backend.execution.utils.shell.windows_bash.subprocess.Popen',
                return_value=proc,
            ),
        ):
            out, err, code = session._run_command('echo hi')
        assert (out, err, code) == ('o', 'e', 0)
        mock_std.assert_not_called()


class TestExecute:
    def test_not_ready_returns_error_observation(
        self, session: WindowsPowershellSession
    ) -> None:
        session._initialized = False
        result = session.execute(CmdRunAction(command='ls'))
        assert isinstance(result, ErrorObservation)
        assert 'not initialized' in result.content

    @patch('backend.execution.utils.shell.windows_bash.bounded_communicate')
    @patch('backend.execution.utils.shell.windows_bash.subprocess.Popen')
    def test_foreground_with_stdin(
        self,
        mock_popen: MagicMock,
        mock_bc: MagicMock,
        session: WindowsPowershellSession,
    ) -> None:
        mock_popen.return_value = MagicMock(pid=7)
        mock_bc.return_value = BoundedResult(
            stdout='result', stderr='', returncode=0, truncated=False, timed_out=False
        )
        action = CmdRunAction(command='cat', is_input=True, stdin='hello')
        result = session.execute(action)
        assert isinstance(result, CmdOutputObservation)
        assert 'result' in result.content
        assert mock_bc.call_args.kwargs['stdin_data'] == b'hello'

    def test_background_success(self, session: WindowsPowershellSession) -> None:
        action = CmdRunAction(command='sleep 5 &')
        with (
            patch.object(
                session, '_run_command', return_value=('123', '', 0)
            ) as mock_rc,
            patch(
                'backend.execution.utils.shell.windows_bash.logger.info'
            ) as mock_info,
        ):
            result = session.execute(action)
        assert isinstance(result, CmdOutputObservation)
        assert result.content == '[123]'
        start_cmd = mock_rc.call_args.args[0]
        assert 'Start-Process -FilePath' in start_cmd
        assert 'Set-Location' in start_cmd
        session._cancellation.register_pid.assert_called_once_with(123)
        assert mock_info.call_args.args[0] == 'Background process started with PID: %s'

    def test_background_failure_falls_back(
        self, session: WindowsPowershellSession
    ) -> None:
        action = CmdRunAction(command='sleep 5 &')
        with (
            patch.object(
                session,
                '_run_command',
                side_effect=[('', 'failed', 1), ('ran normally', '', 0)],
            ),
            patch(
                'backend.execution.utils.shell.windows_bash.logger.warning'
            ) as mock_warn,
        ):
            result = session.execute(action)
        assert isinstance(result, CmdOutputObservation)
        assert 'ran normally' in result.content
        assert (
            mock_warn.call_args.args[0]
            == 'Failed to start background job, running normally'
        )


class TestCwdAndErrorHandlers:
    def test_update_cwd_if_needed(self, session: WindowsPowershellSession) -> None:
        with patch.object(session, '_update_cwd_from_output') as mock_ucwo:
            session._update_cwd_if_needed()
        argv = mock_ucwo.call_args.args[0]
        assert argv[0] == 'pwsh'
        assert any('Get-Location' in a for a in argv)

    def test_timeout_exception_kills_process(
        self, session: WindowsPowershellSession
    ) -> None:
        proc = MagicMock()
        with patch(
            'backend.execution.utils.shell.windows_bash.logger.warning'
        ) as mock_warn:
            out, err, code = session._handle_timeout_exception(proc, 5, 'cmd')
        assert (out, err, code) == ('', 'Command timed out after 5 seconds', 124)
        proc.kill.assert_called_once()
        proc.wait.assert_called_once()
        assert mock_warn.call_args.args[0] == 'Command timed out after %s seconds: %s'

    def test_timeout_exception_kill_failure_swallowed(
        self, session: WindowsPowershellSession
    ) -> None:
        proc = MagicMock()
        proc.kill.side_effect = OSError('no')
        out, _err, code = session._handle_timeout_exception(proc, 5, 'cmd')
        assert code == 124

    def test_timeout_exception_no_process(
        self, session: WindowsPowershellSession
    ) -> None:
        out, err, code = session._handle_timeout_exception(None, 5, 'cmd')
        assert (out, err, code) == ('', 'Command timed out after 5 seconds', 124)

    def test_run_exception_kills_process(
        self, session: WindowsPowershellSession
    ) -> None:
        proc = MagicMock()
        with patch(
            'backend.execution.utils.shell.windows_bash.logger.error'
        ) as mock_err:
            out, err, code = session._handle_run_exception(proc, RuntimeError('boom'))
        assert (out, err, code) == ('', 'boom', 1)
        proc.kill.assert_called_once()
        assert mock_err.call_args.args[0] == 'Error running PowerShell command: %s'

    def test_run_exception_kill_failure_swallowed(
        self, session: WindowsPowershellSession
    ) -> None:
        proc = MagicMock()
        proc.kill.side_effect = OSError('no')
        out, _err, code = session._handle_run_exception(proc, ValueError('x'))
        assert code == 1

    def test_run_exception_no_process(self, session: WindowsPowershellSession) -> None:
        out, err, code = session._handle_run_exception(None, RuntimeError('boom'))
        assert (out, err, code) == ('', 'boom', 1)


class TestExecuteForegroundCommand:
    def test_normal_path(self, session: WindowsPowershellSession) -> None:
        with patch.object(session, '_run_command', return_value=('out', 'err', 0)):
            result = session._execute_foreground_command('echo hi', 30, None)
        assert isinstance(result, CmdOutputObservation)
        assert result.metadata.exit_code == 0
        assert 'out' in result.content
        assert '[ERROR STREAM]' in result.content

    def test_idle_detach_path(self, session: WindowsPowershellSession) -> None:
        session._bg_process = MagicMock()
        session._bg_session_id = 'bg-77'
        with patch.object(session, '_run_command', return_value=('partial', '', -2)):
            result = session._execute_foreground_command('sleep 100', 30, None)
        assert isinstance(result, CmdOutputObservation)
        assert result.content == 'partial'
        assert result.metadata.exit_code == -2
        assert result.metadata.timeout_kind == 'idle_detach'
        assert 'bg-77' in result.metadata.suffix

    def test_blocking_flag_propagates(self, session: WindowsPowershellSession) -> None:
        with patch.object(session, '_run_command', return_value=('', '', 0)) as mock_rc:
            session._execute_foreground_command('echo hi', 30, None, blocking=True)
        assert mock_rc.call_args.kwargs['blocking'] is True
