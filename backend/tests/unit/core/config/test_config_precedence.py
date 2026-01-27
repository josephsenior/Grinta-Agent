from unittest.mock import MagicMock, patch
import pytest
from forge.core.config import (
    FORGE_DEFAULT_AGENT,
    FORGE_MAX_ITERATIONS,
    ForgeConfig,
    get_llm_config_arg,
    setup_config_from_args,
)


@pytest.fixture
def default_config():
    """Fixture to provide a default ForgeConfig instance."""
    yield ForgeConfig()


@pytest.fixture
def temp_config_files(tmp_path):
    """Create temporary config files for testing precedence."""
    user_config_dir = tmp_path / "home" / ".Forge"
    user_config_dir.mkdir(parents=True, exist_ok=True)
    user_config_toml = user_config_dir / "config.toml"
    user_config_toml.write_text(
        '\n[llm]\nmodel = "user-home-model"\napi_key = "user-home-api-key"\n\n[llm.user-llm]\nmodel = "user-specific-model"\napi_key = "user-specific-api-key"\n'
    )
    user_settings_json = user_config_dir / "settings.json"
    user_settings_json.write_text(
        '\n{\n    "LLM_MODEL": "settings-json-model",\n    "LLM_API_KEY": "settings-json-api-key"\n}\n'
    )
    current_dir_toml = tmp_path / "current" / "config.toml"
    current_dir_toml.parent.mkdir(parents=True, exist_ok=True)
    current_dir_toml.write_text(
        '\n[llm]\nmodel = "current-dir-model"\napi_key = "current-dir-api-key"\n\n[llm.current-dir-llm]\nmodel = "current-dir-specific-model"\napi_key = "current-dir-specific-api-key"\n'
    )
    return {
        "user_config_toml": str(user_config_toml),
        "user_settings_json": str(user_settings_json),
        "current_dir_toml": str(current_dir_toml),
        "home_dir": str(user_config_dir.parent),
        "current_dir": str(current_dir_toml.parent),
    }


@patch("forge.core.config.utils.os.path.expanduser")
def test_llm_config_precedence_cli_highest(mock_expanduser, temp_config_files):
    """Test that CLI parameters have the highest precedence."""
    mock_expanduser.side_effect = lambda path: path.replace(
        "~", temp_config_files["home_dir"]
    )
    mock_args = MagicMock()
    mock_args.config_file = temp_config_files["current_dir_toml"]
    mock_args.llm_config = "current-dir-llm"
    mock_args.agent_cls = None
    mock_args.max_iterations = None
    mock_args.max_budget_per_task = None
    mock_args.selected_repo = None
    with patch("os.path.exists", return_value=True):
        config = setup_config_from_args(mock_args)
    assert config.get_llm_config().model == "current-dir-specific-model"
    assert (
        config.get_llm_config().api_key.get_secret_value()
        == "current-dir-specific-api-key"
    )


@patch("forge.core.config.utils.os.path.expanduser")
def test_current_dir_toml_precedence_over_user_config(
    mock_expanduser, temp_config_files
):
    """Test that config.toml in current directory has precedence over ~/.Forge/config.toml."""
    mock_expanduser.side_effect = lambda path: path.replace(
        "~", temp_config_files["home_dir"]
    )
    mock_args = MagicMock()
    mock_args.config_file = temp_config_files["current_dir_toml"]
    mock_args.llm_config = None
    mock_args.agent_cls = None
    mock_args.max_iterations = None
    mock_args.max_budget_per_task = None
    mock_args.selected_repo = None
    with patch("os.path.exists", return_value=True):
        config = setup_config_from_args(mock_args)
    assert config.get_llm_config().model == "current-dir-model"
    assert config.get_llm_config().api_key.get_secret_value() == "current-dir-api-key"


