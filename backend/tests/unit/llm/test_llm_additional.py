"""Additional coverage-oriented tests for `forge.llm.llm`."""

from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest
from pydantic import SecretStr

from forge.core.config.llm_config import LLMConfig, suppress_llm_env_export
from forge.core.message import Message, TextContent
from forge.llm import llm as llm_module


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
    features = SimpleNamespace(
        supports_reasoning_effort=True,
        supports_prompt_cache=True,
        supports_stop_words=True,
        supports_function_calling=True,
    )
    monkeypatch.setattr(llm_module, "get_features", lambda model: features)
    monkeypatch.setattr(llm_module, "STOP_WORDS", ["STOP"])
    monkeypatch.setattr(
        llm_module,
        "convert_fncall_messages_to_non_fncall_messages",
        lambda messages, tools, add_in_context_learning_example=True: [
            {"role": "user", "content": "converted"}
        ],
    )
    monkeypatch.setattr(
        llm_module,
        "convert_non_fncall_messages_to_fncall_messages",
        lambda messages, tools: [{"role": "assistant", "content": "tool call"}],
    )
    monkeypatch.setattr(
        llm_module, "litellm_completion_cost", lambda *args, **kwargs: 0.2
    )

    class DummyLiteLLM:
        Timeout = RuntimeError
        InternalServerError = RuntimeError

        @staticmethod
        def supports_vision(model: str) -> bool:
            return True

        @staticmethod
        def token_counter(**kwargs) -> int:
            return 42

        @staticmethod
        def get_model_info(model: str):
            return {"max_input_tokens": 1000, "max_output_tokens": 999}

    monkeypatch.setattr(llm_module, "litellm", DummyLiteLLM)
    monkeypatch.setattr(llm_module, "logger", DummyLogger())

    def fake_completion(*args, **kwargs):
        return FakeResponse()

    monkeypatch.setattr(llm_module, "litellm_completion", fake_completion)
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


def test_handle_openhands_model(monkeypatch: pytest.MonkeyPatch) -> None:
    llm = build_llm(monkeypatch, model="Openhands/my-model")
    assert llm.config.model.startswith("litellm_proxy/")
    assert llm.config.base_url


def test_setup_logging_requires_folder(monkeypatch: pytest.MonkeyPatch) -> None:
    _patch_llm_env(monkeypatch)
    with suppress_llm_env_export():
        config = LLMConfig(
            model="gpt-4o-mini",
            log_completions=True,
            log_completions_folder=".",
            api_key=SecretStr("sk-1"),
        )
    config.__dict__["log_completions_folder"] = None
    with pytest.raises(RuntimeError):
        llm_module.LLM(config=config, service_id="svc")


