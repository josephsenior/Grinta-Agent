from __future__ import annotations

import importlib
import sys
import types
from pathlib import Path
from typing import Any, Callable

import pytest

ORIGINAL_MODULES: dict[str, types.ModuleType | None] = {}


def _set_stub_module(name: str, module: types.ModuleType) -> None:
    if name not in ORIGINAL_MODULES:
        ORIGINAL_MODULES[name] = sys.modules.get(name)
    sys.modules[name] = module


ROOT_DIR = Path(__file__).resolve().parents[4]


class _RuntimePackage(types.ModuleType):
    __path__: list[str]


runtime_pkg = _RuntimePackage("forge.runtime")
runtime_pkg.__path__ = [str(ROOT_DIR / "forge" / "runtime")]
_set_stub_module("forge.runtime", runtime_pkg)


class _RuntimeImplPackage(types.ModuleType):
    __path__: list[str]


impl_pkg = _RuntimeImplPackage("forge.runtime.impl")
impl_pkg.__path__ = [str(ROOT_DIR / "forge" / "runtime" / "impl")]
_set_stub_module("forge.runtime.impl", impl_pkg)


class _LocalPackage(types.ModuleType):
    __path__: list[str]


local_pkg = _LocalPackage("forge.runtime.impl.local")
local_pkg.__path__ = [str(ROOT_DIR / "forge" / "runtime" / "impl" / "local")]
_set_stub_module("forge.runtime.impl.local", local_pkg)


class _PluginsPackage(types.ModuleType):
    __path__: list[str]


plugins_pkg = _PluginsPackage("forge.runtime.plugins")
plugins_pkg.__path__ = [str(ROOT_DIR / "forge" / "runtime" / "plugins")]
_set_stub_module("forge.runtime.plugins", plugins_pkg)


class _LoggerModule(types.ModuleType):
    forge_logger: "_StubLogger"
    LOG_DIR: str


logger_module = _LoggerModule("forge.core.logger")


class _StubLogger:
    def __getattr__(self, name: str):  # pragma: no cover - simple stub
        return lambda *args, **kwargs: None


setattr(logger_module, "forge_logger", _StubLogger())
setattr(logger_module, "LOG_DIR", str(ROOT_DIR / "logs"))
_set_stub_module("forge.core.logger", logger_module)


class _ActionExecutionModule(types.ModuleType):
    ActionExecutionClient: type[ActionExecutionClient]


action_exec_module = _ActionExecutionModule(
    "forge.runtime.impl.action_execution.action_execution_client"
)


class ActionExecutionClient:
    def __init__(
        self,
        config,
        event_stream,
        llm_registry,
        sid: str = "default",
        plugins: list[object] | None = None,
        env_vars: dict[str, str] | None = None,
        status_callback: object | None = None,
        attach_to_existing: bool = False,
        headless_mode: bool = True,
        user_id: str | None = None,
        git_provider_tokens: object | None = None,
    ) -> None:
        self.config = config
        self.event_stream = event_stream
        self.llm_registry = llm_registry
        self.sid = sid
        self.plugins = list(plugins or [])
        self.env_vars = env_vars or {}
        self.status_callback = status_callback
        self.attach_to_existing = attach_to_existing
        self.headless_mode = headless_mode
        self.user_id = user_id
        self.git_provider_tokens = git_provider_tokens
        self.session = types.SimpleNamespace(
            headers={},
            get=lambda *args, **kwargs: types.SimpleNamespace(
                raise_for_status=lambda: None
            ),
            post=lambda *args, **kwargs: types.SimpleNamespace(json=lambda: {}),
        )
        self.runtime_initialized = False
        self._logs: list[tuple[str, str]] = []
        self._last_status: object | None = None

    def set_runtime_status(self, status) -> None:
        self._last_status = status

    def log(self, level: str, message: str) -> None:
        self._logs.append((level, message))

    def setup_initial_env(self) -> None:  # pragma: no cover - stub for compatibility
        return None

    def get_vscode_token(self) -> str | None:
        return "token"

    def close(self) -> None:  # pragma: no cover - stub
        self.runtime_initialized = False


setattr(action_exec_module, "ActionExecutionClient", ActionExecutionClient)
_set_stub_module(
    "forge.runtime.impl.action_execution.action_execution_client", action_exec_module
)


class _DockerRuntimeModule(types.ModuleType):
    APP_PORT_RANGE_1: tuple[int, int]
    APP_PORT_RANGE_2: tuple[int, int]
    EXECUTION_SERVER_PORT_RANGE: tuple[int, int]
    VSCODE_PORT_RANGE: tuple[int, int]


