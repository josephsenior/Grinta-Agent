import pathlib
import pytest
from forge.core.config import ForgeConfig
from forge.core.config.utils import load_from_toml


@pytest.fixture
def default_config(monkeypatch):
    yield ForgeConfig()


@pytest.fixture
def generic_llm_toml(tmp_path: pathlib.Path) -> str:
    """Fixture to create a generic LLM TOML configuration with all custom LLMs.

    providing mandatory 'model' and 'api_key', and testing fallback to the generic section values
    for other attributes like 'num_retries'.
    """
    toml_content = '\n[core]\nworkspace_base = "./workspace"\n\n[llm]\nmodel = "base-model"\napi_key = "base-api-key"\nnum_retries = 3\n\n[llm.custom1]\nmodel = "custom-model-1"\napi_key = "custom-api-key-1"\n# \'num_retries\' is not overridden and should fallback to the value from [llm]\n\n[llm.custom2]\nmodel = "custom-model-2"\napi_key = "custom-api-key-2"\nnum_retries = 5  # Overridden value\n\n[llm.custom3]\nmodel = "custom-model-3"\napi_key = "custom-api-key-3"\n# No overrides for additional attributes\n    '
    toml_file = tmp_path / "llm_config.toml"
    toml_file.write_text(toml_content)
    return str(toml_file)


def test_load_from_toml_llm_with_fallback(
    default_config: ForgeConfig, generic_llm_toml: str
) -> None:
    """Test that custom LLM configurations fallback non-overridden attributes.

    like 'num_retries' from the generic [llm] section.
    """
    load_from_toml(default_config, generic_llm_toml)
    generic_llm = default_config.get_llm_config("llm")
    assert generic_llm.model == "base-model"
    assert generic_llm.api_key.get_secret_value() == "base-api-key"
    assert generic_llm.num_retries == 3
    custom1 = default_config.get_llm_config("custom1")
    assert custom1.model == "custom-model-1"
    assert custom1.api_key.get_secret_value() == "custom-api-key-1"
    assert custom1.num_retries == 3
    custom2 = default_config.get_llm_config("custom2")
    assert custom2.model == "custom-model-2"
    assert custom2.api_key.get_secret_value() == "custom-api-key-2"
    assert custom2.num_retries == 5
    custom3 = default_config.get_llm_config("custom3")
    assert custom3.model == "custom-model-3"
    assert custom3.api_key.get_secret_value() == "custom-api-key-3"
    assert custom3.num_retries == 3


def test_load_from_toml_llm_custom_overrides_all(
    default_config: ForgeConfig, tmp_path: pathlib.Path
) -> None:
    """Test that a custom LLM can fully override all attributes from the generic [llm] section."""
    toml_content = '\n[core]\nworkspace_base = "./workspace"\n\n[llm]\nmodel = "base-model"\napi_key = "base-api-key"\nnum_retries = 3\n\n[llm.custom_full]\nmodel = "full-custom-model"\napi_key = "full-custom-api-key"\nnum_retries = 10\n    '
    toml_file = tmp_path / "full_override_llm.toml"
    toml_file.write_text(toml_content)
    load_from_toml(default_config, str(toml_file))
    generic_llm = default_config.get_llm_config("llm")
    assert generic_llm.model == "base-model"
    assert generic_llm.api_key.get_secret_value() == "base-api-key"
    assert generic_llm.num_retries == 3
    custom_full = default_config.get_llm_config("custom_full")
    assert custom_full.model == "full-custom-model"
    assert custom_full.api_key.get_secret_value() == "full-custom-api-key"
    assert custom_full.num_retries == 10


def test_load_from_toml_llm_custom_partial_override(
    default_config: ForgeConfig, generic_llm_toml: str
) -> None:
    """Test that custom LLM configurations can partially override attributes.

    from the generic [llm] section while inheriting others.
    """
    load_from_toml(default_config, generic_llm_toml)
    custom1 = default_config.get_llm_config("custom1")
    assert custom1.model == "custom-model-1"
    assert custom1.api_key.get_secret_value() == "custom-api-key-1"
    assert custom1.num_retries == 3
    custom2 = default_config.get_llm_config("custom2")
    assert custom2.model == "custom-model-2"
    assert custom2.api_key.get_secret_value() == "custom-api-key-2"
    assert custom2.num_retries == 5


