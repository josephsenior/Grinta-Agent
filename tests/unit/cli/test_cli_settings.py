from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch
import pytest
from prompt_toolkit.formatted_text import HTML
from pydantic import SecretStr
from openhands.cli.settings import (
    display_settings,
    modify_llm_settings_advanced,
    modify_llm_settings_basic,
    modify_search_api_settings,
)
from openhands.cli.tui import UserCancelledError
from openhands.core.config import OpenHandsConfig
from openhands.storage.data_models.settings import Settings
from openhands.storage.settings.file_settings_store import FileSettingsStore


class MockLLMSummarizingCondenserConfig:

    def __init__(self, llm_config, type, keep_first=4, max_size=120):
        self.llm_config = llm_config
        self.type = type
        self.keep_first = keep_first
        self.max_size = max_size


class MockConversationWindowCondenserConfig:

    def __init__(self, type):
        self.type = type


class MockCondenserPipelineConfig:

    def __init__(self, type, condensers):
        self.type = type
        self.condensers = condensers


class TestDisplaySettings:

    @pytest.fixture
    def app_config(self):
        config = MagicMock(spec=OpenHandsConfig)
        llm_config = MagicMock()
        llm_config.base_url = None
        llm_config.model = "openai/gpt-4"
        llm_config.api_key = SecretStr("test-api-key")
        config.get_llm_config.return_value = llm_config
        config.default_agent = "test-agent"
        config.file_store_path = "/tmp"  # nosec B108 - Safe: test configuration
        security_mock = MagicMock(spec=OpenHandsConfig)
        security_mock.confirmation_mode = True
        config.security = security_mock
        config.enable_default_condenser = True
        config.search_api_key = SecretStr("tvly-test-key")
        return config

    @pytest.fixture
    def advanced_app_config(self):
        config = MagicMock()
        llm_config = MagicMock()
        llm_config.base_url = "https://custom-api.com"
        llm_config.model = "custom-model"
        llm_config.api_key = SecretStr("test-api-key")
        config.get_llm_config.return_value = llm_config
        config.default_agent = "test-agent"
        config.file_store_path = "/tmp"  # nosec B108 - Safe: test configuration
        security_mock = MagicMock()
        security_mock.confirmation_mode = True
        config.security = security_mock
        config.enable_default_condenser = True
        config.search_api_key = SecretStr("tvly-test-key")
        return config

    @patch("openhands.cli.settings.print_container")
    def test_display_settings_standard_config(self, mock_print_container, app_config):
        display_settings(app_config)
        mock_print_container.assert_called_once()
        container = mock_print_container.call_args[0][0]
        text_area = container.body
        settings_text = text_area.text
        assert "LLM Provider:" in settings_text
        assert "openai" in settings_text
        assert "LLM Model:" in settings_text
        assert "gpt-4" in settings_text
        assert "API Key:" in settings_text
        assert "********" in settings_text
        assert "Agent:" in settings_text
        assert "test-agent" in settings_text
        assert "Confirmation Mode:" in settings_text
        assert "Enabled" in settings_text
        assert "Memory Condensation:" in settings_text
        assert "Enabled" in settings_text
        assert "Search API Key:" in settings_text
        assert "********" in settings_text
        assert "Configuration File" in settings_text
        assert str(Path(app_config.file_store_path)) in settings_text

    @patch("openhands.cli.settings.print_container")
    def test_display_settings_advanced_config(self, mock_print_container, advanced_app_config):
        display_settings(advanced_app_config)
        mock_print_container.assert_called_once()
        container = mock_print_container.call_args[0][0]
        text_area = container.body
        settings_text = text_area.text
        assert "Custom Model:" in settings_text
        assert "custom-model" in settings_text
        assert "Base URL:" in settings_text
        assert "https://custom-api.com" in settings_text
        assert "API Key:" in settings_text
        assert "********" in settings_text
        assert "Agent:" in settings_text
        assert "test-agent" in settings_text