docker_runtime_module = _DockerRuntimeModule("forge.runtime.impl.docker.docker_runtime")
docker_runtime_module.APP_PORT_RANGE_1 = (7000, 7001)
docker_runtime_module.APP_PORT_RANGE_2 = (7002, 7003)
docker_runtime_module.EXECUTION_SERVER_PORT_RANGE = (8000, 8001)
docker_runtime_module.VSCODE_PORT_RANGE = (9000, 9001)
_set_stub_module("forge.runtime.impl.docker.docker_runtime", docker_runtime_module)


class _VSCodeModule(types.ModuleType):
    VSCodeRequirement: type[VSCodeRequirement]


vscode_module = _VSCodeModule("forge.runtime.plugins.vscode")


class VSCodeRequirement:
    def __init__(self) -> None:
        self.name = "vscode"


setattr(vscode_module, "VSCodeRequirement", VSCodeRequirement)
_set_stub_module("forge.runtime.plugins.vscode", vscode_module)


class _BrowserEnvModule(types.ModuleType):
    BrowserEnv: type[BrowserEnv]


browser_env_module = _BrowserEnvModule("forge.runtime.browser.browser_env")


class BrowserEnv:
    def __init__(self) -> None:
        self.closed = False

    def close(self) -> None:
        self.closed = True


setattr(browser_env_module, "BrowserEnv", BrowserEnv)
_set_stub_module("forge.runtime.browser.browser_env", browser_env_module)


class _SerializationModule(types.ModuleType):
    event_to_dict: Callable[[object], dict[str, object]]
    observation_from_dict: Callable[[object], object]


serialization_module = _SerializationModule("forge.events.serialization")
setattr(serialization_module, "event_to_dict", lambda action: {"action": action})
setattr(serialization_module, "observation_from_dict", lambda data: data)
_set_stub_module("forge.events.serialization", serialization_module)


class _LibtmuxModule(types.ModuleType):
    Server: type[Server]


libtmux_module = _LibtmuxModule("libtmux")


class _Pane:
    def __init__(self) -> None:
        self.commands: list[str] = []

    def send_keys(self, command: str) -> None:
        self.commands.append(command)

    def cmd(self, *args, **kwargs):
        return types.SimpleNamespace(stdout=["test"])


class _Session:
    def __init__(self) -> None:
        self.attached_pane = _Pane()
        self.killed = False

    def kill_session(self) -> None:
        self.killed = True


class Server:
    def new_session(self, session_name: str) -> _Session:
        return _Session()


setattr(libtmux_module, "Server", Server)
_set_stub_module("libtmux", libtmux_module)


class _AgentModule(types.ModuleType):
    Agent: type[Agent]


agent_module = _AgentModule("forge.controller.agent")


class Agent:
    sandbox_plugins = [types.SimpleNamespace(name="sandbox-plugin")]

    @classmethod
    def get_cls(cls, name: str):
        return cls


setattr(agent_module, "Agent", Agent)
_set_stub_module("forge.controller.agent", agent_module)


local_runtime = importlib.import_module("forge.runtime.impl.local.local_runtime")

ActionExecutionServerInfo = local_runtime.ActionExecutionServerInfo


def teardown_module(module) -> None:  # pragma: no cover - restore modules
    for name, original in ORIGINAL_MODULES.items():
        if original is None:
            sys.modules.pop(name, None)
        else:
            sys.modules[name] = original


@pytest.fixture
def dummy_config(tmp_path):
    sandbox = types.SimpleNamespace(
        local_runtime_url="http://localhost",
        runtime_startup_env_vars={"BOOT": "1"},
        enable_browser=False,
        workspace_mount_path_in_sandbox=None,
        browsergym_eval_env=None,
    )
    config = types.SimpleNamespace(
        sandbox=sandbox,
        workspace_base=None,
        workspace_mount_path_in_sandbox=None,
        enable_browser=False,
        default_agent="DummyAgent",
        run_as_Forge=False,
    )
    return config


@pytest.fixture(autouse=True)
def reset_globals():
    original_running = dict(local_runtime._RUNNING_SERVERS)
    original_warm = list(local_runtime._WARM_SERVERS)
    yield
    local_runtime._RUNNING_SERVERS.clear()
    local_runtime._RUNNING_SERVERS.update(original_running)
    local_runtime._WARM_SERVERS.clear()
    local_runtime._WARM_SERVERS.extend(original_warm)


def _call_sync(func, *args, **kwargs):
    async def _inner():
        return func(*args, **kwargs)

    return _inner()


def test_before_sleep_wait_until_alive(monkeypatch):
    calls: list[tuple[str, object]] = []
    monkeypatch.setattr(
        local_runtime,
        "call_tenacity_hooks",
        lambda before, after, state: calls.append((before, state)),
    )
    monkeypatch.setattr(
        local_runtime, "tenacity_before_sleep_factory", lambda label: f"factory:{label}"
    )
    retry_state = types.SimpleNamespace(attempt_number=2)
    local_runtime._before_sleep_wait_until_alive(retry_state)
    assert calls[0][0] == "factory:runtime.local.wait_until_alive"


