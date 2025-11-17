import logging
import os
from io import StringIO
import pytest
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
from forge.core.logger import forge_logger


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
    monkeypatch.setenv("SANDBOX_VOLUMES", "/repos/Forge/workspace:/workspace:rw")
    monkeypatch.setenv("LLM_API_KEY", "sk-proj-rgMV0...")
    monkeypatch.setenv("LLM_MODEL", "gpt-4o")
    monkeypatch.setenv("DEFAULT_AGENT", "CodeActAgent")
    monkeypatch.setenv("SANDBOX_TIMEOUT", "10")
    config = ForgeConfig()
    load_from_env(config, os.environ)
    finalize_config(config)
    assert config.sandbox.volumes == "/repos/Forge/workspace:/workspace:rw"
    expected_tail = os.path.normcase(os.path.join("repos", "forge", "workspace"))
    assert os.path.normcase(os.path.normpath(config.workspace_base)).endswith(
        expected_tail
    )
    assert os.path.normcase(os.path.normpath(config.workspace_mount_path)).endswith(
        expected_tail
    )
    assert config.workspace_mount_path_in_sandbox == "/workspace"
    assert isinstance(config.get_llm_config(), LLMConfig)
    assert config.get_llm_config().api_key.get_secret_value() == "sk-proj-rgMV0..."
    assert config.get_llm_config().model == "gpt-4o"
    assert isinstance(config.get_agent_config(), AgentConfig)
    assert config.default_agent == "CodeActAgent"
    assert config.sandbox.timeout == 10


def test_load_from_old_style_env(monkeypatch, default_config):
    monkeypatch.setenv("LLM_API_KEY", "test-api-key")
    monkeypatch.setenv("DEFAULT_AGENT", "BrowsingAgent")
    monkeypatch.setenv("WORKSPACE_BASE", "/opt/files/workspace")
    monkeypatch.setenv("SANDBOX_BASE_CONTAINER_IMAGE", "custom_image")
    load_from_env(default_config, os.environ)
    assert default_config.get_llm_config().api_key.get_secret_value() == "test-api-key"
    assert default_config.default_agent == "BrowsingAgent"
    assert os.path.normcase(os.path.normpath(default_config.workspace_base)).endswith(
        os.path.normcase(os.path.join("opt", "files", "workspace"))
    )
    assert default_config.workspace_mount_path is None
    assert default_config.workspace_mount_path_in_sandbox is not None
    assert default_config.sandbox.base_container_image == "custom_image"


def test_load_from_new_style_toml(default_config, temp_toml_file):
    with open(temp_toml_file, "w", encoding="utf-8") as toml_file:
        toml_file.write(
            '\n[llm]\nmodel = "test-model"\napi_key = "toml-api-key"\n\n[llm.cheap]\nmodel = "some-cheap-model"\napi_key = "cheap-model-api-key"\n\n[agent]\nenable_prompt_extensions = true\n\n[agent.BrowsingAgent]\nllm_config = "cheap"\nenable_prompt_extensions = false\n\n[sandbox]\ntimeout = 1\nvolumes = "/opt/files2/workspace:/workspace:rw"\n\n[core]\ndefault_agent = "TestAgent"\n'
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
    assert default_config.sandbox.volumes == "/opt/files2/workspace:/workspace:rw"
    assert default_config.sandbox.timeout == 1
    assert default_config.workspace_mount_path is None
    assert default_config.workspace_mount_path_in_sandbox is not None
    assert default_config.workspace_mount_path_in_sandbox == "/workspace"
    finalize_config(default_config)
    assert os.path.normcase(
        os.path.normpath(default_config.workspace_mount_path)
    ).endswith(os.path.normcase(os.path.join("opt", "files2", "workspace")))
    assert default_config.workspace_mount_path_in_sandbox == "/workspace"


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
            '\n[llm]\nmodel = "test-model"\napi_key = "toml-api-key"\n\n[core]\ndisable_color = true\n\n[sandbox]\nvolumes = "/opt/files3/workspace:/workspace:rw"\ntimeout = 500\nuser_id = 1001\n'
        )
    monkeypatch.setenv("LLM_API_KEY", "env-api-key")
    monkeypatch.setenv("SANDBOX_VOLUMES", "/tmp/test:/workspace:ro")  # nosec B108 - Safe: test environment variable
    monkeypatch.setenv("SANDBOX_TIMEOUT", "1000")
    monkeypatch.setenv("SANDBOX_USER_ID", "1002")
    monkeypatch.delenv("LLM_MODEL", raising=False)
    load_from_toml(default_config, temp_toml_file)
    assert default_config.workspace_mount_path is None
    load_from_env(default_config, os.environ)
    assert os.environ.get("LLM_MODEL") is None
    assert default_config.get_llm_config().model == "test-model"
    assert default_config.get_llm_config("llm").model == "test-model"
    assert default_config.get_llm_config_from_agent().model == "test-model"
    assert default_config.get_llm_config().api_key.get_secret_value() == "env-api-key"
    assert default_config.sandbox.volumes == "/tmp/test:/workspace:ro"  # nosec B108 - Safe: test assertion
    assert default_config.workspace_mount_path is None
    assert default_config.disable_color is True
    assert default_config.sandbox.timeout == 1000
    assert default_config.sandbox.user_id == 1002
    finalize_config(default_config)
    assert os.path.normcase(
        os.path.normpath(default_config.workspace_mount_path)
    ).endswith(os.path.normcase(os.path.join("tmp", "test")))
    assert default_config.workspace_mount_path_in_sandbox == "/workspace"