class TestModifyLLMSettingsBasic:

    @pytest.fixture
    def app_config(self):
        config = MagicMock(spec=OpenHandsConfig)
        llm_config = MagicMock()
        llm_config.model = "openai/gpt-4"
        llm_config.api_key = SecretStr("test-api-key")
        llm_config.base_url = None
        config.get_llm_config.return_value = llm_config
        config.set_llm_config = MagicMock()
        config.set_agent_config = MagicMock()
        agent_config = MagicMock()
        config.get_agent_config.return_value = agent_config
        security_mock = MagicMock()
        security_mock.confirmation_mode = True
        config.security = security_mock
        return config

    @pytest.fixture
    def settings_store(self):
        store = MagicMock(spec=FileSettingsStore)
        store.load = AsyncMock(return_value=Settings())
        store.store = AsyncMock()
        return store

    @pytest.mark.asyncio
    @patch("openhands.cli.settings.get_supported_llm_models")
    @patch("openhands.cli.settings.organize_models_and_providers")
    @patch("openhands.cli.settings.PromptSession")
    @patch("openhands.cli.settings.cli_confirm")
    @patch("openhands.cli.settings.LLMSummarizingCondenserConfig", MockLLMSummarizingCondenserConfig)
    async def test_modify_llm_settings_basic_success(
        self, mock_confirm, mock_session, mock_organize, mock_get_models, app_config, settings_store
    ):
        mock_get_models.return_value = ["openai/gpt-4", "anthropic/claude-3-opus"]
        mock_organize.return_value = {
            "openai": {"models": ["gpt-4", "gpt-3.5-turbo"], "separator": "/"},
            "anthropic": {"models": ["claude-3-opus", "claude-3-sonnet"], "separator": "/"},
        }
        session_instance = MagicMock()
        session_instance.prompt_async = AsyncMock(side_effect=["gpt-4", "new-api-key"])
        mock_session.return_value = session_instance
        mock_confirm.side_effect = [0, 1, 0]
        await modify_llm_settings_basic(app_config, settings_store)
        app_config.set_llm_config.assert_called_once()
        args, kwargs = app_config.set_llm_config.call_args
        assert "gpt-4" in args[0].model
        assert args[0].api_key.get_secret_value() == "new-api-key"
        assert args[0].base_url is None
        settings_store.store.assert_called_once()
        args, kwargs = settings_store.store.call_args
        settings = args[0]
        assert "gpt-4" in settings.llm_model
        assert settings.llm_api_key.get_secret_value() == "new-api-key"
        assert settings.llm_base_url is None

    @pytest.mark.asyncio
    @patch("openhands.cli.settings.get_supported_llm_models")
    @patch("openhands.cli.settings.organize_models_and_providers")
    @patch("openhands.cli.settings.PromptSession")
    @patch("openhands.cli.settings.cli_confirm")
    @patch("openhands.cli.settings.LLMSummarizingCondenserConfig", MockLLMSummarizingCondenserConfig)
    async def test_modify_llm_settings_basic_user_cancels(
        self, mock_confirm, mock_session, mock_organize, mock_get_models, app_config, settings_store
    ):
        mock_get_models.return_value = ["openai/gpt-4", "anthropic/claude-3-opus"]
        mock_organize.return_value = {"openai": {"models": ["gpt-4", "gpt-3.5-turbo"], "separator": "/"}}
        session_instance = MagicMock()
        session_instance.prompt_async = AsyncMock(side_effect=UserCancelledError())
        mock_session.return_value = session_instance
        await modify_llm_settings_basic(app_config, settings_store)
        app_config.set_llm_config.assert_not_called()
        settings_store.store.assert_not_called()

    @pytest.mark.asyncio
    @patch("openhands.cli.settings.get_supported_llm_models")
    @patch("openhands.cli.settings.organize_models_and_providers")
    @patch("openhands.cli.settings.PromptSession")
    @patch("openhands.cli.settings.cli_confirm")
    @patch("openhands.cli.settings.print_formatted_text")
    @patch("openhands.cli.settings.LLMSummarizingCondenserConfig", MockLLMSummarizingCondenserConfig)
    async def test_modify_llm_settings_basic_invalid_provider_input(
        self, mock_print, mock_confirm, mock_session, mock_organize, mock_get_models, app_config, settings_store
    ):
        mock_get_models.return_value = ["openai/gpt-4", "anthropic/claude-3-opus"]
        mock_organize.return_value = {"openai": {"models": ["gpt-4", "gpt-3.5-turbo"], "separator": "/"}}
        session_instance = MagicMock()
        session_instance.prompt_async = AsyncMock(
            side_effect=["invalid-provider", "openai", "custom-model", "new-api-key"]
        )
        mock_session.return_value = session_instance
        mock_confirm.side_effect = [1, 1, 0]
        await modify_llm_settings_basic(app_config, settings_store)
        assert mock_print.call_count >= 2
        provider_error_found = False
        model_warning_found = False
        for call in mock_print.call_args_list:
            args, _ = call
            if args and isinstance(args[0], HTML):
                if "Invalid provider selected" in args[0].value:
                    provider_error_found = True
                if "Warning:" in args[0].value and "custom-model" in args[0].value:
                    model_warning_found = True
        assert provider_error_found, "No error message for invalid provider"
        assert model_warning_found, "No warning message for custom model"
        app_config.set_llm_config.assert_called_once()
        settings_store.store.assert_called_once()
        args, kwargs = settings_store.store.call_args
        settings = args[0]
        assert "custom-model" in settings.llm_model
        assert settings.llm_api_key.get_secret_value() == "new-api-key"
        assert settings.llm_base_url is None

    def test_default_model_selection(self):
        """Test that the default model selection uses the first model in the list."""
        import inspect
        import openhands.cli.settings as settings_module

        source_lines = inspect.getsource(settings_module.modify_llm_settings_basic).splitlines()
        default_model_block = []
        in_default_model_block = False
        for line in source_lines:
            if "# Set default model to the best verified model for the provider" in line:
                in_default_model_block = True
                default_model_block.append(line)
            elif in_default_model_block:
                default_model_block.append(line)
                if "# Show the default model" in line:
                    break
        assert default_model_block, "Could not find the block that sets the default model"
        print("Default model block found:")
        for line in default_model_block:
            print(f"  {line.strip()}")
        first_model_check = any(("provider_models[0]" in line for line in default_model_block))
        assert first_model_check, "Default model selection should use the first model in the list"

    @pytest.mark.asyncio
    @patch("openhands.cli.settings.VERIFIED_PROVIDERS", ["openhands", "anthropic", "openai"])
    @patch("openhands.cli.settings.VERIFIED_ANTHROPIC_MODELS", ["claude-3-opus"])
    @patch("openhands.cli.settings.get_supported_llm_models")
    @patch("openhands.cli.settings.organize_models_and_providers")
    @patch("openhands.cli.settings.PromptSession")
    @patch("openhands.cli.settings.cli_confirm")
    @patch("openhands.cli.settings.print_formatted_text")
    @patch("openhands.cli.settings.LLMSummarizingCondenserConfig", MockLLMSummarizingCondenserConfig)
    async def test_default_provider_print_and_initial_selection(
        self, mock_print, mock_confirm, mock_session, mock_organize, mock_get_models, app_config, settings_store
    ):
        """Verify default provider printing and initial provider selection index."""
        mock_get_models.return_value = ["openhands/o3", "anthropic/claude-3-opus", "openai/gpt-4"]
        mock_organize.return_value = {
            "openhands": {"models": ["o3"], "separator": "/"},
            "anthropic": {"models": ["claude-3-opus"], "separator": "/"},
            "openai": {"models": ["gpt-4"], "separator": "/"},
        }
        session_instance = MagicMock()
        session_instance.prompt_async = AsyncMock(side_effect=["api-key-123"])
        mock_session.return_value = session_instance
        mock_confirm.side_effect = [1, 0, 0]
        await modify_llm_settings_basic(app_config, settings_store)
        default_print_calls = [
            c
            for c in mock_print.call_args_list
            if c and c[0] and isinstance(c[0][0], HTML) and ("Default provider:" in c[0][0].value)
        ]
        assert default_print_calls, "Default provider line was not printed"
        printed_html = default_print_calls[0][0][0].value
        assert "anthropic" in printed_html
        provider_confirm_call = mock_confirm.call_args_list[0]
        assert provider_confirm_call[1]["initial_selection"] == 2

    @pytest.fixture
    def app_config_with_existing(self):
        config = MagicMock(spec=OpenHandsConfig)
        llm_config = MagicMock()
        llm_config.model = "anthropic/claude-3-opus"
        llm_config.api_key = SecretStr("existing-api-key")
        llm_config.base_url = None
        config.get_llm_config.return_value = llm_config
        config.set_llm_config = MagicMock()
        config.set_agent_config = MagicMock()
        agent_config = MagicMock()
        config.get_agent_config.return_value = agent_config
        security_mock = MagicMock()
        security_mock.confirmation_mode = True
        config.security = security_mock
        return config

    @pytest.mark.asyncio
    @patch("openhands.cli.settings.VERIFIED_PROVIDERS", ["openhands", "anthropic"])
    @patch("openhands.cli.settings.VERIFIED_ANTHROPIC_MODELS", ["claude-3-opus", "claude-3-sonnet"])
    @patch("openhands.cli.settings.get_supported_llm_models")
    @patch("openhands.cli.settings.organize_models_and_providers")
    @patch("openhands.cli.settings.PromptSession")
    @patch("openhands.cli.settings.cli_confirm")
    @patch("openhands.cli.settings.LLMSummarizingCondenserConfig", MockLLMSummarizingCondenserConfig)
    async def test_modify_llm_settings_basic_keep_existing_values(
        self, mock_confirm, mock_session, mock_organize, mock_get_models, app_config_with_existing, settings_store
    ):
        """Test keeping existing configuration values by pressing Enter/selecting defaults."""
        mock_get_models.return_value = ["anthropic/claude-3-opus", "openai/gpt-4"]
        mock_organize.return_value = {
            "openhands": {"models": [], "separator": "/"},
            "anthropic": {"models": ["claude-3-opus", "claude-3-sonnet"], "separator": "/"},
        }
        session_instance = MagicMock()
        session_instance.prompt_async = AsyncMock(side_effect=[""])
        mock_session.return_value = session_instance
        mock_confirm.side_effect = [1, 0, 0]
        await modify_llm_settings_basic(app_config_with_existing, settings_store)
        provider_confirm_call = mock_confirm.call_args_list[0]
        assert provider_confirm_call[1]["initial_selection"] == 1
        model_confirm_call = mock_confirm.call_args_list[1]
        assert "initial_selection" in model_confirm_call[1]
        assert model_confirm_call[1]["initial_selection"] == 0
        api_key_prompt_call = session_instance.prompt_async.call_args_list[0]
        prompt_text = api_key_prompt_call[0][0]
        assert "exis***-key" in prompt_text
        assert "ENTER to keep current" in prompt_text
        settings_store.store.assert_called_once()
        args, kwargs = settings_store.store.call_args
        settings = args[0]
        assert settings.llm_model == "anthropic/claude-3-opus"
        assert settings.llm_api_key.get_secret_value() == "existing-api-key"

    @pytest.mark.asyncio
    @patch("openhands.cli.settings.VERIFIED_PROVIDERS", ["openhands", "anthropic"])
    @patch("openhands.cli.settings.VERIFIED_ANTHROPIC_MODELS", ["claude-3-opus", "claude-3-sonnet"])
    @patch("openhands.cli.settings.get_supported_llm_models")
    @patch("openhands.cli.settings.organize_models_and_providers")
    @patch("openhands.cli.settings.PromptSession")
    @patch("openhands.cli.settings.cli_confirm")
    @patch("openhands.cli.settings.LLMSummarizingCondenserConfig", MockLLMSummarizingCondenserConfig)
    async def test_modify_llm_settings_basic_change_only_api_key(
        self, mock_confirm, mock_session, mock_organize, mock_get_models, app_config_with_existing, settings_store
    ):
        """Test changing only the API key while keeping provider and model."""
        mock_get_models.return_value = ["anthropic/claude-3-opus"]
        mock_organize.return_value = {
            "openhands": {"models": [], "separator": "/"},
            "anthropic": {"models": ["claude-3-opus", "claude-3-sonnet"], "separator": "/"},
        }
        session_instance = MagicMock()
        session_instance.prompt_async = AsyncMock(side_effect=["new-api-key-12345"])
        mock_session.return_value = session_instance
        mock_confirm.side_effect = [1, 0, 0]
        await modify_llm_settings_basic(app_config_with_existing, settings_store)
        settings_store.store.assert_called_once()
        args, kwargs = settings_store.store.call_args
        settings = args[0]
        assert settings.llm_model == "anthropic/claude-3-opus"
        assert settings.llm_api_key.get_secret_value() == "new-api-key-12345"

    @pytest.mark.asyncio
    @patch("openhands.cli.settings.VERIFIED_PROVIDERS", ["openhands", "anthropic"])
    @patch(
        "openhands.cli.settings.VERIFIED_OPENHANDS_MODELS", ["claude-sonnet-4-20250514", "claude-opus-4-20250514", "o3"]
    )
    @patch("openhands.cli.settings.get_supported_llm_models")
    @patch("openhands.cli.settings.organize_models_and_providers")
    @patch("openhands.cli.settings.PromptSession")
    @patch("openhands.cli.settings.cli_confirm")
    @patch("openhands.cli.settings.LLMSummarizingCondenserConfig", MockLLMSummarizingCondenserConfig)
    async def test_modify_llm_settings_basic_change_provider_and_model(
        self, mock_confirm, mock_session, mock_organize, mock_get_models, app_config_with_existing, settings_store
    ):
        """Test changing provider and model requires re-entering API key when provider changes."""
        mock_get_models.return_value = [
            "openhands/claude-sonnet-4-20250514",
            "openhands/claude-opus-4-20250514",
            "openhands/o3",
        ]
        mock_organize.return_value = {
            "openhands": {"models": ["claude-sonnet-4-20250514", "claude-opus-4-20250514", "o3"], "separator": "/"},
            "anthropic": {"models": ["claude-3-opus", "claude-3-sonnet"], "separator": "/"},
        }
        session_instance = MagicMock()
        session_instance.prompt_async = AsyncMock(side_effect=["new-api-key-after-provider-change"])
        mock_session.return_value = session_instance
        mock_confirm.side_effect = [0, 2, 0]
        await modify_llm_settings_basic(app_config_with_existing, settings_store)
        api_key_prompt_call = session_instance.prompt_async.call_args_list[0]
        prompt_text = api_key_prompt_call[0][0]
        assert "***" not in prompt_text
        assert "ENTER to keep current" not in prompt_text
        settings_store.store.assert_called_once()
        args, kwargs = settings_store.store.call_args
        settings = args[0]
        assert settings.llm_model == "openhands/o3"
        assert settings.llm_api_key.get_secret_value() == "new-api-key-after-provider-change"

    @pytest.mark.asyncio
    @patch("openhands.cli.settings.VERIFIED_PROVIDERS", ["openhands", "anthropic"])
    @patch("openhands.cli.settings.VERIFIED_OPENHANDS_MODELS", ["anthropic/claude-3-opus", "anthropic/claude-3-sonnet"])
    @patch("openhands.cli.settings.VERIFIED_ANTHROPIC_MODELS", ["claude-sonnet-4-20250514", "claude-3-opus"])
    @patch("openhands.cli.settings.get_supported_llm_models")
    @patch("openhands.cli.settings.organize_models_and_providers")
    @patch("openhands.cli.settings.PromptSession")
    @patch("openhands.cli.settings.cli_confirm")
    @patch("openhands.cli.settings.LLMSummarizingCondenserConfig", MockLLMSummarizingCondenserConfig)
    async def test_modify_llm_settings_basic_from_scratch(
        self, mock_confirm, mock_session, mock_organize, mock_get_models, settings_store
    ):
        """Test setting up LLM configuration from scratch (no existing settings)."""
        config = MagicMock(spec=OpenHandsConfig)
        llm_config = MagicMock()
        llm_config.model = None
        llm_config.api_key = None
        llm_config.base_url = None
        config.get_llm_config.return_value = llm_config
        config.set_llm_config = MagicMock()
        config.set_agent_config = MagicMock()
        agent_config = MagicMock()
        config.get_agent_config.return_value = agent_config
        security_mock = MagicMock()
        security_mock.confirmation_mode = True
        config.security = security_mock
        config.enable_default_condenser = True
        config.default_agent = "test-agent"
        config.file_store_path = "/tmp"  # nosec B108 - Safe: test configuration
        mock_get_models.return_value = ["anthropic/claude-sonnet-4-20250514", "anthropic/claude-3-opus"]
        mock_organize.return_value = {
            "openhands": {"models": [], "separator": "/"},
            "anthropic": {"models": ["claude-sonnet-4-20250514", "claude-3-opus"], "separator": "/"},
        }
        session_instance = MagicMock()
        session_instance.prompt_async = AsyncMock(side_effect=["new-api-key-12345"])
        mock_session.return_value = session_instance
        mock_confirm.side_effect = [1, 0, 0]
        await modify_llm_settings_basic(config, settings_store)
        provider_confirm_call = mock_confirm.call_args_list[0]
        assert provider_confirm_call[1]["initial_selection"] == 1
        model_confirm_call = mock_confirm.call_args_list[1]
        assert "initial_selection" in model_confirm_call[1]
        assert model_confirm_call[1]["initial_selection"] == 0
        api_key_prompt_call = session_instance.prompt_async.call_args_list[0]
        prompt_text = api_key_prompt_call[0][0]
        assert "***" not in prompt_text
        assert "ENTER to keep current" not in prompt_text
        settings_store.store.assert_called_once()
        args, kwargs = settings_store.store.call_args
        settings = args[0]
        assert settings.llm_model == "anthropic/claude-sonnet-4-20250514"
        assert settings.llm_api_key.get_secret_value() == "new-api-key-12345"


