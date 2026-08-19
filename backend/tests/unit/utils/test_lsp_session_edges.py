"""Edge-path tests for backend.utils.lsp.lsp_session.

Covers the branches not exercised by test_lsp_session.py: start/close failure
handling, reader/stderr thread tails, response-waiting bookkeeping, and pool
replacement logic.
"""

from __future__ import annotations

import logging
import os
from pathlib import Path
from unittest.mock import MagicMock, patch

from backend.utils.http.stdio_json_rpc import encode_json_rpc_message
from backend.utils.lsp.lsp_project_routing import LspFileContext
from backend.utils.lsp.lsp_session import (
    LspSession,
    LspSessionPool,
    reset_lsp_session_pool,
)

_CTX = LspFileContext(
    server_name='rust-analyzer',
    command=('rust-analyzer',),
    language_id='rust',
    workspace_root=Path.cwd(),
)


def _make_session() -> LspSession:
    return LspSession(_CTX)


# ── start ────────────────────────────────────────────────────────────


class TestStart:
    def test_already_alive_returns_true(self):
        session = _make_session()
        session._process = MagicMock(poll=lambda: None)  # noqa: SLF001
        assert session.start() is True

    def test_clears_queued_inbox_before_start(self):
        session = _make_session()
        session._inbox.put({'id': 1})
        session._inbox.put({'id': 2})
        with patch('subprocess.Popen') as popen:
            popen.return_value = MagicMock(
                stdin=object(), stdout=object(), stderr=object()
            )
            assert session.start() is True
        assert session._inbox.empty()

    def test_popen_failure_returns_false(self):
        session = _make_session()
        with (
            patch('subprocess.Popen', side_effect=OSError('no such binary')),
            patch.object(logging.getLogger('app'), 'warning') as warn,
        ):
            assert session.start() is False
        assert session._process is None  # noqa: SLF001
        assert any('failed to start' in str(c.args) for c in warn.call_args_list)


# ── close ────────────────────────────────────────────────────────────


class TestClose:
    def test_already_closed_noop(self):
        session = _make_session()
        session._closed = True  # noqa: SLF001
        session.close()  # must not raise

    def test_shutdown_write_exception_swallowed(self):
        session = _make_session()
        proc = MagicMock()
        proc.stdin = object()
        proc.poll.return_value = None
        proc.wait.return_value = 0
        session._process = proc  # noqa: SLF001
        session._initialized = True  # noqa: SLF001
        with patch.object(session, '_write_message', side_effect=OSError('broken pipe')):
            session.close()  # must not raise

    def test_kill_exception_swallowed(self):
        session = _make_session()
        proc = MagicMock()
        proc.stdin = object()
        proc.poll.return_value = None
        proc.kill.side_effect = OSError('kill failed')
        proc.wait.return_value = 0
        session._process = proc  # noqa: SLF001
        session.close()  # must not raise

    def test_wait_exception_falls_back_to_poll(self):
        session = _make_session()
        proc = MagicMock()
        proc.stdin = object()
        proc.poll.return_value = None
        proc.wait.side_effect = OSError('wait failed')
        session._process = proc  # noqa: SLF001
        session.close()  # must not raise
        proc.poll.assert_called()

    def test_warns_on_unexpected_exit_after_initialize(self):
        session = _make_session()
        proc = MagicMock()
        proc.stdin = object()
        proc.poll.return_value = 1
        proc.wait.return_value = 1
        session._process = proc  # noqa: SLF001
        session._initialized = True  # noqa: SLF001
        session._stderr_ring.append('segfault here')  # noqa: SLF001
        with patch.object(logging.getLogger('app'), 'warning') as warn:
            session.close()
        assert any('exited with code' in str(c.args) and 1 in c.args for c in warn.call_args_list)

    def test_stderr_debug_tail_on_close(self):
        session = _make_session()
        proc = MagicMock()
        proc.stdin = object()
        proc.poll.return_value = 0
        proc.wait.return_value = 0
        session._process = proc  # noqa: SLF001
        session._stderr_ring.append('tail line')  # noqa: SLF001
        with (
            patch.dict(os.environ, {'GRINTA_LSP_DEBUG_STDERR': '1'}),
            patch.object(logging.getLogger('app'), 'debug') as dbg,
        ):
            session.close()
        assert any('Stderr tail' in str(c.args) for c in dbg.call_args_list)


# ── reader / stderr threads ──────────────────────────────────────────


