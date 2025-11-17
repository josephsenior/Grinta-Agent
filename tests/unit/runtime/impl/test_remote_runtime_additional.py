from __future__ import annotations

import importlib
import json
import sys
import types
from pathlib import Path
from typing import Any
import importlib.machinery as machinery

import httpx
import pytest


def _ensure_module(name: str, module: types.ModuleType) -> None:
    sys.modules.setdefault(name, module)


ROOT_DIR = Path(__file__).resolve().parents[4]

runtime_pkg = types.ModuleType("forge.runtime")
runtime_pkg.__path__ = [str(ROOT_DIR / "forge" / "runtime")]
_ensure_module("forge.runtime", runtime_pkg)

impl_pkg = types.ModuleType("forge.runtime.impl")
impl_pkg.__path__ = [str(ROOT_DIR / "forge" / "runtime" / "impl")]
_ensure_module("forge.runtime.impl", impl_pkg)

plugins_pkg = types.ModuleType("forge.runtime.plugins")
plugins_pkg.__path__ = [str(ROOT_DIR / "forge" / "runtime" / "plugins")]
_ensure_module("forge.runtime.plugins", plugins_pkg)

logger_module = types.ModuleType("forge.core.logger")


class _StubLogger:
    def __getattr__(self, name: str):
        return lambda *args, **kwargs: None


setattr(logger_module, "forge_logger", _StubLogger())
setattr(logger_module, "LOG_DIR", "/tmp")
_ensure_module("forge.core.logger", logger_module)


# Ensure remote builder package exists before importing RemoteRuntime
builder_pkg = types.ModuleType("forge.runtime.builder")
builder_pkg.__path__ = []
setattr(builder_pkg, "DockerRuntimeBuilder", type("DockerRuntimeBuilder", (), {}))
setattr(builder_pkg, "RuntimeBuilder", type("RuntimeBuilder", (), {}))
sys.modules["forge.runtime.builder"] = builder_pkg

remote_builder_module = types.ModuleType("forge.runtime.builder.remote")


class RemoteRuntimeBuilderStub:
    def __init__(self, api_url: str, api_key: str, session: object) -> None:
        self.api_url = api_url
        self.api_key = api_key
        self.session = session


setattr(remote_builder_module, "RemoteRuntimeBuilder", RemoteRuntimeBuilderStub)
sys.modules["forge.runtime.builder.remote"] = remote_builder_module

utils_pkg = types.ModuleType("forge.runtime.utils")
utils_pkg.__path__ = []
sys.modules["forge.runtime.utils"] = utils_pkg

runtime_build_module = types.ModuleType("forge.runtime.utils.runtime_build")
setattr(
    runtime_build_module, "build_runtime_image", lambda *args, **kwargs: "built:image"
)
sys.modules["forge.runtime.utils.runtime_build"] = runtime_build_module

impl_action_pkg = types.ModuleType("forge.runtime.impl.action_execution")
impl_action_pkg.__path__ = []
sys.modules["forge.runtime.impl.action_execution"] = impl_action_pkg

action_exec_module = types.ModuleType(
    "forge.runtime.impl.action_execution.action_execution_client"
)


class ActionExecutionClientStub:
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
            get=lambda *a, **k: types.SimpleNamespace(raise_for_status=lambda: None),
        )
        self._runtime_closed = False
        self._last_status = None

    def set_runtime_status(self, status) -> None:
        self._last_status = status

    def log(self, level: str, message: str, exc_info: bool | None = None) -> None:
        pass

    def setup_initial_env(self) -> None:
        return None

    def get_vscode_token(self) -> str | None:
        return "token"

    def close(self) -> None:
        self._runtime_closed = True

    def check_if_alive(self) -> None:
        return None

    def _send_action_server_request(
        self, method: str, url: str, **kwargs
    ):  # pragma: no cover - patched later
        raise NotImplementedError


setattr(action_exec_module, "ActionExecutionClient", ActionExecutionClientStub)
sys.modules["forge.runtime.impl.action_execution.action_execution_client"] = (
    action_exec_module
)


class _CommandModule(types.ModuleType):
    DEFAULT_MAIN_MODULE: str

    def get_action_execution_server_startup_command(
        self,
        *,
        server_port: int,
        plugins: list,
        app_config: object,
        python_prefix: list | None = None,
        python_executable: str = "python",
        override_user_id: int | None = None,
        override_username: str | None = None,
        main_module: str = "forge.runtime.action_execution_server",
    ) -> list[str]:
        return [python_executable, main_module, f"--port={server_port}"]


