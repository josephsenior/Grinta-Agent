import pytest

from forge.core.config.provider_config import (
    ProviderConfigurationManager,
    ProviderConfig,
)


@pytest.fixture()
def manager():
    return ProviderConfigurationManager()


def test_validate_base_url_handles_routing(manager):
    openrouter = manager.get_provider_config("openrouter")
    assert openrouter.validate_base_url("https://example.com") is None
    openai = manager.get_provider_config("openai")
    assert (
        openai.validate_base_url("https://api.openai.com") == "https://api.openai.com"
    )
    assert openai.validate_base_url("invalid") is None
    assert openai.validate_base_url("") is None


def test_validate_base_url_unknown_provider(manager):
    unknown = manager.get_provider_config("nonexistent")
    assert unknown.name == "unknown"
    assert unknown.validate_base_url("http://example.com") == "http://example.com"


def test_validate_and_clean_params_removes_forbidden(manager):
    params = {
        "api_key": "sk-test-1234567890",
        "base_url": "https://router",
        "custom_llm_provider": "custom",
        "extra": "value",
    }
    cleaned = manager.validate_and_clean_params("openrouter", params)
    assert "base_url" not in cleaned
    assert cleaned["extra"] == "value"


def test_validate_and_clean_params_missing_required_logs_warning(manager, caplog):
    params = {"timeout": 30}
    cleaned = manager.validate_and_clean_params("openai", params)
    assert cleaned == {"timeout": 30}


def test_validate_and_clean_params_base_url_cleared(manager, caplog):
    provider = ProviderConfig(
        name="custom", handles_own_routing=True, optional_params={"base_url", "model"}
    )
    manager._provider_configs["custom"] = provider
    cleaned = manager.validate_and_clean_params(
        "custom", {"base_url": "https://example.com", "model": "m"}
    )
    assert "base_url" not in cleaned
    assert cleaned["model"] == "m"


def test_validate_api_key_format_warnings(manager, caplog):
    assert manager.validate_api_key_format("openai", "sk-valid-12345678901234567890")
    assert not manager.validate_api_key_format("openai", "short")
    assert manager.validate_api_key_format("unknown", None)
    assert manager.validate_api_key_format("openrouter", "zzzzzzzzzzzzzzzzzzzz")


def test_validate_api_key_format_prefix_warning(manager, caplog):
    caplog.clear()
    assert manager.validate_api_key_format("openai", "pk-other-prefix-123456789012345")


def test_get_environment_variable(manager):
    assert manager.get_environment_variable("openai") == "OPENAI_API_KEY"
    assert manager.get_environment_variable("unknown") is None
