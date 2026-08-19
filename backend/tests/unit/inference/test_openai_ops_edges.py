"""Edge coverage tests for backend.inference.providers.openai_ops."""

# pylint: disable=protected-access

from __future__ import annotations

import logging
from types import SimpleNamespace
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import openai
import pytest

from backend.inference.exceptions import (
    APIConnectionError,
    APIError,
    AuthenticationError,
    BadRequestError,
    ContextWindowExceededError,
    InternalServerError,
    NotFoundError,
    RateLimitError,
    Timeout,
)
from backend.inference.providers import openai_ops as ops


class TestEnsureOpencodeChatCompletionsModelSupported:
    def test_non_opencode_provider_returns_immediately(self) -> None:
        client = MagicMock()
        client._provider_name = 'anthropic'
        ops._ensure_opencode_chat_completions_model_supported(client)


class TestExtractOpenaiHttpStatus:
    def test_recovers_status_from_response_object(self) -> None:
        exc = SimpleNamespace(
            status_code=None, response=SimpleNamespace(status_code=429)
        )
        assert ops.extract_openai_http_status(exc) == 429


class TestExtractOaiErrorMessage:
    def test_returns_none_when_no_braces(self) -> None:
        assert ops._extract_oai_error_message('plain text') is None

    def test_parses_json_error_message(self) -> None:
        raw = '{"error": {"message": "boom", "type": "invalid_request_error"}}'
        assert ops._extract_oai_error_message(raw) == 'boom'

    def test_parses_python_repr_error_message(self) -> None:
        raw = "{'error': {'message': 'invalid api key'}}"
        assert ops._extract_oai_error_message(raw) == 'invalid api key'

    def test_returns_none_when_literal_eval_fails(self) -> None:
        assert ops._extract_oai_error_message('{oops this is not valid!!}') is None

    def test_returns_none_when_body_not_a_dict(self) -> None:
        assert ops._extract_oai_error_message('{1, 2, 3}') is None

    def test_returns_none_when_error_object_has_no_message(self) -> None:
        assert ops._extract_oai_error_message('{"error": {"code": 500}}') is None

    def test_returns_string_error(self) -> None:
        assert ops._extract_oai_error_message('{"error": "denied"}') == 'denied'

    def test_returns_none_without_error_key(self) -> None:
        assert ops._extract_oai_error_message('{"ok": true}') is None


class TestSimplifyOpenaiUnauthorizedMessage:
    def test_403_fallback_reason_is_capitalized_and_period_terminated(self) -> None:
        result = ops.simplify_openai_unauthorized_message(Exception('x'), 403)
        assert result == 'Access denied.'

    def test_403_capitalizes_lowercase_extracted_message(self) -> None:
        exc = Exception('{"error": {"message": "quota exceeded"}}')
        assert ops.simplify_openai_unauthorized_message(exc, 403) == 'Quota exceeded.'

    def test_403_keeps_already_clean_extracted_message(self) -> None:
        exc = Exception('{"error": {"message": "Access denied."}}')
        assert ops.simplify_openai_unauthorized_message(exc, 403) == 'Access denied.'

    def test_unprintable_exception_falls_back_to_type_name(self) -> None:
        class Unprintable(Exception):
            def __str__(self) -> str:
                raise RuntimeError('nope')

        assert ops.simplify_openai_unauthorized_message(Unprintable(), 403) == (
            'Access denied.'
        )

    def test_non_unauthorized_pattern_returns_raw(self) -> None:
        exc = Exception('some other error text')
        assert ops.simplify_openai_unauthorized_message(exc, 401) == (
            'some other error text'
        )


class TestExtractOpenaiToolCalls:
    def test_delegates_to_mappers(self) -> None:
        msg = MagicMock()
        with patch(
            'backend.inference.mappers.openai.extract_tool_calls',
            return_value='tc',
        ) as m:
            assert ops.extract_openai_tool_calls(msg) == 'tc'
        m.assert_called_once_with(msg)


