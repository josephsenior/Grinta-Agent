from __future__ import annotations

from typing import Any

import pytest
from pydantic import SecretStr

from forge.core.config import llm_config as llm_module
from forge.core.config.llm_config import LLMConfig, suppress_llm_env_export


class DummyAPIKeyManager:
    def __init__(self):
        self.get_calls: list[tuple[str, Any]] = []
        self.set_env_calls: list[tuple[str, Any]] = []

    def get_api_key_for_model(self, model: str, provided_key: SecretStr | None):
        self.get_calls.append((model, provided_key))
        return SecretStr("manager-key")

    def set_environment_variables(self, model: str, api_key: SecretStr | None):
        self.set_env_calls.append((model, api_key))

    def _extract_provider(self, model: str) -> str:
        return "openai"


class DummyProviderConfig:
    def __init__(self):
        self.env_var = "OPENAI_API_KEY"
        self.required_params = {"api_key"}
        self.optional_params = {"timeout"}
        self.forbidden_params = set()
        self.api_key_prefixes = ["sk-"]
        self.api_key_min_length = 5

    def validate_base_url(self, base_url: str | None) -> str | None:
        if not base_url:
            return None
        return base_url.rstrip("/")

    def is_param_allowed(self, param_name: str) -> bool:
        return param_name in self.optional_params


class DummyProviderManager:
    def __init__(self):
        self.config = DummyProviderConfig()

    def get_provider_config(self, provider: str):
        return self.config

    def validate_api_key_format(self, provider: str, api_key: str) -> bool:
        return True

    def get_environment_variable(self, provider: str) -> str | None:
        return self.config.env_var


@pytest.fixture()
def patched_managers(monkeypatch: pytest.MonkeyPatch):
    api_manager = DummyAPIKeyManager()
    provider_manager = DummyProviderManager()
    monkeypatch.setattr(llm_module, "api_key_manager", api_manager)
    monkeypatch.setattr(llm_module, "provider_config_manager", provider_manager)
    return api_manager, provider_manager


def test_llm_config_model_post_init_populates_key_and_base_url(patched_managers):
    api_manager, provider_manager = patched_managers
    config = LLMConfig(
        model="gpt-4o", base_url="https://example.com/", custom_llm_provider="custom"
    )
    assert config.api_key.get_secret_value() == "manager-key"
    assert config.base_url == "https://example.com"
    assert api_manager.set_env_calls and api_manager.set_env_calls[0][0] == "gpt-4o"
    assert config.reasoning_effort == "high"


def test_llm_config_respects_suppress_env_export(monkeypatch: pytest.MonkeyPatch):
    dummy_manager = DummyAPIKeyManager()
    monkeypatch.setattr(llm_module, "api_key_manager", dummy_manager)
    with suppress_llm_env_export():
        cfg = LLMConfig(model="gpt-4o", api_key=SecretStr("direct-key"))
    assert not dummy_manager.get_calls
    assert cfg.api_key.get_secret_value() == "direct-key"


def test_llm_config_sets_azure_defaults(
    monkeypatch: pytest.MonkeyPatch, patched_managers
):
    api_manager, _ = patched_managers
    cfg = LLMConfig(model="azure/gpt4", api_key=SecretStr("sk-azure-key"))
    assert cfg.api_version == "2024-12-01-preview"


def test_llm_config_reasoning_effort_not_overridden_for_gemini(
    monkeypatch: pytest.MonkeyPatch, patched_managers
):
    api_manager, _ = patched_managers
    cfg = LLMConfig(
        model="gemini-2.5-pro", api_key=SecretStr("google-key"), reasoning_effort=None
    )
    # gemini models keep explicit None (no default high)
    assert cfg.reasoning_effort is None


def test_suppress_llm_env_export_context_restores_flag():
    assert llm_module._SUPPRESS_ENV_EXPORT is False
    with suppress_llm_env_export():
        assert llm_module._SUPPRESS_ENV_EXPORT is True
    assert llm_module._SUPPRESS_ENV_EXPORT is False
