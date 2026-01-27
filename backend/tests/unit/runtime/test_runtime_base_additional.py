from __future__ import annotations

import asyncio
import os
import sys
import types
from dataclasses import dataclass
from pathlib import Path
from typing import Any, ClassVar, Iterator, List, cast
from unittest.mock import ANY, AsyncMock, MagicMock, patch

import httpx
import pytest
from pydantic import BaseModel

if "tokenizers" not in sys.modules:
    tokenizers_stub = types.ModuleType("tokenizers")

    class Tokenizer:  # pragma: no cover - simple stub
        pass

    setattr(tokenizers_stub, "Tokenizer", Tokenizer)
    sys.modules["tokenizers"] = tokenizers_stub

from forge.core.config import ForgeConfig, SandboxConfig
from forge.core.exceptions import AgentRuntimeDisconnectedError
from forge.events.action import (
    Action,
    ActionConfirmationStatus,
    AgentThinkAction,
    BrowseInteractiveAction,
    BrowseURLAction,
    CmdRunAction,
    FileEditAction,
    FileReadAction,
    FileWriteAction,
    MCPAction,
    MessageAction,
    TaskTrackingAction,
)
from forge.events.event import EventSource
from forge.events.observation import (
    AgentThinkObservation,
    CmdOutputObservation,
    ErrorObservation,
    FileReadObservation,
    FileWriteObservation,
    NullObservation,
    TaskTrackingObservation,
    UserRejectObservation,
)
from forge.runtime.base import (
    Runtime,
    _default_env_vars,
)
from forge.integrations.service_types import AuthenticationError
from forge.runtime.runtime_status import RuntimeStatus
from forge.security.analyzer import SecurityAnalyzer


class DummyRuntime(Runtime):
    """Concrete runtime implementation for unit testing the base Runtime class."""

    def __init__(
        self,
        config: ForgeConfig,
        event_stream: Any,
        llm_registry: Any,
        *,
        run_responses: List[CmdOutputObservation] | None = None,
        **kwargs: Any,
    ) -> None:
        self._run_responses: list[CmdOutputObservation] = run_responses or []
        self.run_calls: list[str] = []
        super().__init__(config, event_stream, llm_registry, **kwargs)

    async def connect(self) -> None:  # pragma: no cover - not used in tests
        self._runtime_initialized = True

    def get_mcp_config(self, extra_stdio_servers: list[Any] | None = None) -> Any:
        return MagicMock()

    def run(self, action: CmdRunAction) -> CmdOutputObservation:
        self.run_calls.append(action.command)
        if self._run_responses:
            response = self._run_responses.pop(0)
            if isinstance(response, CmdOutputObservation):
                response.command = action.command
            return response
        return CmdOutputObservation(content="", command=action.command, exit_code=0)

    def read(self, action: FileReadAction) -> NullObservation:
        return NullObservation("")

    def write(self, action: FileWriteAction) -> NullObservation:
        return NullObservation("")

    def edit(self, action: FileEditAction) -> NullObservation:
        return NullObservation("")

    def browse(self, action: BrowseURLAction) -> NullObservation:
        return NullObservation("")

    def browse_interactive(self, action: BrowseInteractiveAction) -> NullObservation:
        return NullObservation("")

    def copy_to(
        self, host_src: str, sandbox_dest: str, recursive: bool = False
    ) -> None:
        return None

    def copy_from(self, path: str) -> Path:
        return Path(path)

    def list_files(self, path: str, recursive: bool = False) -> list[str]:
        return []

    async def call_tool_mcp(self, action: MCPAction) -> NullObservation:
        return NullObservation("")


def _cmd_output(content: str = "", exit_code: int = 0) -> CmdOutputObservation:
    """Helper to create command observations with specific exit codes."""
    return CmdOutputObservation(content=content, command="cmd", exit_code=exit_code)


def _fake_file_edit_init(self, enable_llm_editor, llm_registry, *args, **kwargs):
    """Inject minimal state for FileEditRuntimeMixin during tests."""
    self.enable_llm_editor = enable_llm_editor
    self.llm_registry = llm_registry


class RuntimeFactoryCallable:
    def __init__(
        self,
        provider_instance: MagicMock,
        provider_handler_cls: MagicMock,
        call_async_mock: MagicMock,
    ) -> None:
        self.provider_instance = provider_instance
        self.provider_handler_cls = provider_handler_cls
        self.call_async_mock = call_async_mock

    def __call__(self, **kwargs: Any) -> DummyRuntime:
        config: ForgeConfig = kwargs.pop("config", ForgeConfig())
        event_stream = kwargs.pop("event_stream", MagicMock())
        llm_registry = kwargs.pop("llm_registry", MagicMock())
        return DummyRuntime(config, event_stream, llm_registry, **kwargs)


@pytest.fixture
def runtime_factory() -> Iterator[RuntimeFactoryCallable]:
    provider_instance = MagicMock()
    provider_env = {"PROVIDER_TOKEN": "abc"}
    call_async_mock = MagicMock(return_value=provider_env)

    with (
        patch("forge.runtime.base.ProviderHandler") as provider_handler_cls,
        patch("forge.runtime.base.call_async_from_sync", call_async_mock),
        patch("forge.runtime.base.GitHandler"),
        patch("forge.runtime.utils.process_manager.ProcessManager"),
        patch(
            "forge.runtime.base.FileEditRuntimeMixin.__init__",
            side_effect=_fake_file_edit_init,
        ),
        patch("forge.runtime.base.atexit.register"),
    ):
        provider_handler_cls.return_value = provider_instance
        factory = RuntimeFactoryCallable(
            provider_instance, provider_handler_cls, call_async_mock
        )
        yield factory


@dataclass
class UnknownAction(Action):
    """Custom action type not registered in runtime mapping for validation testing."""

    action: ClassVar[str] = "unknown_action"


def test_default_env_vars_includes_prefixed_env_and_auto_lint():
    sandbox_config = SandboxConfig(enable_auto_lint=True)
    with patch.dict(os.environ, {"SANDBOX_ENV_FOO": "bar"}, clear=True):
        env_vars = _default_env_vars(sandbox_config)
    assert env_vars == {"FOO": "bar", "ENABLE_AUTO_LINT": "true"}


def test_runtime_initializes_env_and_plugins(runtime_factory):
    config = ForgeConfig()
    config.sandbox.enable_auto_lint = True
    event_stream = MagicMock()
    with patch.dict(os.environ, {"SANDBOX_ENV_ALPHA": "beta"}, clear=True):
        runtime = runtime_factory(
            config=config, env_vars={"extra": "1"}, event_stream=event_stream
        )
    assert any(isinstance(plugin, VSCodeRequirement) for plugin in runtime.plugins)
    assert runtime.initial_env_vars["ALPHA"] == "beta"
    assert runtime.initial_env_vars["PROVIDER_TOKEN"] == "abc"
    assert runtime.initial_env_vars["extra"] == "1"
    assert runtime.initial_env_vars["ENABLE_AUTO_LINT"] == "true"
    assert event_stream.subscribe.called


def test_runtime_setup_initial_env_applies_startup_vars(runtime_factory):
    config = ForgeConfig()
    config.sandbox.runtime_startup_env_vars = {"BOOT": "1"}
    runtime = runtime_factory(config=config)
    with (
        patch.object(runtime, "add_env_vars") as add_env_vars,
        patch.object(runtime, "_setup_git_config") as setup_git_config,
    ):
        runtime.setup_initial_env()
    assert add_env_vars.call_args_list[0].args[0] == runtime.initial_env_vars
    assert (
        add_env_vars.call_args_list[1].args[0]
        == config.sandbox.runtime_startup_env_vars
    )
    setup_git_config.assert_called_once()


def test_runtime_setup_initial_env_skips_when_attached(runtime_factory):
    config = ForgeConfig()
    config.sandbox.runtime_startup_env_vars = {"BOOT": "1"}
    runtime = runtime_factory(config=config, attach_to_existing=True)
    with (
        patch.object(runtime, "add_env_vars") as add_env_vars,
        patch.object(runtime, "_setup_git_config") as setup_git_config,
    ):
        runtime.setup_initial_env()
    add_env_vars.assert_not_called()
    setup_git_config.assert_not_called()