@patch("forge.core.config.utils.os.path.expanduser")
def test_get_llm_config_arg_precedence(mock_expanduser, temp_config_files):
    """Test that get_llm_config_arg prioritizes the specified config file."""
    mock_expanduser.side_effect = lambda path: path.replace(
        "~", temp_config_files["home_dir"]
    )
    with patch("os.path.exists", return_value=True):
        llm_config = get_llm_config_arg(
            "current-dir-llm", temp_config_files["current_dir_toml"]
        )
    assert llm_config.model == "current-dir-specific-model"
    assert llm_config.api_key.get_secret_value() == "current-dir-specific-api-key"
    with patch("os.path.exists", return_value=False):
        llm_config = get_llm_config_arg(
            "user-llm", temp_config_files["current_dir_toml"]
        )
    assert llm_config is None


@patch("forge.core.config.utils.os.path.expanduser")
@patch("forge.cli.main.FileSettingsStore.get_instance")
@patch("forge.cli.main.FileSettingsStore.load")
def test_cli_main_settings_precedence(
    mock_load, mock_get_instance, mock_expanduser, temp_config_files
):
    """Test that the CLI main.py correctly applies settings precedence."""
    from forge.cli.main import setup_config_from_args

    mock_expanduser.side_effect = lambda path: path.replace(
        "~", temp_config_files["home_dir"]
    )
    mock_settings = MagicMock()
    mock_settings.llm_model = "settings-store-model"
    mock_settings.llm_api_key = "settings-store-api-key"
    mock_settings.llm_base_url = None
    mock_settings.agent = "CodeActAgent"
    mock_settings.confirmation_mode = False
    mock_settings.enable_default_condenser = True
    mock_load.return_value = mock_settings
    mock_get_instance.return_value = MagicMock()
    mock_args = MagicMock()
    mock_args.config_file = temp_config_files["current_dir_toml"]
    mock_args.llm_config = None
    mock_args.agent_cls = None
    mock_args.max_iterations = None
    mock_args.max_budget_per_task = None
    mock_args.selected_repo = None
    with patch("os.path.exists", return_value=True):
        config = setup_config_from_args(mock_args)
    assert config.get_llm_config().model == "current-dir-model"
    assert config.get_llm_config().api_key.get_secret_value() == "current-dir-api-key"


def test_default_values_applied_when_none():
    """Test that default values are applied when config values are None."""
    mock_args = MagicMock()
    mock_args.config_file = None
    mock_args.llm_config = None
    mock_args.agent_cls = None
    mock_args.max_iterations = None
    with patch("forge.core.config.utils.load_FORGE_config", return_value=ForgeConfig()):
        config = setup_config_from_args(mock_args)
    assert config.default_agent == FORGE_DEFAULT_AGENT
    assert config.max_iterations == FORGE_MAX_ITERATIONS


def test_cli_args_override_defaults():
    """Test that CLI arguments override default values."""
    mock_args = MagicMock()
    mock_args.config_file = None
    mock_args.llm_config = None
    mock_args.agent_cls = "CustomAgent"
    mock_args.max_iterations = 50
    with patch("forge.core.config.utils.load_FORGE_config", return_value=ForgeConfig()):
        config = setup_config_from_args(mock_args)
    assert config.default_agent == "CustomAgent"
    assert config.max_iterations == 50


def test_cli_args_none_uses_config_toml_values():
    """Test that when CLI args agent_cls and max_iterations are None, config.toml values are used."""
    mock_args = MagicMock()
    mock_args.config_file = None
    mock_args.llm_config = None
    mock_args.agent_cls = None
    mock_args.max_iterations = None
    config_from_toml = ForgeConfig()
    config_from_toml.default_agent = "ConfigTomlAgent"
    config_from_toml.max_iterations = 100
    with patch(
        "forge.core.config.utils.load_FORGE_config", return_value=config_from_toml
    ):
        config = setup_config_from_args(mock_args)
    assert config.default_agent == "ConfigTomlAgent"
    assert config.max_iterations == 100
