"""Edge-path tests for backend.utils.lsp.lsp_client.

Covers the one-shot fallback paths, response parsing, and URI handling not
exercised by test_lsp_client_helpers.py. Subprocesses are mocked throughout.
"""

from __future__ import annotations

import logging
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from backend.utils.lsp import lsp_client as lc
from backend.utils.lsp.lsp_project_routing import LspFileContext

CTX = LspFileContext(
    server_name='pyright-langserver',
    command=('pyright-langserver', '--stdio'),
    language_id='python',
    workspace_root=Path.cwd(),
)

URI = 'file:///app/main.py'
SRC = 'x = 1\n'


@pytest.fixture
def pyfile(tmp_path: Path) -> str:
    p = tmp_path / 'main.py'
    p.write_text(SRC, encoding='utf-8')
    return str(p)


# ── formatting ───────────────────────────────────────────────────────


class TestFormatting:
    def test_unavailable_with_error_message(self):
        res = lc.LspResult(available=False, error='boom').format_text('hover')
        assert res == 'LSP is not available. boom'

    def test_symbols_empty_message(self):
        assert 'No symbols' in lc.LspResult().format_text('list_symbols')

    def test_no_code_actions_message(self):
        assert 'No code actions' in lc.LspResult().format_text('code_action')

    def test_location_str_with_message(self):
        loc = lc.LspLocation(file='/a.py', line=2, column=3, message='hi')
        assert str(loc) == '/a.py:2:3 - hi'


# ── one-shot subprocess runner ───────────────────────────────────────


class TestRunLspSubprocess:
    def test_runs_bounded_subprocess(self, tmp_path: Path):
        import sys

        script = tmp_path / 'echo.py'
        script.write_text(
            'import sys\n'
            'body = b"{\\"result\\": true}"\n'
            'sys.stdout.buffer.write(b"Content-Length: " + str(len(body)).encode() + b"\\r\\n\\r\\n" + body)\n',
            encoding='utf-8',
        )
        result = lc._run_lsp_subprocess(
            [sys.executable, str(script)],
            process_timeout=10.0,
            stdin_data=None,
        )
        assert 'Content-Length' in result.stdout


# ── client helpers ───────────────────────────────────────────────────


class TestClientHelpers:
    def test_get_server_command_context_none(self):
        client = lc.LspClient()
        with patch.object(client, '_get_context', return_value=None):
            assert client._get_server_command('/x.py') is None

    def test_unavailable_lang_key_exception(self):
        client = lc.LspClient()
        with (
            patch.object(client, '_get_context', side_effect=Exception('no context')),
            patch(
                'backend.utils.lsp.lsp_project_routing.find_project_root',
                side_effect=OSError('no root'),
            ),
        ):
            res = client._unavailable('/x.py')
        assert not res.available
        assert 'No language server available' in res.error

    def test_unavailable_installed_tool_available(self):
        client = lc.LspClient()
        tool = MagicMock()
        tool.available = True
        spec = MagicMock()
        spec.name = 'pyright-langserver'
        with (
            patch.object(client, '_get_context', side_effect=Exception('none')),
            patch(
                'backend.utils.lsp.lsp_project_routing.find_project_root',
                return_value=Path('.'),
            ),
            patch(
                'backend.utils.lsp.lsp_project_routing.resolve_language_key',
                return_value='python',
            ),
            patch(
                'backend.utils.runtime_detect.CANONICAL_LSP_SERVERS', {'python': spec}
            ),
            patch(
                'backend.utils.runtime_detect.detect_lsp_servers',
                return_value={spec.name: tool},
            ),
        ):
            res = client._unavailable('/x.py')
        assert not res.available
        assert 'installed but failed to start' in res.error

    def test_query_catches_exception(self):
        client = lc.LspClient()
        with (
            patch.object(client, '_get_server_command', return_value=['pyright']),
            patch.object(client, '_run_query', side_effect=RuntimeError('boom')),
            patch.object(logging.getLogger('app'), 'warning') as warn,
        ):
            res = client.query('hover', '/app/main.py')
        assert not res.available
        assert 'boom' in res.error
        assert any('query failed' in str(c.args) for c in warn.call_args_list)

    def test_resolve_timeout(self):
        client = lc.LspClient()
        with patch.object(lc, 'effective_query_timeout', return_value=7.5) as eq:
            assert client._resolve_timeout(CTX, None) == 7.5
            eq.assert_called_once_with('pyright-langserver', None, post_edit=False)

    def test_use_session_none_returns_fallback(self):
        client = lc.LspClient()
        with patch.object(lc, 'get_lsp_session_pool') as pool:
            pool.return_value.get.return_value = None
            assert client._use_session(CTX, URI, 'python', SRC) == (None, True)

    def test_use_session_prepare_failure_no_fallback(self):
        client = lc.LspClient()
        session = MagicMock()
        session.prepare_document.return_value = False
        with patch.object(lc, 'get_lsp_session_pool') as pool:
            pool.return_value.get.return_value = session
            assert client._use_session(CTX, URI, 'python', SRC) == (None, False)

    def test_error_from_response_variants(self):
        client = lc.LspClient()
        assert client._error_from_response({'error': {'message': 'nope'}}) == 'nope'
        assert (
            client._error_from_response({'error': {'code': -1}}) == 'LSP error code -1'
        )
        assert client._error_from_response({'error': {}}) == 'LSP error (no message)'
        assert client._error_from_response({'error': 'string'}) is None


