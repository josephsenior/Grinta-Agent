"""High-level tests covering `forge.llm.llm.LLM` behaviour."""

from __future__ import annotations

from types import SimpleNamespace

import pytest
from pydantic import SecretStr

from forge.core.config.llm_config import LLMConfig, suppress_llm_env_export
from forge.core.message import Message, TextContent
from forge.llm import llm as llm_module


class DummyLogger:
    def __init__(self) -> None:
        self.debug = lambda *args, **kwargs: None
        self.info = lambda *args, **kwargs: None
        self.warning = lambda *args, **kwargs: None
        self.error = lambda *args, **kwargs: None


class FakeResponse(dict):
    """Simple response object mimicking LiteLLM ModelResponse."""

    def __init__(self, cost: float = 0.3, include_hidden: bool = True) -> None:
        super().__init__(
            id="resp-1",
            usage={
                "prompt_tokens": 3,
                "completion_tokens": 2,
                "prompt_tokens_details": SimpleNamespace(cached_tokens=4),
                "model_extra": {"cache_creation_input_tokens": 5},
            },
        )
        message = SimpleNamespace(content="reply", tool_calls=[])
        self.choices = [SimpleNamespace(message=message)]
        if include_hidden:
            self._hidden_params = {
                "additional_headers": {"llm_provider-x-litellm-response-cost": str(cost)}
            }

    def model_dump(self):
        return {"dumped": True}


def _build_llm(monkeypatch: pytest.MonkeyPatch, *, include_hidden: bool = True, completion_cost=0.4):
    """Create an LLM instance with heavy dependencies patched out."""
    features = SimpleNamespace(
        supports_reasoning_effort=True,
        supports_prompt_cache=True,
        supports_stop_words=True,
        supports_function_calling=False,
    )

    monkeypatch.setattr(llm_module, "get_features", lambda model: features)
    monkeypatch.setattr(llm_module, "STOP_WORDS", ["STOP"])
    monkeypatch.setattr(llm_module, "convert_fncall_messages_to_non_fncall_messages", lambda messages, tools, add_in_context_learning_example: [{"role": "user", "content": "converted"}])
    monkeypatch.setattr(llm_module, "convert_non_fncall_messages_to_fncall_messages", lambda messages, tools: [{"content": "tool-call"}])

    last_call = {}

    def fake_completion(*args, **kwargs):
        last_call["kwargs"] = kwargs
        return FakeResponse(include_hidden=include_hidden)

    monkeypatch.setattr(llm_module, "litellm_completion", fake_completion)
    monkeypatch.setattr(llm_module, "litellm_completion_cost", lambda *args, **kwargs: completion_cost)
    monkeypatch.setattr(llm_module.LLM, "retry_decorator", lambda self, **kwargs: (lambda func: func))
    monkeypatch.setattr(llm_module, "logger", DummyLogger())
    monkeypatch.setattr(llm_module.litellm, "supports_vision", lambda model: True)
    monkeypatch.setattr(llm_module.litellm, "token_counter", lambda **kwargs: 7)
    monkeypatch.setattr(
        llm_module.litellm,
        "get_model_info",
        lambda model: {"max_input_tokens": 200, "max_output_tokens": 100},
    )

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

    response = llm.completion(messages=[{"role": "user", "content": "hello"}], tools=[{"name": "tool"}])
    kwargs = last_call["kwargs"]
    assert kwargs["messages"][0]["content"] == "converted"
    assert kwargs["stop"] == ["STOP"]

    # Response should be post-processed for mock tool calling
    assert response.choices[0].message.content == "tool-call"
    assert llm.metrics.accumulated_cost == pytest.approx(0.3)
    assert llm.metrics.token_usages[-1].prompt_tokens == 3
    assert llm.metrics.token_usages[-1].cache_read_tokens == 4
    assert llm.metrics.response_latencies, "Latency metrics should be recorded"
    assert llm.is_caching_prompt_active() is True
    assert llm.vision_is_active() is True
    assert llm.is_function_calling_active() is False

    message = Message(role="user", content=[TextContent(text="ping")])
    formatted = llm.format_messages_for_llm([message])
    formatted_content = formatted[0]["content"]
    if isinstance(formatted_content, list):
        assert any("ping" in str(part) for part in formatted_content)
    else:
        assert "ping" in formatted_content
    assert llm.get_token_count([{"role": "user", "content": "ping"}]) == 7


def test_completion_cost_fallback_disables_metrics(monkeypatch: pytest.MonkeyPatch) -> None:
    llm, _, _ = _build_llm(monkeypatch, include_hidden=False, completion_cost=0.5)

    def raise_cost(*args, **kwargs):
        raise RuntimeError("no cost")

    monkeypatch.setattr(llm_module, "litellm_completion_cost", raise_cost)

    response = FakeResponse(include_hidden=False)
    cost = llm._completion_cost(response)
    assert cost == 0.0
    assert llm.cost_metric_supported is False