def test_set_runtime_status_invokes_callback(runtime_factory):
    status_callback = MagicMock()
    runtime = runtime_factory(status_callback=status_callback)
    runtime.set_runtime_status(RuntimeStatus.READY, "all good", level="warning")
    assert runtime.runtime_status == RuntimeStatus.READY
    status_callback.assert_called_once_with("warning", RuntimeStatus.READY, "all good")


def test_build_powershell_env_cmd(runtime_factory):
    runtime = runtime_factory()
    cmd = runtime._build_powershell_env_cmd({"FOO": "bar", "BAZ": "qux"})
    assert '$env:FOO = "bar";' in cmd
    assert '$env:BAZ = "qux";' in cmd


def test_add_env_vars_to_powershell_success(runtime_factory):
    success = CmdOutputObservation(content="", command="", exit_code=0)
    runtime = runtime_factory(run_responses=[success])
    runtime._add_env_vars_to_powershell({"FOO": "bar"})
    assert runtime.run_calls == ['$env:FOO = "bar";']


def test_add_env_vars_to_powershell_failure(runtime_factory):
    failure = CmdOutputObservation(content="error", command="", exit_code=1)
    runtime = runtime_factory(run_responses=[failure])
    with pytest.raises(RuntimeError):
        runtime._add_env_vars_to_powershell({"FOO": "bar"})


def test_add_env_vars_skips_powershell_when_empty(runtime_factory):
    runtime = runtime_factory()
    with patch.object(runtime, "run") as run_mock:
        runtime._add_env_vars_to_powershell({})
    run_mock.assert_not_called()


def test_build_bash_env_commands(runtime_factory):
    runtime = runtime_factory()
    cmd, bashrc_cmd = runtime._build_bash_env_commands({"FOO": "bar"})
    assert cmd == 'export FOO="bar";'
    assert 'echo "export FOO="bar"" >> ~/.bashrc;' in bashrc_cmd


def test_add_env_vars_to_bash_success(runtime_factory):
    responses = [
        CmdOutputObservation(content="", command="", exit_code=0),
        CmdOutputObservation(content="", command="", exit_code=0),
    ]
    runtime = runtime_factory(run_responses=responses)
    runtime._add_env_vars_to_bash({"FOO": "bar"})
    assert runtime.run_calls[0].startswith('export FOO="bar";')
    assert runtime.run_calls[1].startswith("touch ~/.bashrc;")


def test_add_env_vars_to_bash_failure(runtime_factory):
    failure = CmdOutputObservation(content="error", command="", exit_code=1)
    runtime = runtime_factory(run_responses=[failure])
    with pytest.raises(RuntimeError):
        runtime._add_env_vars_to_bash({"FOO": "bar"})
    assert len(runtime.run_calls) == 1


def test_add_env_vars_routes_to_powershell_on_windows(runtime_factory):
    runtime = runtime_factory()
    with (
        patch.object(runtime, "_add_env_vars_to_powershell") as mock_power,
        patch.object(runtime, "_add_env_vars_to_bash") as mock_bash,
        patch("os.name", "nt"),
        patch("sys.platform", "win32"),
    ):
        runtime.add_env_vars({"foo": "bar"})
    mock_power.assert_called_once()
    mock_bash.assert_not_called()
    power_call = mock_power.call_args
    assert power_call is not None
    assert power_call.args[0] == {"FOO": "bar"}


def test_add_env_vars_routes_to_bash_on_posix(runtime_factory):
    runtime = runtime_factory()
    with (
        patch.object(runtime, "_add_env_vars_to_powershell") as mock_power,
        patch.object(runtime, "_add_env_vars_to_bash") as mock_bash,
        patch("os.name", "posix"),
        patch("sys.platform", "linux"),
    ):
        runtime.add_env_vars({"foo": "bar"})
    mock_power.assert_not_called()
    mock_bash.assert_called_once()


def test_setup_git_hooks_directory_success(runtime_factory):
    runtime = runtime_factory()
    with patch.object(runtime, "run_action", return_value=_cmd_output("", exit_code=0)):
        assert runtime._setup_git_hooks_directory()


def test_setup_git_hooks_directory_failure_logs(runtime_factory):
    runtime = runtime_factory()
    with (
        patch.object(
            runtime,
            "run_action",
            return_value=_cmd_output("permission denied", exit_code=1),
        ),
        patch.object(runtime, "log") as mock_log,
    ):
        assert not runtime._setup_git_hooks_directory()
        mock_log.assert_called_once_with(
            "error", "Failed to create git hooks directory: permission denied"
        )


def test_setup_git_hooks_directory_non_command_observation(runtime_factory):
    runtime = runtime_factory()
    with patch.object(runtime, "run_action", return_value=NullObservation("")):
        assert not runtime._setup_git_hooks_directory()


def test_make_script_executable_success(runtime_factory):
    runtime = runtime_factory()
    with patch.object(runtime, "run_action", return_value=_cmd_output(exit_code=0)):
        assert runtime._make_script_executable("script.sh")


def test_make_script_executable_failure_logs(runtime_factory):
    runtime = runtime_factory()
    with (
        patch.object(
            runtime, "run_action", return_value=_cmd_output("bad", exit_code=3)
        ),
        patch.object(runtime, "log") as mock_log,
    ):
        assert not runtime._make_script_executable("script.sh")
        mock_log.assert_called_once_with(
            "error", "Failed to make script.sh executable: bad"
        )


def test_preserve_existing_hook_via_command(runtime_factory):
    runtime = runtime_factory()
    with (
        patch.object(
            runtime, "run_action", return_value=_cmd_output(exit_code=0)
        ) as mock_run,
        patch.object(
            Runtime, "_make_script_executable", return_value=True
        ) as mock_exec,
    ):
        assert runtime._preserve_existing_hook(".git/hooks/pre-commit")
        mock_run.assert_called_once()
        mock_exec.assert_called_once_with(runtime, ".git/hooks/pre-commit.local")


def test_preserve_existing_hook_logs_on_failure(runtime_factory):
    runtime = runtime_factory()
    with (
        patch.object(
            runtime, "run_action", return_value=_cmd_output("oops", exit_code=2)
        ),
        patch.object(runtime, "log") as mock_log,
    ):
        assert not runtime._preserve_existing_hook(".git/hooks/pre-commit")
        mock_log.assert_called_once_with(
            "error", "Failed to preserve existing pre-commit hook: oops"
        )


def test_preserve_existing_hook_falls_back_to_shutil(runtime_factory, monkeypatch):
    runtime = runtime_factory()
    monkeypatch.setattr(
        runtime, "run_action", MagicMock(return_value=NullObservation(""))
    )
    move_mock = MagicMock()
    monkeypatch.setattr("forge.runtime.base.shutil.move", move_mock)
    with patch.object(
        Runtime, "_make_script_executable", return_value=True
    ) as mock_exec:
        assert runtime._preserve_existing_hook("pre-commit")
        move_mock.assert_called_once_with("pre-commit", ".git/hooks/pre-commit.local")
        mock_exec.assert_called_once_with(runtime, ".git/hooks/pre-commit.local")


def test_preserve_existing_hook_handles_shutil_error(runtime_factory, monkeypatch):
    runtime = runtime_factory()
    monkeypatch.setattr(
        runtime, "run_action", MagicMock(return_value=NullObservation(""))
    )
    monkeypatch.setattr(
        "forge.runtime.base.shutil.move", MagicMock(side_effect=OSError("boom"))
    )
    with (
        patch.object(Runtime, "_make_script_executable", return_value=True),
        patch.object(runtime, "log") as mock_log,
    ):
        assert not runtime._preserve_existing_hook("pre-commit")
        mock_log.assert_called_once_with(
            "error", "Failed to preserve existing pre-commit hook: boom"
        )


def test_install_pre_commit_hook_success(runtime_factory):
    runtime = runtime_factory()
    with (
        patch.object(runtime, "write", return_value=NullObservation("")),
        patch.object(
            Runtime, "_make_script_executable", return_value=True
        ) as mock_exec,
    ):
        assert runtime._install_pre_commit_hook("script.sh", "hook")
        mock_exec.assert_called_once_with(runtime, "hook")