def test_before_sleep_warm_wait(monkeypatch):
    calls: list[tuple[str, object]] = []
    monkeypatch.setattr(
        local_runtime,
        "call_tenacity_hooks",
        lambda before, after, state: calls.append((before, state)),
    )
    monkeypatch.setattr(
        local_runtime, "tenacity_before_sleep_factory", lambda label: f"factory:{label}"
    )
    retry_state = types.SimpleNamespace(attempt_number=5)
    local_runtime._before_sleep_warm_wait(retry_state)
    assert calls[0][0] == "factory:runtime.local.warm_wait"


def test_get_user_info_uses_env(monkeypatch):
    monkeypatch.setenv("USER", "alice")
    monkeypatch.delenv("USERNAME", raising=False)
    monkeypatch.setattr(local_runtime.os, "getuid", lambda: 42, raising=False)
    uid, username = local_runtime.get_user_info()
    assert uid == 42
    assert username == "alice"


def test_get_user_info_default(monkeypatch):
    monkeypatch.delenv("USER", raising=False)
    monkeypatch.setenv("USERNAME", "bob")
    monkeypatch.delattr(local_runtime.os, "getuid", raising=False)
    uid, username = local_runtime.get_user_info()
    assert uid == 1000
    assert username == "bob"


def test_check_dependencies_missing_path(monkeypatch):
    monkeypatch.setattr(local_runtime.os.path, "exists", lambda path: False)
    with pytest.raises(ValueError) as exc:
        local_runtime.check_dependencies("/missing", False)
    assert "does not exist" in str(exc.value)


def test_check_dependencies_missing_jupyter(monkeypatch):
    monkeypatch.setattr(local_runtime.os.path, "exists", lambda path: True)
    monkeypatch.setattr(
        local_runtime.subprocess, "check_output", lambda *args, **kwargs: "unrelated"
    )
    with pytest.raises(ValueError) as exc:
        local_runtime.check_dependencies("/repo", False)
    assert "Jupyter" in str(exc.value)


def test_check_dependencies_success_windows(monkeypatch):
    calls: list[str] = []
    monkeypatch.setattr(local_runtime.os.path, "exists", lambda path: True)
    monkeypatch.setattr(
        local_runtime.subprocess, "check_output", lambda *args, **kwargs: "Jupyter 1.0"
    )
    monkeypatch.setattr(local_runtime.sys, "platform", "win32")
    browser_module = sys.modules["forge.runtime.browser.browser_env"]
    monkeypatch.setattr(
        browser_module,
        "BrowserEnv",
        lambda: types.SimpleNamespace(close=lambda: calls.append("closed")),
        raising=False,
    )
    local_runtime.check_dependencies("/repo", True)
    assert calls == ["closed"]


def test_check_dependencies_success_non_windows(monkeypatch):
    monkeypatch.setattr(local_runtime.os.path, "exists", lambda path: True)
    monkeypatch.setattr(
        local_runtime.subprocess, "check_output", lambda *args, **kwargs: "Jupyter 1.0"
    )
    monkeypatch.setattr(local_runtime.sys, "platform", "linux")
    local_runtime.check_dependencies("/repo", False)


def test_check_dependencies_tmux_error(monkeypatch):
    monkeypatch.setattr(local_runtime.os.path, "exists", lambda path: True)
    monkeypatch.setattr(
        local_runtime.subprocess, "check_output", lambda *args, **kwargs: "Jupyter 1.0"
    )
    monkeypatch.setattr(local_runtime.sys, "platform", "linux")

    class FailingServer:
        def new_session(self, session_name: str):
            raise RuntimeError("no tmux")

    monkeypatch.setattr(sys.modules["libtmux"], "Server", FailingServer)
    with pytest.raises(ValueError) as exc:
        local_runtime.check_dependencies("/repo", False)
    assert "tmux" in str(exc.value)


def test_check_dependencies_tmux_output_missing(monkeypatch):
    monkeypatch.setattr(local_runtime.os.path, "exists", lambda path: True)
    monkeypatch.setattr(
        local_runtime.subprocess, "check_output", lambda *args, **kwargs: "Jupyter 1.0"
    )
    monkeypatch.setattr(local_runtime.sys, "platform", "linux")

    class BadSession:
        def __init__(self) -> None:
            self.attached_pane = types.SimpleNamespace(
                send_keys=lambda cmd: None,
                cmd=lambda *args, **kwargs: types.SimpleNamespace(stdout=["no match"]),
            )

        def kill_session(self) -> None:
            pass

    class OkServer:
        def new_session(self, session_name: str):
            return BadSession()

    monkeypatch.setattr(sys.modules["libtmux"], "Server", OkServer)
    with pytest.raises(ValueError) as exc:
        local_runtime.check_dependencies("/repo", False)
    assert "libtmux" in str(exc.value)


