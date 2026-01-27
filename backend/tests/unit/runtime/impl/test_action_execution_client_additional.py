from __future__ import annotations

import importlib
import json
import os
import sys
import tempfile
import types
from pathlib import Path
from typing import TYPE_CHECKING, Any, Callable, TypeAlias, cast

import httpx
import pytest

_ORIGINAL_MODULES: dict[str, types.ModuleType | None] = {}
ROOT_DIR = Path(__file__).resolve().parents[4]
ResponseQueue: TypeAlias = list[Any]
StatsCalls: TypeAlias = list[int]
ActionMap: TypeAlias = dict[str, type]


def _set_module(name: str, module: types.ModuleType) -> None:
    if name not in _ORIGINAL_MODULES:
        _ORIGINAL_MODULES[name] = sys.modules.get(name)
    sys.modules[name] = module


# ---------------------------------------------------------------------------
# Stub Forge package tree
# ---------------------------------------------------------------------------

forge_pkg = types.ModuleType("forge")
forge_pkg.__path__ = [str(ROOT_DIR / "forge")]
_set_module("forge", forge_pkg)

runtime_pkg = types.ModuleType("forge.runtime")
runtime_pkg.__path__ = [str(ROOT_DIR / "forge" / "runtime")]
_set_module("forge.runtime", runtime_pkg)

impl_pkg = types.ModuleType("forge.runtime.impl")
impl_pkg.__path__ = [str(ROOT_DIR / "forge" / "runtime" / "impl")]
_set_module("forge.runtime.impl", impl_pkg)
setattr(forge_pkg, "runtime", runtime_pkg)
setattr(runtime_pkg, "impl", impl_pkg)

core_pkg = types.ModuleType("forge.core")
core_pkg.__path__ = [str(ROOT_DIR / "forge" / "core")]
_set_module("forge.core", core_pkg)
setattr(forge_pkg, "core", core_pkg)

runtime_utils_pkg = types.ModuleType("forge.runtime.utils")
runtime_utils_pkg.__path__ = [str(ROOT_DIR / "forge" / "runtime" / "utils")]
_set_module("forge.runtime.utils", runtime_utils_pkg)
setattr(runtime_pkg, "utils", runtime_utils_pkg)

action_exec_pkg = types.ModuleType("forge.runtime.impl.action_execution")
action_exec_pkg.__path__ = [
    str(ROOT_DIR / "forge" / "runtime" / "impl" / "action_execution")
]
_set_module("forge.runtime.impl.action_execution", action_exec_pkg)
setattr(impl_pkg, "action_execution", action_exec_pkg)

# ---------------------------------------------------------------------------
# Core exception/logger stubs
# ---------------------------------------------------------------------------

exceptions_module = types.ModuleType("forge.core.exceptions")
setattr(
    exceptions_module,
    "AgentRuntimeTimeoutError",
    type("AgentRuntimeTimeoutError", (Exception,), {}),
)
_set_module("forge.core.exceptions", exceptions_module)
setattr(core_pkg, "exceptions", exceptions_module)

logger_module = types.ModuleType("forge.core.logger")
setattr(
    logger_module,
    "forge_logger",
    types.SimpleNamespace(
        debug=lambda *a, **k: None,
        info=lambda *a, **k: None,
        warning=lambda *a, **k: None,
        error=lambda *a, **k: None,
    ),
)
_set_module("forge.core.logger", logger_module)
setattr(core_pkg, "logger", logger_module)

# ---------------------------------------------------------------------------
# Runtime base / utils stubs
# ---------------------------------------------------------------------------

runtime_base = types.ModuleType("forge.runtime.base")


class RuntimeBase:
    def __init__(self, *args: Any, **kwargs: Any) -> None:
        self.config = kwargs.get("config")
        self._session_api_key: str | None = None

    def close(self) -> None:
        return None

    async def connect(self) -> None:
        return None

    def get_mcp_config(self, extra_stdio_servers: list[Any] | None = None) -> Any:
        return {}

    def run(self, action: Any) -> Any:
        return None

    def read(self, action: Any) -> Any:
        return None

    def write(self, action: Any) -> Any:
        return None

    def edit(self, action: Any) -> Any:
        return None

    def copy_to(
        self, host_src: str, sandbox_dest: str, recursive: bool = False
    ) -> None:
        return None

    def copy_from(self, path: str) -> Path:
        return Path(path)

    def list_files(self, path: str, recursive: bool = False) -> list[str]:
        return []

    def browse(self, action: Any) -> Any:
        return None

    def browse_interactive(self, action: Any) -> Any:
        return None

    async def call_tool_mcp(self, action: Any) -> Any:
        return None

    @property
    def session_api_key(self) -> str | None:
        return self._session_api_key

    @session_api_key.setter
    def session_api_key(self, value: str | None) -> None:
        self._session_api_key = value