def test_install_pre_commit_hook_logs_on_write_error(runtime_factory):
    runtime = runtime_factory()
    with (
        patch.object(runtime, "write", return_value=ErrorObservation("cannot write")),
        patch.object(runtime, "log") as mock_log,
    ):
        assert not runtime._install_pre_commit_hook("script.sh", "hook")
        mock_log.assert_called_once_with(
            "error", "Failed to write pre-commit hook: cannot write"
        )

def test_setup_git_config_warns_on_nonzero(runtime_factory):
    runtime = runtime_factory()
    with patch.object(runtime, "run", return_value=_cmd_output("bad", exit_code=5)):
        with patch("forge.runtime.base.logger") as mock_logger:
            runtime._setup_git_config()
    mock_logger.warning.assert_called_once_with(
        "Git config command failed: %s, error: %s",
        ANY,
        "bad",
    )


def test_setup_git_config_handles_exception(runtime_factory):
    runtime = runtime_factory()
    with patch.object(runtime, "run", side_effect=RuntimeError("boom")):
        with patch("forge.runtime.base.logger") as mock_logger:
            runtime._setup_git_config()
    mock_logger.warning.assert_called_once_with(
        "Failed to execute git config command: %s, error: %s",
        ANY,
        ANY,
    )


def test_maybe_run_setup_script_no_script(runtime_factory):
    runtime = runtime_factory()
    runtime.event_stream = MagicMock()
    with patch.object(
        runtime, "read", return_value=ErrorObservation("missing")
    ) as mock_read:
        runtime.maybe_run_setup_script()
        mock_read.assert_called_once()
        runtime.event_stream.add_event.assert_not_called()


def test_maybe_run_setup_script_executes(runtime_factory):
    runtime = runtime_factory()
    runtime.event_stream = MagicMock()
    runtime.status_callback = MagicMock()
    runtime.log = MagicMock()
    with (
        patch.object(
            runtime,
            "read",
            return_value=FileReadObservation(
                content="#!/bin/bash", path=".Forge/setup.sh"
            ),
        ),
        patch.object(runtime, "run_action") as mock_run,
    ):
        runtime.maybe_run_setup_script()
        runtime.event_stream.add_event.assert_called_once()
        event_call = runtime.event_stream.add_event.call_args
        assert event_call is not None
        action = event_call.args[0]
        assert isinstance(action, CmdRunAction)
        assert action.command == "chmod +x .Forge/setup.sh && source .Forge/setup.sh"
        mock_run.assert_called_once()
        runtime.status_callback.assert_called_once_with(
            "info", RuntimeStatus.SETTING_UP_WORKSPACE, "Setting up workspace..."
        )


def test_build_powershell_env_cmd_empty(runtime_factory):
    runtime = runtime_factory()
    assert runtime._build_powershell_env_cmd({}) == ""


def test_build_bash_env_commands_empty(runtime_factory):
    runtime = runtime_factory()
    cmd, bashrc_cmd = runtime._build_bash_env_commands({})
    assert cmd == ""
    assert bashrc_cmd == ""


def test_maybe_setup_git_hooks_returns_when_script_missing(runtime_factory):
    runtime = runtime_factory()
    with patch.object(
        runtime, "read", return_value=ErrorObservation("missing")
    ) as mock_read:
        runtime.maybe_setup_git_hooks()
        mock_read.assert_called_once()


def test_maybe_setup_git_hooks_installs_new_hook(runtime_factory):
    runtime = runtime_factory()
    runtime.status_callback = MagicMock()
    runtime.log = MagicMock()
    read_sequence = [
        FileReadObservation(content="echo hook", path=".Forge/pre-commit.sh"),
        ErrorObservation("no existing hook"),
    ]
    with (
        patch.object(runtime, "read", side_effect=read_sequence) as mock_read,
        patch.object(Runtime, "_setup_git_hooks_directory", return_value=True),
        patch.object(Runtime, "_make_script_executable", return_value=True),
        patch.object(
            Runtime, "_preserve_existing_hook", return_value=True
        ) as mock_preserve,
        patch.object(
            Runtime, "_install_pre_commit_hook", return_value=True
        ) as mock_install,
    ):
        runtime.maybe_setup_git_hooks()
        assert mock_read.call_count == 2
        mock_preserve.assert_not_called()
        mock_install.assert_called_once_with(
            runtime, ".Forge/pre-commit.sh", ".git/hooks/pre-commit"
        )
        runtime.log.assert_called_with(
            "info", "Git pre-commit hook installed successfully"
        )


def test_maybe_setup_git_hooks_preserves_existing_hook(runtime_factory):
    runtime = runtime_factory()
    runtime.log = MagicMock()
    with (
        patch.object(
            runtime,
            "read",
            side_effect=[
                FileReadObservation(content="echo hook", path=".Forge/pre-commit.sh"),
                FileReadObservation(
                    content="existing custom hook", path=".git/hooks/pre-commit"
                ),
            ],
        ),
        patch.object(Runtime, "_setup_git_hooks_directory", return_value=True),
        patch.object(Runtime, "_make_script_executable", return_value=True),
        patch.object(
            Runtime, "_preserve_existing_hook", return_value=True
        ) as mock_preserve,
        patch.object(Runtime, "_install_pre_commit_hook", return_value=False),
    ):
        runtime.maybe_setup_git_hooks()
        mock_preserve.assert_called_once_with(runtime, ".git/hooks/pre-commit")
        runtime.log.assert_any_call("info", "Preserving existing pre-commit hook")


def test_maybe_setup_git_hooks_aborts_on_setup_failure(runtime_factory):
    runtime = runtime_factory()
    with (
        patch.object(
            runtime,
            "read",
            return_value=FileReadObservation(
                content="echo hook", path=".Forge/pre-commit.sh"
            ),
        ),
        patch.object(Runtime, "_setup_git_hooks_directory", return_value=False),
        patch.object(Runtime, "_make_script_executable") as mock_exec,
    ):
        runtime.maybe_setup_git_hooks()
        mock_exec.assert_not_called()


def test_maybe_setup_git_hooks_aborts_when_make_executable_fails(runtime_factory):
    runtime = runtime_factory()
    with (
        patch.object(
            runtime,
            "read",
            side_effect=[
                FileReadObservation(content="echo hook", path=".Forge/pre-commit.sh"),
                ErrorObservation("missing"),
            ],
        ),
        patch.object(Runtime, "_setup_git_hooks_directory", return_value=True),
        patch.object(
            Runtime, "_make_script_executable", return_value=False
        ) as mock_exec,
        patch.object(Runtime, "_install_pre_commit_hook") as mock_install,
    ):
        runtime.maybe_setup_git_hooks()
        mock_exec.assert_called_once_with(runtime, ".Forge/pre-commit.sh")
        mock_install.assert_not_called()


def test_set_action_timeout_for_long_running_command(runtime_factory):
    runtime = runtime_factory()
    action = CmdRunAction("npm run dev")
    runtime._set_action_timeout(action)
    assert action.timeout is None
    assert action.blocking is False


def test_set_action_timeout_for_regular_command(runtime_factory):
    runtime = runtime_factory()
    action = CmdRunAction("echo hello")
    runtime._set_action_timeout(action)
    assert action.timeout == runtime.config.sandbox.timeout
    assert action.blocking is False


def test_handle_runtime_error_network(runtime_factory):
    runtime = runtime_factory()
    runtime.log = MagicMock()
    runtime.set_runtime_status = MagicMock()
    event = CmdRunAction("echo hi")
    runtime._handle_runtime_error(event, RuntimeError("boom"), is_network_error=True)
    runtime.log.assert_any_call("error", ANY)
    runtime.set_runtime_status.assert_called_once_with(
        RuntimeStatus.ERROR_RUNTIME_DISCONNECTED, "RuntimeError: boom", level="error"
    )


def test_handle_runtime_error_generic(runtime_factory):
    runtime = runtime_factory()
    runtime.log = MagicMock()
    runtime.set_runtime_status = MagicMock()
    event = CmdRunAction("echo hi")
    runtime._handle_runtime_error(event, ValueError("nope"))
    runtime.set_runtime_status.assert_called_once_with(
        RuntimeStatus.ERROR, "ValueError: nope", level="error"
    )