command_module = _CommandModule("forge.runtime.utils.command")
command_module.DEFAULT_MAIN_MODULE = "forge.runtime.action_execution_server"


def _get_action_execution_server_startup_command(
    *,
    server_port: int,
    plugins: list,
    app_config: object,
    python_prefix: list | None = None,
    python_executable: str = "python",
    override_user_id: int | None = None,
    override_username: str | None = None,
    main_module: str = "forge.runtime.action_execution_server",
) -> list[str]:
    return [python_executable, main_module, f"--port={server_port}"]


command_module.get_action_execution_server_startup_command = (
    _get_action_execution_server_startup_command  # type: ignore[assignment]
)
sys.modules["forge.runtime.utils.command"] = command_module

events_pkg = types.ModuleType("forge.events")
events_pkg.__package__ = "forge"
events_pkg.__path__ = []
events_pkg.__spec__ = machinery.ModuleSpec("forge.events", loader=None, is_package=True)
events_pkg.__spec__.submodule_search_locations = []
sys.modules["forge.events"] = events_pkg

action_module = types.ModuleType("forge.events.action")
action_module.__package__ = "forge.events"
action_module.__spec__ = machinery.ModuleSpec("forge.events.action", loader=None)


class _BaseAction:
    def __init__(self, *args, **kwargs):
        pass


setattr(
    action_module, "ActionConfirmationStatus", type("ActionConfirmationStatus", (), {})
)
setattr(action_module, "AgentThinkAction", _BaseAction)
setattr(action_module, "BrowseInteractiveAction", _BaseAction)
setattr(action_module, "BrowseURLAction", _BaseAction)
setattr(action_module, "CmdRunAction", _BaseAction)
setattr(action_module, "FileEditAction", _BaseAction)
setattr(action_module, "FileReadAction", _BaseAction)
setattr(action_module, "FileWriteAction", _BaseAction)
setattr(action_module, "IPythonRunCellAction", _BaseAction)
sys.modules["forge.events.action"] = action_module

observation_module = types.ModuleType("forge.events.observation")
observation_module.__package__ = "forge.events"
observation_module.__spec__ = machinery.ModuleSpec(
    "forge.events.observation", loader=None
)
setattr(observation_module, "Observation", object)
setattr(observation_module, "ErrorObservation", object)
setattr(observation_module, "AgentThinkObservation", object)
setattr(observation_module, "NullObservation", object)
setattr(observation_module, "UserRejectObservation", object)
sys.modules["forge.events.observation"] = observation_module

serialization_module = types.ModuleType("forge.events.serialization")
serialization_module.__package__ = "forge.events"
serialization_module.__spec__ = machinery.ModuleSpec(
    "forge.events.serialization", loader=None
)
setattr(serialization_module, "event_to_dict", lambda action: {"action": action})
setattr(serialization_module, "observation_from_dict", lambda data: data)
sys.modules["forge.events.serialization"] = serialization_module

serialization_action_module = types.ModuleType("forge.events.serialization.action")
serialization_action_module.__package__ = "forge.events.serialization"
serialization_action_module.__spec__ = machinery.ModuleSpec(
    "forge.events.serialization.action", loader=None
)
setattr(serialization_action_module, "ACTION_TYPE_TO_CLASS", {})
sys.modules["forge.events.serialization.action"] = serialization_action_module

event_module = types.ModuleType("forge.events.event")
event_module.__package__ = "forge.events"
event_module.__spec__ = machinery.ModuleSpec("forge.events.event", loader=None)
setattr(event_module, "Event", object)
setattr(event_module, "EventSource", type("EventSource", (), {}))
setattr(event_module, "RecallType", type("RecallType", (), {}))
sys.modules["forge.events.event"] = event_module

tool_module = types.ModuleType("forge.events.tool")
tool_module.__package__ = "forge.events"
tool_module.__spec__ = machinery.ModuleSpec("forge.events.tool", loader=None)
setattr(tool_module, "ToolCallMetadata", type("ToolCallMetadata", (), {}))
sys.modules["forge.events.tool"] = tool_module

litellm_module = types.ModuleType("litellm")
setattr(litellm_module, "ModelResponse", type("ModelResponse", (), {}))
setattr(
    litellm_module, "ChatCompletionToolParam", type("ChatCompletionToolParam", (), {})
)
sys.modules["litellm"] = litellm_module