setattr(runtime_base, "Runtime", RuntimeBase)
_set_module("forge.runtime.base", runtime_base)
setattr(runtime_pkg, "base", runtime_base)

request_module = types.ModuleType("forge.runtime.utils.request")
_RESPONSE_QUEUE: ResponseQueue = []


def send_request_stub(session, method: str, url: str, **kwargs):
    if not _RESPONSE_QUEUE:
        raise AssertionError("No responses configured")
    result = _RESPONSE_QUEUE.pop(0)
    if isinstance(result, Exception):
        raise result
    return result


setattr(request_module, "send_request", send_request_stub)
_set_module("forge.runtime.utils.request", request_module)
setattr(runtime_utils_pkg, "request", request_module)

stats_module = types.ModuleType("forge.runtime.utils.system_stats")
_stats_calls: StatsCalls = []
setattr(stats_module, "update_last_execution_time", lambda: _stats_calls.append(1))
_set_module("forge.runtime.utils.system_stats", stats_module)
setattr(runtime_utils_pkg, "system_stats", stats_module)

async_utils_module = types.ModuleType("forge.utils.async_utils")
setattr(async_utils_module, "call_sync_from_async", lambda fn, *a, **k: fn(*a, **k))
setattr(async_utils_module, "call_async_from_sync", lambda fn, *a, **k: None)
setattr(async_utils_module, "GENERAL_TIMEOUT", 30)
_set_module("forge.utils.async_utils", async_utils_module)
setattr(forge_pkg, "utils", types.SimpleNamespace(async_utils=async_utils_module))
setattr(runtime_utils_pkg, "async_utils", async_utils_module)

metrics_module = types.ModuleType("forge.utils.tenacity_metrics")
setattr(metrics_module, "tenacity_after_factory", lambda label: (lambda state: None))
setattr(
    metrics_module, "tenacity_before_sleep_factory", lambda label: (lambda state: None)
)
setattr(metrics_module, "call_tenacity_hooks", lambda before, after, state: None)
_set_module("forge.utils.tenacity_metrics", metrics_module)
setattr(forge_pkg.utils, "tenacity_metrics", metrics_module)
setattr(runtime_utils_pkg, "tenacity_metrics", metrics_module)

stop_module = types.ModuleType("forge.utils.tenacity_stop")
setattr(stop_module, "stop_if_should_exit", lambda: (lambda retry_state: False))
_set_module("forge.utils.tenacity_stop", stop_module)
setattr(forge_pkg.utils, "tenacity_stop", stop_module)
setattr(runtime_utils_pkg, "tenacity_stop", stop_module)

# ---------------------------------------------------------------------------
# MCP config / pydantic compat stubs
# ---------------------------------------------------------------------------

mcp_config_pkg = types.ModuleType("forge.core.config")
mcp_config_pkg.__path__ = [str(ROOT_DIR / "forge" / "core" / "config")]
_set_module("forge.core.config", mcp_config_pkg)
setattr(core_pkg, "config", mcp_config_pkg)

mcp_config_module = types.ModuleType("forge.core.config.mcp_config")


class MCPStdioServerConfig:
    def __init__(self, name: str):
        self.name = name


class MCPSSEServerConfig:
    def __init__(self, url: str, api_key: str | None = None):
        self.url = url
        self.api_key = api_key


class MCPConfig:
    def __init__(
        self,
        sse_servers: list[Any] | None = None,
        stdio_servers: list[Any] | None = None,
        shttp_servers: list[Any] | None = None,
    ):
        self.sse_servers = list(sse_servers or [])
        self.stdio_servers = list(stdio_servers or [])
        self.shttp_servers = list(shttp_servers or [])

    def model_copy(self):
        return MCPConfig(
            self.sse_servers.copy(),
            self.stdio_servers.copy(),
            self.shttp_servers.copy(),
        )


setattr(mcp_config_module, "MCPConfig", MCPConfig)
setattr(mcp_config_module, "MCPStdioServerConfig", MCPStdioServerConfig)
setattr(mcp_config_module, "MCPSSEServerConfig", MCPSSEServerConfig)
_set_module("forge.core.config.mcp_config", mcp_config_module)
setattr(mcp_config_pkg, "mcp_config", mcp_config_module)

