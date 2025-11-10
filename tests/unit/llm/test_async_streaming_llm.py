"""Tests for async and streaming LLM adapters."""

from __future__ import annotations

import asyncio
from types import SimpleNamespace
from typing import Any

import pytest

from forge.core.config.llm_config import LLMConfig, suppress_llm_env_export
from forge.llm import async_llm as async_module
from forge.llm import streaming_llm as streaming_module


class FakeResponse(dict):
    def __init__(self, content: str = "content") -> None:
        super().__init__(
            choices=[{"message": {"content": content, "tool_calls": [], "cache_control": {}}}],
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


def _patch_async_env(monkeypatch: pytest.MonkeyPatch) -> None:
    features = SimpleNamespace(
        supports_reasoning_effort=True,
        supports_prompt_cache=True,
        supports_stop_words=True,
    )
    monkeypatch.setattr(async_module, "get_features", lambda model: features)
    monkeypatch.setattr(async_module, "should_continue", lambda: False)
    monkeypatch.setattr(async_module, "logger", SimpleNamespace(debug=lambda *a, **k: None, error=lambda *a, **k: None))
    monkeypatch.setattr(async_module.AsyncLLM, "retry_decorator", lambda self, **kwargs: (lambda func: func))
    async def fake_acompletion(*args, **kwargs):
        return FakeResponse()

    monkeypatch.setattr(async_module, "litellm_acompletion", fake_acompletion, raising=False)


@pytest.mark.asyncio
async def test_async_completion_flow(monkeypatch: pytest.MonkeyPatch) -> None:
    _patch_async_env(monkeypatch)
    config = _make_config()
    llm = async_module.AsyncLLM(config=config, service_id="svc")
    llm._post_completion = lambda resp: None  # type: ignore[method-assign]
    llm.log_response = lambda resp: None  # type: ignore[method-assign]

    result = await llm.async_completion(messages=[{"role": "user", "content": "hi"}])
    assert result["choices"][0]["message"]["content"] == "content"

    # Exercise helper utilities
    parsed = llm._process_completion_args((None, [{"role": "user", "content": "msg"}]), {})
    assert parsed[0]["content"] == "msg"

    with pytest.raises(ValueError):
        llm._validate_messages([])

    kwargs = {}
    llm._configure_completion_params(kwargs)
    assert kwargs["reasoning_effort"] == "medium"


@pytest.mark.asyncio
async def test_async_completion_handles_exceptions(monkeypatch: pytest.MonkeyPatch) -> None:
    _patch_async_env(monkeypatch)
    config = _make_config()
    llm = async_module.AsyncLLM(config=config, service_id="svc")

    async def raise_completion(*args, **kwargs):
        raise RuntimeError("boom")

    llm._base_async_completion = raise_completion  # type: ignore[assignment]
    with pytest.raises(RuntimeError):
        await llm._execute_completion_with_cancellation(raise_completion, (), {"messages": []})


def _patch_stream_env(monkeypatch: pytest.MonkeyPatch) -> None:
    _patch_async_env(monkeypatch)
    monkeypatch.setattr(streaming_module.AsyncLLM, "__init__", async_module.AsyncLLM.__init__)
    monkeypatch.setattr(streaming_module.AsyncLLM, "retry_decorator", lambda self, **kwargs: (lambda func: func))
    monkeypatch.setattr(streaming_module, "logger", SimpleNamespace(debug=lambda *a, **k: None, error=lambda *a, **k: None))
    monkeypatch.setattr("forge.core.config.api_key_manager.APIKeyManager._extract_provider", lambda self, model: "openai", raising=False)
    monkeypatch.setattr("forge.core.config.api_key_manager.APIKeyManager._get_provider_key_from_env", lambda self, provider: None, raising=False)
    monkeypatch.setattr("forge.core.config.api_key_manager.APIKeyManager.validate_and_clean_completion_params", lambda self, model, params: params, raising=False)
    monkeypatch.setattr("forge.core.config.api_key_manager.APIKeyManager.get_api_key_for_model", lambda self, model, key: None, raising=False)
    monkeypatch.setattr("forge.core.config.api_key_manager.APIKeyManager.set_environment_variables", lambda self, model, key: None, raising=False)


@pytest.mark.asyncio
async def test_streaming_completion_flow(monkeypatch: pytest.MonkeyPatch) -> None:
    _patch_stream_env(monkeypatch)
    config = _make_config(base_url="https://example", api_version="v1", custom_llm_provider="custom")
    llm = streaming_module.StreamingLLM(config=config, service_id="svc")

    async def fake_generator(*args, **kwargs):
        yield {"choices": [{"delta": {"content": "chunk"}, "finish_reason": None}]}
        yield {"choices": [{"delta": {}, "finish_reason": "stop"}]}

    llm._base_async_streaming_completion = lambda *a, **k: fake_generator(*a, **k)  # type: ignore[assignment]
    llm._post_completion = lambda resp: None  # type: ignore[method-assign]
    completion_partial = llm._create_streaming_completion_partial()
    assert completion_partial.keywords["base_url"] == "https://example"
    assert completion_partial.keywords["api_version"] == "v1"
    assert completion_partial.keywords["custom_llm_provider"] == "custom"
    chunks = []
    async for chunk in llm.async_streaming_completion(messages=[{"role": "user", "content": "hi"}]):
        chunks.append(chunk)
    assert chunks[0]["choices"][0]["delta"]["content"] == "chunk"

    # Validate helper behavior
    messages = llm._process_streaming_messages((None, [{"role": "user", "content": "ping"}]), {})
    assert messages[0]["content"] == "ping"



@pytest.mark.asyncio
async def test_streaming_handles_cancellation(monkeypatch: pytest.MonkeyPatch) -> None:
    _patch_stream_env(monkeypatch)
    config = _make_config()

    async def cancel():
        return True

    llm = streaming_module.StreamingLLM(config=config, service_id="svc")
    llm.config.__dict__["on_cancel_requested_fn"] = cancel

    async def generator():
        yield {"choices": [{"delta": {}, "finish_reason": None}]}

    with pytest.raises(async_module.UserCancelledError):
        async for _ in llm._process_streaming_chunks(generator(), {}):
            pass


@pytest.mark.asyncio
async def test_streaming_wrapper_exception(monkeypatch: pytest.MonkeyPatch) -> None:
    _patch_stream_env(monkeypatch)
    config = _make_config()
    llm = streaming_module.StreamingLLM(config=config, service_id="svc")

    async def failing_generator(*args, **kwargs):
        raise RuntimeError("failure")

    llm._base_async_streaming_completion = failing_generator  # type: ignore[assignment]
    with pytest.raises(RuntimeError):
        async for _ in llm._async_streaming_completion_wrapper(messages=[{"role": "user", "content": "hi"}], stream=True):
            pass

