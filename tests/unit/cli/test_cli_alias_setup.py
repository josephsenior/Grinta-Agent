"""Unit tests for CLI alias setup functionality."""

import tempfile
from pathlib import Path
from unittest.mock import patch
from forge.cli.main import alias_setup_declined as main_alias_setup_declined
from forge.cli.main import aliases_exist_in_shell_config, run_alias_setup_flow
from forge.cli.shell_config import (
    ShellConfigManager,
    add_aliases_to_shell_config,
    alias_setup_declined,
    get_shell_config_path,
    mark_alias_setup_declined,
)
from forge.core.config import ForgeConfig


def test_get_shell_config_path_no_files_fallback():
    """Test shell config path fallback when no shell detection and no config files exist."""
    with tempfile.TemporaryDirectory() as temp_dir:
        with patch("forge.cli.shell_config.Path.home", return_value=Path(temp_dir)):
            with patch("shellingham.detect_shell", side_effect=Exception("Shell detection failed")):
                profile_path = get_shell_config_path()
                import platform

                if platform.system() == "Windows":
                    assert profile_path.name.endswith("_profile.ps1")
                else:
                    assert profile_path.name == ".bash_profile"


def test_get_shell_config_path_bash_fallback():
    """Test shell config path fallback to bash when it exists."""
    with tempfile.TemporaryDirectory() as temp_dir:
        with patch("forge.cli.shell_config.Path.home", return_value=Path(temp_dir)):
            bashrc = Path(temp_dir) / ".bashrc"
            bashrc.touch()
            with patch("shellingham.detect_shell", side_effect=Exception("Shell detection failed")):
                profile_path = get_shell_config_path()
                import platform

                if platform.system() == "Windows":
                    assert profile_path.name.endswith("_profile.ps1")
                else:
                    assert profile_path.name == ".bashrc"


def test_get_shell_config_path_with_bash_detection():
    """Test shell config path when bash is detected."""
    with tempfile.TemporaryDirectory() as temp_dir:
        with patch("forge.cli.shell_config.Path.home", return_value=Path(temp_dir)):
            bashrc = Path(temp_dir) / ".bashrc"
            bashrc.touch()
            with patch("shellingham.detect_shell", return_value=("bash", "bash")):
                profile_path = get_shell_config_path()
                assert profile_path.name == ".bashrc"


def test_get_shell_config_path_with_zsh_detection():
    """Test shell config path when zsh is detected."""
    with tempfile.TemporaryDirectory() as temp_dir:
        with patch("forge.cli.shell_config.Path.home", return_value=Path(temp_dir)):
            zshrc = Path(temp_dir) / ".zshrc"
            zshrc.touch()
            with patch("shellingham.detect_shell", return_value=("zsh", "zsh")):
                profile_path = get_shell_config_path()
                assert profile_path.name == ".zshrc"


def test_get_shell_config_path_with_fish_detection():
    """Test shell config path when fish is detected."""
    with tempfile.TemporaryDirectory() as temp_dir:
        with patch("forge.cli.shell_config.Path.home", return_value=Path(temp_dir)):
            fish_config_dir = Path(temp_dir) / ".config" / "fish"
            fish_config_dir.mkdir(parents=True)
            fish_config = fish_config_dir / "config.fish"
            fish_config.touch()
            with patch("shellingham.detect_shell", return_value=("fish", "fish")):
                profile_path = get_shell_config_path()
                assert profile_path.name == "config.fish"
                assert "fish" in str(profile_path)


def test_add_aliases_to_shell_config_bash():
    """Test adding aliases to bash config."""
    with tempfile.TemporaryDirectory() as temp_dir:
        with patch("forge.cli.shell_config.Path.home", return_value=Path(temp_dir)):
            with patch("shellingham.detect_shell", return_value=("bash", "bash")):
                success = add_aliases_to_shell_config()
                assert success is True
                with patch("shellingham.detect_shell", return_value=("bash", "bash")):
                    profile_path = get_shell_config_path()
                with open(profile_path, "r", encoding='utf-8') as f:
                    content = f.read()
                    assert "alias Forge=" in content
                    assert "alias oh=" in content
                    assert "uvx --python 3.12 --from forge-ai Forge" in content