compat_module = types.ModuleType("forge.core.pydantic_compat")
setattr(
    compat_module,
    "model_dump_with_options",
    lambda obj, mode=None: obj.__dict__ if hasattr(obj, "__dict__") else dict(obj),
)
_set_module("forge.core.pydantic_compat", compat_module)
setattr(core_pkg, "pydantic_compat", compat_module)

# ---------------------------------------------------------------------------
# Events / observations stubs
# ---------------------------------------------------------------------------

events_pkg = types.ModuleType("forge.events")
events_pkg.__path__ = [str(ROOT_DIR / "forge" / "events")]
_set_module("forge.events", events_pkg)
setattr(forge_pkg, "events", events_pkg)

actions_module = types.ModuleType("forge.events.action")


class BaseAction:
    def __init__(
        self, action: str, *, timeout: int | None = None, runnable: bool = True
    ):
        self.action = action
        self.timeout = timeout
        self.runnable = runnable
        self.confirmation_state = None
        self.blocking = False
        self.hidden = False
        self.id = "action-id"

    def set_hard_timeout(self, timeout: int | None, blocking: bool = False):
        self.timeout = timeout
        self.blocking = blocking


class CmdRunAction(BaseAction):
    def __init__(self, command: str, **kwargs):
        super().__init__("run", **kwargs)
        self.command = command


class BrowseURLAction(BaseAction):
    pass


class BrowseInteractiveAction(BaseAction):
    pass


class FileReadAction(BaseAction):
    def __init__(self, path: str, *args, **kwargs):
        super().__init__("read", *args, **kwargs)
        self.path = path
        self.impl_source = "local"
        self.view_range = None


class FileWriteAction(BaseAction):
    def __init__(self, path: str, content: str, *args, **kwargs):
        super().__init__("write", *args, **kwargs)
        self.path = path
        self.content = content


class AgentThinkAction(BaseAction):
    pass


class FileEditAction(BaseAction):
    def __init__(self, path: str, command: str = "edit", *args, **kwargs):
        super().__init__("edit", *args, **kwargs)
        self.path = path
        self.command = command
        self.file_text = None
        self.old_str = None
        self.new_str = None
        self.insert_line = None
        self.impl_source = "file_editor"


setattr(actions_module, "CmdRunAction", CmdRunAction)
setattr(actions_module, "FileReadAction", FileReadAction)
setattr(actions_module, "FileWriteAction", FileWriteAction)
setattr(actions_module, "FileEditAction", FileEditAction)
setattr(actions_module, "BrowseURLAction", BrowseURLAction)
setattr(actions_module, "BrowseInteractiveAction", BrowseInteractiveAction)
setattr(actions_module, "AgentFinishAction", AgentFinishAction)
setattr(actions_module, "MessageAction", MessageAction)
setattr(actions_module, "AgentThinkAction", AgentThinkAction)
setattr(actions_module, "NullAction", NullAction)
setattr(actions_module, "ChangeAgentStateAction", ChangeAgentStateAction)
setattr(actions_module, "ActionConfirmationStatus", type("ActionConfirmationStatus", (), {"CONFIRMED": "confirmed"}))
_set_module("forge.events.action", actions_module)
setattr(events_pkg, "action", actions_module)

files_module = types.ModuleType("forge.events.action.files")
setattr(
    files_module,
    "FileEditSource",
    types.SimpleNamespace(LLM_BASED_EDIT="llm", FILE_EDITOR="file_editor"),
)
_set_module("forge.events.action.files", files_module)
setattr(actions_module, "files", files_module)

observation_module = types.ModuleType("forge.events.observation")


class Observation:
    def __init__(self, content: str = "", **kwargs):
        self.content = content
        self.metadata = kwargs.get("metadata", {})
        self.cause = None


class ErrorObservation(Observation):
    pass


class NullObservation(Observation):
    pass


class FileReadObservation(Observation):
    pass


class FileWriteObservation(Observation):
    pass


class AgentThinkObservation(Observation):
    pass


serialization_pkg = types.ModuleType("forge.events.serialization")
setattr(
    serialization_pkg,
    "event_to_dict",
    lambda action: {"action": action.action, "id": action.id},
)
setattr(
    serialization_pkg,
    "observation_from_dict",
    lambda data: Observation(content=data.get("content", "")),
)
_set_module("forge.events.serialization", serialization_pkg)

serialization_action_module = types.ModuleType("forge.events.serialization.action")
action_type_map: ActionMap = {
    "run": CmdRunAction,
    "read": FileReadAction,
    "write": FileWriteAction,
    "edit": FileEditAction,
    "browse": BrowseURLAction,
    "browse_interactive": BrowseInteractiveAction,
    "think": AgentThinkAction,
}
setattr(serialization_action_module, "ACTION_TYPE_TO_CLASS", action_type_map)
_set_module("forge.events.serialization.action", serialization_action_module)
setattr(serialization_pkg, "action", serialization_action_module)

