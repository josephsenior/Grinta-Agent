"""Tests for persistent LSP sessions and timeout profiles."""

from __future__ import annotations

import os
from pathlib import Path
from unittest.mock import MagicMock, patch

from backend.utils.http.stdio_json_rpc import (
    encode_json_rpc_message,
    feed_content_length_buffer,
)
from backend.utils.lsp.lsp_project_routing import LspFileContext
from backend.utils.lsp.lsp_session import (
    LspSession,
    LspSessionPool,
    _sessions_disabled,
    _stderr_debug_enabled,
    reset_lsp_session_pool,
)
from backend.utils.lsp.lsp_timeouts import (
    effective_query_timeout,
    init_timeout_for_server,
    query_timeout_for_server,
)


def test_stderr_debug_enabled_and_sessions_disabled_env() -> None:
    with patch.dict(os.environ, {'GRINTA_LSP_DEBUG_STDERR': '1'}):
        assert _stderr_debug_enabled() is True
    with patch.dict(os.environ, {'GRINTA_LSP_DEBUG_STDERR': '0'}):
        assert _stderr_debug_enabled() is False
    with patch.dict(os.environ, {'GRINTA_DISABLE_LSP_SESSION': 'yes'}):
        assert _sessions_disabled() is True
    with patch.dict(os.environ, {'GRINTA_DISABLE_LSP_SESSION': 'no'}):
        assert _sessions_disabled() is False


def test_encode_and_feed_content_length_buffer_roundtrip() -> None:
    message = {'jsonrpc': '2.0', 'id': 7, 'result': {'ok': True}}
    framed = encode_json_rpc_message(message)
    parsed, leftover = feed_content_length_buffer(framed)
    assert leftover == b''
    assert len(parsed) == 1
    assert parsed[0]['id'] == 7


def test_feed_content_length_buffer_handles_partial_frame() -> None:
    message = {'jsonrpc': '2.0', 'id': 1, 'result': 1}
    framed = encode_json_rpc_message(message)
    half = len(framed) // 2
    parsed, leftover = feed_content_length_buffer(framed[:half])
    assert parsed == []
    assert leftover == framed[:half]
    parsed2, leftover2 = feed_content_length_buffer(leftover + framed[half:])
    assert [m['id'] for m in parsed2] == [1]
    assert leftover2 == b''


def test_slow_server_timeouts() -> None:
    assert query_timeout_for_server('jdtls') == 45.0
    assert init_timeout_for_server('metals') == 60.0
    assert query_timeout_for_server('rust-analyzer') == 15.0


def test_effective_query_timeout_post_edit_floor() -> None:
    assert effective_query_timeout('jdtls', 3.0, post_edit=True) == 12.0
    assert effective_query_timeout('rust-analyzer', 3.0, post_edit=True) == 5.0
    assert effective_query_timeout('rust-analyzer', 8.0, post_edit=True) == 8.0
    assert effective_query_timeout('jdtls', None) == 45.0


def test_lsp_session_pool_reuses_alive_session(tmp_path: Path) -> None:
    reset_lsp_session_pool()
    ctx = LspFileContext(
        server_name='rust-analyzer',
        command=('rust-analyzer',),
        language_id='rust',
        workspace_root=tmp_path,
    )
    pool = LspSessionPool()
    mock_session = MagicMock()
    mock_session.is_alive.return_value = True

    with patch('backend.utils.lsp.lsp_session.LspSession', return_value=mock_session):
        first = pool.get(ctx)
        second = pool.get(ctx)

    assert first is mock_session
    assert second is mock_session
    assert mock_session.start.call_count == 1


def test_lsp_session_wait_publish_diagnostics() -> None:
    ctx = LspFileContext(
        server_name='rust-analyzer',
        command=('rust-analyzer',),
        language_id='rust',
        workspace_root=Path('.'),
    )
    session = LspSession(ctx)
    uri = 'file:///tmp/a.rs'
    payload = {
        'jsonrpc': '2.0',
        'method': 'textDocument/publishDiagnostics',
        'params': {
            'uri': uri,
            'diagnostics': [
                {
                    'range': {
                        'start': {'line': 0, 'character': 0},
                        'end': {'line': 0, 'character': 1},
                    },
                    'message': 'unused',
                    'severity': 2,
                }
            ],
        },
    }
    session._inbox.put(payload)  # noqa: SLF001
    diags = session.wait_publish_diagnostics(uri, timeout=0.5)
    assert len(diags) == 1
    assert diags[0]['message'] == 'unused'