request_module = types.ModuleType("forge.runtime.utils.request")


def _send_request(*_args, **_kwargs):
    class _FakeResponse:
        status_code = 200

        @staticmethod
        def json():
            return {}

    return _FakeResponse()


setattr(request_module, "send_request", _send_request)
sys.modules["forge.runtime.utils.request"] = request_module

remote_runtime = importlib.import_module("forge.runtime.impl.remote.remote_runtime")
action_module = sys.modules[
    "forge.runtime.impl.action_execution.action_execution_client"
]
ActionExecutionClient = action_module.ActionExecutionClient


_original_init = ActionExecutionClient.__init__


def _patched_init(self, *args, **kwargs):
    _original_init(self, *args, **kwargs)
    self._runtime_closed = False


ActionExecutionClient.__init__ = _patched_init


if not hasattr(ActionExecutionClient, "check_if_alive"):
    ActionExecutionClient.check_if_alive = lambda self: None


def _base_close(self):
    self._runtime_closed = True


ActionExecutionClient.close = _base_close


def _base_send_action_request(self, method: str, url: str, **kwargs):
    return remote_runtime.send_request(self.session, method, url, **kwargs)


ActionExecutionClient._send_action_server_request = _base_send_action_request


class SendSequence:
    def __init__(self, responses):
        self.responses = list(responses)
        self.calls: list[tuple[str, str, dict]] = []

    def __call__(self, session, method: str, url: str, **kwargs):
        self.calls.append((method, url, kwargs))
        if not self.responses:
            raise AssertionError("No responses configured for send_request")
        result = self.responses.pop(0)
        if isinstance(result, Exception):
            raise result
        return result


def clone_config(config):
    sandbox = types.SimpleNamespace(**config.sandbox.__dict__)
    cfg = types.SimpleNamespace(**config.__dict__)
    cfg.sandbox = sandbox
    return cfg


@pytest.fixture
def dummy_config():
    sandbox = types.SimpleNamespace(
        api_key="key",
        remote_runtime_api_url="https://api.example.com",
        remote_runtime_class=None,
        runtime_container_image=None,
        base_container_image="base:image",
        runtime_extra_deps=[],
        platform="linux/amd64",
        force_rebuild_runtime=False,
        runtime_startup_env_vars={"ENV": "1"},
        remote_runtime_resource_factor=1.0,
        keep_runtime_alive=False,
        pause_closed_runtimes=False,
        remote_runtime_init_timeout=1,
        remote_runtime_api_timeout=5,
        remote_runtime_enable_retries=False,
    )
    return types.SimpleNamespace(
        sandbox=sandbox,
        workspace_base=None,
        workspace_mount_path_in_sandbox="/workspace",
        enable_browser=False,
        default_agent="DummyAgent",
        debug=False,
    )


@pytest.fixture
def runtime(monkeypatch, dummy_config):
    monkeypatch.setattr(
        remote_runtime, "RemoteRuntimeBuilder", RemoteRuntimeBuilderStub
    )
    monkeypatch.setattr(
        remote_runtime, "build_runtime_image", lambda *args, **kwargs: "built:image"
    )
    monkeypatch.setattr(
        remote_runtime,
        "call_sync_from_async",
        lambda func, *args, **kwargs: func(*args, **kwargs),
    )
    cfg = clone_config(dummy_config)
    rt = remote_runtime.RemoteRuntime(
        cfg, types.SimpleNamespace(), types.SimpleNamespace()
    )
    rt.runtime_url = "https://runtime.example.com/rt"
    rt.runtime_id = "rt"
    rt.container_image = "built:image"
    rt.available_hosts = {}
    return rt


def make_response(status: int, data: dict) -> httpx.Response:
    return httpx.Response(status_code=status, json=data)


def make_http_error(
    status: int, method: str = "GET", url: str = "https://runtime"
) -> httpx.HTTPStatusError:
    response = httpx.Response(status_code=status, json={})
    request = httpx.Request(method, url)
    return httpx.HTTPStatusError("error", request=request, response=response)


def test_init_requires_api_key(dummy_config):
    cfg = clone_config(dummy_config)
    cfg.sandbox.api_key = None
    with pytest.raises(ValueError):
        remote_runtime.RemoteRuntime(
            cfg, types.SimpleNamespace(), types.SimpleNamespace()
        )


