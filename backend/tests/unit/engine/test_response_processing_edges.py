"""Edge-path tests for backend.engine.response_processing.

Exercises the retry guard, thinking-tag handling, tool-call argument parsing,
XML transport parsing, and message/action building paths not covered by the
existing suite.
"""

from __future__ import annotations

import json
import logging
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest

from backend.engine import response_processing as rp
from backend.ledger.action.message import MessageAction

_APP_LOGGER = logging.getLogger('app')
_MOD_LOGGER = logging.getLogger('backend.engine.response_processing')


@pytest.fixture(autouse=True)
def _clear_retry_guard():
    rp._RETRY_GUARD.clear()
    yield
    rp._RETRY_GUARD.clear()


def _tool_call(name: str, arguments: str = '{}', call_id: str = 'call_1') -> Any:
    return SimpleNamespace(
        id=call_id,
        function=SimpleNamespace(name=name, arguments=arguments),
    )


def _message(tool_calls: list | None = None, content: str = '', **kw: Any) -> Any:
    return SimpleNamespace(
        tool_calls=tool_calls,
        content=content,
        reasoning_content=kw.get('reasoning_content'),
    )


def _response(tool_calls: list | None = None, content: str = '', **kw: Any) -> Any:
    msg = _message(tool_calls, content, **kw)
    return SimpleNamespace(id='resp-1', choices=[SimpleNamespace(message=msg)])


# ── retry guard ──────────────────────────────────────────────────────


class TestRetryGuard:
    def test_new_key_allowed(self):
        allowed, reason = rp._check_format_error_retry_guard('tool_a', 'x', 'sig')
        assert allowed is True and reason == ''

    def test_same_hash_increments_then_blocks(self):
        rp._check_format_error_retry_guard('tool_a', 'x', 'sig')
        rp._check_format_error_retry_guard('tool_a', 'x', 'sig')
        allowed, reason = rp._check_format_error_retry_guard('tool_a', 'x', 'sig')
        assert allowed is False
        assert 'Retry guard triggered' in reason

    def test_different_content_resets_attempts(self):
        rp._check_format_error_retry_guard('tool_a', 'x', 'sig')
        rp._check_format_error_retry_guard('tool_a', 'x', 'sig')
        allowed, _ = rp._check_format_error_retry_guard('tool_a', 'different', 'sig')
        assert allowed is True
        rp._check_format_error_retry_guard('tool_a', 'different', 'sig')
        allowed, _ = rp._check_format_error_retry_guard('tool_a', 'different', 'sig')
        assert allowed is False

    def test_overflow_clears_guard(self):
        for i in range(1001):
            rp._check_format_error_retry_guard(f'tool_{i}', 'x', 'sig')
        assert len(rp._RETRY_GUARD) == 1001
        rp._check_format_error_retry_guard('overflow_probe', 'x', 'sig')
        assert len(rp._RETRY_GUARD) == 1  # cleared on the call that exceeds the cap


# ── thinking tags ────────────────────────────────────────────────────


class TestThinkingTags:
    def test_extract_inner_multiple_blocks(self):
        text = 'a <redacted_thinking> one </redacted_thinking> b <think> two </think>'
        assert rp.extract_redacted_thinking_inner(text) == 'one\n\ntwo'

    def test_extract_inner_ignores_empty_blocks(self):
        assert rp.extract_redacted_thinking_inner('<redacted_thinking>  </redacted_thinking>') == ''

    def test_strip_tags_collapses_newlines(self):
        text = 'a\n\n\n\n<redacted_thinking>x</redacted_thinking>\n\n\n\nb\n'
        assert rp.strip_thinking_tags(text) == 'a\n\nb'


# ── error classes and extraction helpers ─────────────────────────────