class TestRateLimitErrorDetails:
    def test_extracts_code_and_message_from_body(self) -> None:
        exc = SimpleNamespace(
            code=None,
            body={'error': {'code': 'quota', 'message': 'Slow down'}},
            status_code=503,
        )
        message, code, body, status = ops._rate_limit_error_details(exc)
        assert message == 'Slow down (code=quota)'
        assert code == 'quota'
        assert body == {'error': {'code': 'quota', 'message': 'Slow down'}}
        assert status == 503

    def test_keeps_message_when_code_already_embedded(self) -> None:
        exc = Exception('denied code=abc')
        exc.code = 'abc'
        exc.body = None
        exc.status_code = None
        message, code, body, status = ops._rate_limit_error_details(exc)
        assert message == 'denied code=abc'
        assert code == 'abc'
        assert status == 429

    def test_ignores_non_dict_error_body(self) -> None:
        exc = SimpleNamespace(code=None, body={'error': 'denied'}, status_code=None)
        message, code, body, status = ops._rate_limit_error_details(exc)
        assert code is None
        assert status == 429
        assert 'denied' in message


class TestMapRateLimitError:
    def test_insufficient_quota_maps_to_authentication_error(self) -> None:
        client = MagicMock()
        client.model_name = 'gpt-4'
        exc = Exception('You exceeded your current quota')
        exc.code = 'insufficient_quota'
        exc.body = None
        exc.status_code = 429
        mapped = ops._map_rate_limit_error(client, exc)
        assert isinstance(mapped, AuthenticationError)
        assert mapped.model == 'gpt-4'
        assert mapped.llm_provider == 'openai'
        assert mapped.status_code == 429

    def test_generic_rate_limit_maps_and_enriches(self) -> None:
        client = MagicMock()
        client.model_name = 'gpt-4'
        exc = Exception('Rate limit reached')
        exc.code = None
        exc.body = {'error': {'message': 'slow down please'}}
        exc.status_code = 429
        mapped = ops._map_rate_limit_error(client, exc)
        assert isinstance(mapped, RateLimitError)
        assert mapped.model == 'gpt-4'
        assert mapped.llm_provider == 'openai'


class TestMapBadRequestError:
    def test_context_window_exceeded(self) -> None:
        client = MagicMock()
        client.model_name = 'gpt-4'
        mapped = ops._map_bad_request_error(client, Exception('prompt is too long'))
        assert isinstance(mapped, ContextWindowExceededError)
        assert mapped.model == 'gpt-4'

    def test_plain_bad_request(self) -> None:
        client = MagicMock()
        client.model_name = 'gpt-4'
        mapped = ops._map_bad_request_error(client, Exception('invalid request'))
        assert isinstance(mapped, BadRequestError)
        assert mapped.model == 'gpt-4'


class TestMapOpenaiError:
    @staticmethod
    def _client() -> MagicMock:
        client = MagicMock()
        client.model_name = 'gpt-4'
        return client

    @staticmethod
    def _response(status_code: int) -> MagicMock:
        response = MagicMock()
        response.status_code = status_code
        response.request = MagicMock()
        return response

    def test_maps_sdk_timeout(self) -> None:
        exc = openai.APITimeoutError(request=MagicMock())
        mapped = ops.map_openai_error(self._client(), exc)
        assert isinstance(mapped, Timeout)

    def test_maps_httpx_timeout(self) -> None:
        exc = httpx.TimeoutException('timed out', request=MagicMock())
        mapped = ops.map_openai_error(self._client(), exc)
        assert isinstance(mapped, Timeout)

    def test_maps_sdk_connection_error(self) -> None:
        exc = openai.APIConnectionError(request=MagicMock())
        mapped = ops.map_openai_error(self._client(), exc)
        assert isinstance(mapped, APIConnectionError)

    def test_maps_httpx_request_error(self) -> None:
        exc = httpx.RequestError('connect failed', request=MagicMock())
        mapped = ops.map_openai_error(self._client(), exc)
        assert isinstance(mapped, APIConnectionError)

    def test_maps_rate_limit_error(self) -> None:
        exc = openai.RateLimitError(
            message='slow down', response=self._response(429), body=None
        )
        mapped = ops.map_openai_error(self._client(), exc)
        assert isinstance(mapped, RateLimitError)
        assert mapped.status_code == 429

    def test_maps_authentication_error_with_non_auth_status(self) -> None:
        exc = openai.AuthenticationError(
            message='bad key', response=self._response(400), body=None
        )
        mapped = ops.map_openai_error(self._client(), exc)
        assert isinstance(mapped, AuthenticationError)

    def test_maps_bad_request_error(self) -> None:
        exc = openai.BadRequestError(
            message='invalid request', response=self._response(400), body=None
        )
        mapped = ops.map_openai_error(self._client(), exc)
        assert isinstance(mapped, BadRequestError)

    def test_maps_context_window_bad_request(self) -> None:
        exc = openai.BadRequestError(
            message='maximum context length exceeded',
            response=self._response(400),
            body=None,
        )
        mapped = ops.map_openai_error(self._client(), exc)
        assert isinstance(mapped, ContextWindowExceededError)

    def test_maps_not_found_error(self) -> None:
        exc = openai.NotFoundError(
            message='model not found', response=self._response(404), body=None
        )
        mapped = ops.map_openai_error(self._client(), exc)
        assert isinstance(mapped, NotFoundError)

    def test_maps_internal_server_error(self) -> None:
        exc = openai.InternalServerError(
            message='boom', response=self._response(500), body=None
        )
        mapped = ops.map_openai_error(self._client(), exc)
        assert isinstance(mapped, InternalServerError)

    def test_maps_generic_api_status_error(self) -> None:
        class _CustomStatusError(openai.APIStatusError):
            pass

        exc = _CustomStatusError(
            message='conflict', response=self._response(409), body=None
        )
        mapped = ops.map_openai_error(self._client(), exc)
        assert isinstance(mapped, APIError)
        assert mapped.status_code == 409

    def test_unknown_exception_passes_through(self) -> None:
        exc = RuntimeError('mystery')
        assert ops.map_openai_error(self._client(), exc) is exc


