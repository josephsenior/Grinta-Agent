import os
from typing import Any, Dict

import pytest
from pydantic import SecretStr

from forge.core.config import api_key_manager as api_key_module
from forge.core.config.api_key_manager import APIKeyManager


class DummyProviderConfig:
    def __init__(
        self,
        env_var="OPENAI_API_KEY",
        required_params=None,
        prefixes=None,
        min_length=5,
    ):
        self.env_var = env_var
        self.required_params = required_params or {"api_key"}
        self.optional_params = set()
        self.forbidden_params = set()
        self.api_key_prefixes = prefixes or ["sk-"]
        self.api_key_min_length = min_length
        self.handles_own_routing = False
        self.requires_protocol = True

    def validate_base_url(self, base_url):
        return base_url

    def is_param_allowed(self, param_name: str) -> bool:
        return param_name in self.optional_params or param_name in self.required_params


class DummyProviderManager:
    def __init__(self, config: DummyProviderConfig):
        self.config = config
        self.format_calls: list[tuple[str, str]] = []
        self.providers_requested: list[str] = []

    def get_provider_config(self, provider: str):
        self.providers_requested.append(provider)
        return self.config

    def validate_api_key_format(self, provider: str, api_key: str) -> bool:
        self.format_calls.append((provider, api_key))
        return True

    def get_environment_variable(self, provider: str) -> str | None:
        if provider == "openai":
            return self.config.env_var
        return None


class FlexibleProviderManager:
    def __init__(self, configs: dict[str, DummyProviderConfig]):
        self.configs = configs
        self.validate_calls: list[tuple[str, str]] = []
        self.cleaned_params: dict[str, Any] = {}

    def get_provider_config(self, provider: str):
        return self.configs.get(provider, self.configs["default"])

    def validate_api_key_format(self, provider: str, api_key: str) -> bool:
        self.validate_calls.append((provider, api_key))
        return True

    def get_environment_variable(self, provider: str) -> str | None:
        config = self.get_provider_config(provider)
        return config.env_var

    def validate_and_clean_params(
        self, provider: str, params: Dict[str, Any]
    ) -> Dict[str, Any]:
        self.cleaned_params = {k: v for k, v in params.items() if v is not None}
        return self.cleaned_params


@pytest.fixture()
def dummy_manager(monkeypatch: pytest.MonkeyPatch):
    manager = DummyProviderManager(DummyProviderConfig())
    monkeypatch.setattr(api_key_module, "provider_config_manager", manager)
    return manager


def test_get_api_key_for_model_prefers_provided_key(dummy_manager):
    manager = APIKeyManager()
    provided = SecretStr("sk-provided-abcdef")
    result = manager.get_api_key_for_model("gpt-4o", provided_key=provided)
    assert result is provided


def test_get_api_key_for_model_uses_provided_fallback(
    monkeypatch: pytest.MonkeyPatch, dummy_manager
):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    manager = APIKeyManager()
    provided = SecretStr("not-a-matching-prefix-but-long")
    result = manager.get_api_key_for_model("gpt-4o", provided_key=provided)
    assert result is provided


def test_get_api_key_for_model_reads_environment(
    monkeypatch: pytest.MonkeyPatch, dummy_manager
):
    monkeypatch.setenv("OPENAI_API_KEY", "sk-env-1234567890")
    manager = APIKeyManager()
    result = manager.get_api_key_for_model("gpt-4o")
    assert isinstance(result, SecretStr)
    assert result.get_secret_value() == "sk-env-1234567890"


def test_get_api_key_for_model_missing_returns_none(
    monkeypatch: pytest.MonkeyPatch, dummy_manager
):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    manager = APIKeyManager()
    assert manager.get_api_key_for_model("gpt-4o") is None