# ── one-shot RPC ─────────────────────────────────────────────────────


def _encoded(*messages):
    import json

    out = ''
    for m in messages:
        body = json.dumps(m).encode('utf-8')
        out += 'Content-Length: ' + str(len(body)) + '\r\n\r\n' + body.decode('utf-8')
    return out


class TestOneShotRpc:
    def test_frames_and_parses_responses(self):
        client = lc.LspClient()
        result = MagicMock()
        result.timed_out = False
        result.stderr = ''
        result.returncode = 0
        result.stdout = _encoded({'jsonrpc': '2.0', 'id': 1, 'result': {'ok': 1}})
        with patch.object(lc, '_run_lsp_subprocess', return_value=result) as runner:
            parsed, started, snippet = client._rpc(
                [{'jsonrpc': '2.0', 'id': 1, 'result': {}}],
                ['pyright'],
                process_timeout=5.0,
            )
        assert started is True
        assert parsed[0]['id'] == 1
        assert snippet == ''
        runner.assert_called_once()

    def test_timed_out_returns_empty(self):
        client = lc.LspClient()
        result = MagicMock()
        result.timed_out = True
        result.stderr = 'timeout stderr tail'
        with patch.object(lc, '_run_lsp_subprocess', return_value=result):
            parsed, started, snippet = client._rpc(
                [{}], ['pyright'], process_timeout=5.0
            )
        assert parsed == []
        assert started is False
        assert snippet == 'timeout stderr tail'

    def test_nonzero_exit_with_stderr(self):
        client = lc.LspClient()
        result = MagicMock()
        result.timed_out = False
        result.stderr = '  server crashed  '
        result.returncode = 3
        result.stdout = b''
        with patch.object(lc, '_run_lsp_subprocess', return_value=result):
            parsed, started, snippet = client._rpc(
                [{}], ['pyright'], process_timeout=5.0
            )
        assert parsed == []
        assert started is False
        assert snippet == 'server crashed'

    def test_no_output_but_zero_exit(self):
        client = lc.LspClient()
        result = MagicMock()
        result.timed_out = False
        result.stderr = ''
        result.returncode = 0
        result.stdout = b''
        with patch.object(lc, '_run_lsp_subprocess', return_value=result):
            parsed, started, snippet = client._rpc(
                [{}], ['pyright'], process_timeout=5.0
            )
        assert parsed == []
        assert started is False
        assert snippet == ''

    def test_timeout_error_path(self):
        client = lc.LspClient()
        with (
            patch.object(lc, '_run_lsp_subprocess', side_effect=TimeoutError('slow')),
            patch.object(logging.getLogger('app'), 'warning') as warn,
        ):
            parsed, started, snippet = client._rpc(
                [{}], ['pyright'], process_timeout=5.0
            )
        assert parsed == []
        assert started is False
        assert any('timed out' in str(c.args) for c in warn.call_args_list)

    def test_generic_error_path(self):
        client = lc.LspClient()
        with (
            patch.object(
                lc, '_run_lsp_subprocess', side_effect=OSError('spawn failed')
            ),
            patch.object(logging.getLogger('app'), 'warning') as warn,
        ):
            parsed, started, snippet = client._rpc(
                [{}], ['pyright'], process_timeout=5.0
            )
        assert parsed == []
        assert started is False
        assert any('failed' in str(c.args) for c in warn.call_args_list)

    def test_build_init_msgs_no_context_raises(self):
        client = lc.LspClient()
        with patch.object(client, '_get_context', return_value=None):
            try:
                client._build_init_msgs(URI, '/app/main.py', SRC)
                raise AssertionError('expected RuntimeError')
            except RuntimeError:
                pass


# ── query command dispatch ───────────────────────────────────────────