class TestReaders:
    def test_read_stdout_no_stdout(self):
        session = _make_session()
        proc = MagicMock(stdout=None)
        session._process = proc  # noqa: SLF001
        session._read_stdout()  # must not raise

    def test_read_stdout_drains_tail_after_exit(self):
        session = _make_session()
        framed = encode_json_rpc_message({'jsonrpc': '2.0', 'id': 9, 'result': 1})
        proc = MagicMock()
        proc.poll.return_value = None
        proc.stdout.read1 = MagicMock(return_value=b'')
        proc.stdout.read = MagicMock(return_value=framed)
        session._process = proc  # noqa: SLF001
        session._read_stdout()
        assert session._inbox.get(timeout=0.1)['id'] == 9

    def test_read_stderr_no_stderr(self):
        session = _make_session()
        proc = MagicMock(stderr=None)
        session._process = proc  # noqa: SLF001
        session._read_stderr()  # must not raise

    def test_read_stderr_debug_logging(self):
        session = _make_session()
        proc = MagicMock()
        proc.poll.side_effect = [None, 0]
        proc.stderr.readline.side_effect = [b'warn: bad thing\n', b'']
        session._process = proc  # noqa: SLF001
        with (
            patch.dict(os.environ, {'GRINTA_LSP_DEBUG_STDERR': '1'}),
            patch.object(logging.getLogger('app'), 'debug') as dbg,
        ):
            session._read_stderr()
        assert any('bad thing' in str(c.args) for c in dbg.call_args_list)

    def test_read_stderr_exception_logged(self):
        session = _make_session()
        proc = MagicMock()
        proc.poll.return_value = None
        proc.stderr.readline.side_effect = OSError('pipe broke')
        session._process = proc  # noqa: SLF001
        with patch.object(logging.getLogger('app'), 'debug') as dbg:
            session._read_stderr()  # must not raise
        assert any('stderr reader stopped' in str(c.args) for c in dbg.call_args_list)


# ── stderr snippet ───────────────────────────────────────────────────


class TestStderrSnippet:
    def test_empty_ring_returns_empty(self):
        session = _make_session()
        session._stderr_ring.clear()  # noqa: SLF001
        assert session._format_stderr_snippet() == ''

    def test_long_snippet_truncated_to_2000(self):
        session = _make_session()
        session._stderr_ring.append('x' * 3000)  # noqa: SLF001
        assert len(session._format_stderr_snippet()) == 2000


# ── _write_message ───────────────────────────────────────────────────


class TestWriteMessage:
    def test_missing_stdin_raises(self):
        session = _make_session()
        proc = MagicMock(stdin=None)
        proc.poll.return_value = None
        session._process = proc  # noqa: SLF001
        try:
            session._write_message({})
            raise AssertionError('expected OSError')
        except OSError:
            pass

    def test_exited_process_raises(self):
        session = _make_session()
        proc = MagicMock(stdin=object())
        proc.poll.return_value = 3
        proc.returncode = 3
        session._process = proc  # noqa: SLF001
        try:
            session._write_message({})
            raise AssertionError('expected OSError')
        except OSError:
            pass


# ── response waiting ─────────────────────────────────────────────────


class TestWaitForResponse:
    def test_skips_other_messages_and_requeues(self):
        session = _make_session()
        session._inbox.put({'jsonrpc': '2.0', 'id': 5, 'result': 'a'})
        session._inbox.put({'jsonrpc': '2.0', 'id': 7, 'result': 'b'})
        resp = session._wait_for_response(7, timeout=0.5)
        assert resp['result'] == 'b'
        requeued = session._inbox.get_nowait()
        assert requeued['id'] == 5

    def test_timeout_returns_none_and_requeues(self):
        session = _make_session()
        session._inbox.put({'jsonrpc': '2.0', 'id': 5, 'result': 'a'})
        assert session._wait_for_response(99, timeout=0.05) is None
        assert session._inbox.get_nowait()['id'] == 5

    def test_collect_notifications_grace_break_and_deferrals(self):
        session = _make_session()
        uri = 'file:///tmp/x.rs'
        non_match = {'jsonrpc': '2.0', 'method': 'window/logMessage', 'params': {}}
        match = {
            'jsonrpc': '2.0',
            'method': 'textDocument/publishDiagnostics',
            'params': {'uri': uri, 'diagnostics': []},
        }
        session._inbox.put(non_match)
        session._inbox.put(match)
        msgs = session._collect_notifications(
            'textDocument/publishDiagnostics', timeout=2.0, uri=uri, grace=0.05
        )
        assert len(msgs) == 1
        assert session._inbox.get_nowait()['method'] == 'window/logMessage'

    def test_collect_notifications_uri_mismatch_deferred(self):
        session = _make_session()
        wrong_uri = {'jsonrpc': '2.0', 'method': 'textDocument/publishDiagnostics',
                     'params': {'uri': 'file:///other.rs', 'diagnostics': []}}
        session._inbox.put(wrong_uri)
        msgs = session._collect_notifications(
            'textDocument/publishDiagnostics', timeout=0.05, uri='file:///x.rs'
        )
        assert msgs == []
        assert session._inbox.get_nowait()['method'] == 'textDocument/publishDiagnostics'


# ── ensure_initialized ───────────────────────────────────────────────


