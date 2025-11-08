import os
from unittest.mock import ANY, MagicMock, patch
from forge.core.config import CLIConfig, ForgeConfig


class TestCliViMode:
    """Test the VI mode feature."""

    @patch("forge.cli.tui.PromptSession")
    def test_create_prompt_session_vi_mode_enabled(self, mock_prompt_session):
        """Test that vi_mode can be enabled."""
        from forge.cli.tui import create_prompt_session

        config = ForgeConfig(cli=CLIConfig(vi_mode=True))
        create_prompt_session(config)
        mock_prompt_session.assert_called_with(style=ANY, vi_mode=True)

    @patch("forge.cli.tui.PromptSession")
    def test_create_prompt_session_vi_mode_disabled(self, mock_prompt_session):
        """Test that vi_mode is disabled by default."""
        from forge.cli.tui import create_prompt_session

        config = ForgeConfig(cli=CLIConfig(vi_mode=False))
        create_prompt_session(config)
        mock_prompt_session.assert_called_with(style=ANY, vi_mode=False)

    @patch("forge.cli.tui.Application")
    def test_cli_confirm_vi_keybindings_are_added(self, mock_app_class):
        """Test that vi keybindings are added to the KeyBindings object."""
        from forge.cli.tui import cli_confirm

        config = ForgeConfig(cli=CLIConfig(vi_mode=True))
        with patch("forge.cli.tui.KeyBindings", MagicMock()) as mock_key_bindings:
            cli_confirm(config, "Test question", choices=["Choice 1", "Choice 2", "Choice 3"])
            assert mock_key_bindings.call_count == 1
            mock_kb_instance = mock_key_bindings.return_value
            assert mock_kb_instance.add.call_count > 0

    @patch("forge.cli.tui.Application")
    def test_cli_confirm_vi_keybindings_are_not_added(self, mock_app_class):
        """Test that vi keybindings are not added when vi_mode is False."""
        from forge.cli.tui import cli_confirm

        config = ForgeConfig(cli=CLIConfig(vi_mode=False))
        with patch("forge.cli.tui.KeyBindings", MagicMock()) as mock_key_bindings:
            cli_confirm(config, "Test question", choices=["Choice 1", "Choice 2", "Choice 3"])
            assert mock_key_bindings.call_count == 1
            mock_kb_instance = mock_key_bindings.return_value
            for call in mock_kb_instance.add.call_args_list:
                assert call[0][0] not in ("j", "k")

    @patch.dict(os.environ, {}, clear=True)
    def test_vi_mode_disabled_by_default(self):
        """Test that vi_mode is disabled by default when no env var is set."""
        from forge.core.config.utils import load_from_env

        config = ForgeConfig()
        load_from_env(config, os.environ)
        assert config.cli.vi_mode is False, "vi_mode should be False by default"

    @patch.dict(os.environ, {"CLI_VI_MODE": "True"})
    def test_vi_mode_enabled_from_env(self):
        """Test that vi_mode can be enabled from an environment variable."""
        from forge.core.config.utils import load_from_env

        config = ForgeConfig()
        load_from_env(config, os.environ)
        assert config.cli.vi_mode is True, "vi_mode should be True when CLI_VI_MODE is set"