class TestErrorsAndExtraction:
    def test_function_call_not_exists_error(self):
        err = rp.FunctionCallNotExistsError('nope', per_action=True)
        assert err.per_action is True

    def test_extract_assistant_message_no_choices(self):
        with pytest.raises(rp.FunctionCallValidationError, match='no choices'):
            rp.extract_assistant_message(SimpleNamespace(choices=[]))

    def test_set_response_id_requires_actions(self):
        with pytest.raises(rp.FunctionCallValidationError):
            rp.set_response_id_for_actions([], SimpleNamespace(id='r'))

    def test_set_response_id_applies(self):
        a1, a2 = MagicMock(), MagicMock()
        rp.set_response_id_for_actions([a1, a2], SimpleNamespace(id='r-9'))
        assert a1.response_id == 'r-9' and a2.response_id == 'r-9'

    def test_parse_tool_call_arguments_dict_passthrough(self):
        assert rp.parse_tool_call_arguments(_tool_call('t', '{}')) == {}
        tc = SimpleNamespace(function=SimpleNamespace(arguments={'a': 1}))
        assert rp.parse_tool_call_arguments(tc) == {'a': 1}

    def test_parse_tool_call_arguments_wrong_type(self):
        tc = SimpleNamespace(function=SimpleNamespace(arguments=123))
        with pytest.raises(rp.FunctionCallValidationError, match='JSON string or dict'):
            rp.parse_tool_call_arguments(tc)

    def test_parse_tool_call_arguments_long_preview_truncated(self):
        tc = SimpleNamespace(
            function=SimpleNamespace(arguments='{"a": "' + 'x' * 500 + '}')
        )
        with patch.object(
            rp, 'parse_tool_arguments_object', side_effect=ValueError('bad json')
        ):
            with pytest.raises(rp.FunctionCallValidationError) as exc:
                rp.parse_tool_call_arguments(tc)
        assert '...' in str(exc.value)

    def test_parse_tool_call_arguments_truncated_error_propagates(self):
        from backend.core.tools.tool_arguments_json import TruncatedToolArgumentsError

        tc = SimpleNamespace(
            function=SimpleNamespace(arguments='{"a": "unclosed')
        )
        with pytest.raises(TruncatedToolArgumentsError):
            rp.parse_tool_call_arguments(tc)

    def test_build_tool_call_metadata(self):
        md = rp.build_tool_call_metadata(
            function_name='grep', tool_call_id='c1', response_obj=_response([], 'ok'),
            total_calls_in_response=1,
        )
        assert md.function_name == 'grep'
        assert md.tool_call_id == 'c1'


# ── arguments_from_tool_call_metadata ────────────────────────────────


class TestArgumentsFromToolCallMetadata:
    def test_none_metadata(self):
        assert rp.arguments_from_tool_call_metadata(None) == {}

    def test_no_model_response(self):
        assert rp.arguments_from_tool_call_metadata(
            SimpleNamespace(tool_call_id='c1', model_response=None)
        ) == {}

    def test_no_choices(self):
        assert rp.arguments_from_tool_call_metadata(
            SimpleNamespace(tool_call_id='c1', model_response=SimpleNamespace(choices=None))
        ) == {}

    def test_choices_via_dict(self):
        md = SimpleNamespace(tool_call_id='c1', model_response={'choices': []})
        assert rp.arguments_from_tool_call_metadata(md) == {}

    def test_message_without_tool_calls(self):
        resp = {'choices': [{'message': None}]}
        md = SimpleNamespace(tool_call_id='c1', model_response=resp)
        assert rp.arguments_from_tool_call_metadata(md) == {}

    def test_message_missing(self):
        resp = {'choices': [{'message': None}]}
        md = SimpleNamespace(tool_call_id='c1', model_response=resp)
        assert rp.arguments_from_tool_call_metadata(md) == {}

    def test_tool_calls_with_matching_id(self):
        resp = {
            'choices': [
                {'message': {'tool_calls': [
                    {'id': 'c2', 'function': {'name': 'grep', 'arguments': '{"p": "x"}'}},
                ]}}
            ]
        }
        md = SimpleNamespace(tool_call_id='c1', model_response=resp)
        assert rp.arguments_from_tool_call_metadata(md) == {}

    def test_tool_calls_object_with_matching_id(self):
        tc = SimpleNamespace(id='c1', function={'name': 'grep', 'arguments': '{"p": "x"}'})
        resp = SimpleNamespace(choices=[SimpleNamespace(message=SimpleNamespace(tool_calls=[tc]))])
        md = SimpleNamespace(tool_call_id='c1', model_response=resp)
        assert rp.arguments_from_tool_call_metadata(md) == {'p': 'x'}

    def test_non_dict_function_skipped(self):
        tc = SimpleNamespace(id='c1', function='not-a-dict')
        resp = SimpleNamespace(choices=[SimpleNamespace(message=SimpleNamespace(tool_calls=[tc]))])
        md = SimpleNamespace(tool_call_id='c1', model_response=resp)
        assert rp.arguments_from_tool_call_metadata(md) == {}

    def test_parse_error_returns_empty(self):
        tc = SimpleNamespace(id='c1', function={'name': 'grep', 'arguments': '[1, 2]'})
        resp = SimpleNamespace(choices=[SimpleNamespace(message=SimpleNamespace(tool_calls=[tc]))])
        md = SimpleNamespace(tool_call_id='c1', model_response=resp)
        assert rp.arguments_from_tool_call_metadata(md) == {}