def test_env_overrides_sandbox_toml(monkeypatch, default_config, temp_toml_file):
    with open(temp_toml_file, "w", encoding="utf-8") as toml_file:
        toml_file.write(
            '\n[llm]\nmodel = "test-model"\napi_key = "toml-api-key"\n\n[core]\n\n[sandbox]\nvolumes = "/opt/files3/workspace:/workspace:rw"\ntimeout = 500\nuser_id = 1001\n'
        )
    monkeypatch.setenv("LLM_API_KEY", "env-api-key")
    monkeypatch.setenv("SANDBOX_VOLUMES", "/tmp/test:/workspace:ro")  # nosec B108 - Safe: test environment variable
    monkeypatch.setenv("SANDBOX_TIMEOUT", "1000")
    monkeypatch.setenv("SANDBOX_USER_ID", "1002")
    monkeypatch.delenv("LLM_MODEL", raising=False)
    load_from_toml(default_config, temp_toml_file)
    assert default_config.workspace_mount_path is None
    assert default_config.get_llm_config().api_key.get_secret_value() == "toml-api-key"
    assert default_config.sandbox.volumes == "/opt/files3/workspace:/workspace:rw"
    assert default_config.sandbox.timeout == 500
    assert default_config.sandbox.user_id == 1001
    load_from_env(default_config, os.environ)
    assert os.environ.get("LLM_MODEL") is None
    assert default_config.get_llm_config().model == "test-model"
    assert default_config.get_llm_config().api_key.get_secret_value() == "env-api-key"
    assert default_config.sandbox.volumes == "/tmp/test:/workspace:ro"  # nosec B108 - Safe: test assertion
    assert default_config.sandbox.timeout == 1000
    assert default_config.sandbox.user_id == 1002
    finalize_config(default_config)
    assert os.path.normcase(
        os.path.normpath(default_config.workspace_mount_path)
    ).endswith(os.path.normcase(os.path.join("tmp", "test")))
    assert default_config.workspace_mount_path_in_sandbox == "/workspace"


def test_sandbox_config_from_toml(monkeypatch, default_config, temp_toml_file):
    with open(temp_toml_file, "w", encoding="utf-8") as toml_file:
        toml_file.write(
            '\n[core]\n\n[llm]\nmodel = "test-model"\n\n[sandbox]\nvolumes = "/opt/files/workspace:/workspace:rw"\ntimeout = 1\nbase_container_image = "custom_image"\nuser_id = 1001\n'
        )
    monkeypatch.setattr(os, "environ", {})
    load_from_toml(default_config, temp_toml_file)
    load_from_env(default_config, os.environ)
    finalize_config(default_config)
    assert default_config.get_llm_config().model == "test-model"
    assert default_config.sandbox.volumes == "/opt/files/workspace:/workspace:rw"
    assert os.path.normcase(
        os.path.normpath(default_config.workspace_mount_path)
    ).endswith(os.path.normcase(os.path.join("opt", "files", "workspace")))
    assert default_config.workspace_mount_path_in_sandbox == "/workspace"
    assert default_config.sandbox.timeout == 1
    assert default_config.sandbox.base_container_image == "custom_image"
    assert default_config.sandbox.user_id == 1001