def test_set_environment_variables_sets_expected_env(
    monkeypatch: pytest.MonkeyPatch, dummy_manager
):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.delenv("LLM_API_KEY", raising=False)
    manager = APIKeyManager()
    key = SecretStr("sk-from-manager-12345")
    manager.set_environment_variables("gpt-4o", key)
    assert os.environ["OPENAI_API_KEY"] == "sk-from-manager-12345"
    assert os.environ["LLM_API_KEY"] == "sk-from-manager-12345"
    assert ("openai", "sk-from-manager-12345") in dummy_manager.format_calls


def test_set_environment_variables_no_key_required(monkeypatch: pytest.MonkeyPatch):
    config = DummyProviderConfig(env_var=None, required_params=set())
    provider_manager = FlexibleProviderManager({"default": config})
    monkeypatch.setattr(api_key_module, "provider_config_manager", provider_manager)
    manager = APIKeyManager()
    manager.set_environment_variables("custom-model", None)
    assert provider_manager.validate_calls == []


def test_set_environment_variables_missing_key_returns(monkeypatch: pytest.MonkeyPatch):
    config = DummyProviderConfig(env_var="CUSTOM_API_KEY")
    provider_manager = FlexibleProviderManager({"default": config})
    monkeypatch.setattr(api_key_module, "provider_config_manager", provider_manager)
    manager = APIKeyManager()
    monkeypatch.delenv("CUSTOM_API_KEY", raising=False)
    monkeypatch.delenv("LLM_API_KEY", raising=False)
    manager.set_environment_variables("custom-model", None)
    assert "CUSTOM_API_KEY" not in os.environ


def test_set_environment_variables_google_sets_extra(monkeypatch: pytest.MonkeyPatch):
    google_config = DummyProviderConfig(env_var="GEMINI_API_KEY")
    provider_manager = FlexibleProviderManager(
        {"default": DummyProviderConfig(), "google": google_config}
    )
    monkeypatch.setattr(api_key_module, "provider_config_manager", provider_manager)
    manager = APIKeyManager()
    key = SecretStr("AIza-google-key")
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    monkeypatch.delenv("GOOGLE_API_KEY", raising=False)
    monkeypatch.delenv("LLM_API_KEY", raising=False)
    manager.set_environment_variables("gemini-pro", key)
    assert os.environ["GEMINI_API_KEY"] == "AIza-google-key"
    assert os.environ["GOOGLE_API_KEY"] == "AIza-google-key"
    assert os.environ["LLM_API_KEY"] == "AIza-google-key"


@pytest.mark.parametrize(
    "model,expected",
    [
        ("openrouter/claude", "openrouter"),
        ("claude-3-5-sonnet", "anthropic"),
        ("gemini-2.5-pro", "google"),
        ("unknown-model", "unknown"),
    ],
)
def test_extract_provider_variants(model, expected):
    manager = APIKeyManager()
    assert manager._extract_provider(model) == expected


def test_is_correct_provider_key_patterns():
    manager = APIKeyManager()
    assert manager._is_correct_provider_key(SecretStr("sk-ant-1234abcd"), "anthropic")
    assert not manager._is_correct_provider_key(SecretStr("short"), "openai")


def test_is_correct_provider_key_default_true():
    manager = APIKeyManager()
    assert manager._is_correct_provider_key(SecretStr("some-key"), "unknown-provider")


def test_get_provider_key_from_env_fallback(
    monkeypatch: pytest.MonkeyPatch, dummy_manager
):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.setenv("LLM_API_KEY", "sk-fallback")
    manager = APIKeyManager()
    assert manager._get_provider_key_from_env("unknown") == "sk-fallback"


def test_validate_and_clean_completion_params(monkeypatch: pytest.MonkeyPatch):
    provider_manager = FlexibleProviderManager({"default": DummyProviderConfig()})
    monkeypatch.setattr(api_key_module, "provider_config_manager", provider_manager)
    manager = APIKeyManager()
    params = {"temperature": 0.2, "unused": None}
    cleaned = manager.validate_and_clean_completion_params("gpt-4o", params)
    assert cleaned == {"temperature": 0.2}
    assert provider_manager.cleaned_params == cleaned