setattr(observation_module, "Observation", Observation)
setattr(observation_module, "CmdOutputObservation", Observation)
setattr(observation_module, "ErrorObservation", ErrorObservation)
setattr(observation_module, "FileReadObservation", FileReadObservation)
setattr(observation_module, "FileWriteObservation", FileWriteObservation)
setattr(observation_module, "NullObservation", NullObservation)
setattr(observation_module, "AgentThinkObservation", AgentThinkObservation)
setattr(observation_module, "UserRejectObservation", Observation)
setattr(observation_module, "TaskTrackingObservation", Observation)
_set_module("forge.events.observation", observation_module)
setattr(events_pkg, "observation", observation_module)
setattr(events_pkg, "action", actions_module)
setattr(events_pkg, "serialization", serialization_pkg)

# ---------------------------------------------------------------------------
# Http session stub
# ---------------------------------------------------------------------------

http_session_module = types.ModuleType("forge.utils.http_session")


class HttpSession:
    def __init__(self) -> None:
        self.headers: dict[str, str] = {}
        self.stream_calls: list[tuple[str, str]] = []

    def stream(self, method: str, url: str, params: dict[str, Any], timeout: float):
        class _Stream:
            def __enter__(self_inner):
                return self_inner

            def __exit__(self_inner, exc_type, exc, tb):
                return False

            def iter_bytes(self_inner):
                yield b"test"

        self.stream_calls.append((method, url))
        return _Stream()


setattr(http_session_module, "HttpSession", HttpSession)
_set_module("forge.utils.http_session", http_session_module)
setattr(forge_pkg.utils, "http_session", http_session_module)
setattr(runtime_utils_pkg, "http_session", http_session_module)

# ---------------------------------------------------------------------------
# Import target module
# ---------------------------------------------------------------------------

action_exec_module = importlib.import_module(
    "forge.runtime.impl.action_execution.action_execution_client"
)

if TYPE_CHECKING:
    from forge.runtime.impl.action_execution.action_execution_client import (
        ActionExecutionClient as ActionExecutionClientBase,
    )
else:
    ActionExecutionClientBase = cast(
        type, getattr(action_exec_module, "ActionExecutionClient")
    )

send_request = cast(Callable[..., Any], getattr(action_exec_module, "send_request"))


class ClientUnderTest(ActionExecutionClientBase):
    _workspace_path: str | None

    def __init__(self, config, *args, **kwargs):
        super().__init__(config, *args, **kwargs)
        self.config = config
        self._runtime_initialized = False
        self._workspace_path = None

    @property
    def action_execution_server_url(self) -> str:
        return "http://runtime"

    @property
    def runtime_initialized(self) -> bool:
        return getattr(self, "_runtime_initialized", False)

    @runtime_initialized.setter
    def runtime_initialized(self, value: bool) -> None:
        self._runtime_initialized = value

    def log(self, level: str, message: str, exc_info: bool | None = None) -> None:
        return None

    async def connect(self) -> None:
        return None


@pytest.fixture(autouse=True)
def reset_responses(monkeypatch):
    _RESPONSE_QUEUE.clear()
    _stats_calls.clear()
    yield
    _RESPONSE_QUEUE.clear()
    _stats_calls.clear()


@pytest.fixture
def client(tmp_path):
    sandbox = types.SimpleNamespace(
        timeout=5, runtime_startup_env_vars={}, keep_runtime_alive=False
    )
    config = types.SimpleNamespace(
        sandbox=sandbox,
        mcp=MCPConfig(),
        debug=False,
        workspace_mount_path_in_sandbox="/workspace",
    )
    instance = ClientUnderTest(config, None, None)
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    instance._workspace_path = str(workspace)
    instance._vscode_enabled = True
    instance.runtime_initialized = True
    cast(Any, instance).session_api_key = "session-key"
    return instance


class ResponseStub:
    def __init__(self, data: Any, status_code: int = 200):
        self._data = data
        self.status_code = status_code
        self.is_closed = True
        self.text = json.dumps(data)

    def json(self):
        return self._data


def test_check_if_alive_success(client):
    _RESPONSE_QUEUE.append(ResponseStub({}, 200))
    client.check_if_alive()


def test_list_files_success(client):
    _RESPONSE_QUEUE.append(ResponseStub(["a", "b"]))
    assert client.list_files() == ["a", "b"]


def test_list_files_timeout(client):
    _RESPONSE_QUEUE.append(httpx.TimeoutException("timeout"))
    with pytest.raises(TimeoutError):
        client.list_files()