def _make_runtime(monkeypatch, config, sid: str = "sid"):
    monkeypatch.setattr(local_runtime.sys, "platform", "linux")
    runtime = local_runtime.LocalRuntime(
        config=config,
        event_stream=types.SimpleNamespace(),
        llm_registry=types.SimpleNamespace(),
        sid=sid,
        plugins=[types.SimpleNamespace(name="stub")],
    )
    return runtime


def test_local_runtime_init_sets_session_api_key(monkeypatch, dummy_config):
    monkeypatch.setenv("SESSION_API_KEY", "secret")
    monkeypatch.setattr(local_runtime.sys, "platform", "win32")
    dummy_config.sandbox.runtime_startup_env_vars = {"EXTRA": "1"}
    runtime = local_runtime.LocalRuntime(
        config=dummy_config,
        event_stream=types.SimpleNamespace(),
        llm_registry=types.SimpleNamespace(),
        plugins=[types.SimpleNamespace(name="stub")],
    )
    assert runtime.is_windows is True
    assert runtime.session.headers["X-Session-API-Key"] == "secret"
    assert runtime._session_api_key == "secret"
    assert runtime.session_api_key == "secret"


def test_setup_workspace_directory_temp(monkeypatch, dummy_config):
    runtime = _make_runtime(monkeypatch, dummy_config)
    dummy_config.workspace_base = None
    monkeypatch.setattr(
        local_runtime.tempfile, "mkdtemp", lambda prefix: "/tmp/workspace"
    )
    runtime._setup_workspace_directory()
    assert runtime._temp_workspace == "/tmp/workspace"
    assert dummy_config.workspace_mount_path_in_sandbox == "/tmp/workspace"


def test_setup_workspace_directory_base(monkeypatch, dummy_config):
    dummy_config.workspace_base = "/custom"
    runtime = _make_runtime(monkeypatch, dummy_config)
    runtime._setup_workspace_directory()
    assert runtime._temp_workspace is None
    assert dummy_config.workspace_mount_path_in_sandbox == "/custom"


def _make_process(alive: bool = True):
    class Proc:
        def __init__(self) -> None:
            self.alive = alive
            self.stdout_lines = ["line"]
            self.stdout = types.SimpleNamespace(
                readline=lambda: self.stdout_lines.pop(0) if self.stdout_lines else "",
                __iter__=lambda self: iter([]),
            )

        def poll(self):
            return None if self.alive else 0

        def terminate(self):
            self.alive = False

        def wait(self, timeout=None):
            self.alive = False
            return 0

        def kill(self):
            self.alive = False

    return Proc()


def _make_server_info():
    return ActionExecutionServerInfo(
        process=_make_process(),
        execution_server_port=8100,
        vscode_port=8200,
        app_ports=[8300, 8301],
        log_thread=types.SimpleNamespace(join=lambda timeout=None: None),
        log_thread_exit_event=local_runtime.threading.Event(),
        temp_workspace=None,
        workspace_mount_path="/mount",
    )


def test_use_warm_server_success(monkeypatch, dummy_config):
    runtime = _make_runtime(monkeypatch, dummy_config, sid="session1")
    server_info = _make_server_info()
    local_runtime._WARM_SERVERS[:] = [server_info]
    runtime._temp_workspace = None
    used = runtime._use_warm_server()
    assert used is True
    assert "session1" in local_runtime._RUNNING_SERVERS


def test_use_warm_server_creates_workspace(monkeypatch, dummy_config):
    runtime = _make_runtime(monkeypatch, dummy_config, sid="warm")
    server_info = _make_server_info()
    server_info.temp_workspace = "/tmp/old"
    local_runtime._WARM_SERVERS[:] = [server_info]
    runtime._temp_workspace = None
    dummy_config.workspace_base = None
    removed: list[str] = []
    monkeypatch.setattr(
        local_runtime.shutil, "rmtree", lambda path: removed.append(path)
    )
    monkeypatch.setattr(local_runtime.tempfile, "mkdtemp", lambda prefix: "/tmp/new")
    assert runtime._use_warm_server() is True
    assert removed == ["/tmp/old"]
    assert runtime._temp_workspace == "/tmp/new"


def test_use_warm_server_empty(monkeypatch, dummy_config):
    runtime = _make_runtime(monkeypatch, dummy_config)
    local_runtime._WARM_SERVERS.clear()
    assert runtime._use_warm_server() is False


def test_create_new_server(monkeypatch, dummy_config):
    runtime = _make_runtime(monkeypatch, dummy_config, sid="s1")
    server_info = _make_server_info()
    monkeypatch.setattr(
        local_runtime, "_create_server", lambda **kwargs: (server_info, "http://api")
    )
    runtime._create_new_server()
    assert local_runtime._RUNNING_SERVERS["s1"].execution_server_port == 8100
    assert runtime.api_url == "http://api"


