"""High-level tests covering `forge.llm.llm.LLM` behaviour."""

from __future__ import annotations

from types import SimpleNamespace
from typing import Any
from unittest.mock import MagicMock

import pytest
from pydantic import SecretStr

from forge.core.config.llm_config import LLMConfig, suppress_llm_env_export
from forge.core.message import Message, TextContent
from forge.llm import llm as llm_module
from forge.llm.direct_clients import LLMResponse


class DummyLogger:
    def __init__(self) -> None:
        self.debug = lambda *args, **kwargs: None
        self.info = lambda *args, **kwargs: None
        self.warning = lambda *args, **kwargs: None
        self.error = lambda *args, **kwargs: None


class FakeResponse:
    """Simple response object mimicking LLMResponse."""

    def __init__(self, cost: float = 0.3) -> None:
        self.content = "reply"
        self.model = "mock-model"
        self.usage = {
            "prompt_tokens": 3,
            "completion_tokens": 2,
            "cache_read_tokens": 4,
            "cache_write_tokens": 5,
        }
        self.id = "resp-1"
        self.finish_reason = "stop"

    def to_dict(self):
        return {
            "choices": [
                {
                    "message": {"content": self.content, "role": "assistant"},
                    "finish_reason": self.finish_reason,
                }
            ],
            "usage": self.usage,
            "id": self.id,
            "model": self.model,
        }


def _build_llm(
    monkeypatch: pytest.MonkeyPatch, *, completion_cost=0.4
):
    """Create an LLM instance with heavy dependencies patched out."""
    features = SimpleNamespace(
        supports_reasoning_effort=True,
        supports_prompt_cache=True,
        supports_stop_words=True,
        supports_function_calling=False,
        max_input_tokens=1000,
        max_output_tokens=500,
    )

    monkeypatch.setattr(llm_module, "get_features", lambda model: features)
    
    last_call = {}

    class FakeClient:
        def __init__(self, model, api_key, base_url=None):
            self.model = model

        def completion(self, messages, **kwargs):
            last_call["messages"] = messages
            last_call["kwargs"] = kwargs
            return FakeResponse()

        async def acompletion(self, messages, **kwargs):
            last_call["messages"] = messages
            last_call["kwargs"] = kwargs
            return FakeResponse()

        def get_completion_cost(self, prompt_tokens, completion_tokens, config=None):
            return completion_cost

    monkeypatch.setattr(llm_module, "get_direct_client", FakeClient)
    monkeypatch.setattr(
        llm_module.LLM, "retry_decorator", lambda self, **kwargs: (lambda func: func)
    )
    monkeypatch.setattr(llm_module, "logger", DummyLogger())

    with suppress_llm_env_export():
        config = LLMConfig(
            model="gemini-2.5-pro",
            api_key=SecretStr("sk-test"),
            log_completions=False,
            caching_prompt=True,
            disable_vision=False,
            reasoning_effort="medium",
            max_output_tokens=50,
        )

    llm = llm_module.LLM(config=config, service_id="svc-1")
    return llm, last_call, features


def test_llm_completion_flow(monkeypatch: pytest.MonkeyPatch) -> None:
    llm, last_call, features = _build_llm(monkeypatch, completion_cost=0.4)

    response = llm.completion(
        messages=[{"role": "user", "content": "hello"}], tools=[{"name": "tool"}]     
    )
    
    assert response["choices"][0]["message"]["content"] == "reply"
    assert last_call["messages"][0]["content"] == "hello"
    assert last_call["kwargs"]["tools"] == [{"name": "tool"}]


def test_completion_cost_fallback(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    llm, _, _ = _build_llm(monkeypatch, completion_cost=0.0)
    
    resp = FakeResponse()
    # completion returns response.to_dict()
    # The cost calculation is done inside completion() and added to metrics
    
    llm.completion(messages=[{"role": "user", "content": "hi"}])
    
    # Check metrics
    assert llm.metrics.accumulated_cost == 0.0