# ── content coercion ─────────────────────────────────────────────────


class TestContentCoercion:
    def test_extract_thought_from_reasoning_content(self):
        msg = _message(reasoning_content='  deep thought  ')
        assert rp.extract_thought_from_message(msg) == 'deep thought'

    def test_extract_thought_from_inner_tags(self):
        msg = _message(content='<redacted_thinking>think 1</redacted_thinking>')
        assert rp.extract_thought_from_message(msg) == 'think 1'

    def test_message_content_text_part_non_dict(self):
        assert rp._message_content_text_part(123) == ''

    def test_raw_content_text_dict_and_list(self):
        assert rp._raw_message_content_text({'text': 'hi'}) == 'hi'
        assert rp._raw_message_content_text([{'text': 'a'}, 'b', {'no': 1}]) == 'ab'
        assert rp._raw_message_content_text(None) == ''
        assert rp._raw_message_content_text(42) == ''

    def test_coerce_strips_thinking_tags(self):
        assert rp._coerce_message_content_text(
            '<redacted_thinking>t</redacted_thinking> body'
        ) == 'body'

    def test_coerce_visible_redacts_markers(self):
        with patch(
            'backend.cli.display.tool_call_display.redact_streamed_tool_call_markers',
            return_value='REDACTED',
        ):
            assert rp._coerce_visible_message_content_text('x') == 'REDACTED'

    def test_coerce_visible_empty(self):
        assert rp._coerce_visible_message_content_text('  ') == ''


# ── canonicalization ─────────────────────────────────────────────────


class TestCanonicalizeToolCallArguments:
    def test_non_serializable_arguments_skipped(self):
        tc = _tool_call('t', '{}')
        rp._canonicalize_tool_call_arguments(tc, {'bad': object()})
        assert tc.function.arguments == '{}'

    def test_no_function_attr_noop(self):
        rp._canonicalize_tool_call_arguments(SimpleNamespace(), {'a': 1})

    def test_immutable_function_logs_and_keeps(self):
        class Frozen:
            def __setattr__(self, name, value):
                raise AttributeError('frozen')

        tc = SimpleNamespace(function=Frozen())
        with patch.object(_APP_LOGGER, 'debug') as dbg:
            rp._canonicalize_tool_call_arguments(tc, {'a': 1})
        assert any('immutable' in str(c.args) for c in dbg.call_args_list)

    def test_success_replaces_arguments(self):
        tc = _tool_call('t', '{broken json')
        rp._canonicalize_tool_call_arguments(tc, {'a': 1, 'b': 'ü'})
        assert json.loads(tc.function.arguments) == {'a': 1, 'b': 'ü'}


# ── process_tool_calls ───────────────────────────────────────────────