def test_check_existing_runtime_running(monkeypatch, runtime):
    response = make_response(
        200,
        {
            "status": "running",
            "runtime_id": "rt-1",
            "url": "http://r",
            "work_hosts": {"a": 1},
        },
    )
    monkeypatch.setattr(
        runtime, "_send_runtime_api_request", lambda *args, **kwargs: response
    )
    assert runtime._check_existing_runtime() is True
    assert runtime.runtime_id == "rt-1"
    assert runtime.available_hosts == {"a": 1}


def test_check_existing_runtime_stopped(monkeypatch, runtime):
    response = make_response(200, {"status": "stopped"})
    monkeypatch.setattr(
        runtime, "_send_runtime_api_request", lambda *args, **kwargs: response
    )
    assert runtime._check_existing_runtime() is False


def test_check_existing_runtime_paused_resume_failure(monkeypatch, runtime):
    response = make_response(
        200,
        {
            "status": "paused",
            "runtime_id": "rt",
            "url": "https://runtime",
            "work_hosts": {},
        },
    )
    monkeypatch.setattr(
        runtime, "_send_runtime_api_request", lambda *args, **kwargs: response
    )
    monkeypatch.setattr(
        runtime,
        "_resume_runtime",
        lambda: (_ for _ in ()).throw(RuntimeError("resume")),
    )
    assert runtime._check_existing_runtime() is False


def test_check_existing_runtime_invalid_status(monkeypatch, runtime):
    response = make_response(200, {"status": "mystery"})
    monkeypatch.setattr(
        runtime, "_send_runtime_api_request", lambda *args, **kwargs: response
    )
    assert runtime._check_existing_runtime() is False


def test_check_existing_runtime_invalid_json(monkeypatch, runtime):
    class BadResponse:
        def json(self):
            raise json.decoder.JSONDecodeError("bad", "", 0)

    monkeypatch.setattr(
        runtime, "_send_runtime_api_request", lambda *args, **kwargs: BadResponse()
    )
    with pytest.raises(json.decoder.JSONDecodeError):
        runtime._check_existing_runtime()


def test_build_runtime_success(monkeypatch, runtime):
    cfg = runtime.config
    cfg.sandbox.runtime_extra_deps = ["dep"]
    responses = SendSequence(
        [
            make_response(200, {"registry_prefix": "registry"}),
            make_response(200, {"exists": True}),
        ]
    )
    monkeypatch.setenv("OH_RUNTIME_RUNTIME_IMAGE_REPO", "old")
    monkeypatch.setattr(remote_runtime, "send_request", responses)
    runtime._build_runtime()
    assert runtime.container_image == "built:image"
    assert responses.calls[0][0] == "GET"


def test_build_runtime_missing_base_image(monkeypatch, dummy_config):
    cfg = clone_config(dummy_config)
    cfg.sandbox.base_container_image = None
    runtime = remote_runtime.RemoteRuntime(
        cfg, types.SimpleNamespace(), types.SimpleNamespace()
    )
    responses = SendSequence([make_response(200, {"registry_prefix": "registry"})])
    monkeypatch.setattr(remote_runtime, "send_request", responses)
    with pytest.raises(ValueError):
        runtime._build_runtime()


def test_build_runtime_image_not_found(monkeypatch, runtime):
    responses = SendSequence(
        [
            make_response(200, {"registry_prefix": "registry"}),
            make_response(200, {"exists": False}),
        ]
    )
    monkeypatch.setattr(remote_runtime, "send_request", responses)
    with pytest.raises(remote_runtime.AgentRuntimeError):
        runtime._build_runtime()
    assert runtime._last_status == remote_runtime.RuntimeStatus.ERROR


def test_start_runtime_with_sysbox(monkeypatch, runtime):
    runtime.config.debug = True
    runtime.config.sandbox.remote_runtime_class = "sysbox"
    runtime.container_image = "built:image"
    payload: dict[str, Any] = {}

    def fake_send(method, url, **kwargs):
        payload.update(kwargs["json"])
        return make_response(
            200,
            {
                "runtime_id": "rt-2",
                "url": "https://runtime/rt-2",
                "work_hosts": {"h": 2},
                "session_api_key": "sess",
            },
        )

    monkeypatch.setattr(runtime, "_send_runtime_api_request", fake_send)
    runtime._start_runtime()
    assert payload["runtime_class"] == "sysbox-runc"
    assert payload["environment"]["DEBUG"] == "true"
    assert runtime.runtime_id == "rt-2"
    assert runtime.session.headers["X-Session-API-Key"] == "sess"


