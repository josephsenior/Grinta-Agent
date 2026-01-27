from unittest import mock
import pytest
from forge.core.config import ForgeConfig, SandboxConfig
from forge.events.action import CmdRunAction
from forge.resolver.issue_resolver import IssueResolver


def assert_sandbox_config(
    config: SandboxConfig,
    enable_auto_lint=False,
    timeout=300,
):
    """Helper function to assert the properties of the SandboxConfig object."""
    assert isinstance(config, SandboxConfig)
    assert config.enable_auto_lint is enable_auto_lint
    assert config.timeout == timeout


def test_setup_sandbox_config_default():
    """Test default configuration."""
    FORGE_config = ForgeConfig()
    IssueResolver.update_sandbox_config(
        FORGE_config=FORGE_config,
    )
    assert_sandbox_config(
        FORGE_config.sandbox,
    )


@mock.patch("forge.events.observation.CmdOutputObservation")
@mock.patch("forge.runtime.base.Runtime")
def test_initialize_runtime_runs_setup_script_and_git_hooks(
    mock_runtime, mock_cmd_output
):
    """Test that initialize_runtime calls maybe_run_setup_script and maybe_setup_git_hooks."""

    class MinimalResolver:
        def initialize_runtime(self, runtime):
            action = CmdRunAction(command='git config --global core.pager ""')
            runtime.run_action(action)
            runtime.maybe_run_setup_script()
            runtime.maybe_setup_git_hooks()

    resolver = MinimalResolver()
    mock_cmd_output.return_value.exit_code = 0
    mock_runtime.run_action.return_value = mock_cmd_output.return_value
    resolver.initialize_runtime(mock_runtime)
    mock_runtime.maybe_run_setup_script.assert_called_once()
    mock_runtime.maybe_setup_git_hooks.assert_called_once()