class TestProcessToolCalls:
    def test_full_pipeline_with_thought_attach(self):
        calls = [
            _tool_call('edit_file', '{"p": "a.py"}', 'c1'),
            _tool_call('grep', '{"p": "x"}', 'c2'),
        ]
        msg = _message(calls, content='', reasoning_content='think')
        created: list = []
        combined: list = []

        def create(tc, args):
            a = MagicMock()
            created.append(a)
            return a

        def combine(action, thought):
            combined.append((action, thought))
            return action

        actions = rp.process_tool_calls(
            msg, _response(), create, rp.extract_thought_from_message, combine
        )
        assert len(actions) == 2
        assert len(combined) == 1  # thought attached to first tool call only
        assert actions[0].tool_call_metadata.tool_call_id == 'c1'

    def test_discovery_tools_skip_thought_attach(self):
        call = _tool_call('grep', '{}', 'c1')
        msg = _message([call], content='', reasoning_content='think')
        combined: list = []

        def combine(action, thought):
            combined.append(thought)
            return action

        rp.process_tool_calls(
            msg, _response(), lambda tc, args: MagicMock(), rp.extract_thought_from_message,
            combine,
        )
        assert combined == []

    def test_log_emitted_tool_action_exception_path(self):
        call = _tool_call('edit_file', '{}', 'c1')
        msg = _message([call])
        with patch.object(_APP_LOGGER, 'info', side_effect=RuntimeError('log boom')):
            actions = rp.process_tool_calls(
                msg, _response(), lambda tc, args: MagicMock(),
                rp.extract_thought_from_message, lambda a, t: a,
            )
        assert len(actions) == 1


# ── compact logging ──────────────────────────────────────────────────


class TestCompactToolArgs:
    def test_long_args_truncated(self):
        out = rp._compact_tool_args_for_log({'a': 'x' * 600})
        assert out.endswith('...') and len(out) <= 500

    def test_non_serializable_falls_back_to_str(self):
        out = rp._compact_tool_args_for_log({'a': object()})
        assert 'object' in out

    def test_newlines_collapsed(self):
        out = rp._compact_tool_args_for_log({'a': 'x\ny'})
        assert '\n' not in out


# ── common_response_to_actions ───────────────────────────────────────