def test_start_or_attach_existing(monkeypatch, runtime):
    monkeypatch.setattr(runtime, "_check_existing_runtime", lambda: True)
    monkeypatch.setattr(runtime, "_wait_until_alive", lambda: None)
    runtime._start_or_attach_to_runtime()
    assert runtime._last_status == remote_runtime.RuntimeStatus.READY


def test_start_or_attach_attach_missing(monkeypatch, runtime):
    runtime.attach_to_existing = True
    monkeypatch.setattr(runtime, "_check_existing_runtime", lambda: False)
    with pytest.raises(remote_runtime.AgentRuntimeNotFoundError):
        runtime._start_or_attach_to_runtime()


def test_start_or_attach_new_build(monkeypatch, runtime):
    runtime.config.sandbox.runtime_container_image = None
    monkeypatch.setattr(runtime, "_check_existing_runtime", lambda: False)
    called = {"build": 0, "start": 0}
    monkeypatch.setattr(
        runtime,
        "_build_runtime",
        lambda: called.__setitem__("build", called["build"] + 1),
    )
    monkeypatch.setattr(
        runtime,
        "_start_runtime",
        lambda: called.__setitem__("start", called["start"] + 1),
    )
    monkeypatch.setattr(runtime, "_wait_until_alive", lambda: None)
    runtime._start_or_attach_to_runtime()
    assert called["build"] == 1 and called["start"] == 1


def test_resume_runtime_success(monkeypatch, runtime):
    runtime.runtime_id = "rt-resume"
    monkeypatch.setattr(
        runtime,
        "_send_runtime_api_request",
        lambda *args, **kwargs: make_response(200, {}),
    )
    monkeypatch.setattr(runtime, "_wait_until_alive", lambda: None)
    monkeypatch.setattr(runtime, "setup_initial_env", lambda: None)
    runtime._resume_runtime()


def test_wait_until_alive_impl_ready_alive_failure(monkeypatch, runtime):
    runtime.runtime_id = "rt"
    runtime.runtime_url = "https://runtime"

    def fake_send(method, url, **kwargs):
        return make_response(200, {"runtime_id": "rt", "pod_status": "ready"})

    monkeypatch.setattr(runtime, "_send_runtime_api_request", fake_send)
    monkeypatch.setattr(
        runtime,
        "check_if_alive",
        lambda: (_ for _ in ()).throw(httpx.HTTPError("boom")),
    )
    with pytest.raises(remote_runtime.AgentRuntimeNotReadyError):
        runtime._wait_until_alive_impl()


def test_wait_until_alive_impl_pending(monkeypatch, runtime):
    runtime.runtime_id = "rt"
    monkeypatch.setattr(
        runtime,
        "_send_runtime_api_request",
        lambda *a, **k: make_response(
            200, {"runtime_id": "rt", "pod_status": "pending"}
        ),
    )
    with pytest.raises(remote_runtime.AgentRuntimeNotReadyError):
        runtime._wait_until_alive_impl()


def test_wait_until_alive_impl_crashloop(monkeypatch, runtime):
    runtime.runtime_id = "rt"
    monkeypatch.setattr(
        runtime,
        "_send_runtime_api_request",
        lambda *a, **k: make_response(
            200, {"runtime_id": "rt", "pod_status": "crashLoopBackOff"}
        ),
    )
    with pytest.raises(remote_runtime.AgentRuntimeUnavailableError):
        runtime._wait_until_alive_impl()


def test_wait_until_alive_impl_unknown_status(monkeypatch, runtime):
    runtime.runtime_id = "rt"
    monkeypatch.setattr(
        runtime,
        "_send_runtime_api_request",
        lambda *a, **k: make_response(
            200, {"runtime_id": "rt", "pod_status": "strange"}
        ),
    )
    with pytest.raises(remote_runtime.AgentRuntimeNotReadyError):
        runtime._wait_until_alive_impl()


def test_close_pause_runtime(monkeypatch, runtime):
    runtime.runtime_id = "rt"
    runtime.config.sandbox.keep_runtime_alive = True
    runtime.config.sandbox.pause_closed_runtimes = True
    calls = []
    monkeypatch.setattr(
        runtime,
        "_send_runtime_api_request",
        lambda method, url, **kwargs: calls.append((method, url, kwargs)),
    )
    runtime.close()
    assert calls[0][0] == "POST"