def test_create_new_server_removes_temp(monkeypatch, dummy_config):
    runtime = _make_runtime(monkeypatch, dummy_config, sid="s2")
    server_info = _make_server_info()
    server_info.temp_workspace = "/tmp/cleanup"
    runtime._temp_workspace = "/tmp/current"
    calls: list[str] = []
    monkeypatch.setattr(
        local_runtime, "_create_server", lambda **kwargs: (server_info, "http://api")
    )
    monkeypatch.setattr(local_runtime.shutil, "rmtree", lambda path: calls.append(path))
    runtime._create_new_server()
    assert calls == ["/tmp/cleanup"]


def test_create_additional_warm_servers(monkeypatch, dummy_config):
    runtime = _make_runtime(monkeypatch, dummy_config)
    created: list[int] = []
    monkeypatch.setattr(
        local_runtime,
        "_create_warm_server_in_background",
        lambda config, plugins: created.append(1),
    )
    runtime._create_additional_warm_servers(2)
    assert created == [1, 1]


def test_wait_until_alive_success(monkeypatch, dummy_config):
    runtime = _make_runtime(monkeypatch, dummy_config)
    runtime.server_process = _make_process()

    def fake_get(url):
        return types.SimpleNamespace(raise_for_status=lambda: None)

    runtime.session = types.SimpleNamespace(get=fake_get)
    assert runtime._wait_until_alive() is True


def test_wait_until_alive_process_died(monkeypatch, dummy_config):
    runtime = _make_runtime(monkeypatch, dummy_config)
    process = _make_process(alive=False)
    runtime.server_process = process
    with pytest.raises(RuntimeError):
        local_runtime.LocalRuntime._wait_until_alive.__wrapped__(runtime)


def test_runtime_url_patterns(monkeypatch, dummy_config):
    runtime = _make_runtime(monkeypatch, dummy_config)
    monkeypatch.setenv("RUNTIME_URL", "http://localhost:9999")
    assert runtime.runtime_url == "http://localhost:9999"
    monkeypatch.delenv("RUNTIME_URL", raising=False)
    monkeypatch.setenv("RUNTIME_URL_PATTERN", "https://example.com/{runtime_id}")
    monkeypatch.setenv("RUNTIME_ID", "abc")
    assert runtime.runtime_url == "https://example.com/abc"


def test_create_url_variants(monkeypatch, dummy_config):
    runtime = _make_runtime(monkeypatch, dummy_config)
    monkeypatch.setenv("RUNTIME_URL", "http://localhost:8000")
    runtime._vscode_port = 8501
    assert runtime._create_url("vscode", 1234) == "http://localhost:8000:8501"
    monkeypatch.setenv("RUNTIME_URL", "http://api.example.com/rt-1")
    monkeypatch.setenv("RUNTIME_ID", "rt-1")
    assert runtime._create_url("vscode", 9999) == "http://api.example.com/rt-1/vscode"
    monkeypatch.setenv("RUNTIME_URL", "http://api.example.com")
    monkeypatch.setenv("RUNTIME_ID", "rt-1")
    assert runtime._create_url("vscode", 9999) == "http://vscode-api.example.com"


def test_vscode_url(monkeypatch, dummy_config):
    runtime = _make_runtime(monkeypatch, dummy_config)
    runtime._vscode_port = 8500
    dummy_config.sandbox.workspace_mount_path_in_sandbox = "/workspace"
    url = runtime.vscode_url
    assert url and url.startswith("http://") and "tkn=" in url


def test_web_hosts(dummy_config, monkeypatch):
    runtime = _make_runtime(monkeypatch, dummy_config)
    runtime._app_ports = [7000, 7001]
    monkeypatch.setenv("RUNTIME_URL", "http://api.example.com/base")
    monkeypatch.setenv("RUNTIME_ID", "base")
    hosts = runtime.web_hosts
    assert len(hosts) == 2


def test_python_bin_path():
    assert Path(local_runtime._python_bin_path()).exists()


def test_create_server(monkeypatch, dummy_config):
    ports = [8100, 8200, 8300, 8301]
    monkeypatch.setattr(
        local_runtime, "find_available_tcp_port", lambda start, end: ports.pop(0)
    )
    monkeypatch.setattr(
        local_runtime,
        "get_action_execution_server_startup_command",
        lambda **kwargs: ["python", "-m", "server"],
    )
    monkeypatch.setattr(local_runtime.tempfile, "mkdtemp", lambda prefix: "/tmp/ws")
    popen_calls = {}

    class FakePopen:
        def __init__(
            self, cmd, stdout, stderr, universal_newlines, bufsize, env, cwd
        ) -> None:
            popen_calls.update({"cmd": cmd, "env": env, "cwd": cwd})
            self._process = _make_process()
            self.stdout = self._process.stdout

        def poll(self):
            return None

    monkeypatch.setattr(local_runtime.subprocess, "Popen", FakePopen)
    started_threads: list[Callable[[], None]] = []

    class FakeThread:
        def __init__(self, target, daemon):
            self.target = target
            started_threads.append(target)

        def start(self):
            self.target()

        def join(self, timeout=None):
            pass

    monkeypatch.setattr(local_runtime.threading, "Thread", FakeThread)
    server_info, api_url = local_runtime._create_server(
        dummy_config, [types.SimpleNamespace(name="p")], "pref"
    )
    assert server_info.execution_server_port == 8100
    assert api_url.endswith(":8100")
    assert popen_calls["env"]["LOCAL_RUNTIME_MODE"] == "1"