class TestCommonResponseToActions:
    def test_message_only_action(self):
        actions = rp.common_response_to_actions(
            _response(content='hello there'),
            lambda tc, args: None,
            lambda a, t: a,
        )
        assert len(actions) == 1
        assert isinstance(actions[0], MessageAction)
        assert actions[0].content == 'hello there'
        assert actions[0].final_response is True

    def test_empty_content_and_no_calls(self):
        actions = rp.common_response_to_actions(
            _response(content=''),
            lambda tc, args: None,
            lambda a, t: a,
        )
        assert len(actions) == 1
        assert isinstance(actions[0], MessageAction)
        assert actions[0].content == ''

    def test_native_tool_calls_only(self):
        calls = [_tool_call('edit_file', '{"p": "a.py", "new_string": "b"}', 'c1')]
        created = []

        def create(tc, args):
            created.append(args)
            return MagicMock()

        actions = rp.common_response_to_actions(
            _response(calls, content=''),
            create,
            lambda a, t: a,
        )
        assert len(actions) == 1  # empty content -> no transcript message
        assert created == [{'p': 'a.py', 'new_string': 'b'}]

    def test_native_tool_calls_with_text(self):
        calls = [_tool_call('edit_file', '{"p": "a.py"}', 'c1')]
        actions = rp.common_response_to_actions(
            _response(calls, content='Editing now.'),
            lambda tc, args: MagicMock(),
            lambda a, t: a,
        )
        assert len(actions) == 2  # transcript message + tool action
        assert actions[0].transcript_only is True

    def test_xml_tool_calls_only(self):
        content = (
            'Let me edit.<function=edit_file>'
            '<parameter=path>/tmp/a.py</parameter>'
            '<parameter=new_string>hello</parameter>'
            '</function>'
        )
        created: list = []

        def create(tc, args):
            created.append((tc, args))
            return MagicMock()

        actions = rp.common_response_to_actions(
            _response(content=content),
            create,
            lambda a, t: a,
            xml_tool_names=frozenset({'edit_file'}),
        )
        assert len(created) == 1
        _, args = created[0]
        assert args == {'path': '/tmp/a.py', 'new_string': 'hello'}

    def test_text_marker_tool_calls(self):
        content = 'Let me search.\n[Tool call] grep({"pattern": "x"})\nDone.'
        created: list = []

        def create(tc, args):
            created.append((tc, args))
            return MagicMock()

        actions = rp.common_response_to_actions(
            _response(content=content),
            create,
            lambda a, t: a,
        )
        assert len(created) == 1
        assert created[0][1] == {'pattern': 'x'}

    def test_xml_supersedes_native(self):
        content = (
            '<function=edit_file>'
            '<parameter=path>/tmp/a.py</parameter>'
            '</function>'
        )
        native = [_tool_call('edit_file', '{"path": "/tmp/a.py"}', 'n1')]
        created: list = []

        def create(tc, args):
            created.append(args)
            return MagicMock()

        actions = rp.common_response_to_actions(
            _response(native, content),
            create,
            lambda a, t: a,
            xml_tool_names=frozenset({'edit_file'}),
        )
        assert len(created) == 1  # native dropped, only XML processed
        assert created[0] == {'path': '/tmp/a.py'}

    def test_xml_compliance_rejects_native(self):
        native = [_tool_call('edit_file', '{"path": "/tmp/a.py"}', 'n1')]
        with pytest.raises(rp.CoreFunctionCallValidationError, match='FORMAT_ERROR'):
            rp.common_response_to_actions(
                _response(native, content=''),
                lambda tc, args: None,
                lambda a, t: a,
                xml_tool_names=frozenset({'edit_file'}),
            )

    def test_parse_xml_tool_calls_without_names(self):
        assert rp._parse_xml_tool_calls('<function=edit_file>x</function>', None) == []

    def test_deduplicate_noop_combos(self):
        native = [_tool_call('grep')]
        assert rp._deduplicate_xml_native_calls(native, [], None) == native
        assert rp._deduplicate_xml_native_calls([], [_tool_call('grep')], frozenset({'grep'})) == []

    def test_enforce_xml_compliance_if_needed_skips_without_native(self):
        rp._enforce_xml_compliance_if_needed([], frozenset({'edit_file'}))  # no-op

    def test_build_message_actions_with_cot(self):
        content = '<redacted_thinking>cot</redacted_thinking> visible'
        actions = rp._build_message_actions(content, [])
        assert actions[0].thought == 'cot'
        assert actions[0].content == 'visible'

    def test_build_message_actions_empty_text(self):
        assert rp._build_message_actions('   ', []) == []

    def test_build_tool_actions_sets_mcp_names(self):
        calls = [_tool_call('grep', '{}', 'c1')]
        msg = _message(calls)
        actions = rp._build_tool_actions(
            msg, _response(), calls, lambda tc, args: MagicMock(),
            lambda a, t: a, ['mcp_grep'],
        )
        assert len(actions) == 1
        assert calls[0]._mcp_tool_names == ['mcp_grep']

    def test_empty_message_action(self):
        action = rp._empty_message_action()
        assert isinstance(action, MessageAction) and action.content == ''

    def test_tool_call_function_name_missing(self):
        assert rp._tool_call_function_name(SimpleNamespace(function=None)) == ''


# ── XML parsing helpers ──────────────────────────────────────────────


