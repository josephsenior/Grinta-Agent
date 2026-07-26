"""Unit tests for backend.inference.clients — factory routing and LLMResponse."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from backend.inference.clients import (
    LLMResponse,
    _pool_key,
    get_direct_client,
)
from backend.inference.clients.codex_app_server import CodexAppServerClient

# ---------------------------------------------------------------------------
# Helper: mock the SDK constructors to avoid real HTTP clients
# ---------------------------------------------------------------------------


def _mock_openai_sdk():
    """Return a patch context that makes OpenAI + AsyncOpenAI constructors no-ops."""
    return [
        patch('backend.inference.clients.OpenAI'),
        patch('backend.inference.clients.AsyncOpenAI'),
        patch(
            'backend.inference.clients.get_shared_http_client',
            return_value=MagicMock(spec=True),
        ),
        patch(
            'backend.inference.clients.get_shared_async_http_client',
            return_value=MagicMock(spec=True),
        ),
    ]


def test_codex_model_list_uses_account_catalog() -> None:
    client = CodexAppServerClient()
    with (
        patch.object(client, '_ensure_started'),
        patch.object(
            client,
            '_request',
            side_effect=[
                {
                    'data': [
                        {'id': 'first-id', 'model': 'gpt-5.6-luna'},
                        {'id': 'fallback-id'},
                    ],
                    'nextCursor': 'next',
                },
                {'data': [{'id': 'second-id', 'model': 'gpt-5.4-mini'}]},
            ],
        ),
    ):
        assert client.list_available_models() == [
            'gpt-5.6-luna',
            'fallback-id',
            'gpt-5.4-mini',
        ]


def test_codex_thread_params_pass_reasoning_effort_to_app_server() -> None:
    client = CodexAppServerClient(model_name='gpt-5.6-sol')
    params = client._thread_params('xhigh')
    assert params['model'] == 'gpt-5.6-sol'
    assert params['sandbox'] == 'workspace-write'
    assert params['config'] == {
        'model_reasoning_effort': 'xhigh',
        'model_reasoning_summary': 'detailed',
    }


def test_codex_stream_turn_forwards_reasoning_to_the_transcript() -> None:
    client = CodexAppServerClient()
    emitted = []
    with (
        patch.object(client, '_ensure_started'),
        patch.object(
            client,
            '_request',
            side_effect=[{'thread': {'id': 'thread-1'}}, {'turn': {'id': 'turn-1'}}],
        ),
        patch.object(
            client,
            '_read',
            side_effect=[
                {
                    'method': 'item/reasoning/summaryTextDelta',
                    'params': {'turnId': 'turn-1', 'delta': 'Checking the request. '},
                },
                {
                    'method': 'item/agentMessage/delta',
                    'params': {'turnId': 'turn-1', 'delta': 'Done.'},
                },
                {
                    'method': 'turn/completed',
                    'params': {'turn': {'id': 'turn-1'}},
                },
            ],
        ),
    ):
        client._stream_turn([{'role': 'user', 'content': 'Hi'}], 'high', emitted.append)

    assert emitted == [
        {'reasoning_content': 'Checking the request. '},
        {'content': 'Done.'},
    ]


def test_codex_turn_usage_includes_reasoning_tokens() -> None:
    client = CodexAppServerClient()
    with patch.object(
        client,
        '_read',
        side_effect=[
            {
                'method': 'thread/tokenUsage/updated',
                'params': {
                    'turnId': 'turn-1',
                    'tokenUsage': {
                        'total': {
                            'inputTokens': 100,
                            'outputTokens': 50,
                            'reasoningOutputTokens': 40,
                            'totalTokens': 150,
                        }
                    },
                },
            },
            {
                'method': 'item/agentMessage/delta',
                'params': {'delta': 'Hello'},
            },
            {
                'method': 'turn/completed',
                'params': {'turn': {'id': 'turn-1'}},
            },
        ],
    ):
        content, usage = client._wait_for_turn('turn-1')

    assert content == 'Hello'
    assert usage['reasoning_tokens'] == 40


# ---------------------------------------------------------------------------
# _pool_key
# ---------------------------------------------------------------------------


class TestPoolKey:
    def test_with_base_url(self):
        assert (
            _pool_key('openai', 'https://api.openai.com')
            == 'openai::https://api.openai.com'
        )

    def test_without_base_url(self):
        assert _pool_key('anthropic', None) == 'anthropic::default'


# ---------------------------------------------------------------------------
# LLMResponse
# ---------------------------------------------------------------------------


class TestLLMResponse:
    def test_construction(self):
        r = LLMResponse(
            content='Hello',
            model='gpt-4o',
            usage={'prompt_tokens': 10, 'completion_tokens': 5},
        )
        assert r.content == 'Hello'
        assert r.model == 'gpt-4o'
        assert r.usage == {'prompt_tokens': 10, 'completion_tokens': 5}
        assert r.finish_reason == 'stop'
        assert r.tool_calls is None

    def test_choices_attribute(self):
        r = LLMResponse(content='Hi', model='m', usage={})
        assert len(r.choices) == 1
        assert r.choices[0].message.content == 'Hi'
        assert r.choices[0].message.role == 'assistant'
        assert r.choices[0].finish_reason == 'stop'

    def test_to_dict(self):
        r = LLMResponse(content='reply', model='m', usage={'prompt_tokens': 1})
        d = r.to_dict()
        assert d['choices'][0]['message']['content'] == 'reply'
        assert d['choices'][0]['message']['role'] == 'assistant'
        assert d['model'] == 'm'

    def test_to_dict_includes_tool_calls(self):
        tc = [
            {
                'id': 't1',
                'type': 'function',
                'function': {'name': 'f', 'arguments': '{}'},
            }
        ]
        r = LLMResponse(content='', model='m', usage={}, tool_calls=tc)
        d = r.to_dict()
        assert d['choices'][0]['message']['tool_calls'] == tc

    def test_getitem_dict_access(self):
        r = LLMResponse(content='x', model='m', usage={})
        assert r['model'] == 'm'
        assert len(r['choices']) == 1

    def test_custom_finish_reason(self):
        r = LLMResponse(content='', model='m', usage={}, finish_reason='length')
        assert r.finish_reason == 'length'
        assert r.choices[0].finish_reason == 'length'


# ---------------------------------------------------------------------------
# get_direct_client — routing
# ---------------------------------------------------------------------------


class TestGetDirectClientRouting:
    """Verify factory routes models to the correct client classes."""

    @patch('backend.inference.clients.AsyncOpenAI')
    @patch('backend.inference.clients.OpenAI')
    @patch(
        'backend.inference.clients.get_shared_async_http_client',
        return_value=MagicMock(),
    )
    @patch(
        'backend.inference.clients.get_shared_http_client',
        return_value=MagicMock(),
    )
    def test_openai_default(self, _h, _ah, _oai, _aoai):
        client = get_direct_client('openai/gpt-5', api_key='sk-test')
        assert type(client).__name__ == 'OpenAIClient'
        assert client._model_name == 'gpt-5'

    def test_codex_routes_to_app_server(self):
        client = get_direct_client('codex/default', api_key='')
        assert type(client).__name__ == 'CodexAppServerClient'
        assert client._model_name == 'default'

    @patch('backend.inference.clients.Anthropic')
    @patch('backend.inference.clients.AsyncAnthropic')
    def test_anthropic_routing(self, _async, _sync):
        client = get_direct_client('anthropic/claude-3.5-sonnet', api_key='key')
        assert type(client).__name__ == 'AnthropicClient'

    @patch('backend.inference.clients.Anthropic')
    @patch('backend.inference.clients.AsyncAnthropic')
    def test_claude_routing(self, _async, _sync):
        client = get_direct_client('anthropic/claude-sonnet-4-5', api_key='key')
        assert type(client).__name__ == 'AnthropicClient'

    @patch('backend.inference.providers.gemini_ops.genai')
    def test_gemini_alias_prefix_rejected(self, _genai):
        with pytest.raises(ValueError):
            get_direct_client('gemini/gemini-2.5-flash', api_key='key')

    @patch('backend.inference.providers.gemini_ops.genai')
    def test_google_routing(self, _genai):
        client = get_direct_client('google/gemini-1.5-pro', api_key='key')
        assert type(client).__name__ == 'GeminiClient'

    @patch('backend.inference.clients.AsyncOpenAI')
    @patch('backend.inference.clients.OpenAI')
    @patch(
        'backend.inference.clients.get_shared_async_http_client',
        return_value=MagicMock(),
    )
    @patch(
        'backend.inference.clients.get_shared_http_client',
        return_value=MagicMock(),
    )
    def test_lightning_routing_strips_provider_prefix(self, _h, _ah, _oai, _aoai):
        client = get_direct_client(
            'lightning/google/gemini-3-flash-preview',
            api_key='key',
        )
        assert type(client).__name__ == 'OpenAIClient'
        assert client._model_name == 'google/gemini-3-flash-preview'

    @patch('backend.inference.clients.AsyncOpenAI')
    @patch('backend.inference.clients.OpenAI')
    @patch(
        'backend.inference.clients.get_shared_async_http_client',
        return_value=MagicMock(),
    )
    @patch(
        'backend.inference.clients.get_shared_http_client',
        return_value=MagicMock(),
    )
    def test_xai_grok_routing(self, _h, _ah, _oai, _aoai):
        client = get_direct_client('xai/grok-3', api_key='key')
        assert type(client).__name__ == 'OpenAIClient'

    @patch('backend.inference.clients.AsyncOpenAI')
    @patch('backend.inference.clients.OpenAI')
    @patch(
        'backend.inference.clients.get_shared_async_http_client',
        return_value=MagicMock(),
    )
    @patch(
        'backend.inference.clients.get_shared_http_client',
        return_value=MagicMock(),
    )
    def test_grok_routing(self, _h, _ah, _oai, _aoai):
        client = get_direct_client('xai/grok-build-0.1', api_key='key')
        assert type(client).__name__ == 'OpenAIClient'

    @patch('backend.inference.clients.AsyncOpenAI')
    @patch('backend.inference.clients.OpenAI')
    @patch(
        'backend.inference.clients.get_shared_async_http_client',
        return_value=MagicMock(),
    )
    @patch(
        'backend.inference.clients.get_shared_http_client',
        return_value=MagicMock(),
    )
    def test_ollama_routing_strips_prefix(self, _h, _ah, _oai, _aoai):
        client = get_direct_client('ollama/llama3.2', api_key='')
        assert type(client).__name__ == 'OpenAIClient'
        assert client._model_name == 'llama3.2'

    @patch('backend.inference.clients.AsyncOpenAI')
    @patch('backend.inference.clients.OpenAI')
    @patch(
        'backend.inference.clients.get_shared_async_http_client',
        return_value=MagicMock(),
    )
    @patch(
        'backend.inference.clients.get_shared_http_client',
        return_value=MagicMock(),
    )
    def test_ollama_defaults_base_url(self, _h, _ah, _oai, _aoai):
        client = get_direct_client('ollama/codestral', api_key='')
        assert client._model_name == 'codestral'

    @patch('backend.inference.clients.AsyncOpenAI')
    @patch('backend.inference.clients.OpenAI')
    @patch(
        'backend.inference.clients.get_shared_async_http_client',
        return_value=MagicMock(),
    )
    @patch(
        'backend.inference.clients.get_shared_http_client',
        return_value=MagicMock(),
    )
    def test_ollama_custom_base_url_respected(self, _h, _ah, _oai, _aoai):
        client = get_direct_client(
            'ollama/phi3',
            api_key='',
            base_url='http://remote:11434/v1',
        )
        assert client._model_name == 'phi3'

    @patch('backend.inference.clients.AsyncOpenAI')
    @patch('backend.inference.clients.OpenAI')
    @patch(
        'backend.inference.clients.get_shared_async_http_client',
        return_value=MagicMock(),
    )
    @patch(
        'backend.inference.clients.get_shared_http_client',
        return_value=MagicMock(),
    )
    def test_ollama_without_prefix(self, _h, _ah, _oai, _aoai):
        """Ambiguous local-looking names no longer route without an explicit prefix."""
        with pytest.raises(ValueError, match='Provider is ambiguous'):
            get_direct_client('ollama-test-model', api_key='')

    @patch('backend.inference.clients.AsyncOpenAI')
    @patch('backend.inference.clients.OpenAI')
    @patch(
        'backend.inference.clients.get_shared_async_http_client',
        return_value=MagicMock(),
    )
    @patch(
        'backend.inference.clients.get_shared_http_client',
        return_value=MagicMock(),
    )
    def test_unknown_model_defaults_to_openai(self, _h, _ah, _oai, _aoai):
        with pytest.raises(ValueError, match='Provider is ambiguous'):
            get_direct_client('my-custom-model', api_key='key')

    @patch('backend.inference.clients.AsyncOpenAI')
    @patch('backend.inference.clients.OpenAI')
    @patch(
        'backend.inference.clients.get_shared_async_http_client',
        return_value=MagicMock(),
    )
    @patch(
        'backend.inference.clients.get_shared_http_client',
        return_value=MagicMock(),
    )
    def test_explicit_custom_openai_model_routes(self, _h, _ah, _oai, _aoai):
        client = get_direct_client('openai/my-custom-model', api_key='key')
        assert type(client).__name__ == 'OpenAIClient'

    @patch('backend.inference.clients.AsyncOpenAI')
    @patch('backend.inference.clients.OpenAI')
    @patch(
        'backend.inference.clients.get_shared_async_http_client',
        return_value=MagicMock(),
    )
    @patch(
        'backend.inference.clients.get_shared_http_client',
        return_value=MagicMock(),
    )
    def test_custom_base_url_passthrough(self, _h, _ah, _oai, _aoai):
        client = get_direct_client(
            'openai/my-model', api_key='key', base_url='http://localhost:8080/v1'
        )
        assert type(client).__name__ == 'OpenAIClient'

    @patch('backend.inference.clients.Anthropic')
    @patch('backend.inference.clients.AsyncAnthropic')
    @patch(
        'backend.inference.clients.get_shared_async_http_client',
        return_value=MagicMock(),
    )
    @patch(
        'backend.inference.clients.get_shared_http_client',
        return_value=MagicMock(),
    )
    def test_opencode_go_minimax_routes_to_anthropic_messages(
        self, _h, _ah, _async_anth, _anth
    ):
        client = get_direct_client('opencode-go/minimax-m2.7', api_key='key')
        assert type(client).__name__ == 'AnthropicClient'
        assert client._model_name == 'minimax-m2.7'

    @patch('backend.inference.clients.AsyncOpenAI')
    @patch('backend.inference.clients.OpenAI')
    @patch(
        'backend.inference.clients.get_shared_async_http_client',
        return_value=MagicMock(),
    )
    @patch(
        'backend.inference.clients.get_shared_http_client',
        return_value=MagicMock(),
    )
    def test_opencode_go_qwen_routes_to_openai_compatible(self, _h, _ah, _oai, _aoai):
        client = get_direct_client('opencode-go/deepseek-v4-flash', api_key='key')
        assert type(client).__name__ == 'OpenAIClient'
        assert client._model_name == 'deepseek-v4-flash'


# ---------------------------------------------------------------------------
# DirectLLMClient.model_name validation
# ---------------------------------------------------------------------------


class TestDirectLLMClientModelName:
    @patch('backend.inference.clients.AsyncOpenAI')
    @patch('backend.inference.clients.OpenAI')
    @patch(
        'backend.inference.clients.get_shared_async_http_client',
        return_value=MagicMock(),
    )
    @patch(
        'backend.inference.clients.get_shared_http_client',
        return_value=MagicMock(),
    )
    def test_model_name_set(self, _h, _ah, _oai, _aoai):
        client = get_direct_client('openai/gpt-5', api_key='k')
        assert client.model_name == 'gpt-5'