class TestIsDeepseekThinkingReplayModel:
    def test_returns_false_for_non_deepseek_provider(self) -> None:
        client = MagicMock()
        client._provider_name = 'anthropic'
        client.model_name = 'deepseek-v4-flash'
        assert ops._is_deepseek_thinking_replay_model(client) is False


class TestMessageContentToText:
    def test_none_content(self) -> None:
        assert ops._message_content_to_text(None) == ''

    def test_dict_content_with_text_string(self) -> None:
        assert ops._message_content_to_text({'text': 'hello'}) == 'hello'

    def test_dict_content_without_text_string(self) -> None:
        assert ops._message_content_to_text({'text': 5}) == str({'text': 5})

    def test_list_content_joined(self) -> None:
        assert ops._message_content_to_text(['a', {'text': 'b'}, 3]) == 'ab3'

    def test_other_scalar(self) -> None:
        assert ops._message_content_to_text(42) == '42'


class TestFlattenStaleDeepseekAssistantMessage:
    def test_skips_non_dict_tool_calls(self) -> None:
        msg = {
            'role': 'assistant',
            'content': 'checking',
            'tool_calls': [
                'nope',
                {
                    'id': 'c1',
                    'type': 'function',
                    'function': {'name': 'read_file', 'arguments': '{}'},
                },
            ],
        }
        result = ops._flatten_stale_deepseek_assistant_message(msg)
        assert result['role'] == 'user'
        assert 'checking' in result['content']
        assert 'nope' not in result['content']
        assert 'read_file' in result['content']


class TestRecoverDeepseekThinkingHistory:
    def test_returns_messages_unchanged_for_other_providers(self) -> None:
        client = MagicMock()
        client._provider_name = 'anthropic'
        messages = [{'role': 'user', 'content': 'hi'}]
        assert ops._recover_deepseek_thinking_history(client, messages) is messages

    def test_non_dict_messages_pass_through(self) -> None:
        client = MagicMock()
        client._provider_name = 'opencode-go'
        client.model_name = 'deepseek-v4-flash'
        messages = ['raw', {'role': 'assistant', 'content': 'stale'}]
        recovered = ops._recover_deepseek_thinking_history(client, messages)
        assert recovered[0] == 'raw'
        assert recovered[1]['role'] == 'user'


class TestCallOpenaiChat:
    def test_reraises_mapped_error(self) -> None:
        client = MagicMock()
        mapped = BadRequestError('mapped', llm_provider='openai', model='gpt-4')
        client._map_openai_error.side_effect = lambda exc: mapped
        client.client.chat.completions.create.side_effect = RuntimeError('wire failure')
        with pytest.raises(BadRequestError, match='mapped'):
            ops._call_openai_chat(client, [], {})