class TestXmlParsing:
    def test_xml_tools_successfully_parsed(self):
        calls = [
            _tool_call('edit_file', '{"a": 1}'),
            _tool_call('bad', '{not json'),
            _tool_call('syn', '{"__xml_syntax_error__": "x"}'),
            _tool_call('', '{}'),
            _tool_call('ok2', '{}'),
        ]
        assert rp._xml_tools_successfully_parsed(calls) == {'edit_file', 'ok2'}

    def test_filter_native_superseded(self):
        native = [_tool_call('grep'), _tool_call('edit_file'), _tool_call('keep')]
        xml = [_tool_call('edit_file', '{}')]
        filtered = rp._filter_native_tool_calls_superseded_by_xml(
            native, xml, frozenset({'edit_file'})
        )
        assert [c.function.name for c in filtered] == ['grep', 'keep']

    def test_filter_native_none_superseded(self):
        native = [_tool_call('grep')]
        xml = [_tool_call('edit_file', '{}')]
        assert rp._filter_native_tool_calls_superseded_by_xml(
            native, xml, frozenset({'edit_file'})
        ) == native

    def test_text_marker_extraction_early_return(self):
        assert rp._extract_text_marker_tool_calls_from_content('') == []
        assert rp._extract_text_marker_tool_calls_from_content('no markers here') == []

    def test_text_marker_extraction_skips_unnamed(self):
        with patch(
            'backend.cli.display.tool_call_display.extract_tool_calls_from_text_markers',
            return_value=[{'id': 'm1', 'function': {}}],
        ):
            assert rp._extract_text_marker_tool_calls_from_content(
                '[tool_call] name: grep'
            ) == []

    def test_enforce_xml_compliance_non_matching_name(self):
        rp._enforce_xml_compliance([_tool_call('grep', '{}')], frozenset({'edit_file'}))
        # no exception raised

    def test_enforce_xml_compliance_raises(self):
        with pytest.raises(rp.CoreFunctionCallValidationError, match='FORMAT_ERROR'):
            rp._enforce_xml_compliance(
                [_tool_call('edit_file', '{"p": "a.py"}')], frozenset({'edit_file'})
            )

    def test_enforce_xml_compliance_retry_guard_blocks(self):
        tc = _tool_call('edit_file', '{"p": "a.py"}')
        with pytest.raises(rp.CoreFunctionCallValidationError, match='FORMAT_ERROR'):
            rp._enforce_xml_compliance([tc], frozenset({'edit_file'}))
        with pytest.raises(rp.CoreFunctionCallValidationError, match='FORMAT_ERROR'):
            rp._enforce_xml_compliance([tc], frozenset({'edit_file'}))
        with pytest.raises(rp.CoreFunctionCallValidationError, match='Retry guard'):
            rp._enforce_xml_compliance([tc], frozenset({'edit_file'}))

    def test_synthetic_function(self):
        fn = rp._SyntheticFunction('grep', '{}')
        assert fn.name == 'grep' and fn.arguments == '{}'

    def test_synthetic_tool_call(self):
        tc = rp._SyntheticToolCall('id-1', 'grep', '{}')
        assert tc.id == 'id-1' and tc.type == 'function'
        assert tc.function.name == 'grep'
        assert tc._mcp_tool_names is None

    def test_strip_param_newlines(self):
        assert rp._strip_param_newlines('\nvalue\n') == 'value'
        assert rp._strip_param_newlines('plain') == 'plain'

    def test_build_params_from_matches(self):
        m1 = SimpleNamespace(group=lambda i: 'path' if i == 1 else '/tmp/a.py')
        m2 = SimpleNamespace(group=lambda i: 'content' if i == 1 else '\nx\n')
        assert rp._build_params_from_matches([m1, m2]) == {
            'path': '/tmp/a.py',
            'content': 'x',
        }

    def test_annotate_xml_syntax_errors_unclosed(self):
        params = {}
        rp._annotate_xml_syntax_errors(params, 'body', is_unclosed=True)
        assert '__xml_syntax_error__' in params

    def test_annotate_xml_syntax_errors_no_params(self):
        params = {}
        rp._annotate_xml_syntax_errors(params, '  body  ', is_unclosed=False)
        assert 'No <parameter' in params['__xml_syntax_error__']

    def test_annotate_xml_syntax_errors_with_params(self):
        params = {'path': '/x'}
        rp._annotate_xml_syntax_errors(params, 'body', is_unclosed=False)
        assert '__xml_syntax_error__' not in params

    def test_apply_xml_retry_guard_no_error(self):
        params = {'path': '/x'}
        assert rp._apply_xml_retry_guard(params, 'edit_file') == params

    def test_apply_xml_retry_guard_allowed_then_blocked(self):
        params = {'__xml_syntax_error__': 'Unclosed <function> tag.'}
        first = rp._apply_xml_retry_guard(dict(params), 'edit_file')
        assert first == params
        rp._apply_xml_retry_guard(dict(params), 'edit_file')
        blocked = rp._apply_xml_retry_guard(dict(params), 'edit_file')
        assert 'Retry guard stopped repeated error' in blocked['__xml_syntax_error__']

    def test_extract_xml_params_exception_path(self):
        def boom(*args):
            raise ValueError('bad body')

        with patch.object(_APP_LOGGER, 'warning') as warn:
            params = rp._extract_xml_params('body', 'edit_file', False, boom)
        assert 'Malformed parameters' in params['__xml_syntax_error__']
        assert any('Failed to parse parameters' in str(c.args) for c in warn.call_args_list)

    def test_extract_xml_calls_empty(self):
        assert rp._extract_xml_tool_calls_from_content('', frozenset({'edit_file'})) == []
        assert rp._extract_xml_tool_calls_from_content(
            'no function block', frozenset({'edit_file'})
        ) == []

    def test_extract_xml_calls_unknown_tool_skipped(self):
        out = rp._extract_xml_tool_calls_from_content(
            'text <function=unknown>x</function>', frozenset({'edit_file'})
        )
        assert out == []

    def test_extract_xml_calls_duplicate_tool(self):
        content = (
            '<function=edit_file><parameter=path>a</parameter></function>'
            '<function=edit_file><parameter=path>b</parameter></function>'
        )
        with patch.object(_APP_LOGGER, 'warning') as warn:
            out = rp._extract_xml_tool_calls_from_content(
                content, frozenset({'edit_file'})
            )
        assert len(out) == 1
        assert any('Multiple <function=' in str(c.args) for c in warn.call_args_list)

    def test_extract_xml_calls_unclosed(self):
        content = '<function=edit_file><parameter=path>a</parameter>'
        with patch.object(_APP_LOGGER, 'warning') as warn:
            out = rp._extract_xml_tool_calls_from_content(
                content, frozenset({'edit_file'})
            )
        assert len(out) == 1
        assert 'Unclosed' in str(warn.call_args_list[0].args[0])

    def test_extract_xml_calls_valid(self):
        content = (
            'Let me fix it. <function=edit_file>'
            '<parameter=path>/tmp/a.py</parameter>'
            '<parameter=new_string>hi</parameter>'
            '</function> done'
        )
        out = rp._extract_xml_tool_calls_from_content(
            content, frozenset({'edit_file'})
        )
        assert len(out) == 1
        assert out[0].id == 'xml_toolu_00'
        assert out[0].function.name == 'edit_file'
        assert json.loads(out[0].function.arguments) == {
            'path': '/tmp/a.py',
            'new_string': 'hi',
        }

    def test_create_tool_definition(self):
        tool = rp.create_tool_definition(
            name='grep',
            description='Search files',
            properties={'pattern': {'type': 'string'}},
            required=['pattern'],
            additional_properties=True,
        )
        assert tool['function']['name'] == 'grep'
        assert tool['function']['parameters']['required'] == ['pattern']
        assert tool['function']['parameters']['additionalProperties'] is True