class TestQueryDispatch:
    def test_query_diagnostics_session_path(self, pyfile):
        client = lc.LspClient()
        session = MagicMock()
        session.wait_publish_diagnostics.return_value = [
            {'range': {'start': {'line': 0, 'character': 0}}, 'message': 'err'}
        ]
        with (
            patch.object(client, '_get_context', return_value=CTX),
            patch.object(client, '_resolve_timeout', return_value=5.0),
            patch.object(client, '_use_session', return_value=(session, False)),
        ):
            res = client.query('diagnostics', pyfile)
        assert res.available
        assert len(res.locations) == 1
        assert res.locations[0].message == 'err'

    def test_query_diagnostics_session_failed(self, pyfile):
        client = lc.LspClient()
        with (
            patch.object(client, '_get_context', return_value=CTX),
            patch.object(client, '_resolve_timeout', return_value=5.0),
            patch.object(client, '_use_session', return_value=(None, False)),
        ):
            res = client.query('diagnostics', pyfile)
        assert not res.available
        assert 'failed to start' in res.error

    def test_query_diagnostics_oneshot_fallback(self, pyfile):
        client = lc.LspClient()
        uri = Path(pyfile).as_uri()
        with (
            patch.object(client, '_get_context', return_value=CTX),
            patch.object(client, '_resolve_timeout', return_value=5.0),
            patch.object(client, '_use_session', return_value=(None, True)),
            patch.object(
                client,
                '_rpc',
                return_value=(
                    [
                        {
                            'method': 'textDocument/publishDiagnostics',
                            'params': {
                                'uri': uri,
                                'diagnostics': [
                                    {
                                        'range': {'start': {'line': 3, 'character': 1}},
                                        'message': 'bad',
                                    }
                                ],
                            },
                        }
                    ],
                    True,
                    '',
                ),
            ),
        ):
            res = client.query('diagnostics', pyfile)
        assert res.available
        assert len(res.locations) == 1
        assert res.locations[0].line == 4

    def test_query_diagnostics_oneshot_not_started(self, pyfile):
        client = lc.LspClient()
        with (
            patch.object(client, '_get_context', return_value=CTX),
            patch.object(client, '_resolve_timeout', return_value=5.0),
            patch.object(client, '_use_session', return_value=(None, True)),
            patch.object(client, '_rpc', return_value=([], False, 'server exploded')),
        ):
            res = client.query('diagnostics', pyfile)
        assert not res.available
        assert 'server exploded' in res.error

    def test_query_hover_oneshot_fallback(self, pyfile):
        client = lc.LspClient()
        with (
            patch.object(client, '_get_context', return_value=CTX),
            patch.object(client, '_resolve_timeout', return_value=5.0),
            patch.object(client, '_use_session', return_value=(None, True)),
            patch.object(
                client,
                '_rpc',
                return_value=(
                    [
                        {
                            'jsonrpc': '2.0',
                            'id': 10,
                            'result': {'contents': 'doc string'},
                        }
                    ],
                    True,
                    '',
                ),
            ),
        ):
            res = client.query('hover', pyfile, 2, 3)
        assert res.available
        assert res.hover_text == 'doc string'

    def test_query_hover_oneshot_missing_result(self, pyfile):
        client = lc.LspClient()
        with (
            patch.object(client, '_get_context', return_value=CTX),
            patch.object(client, '_resolve_timeout', return_value=5.0),
            patch.object(client, '_use_session', return_value=(None, True)),
            patch.object(
                client,
                '_rpc',
                return_value=(
                    [
                        {
                            'jsonrpc': '2.0',
                            'id': 10,
                            'error': {'code': -1, 'message': 'nope'},
                        }
                    ],
                    True,
                    '',
                ),
            ),
        ):
            res = client.query('hover', pyfile, 2, 3)
        assert not res.available
        assert 'nope' in res.error

    def test_query_symbols_oneshot_fallback(self, pyfile):
        client = lc.LspClient()
        with (
            patch.object(client, '_get_context', return_value=CTX),
            patch.object(client, '_resolve_timeout', return_value=5.0),
            patch.object(client, '_use_session', return_value=(None, True)),
            patch.object(
                client,
                '_rpc',
                return_value=(
                    [
                        {
                            'jsonrpc': '2.0',
                            'id': 20,
                            'result': [
                                {
                                    'name': 'main',
                                    'kind': 12,
                                    'range': {'start': {'line': 2}},
                                }
                            ],
                        }
                    ],
                    True,
                    '',
                ),
            ),
        ):
            res = client.query('list_symbols', pyfile)
        assert res.available
        assert res.symbols[0].name == 'main'
        assert res.symbols[0].line == 3

    def test_query_symbols_oneshot_not_started(self, pyfile):
        client = lc.LspClient()
        with (
            patch.object(client, '_get_context', return_value=CTX),
            patch.object(client, '_resolve_timeout', return_value=5.0),
            patch.object(client, '_use_session', return_value=(None, True)),
            patch.object(client, '_rpc', return_value=([], False, '')),
        ):
            res = client.query('list_symbols', pyfile)
        assert not res.available

    def test_query_locations_oneshot_fallback(self, pyfile):
        client = lc.LspClient()
        loc = {'uri': 'file:///app/target.py', 'range': {'start': {'line': 1}}}
        with (
            patch.object(client, '_get_context', return_value=CTX),
            patch.object(client, '_resolve_timeout', return_value=5.0),
            patch.object(client, '_use_session', return_value=(None, True)),
            patch.object(
                client,
                '_rpc',
                return_value=(
                    [{'jsonrpc': '2.0', 'id': 10, 'result': [loc]}],
                    True,
                    '',
                ),
            ),
        ):
            res = client.query('find_definition', pyfile, 2, 3)
        assert res.available
        assert len(res.locations) == 1
        assert res.locations[0].line == 2

    def test_query_locations_oneshot_not_started(self, pyfile):
        client = lc.LspClient()
        with (
            patch.object(client, '_get_context', return_value=CTX),
            patch.object(client, '_resolve_timeout', return_value=5.0),
            patch.object(client, '_use_session', return_value=(None, True)),
            patch.object(client, '_rpc', return_value=([], False, 'crashed')),
        ):
            res = client.query('find_references', pyfile, 2, 3)
        assert not res.available

    def test_query_code_action_oneshot_fallback(self, pyfile):
        client = lc.LspClient()
        with (
            patch.object(client, '_get_context', return_value=CTX),
            patch.object(client, '_resolve_timeout', return_value=5.0),
            patch.object(client, '_use_session', return_value=(None, True)),
            patch.object(
                client, '_collect_diagnostics_for_code_action', return_value=[]
            ),
            patch.object(
                client,
                '_execute_code_action_request',
                return_value=lc.LspResult(
                    available=True, code_actions=[lc.LspCodeAction(title='Fix it')]
                ),
            ),
        ):
            res = client.query('code_action', pyfile, 2, 3)
        assert res.available
        assert res.code_actions[0].title == 'Fix it'

    def test_query_code_action_oneshot_not_started(self, pyfile):
        client = lc.LspClient()
        with (
            patch.object(client, '_get_context', return_value=CTX),
            patch.object(client, '_resolve_timeout', return_value=5.0),
            patch.object(client, '_use_session', return_value=(None, True)),
            patch.object(
                client, '_collect_diagnostics_for_code_action', return_value=[]
            ),
            patch.object(
                client,
                '_execute_code_action_request',
                return_value=lc.LspResult(available=False, error='failed to start'),
            ),
        ):
            res = client.query('code_action', pyfile, 2, 3)
        assert not res.available