def test_process_observation_sets_metadata_dict(runtime_factory):
    runtime = runtime_factory()
    event = CmdRunAction("echo hi")
    event.id = 42
    event.tool_call_metadata = cast(Any, {"foo": "bar"})
    observation = _cmd_output("out", exit_code=0)
    assert runtime._process_observation(observation, event) is True
    assert observation.cause == 42
    assert observation.tool_call_metadata == {"foo": "bar"}


def test_process_observation_null(runtime_factory):
    runtime = runtime_factory()
    event = CmdRunAction("echo hi")
    assert runtime._process_observation(NullObservation(""), event) is False


@pytest.mark.asyncio
async def test_handle_action_skips_null_observation(runtime_factory):
    runtime = runtime_factory()
    runtime.event_stream = MagicMock()
    action = CmdRunAction("echo hi")
    action.id = 1
    with (
        patch.object(
            runtime, "_execute_action", AsyncMock(return_value=NullObservation(""))
        ),
        patch.object(
            runtime, "_process_observation", wraps=runtime._process_observation
        ) as mock_process,
    ):
        await runtime._handle_action(action)
    mock_process.assert_called_once()
    runtime.event_stream.add_event.assert_not_called()


@pytest.mark.asyncio
async def test_handle_action_handles_permission_error(runtime_factory):
    runtime = runtime_factory()
    runtime.event_stream = MagicMock()
    action = CmdRunAction("cat secret")
    action.id = 2
    with patch.object(
        runtime, "_execute_action", AsyncMock(side_effect=PermissionError("denied"))
    ):
        await runtime._handle_action(action)
    runtime.event_stream.add_event.assert_called_once()
    perm_call = runtime.event_stream.add_event.call_args
    assert perm_call is not None
    obs = perm_call.args[0]
    assert isinstance(obs, ErrorObservation)
    assert obs.content == "denied"


@pytest.mark.asyncio
async def test_handle_action_handles_network_error(runtime_factory):
    runtime = runtime_factory()
    runtime.event_stream = MagicMock()
    runtime._handle_runtime_error = MagicMock()
    action = CmdRunAction("run")
    with patch.object(
        runtime,
        "_execute_action",
        AsyncMock(side_effect=AgentRuntimeDisconnectedError("lost")),
    ):
        await runtime._handle_action(action)
    runtime._handle_runtime_error.assert_called_once()
    runtime.event_stream.add_event.assert_not_called()


@pytest.mark.asyncio
async def test_clone_or_init_repo_initializes_workspace(runtime_factory):
    runtime = runtime_factory()
    runtime.config.init_git_in_empty_workspace = True
    runtime.config.workspace_mount_path_in_sandbox = "/workspace"
    with patch("forge.runtime.base.call_sync_from_async", AsyncMock()) as call_sync:
        result = await runtime.clone_or_init_repo(None, None, None)
    assert result == ""
    call_sync.assert_called_once()
    await_call = call_sync.await_args
    assert await_call is not None
    action = await_call.args[1]
    assert isinstance(action, CmdRunAction)
    assert "git init" in action.command


@pytest.mark.asyncio
async def test_clone_or_init_repo_requires_authenticated_url(runtime_factory):
    runtime = runtime_factory()
    runtime.provider_handler = MagicMock()
    runtime.provider_handler.get_authenticated_git_url = AsyncMock(return_value=None)
    with pytest.raises(ValueError):
        await runtime.clone_or_init_repo(None, "github.com/foo/bar", None)


@pytest.mark.asyncio
async def test_clone_or_init_repo_clones_repository(runtime_factory):
    runtime = runtime_factory()
    runtime.provider_handler = MagicMock()
    runtime.provider_handler.get_authenticated_git_url = AsyncMock(
        return_value="https://example.git"
    )
    runtime.log = MagicMock()
    runtime.status_callback = MagicMock()
    with patch("forge.runtime.base.call_sync_from_async", AsyncMock()) as call_sync:
        repo_dir = await runtime.clone_or_init_repo(None, "github.com/foo/repo", "main")
    assert repo_dir == "repo"
    assert call_sync.await_count == 2
    clone_action = call_sync.await_args_list[0].args[1]
    checkout_action = call_sync.await_args_list[1].args[1]
    assert clone_action.command.startswith("git clone https://example.git repo")
    assert "git checkout main" in checkout_action.command
    runtime.status_callback.assert_called_with(
        "info", RuntimeStatus.SETTING_UP_WORKSPACE, "Setting up workspace..."
    )


def test_verify_action_returns_none_for_non_file_edit(runtime_factory):
    runtime = runtime_factory()
    observation = _cmd_output("done")
    assert (
        runtime._verify_action_if_needed(CmdRunAction("echo hi"), observation) is None
    )


def test_verify_action_skips_on_error_observation(runtime_factory):
    runtime = runtime_factory()
    action = FileEditAction(path="foo.txt")
    observation = ErrorObservation("failed")
    with patch.object(runtime, "_execute_action") as mock_exec:
        assert runtime._verify_action_if_needed(action, observation) is None
    mock_exec.assert_not_called()


def test_verify_action_detects_missing_file(runtime_factory):
    runtime = runtime_factory()
    action = FileEditAction(path="/tmp/foo.txt")
    observation = _cmd_output("edit ok")
    with (
        patch.object(
            runtime, "_execute_action", side_effect=[_cmd_output("ERROR:MISSING")]
        ),
        patch("forge.runtime.base.logger") as mock_logger,
    ):
        result = runtime._verify_action_if_needed(action, observation)
    assert isinstance(result, ErrorObservation)
    assert "/tmp/foo.txt" in result.content
    mock_logger.error.assert_called_once()


def test_verify_action_confirms_existing_file(runtime_factory):
    runtime = runtime_factory()
    action = FileEditAction(path="/tmp/bar.txt")
    observation = _cmd_output("write ok")
    with patch.object(
        runtime,
        "_execute_action",
        side_effect=[_cmd_output("VERIFIED:EXISTS"), _cmd_output("7\n")],
    ):
        result = runtime._verify_action_if_needed(action, observation)
    assert isinstance(result, FileWriteObservation)
    assert "VERIFICATION" in result.content
    assert result.path == "/tmp/bar.txt"


def test_verify_action_returns_none_on_invalid_line_count(runtime_factory):
    runtime = runtime_factory()
    action = FileEditAction(path="/tmp/baz.txt")
    observation = _cmd_output("done")
    with patch.object(
        runtime,
        "_execute_action",
        side_effect=[_cmd_output("VERIFIED:EXISTS"), _cmd_output("not-a-number")],
    ):
        result = runtime._verify_action_if_needed(action, observation)
    assert result is None


def test_verify_action_returns_none_when_size_not_cmd_output(runtime_factory):
    runtime = runtime_factory()
    action = FileEditAction(path="foo.txt")
    observation = _cmd_output("done")
    with patch.object(
        runtime,
        "_execute_action",
        side_effect=[_cmd_output("VERIFIED:EXISTS"), NullObservation("")],
    ):
        result = runtime._verify_action_if_needed(action, observation)
    assert result is None


def test_verify_action_returns_none_when_verification_non_cmd_output(runtime_factory):
    runtime = runtime_factory()
    action = FileEditAction(path="foo.txt")
    observation = _cmd_output("done")
    with patch.object(runtime, "_execute_action", return_value=NullObservation("")):
        result = runtime._verify_action_if_needed(action, observation)
    assert result is None


def test_verify_action_handles_exception(runtime_factory):
    runtime = runtime_factory()
    action = FileEditAction(path="foo.txt")
    observation = _cmd_output("done")
    with (
        patch.object(runtime, "_execute_action", side_effect=RuntimeError("boom")),
        patch("forge.runtime.base.logger") as mock_logger,
    ):
        result = runtime._verify_action_if_needed(action, observation)
    assert result is None
    mock_logger.warning.assert_called_once()