def test_load_from_env_with_list(monkeypatch, default_config):
    """Test loading list values from environment variables, particularly SANDBOX_RUNTIME_EXTRA_BUILD_ARGS."""
    monkeypatch.setenv(
        "SANDBOX_RUNTIME_EXTRA_BUILD_ARGS",
        "["
        + '  "--add-host=host.docker.internal:host-gateway",'
        + '  "--build-arg=https_proxy=https://my-proxy:912",'
        + "]",
    )
    load_from_env(default_config, os.environ)
    assert isinstance(default_config.sandbox.runtime_extra_build_args, list)
    assert len(default_config.sandbox.runtime_extra_build_args) == 2
    assert (
        "--add-host=host.docker.internal:host-gateway"
        in default_config.sandbox.runtime_extra_build_args
    )
    assert (
        "--build-arg=https_proxy=https://my-proxy:912"
        in default_config.sandbox.runtime_extra_build_args
    )


def test_security_config_from_toml(default_config, temp_toml_file):
    """Test loading security specific configurations."""
    with open(temp_toml_file, "w", encoding="utf-8") as toml_file:
        toml_file.write(
            '\n[core]  # make sure core is loaded first\nworkspace_base = "/opt/files/workspace"\n\n[llm]\nmodel = "test-model"\n\n[security]\nconfirmation_mode = false\nsecurity_analyzer = "semgrep"\n'
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
    assert initial_defaults["workspace_mount_path"]["default"] is None
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
    assert defaults_after_updates["workspace_mount_path"]["default"] is None
    assert defaults_after_updates["sandbox"]["timeout"]["default"] == 120
    assert (
        defaults_after_updates["sandbox"]["base_container_image"]["default"]
        == "nikolaik/python-nodejs:python3.12-nodejs22"
    )
    assert defaults_after_updates == initial_defaults


def test_sandbox_volumes(monkeypatch, default_config):
    monkeypatch.setenv(
        "SANDBOX_VOLUMES",
        "/host/path1:/container/path1,/host/path2:/container/path2:ro",
    )
    load_from_env(default_config, os.environ)
    finalize_config(default_config)
    assert (
        default_config.sandbox.volumes
        == "/host/path1:/container/path1,/host/path2:/container/path2:ro"
    )
    assert default_config.workspace_base is None
    assert default_config.workspace_mount_path is None
    assert default_config.workspace_mount_path_in_sandbox == "/workspace"


def test_sandbox_volumes_with_mode(monkeypatch, default_config):
    monkeypatch.setenv("SANDBOX_VOLUMES", "/host/path1:/container/path1:ro")
    load_from_env(default_config, os.environ)
    finalize_config(default_config)
    assert default_config.sandbox.volumes == "/host/path1:/container/path1:ro"
    assert default_config.workspace_base is None
    assert default_config.workspace_mount_path is None
    assert default_config.workspace_mount_path_in_sandbox == "/workspace"


def test_invalid_toml_format(monkeypatch, temp_toml_file, default_config):
    monkeypatch.setenv("LLM_MODEL", "gpt-5-turbo-1106")
    monkeypatch.setenv("WORKSPACE_MOUNT_PATH", "/home/user/project")
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
    assert default_config.workspace_mount_path == "/home/user/project"


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
            '\n[llm]\nmodel = "test-model"\n\n[agent]\nenable_prompt_extensions = true\n\n[sandbox]\ntimeout = 1\nbase_container_image = "custom_image"\nuser_id = 1001\n\n[security]\nsecurity_analyzer = "semgrep"\n'
        )
    load_from_toml(default_config, temp_toml_file)
    assert default_config.get_llm_config().model == "test-model"
    assert default_config.get_agent_config().enable_prompt_extensions is True
    assert default_config.sandbox.base_container_image == "custom_image"
    assert default_config.sandbox.user_id == 1001
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
            '\n[core]\ndebug = true\n\n[llm]\n# Not set in `Forge/core/schema/config.py`\ninvalid_field = "test"\nmodel = "gpt-4"\n\n[agent]\nenable_prompt_extensions = true\n\n[sandbox]\ninvalid_field_in_sandbox = "test"\n'
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
    assert default_config.workspace_mount_path is None
    default_config.workspace_base = None
    finalize_config(default_config)
    assert default_config.workspace_mount_path is None