class TestRemainingBranches:
    def test_extract_assistant_message_missing_payload(self):
        choice = SimpleNamespace(message=None)
        with pytest.raises(rp.FunctionCallValidationError, match='missing a message'):
            rp.extract_assistant_message(SimpleNamespace(choices=[choice]))

    def test_arguments_empty_tool_calls(self):
        resp = {'choices': [{'message': {'tool_calls': []}}]}
        md = SimpleNamespace(tool_call_id='c1', model_response=resp)
        assert rp.arguments_from_tool_call_metadata(md) == {}

    def test_arguments_non_dict_function_dict_style(self):
        resp = {
            'choices': [
                {'message': {'tool_calls': [
                    {'id': 'c1', 'function': 'plain-string'},
                ]}}
            ]
        }
        md = SimpleNamespace(tool_call_id='c1', model_response=resp)
        assert rp.arguments_from_tool_call_metadata(md) == {}

    def test_filter_native_superseded_empty_returns_early(self):
        native = [_tool_call('grep')]
        xml = [_tool_call('other_tool', '{}')]  # not in xml_tool_names
        assert rp._filter_native_tool_calls_superseded_by_xml(
            native, xml, frozenset({'edit_file'})
        ) == native

    def test_common_path_param_default(self):
        assert rp.get_common_path_param()['description'] == (
            'Absolute path to file or directory.'
        )

    def test_common_pattern_param(self):
        assert rp.get_common_pattern_param('A pattern') == {
            'type': 'string',
            'description': 'A pattern',
        }

    def test_common_timeout_param(self):
        assert rp.get_common_timeout_param() == {
            'type': 'number',
            'description': 'Optional timeout in seconds.',
        }