class TestWarnEmptyResponse:
    def test_raises_when_no_choices(self) -> None:
        with pytest.raises(BadRequestError, match='no choices'):
            ops._warn_empty_response(MagicMock(choices=[]), 'gpt-4')

    def test_raises_when_choices_attr_missing(self) -> None:
        with pytest.raises(BadRequestError, match='no choices'):
            ops._warn_empty_response(MagicMock(), 'gpt-4')

    def test_warns_when_content_is_blank(self) -> None:
        first = MagicMock()
        msg = MagicMock()
        msg.content = '   '
        msg.model_dump.side_effect = RuntimeError('dump failed')
        first.message = msg
        first.finish_reason = 'stop'
        response = MagicMock(choices=[first])
        with patch.object(logging.getLogger('app'), 'warning') as warn:
            ops._warn_empty_response(response, 'gpt-4')
        warn.assert_called_once()
        args = warn.call_args.args
        assert 'empty message' in args[0]
        assert 'model=%s' in args[0]


class TestACompletion:
    @staticmethod
    def _response(content: str = 'ok') -> MagicMock:
        response = MagicMock()
        response.choices = [
            MagicMock(message=MagicMock(content=content), finish_reason='stop')
        ]
        response.model = 'gpt-4'
        response.usage = None
        response.id = 'resp-1'
        return response

    @staticmethod
    def _client(response: MagicMock) -> MagicMock:
        client = MagicMock()
        client.model_name = 'gpt-4'
        client._provider_name = 'openai'
        client._clean_messages.side_effect = lambda msgs: msgs
        client._strip_unsupported_params.side_effect = lambda kwargs: kwargs
        client._extract_openai_tool_calls.return_value = None
        client.async_client.chat.completions.create = AsyncMock(return_value=response)
        return client

    async def test_happy_path(self) -> None:
        client = self._client(self._response())
        result = await ops.acompletion(
            client, [{'role': 'user', 'content': 'hi'}], model='override'
        )
        assert result.content == 'ok'
        assert result.model == 'gpt-4'
        assert result.id == 'resp-1'
        assert result.usage['prompt_tokens'] == 0
        assert result.usage['total_tokens'] == 0
        assert result.tool_calls is None
        create_kwargs = client.async_client.chat.completions.create.call_args.kwargs
        assert create_kwargs['model'] == 'gpt-4'

    async def test_reraises_mapped_error_from_create(self) -> None:
        client = self._client(self._response())
        mapped = Timeout('timed out', llm_provider='openai', model='gpt-4')
        client.async_client.chat.completions.create = AsyncMock(
            side_effect=RuntimeError('wire')
        )
        client._map_openai_error.side_effect = lambda exc: mapped
        with pytest.raises(Timeout):
            await ops.acompletion(client, [{'role': 'user', 'content': 'hi'}])

    async def test_raises_when_no_choices(self) -> None:
        response = MagicMock(choices=[])
        client = self._client(response)
        with pytest.raises(BadRequestError, match='no choices'):
            await ops.acompletion(client, [{'role': 'user', 'content': 'hi'}])

    async def test_returns_tool_calls(self) -> None:
        client = self._client(self._response())
        tool_calls = [
            {
                'id': 'c1',
                'type': 'function',
                'function': {'name': 'read_file', 'arguments': '{}'},
            }
        ]
        client._extract_openai_tool_calls.return_value = tool_calls
        result = await ops.acompletion(client, [{'role': 'user', 'content': 'hi'}])
        assert result.tool_calls == tool_calls


class TestReasoningDetailsText:
    def test_non_list_returns_empty(self) -> None:
        assert ops._reasoning_details_text(None) == ''
        assert ops._reasoning_details_text('nope') == ''

    def test_joins_string_and_dict_items(self) -> None:
        details = [
            'a',
            '',
            5,
            {'type': 'text', 'text': 'b'},
            {'type': 'summary', 'summary': 'c'},
            {'type': 'encrypted', 'text': 'secret'},
            {'type': 'text', 'text': ''},
        ]
        assert ops._reasoning_details_text(details) == 'abc'


class TestCoalesceStreamDeltaReasoning:
    def test_keeps_existing_reasoning_content(self) -> None:
        delta = {'reasoning_content': 'already there'}
        assert ops._coalesce_stream_delta_reasoning(delta) is delta

    def test_maps_reasoning_field(self) -> None:
        result = ops._coalesce_stream_delta_reasoning({'reasoning': 'thoughts'})
        assert result == {'reasoning': 'thoughts', 'reasoning_content': 'thoughts'}

    def test_maps_thinking_field(self) -> None:
        result = ops._coalesce_stream_delta_reasoning({'thinking': 'hmm'})
        assert result['reasoning_content'] == 'hmm'

    def test_maps_reasoning_details(self) -> None:
        delta = {'reasoning_details': [{'type': 'text', 'text': 'deep'}]}
        result = ops._coalesce_stream_delta_reasoning(delta)
        assert result == {
            'reasoning_details': [{'type': 'text', 'text': 'deep'}],
            'reasoning_content': 'deep',
        }

    def test_returns_unchanged_when_no_reasoning_fields(self) -> None:
        delta = {'content': 'x'}
        assert ops._coalesce_stream_delta_reasoning(delta) is delta