def test_workspace_mount_path_default(default_config):
    assert default_config.workspace_mount_path is None
    default_config.workspace_base = "/home/user/project"
    finalize_config(default_config)
    assert default_config.workspace_mount_path == os.path.abspath(
        default_config.workspace_base
    )


def test_workspace_mount_rewrite(default_config, monkeypatch):
    default_config.workspace_base = "/home/user/project"
    default_config.workspace_mount_rewrite = "/home/user:/sandbox"
    monkeypatch.setattr("os.getcwd", lambda: "/current/working/directory")
    finalize_config(default_config)
    assert default_config.workspace_mount_path == "/sandbox/project"


def test_cache_dir_creation(default_config, tmpdir):
    default_config.cache_dir = str(tmpdir.join("test_cache"))
    finalize_config(default_config)
    assert os.path.exists(default_config.cache_dir)


def test_sandbox_volumes_with_workspace(default_config):
    """Test that sandbox.volumes with explicit /workspace mount works correctly."""
    default_config.sandbox.volumes = "/home/user/mydir:/workspace:rw,/data:/data:ro"
    finalize_config(default_config)
    assert default_config.workspace_mount_path == "/home/user/mydir"
    assert default_config.workspace_mount_path_in_sandbox == "/workspace"
    assert default_config.workspace_base == "/home/user/mydir"


def test_sandbox_volumes_without_workspace(default_config):
    """Test that sandbox.volumes without explicit /workspace mount doesn't set workspace paths."""
    default_config.sandbox.volumes = "/data:/data:ro,/models:/models:ro"
    finalize_config(default_config)
    assert default_config.workspace_mount_path is None
    assert default_config.workspace_base is None
    assert default_config.workspace_mount_path_in_sandbox == "/workspace"


def test_sandbox_volumes_with_workspace_not_first(default_config):
    """Test that sandbox.volumes with /workspace mount not as first entry works correctly."""
    default_config.sandbox.volumes = (
        "/data:/data:ro,/home/user/mydir:/workspace:rw,/models:/models:ro"
    )
    finalize_config(default_config)
    assert default_config.workspace_mount_path == "/home/user/mydir"
    assert default_config.workspace_mount_path_in_sandbox == "/workspace"
    assert default_config.workspace_base == "/home/user/mydir"


def test_agent_config_condenser_with_no_enabled():
    """Test default agent condenser with enable_default_condenser=False."""
    config = ForgeConfig(enable_default_condenser=False)
    agent_config = config.get_agent_config()
    assert isinstance(agent_config.condenser_config, ConversationWindowCondenserConfig)


def test_sandbox_volumes_toml(default_config, temp_toml_file):
    """Test that volumes configuration under [sandbox] works correctly."""
    with open(temp_toml_file, "w", encoding="utf-8") as toml_file:
        toml_file.write(
            '\n[sandbox]\nvolumes = "/home/user/mydir:/workspace:rw,/data:/data:ro"\ntimeout = 1\n'
        )
    load_from_toml(default_config, temp_toml_file)
    finalize_config(default_config)
    assert (
        default_config.sandbox.volumes
        == "/home/user/mydir:/workspace:rw,/data:/data:ro"
    )
    assert default_config.workspace_mount_path == "/home/user/mydir"
    assert default_config.workspace_mount_path_in_sandbox == "/workspace"
    assert default_config.workspace_base == "/home/user/mydir"
    assert default_config.sandbox.timeout == 1