class TestEnsureInitialized:
    def test_already_initialized(self):
        session = _make_session()
        session._initialized = True  # noqa: SLF001
        assert session.ensure_initialized() is True

    def test_start_failure_returns_false(self):
        session = _make_session()
        with patch.object(session, 'start', return_value=False):
            assert session.ensure_initialized() is False

    def test_initialize_write_oserror(self):
        session = _make_session()
        with (
            patch.object(session, 'start', return_value=True),
            patch.object(session, '_write_message', side_effect=OSError('pipe closed')),
            patch.object(logging.getLogger('app'), 'warning') as warn,
        ):
            assert session.ensure_initialized(timeout=0.5) is False
        assert any('initialize write failed' in str(c.args) for c in warn.call_args_list)

    def test_initialize_timeout(self):
        session = _make_session()
        with (
            patch.object(session, 'start', return_value=True),
            patch.object(session, '_write_message'),
            patch.object(session, '_wait_for_response', return_value=None),
            patch.object(logging.getLogger('app'), 'warning') as warn,
        ):
            assert session.ensure_initialized(timeout=0.5) is False
        assert any('timed out' in str(c.args) for c in warn.call_args_list)

    def test_initialize_no_result(self):
        session = _make_session()
        response = {'jsonrpc': '2.0', 'id': 1}
        with (
            patch.object(session, 'start', return_value=True),
            patch.object(session, '_write_message'),
            patch.object(session, '_wait_for_response', return_value=response),
            patch.object(logging.getLogger('app'), 'warning') as warn,
        ):
            assert session.ensure_initialized(timeout=0.5) is False
        assert any('no result' in str(c.args) for c in warn.call_args_list)

    def test_initialized_notification_write_failure_ignored(self):
        session = _make_session()
        response = {
            'jsonrpc': '2.0',
            'id': 1,
            'result': {'capabilities': {'hoverProvider': True}},
        }

        with (
            patch.object(session, 'start', return_value=True),
            patch.object(session, '_write_message', side_effect=[None, OSError('gone')]),
            patch.object(session, '_wait_for_response', return_value=response),
        ):
            assert session.ensure_initialized(timeout=0.5) is True
        assert session._initialized is True  # noqa: SLF001


# ── supports ─────────────────────────────────────────────────────────


class TestSupports:
    def test_string_provider_is_supported(self):
        session = _make_session()
        session._server_capabilities = {'hoverProvider': 'manual'}  # noqa: SLF001
        assert session.supports('textDocument/hover') is True


# ── request / prepare_document ───────────────────────────────────────


class TestRequest:
    def test_request_roundtrip(self):
        session = _make_session()
        session._next_id = 10  # noqa: SLF001
        expected = {'jsonrpc': '2.0', 'id': 10, 'result': {'ok': True}}
        with (
            patch.object(session, '_write_message'),
            patch.object(session, '_wait_for_response', return_value=expected),
        ):
            result = session.request('textDocument/hover', {'position': {}}, timeout=0.5)
        assert result is expected

    def test_request_write_failure_returns_none(self):
        session = _make_session()
        with (
            patch.object(session, '_write_message', side_effect=OSError('dead')) as write_mock,
            patch.object(session, '_wait_for_response') as wait_mock,
        ):
            assert session.request('textDocument/hover', {}, timeout=0.5) is None
            wait_mock.assert_not_called()

    def test_prepare_document_skips_when_uninitialized(self):
        session = _make_session()
        with patch.object(session, 'ensure_initialized', return_value=False):
            assert session.prepare_document('file:///a.py', 'python', 'x') is False


# ── pool ─────────────────────────────────────────────────────────────


class TestPool:
    def test_get_disabled_returns_none(self):
        with patch.dict(os.environ, {'GRINTA_DISABLE_LSP_SESSION': '1'}):
            assert LspSessionPool().get(_CTX) is None

    def test_get_closes_dead_session_and_replaces(self):
        reset_lsp_session_pool()
        pool = LspSessionPool()
        dead = MagicMock()
        dead.is_alive.return_value = False
        pool._sessions[('rust-analyzer', str(_CTX.workspace_root.resolve()))] = dead  # noqa: SLF001
        fresh = MagicMock()
        fresh.is_alive.return_value = True
        fresh.start.return_value = True
        with patch('backend.utils.lsp.lsp_session.LspSession', return_value=fresh):
            got = pool.get(_CTX)
        assert got is fresh
        dead.close.assert_called_once()

    def test_get_start_failure_returns_none(self):
        reset_lsp_session_pool()
        pool = LspSessionPool()
        session = MagicMock()
        session.start.return_value = False
        with patch('backend.utils.lsp.lsp_session.LspSession', return_value=session):
            assert pool.get(_CTX) is None

    def test_reset_closes_all_sessions(self):
        reset_lsp_session_pool()
        pool = LspSessionPool()
        a = MagicMock()
        b = MagicMock()
        pool._sessions[('a', 'w1')] = a  # noqa: SLF001
        pool._sessions[('b', 'w2')] = b  # noqa: SLF001
        pool.reset()
        a.close.assert_called_once()
        b.close.assert_called_once()
        assert pool._sessions == {}  # noqa: SLF001

    def test_module_level_reset(self):
        reset_lsp_session_pool()  # must not raise
        reset_lsp_session_pool()  # idempotent