class TestEnrichOpenaiStreamChunk:
    def test_unchanged_without_choices(self) -> None:
        chunk = {'id': 'x'}
        assert ops._enrich_openai_stream_chunk(chunk) is chunk

    def test_unchanged_when_choices_not_a_list(self) -> None:
        chunk = {'choices': 'nope'}
        assert ops._enrich_openai_stream_chunk(chunk) is chunk

    def test_unchanged_when_choices_empty(self) -> None:
        chunk: dict[str, Any] = {'choices': []}
        assert ops._enrich_openai_stream_chunk(chunk) is chunk

    def test_unchanged_when_choice_not_a_dict(self) -> None:
        chunk = {'choices': ['nope']}
        assert ops._enrich_openai_stream_chunk(chunk) is chunk

    def test_unchanged_when_delta_not_a_dict(self) -> None:
        chunk = {'choices': [{'delta': 'x'}]}
        assert ops._enrich_openai_stream_chunk(chunk) is chunk

    def test_unchanged_when_no_enrichment_needed(self) -> None:
        chunk = {'choices': [{'delta': {'content': 'hi'}}]}
        assert ops._enrich_openai_stream_chunk(chunk) is chunk

    def test_enriches_first_choice_delta(self) -> None:
        chunk = {
            'choices': [
                {'index': 0, 'delta': {'thinking': 'hmm'}},
                {'index': 1, 'delta': {'content': 'y'}},
            ]
        }
        result = ops._enrich_openai_stream_chunk(chunk)
        assert result['choices'][0]['delta'] == {
            'thinking': 'hmm',
            'reasoning_content': 'hmm',
        }
        assert result['choices'][1] == {'index': 1, 'delta': {'content': 'y'}}


class TestAStream:
    @staticmethod
    def _client(stream: object) -> MagicMock:
        client = MagicMock()
        client.model_name = 'gpt-4'
        client._provider_name = 'openai'
        client._clean_messages.side_effect = lambda msgs: msgs
        client._strip_unsupported_params.side_effect = lambda kwargs: kwargs
        client.async_client.chat.completions.create = AsyncMock(return_value=stream)
        return client

    async def test_yields_enriched_chunks(self) -> None:
        async def _gen():
            yield SimpleNamespace(
                model_dump=lambda: {'choices': [{'delta': {'content': 'a'}}]}
            )
            yield SimpleNamespace(
                model_dump=lambda: {'choices': [{'delta': {'reasoning': 'r'}}]}
            )

        client = self._client(_gen())
        out = [c async for c in ops.astream(client, [{'role': 'user', 'content': 'hi'}])]
        assert out[0] == {'choices': [{'delta': {'content': 'a'}}]}
        assert out[1]['choices'][0]['delta'] == {
            'reasoning': 'r',
            'reasoning_content': 'r',
        }
        create_kwargs = client.async_client.chat.completions.create.call_args.kwargs
        assert create_kwargs['stream'] is True
        assert create_kwargs['stream_options'] == {'include_usage': True}
        assert create_kwargs['model'] == 'gpt-4'

    async def test_reraises_mapped_create_error(self) -> None:
        client = self._client(None)
        client.async_client.chat.completions.create = AsyncMock(
            side_effect=RuntimeError('boom')
        )
        client._map_openai_error.side_effect = lambda exc: Timeout(
            't', llm_provider='openai', model='gpt-4'
        )
        with pytest.raises(Timeout):
            async for _ in ops.astream(client, [{'role': 'user', 'content': 'hi'}]):
                pass

    async def test_reraises_mapped_iteration_error(self) -> None:
        async def _gen():
            yield SimpleNamespace(model_dump=lambda: {'choices': []})
            raise RuntimeError('mid-stream')

        client = self._client(_gen())
        client._map_openai_error.side_effect = lambda exc: BadRequestError(
            'mid', llm_provider='openai', model='gpt-4'
        )
        collected = []
        with pytest.raises(BadRequestError, match='mid'):
            async for c in ops.astream(client, [{'role': 'user', 'content': 'hi'}]):
                collected.append(c)
        assert len(collected) == 1
