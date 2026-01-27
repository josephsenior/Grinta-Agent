import logging
import os
from io import StringIO
import pytest
from pydantic import SecretStr, ValidationError
from forge.core.config import (
    AgentConfig,
    LLMConfig,
    ForgeConfig,
    finalize_config,
    get_agent_config_arg,
    get_llm_config_arg,
    load_from_env,
    load_from_toml,
    load_FORGE_config,
)
from forge.core.config.condenser_config import (
    ConversationWindowCondenserConfig,
    LLMSummarizingCondenserConfig,
    NoOpCondenserConfig,
    RecentEventsCondenserConfig,
)
from forge.core.logger import forge_logger as FORGE_logger


@pytest.fixture
def setup_env():
    with open("old_style_config.toml", "w", encoding="utf-8") as f:
        f.write('[default]\nLLM_MODEL="GPT-4"\n')
    with open("new_style_config.toml", "w", encoding="utf-8") as f:
        f.write('[app]\nLLM_MODEL="GPT-3"\n')
    yield
    os.remove("old_style_config.toml")
    os.remove("new_style_config.toml")


@pytest.fixture
def temp_toml_file(tmp_path):
    yield os.path.join(tmp_path, "config.toml")


@pytest.fixture
def default_config(monkeypatch):
    yield ForgeConfig()


def test_compat_env_to_config(monkeypatch, setup_env):
    monkeypatch.setenv("LLM_API_KEY", "sk-proj-rgMV0...")
    monkeypatch.setenv("LLM_MODEL", "gpt-4o")
    monkeypatch.setenv("DEFAULT_AGENT", "CodeActAgent")
    monkeypatch.setenv("SANDBOX_TIMEOUT", "10")
    config = ForgeConfig()
    load_from_env(config, os.environ)
    finalize_config(config)
    assert isinstance(config.get_llm_config(), LLMConfig)
    assert config.get_llm_config().api_key.get_secret_value() == "sk-proj-rgMV0..."
    assert config.get_llm_config().model == "gpt-4o"
    assert isinstance(config.get_agent_config(), AgentConfig)
    assert config.default_agent == "CodeActAgent"
    assert config.sandbox.timeout == 10


def test_load_from_old_style_env(monkeypatch, default_config):
    monkeypatch.setenv("LLM_API_KEY", "test-api-key")
    monkeypatch.setenv("DEFAULT_AGENT", "BrowsingAgent")
    load_from_env(default_config, os.environ)
    assert default_config.get_llm_config().api_key.get_secret_value() == "test-api-key"
    assert default_config.default_agent == "BrowsingAgent"


def test_load_from_new_style_toml(default_config, temp_toml_file):
    with open(temp_toml_file, "w", encoding="utf-8") as toml_file:
        toml_file.write(
            '\n[llm]\nmodel = "test-model"\napi_key = "toml-api-key"\n\n[llm.cheap]\nmodel = "some-cheap-model"\napi_key = "cheap-model-api-key"\n\n[agent]\nenable_prompt_extensions = true\n\n[agent.BrowsingAgent]\nllm_config = "cheap"\nenable_prompt_extensions = false\n\n[sandbox]\ntimeout = 1\n\n[core]\ndefault_agent = "TestAgent"\n'
        )
    load_from_toml(default_config, temp_toml_file)
    assert default_config.default_agent == "TestAgent"
    assert default_config.get_llm_config().model == "test-model"
    assert default_config.get_llm_config().api_key.get_secret_value() == "toml-api-key"
    assert default_config.get_agent_config().enable_prompt_extensions is True
    assert (
        default_config.get_llm_config_from_agent("CodeActAgent")
        == default_config.get_llm_config()
    )
    assert (
        default_config.get_agent_config("CodeActAgent").enable_prompt_extensions is True
    )
    assert default_config.get_llm_config_from_agent(
        "BrowsingAgent"
    ) == default_config.get_llm_config("cheap")
    assert (
        default_config.get_llm_config_from_agent("BrowsingAgent").model
        == "some-cheap-model"
    )
    assert (
        default_config.get_agent_config("BrowsingAgent").enable_prompt_extensions
        is False
    )
    assert default_config.sandbox.timeout == 1
    finalize_config(default_config)


