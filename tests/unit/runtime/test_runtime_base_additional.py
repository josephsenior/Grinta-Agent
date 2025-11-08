from __future__ import annotations

import os
from typing import Any, List
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

from forge.core.config import ForgeConfig, SandboxConfig
from forge.core.exceptions import AgentRuntimeDisconnectedError
from forge.events.action import CmdRunAction, IPythonRunCellAction, MCPAction
from forge.events.event import EventSource
from forge.events.observation import CmdOutputObservation, ErrorObservation, NullObservation
from forge.runtime.base import (
    JupyterRequirement,
    Runtime,
    VSCodeRequirement,
    _default_env_vars,
)
from forge.runtime.runtime_status import RuntimeStatus


class DummyRuntime(Runtime):
    """Concrete runtime implementation for unit testing the base Runtime class."""

    def __init__(
        self,
        config: ForgeConfig,
        event_stream: Any,
        llm_registry: Any,
        *,
        run_responses: List[CmdOutputObservation] | None = None,
        ipython_response: NullObservation | None = None,
        **kwargs: Any,
    ) -> None:
        self._run_responses: list[CmdOutputObservation] = run_responses or []
        self._ipython_response = ipython_response
        self.run_calls: list[str] = []
        self.run_ipython_calls: list[str] = []
        super().__init__(config, event_stream, llm_registry, **kwargs)

    async def connect(self) -> None:  # pragma: no cover - not used in tests
        self._runtime_initialized = True

    def get_mcp_config(self, extra_stdio_servers=None):  # pragma: no cover - unused
        return MagicMock()

    def run(self, action: CmdRunAction):
        self.run_calls.append(action.command)
        if self._run_responses:
            response = self._run_responses.pop(0)
            if isinstance(response, CmdOutputObservation):
                response.command = action.command
            return response
        return CmdOutputObservation(content="", command=action.command, exit_code=0)

    def run_ipython(self, action: IPythonRunCellAction):
        self.run_ipython_calls.append(action.code)
        return self._ipython_response or NullObservation("")

    def read(self, action):  # pragma: no cover - interface requirement
        return NullObservation("")

    def write(self, action):  # pragma: no cover - interface requirement
        return NullObservation("")

    def edit(self, action):  # pragma: no cover - interface requirement
        return NullObservation("")

    def browse(self, action):  # pragma: no cover - interface requirement
        return NullObservation("")

    def browse_interactive(self, action):  # pragma: no cover - interface requirement
        return NullObservation("")

    async def call_tool_mcp(self, action):  # pragma: no cover - interface requirement
        return NullObservation("")


def _fake_file_edit_init(self, enable_llm_editor, llm_registry, *args, **kwargs):
    """Inject minimal state for FileEditRuntimeMixin during tests."""
    self.enable_llm_editor = enable_llm_editor
    self.llm_registry = llm_registry


@pytest.fixture
def runtime_factory():
    provider_instance = MagicMock()
    provider_env = {"PROVIDER_TOKEN": "abc"}
    call_async_mock = MagicMock(return_value=provider_env)

    with (
        patch("forge.runtime.base.ProviderHandler") as provider_handler_cls,
        patch("forge.runtime.base.call_async_from_sync", call_async_mock),
        patch("forge.runtime.base.GitHandler"),
        patch("forge.runtime.utils.process_manager.ProcessManager"),
        patch("forge.runtime.base.FileEditRuntimeMixin.__init__", side_effect=_fake_file_edit_init),
        patch("forge.runtime.base.atexit.register"),
    ):
        provider_handler_cls.return_value = provider_instance
        def factory(**kwargs: Any) -> DummyRuntime:
            config: ForgeConfig = kwargs.pop("config", ForgeConfig())
            event_stream = kwargs.pop("event_stream", MagicMock())
            llm_registry = kwargs.pop("llm_registry", MagicMock())
            return DummyRuntime(config, event_stream, llm_registry, **kwargs)

        factory.provider_instance = provider_instance
        factory.provider_handler_cls = provider_handler_cls
        factory.call_async_mock = call_async_mock
        yield factory


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
        runtime = runtime_factory(config=config, env_vars={"extra": "1"}, event_stream=event_stream)
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
    assert add_env_vars.call_args_list[1].args[0] == config.sandbox.runtime_startup_env_vars
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


def test_add_env_vars_to_jupyter_invokes_ipython(runtime_factory):
    runtime = runtime_factory()
    with patch.object(runtime, "run_ipython", return_value=NullObservation("")) as run_ipython:
        runtime._add_env_vars_to_jupyter({"FOO": "bar"})
    action = run_ipython.call_args.args[0]
    assert isinstance(action, IPythonRunCellAction)
    assert 'os.environ["FOO"] = "bar"' in action.code


def test_build_powershell_env_cmd(runtime_factory):
    runtime = runtime_factory()
    cmd = runtime._build_powershell_env_cmd({"FOO": "bar", "BAZ": "qux"})
    assert "$env:FOO = \"bar\";" in cmd
    assert "$env:BAZ = \"qux\";" in cmd