def test_load_microagents_directory_no_files(runtime_factory):
    runtime = runtime_factory()
    runtime.log = MagicMock()
    runtime.list_files = MagicMock(return_value=[])
    result = runtime._load_microagents_from_directory(Path("/tmp/micro"), "repository")
    assert result == []
    runtime.list_files.assert_called_once_with(str(Path("/tmp/micro")))
    assert any(
        call_args[0][0] == "debug"
        and "No files found in repository microagents directory" in call_args[0][1]
        for call_args in runtime.log.call_args_list
    )


def test_load_microagents_directory_success(runtime_factory):
    runtime = runtime_factory()
    runtime.log = MagicMock()
    runtime.list_files = MagicMock(return_value=["bundle.zip"])
    fake_zip = MagicMock()
    fake_zip.unlink = MagicMock()
    runtime.copy_from = MagicMock(return_value=fake_zip)

    with (
        patch("forge.runtime.base.tempfile.mkdtemp", return_value="/tmp/microagents"),
        patch("forge.runtime.base.ZipFile") as zip_cls,
        patch(
            "forge.runtime.base.load_microagents_from_dir",
            return_value=({"repo": "r_agent"}, {"knowledge": "k_agent"}),
        ) as load_mock,
        patch("forge.runtime.base.shutil.rmtree") as rm_mock,
    ):
        zip_instance = MagicMock()
        zip_cls.return_value.__enter__.return_value = zip_instance
        result = runtime._load_microagents_from_directory(
            Path("/data/micro"), "repository"
        )

    assert result == ["r_agent", "k_agent"]
    zip_instance.extractall.assert_called_once_with("/tmp/microagents")
    fake_zip.unlink.assert_called_once()
    load_mock.assert_called_once_with("/tmp/microagents")
    rm_mock.assert_called_once_with("/tmp/microagents")


def test_load_microagents_directory_handles_exception(runtime_factory):
    runtime = runtime_factory()
    runtime.log = MagicMock()
    runtime.list_files = MagicMock(return_value=["bundle.zip"])
    fake_zip = MagicMock()
    fake_zip.unlink = MagicMock()
    runtime.copy_from = MagicMock(return_value=fake_zip)

    with (
        patch("forge.runtime.base.tempfile.mkdtemp", return_value="/tmp/microagents"),
        patch("forge.runtime.base.ZipFile") as zip_cls,
        patch(
            "forge.runtime.base.load_microagents_from_dir",
            side_effect=RuntimeError("boom"),
        ),
        patch("forge.runtime.base.shutil.rmtree") as rm_mock,
    ):
        zip_instance = MagicMock()
        zip_cls.return_value.__enter__.return_value = zip_instance
        result = runtime._load_microagents_from_directory(
            Path("/data/micro"), "repository"
        )

    assert result == []
    runtime.log.assert_any_call("error", "Failed to load agents from repository: boom")
    rm_mock.assert_called_once_with("/tmp/microagents")


def test_clone_and_load_org_microagents_success(runtime_factory):
    runtime = runtime_factory()
    runtime.log = MagicMock()
    runtime.provider_handler = MagicMock()
    runtime.config.workspace_mount_path_in_sandbox = "/workspace"
    with (
        patch(
            "forge.runtime.base.call_async_from_sync",
            return_value="https://example.com/org.git",
        ) as call_async,
        patch.object(
            runtime, "_execute_clone_and_load", return_value=["agent"]
        ) as exec_mock,
    ):
        result = runtime._clone_and_load_org_microagents("org", "org/.Forge")

    assert result == ["agent"]
    call_async.assert_called_once_with(
        runtime.provider_handler.get_authenticated_git_url, ANY, "org/.Forge"
    )
    expected_dir = runtime.workspace_root / "org_FORGE_org"
    exec_mock.assert_called_once_with(
        expected_dir, "https://example.com/org.git", "org/.Forge"
    )


def test_clone_and_load_org_microagents_auth_error(runtime_factory):
    runtime = runtime_factory()
    runtime.log = MagicMock()
    runtime.provider_handler = MagicMock()
    runtime.config.workspace_mount_path_in_sandbox = "/workspace"
    with patch(
        "forge.runtime.base.call_async_from_sync",
        side_effect=AuthenticationError("unauthorized"),
    ):
        result = runtime._clone_and_load_org_microagents("org", "org/.Forge")
    assert result == []


def test_clone_and_load_org_microagents_generic_error(runtime_factory):
    runtime = runtime_factory()
    runtime.log = MagicMock()
    runtime.provider_handler = MagicMock()
    runtime.config.workspace_mount_path_in_sandbox = "/workspace"
    with patch(
        "forge.runtime.base.call_async_from_sync",
        side_effect=RuntimeError("network"),
    ):
        result = runtime._clone_and_load_org_microagents("org", "org/.Forge")
    assert result == []


def test_execute_clone_and_load_success(runtime_factory):
    runtime = runtime_factory()
    runtime.log = MagicMock()
    runtime.run_action = MagicMock(return_value=_cmd_output(exit_code=0))
    with patch.object(
        runtime, "_load_and_cleanup_org_microagents", return_value=["agent"]
    ) as load_mock:
        result = runtime._execute_clone_and_load(
            Path("/tmp/org"), "https://git", "org/.Forge"
        )
    assert result == ["agent"]
    load_mock.assert_called_once_with(Path("/tmp/org"), "org/.Forge")


def test_execute_clone_and_load_failure(runtime_factory):
    runtime = runtime_factory()
    runtime.log = MagicMock()
    failure_obs = _cmd_output("failed", exit_code=1)
    runtime.run_action = MagicMock(return_value=failure_obs)
    with (
        patch.object(runtime, "_load_and_cleanup_org_microagents") as load_mock,
        patch.object(runtime, "_log_clone_failure") as log_fail,
    ):
        result = runtime._execute_clone_and_load(
            Path("/tmp/org"), "https://git", "org/.Forge"
        )
    assert result == []
    load_mock.assert_not_called()
    log_fail.assert_called_once_with(failure_obs, "org/.Forge")


def test_load_and_cleanup_org_microagents(runtime_factory):
    runtime = runtime_factory()
    runtime.log = MagicMock()
    runtime.run_action = MagicMock(return_value=_cmd_output(exit_code=0))
    with patch.object(
        runtime,
        "_load_microagents_from_directory",
        return_value=["agent"],
    ) as load_mock:
        result = runtime._load_and_cleanup_org_microagents(
            Path("/tmp/org"), "org/.Forge"
        )
    assert result == ["agent"]
    load_mock.assert_called_once_with(Path("/tmp/org") / "microagents", "org-level")
    run_call = runtime.run_action.call_args
    assert run_call is not None
    cleanup_action = run_call.args[0]
    assert isinstance(cleanup_action, CmdRunAction)
    assert cleanup_action.command == f"rm -rf {Path('/tmp/org')}"


def test_get_microagents_from_selected_repo_workspace(runtime_factory):
    runtime = runtime_factory()
    runtime.config.workspace_mount_path_in_sandbox = "/workspace"
    runtime.get_microagents_from_org_or_user = MagicMock(return_value=[])
    runtime._load_microagents_from_directory = MagicMock(return_value=["repo_agent"])
    runtime.read = MagicMock(
        return_value=FileReadObservation(
            content="instruction data", path=".FORGE_instructions"
        )
    )

    with patch(
        "forge.runtime.base.BaseMicroagent.load", return_value="instr_agent"
    ) as load_mock:
        result = runtime.get_microagents_from_selected_repo(None)

    load_mock.assert_called_once_with(
        path=".FORGE_instructions", microagent_dir=None, file_content="instruction data"
    )
    runtime._load_microagents_from_directory.assert_called_once_with(
        Path("/workspace/.Forge/microagents"), "repository"
    )
    assert result == ["instr_agent", "repo_agent"]


def test_get_microagents_from_selected_repo_fallback_instructions(runtime_factory):
    runtime = runtime_factory()
    runtime.config.workspace_mount_path_in_sandbox = "/workspace"
    runtime.get_microagents_from_org_or_user = MagicMock(return_value=[])
    runtime._load_microagents_from_directory = MagicMock(return_value=["repo_agent"])
    repo_path = Path("/workspace/repo")
    runtime.read = MagicMock(
        side_effect=[
            ErrorObservation("missing workspace instructions"),
            FileReadObservation(
                content="repo instructions", path=str(repo_path / ".FORGE_instructions")
            ),
        ]
    )

    with patch("forge.runtime.base.BaseMicroagent.load", return_value="repo_instr"):
        result = runtime.get_microagents_from_selected_repo("github.com/owner/repo")

    runtime._load_microagents_from_directory.assert_called_once_with(
        repo_path / ".Forge" / "microagents", "repository"
    )
    assert result == ["repo_instr", "repo_agent"]