def test_llm_config_native_tool_calling(default_config, temp_toml_file, monkeypatch):
    assert default_config.get_llm_config().native_tool_calling is None
    with open(temp_toml_file, "w", encoding="utf-8") as toml_file:
        toml_file.write("\n[core]\n\n[llm.gpt4o-mini]\nnative_tool_calling = false\n")
    load_from_toml(default_config, temp_toml_file)
    assert default_config.get_llm_config().native_tool_calling is None
    assert default_config.get_llm_config("gpt4o-mini").native_tool_calling is False
    with open(temp_toml_file, "w", encoding="utf-8") as toml_file:
        toml_file.write("\n[core]\n\n[llm.gpt4o-mini]\nnative_tool_calling = true\n")
    load_from_toml(default_config, temp_toml_file)
    assert default_config.get_llm_config("gpt4o-mini").native_tool_calling is True
    monkeypatch.setenv("LLM_NATIVE_TOOL_CALLING", "false")
    load_from_env(default_config, os.environ)
    assert default_config.get_llm_config().native_tool_calling is False
    assert default_config.get_llm_config("gpt4o-mini").native_tool_calling is True


def test_env_overrides_compat_toml(monkeypatch, default_config, temp_toml_file):
    with open(temp_toml_file, "w", encoding="utf-8") as toml_file:
        toml_file.write(
            '\n[llm]\nmodel = "test-model"\napi_key = "toml-api-key"\n\n[core]\ndisable_color = true\n\n[sandbox]\ntimeout = 500\n'
        )
    monkeypatch.setenv("LLM_API_KEY", "env-api-key")
    monkeypatch.setenv("SANDBOX_TIMEOUT", "1000")
    monkeypatch.delenv("LLM_MODEL", raising=False)
    load_from_toml(default_config, temp_toml_file)
    load_from_env(default_config, os.environ)
    assert os.environ.get("LLM_MODEL") is None
    assert default_config.get_llm_config().model == "test-model"
    assert default_config.get_llm_config("llm").model == "test-model"
    assert default_config.get_llm_config_from_agent().model == "test-model"
    assert default_config.get_llm_config().api_key.get_secret_value() == "env-api-key"
    assert default_config.disable_color is True
    assert default_config.sandbox.timeout == 1000
    finalize_config(default_config)


def test_env_overrides_sandbox_toml(monkeypatch, default_config, temp_toml_file):
    with open(temp_toml_file, "w", encoding="utf-8") as toml_file:
        toml_file.write(
            '\n[llm]\nmodel = "test-model"\napi_key = "toml-api-key"\n\n[core]\n\n[sandbox]\ntimeout = 500\n'
        )
    monkeypatch.setenv("LLM_API_KEY", "env-api-key")
    monkeypatch.setenv("SANDBOX_TIMEOUT", "1000")
    monkeypatch.delenv("LLM_MODEL", raising=False)
    load_from_toml(default_config, temp_toml_file)
    assert default_config.get_llm_config().api_key.get_secret_value() == "toml-api-key"
    assert default_config.sandbox.timeout == 500
    load_from_env(default_config, os.environ)
    assert os.environ.get("LLM_MODEL") is None
    assert default_config.get_llm_config().model == "test-model"
    assert default_config.get_llm_config().api_key.get_secret_value() == "env-api-key"
    assert default_config.sandbox.timeout == 1000
    finalize_config(default_config)


def test_sandbox_config_from_toml(monkeypatch, default_config, temp_toml_file):
    with open(temp_toml_file, "w", encoding="utf-8") as toml_file:
        toml_file.write(
            '\n[core]\n\n[llm]\nmodel = "test-model"\n\n[sandbox]\ntimeout = 1\n'
        )
    monkeypatch.setattr(os, "environ", {})
    load_from_toml(default_config, temp_toml_file)
    load_from_env(default_config, os.environ)
    finalize_config(default_config)
    assert default_config.get_llm_config().model == "test-model"
    assert default_config.sandbox.timeout == 1


def test_security_config_from_toml(default_config, temp_toml_file):
    """Test loading security specific configurations."""
    with open(temp_toml_file, "w", encoding="utf-8") as toml_file:
        toml_file.write(
            '\n[core]  # make sure core is loaded first\n\n[llm]\nmodel = "test-model"\n\n[security]\nconfirmation_mode = false\nsecurity_analyzer = "semgrep"\n'
        )
    load_from_toml(default_config, temp_toml_file)
    assert default_config.security.confirmation_mode is False
    assert default_config.security.security_analyzer == "semgrep"


def test_security_config_from_dict():
    """Test creating SecurityConfig instance from dictionary."""
    from forge.core.config.security_config import SecurityConfig

    config_dict = {"confirmation_mode": True, "security_analyzer": "some_analyzer"}
    security_config = SecurityConfig(**config_dict)
    assert security_config.confirmation_mode is True
    assert security_config.security_analyzer == "some_analyzer"