def test_close_stop_runtime(monkeypatch, runtime):
    runtime.runtime_id = "rt"
    runtime.config.sandbox.keep_runtime_alive = False
    calls = []
    monkeypatch.setattr(
        runtime,
        "_send_runtime_api_request",
        lambda method, url, **kwargs: calls.append((method, url, kwargs)),
    )
    runtime.close()
    assert calls[0][1].endswith("/stop")


def test_close_pause_error(monkeypatch, runtime):
    runtime.runtime_id = "rt"
    runtime.config.sandbox.keep_runtime_alive = True
    runtime.config.sandbox.pause_closed_runtimes = True
    monkeypatch.setattr(
        runtime,
        "_send_runtime_api_request",
        lambda *a, **k: (_ for _ in ()).throw(RuntimeError("fail")),
    )
    with pytest.raises(RuntimeError):
        runtime.close()


def test_send_runtime_api_request_timeout(monkeypatch, runtime):
    monkeypatch.setattr(
        remote_runtime,
        "send_request",
        lambda *a, **k: (_ for _ in ()).throw(httpx.TimeoutException("timeout")),
    )
    with pytest.raises(httpx.TimeoutException):
        runtime._send_runtime_api_request("GET", "https://api")


def test_send_action_server_request_retries_disabled(monkeypatch, runtime):
    runtime.config.sandbox.remote_runtime_enable_retries = False
    monkeypatch.setattr(
        remote_runtime, "send_request", lambda *a, **k: make_response(200, {})
    )
    runtime._send_action_server_request("GET", "https://runtime")


def test_send_action_server_request_with_retry(monkeypatch, runtime):
    runtime.config.sandbox.remote_runtime_enable_retries = True
    calls = {"count": 0}

    def send_request_side_effect(session, method, url, **kwargs):
        calls["count"] += 1
        if calls["count"] == 1:
            raise httpx.NetworkError("fail")
        return make_response(200, {})

    monkeypatch.setattr(remote_runtime, "send_request", send_request_side_effect)
    runtime._send_action_server_request("GET", "https://runtime")
    assert calls["count"] == 2


def test_send_action_server_request_impl_404(monkeypatch, runtime):
    runtime.config.sandbox.remote_runtime_enable_retries = False
    monkeypatch.setattr(
        remote_runtime,
        "send_request",
        lambda *a, **k: (_ for _ in ()).throw(make_http_error(404)),
    )
    with pytest.raises(remote_runtime.AgentRuntimeDisconnectedError):
        runtime._send_action_server_request_impl("GET", "https://runtime")


def test_send_action_server_request_impl_503_resume(monkeypatch, runtime):
    runtime.runtime_id = "rt"
    runtime.config.sandbox.keep_runtime_alive = True
    calls = {"count": 0}

    def send_request_side_effect(session, method, url, **kwargs):
        calls["count"] += 1
        if calls["count"] == 1:
            raise make_http_error(503)
        return make_response(200, {})

    monkeypatch.setattr(remote_runtime, "send_request", send_request_side_effect)
    monkeypatch.setattr(runtime, "_resume_runtime", lambda: None)
    runtime._send_action_server_request_impl("GET", "https://runtime")
    assert calls["count"] == 2


def test_send_action_server_request_impl_503_resume_failure(monkeypatch, runtime):
    runtime.runtime_id = "rt"
    runtime.config.sandbox.keep_runtime_alive = True

    def send_request_side_effect(session, method, url, **kwargs):
        raise make_http_error(503)

    monkeypatch.setattr(remote_runtime, "send_request", send_request_side_effect)
    monkeypatch.setattr(
        runtime,
        "_resume_runtime",
        lambda: (_ for _ in ()).throw(RuntimeError("resume")),
    )
    with pytest.raises(remote_runtime.AgentRuntimeDisconnectedError):
        runtime._send_action_server_request_impl("GET", "https://runtime")


def test_send_action_server_request_impl_503_keep_alive_false(monkeypatch, runtime):
    runtime.runtime_id = "rt"
    runtime.config.sandbox.keep_runtime_alive = False
    monkeypatch.setattr(
        remote_runtime,
        "send_request",
        lambda *a, **k: (_ for _ in ()).throw(make_http_error(503)),
    )
    with pytest.raises(remote_runtime.AgentRuntimeDisconnectedError):
        runtime._send_action_server_request_impl("GET", "https://runtime")