def test_get_microagents_from_selected_repo_includes_org(runtime_factory):
    runtime = runtime_factory()
    runtime.config.workspace_mount_path_in_sandbox = "/workspace"
    runtime.get_microagents_from_org_or_user = MagicMock(return_value=["org_agent"])
    runtime._load_microagents_from_directory = MagicMock(return_value=[])
    runtime.read = MagicMock(return_value=ErrorObservation("missing"))

    result = runtime.get_microagents_from_selected_repo("github.com/owner/repo")

    runtime.get_microagents_from_org_or_user.assert_called_once_with(
        "github.com/owner/repo"
    )
    assert result == ["org_agent"]


def test_get_microagents_from_selected_repo_no_instructions(runtime_factory):
    runtime = runtime_factory()
    runtime.config.workspace_mount_path_in_sandbox = "/workspace"
    runtime.get_microagents_from_org_or_user = MagicMock(return_value=[])
    runtime._load_microagents_from_directory = MagicMock(return_value=["repo_agent"])
    runtime.read = MagicMock(return_value=ErrorObservation("missing"))

    result = runtime.get_microagents_from_selected_repo("github.com/owner/repo")

    runtime._load_microagents_from_directory.assert_called_once()
    assert result == ["repo_agent"]


def test_setup_git_config_success(runtime_factory):
    runtime = runtime_factory()
    runtime.config.git_user_name = "Alice"
    runtime.config.git_user_email = "alice@example.com"
    obs = CmdOutputObservation(content="", command="", exit_code=0)
    with (
        patch.object(runtime, "run", return_value=obs) as run_mock,
        patch("forge.runtime.base.logger") as logger_mock,
    ):
        runtime._setup_git_config()
    run_mock.assert_called_once()
    logger_mock.info.assert_called()

def test_setup_git_config_warns_on_failure(runtime_factory):
    runtime = runtime_factory()
    failure_obs = CmdOutputObservation(content="err", command="", exit_code=1)
    with (
        patch.object(runtime, "run", return_value=failure_obs),
        patch("forge.runtime.base.logger") as logger_mock,
    ):
        runtime._setup_git_config()
    logger_mock.warning.assert_called()


def test_on_event_runs_actions(runtime_factory):
    runtime = runtime_factory()
    action = CmdRunAction(command="echo hello")
    loop = MagicMock()
    with (
        patch("asyncio.get_event_loop", return_value=loop),
        patch.object(runtime, "_handle_action", return_value=MagicMock()) as handler,
    ):
        runtime.on_event(action)
    loop.run_until_complete.assert_called_once()
    handler.assert_called_once_with(action)


def test_on_event_ignores_non_actions(runtime_factory):
    runtime = runtime_factory()
    with patch("asyncio.get_event_loop") as loop:
        runtime.on_event(object())  # type: ignore[arg-type]
    loop.assert_not_called()


def test_set_action_timeout_long_running(runtime_factory):
    runtime = runtime_factory()
    action = CmdRunAction(command="npm run dev")
    runtime._set_action_timeout(action)
    assert action.timeout is None
    assert action.blocking is False


def test_set_action_timeout_default(runtime_factory):
    runtime = runtime_factory()
    action = CmdRunAction(command="echo hello")
    runtime._set_action_timeout(action)
    assert action.timeout == runtime.config.sandbox.timeout
    assert action.blocking is False


def test_set_action_timeout_preserves_existing(runtime_factory):
    runtime = runtime_factory()
    action = CmdRunAction(command="echo")
    action.set_hard_timeout(5, blocking=True)
    runtime._set_action_timeout(action)
    assert action.timeout == 5
    assert action.blocking is True


@pytest.mark.asyncio
async def test_execute_action_calls_mcp(runtime_factory):
    runtime = runtime_factory()
    runtime_factory.provider_handler_cls.check_cmd_action_for_provider_token_ref.return_value = []
    event = MCPAction(name="mcp", thought="")
    expected = ErrorObservation("oops")
    runtime.call_tool_mcp = AsyncMock(return_value=expected)
    result = await runtime._execute_action(event)
    assert result is expected
    runtime.call_tool_mcp.assert_awaited_once_with(event)


def test_process_observation_sets_cause_and_metadata(runtime_factory):
    runtime = runtime_factory()
    event = CmdRunAction(command="echo", thought="hi")
    event._id = 42  # type: ignore[attr-defined]
    event.tool_call_metadata = MagicMock()
    observation = CmdOutputObservation(content="ok", command="echo", exit_code=0)
    assert runtime._process_observation(observation, event) is True
    assert observation._cause == 42  # type: ignore[attr-defined]
    assert observation.tool_call_metadata is event.tool_call_metadata


def test_process_observation_skips_null(runtime_factory):
    runtime = runtime_factory()
    event = CmdRunAction(command="echo")
    observation = NullObservation("")
    assert runtime._process_observation(observation, event) is False


@pytest.mark.asyncio
async def test_handle_action_success_adds_event(runtime_factory):
    runtime = runtime_factory()
    runtime.event_stream = MagicMock()
    event = CmdRunAction(command="echo hi")
    observation = CmdOutputObservation(content="done", command="echo hi", exit_code=0)
    with patch.object(runtime, "_execute_action", AsyncMock(return_value=observation)):
        await runtime._handle_action(event)
    runtime.event_stream.add_event.assert_called_once_with(
        observation, EventSource.AGENT
    )
    assert event.timeout == runtime.config.sandbox.timeout


@pytest.mark.asyncio
async def test_handle_action_permission_error(runtime_factory):
    runtime = runtime_factory()
    runtime.event_stream = MagicMock()
    event = CmdRunAction(command="echo hi")
    with patch.object(
        runtime,
        "_execute_action",
        AsyncMock(side_effect=PermissionError("denied")),
    ):
        await runtime._handle_action(event)
    add_event_call = runtime.event_stream.add_event.call_args
    assert add_event_call is not None
    args, _ = add_event_call
    assert isinstance(args[0], ErrorObservation)
    assert args[1] == EventSource.AGENT


@pytest.mark.asyncio
async def test_handle_action_network_error(runtime_factory):
    runtime = runtime_factory()
    runtime.event_stream = MagicMock()
    event = CmdRunAction(command="echo hi")
    error = httpx.NetworkError("boom")
    with (
        patch.object(runtime, "_execute_action", AsyncMock(side_effect=error)),
        patch.object(runtime, "_handle_runtime_error") as handle_error,
    ):
        await runtime._handle_action(event)
    handle_error.assert_called_once_with(event, error, is_network_error=True)
    runtime.event_stream.add_event.assert_not_called()


@pytest.mark.asyncio
async def test_handle_action_runtime_disconnected(runtime_factory):
    runtime = runtime_factory()
    runtime.event_stream = MagicMock()
    event = CmdRunAction(command="echo hi")
    error = AgentRuntimeDisconnectedError("lost connection")
    with (
        patch.object(runtime, "_execute_action", AsyncMock(side_effect=error)),
        patch.object(runtime, "_handle_runtime_error") as handle_error,
    ):
        await runtime._handle_action(event)
    handle_error.assert_called_once_with(event, error, is_network_error=True)


def test_handle_runtime_error_sets_status(runtime_factory):
    runtime = runtime_factory()
    runtime.log = MagicMock()
    runtime.set_runtime_status = MagicMock()
    event = CmdRunAction(command="echo")
    runtime._handle_runtime_error(event, ValueError("bad"), is_network_error=False)
    runtime.set_runtime_status.assert_called_once()
    status_call = runtime.set_runtime_status.call_args
    assert status_call is not None
    args, _ = status_call
    assert args[0] is RuntimeStatus.ERROR


