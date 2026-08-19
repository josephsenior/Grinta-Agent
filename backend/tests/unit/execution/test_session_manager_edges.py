"""Edge-path tests for backend.execution.utils.shell.session_manager.

Covers session lifecycle (create/close/close_all), idle-session cleanup
branches, default-session liveness checks, and tool-registry fallback.
"""

from __future__ import annotations

import builtins
from types import SimpleNamespace
from typing import cast
from unittest.mock import MagicMock, patch

import pytest

from backend.execution.utils.shell.session_manager import SessionManager
from backend.execution.utils.shell.unified_shell import UnifiedShellSession


@pytest.fixture
def mgr(tmp_path) -> SessionManager:
    return SessionManager(
        work_dir=str(tmp_path),
        username='tester',
        tool_registry=MagicMock(),
        cancellation_service=MagicMock(),
    )


class TestToolRegistryFallback:
    def test_import_error_leaves_registry_none(self, tmp_path, monkeypatch) -> None:
        real_import = builtins.__import__

        def raiser(name, *args, **kwargs):
            if name == 'backend.execution.utils.tool_registry':
                raise ImportError('simulated missing')
            return real_import(name, *args, **kwargs)

        monkeypatch.setattr(builtins, '__import__', raiser)
        with patch('backend.execution.utils.shell.session_manager.logger.warning') as mock_warn:
            m = SessionManager(
                work_dir=str(tmp_path),
                username='tester',
                cancellation_service=MagicMock(),
            )
        assert m.tool_registry is None
        assert mock_warn.call_args.args[0] == 'Failed to import ToolRegistry'

    def test_creates_default_registry(self, tmp_path) -> None:
        registry = MagicMock()
        with patch(
            'backend.execution.utils.tool_registry.ToolRegistry', return_value=registry
        ):
            m = SessionManager(
                work_dir=str(tmp_path),
                username='tester',
                cancellation_service=MagicMock(),
            )
        assert m.tool_registry is registry


class TestCreateSession:
    def test_generates_session_id(self, mgr: SessionManager, tmp_path, monkeypatch) -> None:
        monkeypatch.delenv('NO_CHANGE_TIMEOUT_SECONDS', raising=False)
        session = MagicMock()
        with (
            patch('backend.execution.utils.shell.session_manager.uuid.uuid4', return_value='uuid-1'),
            patch('backend.utils.stdio_restore.real_stdio_for_subprocess') as mock_stdio,
            patch(
                'backend.execution.utils.shell.session_manager.create_shell_session',
                return_value=session,
            ) as mock_create,
        ):
            result = mgr.create_session(cwd=str(tmp_path))
        assert result is session
        assert mgr.sessions == {'uuid-1': session}
        mock_stdio.assert_called_once()
        session.initialize.assert_called_once()
        kwargs = mock_create.call_args.kwargs
        assert kwargs['work_dir'] == str(tmp_path)
        assert kwargs['interactive'] is False
        assert kwargs['no_change_timeout_seconds'] == 30
        assert kwargs['max_memory_mb'] is None

    def test_explicit_id_and_interactive(self, mgr: SessionManager) -> None:
        session = MagicMock()
        with (
            patch('backend.utils.stdio_restore.real_stdio_for_subprocess'),
            patch(
                'backend.execution.utils.shell.session_manager.create_shell_session',
                return_value=session,
            ),
        ):
            result = mgr.create_session('default', interactive=True)
        assert result is session
        assert mgr.sessions['default'] is session

    def test_max_memory_gb_converted(self, tmp_path) -> None:
        m = SessionManager(
            work_dir=str(tmp_path),
            username='tester',
            tool_registry=MagicMock(),
            cancellation_service=MagicMock(),
            max_memory_gb=2,
        )
        with (
            patch('backend.utils.stdio_restore.real_stdio_for_subprocess'),
            patch(
                'backend.execution.utils.shell.session_manager.create_shell_session',
                return_value=MagicMock(),
            ) as mock_create,
        ):
            m.create_session()
        assert mock_create.call_args.kwargs['max_memory_mb'] == 2048

    def test_failure_logs_and_raises(self, mgr: SessionManager) -> None:
        with (
            patch(
                'backend.execution.utils.shell.session_manager.create_shell_session',
                side_effect=RuntimeError('boom'),
            ),
            patch('backend.execution.utils.shell.session_manager.logger.error') as mock_err,
            pytest.raises(RuntimeError, match='boom'),
        ):
            mgr.create_session()
        assert mock_err.call_args.args[0] == 'Failed to create session %s: %s'
        assert mgr.sessions == {}