class TestModifyLLMSettingsAdvanced:

    @pytest.fixture
    def app_config(self):
        config = MagicMock(spec=OpenHandsConfig)
        llm_config = MagicMock()
        llm_config.model = "custom-model"
        llm_config.api_key = SecretStr("test-api-key")
        llm_config.base_url = "https://custom-api.com"
        config.get_llm_config.return_value = llm_config
        config.set_llm_config = MagicMock()
        config.set_agent_config = MagicMock()
        config.default_agent = "test-agent"
        config.enable_default_condenser = True
        agent_config = MagicMock()
        config.get_agent_config.return_value = agent_config
        security_mock = MagicMock()
        security_mock.confirmation_mode = True
        config.security = security_mock
        return config

    @pytest.fixture
    def settings_store(self):
        store = MagicMock(spec=FileSettingsStore)
        store.load = AsyncMock(return_value=Settings())
        store.store = AsyncMock()
        return store

    @pytest.mark.asyncio
    @patch("openhands.cli.settings.Agent.list_agents")
    @patch("openhands.cli.settings.PromptSession")
    @patch("openhands.cli.settings.cli_confirm")
    @patch("openhands.cli.settings.LLMSummarizingCondenserConfig", MockLLMSummarizingCondenserConfig)
    @patch("openhands.cli.settings.ConversationWindowCondenserConfig", MockConversationWindowCondenserConfig)
    @patch("openhands.cli.settings.CondenserPipelineConfig", MockCondenserPipelineConfig)
    async def test_modify_llm_settings_advanced_success(
        self, mock_confirm, mock_session, mock_list_agents, app_config, settings_store
    ):
        mock_list_agents.return_value = ["default", "test-agent"]
        session_instance = MagicMock()
        session_instance.prompt_async = AsyncMock(
            side_effect=["new-model", "https://new-url", "new-api-key", "default"]
        )
        mock_session.return_value = session_instance
        mock_confirm.side_effect = [0, 0, 0]
        await modify_llm_settings_advanced(app_config, settings_store)
        app_config.set_llm_config.assert_called_once()
        args, kwargs = app_config.set_llm_config.call_args
        assert args[0].model == "new-model"
        assert args[0].api_key.get_secret_value() == "new-api-key"
        assert args[0].base_url == "https://new-url"
        settings_store.store.assert_called_once()
        args, kwargs = settings_store.store.call_args
        settings = args[0]
        assert settings.llm_model == "new-model"
        assert settings.llm_api_key.get_secret_value() == "new-api-key"
        assert settings.llm_base_url == "https://new-url"
        assert settings.agent == "default"
        assert settings.confirmation_mode is True
        assert settings.enable_default_condenser is True

    @pytest.mark.asyncio
    @patch("openhands.cli.settings.Agent.list_agents")
    @patch("openhands.cli.settings.PromptSession")
    @patch("openhands.cli.settings.cli_confirm")
    @patch("openhands.cli.settings.LLMSummarizingCondenserConfig", MockLLMSummarizingCondenserConfig)
    @patch("openhands.cli.settings.ConversationWindowCondenserConfig", MockConversationWindowCondenserConfig)
    async def test_modify_llm_settings_advanced_user_cancels(
        self, mock_confirm, mock_session, mock_list_agents, app_config, settings_store
    ):
        mock_list_agents.return_value = ["default", "test-agent"]
        session_instance = MagicMock()
        session_instance.prompt_async = AsyncMock(side_effect=UserCancelledError())
        mock_session.return_value = session_instance
        await modify_llm_settings_advanced(app_config, settings_store)
        app_config.set_llm_config.assert_not_called()
        settings_store.store.assert_not_called()

    @pytest.mark.asyncio
    @patch("openhands.cli.settings.Agent.list_agents")
    @patch("openhands.cli.settings.PromptSession")
    @patch("openhands.cli.settings.cli_confirm")
    @patch("openhands.cli.settings.print_formatted_text")
    @patch("openhands.cli.settings.LLMSummarizingCondenserConfig", MockLLMSummarizingCondenserConfig)
    @patch("openhands.cli.settings.ConversationWindowCondenserConfig", MockConversationWindowCondenserConfig)
    async def test_modify_llm_settings_advanced_invalid_agent(
        self, mock_print, mock_confirm, mock_session, mock_list_agents, app_config, settings_store
    ):
        mock_list_agents.return_value = ["default", "test-agent"]
        session_instance = MagicMock()
        session_instance.prompt_async = AsyncMock(
            side_effect=["new-model", "https://new-url", "new-api-key", "invalid-agent", "default"]
        )
        mock_session.return_value = session_instance
        await modify_llm_settings_advanced(app_config, settings_store)
        assert mock_print.call_count == 3
        error_message_call = mock_print.call_args_list[1]
        args, kwargs = error_message_call
        assert isinstance(args[0], HTML)
        assert "Invalid agent" in args[0].value
        app_config.set_llm_config.assert_not_called()
        settings_store.store.assert_not_called()

    @pytest.mark.asyncio
    @patch("openhands.cli.settings.Agent.list_agents")
    @patch("openhands.cli.settings.PromptSession")
    @patch("openhands.cli.settings.cli_confirm")
    @patch("openhands.cli.settings.LLMSummarizingCondenserConfig", MockLLMSummarizingCondenserConfig)
    @patch("openhands.cli.settings.ConversationWindowCondenserConfig", MockConversationWindowCondenserConfig)
    async def test_modify_llm_settings_advanced_user_rejects_save(
        self, mock_confirm, mock_session, mock_list_agents, app_config, settings_store
    ):
        mock_list_agents.return_value = ["default", "test-agent"]
        session_instance = MagicMock()
        session_instance.prompt_async = AsyncMock(
            side_effect=["new-model", "https://new-url", "new-api-key", "default"]
        )
        mock_session.return_value = session_instance
        mock_confirm.side_effect = [0, 0, 1]
        await modify_llm_settings_advanced(app_config, settings_store)
        app_config.set_llm_config.assert_not_called()
        settings_store.store.assert_not_called()

    @pytest.fixture
    def app_config_with_existing(self):
        config = MagicMock(spec=OpenHandsConfig)
        llm_config = MagicMock()
        llm_config.model = "custom-existing-model"
        llm_config.api_key = SecretStr("existing-advanced-key")
        llm_config.base_url = "https://existing-api.com"
        config.get_llm_config.return_value = llm_config
        config.set_llm_config = MagicMock()
        config.set_agent_config = MagicMock()
        config.default_agent = "existing-agent"
        config.enable_default_condenser = False
        agent_config = MagicMock()
        config.get_agent_config.return_value = agent_config
        security_mock = MagicMock()
        security_mock.confirmation_mode = False
        config.security = security_mock
        return config

    @pytest.mark.asyncio
    @patch("openhands.cli.settings.Agent.list_agents")
    @patch("openhands.cli.settings.PromptSession")
    @patch("openhands.cli.settings.cli_confirm")
    @patch("openhands.cli.settings.LLMSummarizingCondenserConfig", MockLLMSummarizingCondenserConfig)
    @patch("openhands.cli.settings.ConversationWindowCondenserConfig", MockConversationWindowCondenserConfig)
    @patch("openhands.cli.settings.CondenserPipelineConfig", MockCondenserPipelineConfig)
    async def test_modify_llm_settings_advanced_keep_existing_values(
        self, mock_confirm, mock_session, mock_list_agents, app_config_with_existing, settings_store
    ):
        """Test keeping all existing values in advanced settings by pressing Enter."""
        mock_list_agents.return_value = ["default", "existing-agent", "test-agent"]
        session_instance = MagicMock()
        session_instance.prompt_async = AsyncMock(
            side_effect=["custom-existing-model", "https://existing-api.com", "", "existing-agent"]
        )
        mock_session.return_value = session_instance
        mock_confirm.side_effect = [1, 1, 0]
        await modify_llm_settings_advanced(app_config_with_existing, settings_store)
        prompt_calls = session_instance.prompt_async.call_args_list
        assert prompt_calls[0][1]["default"] == "custom-existing-model"
        assert prompt_calls[1][1]["default"] == "https://existing-api.com"
        api_key_prompt = prompt_calls[2][0][0]
        assert "exis***-key" in api_key_prompt
        assert "ENTER to keep current" in api_key_prompt
        assert prompt_calls[2][1]["default"] == ""
        assert prompt_calls[3][1]["default"] == "existing-agent"
        confirm_calls = mock_confirm.call_args_list
        assert confirm_calls[0][1]["initial_selection"] == 1
        assert confirm_calls[1][1]["initial_selection"] == 1
        settings_store.store.assert_called_once()
        args, kwargs = settings_store.store.call_args
        settings = args[0]
        assert settings.llm_model == "custom-existing-model"
        assert settings.llm_api_key.get_secret_value() == "existing-advanced-key"
        assert settings.llm_base_url == "https://existing-api.com"
        assert settings.agent == "existing-agent"
        assert settings.confirmation_mode is False
        assert settings.enable_default_condenser is False

    @pytest.mark.asyncio
    @patch("openhands.cli.settings.Agent.list_agents")
    @patch("openhands.cli.settings.PromptSession")
    @patch("openhands.cli.settings.cli_confirm")
    @patch("openhands.cli.settings.LLMSummarizingCondenserConfig", MockLLMSummarizingCondenserConfig)
    @patch("openhands.cli.settings.ConversationWindowCondenserConfig", MockConversationWindowCondenserConfig)
    @patch("openhands.cli.settings.CondenserPipelineConfig", MockCondenserPipelineConfig)
    async def test_modify_llm_settings_advanced_partial_change(
        self, mock_confirm, mock_session, mock_list_agents, app_config_with_existing, settings_store
    ):
        """Test changing only some values in advanced settings while keeping others."""
        mock_list_agents.return_value = ["default", "existing-agent", "test-agent"]
        session_instance = MagicMock()
        session_instance.prompt_async = AsyncMock(
            side_effect=["new-custom-model", "https://existing-api.com", "new-api-key-123", "test-agent"]
        )
        mock_session.return_value = session_instance
        mock_confirm.side_effect = [0, 1, 0]
        await modify_llm_settings_advanced(app_config_with_existing, settings_store)
        settings_store.store.assert_called_once()
        args, kwargs = settings_store.store.call_args
        settings = args[0]
        assert settings.llm_model == "new-custom-model"
        assert settings.llm_api_key.get_secret_value() == "new-api-key-123"
        assert settings.llm_base_url == "https://existing-api.com"
        assert settings.agent == "test-agent"
        assert settings.confirmation_mode is True
        assert settings.enable_default_condenser is False

    @pytest.mark.asyncio
    @patch("openhands.cli.settings.Agent.list_agents")
    @patch("openhands.cli.settings.PromptSession")
    @patch("openhands.cli.settings.cli_confirm")
    @patch("openhands.cli.settings.LLMSummarizingCondenserConfig", MockLLMSummarizingCondenserConfig)
    @patch("openhands.cli.settings.ConversationWindowCondenserConfig", MockConversationWindowCondenserConfig)
    @patch("openhands.cli.settings.CondenserPipelineConfig", MockCondenserPipelineConfig)
    async def test_modify_llm_settings_advanced_from_scratch(
        self, mock_confirm, mock_session, mock_list_agents, settings_store
    ):
        """Test setting up advanced configuration from scratch (no existing settings)."""
        config = MagicMock(spec=OpenHandsConfig)
        llm_config = MagicMock()
        llm_config.model = None
        llm_config.api_key = None
        llm_config.base_url = None
        config.get_llm_config.return_value = llm_config
        config.set_llm_config = MagicMock()
        config.set_agent_config = MagicMock()
        config.default_agent = None
        config.enable_default_condenser = True
        agent_config = MagicMock()
        config.get_agent_config.return_value = agent_config
        security_mock = MagicMock()
        security_mock.confirmation_mode = True
        config.security = security_mock
        mock_list_agents.return_value = ["default", "test-agent", "advanced-agent"]
        session_instance = MagicMock()
        session_instance.prompt_async = AsyncMock(
            side_effect=["from-scratch-model", "https://new-api-endpoint.com", "brand-new-api-key", "advanced-agent"]
        )
        mock_session.return_value = session_instance
        mock_confirm.side_effect = [1, 0, 0]
        await modify_llm_settings_advanced(config, settings_store)
        prompt_calls = session_instance.prompt_async.call_args_list
        assert prompt_calls[0][1]["default"] == ""
        assert prompt_calls[1][1]["default"] == ""
        api_key_prompt = prompt_calls[2][0][0]
        assert "***" not in api_key_prompt
        assert "ENTER to keep current" not in api_key_prompt
        assert prompt_calls[2][1]["default"] == ""
        assert prompt_calls[3][1]["default"] == ""
        confirm_calls = mock_confirm.call_args_list
        assert confirm_calls[0][1]["initial_selection"] == 0
        assert confirm_calls[1][1]["initial_selection"] == 0
        settings_store.store.assert_called_once()
        args, kwargs = settings_store.store.call_args
        settings = args[0]
        assert settings.llm_model == "from-scratch-model"
        assert settings.llm_api_key.get_secret_value() == "brand-new-api-key"
        assert settings.llm_base_url == "https://new-api-endpoint.com"
        assert settings.agent == "advanced-agent"
        assert settings.confirmation_mode is False
        assert settings.enable_default_condenser is True