def test_send_action_server_request_impl_timeout(monkeypatch, runtime):
    monkeypatch.setattr(
        remote_runtime,
        "send_request",
        lambda *a, **k: (_ for _ in ()).throw(httpx.TimeoutException("timeout")),
    )
    with pytest.raises(httpx.TimeoutException):
        runtime._send_action_server_request_impl("GET", "https://runtime")


def test_session_api_key_property(monkeypatch, runtime):
    runtime._session_api_key = "session"
    assert runtime.session_api_key == "session"


def test_vscode_url_path(monkeypatch, runtime):
    runtime.runtime_url = "https://runtime.example.com/rt-id"
    runtime.runtime_id = "rt-id"
    assert "rt-id/vscode" in runtime.vscode_url


def test_vscode_url_subdomain(monkeypatch, runtime):
    runtime.runtime_url = "https://runtime.example.com"
    runtime.runtime_id = "rt-id"
    assert "vscode-runtime" in runtime.vscode_url


def test_web_hosts_property(runtime):
    runtime.available_hosts = {"h": 1}
    assert runtime.web_hosts == {"h": 1}


def test_stop_if_closed(runtime):
    runtime._runtime_closed = True
    assert runtime._stop_if_closed(None) is True


def test_get_action_execution_server_startup_command(runtime):
    cmd = runtime.get_action_execution_server_startup_command()
    assert isinstance(cmd, list) and cmd


def test_compose_stop_conditions():
    cond = remote_runtime._compose_stop_conditions(
        lambda state: False, lambda state: True
    )
    assert cond(types.SimpleNamespace()) is True


def test_before_sleep_action_request(monkeypatch):
    captured = []
    monkeypatch.setattr(
        remote_runtime,
        "call_tenacity_hooks",
        lambda before, after, state: captured.append(before),
    )
    monkeypatch.setattr(
        remote_runtime.tenacity,
        "before_sleep_log",
        lambda logger, level: lambda state: captured.append(level),
    )
    remote_runtime._before_sleep_action_request(types.SimpleNamespace())
    assert captured[0] is not None


def test_runtime_init_workspace_base_logs(dummy_config):
    cfg = clone_config(dummy_config)
    cfg.workspace_base = "/workspace-base"
    remote_runtime.RemoteRuntime(cfg, types.SimpleNamespace(), types.SimpleNamespace())


def test_runtime_init_missing_api_url(dummy_config):
    cfg = clone_config(dummy_config)
    cfg.sandbox.remote_runtime_api_url = None
    with pytest.raises(ValueError):
        remote_runtime.RemoteRuntime(
            cfg, types.SimpleNamespace(), types.SimpleNamespace()
        )


def test_action_execution_server_url_not_initialized(runtime):
    runtime.runtime_url = None
    with pytest.raises(NotImplementedError):
        _ = runtime.action_execution_server_url


@pytest.mark.asyncio
async def test_connect_handles_start_error(monkeypatch, runtime):
    runtime.runtime_url = "https://runtime"
    monkeypatch.setattr(
        runtime,
        "_start_or_attach_to_runtime",
        lambda: (_ for _ in ()).throw(RuntimeError("boom")),
    )
    runtime._runtime_closed = False
    with pytest.raises(RuntimeError):
        await runtime.connect()
    assert runtime._runtime_closed is True


def test_check_existing_runtime_http_error(monkeypatch, runtime):
    def raise_http(*args, **kwargs):
        raise make_http_error(500)

    monkeypatch.setattr(runtime, "_send_runtime_api_request", raise_http)
    with pytest.raises(httpx.HTTPStatusError):
        runtime._check_existing_runtime()


def test_check_existing_runtime_resume_success(monkeypatch, runtime):
    response = make_response(
        200,
        {
            "status": "paused",
            "runtime_id": "rt",
            "url": "https://runtime",
            "work_hosts": {},
        },
    )
    monkeypatch.setattr(
        runtime, "_send_runtime_api_request", lambda *args, **kwargs: response
    )
    resumed = {"value": False}
    monkeypatch.setattr(
        runtime, "_resume_runtime", lambda: resumed.__setitem__("value", True)
    )
    assert runtime._check_existing_runtime() is True
    assert resumed["value"] is True