@pytest.mark.asyncio
async def test_export_latest_git_provider_tokens_no_providers(runtime_factory):
    runtime = runtime_factory()
    runtime_factory.provider_handler_cls.check_cmd_action_for_provider_token_ref.return_value = []
    runtime.add_env_vars = MagicMock()
    event = CmdRunAction(command="echo hello")
    await runtime._export_latest_git_provider_tokens(event)
    runtime.add_env_vars.assert_not_called()


@pytest.mark.asyncio
async def test_export_latest_git_provider_tokens_updates_env(runtime_factory):
    runtime = runtime_factory()
    runtime.event_stream = MagicMock()
    runtime_factory.provider_handler_cls.check_cmd_action_for_provider_token_ref.return_value = [
        "github"
    ]
    handler = runtime_factory.provider_instance
    handler.get_env_vars = AsyncMock(return_value={"GH_TOKEN": "123"})
    handler.expose_env_vars.return_value = {"GH_TOKEN": "masked"}
    handler.set_event_stream_secrets = AsyncMock()
    runtime.add_env_vars = MagicMock()

    event = CmdRunAction(command="git push")
    await runtime._export_latest_git_provider_tokens(event)

    handler.get_env_vars.assert_awaited_once()
    handler.set_event_stream_secrets.assert_awaited_once_with(
        runtime.event_stream, env_vars={"GH_TOKEN": "123"}
    )
    runtime.add_env_vars.assert_called_once_with({"GH_TOKEN": "masked"})


@pytest.mark.asyncio
async def test_export_latest_git_provider_tokens_handles_exception(runtime_factory):
    runtime = runtime_factory()
    runtime.event_stream = MagicMock()
    runtime_factory.provider_handler_cls.check_cmd_action_for_provider_token_ref.return_value = [
        "github"
    ]
    handler = runtime_factory.provider_instance
    handler.get_env_vars = AsyncMock(return_value={"GH_TOKEN": "123"})
    handler.expose_env_vars.return_value = {"GH_TOKEN": "masked"}
    handler.set_event_stream_secrets = AsyncMock()

    runtime.add_env_vars = MagicMock(side_effect=RuntimeError("fail"))

    event = CmdRunAction(command="git push")
    with patch("forge.runtime.base.logger") as logger_mock:
        await runtime._export_latest_git_provider_tokens(event)
    logger_mock.warning.assert_called()


def test_runtime_handles_unsubscribe_failure(runtime_factory):
    config = ForgeConfig()
    event_stream = MagicMock()
    event_stream.unsubscribe.side_effect = RuntimeError("boom")
    runtime = runtime_factory(config=config, event_stream=event_stream)
    assert runtime.event_stream is event_stream
    assert event_stream.unsubscribe.called
    assert event_stream.subscribe.called


def test_runtime_initializes_security_analyzer(runtime_factory):
    class DummyAnalyzer(SecurityAnalyzer):
        pass

    config = ForgeConfig()
    config.security.security_analyzer = "dummy"
    with patch.dict(
        "forge.runtime.base.options.SecurityAnalyzers",
        {"dummy": DummyAnalyzer},
        clear=False,
    ):
        runtime = runtime_factory(config=config)
    assert isinstance(runtime.security_analyzer, DummyAnalyzer)


def test_runtime_close_is_noop(runtime_factory):
    runtime = runtime_factory()
    runtime.close()


@pytest.mark.asyncio
async def test_runtime_delete_is_noop():
    await DummyRuntime.delete("conversation-id")


def test_add_env_vars_to_bash_no_vars(runtime_factory):
    runtime = runtime_factory()
    runtime._add_env_vars_to_bash({})
    assert runtime.run_calls == []


def test_add_env_vars_to_bash_bashrc_failure(runtime_factory):
    responses = [
        CmdOutputObservation(content="", command="", exit_code=0),
        CmdOutputObservation(content="boom", command="", exit_code=1),
    ]
    runtime = runtime_factory(run_responses=responses)
    with pytest.raises(RuntimeError) as exc:
        runtime._add_env_vars_to_bash({"FOO": "bar"})
    assert "bashrc" in str(exc.value)
    assert len(runtime.run_calls) == 2


def test_execute_action_runs_command(runtime_factory):
    runtime = runtime_factory()
    event = CmdRunAction(command="echo hi")
    expected = CmdOutputObservation(content="done", command="echo hi", exit_code=0)

    with patch.object(runtime, "run", return_value=expected) as run_mock:
        result = runtime._execute_action(event)
    assert result is expected
    run_mock.assert_called_once_with(event)


@pytest.mark.asyncio
async def test_handle_action_generic_error(runtime_factory):
    runtime = runtime_factory()
    runtime.event_stream = MagicMock()
    event = CmdRunAction(command="echo hi")
    error = RuntimeError("boom")
    with (
        patch.object(runtime, "_execute_action", AsyncMock(side_effect=error)),
        patch.object(runtime, "_handle_runtime_error") as handle_error,
    ):
        await runtime._handle_action(event)
    handle_error.assert_called_once_with(event, error, is_network_error=False)
    runtime.event_stream.add_event.assert_not_called()


def test_log_clone_failure_records_details(runtime_factory):
    runtime = runtime_factory()
    runtime.log = MagicMock()
    obs = CmdOutputObservation(
        content="failure output", command="git clone", exit_code=128
    )
    runtime._log_clone_failure(obs, "org/.Forge")
    runtime.log.assert_any_call(
        "info", "No org-level microagents found at org/.Forge (exit_code: 128)"
    )
    runtime.log.assert_any_call("debug", "Clone command output: failure output")


def test_extract_org_name_invalid(runtime_factory):
    runtime = runtime_factory()
    runtime.log = MagicMock()
    assert runtime._extract_org_name("invalid") is None
    runtime.log.assert_called_once()


def test_run_action_agent_think_returns_observation(runtime_factory):
    runtime = runtime_factory()
    action = AgentThinkAction(thought="pondering")
    obs = runtime.run_action(action)
    assert isinstance(obs, AgentThinkObservation)


def test_run_action_task_tracking_delegates(runtime_factory):
    runtime = runtime_factory()
    action = TaskTrackingAction(command="plan")
    expected = TaskTrackingObservation(content="ok", command="plan", task_list=[])
    with patch.object(
        runtime, "_handle_task_tracking_action", return_value=expected
    ) as handler:
        obs = runtime.run_action(action)
    handler.assert_called_once_with(action)
    assert obs is expected


def test_run_action_confirmation_states(runtime_factory):
    runtime = runtime_factory()
    action = CmdRunAction(command="echo wait")
    action.confirmation_state = ActionConfirmationStatus.AWAITING_CONFIRMATION
    assert isinstance(runtime.run_action(action), NullObservation)
    action.confirmation_state = ActionConfirmationStatus.REJECTED
    result = runtime.run_action(action)
    assert isinstance(result, UserRejectObservation)


def test_run_action_validation_error(runtime_factory):
    runtime = runtime_factory()
    result = runtime.run_action(UnknownAction())
    assert isinstance(result, ErrorObservation)
    assert "does not exist" in result.content


def test_run_action_agent_level_action_returns_null(runtime_factory):
    runtime = runtime_factory()
    action = MessageAction(content="hello")
    with (
        patch.object(runtime, "_validate_action", return_value=None),
        patch.object(runtime, "_execute_action") as execute_mock,
    ):
        obs = runtime.run_action(action)
    assert isinstance(obs, NullObservation)
    execute_mock.assert_not_called()


def test_run_action_verification_overrides_observation(runtime_factory):
    runtime = runtime_factory()
    action = FileEditAction(path="foo.txt")
    base_obs = CmdOutputObservation(content="edited", command="cmd", exit_code=0)
    verification = FileWriteObservation(content="verified", path="foo.txt")
    with (
        patch.object(runtime, "_validate_action", return_value=None),
        patch.object(runtime, "_execute_action", return_value=base_obs),
        patch.object(runtime, "_verify_action_if_needed", return_value=verification),
    ):
        result = runtime.run_action(action)
    assert result is verification


def test_run_action_returns_original_observation(runtime_factory):
    runtime = runtime_factory()
    action = CmdRunAction(command="echo hi")
    base_obs = CmdOutputObservation(content="hi", command="echo hi", exit_code=0)
    with (
        patch.object(runtime, "_validate_action", return_value=None),
        patch.object(runtime, "_execute_action", return_value=base_obs),
        patch.object(runtime, "_verify_action_if_needed", return_value=None),
    ):
        result = runtime.run_action(action)
    assert result is base_obs


