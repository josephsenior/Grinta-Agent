import pytest

from forge.core.config.provider_config import ProviderConfigurationManager


@pytest.fixture()
def manager():
    return ProviderConfigurationManager()


def test_validate_base_url_handles_routing(manager):
    openrouter = manager.get_provider_config("openrouter")
    assert openrouter.validate_base_url("https://example.com") is None
    openai = manager.get_provider_config("openai")
    assert openai.validate_base_url("https://api.openai.com") == "https://api.openai.com"
    assert openai.validate_base_url("invalid") is None


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


def test_validate_api_key_format_warnings(manager, caplog):
    assert manager.validate_api_key_format("openai", "sk-valid-12345678901234567890")
    assert not manager.validate_api_key_format("openai", "short")


def test_get_environment_variable(manager):
    assert manager.get_environment_variable("openai") == "OPENAI_API_KEY"
    assert manager.get_environment_variable("unknown") is None