def test_copy_to_missing_source(client):
    with pytest.raises(FileNotFoundError):
        client.copy_to("/does/not/exist", "dest.txt")


def test_copy_to_recursive(client, tmp_path):
    src_dir = tmp_path / "src"
    src_dir.mkdir()
    file_path = src_dir / "file.txt"
    file_path.write_text("data")
    dest_dir = tmp_path / "dest"
    client._workspace_path = str(dest_dir)
    client._runtime_initialized = True
    captured: dict[str, Any] = {}

    def fake_upload(file_handle, sandbox_dest, recursive, host_src):
        captured["zip_path"] = file_handle.name
        captured["dest"] = sandbox_dest
        captured["recursive"] = recursive

    original_upload = client._upload_file_to_sandbox
    client._upload_file_to_sandbox = fake_upload  # type: ignore[assignment]
    try:
        client.copy_to(str(src_dir), "folder", recursive=True)
    finally:
        client._upload_file_to_sandbox = original_upload  # type: ignore[assignment]

    assert captured["dest"] == "folder"
    assert captured["recursive"] is True
    assert not os.path.exists(captured["zip_path"])


def test_validate_action_type_agent_level(client):
    action = AgentThinkAction("think")
    action.action = "think"
    client._validate_action_type(action)


def test_validate_action_type_missing_method(client):
    action = BaseAction("unknown")
    with pytest.raises(ValueError):
        client._validate_action_type(action)


def test_send_action_for_execution_invalid_action(client):
    action = BaseAction("unknown")
    action.timeout = 5
    action.confirmation_state = None
    result = client.send_action_for_execution(action)
    assert isinstance(result, ErrorObservation)
    assert "does not exist" in result.content


def test_send_action_for_execution_timeout(client, monkeypatch):
    action = CmdRunAction("echo hi", timeout=5)

    def raise_timeout(*args, **kwargs):
        raise httpx.TimeoutException("slow")

    monkeypatch.setattr(action_exec_module, "update_last_execution_time", lambda: None)
    monkeypatch.setattr(client, "_execute_action_on_server", raise_timeout)
    with pytest.raises(exceptions_module.AgentRuntimeTimeoutError):
        client.send_action_for_execution(action)


def test_send_action_for_execution_success(client, monkeypatch):
    action = CmdRunAction("echo hi", timeout=5)
    outputs = Observation("done")
    monkeypatch.setattr(client, "_execute_action_on_server", lambda a: outputs)
    result = client.send_action_for_execution(action)
    assert result is outputs and result.content == "done"
    assert _stats_calls


def test_null_observation_returned_when_not_runnable(client):
    action = BaseAction("run")
    action.runnable = False
    result = client.send_action_for_execution(action)
    assert isinstance(result, NullObservation)


def test_get_vscode_token_caches(client, monkeypatch):
    client._vscode_token = None
    response = ResponseStub({"token": "abc"})
    _RESPONSE_QUEUE.append(response)
    token1 = client.get_vscode_token()
    assert token1 == "abc"
    token2 = client.get_vscode_token()
    assert token2 == "abc"


def test_get_vscode_token_disabled(client):
    client._vscode_enabled = False
    assert client.get_vscode_token() == ""


def test_get_mcp_config_windows(client, monkeypatch):
    monkeypatch.setattr(sys, "platform", "win32")
    config = client.get_mcp_config()
    assert config.sse_servers == []


def test_get_mcp_config_updates(client, monkeypatch):
    monkeypatch.setattr(sys, "platform", "linux")
    client.config.mcp = MCPConfig(stdio_servers=[MCPStdioServerConfig("base")])
    extra = [MCPStdioServerConfig("extra")]
    monkeypatch.setattr(
        client, "_send_action_server_request", lambda *a, **k: ResponseStub({}, 200)
    )
    config = client.get_mcp_config(extra)
    assert any(
        server.name == "extra" for server in client._last_updated_mcp_stdio_servers
    )
    assert config.sse_servers


@pytest.mark.asyncio
async def test_call_tool_mcp_windows(client, monkeypatch):
    monkeypatch.setattr(sys, "platform", "win32")
    result = await client.call_tool_mcp(BaseAction("mcp"))
    assert isinstance(result, ErrorObservation)


def test_check_if_alive_failure(client):
    _RESPONSE_QUEUE.append(Exception("boom"))
    with pytest.raises(Exception):
        client.check_if_alive()


def teardown_module(module) -> None:
    for name, original in _ORIGINAL_MODULES.items():
        if original is None:
            sys.modules.pop(name, None)
        else:
            sys.modules[name] = original
