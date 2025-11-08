from unittest import mock
import pytest
from forge.core.config import ForgeConfig, SandboxConfig
from forge.events.action import CmdRunAction
from forge.resolver.issue_resolver import IssueResolver


def assert_sandbox_config(
    config: SandboxConfig,
    base_container_image=SandboxConfig.model_fields["base_container_image"].default,
    runtime_container_image="ghcr.io/all-hands-ai/runtime:mock-nikolaik",
    local_runtime_url=SandboxConfig.model_fields["local_runtime_url"].default,
    enable_auto_lint=False,
):
    """Helper function to assert the properties of the SandboxConfig object."""
    assert isinstance(config, SandboxConfig)
    assert config.base_container_image == base_container_image
    assert config.runtime_container_image == runtime_container_image
    assert config.enable_auto_lint is enable_auto_lint
    assert config.use_host_network is False
    assert config.timeout == 300
    assert config.local_runtime_url == local_runtime_url


def test_setup_sandbox_config_default():
    """Test default configuration when no images provided and not experimental."""
    with mock.patch("forge.__version__", "mock"):
        FORGE_config = ForgeConfig()
        IssueResolver.update_sandbox_config(
            FORGE_config=FORGE_config,
            base_container_image=None,
            runtime_container_image=None,
            is_experimental=False,
        )
        assert_sandbox_config(
            FORGE_config.sandbox, runtime_container_image="ghcr.io/all-hands-ai/runtime:mock-nikolaik"
        )


def test_setup_sandbox_config_both_images():
    """Test that providing both container images raises ValueError."""
    with pytest.raises(ValueError, match="Cannot provide both runtime and base container images."):
        FORGE_config = ForgeConfig()
        IssueResolver.update_sandbox_config(
            FORGE_config=FORGE_config,
            base_container_image="base-image",
            runtime_container_image="runtime-image",
            is_experimental=False,
        )


def test_setup_sandbox_config_base_only():
    """Test configuration when only base_container_image is provided."""
    base_image = "custom-base-image"
    FORGE_config = ForgeConfig()
    IssueResolver.update_sandbox_config(
        FORGE_config=FORGE_config,
        base_container_image=base_image,
        runtime_container_image=None,
        is_experimental=False,
    )
    assert_sandbox_config(FORGE_config.sandbox, base_container_image=base_image, runtime_container_image=None)


def test_setup_sandbox_config_runtime_only():
    """Test configuration when only runtime_container_image is provided."""
    runtime_image = "custom-runtime-image"
    FORGE_config = ForgeConfig()
    IssueResolver.update_sandbox_config(
        FORGE_config=FORGE_config,
        base_container_image=None,
        runtime_container_image=runtime_image,
        is_experimental=False,
    )
    assert_sandbox_config(FORGE_config.sandbox, runtime_container_image=runtime_image)


def test_setup_sandbox_config_experimental():
    """Test configuration when experimental mode is enabled."""
    with mock.patch("forge.__version__", "mock"):
        FORGE_config = ForgeConfig()
        IssueResolver.update_sandbox_config(
            FORGE_config=FORGE_config,
            base_container_image=None,
            runtime_container_image=None,
            is_experimental=True,
        )
        assert_sandbox_config(FORGE_config.sandbox, runtime_container_image=None)


@mock.patch("forge.resolver.issue_resolver.os.getuid", return_value=0, create=True)
@mock.patch("forge.resolver.issue_resolver.get_unique_uid", return_value=1001)
def test_setup_sandbox_config_gitlab_ci(mock_get_unique_uid, mock_getuid):
    """Test GitLab CI specific configuration when running as root."""
    with mock.patch("forge.__version__", "mock"):
        with mock.patch.object(IssueResolver, "GITLAB_CI", True):
            FORGE_config = ForgeConfig()
            IssueResolver.update_sandbox_config(
                FORGE_config=FORGE_config,
                base_container_image=None,
                runtime_container_image=None,
                is_experimental=False,
            )
            assert_sandbox_config(FORGE_config.sandbox, local_runtime_url="http://localhost")


@mock.patch("forge.resolver.issue_resolver.os.getuid", return_value=1000, create=True)
def test_setup_sandbox_config_gitlab_ci_non_root(mock_getuid):
    """Test GitLab CI configuration when not running as root."""
    with mock.patch("forge.__version__", "mock"):
        with mock.patch.object(IssueResolver, "GITLAB_CI", True):
            FORGE_config = ForgeConfig()
            IssueResolver.update_sandbox_config(
                FORGE_config=FORGE_config,
                base_container_image=None,
                runtime_container_image=None,
                is_experimental=False,
            )
            assert_sandbox_config(FORGE_config.sandbox, local_runtime_url="http://localhost")


@mock.patch("forge.events.observation.CmdOutputObservation")
@mock.patch("forge.runtime.base.Runtime")
def test_initialize_runtime_runs_setup_script_and_git_hooks(mock_runtime, mock_cmd_output):
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