def test_handle_task_tracking_plan_success(runtime_factory):
    runtime = runtime_factory()
    runtime.event_stream = MagicMock()
    runtime.event_stream.user_id = "user"
    runtime.event_stream.file_store.write = MagicMock()
    action = TaskTrackingAction(
        command="plan",
        task_list=[{"title": "Task", "status": "done", "notes": "note"}],
    )
    with patch("forge.runtime.base.get_conversation_dir", return_value="/tmp/session/"):
        obs = runtime._handle_task_tracking_action(action)
    runtime.event_stream.file_store.write.assert_called_once()
    assert isinstance(obs, TaskTrackingObservation)
    assert "Task list has been updated" in obs.content


def test_handle_task_tracking_plan_failure(runtime_factory):
    runtime = runtime_factory()
    runtime.event_stream = MagicMock()
    runtime.event_stream.user_id = "user"
    runtime.event_stream.file_store.write.side_effect = Exception("disk full")
    action = TaskTrackingAction(command="plan", task_list=[])
    result = runtime._handle_task_plan_action(action, "/tmp/session/TASKS.md")
    assert isinstance(result, ErrorObservation)
    assert "Failed to write task list" in result.content


def test_handle_task_tracking_view_success(runtime_factory):
    runtime = runtime_factory()
    runtime.event_stream = MagicMock()
    runtime.event_stream.file_store.read.return_value = "Task content"
    action = TaskTrackingAction(command="view")
    result = runtime._handle_task_view_action(action, "/tmp/session/TASKS.md")
    assert isinstance(result, TaskTrackingObservation)
    assert result.content == "Task content"


def test_handle_task_tracking_view_missing(runtime_factory):
    runtime = runtime_factory()
    runtime.event_stream = MagicMock()
    runtime.event_stream.file_store.read.side_effect = FileNotFoundError()
    action = TaskTrackingAction(command="view")
    result = runtime._handle_task_view_action(action, "/tmp/session/TASKS.md")
    assert isinstance(result, TaskTrackingObservation)
    assert "No task list found" in result.content


def test_handle_task_tracking_view_error(runtime_factory):
    runtime = runtime_factory()
    runtime.event_stream = MagicMock()
    runtime.event_stream.file_store.read.side_effect = RuntimeError("failure")
    action = TaskTrackingAction(command="view")
    result = runtime._handle_task_view_action(action, "/tmp/session/TASKS.md")
    assert isinstance(result, TaskTrackingObservation)
    assert "Failed to read the task list" in result.content


def test_generate_task_list_content_formats_output(runtime_factory):
    runtime = runtime_factory()
    tasks = [
        {"title": "todo item", "notes": "note"},
        {"title": "progress", "status": "in_progress", "notes": ""},
        {"title": "done", "status": "done", "notes": ""},
    ]
    content = runtime._generate_task_list_content(tasks)
    assert "⏳" in content
    assert "🔄" in content
    assert "✅" in content


def test_check_action_confirmation_returns_none_when_confirmed(runtime_factory):
    runtime = runtime_factory()
    action = CmdRunAction(command="echo")
    assert runtime._check_action_confirmation(action) is None


def test_validate_action_agent_level_allowed(runtime_factory):
    runtime = runtime_factory()
    action = MessageAction(content="hi")
    assert runtime._validate_action(action) is None


def test_validate_action_missing_runtime_method(runtime_factory):
    runtime = runtime_factory()

    @dataclass
    class CustomAction(Action):
        action: ClassVar[str] = "custom_action"

    with patch.dict(
        "forge.runtime.base.ACTION_TYPE_TO_CLASS",
        {"custom_action": CustomAction},
        clear=False,
    ):
        result = runtime._validate_action(CustomAction())
    assert isinstance(result, ErrorObservation)
    assert "not supported" in result.content


def test_get_git_diff_delegates(runtime_factory):
    runtime = runtime_factory()
    runtime.git_handler = MagicMock()
    runtime.get_git_diff("file.py", "/tmp/repo")
    runtime.git_handler.set_cwd.assert_called_once_with("/tmp/repo")
    runtime.git_handler.get_git_diff.assert_called_once_with("file.py")


def test_get_workspace_branch_with_repo(runtime_factory):
    runtime = runtime_factory()
    runtime.config.workspace_mount_path_in_sandbox = "/tmp/workspace"
    runtime.git_handler = MagicMock()
    runtime.git_handler.get_current_branch.return_value = "main"
    branch = runtime.get_workspace_branch("repo")
    runtime.git_handler.set_cwd.assert_called_once_with(
        str(Path("/tmp/workspace") / "repo")
    )
    assert branch == "main"


def test_execute_shell_fn_git_handler_handles_observations(runtime_factory):
    runtime = runtime_factory()
    success = CmdOutputObservation(content="ok", command="git", exit_code=0)
    runtime.run = MagicMock(return_value=success)
    result = runtime._execute_shell_fn_git_handler("git status", "/tmp/repo")
    assert result.exit_code == 0
    assert result.content == "ok"

    runtime.run.return_value = ErrorObservation("bad")
    result = runtime._execute_shell_fn_git_handler("git status", None)
    assert result.exit_code in (-1, None)
    assert result.content == "bad"


def test_create_file_fn_git_handler_returns_codes(runtime_factory):
    runtime = runtime_factory()
    runtime.write = MagicMock(return_value=NullObservation(""))
    assert runtime._create_file_fn_git_handler("path.txt", "content") == 0
    runtime.write.return_value = ErrorObservation("fail")
    assert runtime._create_file_fn_git_handler("path.txt", "content") == -1


def test_runtime_context_manager_calls_close(runtime_factory):
    runtime = runtime_factory()
    with patch.object(runtime, "close") as close_mock:
        with runtime:
            pass
    close_mock.assert_called_once()


def test_runtime_session_api_key_default_none(runtime_factory):
    runtime = runtime_factory()
    assert runtime.session_api_key is None


def test_runtime_additional_agent_instructions_empty(runtime_factory):
    runtime = runtime_factory()
    assert runtime.additional_agent_instructions() == ""


def test_runtime_setup_teardown_noop(runtime_factory):
    DummyRuntime.setup(ForgeConfig())
    DummyRuntime.teardown(ForgeConfig())


def test_runtime_subscribe_to_shell_stream_returns_none(runtime_factory):
    runtime = runtime_factory()
    assert runtime.subscribe_to_shell_stream() is None


@pytest.mark.asyncio
async def test_runtime_super_async_noops(runtime_factory):
    runtime = runtime_factory()
    assert await super(DummyRuntime, runtime).connect() is None
    mcp_action = MCPAction(name="noop", thought="")
    assert await super(DummyRuntime, runtime).call_tool_mcp(mcp_action) is None


def test_runtime_super_sync_noops(runtime_factory):
    runtime = runtime_factory()
    cmd_action = CmdRunAction(command="echo")
    read_action = FileReadAction(path="file.txt")
    write_action = FileWriteAction(path="file.txt", content="data")
    edit_action = FileEditAction(path="file.txt")
    browse_action = BrowseURLAction(url="https://example.com")
    browse_interactive_action = BrowseInteractiveAction(browser_actions="")

    assert super(DummyRuntime, runtime).run(cmd_action) is None
    assert super(DummyRuntime, runtime).read(read_action) is None
    assert super(DummyRuntime, runtime).write(write_action) is None
    assert super(DummyRuntime, runtime).edit(edit_action) is None
    assert super(DummyRuntime, runtime).browse(browse_action) is None
    assert (
        super(DummyRuntime, runtime).browse_interactive(browse_interactive_action)
        is None
    )


def test_runtime_super_copy_methods_raise(runtime_factory):
    runtime = runtime_factory()
    with pytest.raises(NotImplementedError):
        super(DummyRuntime, runtime).copy_to("src", "dest")
    with pytest.raises(NotImplementedError):
        super(DummyRuntime, runtime).copy_from("path")
    with pytest.raises(NotImplementedError):
        super(DummyRuntime, runtime).list_files("path")