def test_add_env_vars_to_powershell_success(runtime_factory):
    success = CmdOutputObservation(content="", command="", exit_code=0)
    runtime = runtime_factory(run_responses=[success])
    runtime._add_env_vars_to_powershell({"FOO": "bar"})
    assert runtime.run_calls == ["$env:FOO = \"bar\";"]


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
    runtime.plugins.append(JupyterRequirement())
    with (
        patch.object(runtime, "_add_env_vars_to_jupyter") as mock_jupyter,
        patch.object(runtime, "_add_env_vars_to_powershell") as mock_power,
        patch.object(runtime, "_add_env_vars_to_bash") as mock_bash,
        patch("os.name", "nt"),
        patch("sys.platform", "win32"),
    ):
        runtime.add_env_vars({"foo": "bar"})
    mock_jupyter.assert_called_once()
    mock_power.assert_called_once()
    mock_bash.assert_not_called()
    assert mock_power.call_args.args[0] == {"FOO": "bar"}


def test_add_env_vars_routes_to_bash_on_posix(runtime_factory):
    runtime = runtime_factory()
    runtime.plugins.append(JupyterRequirement())
    with (
        patch.object(runtime, "_add_env_vars_to_jupyter") as mock_jupyter,
        patch.object(runtime, "_add_env_vars_to_powershell") as mock_power,
        patch.object(runtime, "_add_env_vars_to_bash") as mock_bash,
        patch("os.name", "posix"),
        patch("sys.platform", "linux"),
    ):
        runtime.add_env_vars({"foo": "bar"})
    mock_jupyter.assert_called_once()
    mock_power.assert_not_called()
    mock_bash.assert_called_once()
    assert mock_bash.call_args.args[0] == {"FOO": "bar"}


def test_setup_git_config_success(runtime_factory):
    runtime = runtime_factory()
    runtime.config.git_user_name = "Alice"
    runtime.config.git_user_email = "alice@example.com"
    obs = CmdOutputObservation(content="", command="", exit_code=0)
    with patch.object(runtime, "run", return_value=obs) as run_mock, patch(
        "forge.runtime.base.logger"
    ) as logger_mock:
        runtime._setup_git_config()
    run_mock.assert_called_once()
    logger_mock.info.assert_called()


def test_setup_git_config_cli_skips(runtime_factory):
    runtime = runtime_factory()
    runtime.config.runtime = "cli"
    with patch.object(runtime, "run") as run_mock:
        runtime._setup_git_config()
    run_mock.assert_not_called()


def test_setup_git_config_warns_on_failure(runtime_factory):
    runtime = runtime_factory()
    failure_obs = CmdOutputObservation(content="err", command="", exit_code=1)
    with patch.object(runtime, "run", return_value=failure_obs), patch(
        "forge.runtime.base.logger"
    ) as logger_mock:
        runtime._setup_git_config()
    logger_mock.warning.assert_called()


def test_on_event_runs_actions(runtime_factory):
    runtime = runtime_factory()
    action = CmdRunAction(command="echo hello")
    loop = MagicMock()
    with patch("asyncio.get_event_loop", return_value=loop), patch.object(
        runtime, "_handle_action", return_value=MagicMock()
    ) as handler:
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


def test_process_observation_sets_metadata(runtime_factory):
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
    args, _ = runtime.event_stream.add_event.call_args
    assert isinstance(args[0], ErrorObservation)
    assert args[1] == EventSource.AGENT


@pytest.mark.asyncio
async def test_handle_action_network_error(runtime_factory):
    runtime = runtime_factory()
    runtime.event_stream = MagicMock()
    event = CmdRunAction(command="echo hi")
    error = httpx.NetworkError("boom")
    with patch.object(
        runtime, "_execute_action", AsyncMock(side_effect=error)
    ), patch.object(runtime, "_handle_runtime_error") as handle_error:
        await runtime._handle_action(event)
    handle_error.assert_called_once_with(event, error, is_network_error=True)
    runtime.event_stream.add_event.assert_not_called()


@pytest.mark.asyncio
async def test_handle_action_runtime_disconnected(runtime_factory):
    runtime = runtime_factory()
    runtime.event_stream = MagicMock()
    event = CmdRunAction(command="echo hi")
    error = AgentRuntimeDisconnectedError("lost connection")
    with patch.object(
        runtime, "_execute_action", AsyncMock(side_effect=error)
    ), patch.object(runtime, "_handle_runtime_error") as handle_error:
        await runtime._handle_action(event)
    handle_error.assert_called_once_with(event, error, is_network_error=True)


def test_handle_runtime_error_sets_status(runtime_factory):
    runtime = runtime_factory()
    runtime.log = MagicMock()
    runtime.set_runtime_status = MagicMock()
    event = CmdRunAction(command="echo")
    runtime._handle_runtime_error(event, ValueError("bad"), is_network_error=False)
    runtime.set_runtime_status.assert_called_once()
    args = runtime.set_runtime_status.call_args[0]
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
    runtime_factory.provider_handler_cls.check_cmd_action_for_provider_token_ref.return_value = ["github"]
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
    runtime_factory.provider_handler_cls.check_cmd_action_for_provider_token_ref.return_value = ["github"]
    handler = runtime_factory.provider_instance
    handler.get_env_vars = AsyncMock(return_value={"GH_TOKEN": "123"})
    handler.expose_env_vars.return_value = {"GH_TOKEN": "masked"}
    handler.set_event_stream_secrets = AsyncMock()

    runtime.add_env_vars = MagicMock(side_effect=RuntimeError("fail"))

    event = CmdRunAction(command="git push")
    with patch("forge.runtime.base.logger") as logger_mock:
        await runtime._export_latest_git_provider_tokens(event)
    logger_mock.warning.assert_called()

