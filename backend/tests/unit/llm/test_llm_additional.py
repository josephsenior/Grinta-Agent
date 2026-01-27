"""Additional coverage-oriented tests for `forge.llm.llm`."""

from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace
from typing import Any
from unittest.mock import MagicMock

import pytest
from pydantic import SecretStr

from forge.core.config.llm_config import LLMConfig, suppress_llm_env_export
from forge.core.message import Message, TextContent
from forge.llm import llm as llm_module
from forge.llm.direct_clients import LLMResponse
from forge.llm.model_features import ModelFeatures


class DummyLogger:
    def __init__(self) -> None:
        self.debug_messages: list[str] = []
        self.warning_messages: list[str] = []
        self.error_messages: list[str] = []

    def debug(self, message: str, *args) -> None:
        if args:
            message = message % args
        self.debug_messages.append(message)

    def warning(self, message: str, *args) -> None:
        if args:
            message = message % args
        self.warning_messages.append(message)

    def error(self, message: str, *args) -> None:
        if args:
            message = message % args
        self.error_messages.append(message)

    def info(self, message: str, *args) -> None:
        pass

    def isEnabledFor(self, level: int) -> bool:  # noqa: N802
        return True


class FakeResponse(dict):
    def __init__(self, *, content: str = "reply") -> None:
        super().__init__(id="resp-1")
        self.choices = [
            SimpleNamespace(
                message=SimpleNamespace(
                    content=content,
                    tool_calls=[
                        SimpleNamespace(
                            function=SimpleNamespace(name="foo", arguments="{}")
                        )
                    ],
                )
            )
        ]

    def get(self, key: str, default: Any = None) -> Any:
        if key == "id":
            return "resp-1"
        return super().get(key, default)

    def model_dump(self):
        return {"content": self.choices[0].message.content}


def _patch_llm_env(monkeypatch: pytest.MonkeyPatch) -> None:
    """Patch expensive dependencies so we can instantiate LLM safely."""
    features = ModelFeatures(
        supports_reasoning_effort=True,
        supports_prompt_cache=True,
        supports_stop_words=True,
        supports_function_calling=True,
    )
    monkeypatch.setattr(llm_module, "get_features", lambda model: features)
    
    # Mock get_direct_client
    mock_client = MagicMock()
    mock_client.completion.return_value = LLMResponse(
        content="reply",
        model="gemini-2.5-pro",
        usage={"prompt_tokens": 3, "completion_tokens": 2},
        id="resp-1"
    )
    monkeypatch.setattr(llm_module, "get_direct_client", lambda model, api_key, base_url: mock_client)
    
    monkeypatch.setattr(llm_module, "logger", DummyLogger())

    monkeypatch.setattr(
        llm_module.LLM, "retry_decorator", lambda self, **kwargs: (lambda func: func)
    )


def make_config(**overrides: Any) -> LLMConfig:
    defaults = dict(
        model="gemini-2.5-pro",
        api_key=None,
        log_completions=False,
        caching_prompt=True,
        disable_vision=False,
        reasoning_effort="medium",
        max_output_tokens=50,
    )
    defaults.update(overrides)
    with suppress_llm_env_export():
        return LLMConfig(**defaults)


def build_llm(monkeypatch: pytest.MonkeyPatch, **config_overrides: Any):
    _patch_llm_env(monkeypatch)
    config = make_config(**config_overrides)
    return llm_module.LLM(config=config, service_id="svc-123")


def test_handle_Forge_model(monkeypatch: pytest.MonkeyPatch) -> None:
    llm = build_llm(monkeypatch, model="Forge/my-model")
    assert llm.config.model == "Forge/my-model"


def test_extract_api_key_manager_fallback(monkeypatch: pytest.MonkeyPatch) -> None:
    _patch_llm_env(monkeypatch)
    with suppress_llm_env_export():
        config = LLMConfig(model="gpt-4o", api_key=None)
    manager = SimpleNamespace(
        _extract_provider=lambda model: "openai",
        _get_provider_key_from_env=lambda provider: "",
        get_api_key_for_model=lambda model, key: SimpleNamespace(
            get_secret_value=lambda: "sk-manager"
        ),
    )
    monkeypatch.setattr("forge.core.config.api_key_manager.api_key_manager", manager)
    llm = llm_module.LLM(config=config, service_id="svc")
    assert llm._extract_api_key() == "sk-manager"


def test_format_messages_for_llm(monkeypatch: pytest.MonkeyPatch) -> None:
    llm = build_llm(monkeypatch)
    message = Message(role="user", content=[TextContent(text="hello")])
    formatted = llm.format_messages_for_llm(message)
    assert formatted[0]["role"] == "user"
    assert formatted[0]["content"] == "hello"


def test_retry_decorator_function() -> None:
    retries = []

    @llm_module.retry_decorator(num_retries=2, retry_exceptions=(ValueError,))
    def flaky():
        retries.append(1)
        if len(retries) < 2:
            raise ValueError("fail")
        return "ok"

    assert flaky() == "ok"


def test_get_token_count(monkeypatch: pytest.MonkeyPatch) -> None:
    llm = build_llm(monkeypatch)
    messages = [{"role": "user", "content": "hello world"}]
    # "hello world" is 11 chars. 11 // 4 = 2
    assert llm.get_token_count(messages) == 2


def test_vision_is_active(monkeypatch: pytest.MonkeyPatch) -> None:
    llm = build_llm(monkeypatch, disable_vision=True)
    assert llm.vision_is_active() is False
    
    llm2 = build_llm(monkeypatch, disable_vision=False)
    assert llm2.vision_is_active() is True