def test_condenser_config_from_toml_basic(default_config, temp_toml_file):
    """Test loading basic condenser configuration from TOML."""
    with open(temp_toml_file, "w", encoding="utf-8") as toml_file:
        toml_file.write(
            '\n[condenser]\ntype = "recent"\nkeep_first = 3\nmax_events = 15\n'
        )
    load_from_toml(default_config, temp_toml_file)
    agent_config = default_config.get_agent_config()
    assert isinstance(agent_config.condenser_config, RecentEventsCondenserConfig)
    assert agent_config.condenser_config.keep_first == 3
    assert agent_config.condenser_config.max_events == 15
    from forge.core.config.condenser_config import condenser_config_from_toml_section

    condenser_data = {"type": "recent", "keep_first": 3, "max_events": 15}
    condenser_mapping = condenser_config_from_toml_section(condenser_data)
    assert "condenser" in condenser_mapping
    assert isinstance(condenser_mapping["condenser"], RecentEventsCondenserConfig)
    assert condenser_mapping["condenser"].keep_first == 3
    assert condenser_mapping["condenser"].max_events == 15


def test_condenser_config_from_toml_with_llm_reference(default_config, temp_toml_file):
    """Test loading condenser configuration with LLM reference from TOML."""
    with open(temp_toml_file, "w", encoding="utf-8") as toml_file:
        toml_file.write(
            '\n[llm.condenser_llm]\nmodel = "gpt-4"\napi_key = "test-key"\n\n[condenser]\ntype = "llm"\nllm_config = "condenser_llm"\nkeep_first = 2\nmax_size = 50\n'
        )
    load_from_toml(default_config, temp_toml_file)
    assert "condenser_llm" in default_config.llms
    assert default_config.llms["condenser_llm"].model == "gpt-4"
    agent_config = default_config.get_agent_config()
    assert isinstance(agent_config.condenser_config, LLMSummarizingCondenserConfig)
    assert agent_config.condenser_config.keep_first == 2
    assert agent_config.condenser_config.max_size == 50
    assert agent_config.condenser_config.llm_config.model == "gpt-4"
    from forge.core.config.condenser_config import condenser_config_from_toml_section

    condenser_data = {
        "type": "llm",
        "llm_config": "condenser_llm",
        "keep_first": 2,
        "max_size": 50,
    }
    condenser_mapping = condenser_config_from_toml_section(
        condenser_data, default_config.llms
    )
    assert "condenser" in condenser_mapping
    assert isinstance(condenser_mapping["condenser"], LLMSummarizingCondenserConfig)
    assert condenser_mapping["condenser"].keep_first == 2
    assert condenser_mapping["condenser"].max_size == 50
    assert condenser_mapping["condenser"].llm_config.model == "gpt-4"


def test_condenser_config_from_toml_with_missing_llm_reference(
    default_config, temp_toml_file
):
    """Test loading condenser configuration with missing LLM reference from TOML."""
    with open(temp_toml_file, "w", encoding="utf-8") as toml_file:
        toml_file.write(
            '\n[condenser]\ntype = "llm"\nllm_config = "missing_llm"\nkeep_first = 2\nmax_size = 50\n'
        )
    load_from_toml(default_config, temp_toml_file)
    from forge.core.config.condenser_config import condenser_config_from_toml_section

    condenser_data = {
        "type": "llm",
        "llm_config": "missing_llm",
        "keep_first": 2,
        "max_size": 50,
    }
    condenser_mapping = condenser_config_from_toml_section(
        condenser_data, default_config.llms
    )
    assert "condenser" in condenser_mapping
    assert isinstance(condenser_mapping["condenser"], NoOpCondenserConfig)
    assert not hasattr(condenser_mapping["condenser"], "llm_config")


def test_condenser_config_from_toml_with_invalid_config(default_config, temp_toml_file):
    """Test loading invalid condenser configuration from TOML."""
    with open(temp_toml_file, "w", encoding="utf-8") as toml_file:
        toml_file.write('\n[condenser]\ntype = "invalid_type"\n')
    load_from_toml(default_config, temp_toml_file)
    from forge.core.config.condenser_config import condenser_config_from_toml_section

    condenser_data = {"type": "invalid_type"}
    condenser_mapping = condenser_config_from_toml_section(condenser_data)
    assert "condenser" in condenser_mapping
    assert isinstance(condenser_mapping["condenser"], NoOpCondenserConfig)