def test_create_warm_server_success(monkeypatch, dummy_config):
    server_info = _make_server_info()
    monkeypatch.setattr(
        local_runtime, "_create_server", lambda **kwargs: (server_info, "http://api")
    )

    class FakeResponse:
        def raise_for_status(self):
            return None

    class FakeClient:
        def __init__(self, timeout):
            self.timeout = timeout

        def get(self, url):
            return FakeResponse()

    monkeypatch.setattr(local_runtime.httpx, "Client", FakeClient)
    local_runtime._create_warm_server(dummy_config, [])
    assert server_info in local_runtime._WARM_SERVERS


def test_create_warm_server_error(monkeypatch, dummy_config):
    called: list[int] = []

    def raise_create(**kwargs):
        called.append(1)
        raise RuntimeError("fail")

    monkeypatch.setattr(local_runtime, "_create_server", raise_create)
    local_runtime._create_warm_server(dummy_config, [])
    assert called == [1]


def test_create_warm_server_in_background(monkeypatch, dummy_config):
    captured: dict[str, object] = {}

    class FakeThread:
        def __init__(self, target, daemon, args):
            captured["target"] = target
            captured["args"] = args

        def start(self):
            captured["started"] = True

    monkeypatch.setattr(local_runtime.threading, "Thread", FakeThread)
    local_runtime._create_warm_server_in_background(dummy_config, [])
    assert captured.get("started") is True


def test_get_plugins():
    plugins = local_runtime._get_plugins(types.SimpleNamespace(default_agent="any"))
    assert plugins[0].name == "sandbox-plugin"


def test_setup_invokes_dependencies(monkeypatch, dummy_config):
    dummy_config.enable_browser = True
    called: dict[str, int] = {"deps": 0, "warm": 0}
    monkeypatch.setattr(
        local_runtime,
        "check_dependencies",
        lambda path, check: called.__setitem__("deps", called["deps"] + 1),
    )
    monkeypatch.setattr(
        local_runtime,
        "_create_warm_server",
        lambda config, plugins: called.__setitem__("warm", called["warm"] + 1),
    )
    monkeypatch.setenv("INITIAL_NUM_WARM_SERVERS", "2")
    local_runtime.LocalRuntime.setup(dummy_config, headless_mode=False)
    assert called["deps"] == 1
    assert called["warm"] == 2


@pytest.mark.asyncio
async def test_connect_attach_to_existing_error(monkeypatch, dummy_config):
    runtime = _make_runtime(monkeypatch, dummy_config, sid="missing")
    runtime.attach_to_existing = True
    monkeypatch.setattr(local_runtime, "call_sync_from_async", _call_sync)
    with pytest.raises(local_runtime.AgentRuntimeDisconnectedError):
        await runtime.connect()


@pytest.mark.asyncio
async def test_connect_starts_server(monkeypatch, dummy_config):
    runtime = _make_runtime(monkeypatch, dummy_config, sid="s1")
    monkeypatch.setattr(local_runtime, "call_sync_from_async", _call_sync)
    monkeypatch.setattr(
        runtime,
        "_setup_workspace_directory",
        lambda: setattr(runtime, "workspace_prepared", True),
    )
    monkeypatch.setattr(runtime, "_use_warm_server", lambda: False)
    server_info = _make_server_info()
    monkeypatch.setattr(
        local_runtime,
        "_create_server",
        lambda **kwargs: (server_info, "http://api:8001"),
    )
    monkeypatch.setattr(runtime, "_wait_until_alive", lambda: True)
    monkeypatch.setattr(runtime, "setup_initial_env", lambda: None)
    runtime.session = types.SimpleNamespace(
        get=lambda url: types.SimpleNamespace(raise_for_status=lambda: None)
    )
    monkeypatch.setattr(local_runtime.shutil, "rmtree", lambda path: None)
    await runtime.connect()
    assert runtime._runtime_initialized is True
    assert runtime.api_url == "http://api:8001"