class TestCloseSession:
    def test_close_existing(self, mgr: SessionManager) -> None:
        session = MagicMock()
        mgr.sessions['s1'] = session
        mgr.close_session('s1')
        assert 's1' not in mgr.sessions
        session.close.assert_called_once()

    def test_close_missing_is_noop(self, mgr: SessionManager) -> None:
        mgr.close_session('nope')
        assert mgr.sessions == {}

    def test_get_session(self, mgr: SessionManager) -> None:
        assert mgr.get_session('missing') is None
        s = MagicMock()
        mgr.sessions['s1'] = s
        assert mgr.get_session('s1') is s

    def test_request_close_missing_returns_false(self, mgr: SessionManager) -> None:
        assert mgr.request_close_session('nope') is False

    def test_request_close_detaches_async(self, mgr: SessionManager) -> None:
        session = MagicMock()
        mgr.sessions['s1'] = session
        with patch.object(SessionManager, '_close_detached_session') as mock_close:
            assert mgr.request_close_session('s1') is True
        assert 's1' not in mgr.sessions
        mock_close.assert_called_once()
        assert mock_close.call_args.args[0] == 's1'
        assert mock_close.call_args.args[1] is session

    def test_close_detached_error_logged(self) -> None:
        bad = MagicMock()
        bad.close.side_effect = RuntimeError('boom')
        with patch('backend.execution.utils.shell.session_manager.logger.error') as mock_err:
            SessionManager._close_detached_session('s1', bad)
        assert mock_err.call_args.args[0] == 'Error closing session %s: %s'

    def test_close_all(self, mgr: SessionManager) -> None:
        good = MagicMock()
        bad = MagicMock()
        bad.close.side_effect = RuntimeError('boom')
        mgr.sessions['a'] = good
        mgr.sessions['b'] = bad
        mgr.close_all()
        assert mgr.sessions == {}
        good.close.assert_called_once()
        bad.close.assert_called_once()
        mgr.cancellation_service.cancel_all.assert_called_once()

    def test_default_session_property(self, mgr: SessionManager) -> None:
        assert mgr.default_session is None
        s = MagicMock()
        mgr.sessions['default'] = s
        assert mgr.default_session is s


class _GhostDict(dict):
    def get(self, key, default=None):
        if key == 'ghost':
            return None
        return super().get(key, default)