def test_condenser_config_from_toml_with_validation_error(
    default_config, temp_toml_file
):
    """Test loading condenser configuration with validation error from TOML."""
    with open(temp_toml_file, "w", encoding="utf-8") as toml_file:
        toml_file.write(
            '\n[condenser]\ntype = "recent"\nkeep_first = -1  # Invalid: must be >= 0\nmax_events = 0   # Invalid: must be >= 1\n'
        )
    load_from_toml(default_config, temp_toml_file)
    from forge.core.config.condenser_config import condenser_config_from_toml_section

    condenser_data = {"type": "recent", "keep_first": -1, "max_events": 0}
    condenser_mapping = condenser_config_from_toml_section(condenser_data)
    assert "condenser" in condenser_mapping
    assert isinstance(condenser_mapping["condenser"], NoOpCondenserConfig)


def test_default_condenser_behavior_enabled(default_config, temp_toml_file):
    """Test the default condenser behavior when enable_default_condenser is True."""
    with open(temp_toml_file, "w", encoding="utf-8") as toml_file:
        toml_file.write("\n[core]\n# Empty core section, no condenser section\n")
    default_config.enable_default_condenser = True
    load_from_toml(default_config, temp_toml_file)
    agent_config = default_config.get_agent_config()
    assert isinstance(agent_config.condenser_config, LLMSummarizingCondenserConfig)
    assert agent_config.condenser_config.keep_first == 1
    assert agent_config.condenser_config.max_size == 100


def test_default_condenser_behavior_disabled(default_config, temp_toml_file):
    """Test the default condenser behavior when enable_default_condenser is False."""
    with open(temp_toml_file, "w", encoding="utf-8") as toml_file:
        toml_file.write("\n[core]\n# Empty core section, no condenser section\n")
    default_config.enable_default_condenser = False
    load_from_toml(default_config, temp_toml_file)
    agent_config = default_config.get_agent_config()
    assert isinstance(agent_config.condenser_config, ConversationWindowCondenserConfig)


def test_default_condenser_explicit_toml_override(default_config, temp_toml_file):
    """Test that explicit condenser in TOML takes precedence over the default."""
    default_config.enable_default_condenser = True
    with open(temp_toml_file, "w", encoding="utf-8") as toml_file:
        toml_file.write(
            '\n[condenser]\ntype = "recent"\nkeep_first = 3\nmax_events = 15\n'
        )
    load_from_toml(default_config, temp_toml_file)
    agent_config = default_config.get_agent_config()
    assert isinstance(agent_config.condenser_config, RecentEventsCondenserConfig)
    assert agent_config.condenser_config.keep_first == 3
    assert agent_config.condenser_config.max_events == 15


def _test_llm_config_api_key_redaction():
    """Test that LLM config API keys are redacted in string representations."""
    llm_config = LLMConfig(
        api_key="my_api_key",
        aws_access_key_id="my_access_key",
        aws_secret_access_key="my_secret_key",
    )
    assert "my_api_key" not in repr(llm_config)
    assert "my_api_key" not in str(llm_config)
    assert "my_access_key" not in repr(llm_config)
    assert "my_access_key" not in str(llm_config)
    assert "my_secret_key" not in repr(llm_config)
    assert "my_secret_key" not in str(llm_config)


def _validate_llm_config_attributes():
    """Validate LLM config attributes don't contain unexpected key/token names."""
    known_key_token_attrs_llm = [
        "api_key",
        "aws_access_key_id",
        "aws_secret_access_key",
        "input_cost_per_token",
        "output_cost_per_token",
        "custom_tokenizer",
    ]
    for attr_name in LLMConfig.model_fields.keys():
        if (
            not attr_name.startswith("__")
            and attr_name not in known_key_token_attrs_llm
        ):
            assert "key" not in attr_name.lower(), (
                f"Unexpected attribute '{attr_name}' contains 'key' in LLMConfig"
            )
            assert "token" not in attr_name.lower() or "tokens" in attr_name.lower(), (
                f"Unexpected attribute '{attr_name}' contains 'token' in LLMConfig"
            )