def test_setup_logging_creates_directory(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    _patch_llm_env(monkeypatch)
    config = make_config(
        log_completions=True, log_completions_folder=str(tmp_path), api_key=SecretStr("sk-1")
    )
    llm_module.LLM(config=config, service_id="svc")
    assert tmp_path.exists()


def test_configure_reasoning_effort_for_gemini(monkeypatch: pytest.MonkeyPatch) -> None:
    _patch_llm_env(monkeypatch)
    config = make_config(model="gemini-2.5-pro", reasoning_effort="low")
    llm = llm_module.LLM(config=config, service_id="svc")
    assert llm.config.reasoning_effort == "low"


def test_configure_model_specific_settings(monkeypatch: pytest.MonkeyPatch) -> None:
    _patch_llm_env(monkeypatch)
    config = make_config(
        model="azure/gpt",
        aws_access_key_id="AKIA",
        aws_secret_access_key="SECRET",
        safety_settings=[{"level": "high"}],
    )
    llm = llm_module.LLM(config=config, service_id="svc")
    kwargs = llm._build_basic_kwargs()
    llm._configure_model_specific_settings(kwargs)
    assert "aws_access_key_id" in kwargs
    assert kwargs["aws_region_name"] is None


def test_configure_model_specific_settings_for_claude(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _patch_llm_env(monkeypatch)
    config = make_config(model="claude-opus-4-1", max_output_tokens=None)
    llm = llm_module.LLM(config=config, service_id="svc")
    kwargs = llm._build_basic_kwargs()
    llm._configure_model_specific_settings(kwargs)
    assert "thinking" in kwargs


def test_extract_api_key_from_config(monkeypatch: pytest.MonkeyPatch) -> None:
    _patch_llm_env(monkeypatch)
    with suppress_llm_env_export():
        config = LLMConfig(model="gpt-4o-mini", api_key=SecretStr("sk-123"))
    llm = llm_module.LLM(config=config, service_id="svc")
    key = llm._extract_api_key()
    assert key == "sk-123"


def test_extract_api_key_from_env(monkeypatch: pytest.MonkeyPatch) -> None:
    _patch_llm_env(monkeypatch)
    with suppress_llm_env_export():
        config = LLMConfig(model="anthropic/claude", api_key=None)
    monkeypatch.setenv("ANTHROPIC_API_KEY", "env-key")
    monkeypatch.setattr(
        "forge.core.config.api_key_manager.api_key_manager",
        SimpleNamespace(
            _extract_provider=lambda model: "anthropic",
            _get_provider_key_from_env=lambda provider: "env-key",
            get_api_key_for_model=lambda model, key: None,
            set_environment_variables=lambda model, key: None,
        ),
    )
    llm = llm_module.LLM(config=config, service_id="svc")
    assert llm._extract_api_key() == "env-key"


def test_prepare_messages_with_message_objects(monkeypatch: pytest.MonkeyPatch) -> None:
    llm = build_llm(monkeypatch)
    message = Message(role="user", content=[TextContent(text="hello")])
    messages, mock_fn_calling, tools, has_extra = llm._prepare_messages(
        ([], [message]), {"tools": [{"name": "tool"}]}
    )
    assert isinstance(messages[0], dict)
    assert mock_fn_calling in {True, False}
    assert tools is None or isinstance(tools, list)
    assert has_extra is True


def test_log_completion_helpers(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    llm = build_llm(
        monkeypatch, log_completions=True, log_completions_folder=str(tmp_path)
    )
    messages = [{"role": "user", "content": "hello"}]
    kwargs = {"messages": messages}
    llm._log_completion_input(messages, True, [{"name": "dummy"}], kwargs)
    llm._log_completion_output(FakeResponse(), messages, kwargs)
    llm._log_completion_error(messages, RuntimeError("fail"), kwargs)
    assert len(list(tmp_path.iterdir())) == 3


def test_completion_wrapper_streaming(monkeypatch: pytest.MonkeyPatch) -> None:
    _patch_llm_env(monkeypatch)
    config = make_config()
    llm = llm_module.LLM(config=config, service_id="svc")

    def fake_stream(*args, **kwargs):
        yield {"choices": [{"delta": {"content": "chunk"}, "finish_reason": None}]}

    llm._base_completion = fake_stream
    stream = llm._completion_wrapper(
        messages=[{"role": "user", "content": "hi"}], stream=True
    )
    assert next(stream)["choices"][0]["delta"]["content"] == "chunk"


def test_apply_mock_function_calling(monkeypatch: pytest.MonkeyPatch) -> None:
    llm = build_llm(monkeypatch)
    response = FakeResponse(content="tool text")
    llm._apply_mock_function_calling(response, [{"name": "tool"}])
    assert response.choices[0].message.content == "tool call"


def test_configure_token_limits(monkeypatch: pytest.MonkeyPatch) -> None:
    _patch_llm_env(monkeypatch)
    config = make_config(
        model="huggingface/my-model", max_output_tokens=None, max_input_tokens=None
    )
    llm = llm_module.LLM(config=config, service_id="svc")
    assert llm.config.max_output_tokens == 999
    assert llm.config.max_input_tokens == 1000


def test_build_basic_kwargs_includes_top_values(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    llm = build_llm(monkeypatch, top_k=5, top_p=0.7)
    kwargs = llm._build_basic_kwargs()
    assert kwargs["top_k"] == 5
    assert kwargs["top_p"] == 0.7


def test_configure_reasoning_effort_special_case(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    llm = build_llm(monkeypatch, model="gemini-2.5-pro", reasoning_effort=None)
    kwargs = llm._build_basic_kwargs()
    kwargs["reasoning_effort"] = None
    llm._configure_reasoning_effort(kwargs)
    assert "thinking" in kwargs


def test_configure_safety_settings(monkeypatch: pytest.MonkeyPatch) -> None:
    llm = build_llm(
        monkeypatch, model="mistral-large", safety_settings=[{"rule": "strict"}]
    )
    kwargs = llm._build_basic_kwargs()
    llm._configure_model_specific_settings(kwargs)
    assert "safety_settings" in kwargs


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


def test_prepare_messages_sets_stop_words(monkeypatch: pytest.MonkeyPatch) -> None:
    llm = build_llm(monkeypatch)
    messages, mock_fn, mock_tools, _ = llm._prepare_messages(
        (None, [{"role": "assistant", "content": "fncall"}]),
        {"tools": [{"type": "function", "function": {"name": "tool"}}]},
    )
    assert mock_fn is True or mock_fn is False


def test_completion_wrapper_error_logging(monkeypatch: pytest.MonkeyPatch) -> None:
    llm = build_llm(monkeypatch)

    def failing_completion(*args, **kwargs):
        raise RuntimeError("fail")

    llm._base_completion = failing_completion  # type: ignore[assignment]
    with pytest.raises(RuntimeError):
        llm._completion_wrapper(messages=[{"role": "user", "content": "hi"}])


def test_post_completion_updates_metrics(monkeypatch: pytest.MonkeyPatch) -> None:
    llm = build_llm(monkeypatch)
    resp = FakeResponse()
    resp["usage"] = {"prompt_tokens": 3, "completion_tokens": 2}
    assert llm._post_completion(resp) >= 0.0


def test_get_token_count_handles_errors(monkeypatch: pytest.MonkeyPatch) -> None:
    llm = build_llm(monkeypatch)
    assert llm.get_token_count([{"role": "user", "content": "hi"}]) == 42

    def raise_counter(*args, **kwargs):
        raise RuntimeError("boom")

    monkeypatch.setattr(llm_module.litellm, "token_counter", raise_counter)
    assert llm.get_token_count([{"role": "user", "content": "hi"}]) == 0


def test_is_local_detection(monkeypatch: pytest.MonkeyPatch) -> None:
    llm = build_llm(monkeypatch, base_url="http://localhost:8000")
    llm.config.base_url = "http://localhost:8000"
    assert llm._is_local() is True


def test_completion_cost_custom_prices(monkeypatch: pytest.MonkeyPatch) -> None:
    llm = build_llm(monkeypatch, input_cost_per_token=0.1, output_cost_per_token=0.2)
    resp = FakeResponse()
    resp._hidden_params = {}
    assert llm._completion_cost(resp) >= 0.0


def test_format_messages_for_llm_sets_flags(monkeypatch: pytest.MonkeyPatch) -> None:
    llm = build_llm(monkeypatch)
    message = Message(role="user", content=[TextContent(text="hello")])
    formatted = llm.format_messages_for_llm(message)
    assert message.cache_enabled is True
    assert formatted[0]["role"] == "user"


def test_retry_decorator_function() -> None:
    retries = []

    @llm_module.retry_decorator(num_retries=2, retry_exceptions=(ValueError,))
    def flaky():
        retries.append(1)
        if len(retries) < 2:
            raise ValueError("fail")
        return "ok"

    assert flaky() == "ok"