class TestGetValidatedInput:

    @pytest.mark.asyncio
    @patch("openhands.cli.settings.PromptSession")
    async def test_get_validated_input_with_prefill(self, mock_session):
        """Test get_validated_input with default_value prefilled."""
        from openhands.cli.settings import get_validated_input

        session_instance = MagicMock()
        session_instance.prompt_async = AsyncMock(return_value="modified-value")
        result = await get_validated_input(session_instance, "Enter value: ", default_value="existing-value")
        session_instance.prompt_async.assert_called_once_with("Enter value: ", default="existing-value")
        assert result == "modified-value"

    @pytest.mark.asyncio
    @patch("openhands.cli.settings.PromptSession")
    async def test_get_validated_input_empty_returns_current(self, mock_session):
        """Test that pressing Enter with empty input returns enter_keeps_value."""
        from openhands.cli.settings import get_validated_input

        session_instance = MagicMock()
        session_instance.prompt_async = AsyncMock(return_value="  ")
        result = await get_validated_input(
            session_instance, "Enter value: ", default_value="", enter_keeps_value="existing-value"
        )
        session_instance.prompt_async.assert_called_once_with("Enter value: ", default="")
        assert result == "existing-value"

    @pytest.mark.asyncio
    @patch("openhands.cli.settings.PromptSession")
    async def test_get_validated_input_with_validator(self, mock_session):
        """Test get_validated_input with validator and error message."""
        from openhands.cli.settings import get_validated_input

        session_instance = MagicMock()
        session_instance.prompt_async = AsyncMock(side_effect=["invalid", "valid-input"])
        with patch("openhands.cli.settings.print_formatted_text") as mock_print:
            result = await get_validated_input(
                session_instance,
                "Enter value: ",
                validator=lambda x: x.startswith("valid"),
                error_message='Input must start with "valid"',
            )
        assert mock_print.call_count == 3
        error_message_call = mock_print.call_args_list[1]
        args, kwargs = error_message_call
        assert isinstance(args[0], HTML)
        assert 'Input must start with "valid"' in args[0].value
        assert result == "valid-input"