def test_lsp_session_supports_capability(tmp_path: Path) -> None:
    ctx = LspFileContext(
        server_name='pyright-langserver',
        command=('pyright-langserver', '--stdio'),
        language_id='python',
        workspace_root=tmp_path,
    )
    session = LspSession(ctx)
    session._server_capabilities = {  # noqa: SLF001
        'hoverProvider': True,
        'definitionProvider': True,
        'codeActionProvider': False,
        'documentSymbolProvider': {'hierarchicalDocumentSymbolSupport': True},
    }
    assert session.supports('textDocument/hover') is True
    assert session.supports('textDocument/definition') is True
    assert session.supports('textDocument/codeAction') is False
    assert session.supports('textDocument/documentSymbol') is True
    assert session.supports('textDocument/signatureHelp') is True


def test_lsp_session_prepare_document_did_open_and_did_change(tmp_path: Path) -> None:
    ctx = LspFileContext(
        server_name='pyright-langserver',
        command=('pyright-langserver', '--stdio'),
        language_id='python',
        workspace_root=tmp_path,
    )
    session = LspSession(ctx)
    uri = 'file:///tmp/mod.py'

    with (
        patch.object(session, 'ensure_initialized', return_value=True),
        patch.object(session, '_write_message') as mock_write,
    ):
        # First call -> didOpen
        res1 = session.prepare_document(uri, 'python', 'def foo(): pass')
        assert res1 is True
        assert mock_write.call_count == 1
        assert mock_write.call_args[0][0]['method'] == 'textDocument/didOpen'

        # Second call with updated source -> didChange
        res2 = session.prepare_document(uri, 'python', 'def foo(): print(1)')
        assert res2 is True
        assert mock_write.call_count == 2
        assert mock_write.call_args[0][0]['method'] == 'textDocument/didChange'


def test_lsp_session_ensure_initialized_rejects_error_response(tmp_path: Path) -> None:
    ctx = LspFileContext(
        server_name='fake',
        command=('python', '-c', 'pass'),
        language_id='python',
        workspace_root=tmp_path,
    )
    session = LspSession(ctx)
    error_response = {
        'jsonrpc': '2.0',
        'id': 1,
        'error': {'code': -32603, 'message': 'internal error on init'},
    }

    def fake_wait_for_response(_id: int, _timeout: float):
        session._inbox.put(error_response)  # noqa: SLF001
        return error_response

    with (
        patch.object(session, 'start', return_value=True),
        patch.object(session, '_write_message'),
        patch.object(session, '_wait_for_response', side_effect=fake_wait_for_response),
    ):
        result = session.ensure_initialized(timeout=0.5)

    assert result is False
    assert session._initialized is False  # noqa: SLF001
    assert session._closed is True  # noqa: SLF001


def test_lsp_session_collect_notifications_early_return(tmp_path: Path) -> None:
    import time as _time

    ctx = LspFileContext(
        server_name='rust-analyzer',
        command=('rust-analyzer',),
        language_id='rust',
        workspace_root=tmp_path,
    )
    session = LspSession(ctx)
    uri = 'file:///tmp/b.rs'
    payload = {
        'jsonrpc': '2.0',
        'method': 'textDocument/publishDiagnostics',
        'params': {'uri': uri, 'diagnostics': []},
    }
    session._inbox.put(payload)  # noqa: SLF001
    start = _time.monotonic()
    diags = session.wait_publish_diagnostics(uri, timeout=5.0)
    elapsed = _time.monotonic() - start
    assert elapsed < 1.0
    assert len(diags) == 0


def test_lsp_session_stderr_ring_buffer_captures_output(tmp_path: Path) -> None:
    import sys

    ctx = LspFileContext(
        server_name='fake-crash',
        command=(
            sys.executable,
            '-c',
            (
                'import sys, time; '
                "sys.stderr.write('boom startup failure\\n'); "
                'sys.stderr.flush(); '
                'time.sleep(0.1); '
                'sys.exit(1)'
            ),
        ),
        language_id='python',
        workspace_root=tmp_path,
    )
    session = LspSession(ctx)
    assert session.start() is True
    proc = session._process  # noqa: SLF001
    if proc is not None:
        proc.wait(timeout=5.0)
    import time as _time

    _time.sleep(0.2)
    snippet = session.recent_stderr()
    assert 'boom startup failure' in snippet
    session.close()