@pytest.mark.asyncio
async def test_connect_uses_warm_server(monkeypatch, dummy_config):
    runtime = _make_runtime(monkeypatch, dummy_config, sid="warm-flag")
    monkeypatch.setattr(local_runtime, "call_sync_from_async", _call_sync)
    monkeypatch.setattr(runtime, "_setup_workspace_directory", lambda: None)
    monkeypatch.setattr(runtime, "_use_warm_server", lambda: True)
    monkeypatch.setattr(runtime, "_wait_until_alive", lambda: True)
    monkeypatch.setattr(runtime, "setup_initial_env", lambda: None)
    runtime.session = types.SimpleNamespace(
        get=lambda url: types.SimpleNamespace(raise_for_status=lambda: None)
    )
    await runtime.connect()
    assert runtime._runtime_initialized is True


@pytest.mark.asyncio
async def test_connect_uses_existing(monkeypatch, dummy_config):
    runtime = _make_runtime(monkeypatch, dummy_config, sid="existing")
    monkeypatch.setattr(local_runtime, "call_sync_from_async", _call_sync)
    server_info = _make_server_info()
    local_runtime._RUNNING_SERVERS["existing"] = server_info
    await runtime.connect()
    assert runtime.server_process is server_info.process


@pytest.mark.asyncio
async def test_execute_action_success(monkeypatch, dummy_config):
    runtime = _make_runtime(monkeypatch, dummy_config)
    runtime.runtime_initialized = True
    runtime.server_process = _make_process()
    monkeypatch.setattr(local_runtime, "call_sync_from_async", _call_sync)
    runtime.session = types.SimpleNamespace(
        post=lambda *args, **kwargs: types.SimpleNamespace(json=lambda: {"ok": 1})
    )
    result = await runtime.execute_action(types.SimpleNamespace())
    assert result == {"ok": 1}


@pytest.mark.asyncio
async def test_execute_action_server_dead(monkeypatch, dummy_config):
    runtime = _make_runtime(monkeypatch, dummy_config)
    runtime.runtime_initialized = True
    dead_process = _make_process(alive=False)
    runtime.server_process = dead_process
    with pytest.raises(local_runtime.AgentRuntimeDisconnectedError):
        await runtime.execute_action(types.SimpleNamespace())


@pytest.mark.asyncio
async def test_execute_action_not_initialized(monkeypatch, dummy_config):
    runtime = _make_runtime(monkeypatch, dummy_config)
    with pytest.raises(local_runtime.AgentRuntimeDisconnectedError):
        await runtime.execute_action(types.SimpleNamespace())


@pytest.mark.asyncio
async def test_execute_action_fetches_existing_process(monkeypatch, dummy_config):
    runtime = _make_runtime(monkeypatch, dummy_config, sid="reuse")
    runtime.runtime_initialized = True
    runtime.server_process = None
    local_runtime._RUNNING_SERVERS["reuse"] = _make_server_info()
    monkeypatch.setattr(local_runtime, "call_sync_from_async", _call_sync)
    runtime.session = types.SimpleNamespace(
        post=lambda *args, **kwargs: types.SimpleNamespace(json=lambda: {})
    )
    result = await runtime.execute_action(types.SimpleNamespace())
    assert result == {}


@pytest.mark.asyncio
async def test_execute_action_process_died_removes_entry(monkeypatch, dummy_config):
    runtime = _make_runtime(monkeypatch, dummy_config, sid="dead")
    runtime.runtime_initialized = True
    runtime.server_process = _make_process(alive=False)
    local_runtime._RUNNING_SERVERS["dead"] = _make_server_info()
    with pytest.raises(local_runtime.AgentRuntimeDisconnectedError):
        await runtime.execute_action(types.SimpleNamespace())
    assert "dead" not in local_runtime._RUNNING_SERVERS


@pytest.mark.asyncio
async def test_execute_action_triggers_warm_server(monkeypatch, dummy_config):
    runtime = _make_runtime(monkeypatch, dummy_config)
    runtime.runtime_initialized = True
    runtime.server_process = _make_process()
    monkeypatch.setattr(local_runtime, "call_sync_from_async", _call_sync)
    runtime.session = types.SimpleNamespace(
        post=lambda *args, **kwargs: types.SimpleNamespace(json=lambda: {})
    )
    local_runtime._WARM_SERVERS.clear()
    monkeypatch.setenv("DESIRED_NUM_WARM_SERVERS", "1")
    created: list[int] = []
    monkeypatch.setattr(
        local_runtime,
        "_create_warm_server_in_background",
        lambda config, plugins: created.append(1),
    )
    await runtime.execute_action(types.SimpleNamespace())
    assert created == [1]


@pytest.mark.asyncio
async def test_execute_action_network_error(monkeypatch, dummy_config):
    runtime = _make_runtime(monkeypatch, dummy_config)
    runtime.runtime_initialized = True
    runtime.server_process = _make_process()
    monkeypatch.setattr(local_runtime, "call_sync_from_async", _call_sync)

    class NetworkError(Exception):
        pass

    monkeypatch.setattr(
        local_runtime.httpx, "NetworkError", NetworkError, raising=False
    )
    runtime.session = types.SimpleNamespace(
        post=lambda *args, **kwargs: (_ for _ in ()).throw(NetworkError("lost"))
    )
    with pytest.raises(local_runtime.AgentRuntimeDisconnectedError):
        await runtime.execute_action(types.SimpleNamespace())