def test_add_aliases_to_shell_config_zsh():
    """Test adding aliases to zsh config."""
    with tempfile.TemporaryDirectory() as temp_dir:
        with patch("forge.cli.shell_config.Path.home", return_value=Path(temp_dir)):
            with patch("shellingham.detect_shell", return_value=("zsh", "zsh")):
                success = add_aliases_to_shell_config()
                assert success is True
                profile_path = Path(temp_dir) / ".zshrc"
                with open(profile_path, "r", encoding='utf-8') as f:
                    content = f.read()
                    assert "alias Forge=" in content
                    assert "alias oh=" in content
                    assert "uvx --python 3.12 --from forge-ai Forge" in content


def test_add_aliases_handles_existing_aliases():
    """Test that adding aliases handles existing aliases correctly."""
    with tempfile.TemporaryDirectory() as temp_dir:
        with patch("forge.cli.shell_config.Path.home", return_value=Path(temp_dir)):
            with patch("shellingham.detect_shell", return_value=("bash", "bash")):
                success = add_aliases_to_shell_config()
                assert success is True
                success = add_aliases_to_shell_config()
                assert success is True
                with patch("shellingham.detect_shell", return_value=("bash", "bash")):
                    profile_path = get_shell_config_path()
                with open(profile_path, "r", encoding='utf-8') as f:
                    content = f.read()
                    FORGE_count = content.count("alias Forge=")
                    oh_count = content.count("alias oh=")
                    assert FORGE_count == 1
                    assert oh_count == 1


def test_aliases_exist_in_shell_config_no_file():
    """Test alias detection when no shell config exists."""
    with tempfile.TemporaryDirectory() as temp_dir:
        with patch("forge.cli.shell_config.Path.home", return_value=Path(temp_dir)):
            with patch("shellingham.detect_shell", return_value=("bash", "bash")):
                assert aliases_exist_in_shell_config() is False


def test_aliases_exist_in_shell_config_no_aliases():
    """Test alias detection when shell config exists but has no aliases."""
    with tempfile.TemporaryDirectory() as temp_dir:
        with patch("forge.cli.shell_config.Path.home", return_value=Path(temp_dir)):
            with patch("shellingham.detect_shell", return_value=("bash", "bash")):
                profile_path = get_shell_config_path()
                with open(profile_path, "w", encoding='utf-8') as f:
                    f.write("export PATH=$PATH:/usr/local/bin\n")
                assert aliases_exist_in_shell_config() is False


def test_aliases_exist_in_shell_config_with_aliases():
    """Test alias detection when aliases exist."""
    with tempfile.TemporaryDirectory() as temp_dir:
        with patch("forge.cli.shell_config.Path.home", return_value=Path(temp_dir)):
            with patch("shellingham.detect_shell", return_value=("bash", "bash")):
                add_aliases_to_shell_config()
                assert aliases_exist_in_shell_config() is True


def test_shell_config_manager_basic_functionality():
    """Test basic ShellConfigManager functionality."""
    manager = ShellConfigManager()
    custom_manager = ShellConfigManager(command="custom-command")
    assert custom_manager.command == "custom-command"
    assert manager.get_shell_type_from_path(Path("/home/user/.bashrc")) == "bash"
    assert manager.get_shell_type_from_path(Path("/home/user/.zshrc")) == "zsh"
    assert manager.get_shell_type_from_path(Path("/home/user/.config/fish/config.fish")) == "fish"


def test_shell_config_manager_reload_commands():
    """Test reload command generation."""
    manager = ShellConfigManager()
    assert "source ~/.zshrc" in manager.get_reload_command(Path("/home/user/.zshrc"))
    assert "source ~/.bashrc" in manager.get_reload_command(Path("/home/user/.bashrc"))
    assert "source ~/.bash_profile" in manager.get_reload_command(Path("/home/user/.bash_profile"))
    assert "source ~/.config/fish/config.fish" in manager.get_reload_command(
        Path("/home/user/.config/fish/config.fish")
    )


