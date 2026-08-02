"""Regression tests for the persistent LSP session's pipe reader."""

from __future__ import annotations

import sys
from pathlib import Path

from backend.utils.http.stdio_json_rpc import encode_json_rpc_message
from backend.utils.lsp.lsp_project_routing import LspFileContext
from backend.utils.lsp.lsp_session import LspSession


def test_lsp_session_reader_delivers_short_frame_without_waiting_for_eof(
    tmp_path: Path,
) -> None:
    response = encode_json_rpc_message(
        {
            'jsonrpc': '2.0',
            'id': 1,
            'result': {'capabilities': {'referencesProvider': True}},
        }
    )
    assert len(response) < 4096
    ctx = LspFileContext(
        server_name='fake-short-response',
        command=(
            sys.executable,
            '-c',
            (
                'import sys, time; '
                f'sys.stdout.buffer.write({response!r}); '
                'sys.stdout.buffer.flush(); '
                'time.sleep(5)'
            ),
        ),
        language_id='python',
        workspace_root=tmp_path,
    )
    session = LspSession(ctx)

    try:
        assert session.ensure_initialized(timeout=1.0) is True
    finally:
        session.close()