# ── parsing helpers ──────────────────────────────────────────────────


class TestParsing:
    def test_parse_code_action_items(self):
        client = lc.LspClient()
        result = [
            {
                'title': 'Fix',
                'kind': 'quickfix',
                'isPreferred': True,
                'diagnostics': [{'message': 'unused'}],
            },
            {'title': 'Fix'},  # duplicate title -> skipped
            'not-a-dict',  # skipped
            {'title': '   '},  # blank title -> skipped
            {'title': 'Zebra fix', 'kind': 'source'},
        ]
        actions = client._parse_code_action_items(result)
        assert [a.title for a in actions] == ['Fix', 'Zebra fix']  # preferred first
        assert actions[0].is_preferred is True
        assert actions[0].diagnostic_message == 'unused'

    def test_diag_contains_point(self):
        client = lc.LspClient()
        diag = {
            'range': {
                'start': {'line': 1, 'character': 2},
                'end': {'line': 3, 'character': 4},
            }
        }
        assert client._diag_contains_point(diag, 2, 3) is True
        assert client._diag_contains_point(diag, 0, 0) is False  # before start line
        assert client._diag_contains_point(diag, 4, 0) is False  # after end line
        assert client._diag_contains_point(diag, 1, 1) is False  # col before start
        assert client._diag_contains_point(diag, 3, 5) is False  # col after end

    def test_parse_hover_response_variants(self):
        client = lc.LspClient()
        r1 = client._parse_hover_response({'contents': {'value': 'value text'}})
        assert r1.hover_text == 'value text'
        r2 = client._parse_hover_response({'contents': ['a', 'b']})
        assert r2.hover_text == 'a\nb'
        r3 = client._parse_hover_response({'contents': 'plain'})
        assert r3.hover_text == 'plain'
        r4 = client._parse_hover_response({})
        assert r4.available is True

    def test_parse_location_response_variants(self):
        client = lc.LspClient()
        empty = client._parse_location_response(None)
        assert empty.available is True and empty.locations == []
        single = client._parse_location_response(
            {'uri': 'file:///app/t.py', 'range': {'start': {'line': 0}}}
        )
        assert single.locations[0].line == 1
        multi = client._parse_location_response(
            [{'uri': 'file:///app/t.py', 'range': {'start': {'line': 0}}}]
        )
        assert len(multi.locations) == 1

    def test_path_from_file_uri(self):
        assert lc.LspClient._path_from_file_uri('http://x/y') == 'http://x/y'
        assert (
            lc.LspClient._path_from_file_uri('file://server/share/f.py')
            == '//server/share/f.py'
        )
        assert (
            lc.LspClient._path_from_file_uri('file:///home/a%20b.py') == '/home/a b.py'
        )
        assert (
            lc.LspClient._path_from_file_uri('file:///c:/Windows/x.py')
            == 'c:/Windows/x.py'
        )

    def test_build_code_action_range_and_diags(self):
        client = lc.LspClient()
        source = 'a\nb\nc\n'
        diags = [
            {
                'range': {'start': {'line': 0}, 'end': {'line': 0}},
                'message': 'line 1 issue',
            }
        ]
        full, all_diags = client._build_code_action_range_and_diags(source, diags, 0, 0)
        assert full['start'] == {'line': 0, 'character': 0}
        assert full['end'] == {'line': 3, 'character': 0}
        assert all_diags == diags
        ranged, relevant = client._build_code_action_range_and_diags(
            source, diags, 0, 5
        )
        assert relevant == diags  # diag contains point
        ranged2, fallback = client._build_code_action_range_and_diags(
            source, diags, 2, 5
        )
        assert fallback == diags  # no diag at point -> falls back to all

    def test_collect_diagnostics_for_code_action(self):
        client = lc.LspClient()
        diag = {'range': {'start': {'line': 0}}, 'message': 'err'}
        with (
            patch.object(
                client,
                '_rpc',
                return_value=(
                    [
                        {
                            'method': 'textDocument/publishDiagnostics',
                            'params': {'uri': URI, 'diagnostics': [diag]},
                        }
                    ],
                    True,
                    '',
                ),
            ),
            patch.object(client, '_build_init_msgs', return_value=[]),
        ):
            got = client._collect_diagnostics_for_code_action(
                ['pyright'], URI, '/app/main.py', SRC, process_timeout=5.0
            )
        assert got == [diag]

    def test_collect_diagnostics_for_code_action_empty(self):
        client = lc.LspClient()
        with (
            patch.object(client, '_rpc', return_value=([], True, '')),
            patch.object(client, '_build_init_msgs', return_value=[]),
        ):
            got = client._collect_diagnostics_for_code_action(
                ['pyright'], URI, '/app/main.py', SRC, process_timeout=5.0
            )
        assert got == []

    def test_execute_code_action_request(self):
        client = lc.LspClient()
        with (
            patch.object(
                client,
                '_rpc',
                return_value=(
                    [
                        {
                            'jsonrpc': '2.0',
                            'id': 30,
                            'result': [{'title': 'Organize', 'kind': 'source'}],
                        }
                    ],
                    True,
                    '',
                ),
            ),
            patch.object(client, '_build_init_msgs', return_value=[]),
        ):
            res = client._execute_code_action_request(
                ['pyright'], URI, '/app/main.py', SRC, {}, [], process_timeout=5.0
            )
        assert res.available
        assert res.code_actions[0].title == 'Organize'

    def test_execute_code_action_request_error(self):
        client = lc.LspClient()
        with (
            patch.object(
                client,
                '_rpc',
                return_value=(
                    [
                        {
                            'jsonrpc': '2.0',
                            'id': 30,
                            'error': {'code': -1, 'message': 'denied'},
                        }
                    ],
                    True,
                    '',
                ),
            ),
            patch.object(client, '_build_init_msgs', return_value=[]),
        ):
            res = client._execute_code_action_request(
                ['pyright'], URI, '/app/main.py', SRC, {}, [], process_timeout=5.0
            )
        assert not res.available
        assert 'denied' in res.error

    def test_execute_code_action_request_no_match(self):
        client = lc.LspClient()
        with (
            patch.object(
                client, '_rpc', return_value=([{'id': 99, 'result': []}], True, '')
            ),
            patch.object(client, '_build_init_msgs', return_value=[]),
        ):
            res = client._execute_code_action_request(
                ['pyright'], URI, '/app/main.py', SRC, {}, [], process_timeout=5.0
            )
        assert res.available and res.code_actions == []

    def test_parse_document_symbols_non_list_and_location(self):
        client = lc.LspClient()
        assert client._parse_document_symbols('not-a-list', '') == []
        result = [
            {
                'name': 'f',
                'kind': 12,
                'location': {'uri': URI, 'range': {'start': {'line': 4}}},
                'children': 'not-a-list',  # skipped by walk guard
            }
        ]
        symbols = client._parse_document_symbols(result, '')
        assert symbols[0].line == 5
        filtered = client._parse_document_symbols(result, 'nomatch')
        assert filtered == []