def test_start_runtime_http_error(monkeypatch, runtime):
    runtime.container_image = "img"

    def raise_http(*args, **kwargs):
        raise make_http_error(500)

    monkeypatch.setattr(runtime, "_send_runtime_api_request", raise_http)
    with pytest.raises(remote_runtime.AgentRuntimeUnavailableError):
        runtime._start_runtime()


def test_resume_runtime_fail_api(monkeypatch, runtime):
    runtime.runtime_id = "rt"
    monkeypatch.setattr(
        runtime,
        "_send_runtime_api_request",
        lambda *a, **k: (_ for _ in ()).throw(RuntimeError("api")),
    )
    with pytest.raises(RuntimeError):
        runtime._resume_runtime()


def test_resume_runtime_fail_wait(monkeypatch, runtime):
    runtime.runtime_id = "rt"
    monkeypatch.setattr(
        runtime, "_send_runtime_api_request", lambda *a, **k: make_response(200, {})
    )
    monkeypatch.setattr(
        runtime,
        "_wait_until_alive",
        lambda: (_ for _ in ()).throw(RuntimeError("wait")),
    )
    with pytest.raises(RuntimeError):
        runtime._resume_runtime()


def test_resume_runtime_fail_initial_env(monkeypatch, runtime):
    runtime.runtime_id = "rt"
    monkeypatch.setattr(
        runtime, "_send_runtime_api_request", lambda *a, **k: make_response(200, {})
    )
    monkeypatch.setattr(runtime, "_wait_until_alive", lambda: None)
    monkeypatch.setattr(
        runtime, "setup_initial_env", lambda: (_ for _ in ()).throw(RuntimeError("env"))
    )
    with pytest.raises(RuntimeError):
        runtime._resume_runtime()


def test_wait_until_alive_uses_retry(monkeypatch, runtime):
    calls: list[str] = []

    def fake_retry(*args, **kwargs):
        def decorator(func):
            def wrapper():
                calls.append("retry")
                return func()

            return wrapper

        return decorator

    monkeypatch.setattr(remote_runtime.tenacity, "retry", fake_retry)
    monkeypatch.setattr(remote_runtime.tenacity, "wait_fixed", lambda *a, **k: None)
    monkeypatch.setattr(
        remote_runtime.tenacity, "stop_after_delay", lambda timeout: lambda state: False
    )
    monkeypatch.setattr(runtime, "_wait_until_alive_impl", lambda: calls.append("impl"))
    runtime._wait_until_alive()
    assert calls == ["retry", "impl"]


def test_wait_until_alive_impl_restart_logs(monkeypatch, runtime):
    runtime.runtime_id = "rt"
    runtime.runtime_url = "https://runtime"
    response = make_response(
        200,
        {
            "runtime_id": "rt",
            "pod_status": "pending",
            "restart_count": 1,
            "restart_reasons": ["OOM"],
        },
    )
    monkeypatch.setattr(runtime, "_send_runtime_api_request", lambda *a, **k: response)
    with pytest.raises(remote_runtime.AgentRuntimeNotReadyError):
        runtime._wait_until_alive_impl()


def test_wait_until_alive_impl_ready_success(monkeypatch, runtime):
    runtime.runtime_id = "rt"
    runtime.runtime_url = "https://runtime"
    response = make_response(200, {"runtime_id": "rt", "pod_status": "ready"})
    monkeypatch.setattr(runtime, "_send_runtime_api_request", lambda *a, **k: response)
    monkeypatch.setattr(runtime, "check_if_alive", lambda: None)
    assert runtime._wait_until_alive_impl() is None


def test_close_attach_to_existing(runtime):
    runtime.attach_to_existing = True
    runtime.close()
    assert runtime._runtime_closed is True


def test_close_stop_error(monkeypatch, runtime):
    runtime.runtime_id = "rt"
    runtime.config.sandbox.keep_runtime_alive = False
    monkeypatch.setattr(
        runtime,
        "_send_runtime_api_request",
        lambda *a, **k: (_ for _ in ()).throw(RuntimeError("stop")),
    )
    with pytest.raises(RuntimeError):
        runtime.close()


def test_send_action_server_request_impl_other_error(monkeypatch, runtime):
    def raise_http(*args, **kwargs):
        raise make_http_error(400)

    monkeypatch.setattr(remote_runtime, "send_request", raise_http)
    with pytest.raises(httpx.HTTPStatusError):
        runtime._send_action_server_request_impl("GET", "https://runtime")