def test_shell_config_manager_template_rendering():
    """Test that templates are properly rendered."""
    manager = ShellConfigManager(command="test-command")
    with tempfile.TemporaryDirectory() as temp_dir:
        with patch("forge.cli.shell_config.Path.home", return_value=Path(temp_dir)):
            bashrc = Path(temp_dir) / ".bashrc"
            bashrc.touch()
            with patch.object(manager, "detect_shell", return_value="bash"):
                success = manager.add_aliases()
                assert success is True
                with open(bashrc, "r", encoding='utf-8') as f:
                    content = f.read()
                    assert "test-command" in content
                    assert 'alias Forge="test-command"' in content
                    assert 'alias oh="test-command"' in content


def test_alias_setup_declined_false():
    """Test alias setup declined check when marker file doesn't exist."""
    with tempfile.TemporaryDirectory() as temp_dir:
        with patch("forge.cli.shell_config.Path.home", return_value=Path(temp_dir)):
            assert alias_setup_declined() is False


def test_alias_setup_declined_true():
    """Test alias setup declined check when marker file exists."""
    with tempfile.TemporaryDirectory() as temp_dir:
        with patch("forge.cli.shell_config.Path.home", return_value=Path(temp_dir)):
            mark_alias_setup_declined()
            assert alias_setup_declined() is True


def test_mark_alias_setup_declined():
    """Test marking alias setup as declined creates the marker file."""
    with tempfile.TemporaryDirectory() as temp_dir:
        with patch("forge.cli.shell_config.Path.home", return_value=Path(temp_dir)):
            assert alias_setup_declined() is False
            mark_alias_setup_declined()
            assert alias_setup_declined() is True
            marker_file = Path(temp_dir) / ".Forge" / ".cli_alias_setup_declined"
            assert marker_file.exists()


def test_alias_setup_declined_persisted():
    """Test that when user declines alias setup, their choice is persisted."""
    config = ForgeConfig()
    with tempfile.TemporaryDirectory() as temp_dir:
        with patch("forge.cli.shell_config.Path.home", return_value=Path(temp_dir)):
            with patch("shellingham.detect_shell", return_value=("bash", "bash")):
                with patch("forge.cli.shell_config.aliases_exist_in_shell_config", return_value=False):
                    with patch("forge.cli.main.cli_confirm", return_value=1):
                        with patch("prompt_toolkit.print_formatted_text"):
                            assert not alias_setup_declined()
                            run_alias_setup_flow(config)
                            assert alias_setup_declined()


def test_alias_setup_skipped_when_previously_declined():
    """Test that alias setup is skipped when user has previously declined."""
    ForgeConfig()
    with tempfile.TemporaryDirectory() as temp_dir:
        with patch("forge.cli.shell_config.Path.home", return_value=Path(temp_dir)):
            mark_alias_setup_declined()
            assert alias_setup_declined()
            with patch("shellingham.detect_shell", return_value=("bash", "bash")):
                with patch("forge.cli.shell_config.aliases_exist_in_shell_config", return_value=False):
                    with patch("forge.cli.main.cli_confirm"):
                        with patch("prompt_toolkit.print_formatted_text"):
                            should_show = not aliases_exist_in_shell_config() and (not main_alias_setup_declined())
                            assert not should_show, "Alias setup should be skipped when user previously declined"


def test_alias_setup_accepted_does_not_set_declined_flag():
    """Test that when user accepts alias setup, no declined marker is created."""
    config = ForgeConfig()
    with tempfile.TemporaryDirectory() as temp_dir:
        with patch("forge.cli.shell_config.Path.home", return_value=Path(temp_dir)):
            with patch("shellingham.detect_shell", return_value=("bash", "bash")):
                with patch("forge.cli.shell_config.aliases_exist_in_shell_config", return_value=False):
                    with patch("forge.cli.main.cli_confirm", return_value=0):
                        with patch("forge.cli.shell_config.add_aliases_to_shell_config", return_value=True):
                            with patch("prompt_toolkit.print_formatted_text"):
                                assert not alias_setup_declined()
                                run_alias_setup_flow(config)
                                assert not alias_setup_declined()