# ── session-path branches and module helpers ─────────────────────────


class TestSessionPathsAndHelpers:
    def test_get_context_exception(self):
        client = lc.LspClient()
        with patch.object(lc, 'lsp_context_for_file', side_effect=OSError('no ctx')):
            assert client._get_context('/x.py') is None

    def test_query_no_server_command(self, pyfile):
        client = lc.LspClient()
        with patch.object(client, '_get_server_command', return_value=None):
            res = client.query('hover', pyfile)
        assert not res.available
        assert 'No language server available' in res.error

    def test_parse_lsp_responses(self):
        client = lc.LspClient()
        body = '{"jsonrpc": "2.0"}'
        parsed = client._parse_lsp_responses(
            'Content-Length: ' + str(len(body.encode())) + '\r\n\r\n' + body
        )
        assert parsed[0]['jsonrpc'] == '2.0'

    def test_get_lsp_client_singleton(self):
        assert lc.get_lsp_client() is lc.get_lsp_client()

    def test_query_diagnostics_ctx_none(self):
        client = lc.LspClient()
        with (
            patch.object(client, '_get_context', return_value=None),
            patch.object(
                client,
                '_unavailable',
                return_value=lc.LspResult(
                    available=False, error='No language server available'
                ),
            ),
        ):
            res = client._query_diagnostics('/x.py', URI, SRC)
        assert not res.available

    def test_query_code_actions_session_unsupported(self, pyfile):
        client = lc.LspClient()
        session = MagicMock()
        session.supports.return_value = False
        with (
            patch.object(client, '_get_context', return_value=CTX),
            patch.object(client, '_resolve_timeout', return_value=5.0),
            patch.object(client, '_use_session', return_value=(session, False)),
        ):
            res = client._query_code_actions(pyfile, Path(pyfile).as_uri(), SRC, 0, 0)
        assert not res.available
        assert 'does not advertise support' in res.error

    def test_query_code_actions_session_success(self, pyfile):
        client = lc.LspClient()
        session = MagicMock()
        session.supports.return_value = True
        session.wait_publish_diagnostics.return_value = []
        session.request.return_value = {'result': [{'title': 'Quick fix'}]}
        with (
            patch.object(client, '_get_context', return_value=CTX),
            patch.object(client, '_resolve_timeout', return_value=5.0),
            patch.object(client, '_use_session', return_value=(session, False)),
        ):
            res = client._query_code_actions(pyfile, Path(pyfile).as_uri(), SRC, 0, 0)
        assert res.available
        assert res.code_actions[0].title == 'Quick fix'

    def test_query_code_actions_session_none_response(self, pyfile):
        client = lc.LspClient()
        session = MagicMock()
        session.supports.return_value = True
        session.wait_publish_diagnostics.return_value = []
        session.request.return_value = None
        with (
            patch.object(client, '_get_context', return_value=CTX),
            patch.object(client, '_resolve_timeout', return_value=5.0),
            patch.object(client, '_use_session', return_value=(session, False)),
        ):
            res = client._query_code_actions(pyfile, Path(pyfile).as_uri(), SRC, 0, 0)
        assert not res.available

    def test_query_code_actions_session_error_result(self, pyfile):
        client = lc.LspClient()
        session = MagicMock()
        session.supports.return_value = True
        session.wait_publish_diagnostics.return_value = []
        session.request.return_value = {'error': {'message': 'denied'}}
        with (
            patch.object(client, '_get_context', return_value=CTX),
            patch.object(client, '_resolve_timeout', return_value=5.0),
            patch.object(client, '_use_session', return_value=(session, False)),
        ):
            res = client._query_code_actions(pyfile, Path(pyfile).as_uri(), SRC, 0, 0)
        assert not res.available
        assert 'denied' in res.error

    def test_query_code_actions_no_fallback(self, pyfile):
        client = lc.LspClient()
        with (
            patch.object(client, '_get_context', return_value=CTX),
            patch.object(client, '_resolve_timeout', return_value=5.0),
            patch.object(client, '_use_session', return_value=(None, False)),
        ):
            res = client._query_code_actions(pyfile, Path(pyfile).as_uri(), SRC, 0, 0)
        assert not res.available

    def test_query_code_actions_ctx_none(self):
        client = lc.LspClient()
        with (
            patch.object(client, '_get_context', return_value=None),
            patch.object(
                client,
                '_unavailable',
                return_value=lc.LspResult(
                    available=False, error='No language server available'
                ),
            ),
        ):
            res = client._query_code_actions('/x.py', URI, SRC, 0, 0)
        assert not res.available

    def test_execute_code_action_not_started(self):
        client = lc.LspClient()
        with (
            patch.object(client, '_rpc', return_value=([], False, 'crashed')),
            patch.object(client, '_build_init_msgs', return_value=[]),
        ):
            res = client._execute_code_action_request(
                ['pyright'], URI, '/app/main.py', SRC, {}, [], process_timeout=5.0
            )
        assert not res.available
        assert 'crashed' in res.error

    def test_query_symbols_session_path(self, pyfile):
        client = lc.LspClient()
        session = MagicMock()
        session.supports.return_value = True
        session.request.return_value = {'result': [{'name': 'main', 'kind': 12}]}
        with (
            patch.object(client, '_get_context', return_value=CTX),
            patch.object(client, '_resolve_timeout', return_value=5.0),
            patch.object(client, '_use_session', return_value=(session, False)),
        ):
            res = client._query_document_symbols(pyfile, Path(pyfile).as_uri(), SRC, '')
        assert res.available
        assert res.symbols[0].name == 'main'

    def test_query_symbols_session_unsupported(self, pyfile):
        client = lc.LspClient()
        session = MagicMock()
        session.supports.return_value = False
        with (
            patch.object(client, '_get_context', return_value=CTX),
            patch.object(client, '_resolve_timeout', return_value=5.0),
            patch.object(client, '_use_session', return_value=(session, False)),
        ):
            res = client._query_document_symbols(pyfile, Path(pyfile).as_uri(), SRC, '')
        assert not res.available

    def test_query_symbols_session_none_and_error(self, pyfile):
        client = lc.LspClient()
        session = MagicMock()
        session.supports.return_value = True
        session.request.return_value = None
        with (
            patch.object(client, '_get_context', return_value=CTX),
            patch.object(client, '_resolve_timeout', return_value=5.0),
            patch.object(client, '_use_session', return_value=(session, False)),
        ):
            assert not client._query_document_symbols(
                pyfile, Path(pyfile).as_uri(), SRC, ''
            ).available
        session.request.return_value = {'error': {'code': -1, 'message': 'nope'}}
        with (
            patch.object(client, '_get_context', return_value=CTX),
            patch.object(client, '_resolve_timeout', return_value=5.0),
            patch.object(client, '_use_session', return_value=(session, False)),
        ):
            res = client._query_document_symbols(pyfile, Path(pyfile).as_uri(), SRC, '')
        assert 'nope' in res.error

    def test_query_symbols_no_fallback(self, pyfile):
        client = lc.LspClient()
        with (
            patch.object(client, '_get_context', return_value=CTX),
            patch.object(client, '_resolve_timeout', return_value=5.0),
            patch.object(client, '_use_session', return_value=(None, False)),
        ):
            res = client._query_document_symbols(pyfile, Path(pyfile).as_uri(), SRC, '')
        assert not res.available

    def test_query_symbols_ctx_none(self):
        client = lc.LspClient()
        with (
            patch.object(client, '_get_context', return_value=None),
            patch.object(
                client,
                '_unavailable',
                return_value=lc.LspResult(
                    available=False, error='No language server available'
                ),
            ),
        ):
            assert not client._query_document_symbols('/x.py', URI, SRC, '').available

    def test_query_symbols_oneshot_error_and_no_match(self, pyfile):
        client = lc.LspClient()
        with (
            patch.object(client, '_get_context', return_value=CTX),
            patch.object(client, '_resolve_timeout', return_value=5.0),
            patch.object(client, '_use_session', return_value=(None, True)),
            patch.object(
                client,
                '_rpc',
                return_value=(
                    [{'jsonrpc': '2.0', 'id': 20, 'error': {'message': 'bad'}}],
                    True,
                    '',
                ),
            ),
        ):
            res = client._query_document_symbols(pyfile, Path(pyfile).as_uri(), SRC, '')
        assert 'bad' in res.error
        with (
            patch.object(client, '_get_context', return_value=CTX),
            patch.object(client, '_resolve_timeout', return_value=5.0),
            patch.object(client, '_use_session', return_value=(None, True)),
            patch.object(client, '_rpc', return_value=([{'id': 99}], True, '')),
        ):
            res = client._query_document_symbols(pyfile, Path(pyfile).as_uri(), SRC, '')
        assert res.available and res.symbols == []

    def test_parse_document_symbols_skips_non_dict(self):
        client = lc.LspClient()
        symbols = client._parse_document_symbols(
            ['nope', {'name': 'f', 'kind': 12}], ''
        )
        assert [s.name for s in symbols] == ['f']

    def test_query_hover_session_path(self, pyfile):
        client = lc.LspClient()
        session = MagicMock()
        session.supports.return_value = True
        session.request.return_value = {'result': {'contents': {'value': 'doc'}}}
        with (
            patch.object(client, '_get_context', return_value=CTX),
            patch.object(client, '_resolve_timeout', return_value=5.0),
            patch.object(client, '_use_session', return_value=(session, False)),
        ):
            res = client._query_hover(pyfile, Path(pyfile).as_uri(), SRC, 0, 0)
        assert res.hover_text == 'doc'

    def test_query_hover_session_unsupported(self, pyfile):
        client = lc.LspClient()
        session = MagicMock()
        session.supports.return_value = False
        with (
            patch.object(client, '_get_context', return_value=CTX),
            patch.object(client, '_resolve_timeout', return_value=5.0),
            patch.object(client, '_use_session', return_value=(session, False)),
        ):
            res = client._query_hover(pyfile, Path(pyfile).as_uri(), SRC, 0, 0)
        assert not res.available

    def test_query_hover_session_none_and_error(self, pyfile):
        client = lc.LspClient()
        session = MagicMock()
        session.supports.return_value = True
        session.request.return_value = None
        with (
            patch.object(client, '_get_context', return_value=CTX),
            patch.object(client, '_resolve_timeout', return_value=5.0),
            patch.object(client, '_use_session', return_value=(session, False)),
        ):
            assert not client._query_hover(
                pyfile, Path(pyfile).as_uri(), SRC, 0, 0
            ).available
        session.request.return_value = {'error': {'code': -1, 'message': 'nope'}}
        with (
            patch.object(client, '_get_context', return_value=CTX),
            patch.object(client, '_resolve_timeout', return_value=5.0),
            patch.object(client, '_use_session', return_value=(session, False)),
        ):
            res = client._query_hover(pyfile, Path(pyfile).as_uri(), SRC, 0, 0)
        assert 'nope' in res.error

    def test_query_hover_no_fallback(self, pyfile):
        client = lc.LspClient()
        with (
            patch.object(client, '_get_context', return_value=CTX),
            patch.object(client, '_resolve_timeout', return_value=5.0),
            patch.object(client, '_use_session', return_value=(None, False)),
        ):
            assert not client._query_hover(
                pyfile, Path(pyfile).as_uri(), SRC, 0, 0
            ).available

    def test_query_hover_ctx_none(self):
        client = lc.LspClient()
        with (
            patch.object(client, '_get_context', return_value=None),
            patch.object(
                client,
                '_unavailable',
                return_value=lc.LspResult(
                    available=False, error='No language server available'
                ),
            ),
        ):
            assert not client._query_hover('/x.py', URI, SRC, 0, 0).available

    def test_query_hover_oneshot_not_started_and_no_match(self, pyfile):
        client = lc.LspClient()
        with (
            patch.object(client, '_get_context', return_value=CTX),
            patch.object(client, '_resolve_timeout', return_value=5.0),
            patch.object(client, '_use_session', return_value=(None, True)),
            patch.object(client, '_rpc', return_value=([], False, 'crashed')),
        ):
            res = client._query_hover(pyfile, Path(pyfile).as_uri(), SRC, 0, 0)
        assert not res.available
        with (
            patch.object(client, '_get_context', return_value=CTX),
            patch.object(client, '_resolve_timeout', return_value=5.0),
            patch.object(client, '_use_session', return_value=(None, True)),
            patch.object(client, '_rpc', return_value=([{'id': 99}], True, '')),
        ):
            res = client._query_hover(pyfile, Path(pyfile).as_uri(), SRC, 0, 0)
        assert res.hover_text == 'No hover info'

    def test_query_locations_session_path(self, pyfile):
        client = lc.LspClient()
        session = MagicMock()
        session.supports.return_value = True
        session.request.return_value = {
            'result': [{'uri': 'file:///app/t.py', 'range': {'start': {'line': 0}}}]
        }
        with (
            patch.object(client, '_get_context', return_value=CTX),
            patch.object(client, '_resolve_timeout', return_value=5.0),
            patch.object(client, '_use_session', return_value=(session, False)),
        ):
            res = client._query_locations(
                'find_definition', pyfile, Path(pyfile).as_uri(), SRC, 0, 0
            )
        assert res.locations[0].line == 1
        session.request.assert_called_once()
        method = session.request.call_args.args[0]
        assert method == 'textDocument/definition'

    def test_query_locations_session_references_context(self, pyfile):
        client = lc.LspClient()
        session = MagicMock()
        session.supports.return_value = True
        session.request.return_value = {'result': []}
        with (
            patch.object(client, '_get_context', return_value=CTX),
            patch.object(client, '_resolve_timeout', return_value=5.0),
            patch.object(client, '_use_session', return_value=(session, False)),
        ):
            res = client._query_locations(
                'find_references', pyfile, Path(pyfile).as_uri(), SRC, 0, 0
            )
        assert res.available
        params = session.request.call_args.args[1]
        assert params['context'] == {'includeDeclaration': True}

    def test_query_locations_session_unsupported(self, pyfile):
        client = lc.LspClient()
        session = MagicMock()
        session.supports.return_value = False
        with (
            patch.object(client, '_get_context', return_value=CTX),
            patch.object(client, '_resolve_timeout', return_value=5.0),
            patch.object(client, '_use_session', return_value=(session, False)),
        ):
            res = client._query_locations(
                'find_definition', pyfile, Path(pyfile).as_uri(), SRC, 0, 0
            )
        assert not res.available

    def test_query_locations_session_none_and_error(self, pyfile):
        client = lc.LspClient()
        session = MagicMock()
        session.supports.return_value = True
        session.request.return_value = None
        with (
            patch.object(client, '_get_context', return_value=CTX),
            patch.object(client, '_resolve_timeout', return_value=5.0),
            patch.object(client, '_use_session', return_value=(session, False)),
        ):
            assert not client._query_locations(
                'find_definition', pyfile, Path(pyfile).as_uri(), SRC, 0, 0
            ).available
        session.request.return_value = {'error': {'message': 'boom'}}
        with (
            patch.object(client, '_get_context', return_value=CTX),
            patch.object(client, '_resolve_timeout', return_value=5.0),
            patch.object(client, '_use_session', return_value=(session, False)),
        ):
            res = client._query_locations(
                'find_definition', pyfile, Path(pyfile).as_uri(), SRC, 0, 0
            )
        assert 'boom' in res.error

    def test_query_locations_no_fallback(self, pyfile):
        client = lc.LspClient()
        with (
            patch.object(client, '_get_context', return_value=CTX),
            patch.object(client, '_resolve_timeout', return_value=5.0),
            patch.object(client, '_use_session', return_value=(None, False)),
        ):
            assert not client._query_locations(
                'find_definition', pyfile, Path(pyfile).as_uri(), SRC, 0, 0
            ).available

    def test_query_locations_ctx_none(self):
        client = lc.LspClient()
        with (
            patch.object(client, '_get_context', return_value=None),
            patch.object(
                client,
                '_unavailable',
                return_value=lc.LspResult(
                    available=False, error='No language server available'
                ),
            ),
        ):
            assert not client._query_locations(
                'find_definition', '/x.py', URI, SRC, 0, 0
            ).available

    def test_try_lsp_locations_error_and_no_match(self):
        client = lc.LspClient()
        with (
            patch.object(
                client,
                '_rpc',
                return_value=(
                    [{'jsonrpc': '2.0', 'id': 10, 'error': {'message': 'bad'}}],
                    True,
                    '',
                ),
            ),
            patch.object(client, '_build_init_msgs', return_value=[]),
        ):
            res, started = client._try_lsp_locations(
                ['pyright'], 'find_definition', URI, '/app/main.py', SRC, 0, 0
            )
        assert started is True
        assert 'bad' in res.error
        with (
            patch.object(client, '_rpc', return_value=([{'id': 99}], True, '')),
            patch.object(client, '_build_init_msgs', return_value=[]),
        ):
            res, started = client._try_lsp_locations(
                ['pyright'], 'find_definition', URI, '/app/main.py', SRC, 0, 0
            )
        assert started is True
        assert res.available

    def test_try_lsp_locations_not_started(self):
        client = lc.LspClient()
        with (
            patch.object(client, '_rpc', return_value=([], False, 'crashed')),
            patch.object(client, '_build_init_msgs', return_value=[]),
        ):
            res, started = client._try_lsp_locations(
                ['pyright'], 'find_definition', URI, '/app/main.py', SRC, 0, 0
            )
        assert started is False
        assert 'crashed' in res.error