def _validate_agent_config_attributes():
    """Validate Agent config attributes don't contain unexpected key/token names."""
    # Create instance to ensure config is valid
    _ = AgentConfig(enable_prompt_extensions=True, enable_browsing=False)
    for attr_name in AgentConfig.model_fields.keys():
        if not attr_name.startswith("__"):
            assert "key" not in attr_name.lower(), (
                f"Unexpected attribute '{attr_name}' contains 'key' in AgentConfig"
            )
            assert "token" not in attr_name.lower() or "tokens" in attr_name.lower(), (
                f"Unexpected attribute '{attr_name}' contains 'token' in AgentConfig"
            )


def _test_app_config_api_key_redaction():
    """Test that app config API keys are redacted in string representations."""
    llm_config = LLMConfig(
        api_key="my_api_key",
        aws_access_key_id="my_access_key",
        aws_secret_access_key="my_secret_key",
    )
    agent_config = AgentConfig(enable_prompt_extensions=True, enable_browsing=False)
    app_config = ForgeConfig(
        llms={"llm": llm_config},
        agents={"agent": agent_config},
        search_api_key="my_search_api_key",
    )
    assert "my_search_api_key" not in repr(app_config)
    assert "my_search_api_key" not in str(app_config)


def _validate_app_config_attributes():
    """Validate app config attributes don't contain unexpected key/token names."""
    known_key_token_attrs_app = ["search_api_key"]
    for attr_name in ForgeConfig.model_fields.keys():
        if (
            not attr_name.startswith("__")
            and attr_name not in known_key_token_attrs_app
        ):
            assert "key" not in attr_name.lower(), (
                f"Unexpected attribute '{attr_name}' contains 'key' in ForgeConfig"
            )
            assert "token" not in attr_name.lower() or "tokens" in attr_name.lower(), (
                f"Unexpected attribute '{attr_name}' contains 'token' in ForgeConfig"
            )


def test_api_keys_repr_str():
    """Test that API keys are properly redacted in string representations."""
    # Test LLM config API key redaction
    _test_llm_config_api_key_redaction()

    # Validate LLM config attributes
    _validate_llm_config_attributes()

    # Validate Agent config attributes
    _validate_agent_config_attributes()

    # Test app config API key redaction
    _test_app_config_api_key_redaction()

    # Validate app config attributes
    _validate_app_config_attributes()


def test_max_iterations_and_max_budget_per_task_from_toml(temp_toml_file):
    temp_toml = "\n[core]\nmax_iterations = 42\nmax_budget_per_task = 4.7\n"
    config = ForgeConfig()
    with open(temp_toml_file, "w", encoding="utf-8") as f:
        f.write(temp_toml)
    load_from_toml(config, temp_toml_file)
    assert config.max_iterations == 42
    assert config.max_budget_per_task == 4.7


def test_get_llm_config_arg(temp_toml_file):
    temp_toml = '\n[core]\nmax_iterations = 100\nmax_budget_per_task = 4.0\n\n[llm.gpt3]\nmodel="gpt-3.5-turbo"\napi_key="redacted"\n\n[llm.gpt4o]\nmodel="gpt-4o"\napi_key="redacted"\n'
    with open(temp_toml_file, "w", encoding="utf-8") as f:
        f.write(temp_toml)
    llm_config = get_llm_config_arg("gpt3", temp_toml_file)
    assert llm_config.model == "gpt-3.5-turbo"


def test_get_agent_configs(default_config, temp_toml_file):
    temp_toml = "\n[core]\nmax_iterations = 100\nmax_budget_per_task = 4.0\n\n[agent.CodeActAgent]\nenable_prompt_extensions = true\n\n[agent.BrowsingAgent]\nenable_jupyter = false\n"
    with open(temp_toml_file, "w", encoding="utf-8") as f:
        f.write(temp_toml)
    load_from_toml(default_config, temp_toml_file)
    codeact_config = default_config.get_agent_configs().get("CodeActAgent")
    assert codeact_config.enable_prompt_extensions is True
    browsing_config = default_config.get_agent_configs().get("BrowsingAgent")
    assert browsing_config.enable_jupyter is False