def test_defaults_dict_after_updates(default_config):
    initial_defaults = default_config.defaults_dict
    assert initial_defaults["default_agent"]["default"] == "CodeActAgent"
    updated_config = ForgeConfig()
    updated_config.get_llm_config().api_key = "updated-api-key"
    updated_config.get_llm_config("llm").api_key = "updated-api-key"
    updated_config.get_llm_config_from_agent("agent").api_key = "updated-api-key"
    updated_config.get_llm_config_from_agent(
        "BrowsingAgent"
    ).api_key = "updated-api-key"
    updated_config.default_agent = "BrowsingAgent"
    defaults_after_updates = updated_config.defaults_dict
    assert defaults_after_updates["default_agent"]["default"] == "CodeActAgent"
    assert defaults_after_updates["sandbox"]["timeout"]["default"] == 120
    assert defaults_after_updates == initial_defaults


def test_invalid_toml_format(monkeypatch, temp_toml_file, default_config):
    monkeypatch.setenv("LLM_MODEL", "gpt-5-turbo-1106")
    monkeypatch.delenv("LLM_API_KEY", raising=False)
    with open(temp_toml_file, "w", encoding="utf-8") as toml_file:
        toml_file.write("INVALID TOML CONTENT")
    load_from_toml(default_config, temp_toml_file)
    load_from_env(default_config, os.environ)
    default_config.jwt_secret = None
    for llm in default_config.llms.values():
        llm.api_key = None
    assert default_config.get_llm_config().model == "gpt-5-turbo-1106"
    assert default_config.get_llm_config().custom_llm_provider is None


def test_load_from_toml_file_not_found(default_config):
    """Test loading configuration when the TOML file doesn't exist.

    This ensures that:
    1. The program doesn't crash when the config file is missing
    2. The config object retains its default values
    3. The application remains usable
    """
    load_from_toml(default_config, "nonexistent.toml")
    assert default_config.get_llm_config() is not None
    assert default_config.get_agent_config() is not None
    assert default_config.sandbox is not None


def test_core_not_in_toml(default_config, temp_toml_file):
    """Test loading configuration when the core section is not in the TOML file.

    default values should be used for the missing sections.
    """
    with open(temp_toml_file, "w", encoding="utf-8") as toml_file:
        toml_file.write(
            '\n[llm]\nmodel = "test-model"\n\n[agent]\nenable_prompt_extensions = true\n\n[sandbox]\ntimeout = 1\n\n[security]\nsecurity_analyzer = "semgrep"\n'
        )
    load_from_toml(default_config, temp_toml_file)
    assert default_config.get_llm_config().model == "test-model"
    assert default_config.get_agent_config().enable_prompt_extensions is True
    assert default_config.security.security_analyzer == "semgrep"


def test_load_from_toml_partial_invalid(default_config, temp_toml_file, caplog):
    """Test loading configuration with partially invalid TOML content.

    This ensures that:
    1. Valid configuration sections are properly loaded
    2. Invalid fields in security and sandbox sections raise ValueError
    4. The config object maintains correct values for valid fields
    """
    with open(temp_toml_file, "w", encoding="utf-8") as f:
        f.write(
            '\n[core]\ndebug = true\n\n[llm]\n# Not set in `Forge/core/schema/config.py`\ninvalid_field = "test"\nmodel = "gpt-4"\n\n[agent]\nenable_prompt_extensions = true\n\n[sandbox]\ntimeout = "invalid"\n'
        )
    log_output = StringIO()
    handler = logging.StreamHandler(log_output)
    handler.setLevel(logging.WARNING)
    formatter = logging.Formatter("%(message)s")
    handler.setFormatter(formatter)
    FORGE_logger.addHandler(handler)
    try:
        with pytest.raises(ValueError) as excinfo:
            load_from_toml(default_config, temp_toml_file)
        assert "Error in [sandbox] section in config.toml" in str(excinfo.value)
        log_content = log_output.getvalue()
        assert "Cannot parse [llm] config from toml" in log_content
        assert default_config.debug is True
    finally:
        FORGE_logger.removeHandler(handler)


def test_load_from_toml_security_invalid(default_config, temp_toml_file):
    """Test that invalid security configuration raises ValueError."""
    with open(temp_toml_file, "w", encoding="utf-8") as f:
        f.write(
            '\n[core]\ndebug = true\n\n[security]\ninvalid_security_field = "test"\n'
        )
    with pytest.raises(ValueError) as excinfo:
        load_from_toml(default_config, temp_toml_file)
    assert "Error in [security] section in config.toml" in str(excinfo.value)


def test_finalize_config(default_config):
    finalize_config(default_config)


def test_cache_dir_creation(default_config, tmpdir):
    default_config.cache_dir = str(tmpdir.join("test_cache"))
    finalize_config(default_config)
    assert os.path.exists(default_config.cache_dir)