def test_close_terminates(monkeypatch, dummy_config):
    runtime = _make_runtime(monkeypatch, dummy_config, sid="close")
    runtime.attach_to_existing = False
    process = _make_process()
    runtime.server_process = process
    runtime._log_thread = types.SimpleNamespace(join=lambda timeout=None: None)
    runtime._log_thread_exit_event = local_runtime.threading.Event()
    runtime._temp_workspace = "/tmp/temp"
    local_runtime._RUNNING_SERVERS["close"] = _make_server_info()
    monkeypatch.setattr(local_runtime.shutil, "rmtree", lambda path: None)
    runtime.close()
    assert "close" not in local_runtime._RUNNING_SERVERS
    assert runtime.server_process is None


def test_close_attach(monkeypatch, dummy_config):
    runtime = _make_runtime(monkeypatch, dummy_config)
    runtime.attach_to_existing = True
    runtime.server_process = _make_process()
    runtime._log_thread = types.SimpleNamespace(join=lambda timeout=None: None)
    runtime._log_thread_exit_event = local_runtime.threading.Event()
    runtime.close()
    assert runtime.server_process is None


@pytest.mark.asyncio
async def test_delete_cleans_servers(monkeypatch, dummy_config):
    server_info = _make_server_info()
    local_runtime._RUNNING_SERVERS["conv"] = server_info
    local_runtime._WARM_SERVERS.append(_make_server_info())
    monkeypatch.setattr(local_runtime.shutil, "rmtree", lambda path: None)
    await local_runtime.LocalRuntime.delete("conv")
    assert "conv" not in local_runtime._RUNNING_SERVERS
    assert local_runtime._WARM_SERVERS == []


@pytest.mark.asyncio
async def test_delete_cleans_temp_dirs(monkeypatch, dummy_config):
    run_info = _make_server_info()
    run_info.temp_workspace = "/tmp/run-delete"
    run_info.process = _make_process()
    warm_info = _make_server_info()
    warm_info.temp_workspace = "/tmp/warm-delete"
    warm_info.process = _make_process()
    local_runtime._RUNNING_SERVERS["conv2"] = run_info
    local_runtime._WARM_SERVERS[:] = [warm_info]
    removed: list[str] = []
    monkeypatch.setattr(
        local_runtime.shutil, "rmtree", lambda path: removed.append(path)
    )
    await local_runtime.LocalRuntime.delete("conv2")
    assert "/tmp/run-delete" in removed or "/tmp/warm-delete" in removed


def test_vscode_url_no_token(monkeypatch, dummy_config):
    runtime = _make_runtime(monkeypatch, dummy_config)
    monkeypatch.setattr(ActionExecutionClient, "get_vscode_token", lambda self: None)
    assert runtime.vscode_url is None


def test_create_server_missing_stdout(monkeypatch, dummy_config):
    ports = [8100, 8200, 8300, 8301]
    monkeypatch.setattr(
        local_runtime, "find_available_tcp_port", lambda start, end: ports.pop(0)
    )
    monkeypatch.setattr(local_runtime.tempfile, "mkdtemp", lambda prefix: "/tmp/ws-x")

    class NoStdoutProcess:
        def __init__(
            self, cmd, stdout, stderr, universal_newlines, bufsize, env, cwd
        ) -> None:
            self.stdout = None

        def poll(self):
            return 0

    monkeypatch.setattr(local_runtime.subprocess, "Popen", NoStdoutProcess)

    started: list[Callable[[], None]] = []

    class FakeThread:
        def __init__(self, target, daemon):
            started.append(target)

        def start(self):
            started[0]()

        def join(self, timeout=None):
            pass

    monkeypatch.setattr(local_runtime.threading, "Thread", FakeThread)
    server_info, _ = local_runtime._create_server(dummy_config, [], "pref")
    assert server_info.process.poll() == 0


def test_close_wait_timeout(monkeypatch, dummy_config):
    runtime = _make_runtime(monkeypatch, dummy_config, sid="timeout")
    runtime.attach_to_existing = False

    class SlowProcess:
        def terminate(self):
            pass

        def wait(self, timeout=None):
            raise local_runtime.subprocess.TimeoutExpired(cmd="cmd", timeout=timeout)

        def kill(self):
            pass

        def poll(self):
            return None

        stdout = types.SimpleNamespace()

    runtime.server_process = SlowProcess()
    runtime._log_thread = types.SimpleNamespace(join=lambda timeout=None: None)
    runtime._log_thread_exit_event = local_runtime.threading.Event()
    runtime._temp_workspace = None
    monkeypatch.setattr(local_runtime.shutil, "rmtree", lambda path: None)
    runtime.close()
    assert runtime.server_process is None