class TestCleanupIdleSessions:
    def test_closes_only_idle_exited(self, mgr: SessionManager) -> None:
        now = 1_000_000.0
        default = SimpleNamespace(_last_interaction_at=0.0, close=MagicMock())
        idle_dead = SimpleNamespace(
            _last_interaction_at=0.0,
            _process=SimpleNamespace(poll=lambda: 0),
            close=MagicMock(),
        )
        idle_running = SimpleNamespace(
            _last_interaction_at=0.0,
            _process=SimpleNamespace(poll=lambda: None),
            close=MagicMock(),
        )
        fresh = SimpleNamespace(_last_interaction_at=now, close=MagicMock())
        no_last = SimpleNamespace(close=MagicMock())
        mgr.sessions = cast(
            'dict[str, UnifiedShellSession]',
            {
                'default': default,
                'bg-dead': idle_dead,
                'bg-running': idle_running,
                'bg-fresh': fresh,
                'bg-no-last': no_last,
            },
        )
        with (
            patch('time.time', return_value=now),
            patch('backend.execution.utils.shell.session_manager.logger.info') as mock_info,
        ):
            closed = mgr.cleanup_idle_sessions(max_idle_seconds=100)
        assert closed == ['bg-dead']
        assert 'bg-dead' not in mgr.sessions
        assert 'default' in mgr.sessions
        assert 'bg-running' in mgr.sessions
        assert 'bg-fresh' in mgr.sessions
        assert 'bg-no-last' in mgr.sessions
        idle_dead.close.assert_called_once()
        default.close.assert_not_called()
        assert mock_info.call_args.args[0] == 'cleanup_idle_sessions: closed idle session %s'

    def test_require_exited_false_closes_running(
        self, mgr: SessionManager
    ) -> None:
        now = 1_000_000.0
        idle_running = SimpleNamespace(
            _last_interaction_at=0.0,
            _process=SimpleNamespace(poll=lambda: None),
            close=MagicMock(),
        )
        mgr.sessions = cast(
            'dict[str, UnifiedShellSession]',
            {'default': SimpleNamespace(_last_interaction_at=0.0), 'bg-r': idle_running},
        )
        with patch('time.time', return_value=now):
            closed = mgr.cleanup_idle_sessions(max_idle_seconds=100, require_exited=False)
        assert closed == ['bg-r']
        idle_running.close.assert_called_once()

    def test_ghost_session_skipped(self, mgr: SessionManager) -> None:
        mgr.sessions = _GhostDict({'ghost': object()})
        with patch('time.time', return_value=1_000_000.0):
            assert mgr.cleanup_idle_sessions() == []

    def test_close_failure_warns(self, mgr: SessionManager) -> None:
        mgr.sessions = cast(
            'dict[str, UnifiedShellSession]',
            {'bg-x': SimpleNamespace(_last_interaction_at=0.0)},
        )
        with (
            patch.object(mgr, 'close_session', side_effect=RuntimeError('boom')),
            patch('time.time', return_value=1_000_000.0),
            patch('backend.execution.utils.shell.session_manager.logger.warning') as mock_warn,
        ):
            assert mgr.cleanup_idle_sessions() == []
        assert mock_warn.call_args.args[0] == 'cleanup_idle_sessions: failed to close %s'


class TestDefaultSessionAlive:
    def test_no_default_false(self, mgr: SessionManager) -> None:
        assert mgr.is_default_session_alive() is False

    def test_running_process_true(self, mgr: SessionManager) -> None:
        mgr.sessions['default'] = SimpleNamespace(
            _process=SimpleNamespace(poll=lambda: None)
        )
        assert mgr.is_default_session_alive() is True

    def test_dead_process_false(self, mgr: SessionManager) -> None:
        mgr.sessions['default'] = SimpleNamespace(
            _process=SimpleNamespace(poll=lambda: 3)
        )
        assert mgr.is_default_session_alive() is False

    def test_no_process_assumed_alive(self, mgr: SessionManager) -> None:
        mgr.sessions['default'] = SimpleNamespace()
        assert mgr.is_default_session_alive() is True


class TestEnsureDefaultSession:
    def test_alive_returns_existing(self, mgr: SessionManager) -> None:
        alive = SimpleNamespace(_process=SimpleNamespace(poll=lambda: None))
        mgr.sessions['default'] = alive
        with patch.object(mgr, 'create_session') as mock_create:
            assert mgr.ensure_default_session() is alive
        mock_create.assert_not_called()

    def test_dead_recreates(self, mgr: SessionManager) -> None:
        dead = SimpleNamespace(
            _process=SimpleNamespace(poll=lambda: 3), close=MagicMock()
        )
        mgr.sessions['default'] = dead
        fresh = MagicMock()
        with (
            patch.object(mgr, 'create_session', return_value=fresh) as mock_create,
            patch('backend.execution.utils.shell.session_manager.logger.info') as mock_info,
        ):
            result = mgr.ensure_default_session(foo='bar')
        assert result is fresh
        mock_create.assert_called_once_with('default', foo='bar')
        assert mock_info.call_args.args[0] == 'ensure_default_session: replaced dead default session'

    def test_close_failure_debug_logged(self, mgr: SessionManager) -> None:
        dead = SimpleNamespace(
            _process=SimpleNamespace(poll=lambda: 3), close=MagicMock()
        )
        mgr.sessions['default'] = dead
        fresh = MagicMock()
        with (
            patch.object(mgr, 'close_session', side_effect=RuntimeError('boom')),
            patch.object(mgr, 'create_session', return_value=fresh),
            patch('backend.execution.utils.shell.session_manager.logger.debug') as mock_debug,
        ):
            assert mgr.ensure_default_session() is fresh
        assert mock_debug.call_args.args[0] == 'ensure_default_session: close failed'