class TestModifySearchApiSettings:

    @pytest.fixture
    def app_config(self):
        config = MagicMock(spec=OpenHandsConfig)
        config.search_api_key = SecretStr("tvly-existing-key")
        return config

    @pytest.fixture
    def settings_store(self):
        store = MagicMock(spec=FileSettingsStore)
        store.load = AsyncMock(return_value=Settings())
        store.store = AsyncMock()
        return store

    @pytest.mark.asyncio
    @patch("openhands.cli.settings.PromptSession")
    @patch("openhands.cli.settings.cli_confirm")
    @patch("openhands.cli.settings.print_formatted_text")
    async def test_modify_search_api_settings_set_new_key(
        self, mock_print, mock_confirm, mock_session, app_config, settings_store
    ):
        session_instance = MagicMock()
        session_instance.prompt_async = AsyncMock(return_value="tvly-new-key")
        mock_session.return_value = session_instance
        mock_confirm.side_effect = [0, 0]
        await modify_search_api_settings(app_config, settings_store)
        assert app_config.search_api_key.get_secret_value() == "tvly-new-key"
        settings_store.store.assert_called_once()
        args, kwargs = settings_store.store.call_args
        settings = args[0]
        assert settings.search_api_key.get_secret_value() == "tvly-new-key"

    @pytest.mark.asyncio
    @patch("openhands.cli.settings.PromptSession")
    @patch("openhands.cli.settings.cli_confirm")
    @patch("openhands.cli.settings.print_formatted_text")
    async def test_modify_search_api_settings_remove_key(
        self, mock_print, mock_confirm, mock_session, app_config, settings_store
    ):
        session_instance = MagicMock()
        mock_session.return_value = session_instance
        mock_confirm.side_effect = [1, 0]
        await modify_search_api_settings(app_config, settings_store)
        assert app_config.search_api_key is None
        settings_store.store.assert_called_once()
        args, kwargs = settings_store.store.call_args
        settings = args[0]
        assert settings.search_api_key is None

    @pytest.mark.asyncio
    @patch("openhands.cli.settings.PromptSession")
    @patch("openhands.cli.settings.cli_confirm")
    @patch("openhands.cli.settings.print_formatted_text")
    async def test_modify_search_api_settings_keep_current(
        self, mock_print, mock_confirm, mock_session, app_config, settings_store
    ):
        session_instance = MagicMock()
        mock_session.return_value = session_instance
        mock_confirm.return_value = 2
        await modify_search_api_settings(app_config, settings_store)
        settings_store.store.assert_not_called()
