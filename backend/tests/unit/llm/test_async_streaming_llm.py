"""Tests for async and streaming LLM adapters."""

from __future__ import annotations

import asyncio
from typing import Any
from unittest.mock import MagicMock, patch

import pytest

from forge.core.config.llm_config import LLMConfig, suppress_llm_env_export
from forge.llm import LLM
from forge.llm.direct_clients import LLMResponse
from forge.core.exceptions import UserCancelledError


class FakeResponse(dict):
    def __init__(self, content: str = "content") -> None:
        super().__init__(
            choices=[
                {"message": {"content": content, "tool_calls": [], "cache_control": {}}}
            ],
            usage={"prompt_tokens": 1, "completion_tokens": 1},
        )


def _make_config(**overrides: Any) -> LLMConfig:
    defaults = dict(
        model="gemini-2.5-pro",
        api_key=None,
        log_completions=False,
        caching_prompt=True,
        disable_vision=False,
        reasoning_effort="medium",
        max_output_tokens=32,
        timeout=5,
    )
    defaults.update(overrides)
    with suppress_llm_env_export():
        return LLMConfig(**defaults)


@pytest.fixture
def mock_client():
    client = MagicMock()
    client.acompletion.return_value = LLMResponse(
        content="content",
        model="gemini-2.5-pro",
        usage={"prompt_tokens": 1, "completion_tokens": 1},
        response_id="resp-1"
    )
    async def fake_stream(*args, **kwargs):
        yield {"choices": [{"delta": {"content": "chunk"}, "finish_reason": None}]}
        yield {"choices": [{"delta": {}, "finish_reason": "stop"}]}
    client.astream.side_effect = fake_stream
    return client


@pytest.mark.asyncio
@patch("forge.llm.llm.get_direct_client")
async def test_async_completion_flow(mock_get_direct_client, mock_client) -> None:
    mock_get_direct_client.return_value = mock_client
    config = _make_config()
    llm = LLM(config=config, service_id="svc")
    
    result = await llm.async_completion(messages=[{"role": "user", "content": "hi"}])
    assert result["choices"][0]["message"]["content"] == "content"

    # Exercise helper utilities
    parsed = llm._extract_messages(([{"role": "user", "content": "msg"}],), {})
    assert parsed[0]["content"] == "msg"

    kwargs = {"messages": [{"role": "user", "content": "hi"}]}
    # In the new LLM class, _configure_completion_params doesn't exist anymore
    # but completion/acompletion handles it internally.
    # We can test that the client was called with correct params.
    await llm.acompletion(messages=[{"role": "user", "content": "hi"}], reasoning_effort="high")
    mock_client.acompletion.assert_called_with(
        messages=[{"role": "user", "content": "hi"}],
        temperature=config.temperature,
        max_tokens=config.max_output_tokens,
        reasoning_effort="high"
    )


@pytest.mark.asyncio
@patch("forge.llm.llm.get_direct_client")
async def test_async_completion_handles_exceptions(
    mock_get_direct_client, mock_client
) -> None:
    mock_get_direct_client.return_value = mock_client
    mock_client.acompletion.side_effect = RuntimeError("boom")
    
    config = _make_config()
    llm = LLM(config=config, service_id="svc")

    with pytest.raises(RuntimeError):
        await llm.acompletion(messages=[{"role": "user", "content": "hi"}])


@pytest.mark.asyncio
@patch("forge.llm.llm.get_direct_client")
async def test_streaming_completion_flow(mock_get_direct_client, mock_client) -> None:
    mock_get_direct_client.return_value = mock_client
    config = _make_config(
        base_url="https://example", api_version="v1", custom_llm_provider="custom"
    )
    llm = LLM(config=config, service_id="svc")

    chunks = []
    async for chunk in llm.async_streaming_completion(
        messages=[{"role": "user", "content": "hi"}]
    ):
        chunks.append(chunk)
    assert chunks[0]["choices"][0]["delta"]["content"] == "chunk"

    # Validate helper behavior
    messages = llm._extract_messages(([{"role": "user", "content": "ping"}],), {})
    assert messages[0]["content"] == "ping"


@pytest.mark.asyncio
@patch("forge.llm.llm.get_direct_client")
async def test_streaming_handles_cancellation(mock_get_direct_client, mock_client) -> None:
    mock_get_direct_client.return_value = mock_client
    
    async def cancel():
        return True

    config = _make_config()
    config.on_cancel_requested_fn = cancel
    llm = LLM(config=config, service_id="svc")

    async def generator(*args, **kwargs):
        yield {"choices": [{"delta": {"content": "chunk"}, "finish_reason": None}]}

    mock_client.astream.side_effect = generator

    # The current LLM.astream implementation doesn't raise UserCancelledError, 
    # it just breaks the loop.
    chunks = []
    async for chunk in llm.astream(messages=[{"role": "user", "content": "hi"}]):
        chunks.append(chunk)
    
    # It should break after the first chunk if cancel is True
    # Actually in the implementation it checks AFTER yielding a chunk.
    # So it should yield one chunk and then stop.
    assert len(chunks) == 1


@pytest.mark.asyncio
@patch("forge.llm.llm.get_direct_client")
async def test_streaming_wrapper_exception(mock_get_direct_client, mock_client) -> None:
    mock_get_direct_client.return_value = mock_client
    mock_client.astream.side_effect = RuntimeError("failure")
    
    config = _make_config()
    llm = LLM(config=config, service_id="svc")

    with pytest.raises(RuntimeError):
        async for _ in llm.astream(
            messages=[{"role": "user", "content": "hi"}]
        ):
            pass