def test_get_agent_config_arg(temp_toml_file):
    temp_toml = "\n[core]\nmax_iterations = 100\nmax_budget_per_task = 4.0\n\n[agent.CodeActAgent]\nenable_prompt_extensions = false\nenable_browsing = false\n\n[agent.BrowsingAgent]\nenable_prompt_extensions = true\nenable_jupyter = false\n"
    with open(temp_toml_file, "w", encoding="utf-8") as f:
        f.write(temp_toml)
    agent_config = get_agent_config_arg("CodeActAgent", temp_toml_file)
    assert not agent_config.enable_prompt_extensions
    assert not agent_config.enable_browsing
    agent_config2 = get_agent_config_arg("BrowsingAgent", temp_toml_file)
    assert agent_config2.enable_prompt_extensions
    assert not agent_config2.enable_jupyter


def test_agent_config_custom_group_name(temp_toml_file):
    temp_toml = "\n[core]\nmax_iterations = 99\n\n[agent.group1]\nenable_prompt_extensions = true\n\n[agent.group2]\nenable_prompt_extensions = false\n"
    with open(temp_toml_file, "w", encoding="utf-8") as f:
        f.write(temp_toml)
    app_config = load_FORGE_config(config_file=temp_toml_file)
    assert app_config.max_iterations == 99
    agent_config1 = get_agent_config_arg("group1", temp_toml_file)
    assert agent_config1.enable_prompt_extensions
    agent_config2 = get_agent_config_arg("group2", temp_toml_file)
    assert not agent_config2.enable_prompt_extensions


def test_agent_config_from_toml_section():
    """Test that AgentConfig.from_toml_section correctly parses agent configurations from TOML."""
    from forge.core.config.agent_config import AgentConfig

    agent_section = {
        "enable_prompt_extensions": True,
        "enable_browsing": True,
        "CustomAgent1": {"enable_browsing": False},
        "CustomAgent2": {"enable_prompt_extensions": False},
        "InvalidAgent": {"invalid_field": "some_value"},
    }
    result = AgentConfig.from_toml_section(agent_section)
    assert "agent" in result
    assert result["agent"].enable_prompt_extensions is True
    assert result["agent"].enable_browsing is True
    assert "CustomAgent1" in result
    assert result["CustomAgent1"].enable_browsing is False
    assert result["CustomAgent1"].enable_prompt_extensions is True
    assert "CustomAgent2" in result
    assert result["CustomAgent2"].enable_browsing is True
    assert result["CustomAgent2"].enable_prompt_extensions is False
    assert "InvalidAgent" not in result


def test_agent_config_from_toml_section_with_invalid_base():
    """Test that AgentConfig.from_toml_section handles invalid base configurations gracefully."""
    from forge.core.config.agent_config import AgentConfig

    agent_section = {
        "invalid_field": "some_value",
        "enable_jupyter": "not_a_bool",
        "CustomAgent": {"enable_browsing": False, "enable_jupyter": True},
    }
    result = AgentConfig.from_toml_section(agent_section)
    assert "agent" in result
    assert result["agent"].enable_browsing is True
    assert result["agent"].enable_jupyter is True
    assert "CustomAgent" in result
    assert result["CustomAgent"].enable_browsing is False
    assert result["CustomAgent"].enable_jupyter is True


def test_agent_config_system_prompt_filename_default():
    """Test that AgentConfig defaults to 'system_prompt.j2' for system_prompt_filename."""
    config = AgentConfig()
    assert config.system_prompt_filename == "system_prompt.j2"


def test_agent_config_system_prompt_filename_toml_integration(
    default_config, temp_toml_file
):
    """Test that system_prompt_filename is correctly loaded from TOML configuration."""
    with open(temp_toml_file, "w", encoding="utf-8") as toml_file:
        toml_file.write(
            '\n[agent]\nenable_browsing = true\nsystem_prompt_filename = "custom_prompt.j2"\n\n[agent.CodeReviewAgent]\nsystem_prompt_filename = "code_review_prompt.j2"\nenable_browsing = false\n'
        )
    load_from_toml(default_config, temp_toml_file)
    default_agent_config = default_config.get_agent_config()
    assert default_agent_config.system_prompt_filename == "custom_prompt.j2"
    assert default_agent_config.enable_browsing is True
    custom_agent_config = default_config.get_agent_config("CodeReviewAgent")
    assert custom_agent_config.system_prompt_filename == "code_review_prompt.j2"
    assert custom_agent_config.enable_browsing is False