def test_load_from_toml_llm_custom_no_override(
    default_config: ForgeConfig, generic_llm_toml: str
) -> None:
    """Test that custom LLM configurations with no additional overrides.

    inherit all non-specified attributes from the generic [llm] section.
    """
    load_from_toml(default_config, generic_llm_toml)
    custom3 = default_config.get_llm_config("custom3")
    assert custom3.model == "custom-model-3"
    assert custom3.api_key.get_secret_value() == "custom-api-key-3"
    assert custom3.num_retries == 3


def test_load_from_toml_llm_missing_generic(
    default_config: ForgeConfig, tmp_path: pathlib.Path
) -> None:
    """Test that custom LLM configurations without a generic [llm] section.

    use only their own attributes and fallback to defaults for others.
    """
    toml_content = '\n[core]\nworkspace_base = "./workspace"\n\n[llm.custom_only]\nmodel = "custom-only-model"\napi_key = "custom-only-api-key"\n    '
    toml_file = tmp_path / "custom_only_llm.toml"
    toml_file.write_text(toml_content)
    load_from_toml(default_config, str(toml_file))
    custom_only = default_config.get_llm_config("custom_only")
    assert custom_only.model == "custom-only-model"
    assert custom_only.api_key.get_secret_value() == "custom-only-api-key"
    assert custom_only.num_retries == 5


def test_load_from_toml_llm_invalid_config(
    default_config: ForgeConfig, tmp_path: pathlib.Path
) -> None:
    """Test that invalid custom LLM configurations do not override the generic.

    and raise appropriate warnings.
    """
    toml_content = '\n[core]\nworkspace_base = "./workspace"\n\n[llm]\nmodel = "base-model"\napi_key = "base-api-key"\nnum_retries = 3\n\n[llm.invalid_custom]\nunknown_attr = "should_not_exist"\n    '
    toml_file = tmp_path / "invalid_custom_llm.toml"
    toml_file.write_text(toml_content)
    load_from_toml(default_config, str(toml_file))
    generic_llm = default_config.get_llm_config("llm")
    assert generic_llm.model == "base-model"
    assert generic_llm.api_key.get_secret_value() == "base-api-key"
    assert generic_llm.num_retries == 3
    custom_invalid = default_config.get_llm_config("invalid_custom")
    assert custom_invalid.model == "base-model"
    assert custom_invalid.api_key.get_secret_value() == "base-api-key"
    assert custom_invalid.num_retries == 3


def test_azure_model_api_version(
    default_config: ForgeConfig, tmp_path: pathlib.Path
) -> None:
    """Test that Azure models get the correct API version by default."""
    toml_content = '\n[core]\nworkspace_base = "./workspace"\n\n[llm]\nmodel = "azure/o3-mini"\napi_key = "test-api-key"\n    '
    toml_file = tmp_path / "azure_llm.toml"
    toml_file.write_text(toml_content)
    load_from_toml(default_config, str(toml_file))
    azure_llm = default_config.get_llm_config("llm")
    assert azure_llm.model == "azure/o3-mini"
    assert azure_llm.api_version == "2024-12-01-preview"
    toml_content = '\n[core]\nworkspace_base = "./workspace"\n\n[llm]\nmodel = "anthropic/claude-3-sonnet"\napi_key = "test-api-key"\n    '
    toml_file = tmp_path / "non_azure_llm.toml"
    toml_file.write_text(toml_content)
    load_from_toml(default_config, str(toml_file))
    non_azure_llm = default_config.get_llm_config("llm")
    assert non_azure_llm.model == "anthropic/claude-3-sonnet"
    assert non_azure_llm.api_version is None
