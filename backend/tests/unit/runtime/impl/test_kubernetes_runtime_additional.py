from __future__ import annotations

import importlib
import sys
import types
from pathlib import Path
from typing import Any, Callable, TypeAlias

import pytest

ROOT_DIR = Path(__file__).resolve().parents[4]

# ---------------------------------------------------------------------------
# Helper to register stub modules while remembering originals
# ---------------------------------------------------------------------------

_ORIGINAL_MODULES: dict[str, types.ModuleType | None] = {}
_ShutdownCallbacks: TypeAlias = list[Callable[[], None]]


def _set_module(name: str, module: types.ModuleType) -> None:
    if name not in _ORIGINAL_MODULES:
        _ORIGINAL_MODULES[name] = sys.modules.get(name)
    sys.modules[name] = module


# ---------------------------------------------------------------------------
# Minimal Forge package structure for module import
# ---------------------------------------------------------------------------

forge_pkg = types.ModuleType("forge")
forge_pkg.__path__ = [str(ROOT_DIR / "forge")]
_set_module("forge", forge_pkg)

core_pkg = types.ModuleType("forge.core")
core_pkg.__path__ = [str(ROOT_DIR / "forge" / "core")]
_set_module("forge.core", core_pkg)

runtime_pkg = types.ModuleType("forge.runtime")
runtime_pkg.__path__ = [str(ROOT_DIR / "forge" / "runtime")]
_set_module("forge.runtime", runtime_pkg)
setattr(forge_pkg, "core", core_pkg)
setattr(forge_pkg, "runtime", runtime_pkg)

impl_pkg = types.ModuleType("forge.runtime.impl")
impl_pkg.__path__ = [str(ROOT_DIR / "forge" / "runtime" / "impl")]
_set_module("forge.runtime.impl", impl_pkg)
setattr(runtime_pkg, "impl", impl_pkg)

runtime_utils_pkg = types.ModuleType("forge.runtime.utils")
runtime_utils_pkg.__path__ = [str(ROOT_DIR / "forge" / "runtime" / "utils")]
_set_module("forge.runtime.utils", runtime_utils_pkg)
setattr(runtime_pkg, "utils", runtime_utils_pkg)

utils_pkg = types.ModuleType("forge.utils")
utils_pkg.__path__ = [str(ROOT_DIR / "forge" / "utils")]
_set_module("forge.utils", utils_pkg)
setattr(forge_pkg, "utils", utils_pkg)

k8s_pkg = types.ModuleType("forge.runtime.impl.kubernetes")
k8s_pkg.__path__ = [str(ROOT_DIR / "forge" / "runtime" / "impl" / "kubernetes")]
_set_module("forge.runtime.impl.kubernetes", k8s_pkg)
setattr(impl_pkg, "kubernetes", k8s_pkg)

action_exec_pkg = types.ModuleType("forge.runtime.impl.action_execution")
action_exec_pkg.__path__ = [
    str(ROOT_DIR / "forge" / "runtime" / "impl" / "action_execution")
]
_set_module("forge.runtime.impl.action_execution", action_exec_pkg)

# ---------------------------------------------------------------------------
# Stub core exceptions/logger
# ---------------------------------------------------------------------------

core_exceptions = types.ModuleType("forge.core.exceptions")
setattr(
    core_exceptions,
    "AgentRuntimeDisconnectedError",
    type("AgentRuntimeDisconnectedError", (Exception,), {}),
)
setattr(
    core_exceptions,
    "AgentRuntimeNotFoundError",
    type("AgentRuntimeNotFoundError", (Exception,), {}),
)
setattr(
    core_exceptions, "AgentRuntimeError", type("AgentRuntimeError", (Exception,), {})
)
setattr(
    core_exceptions,
    "AgentRuntimeUnavailableError",
    type("AgentRuntimeUnavailableError", (Exception,), {}),
)
_set_module("forge.core.exceptions", core_exceptions)
setattr(core_pkg, "exceptions", core_exceptions)

logger_module = types.ModuleType("forge.core.logger")
setattr(logger_module, "DEBUG", False)
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
# Stub runtime utils / command helpers referenced by KubernetesRuntime
# ---------------------------------------------------------------------------

command_module = types.ModuleType("forge.runtime.utils.command")
setattr(
    command_module,
    "get_action_execution_server_startup_command",
    lambda **kwargs: [
        "python",
        "-m",
        "forge.runtime.action_execution_server",
    ],
)
_set_module("forge.runtime.utils.command", command_module)
setattr(runtime_utils_pkg, "command", command_module)

async_utils_module = types.ModuleType("forge.utils.async_utils")


async def _call_sync_from_async(fn, *a, **k):
    return fn(*a, **k)


setattr(async_utils_module, "call_sync_from_async", _call_sync_from_async)
_set_module("forge.utils.async_utils", async_utils_module)
setattr(utils_pkg, "async_utils", async_utils_module)

shutdown_module = types.ModuleType("forge.utils.shutdown_listener")
_shutdown_callbacks: _ShutdownCallbacks = []


def _add_shutdown_listener(callback: Callable[[], None]) -> str:
    _shutdown_callbacks.append(callback)
    return f"listener-{len(_shutdown_callbacks)}"


setattr(shutdown_module, "add_shutdown_listener", _add_shutdown_listener)
setattr(shutdown_module, "should_continue", lambda: True)
_set_module("forge.utils.shutdown_listener", shutdown_module)
setattr(utils_pkg, "shutdown_listener", shutdown_module)

metrics_module = types.ModuleType("forge.utils.tenacity_metrics")
setattr(metrics_module, "tenacity_after_factory", lambda label: (lambda state: None))
setattr(
    metrics_module, "tenacity_before_sleep_factory", lambda label: (lambda state: None)
)
setattr(metrics_module, "call_tenacity_hooks", lambda before, after, state: None)
_set_module("forge.utils.tenacity_metrics", metrics_module)
setattr(utils_pkg, "tenacity_metrics", metrics_module)

stop_module = types.ModuleType("forge.utils.tenacity_stop")
setattr(stop_module, "stop_if_should_exit", lambda: (lambda retry_state: False))
_set_module("forge.utils.tenacity_stop", stop_module)
setattr(utils_pkg, "tenacity_stop", stop_module)

# ---------------------------------------------------------------------------
# Stub ActionExecutionClient base and registries
# ---------------------------------------------------------------------------

runtime_base = types.ModuleType("forge.runtime.base")
_runtime_base_attrs = {
    "__init__": lambda self, *a, **k: None,
    "close": lambda self: None,
}
setattr(runtime_base, "Runtime", type("Runtime", (), _runtime_base_attrs))
_set_module("forge.runtime.base", runtime_base)
setattr(runtime_pkg, "base", runtime_base)
setattr(impl_pkg, "action_execution", action_exec_pkg)

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
        plugins: list[Any] | None = None,
        env_vars: dict[str, str] | None = None,
        status_callback: Callable | None = None,
        attach_to_existing: bool = False,
        headless_mode: bool = True,
        user_id: str | None = None,
        git_provider_tokens: Any | None = None,
    ) -> None:
        self.config = config
        self.sid = sid
        self.plugins = list(plugins or [])
        self.session = types.SimpleNamespace(headers={})
        self._runtime_closed = False
        self._runtime_initialized = False
        self.attach_to_existing = attach_to_existing
        self._last_status: tuple[Any, str | None] | None = None
        self._vscode_enabled = True

    def log(self, level: str, message: str, exc_info: bool | None = None) -> None:
        pass

    def set_runtime_status(self, status, message: str | None = None):
        self._last_status = (status, message)

    def get_vscode_token(self) -> str:
        return "token"

    def close(self) -> None:
        self._runtime_closed = True


_action_exec_stub = ActionExecutionClientStub
setattr(action_exec_module, "ActionExecutionClient", _action_exec_stub)
_set_module(
    "forge.runtime.impl.action_execution.action_execution_client", action_exec_module
)
setattr(action_exec_pkg, "action_execution_client", action_exec_module)

# ---------------------------------------------------------------------------
# Stub kubernetes client library
# ---------------------------------------------------------------------------

k8s_client_module = types.ModuleType("kubernetes")
api_client_calls: dict[str, list[Any]] = {"read": [], "create": [], "delete": []}


class CoreV1ApiStub:
    def __init__(self) -> None:
        self.created: list[tuple[str, Any]] = []
        self.deleted: list[tuple[str, str, str, Any | None]] = []
        self.services: list[tuple[str, Any]] = []
        self.pvcs: list[tuple[str, Any]] = []

    def create_namespaced_persistent_volume_claim(
        self, namespace: str, body: Any
    ) -> None:
        self.pvcs.append((namespace, body))

    def create_namespaced_pod(self, namespace: str, body: Any) -> None:
        self.created.append((namespace, body))

    def create_namespaced_service(self, namespace: str, body: Any) -> None:
        self.services.append((namespace, body))

    def delete_namespaced_persistent_volume_claim(
        self, name: str, namespace: str, body: Any | None = None
    ) -> None:
        self.deleted.append(("pvc", name, namespace, body))

    def delete_namespaced_pod(
        self, name: str, namespace: str, body: Any | None = None
    ) -> None:
        self.deleted.append(("pod", name, namespace, body))

    def delete_namespaced_service(self, name: str, namespace: str) -> None:
        self.deleted.append(("service", name, namespace, None))

    def read_namespaced_pod(self, name: str, namespace: str) -> Any:
        api_client_calls["read"].append((name, namespace))
        status = types.SimpleNamespace(
            phase="Running",
            conditions=[types.SimpleNamespace(type="Ready", status="True")],
        )
        return types.SimpleNamespace(status=status)

    def read_namespaced_persistent_volume_claim(self, name: str, namespace: str) -> Any:
        raise client.rest.ApiException(status=404)


class NetworkingV1ApiStub:
    def __init__(self) -> None:
        self.ingresses: list[tuple[str, Any]] = []
        self.deleted_ingresses: list[tuple[str, str]] = []

    def create_namespaced_ingress(self, namespace: str, body: Any) -> None:
        self.ingresses.append((namespace, body))

    def delete_namespaced_ingress(self, name: str, namespace: str) -> None:
        self.deleted_ingresses.append((name, namespace))


class FakeConfigModule(types.ModuleType):
    def load_incluster_config(self):
        return None

    def load_kube_config(self):
        return None


class ApiException(Exception):
    def __init__(self, status: int | None = None):
        super().__init__(status)
        self.status = status


client_module = types.ModuleType("kubernetes.client")
setattr(client_module, "CoreV1Api", CoreV1ApiStub)
setattr(client_module, "NetworkingV1Api", NetworkingV1ApiStub)

rest_module = types.ModuleType("kubernetes.rest")
setattr(rest_module, "ApiException", ApiException)
setattr(client_module, "rest", rest_module)

setattr(k8s_client_module, "client", client_module)
setattr(k8s_client_module, "config", FakeConfigModule("kubernetes.config"))
setattr(k8s_client_module, "rest", rest_module)
_set_module("kubernetes", k8s_client_module)
_set_module("kubernetes.config", k8s_client_module.config)
_set_module("kubernetes.client", client_module)
_set_module("kubernetes.rest", rest_module)
client = k8s_client_module.client


def _client_model(name: str):
    return lambda *a, **k: {"_model": name, "args": a, "kwargs": k}


for cls_name in [
    "V1DeleteOptions",
    "V1LocalObjectReference",
    "V1Probe",
    "V1HTTPGetAction",
    "V1ResourceRequirements",
    "V1ServiceBackendPort",
    "V1IngressTLS",
    "V1Container",
    "V1ContainerPort",
    "V1EnvVar",
    "V1Volume",
    "V1VolumeMount",
    "V1Service",
    "V1ServiceSpec",
    "V1ServicePort",
    "V1Ingress",
    "V1IngressSpec",
    "V1IngressRule",
    "V1HTTPIngressPath",
    "V1HTTPIngressRuleValue",
    "V1IngressBackend",
    "V1IngressServiceBackend",
    "V1PersistentVolumeClaim",
    "V1PersistentVolumeClaimSpec",
    "V1PersistentVolumeClaimVolumeSource",
    "V1SecurityContext",
    "V1Toleration",
    "V1Pod",
    "V1PodSpec",
]:
    setattr(client, cls_name, _client_model(cls_name))

models_module = types.ModuleType("kubernetes.client.models")


def _model(name: str):
    return lambda *a, **k: {"_model": name, "args": a, "kwargs": k}


for cls_name in [
    "V1Container",
    "V1ContainerPort",
    "V1EnvVar",
    "V1Volume",
    "V1VolumeMount",
    "V1Service",
    "V1ServiceSpec",
    "V1ServicePort",
    "V1ServiceBackendPort",
    "V1Ingress",
    "V1IngressSpec",
    "V1IngressRule",
    "V1HTTPIngressPath",
    "V1HTTPIngressRuleValue",
    "V1IngressBackend",
    "V1IngressServiceBackend",
    "V1IngressTLS",
    "V1PersistentVolumeClaim",
    "V1PersistentVolumeClaimSpec",
    "V1PersistentVolumeClaimVolumeSource",
    "V1ResourceRequirements",
    "V1SecurityContext",
    "V1Toleration",
    "V1DeleteOptions",
    "V1LocalObjectReference",
    "V1Probe",
    "V1HTTPGetAction",
    "V1Pod",
    "V1PodSpec",
]:
    setattr(models_module, cls_name, _model(cls_name))

_set_module("kubernetes.client.models", models_module)
setattr(client_module, "models", models_module)

# ---------------------------------------------------------------------------
# Import target module after stubbing
# ---------------------------------------------------------------------------

kubernetes_runtime = importlib.import_module(
    "forge.runtime.impl.kubernetes.kubernetes_runtime"
)
KubernetesRuntime = kubernetes_runtime.KubernetesRuntime
_ORIGINAL_INIT_CLIENT = KubernetesRuntime._init_kubernetes_client


@pytest.fixture(autouse=True)
def reset_state(monkeypatch):
    KubernetesRuntime._shutdown_listener_id = None
    KubernetesRuntime._namespace = ""
    api_client_calls["read"].clear()

    def _init_clients():
        return (CoreV1ApiStub(), NetworkingV1ApiStub())

    monkeypatch.setattr(
        kubernetes_runtime.KubernetesRuntime,
        "_init_kubernetes_client",
        staticmethod(_init_clients),
    )
    yield
    KubernetesRuntime._shutdown_listener_id = None
    KubernetesRuntime._namespace = ""


@pytest.fixture
def dummy_config():
    sandbox = types.SimpleNamespace(
        runtime_container_image="forge/runtime:image",
        base_container_image="forge/base:image",
        runtime_startup_env_vars={},
        keep_runtime_alive=False,
    )
    kubernetes_cfg = types.SimpleNamespace(
        namespace="forge",
        storage_class="standard",
        pvc_storage_size="1Gi",
        pvc_storage_class="standard",
        ingress_domain="example.com",
        ingress_tls_secret=None,
        resource_memory_limit="1Gi",
        resource_cpu_request="500m",
        resource_memory_request="512Mi",
        privileged=False,
        image_pull_secret=None,
        node_selector_key=None,
        node_selector_val=None,
        tolerations=[],
        tolerations_yaml=None,
    )
    config = types.SimpleNamespace(
        sandbox=sandbox,
        kubernetes=kubernetes_cfg,
        debug=False,
        enable_browser=False,
        workspace_mount_path_in_sandbox="/workspace",
    )
    return config


@pytest.fixture
def dummy_runtime(monkeypatch, dummy_config):
    runtime = KubernetesRuntime(dummy_config, None, None)
    runtime.k8s_client = CoreV1ApiStub()
    runtime.k8s_networking_client = NetworkingV1ApiStub()
    return runtime


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


def test_shutdown_listener_registers_once(dummy_config):
    runtime1 = KubernetesRuntime(dummy_config, None, None)
    runtime2 = KubernetesRuntime(dummy_config, None, None)
    assert runtime1._shutdown_listener_id == runtime2._shutdown_listener_id
    assert KubernetesRuntime._namespace == "forge"


def test_init_requires_kubernetes_config():
    config = types.SimpleNamespace(sandbox=types.SimpleNamespace(), kubernetes=None)
    with pytest.raises(ValueError):
        KubernetesRuntime(config, None, None)


def test_init_sets_urls(dummy_config):
    runtime = KubernetesRuntime(dummy_config, None, None, sid="session1")
    assert runtime.pod_name == "Forge-runtime-session1"
    assert runtime.api_url.endswith(":8080")
    assert "forge-runtime-session1" in runtime.k8s_local_url.lower()


def test_handle_create_k8s_resources(dummy_runtime):
    body = {"meta": "pod"}
    dummy_runtime._runtime_initialized = True
    dummy_runtime._pvc_exists = lambda: False
    dummy_runtime._get_runtime_pod_manifest = lambda: body
    dummy_runtime._get_runtime_service_manifest = lambda: {"service": True}
    dummy_runtime._get_vscode_service_manifest = lambda: {"vscode": True}
    dummy_runtime._get_vscode_ingress_manifest = lambda: {"ingress": True}
    dummy_runtime._get_pvc_manifest = lambda: {"pvc": True}
    dummy_runtime._wait_until_ready = lambda: None

    dummy_runtime._init_k8s_resources()


def test_create_pod_calls_k8s_client(dummy_runtime):
    dummy_runtime._k8s_config.node_selector_key = "disktype"
    dummy_runtime._k8s_config.node_selector_val = "ssd"
    dummy_runtime._k8s_config.tolerations_yaml = (
        "- key: work\n  operator: Exists\n  effect: NoSchedule"
    )
    pod = dummy_runtime._get_runtime_pod_manifest()
    assert pod["_model"] == "V1Pod"
    metadata = pod["kwargs"]["metadata"]["kwargs"]
    assert metadata["name"] == dummy_runtime.pod_name
    spec_kwargs = pod["kwargs"]["spec"]["kwargs"]
    assert spec_kwargs["node_selector"] == {"disktype": "ssd"}
    assert spec_kwargs["tolerations"][0]["kwargs"]["key"] == "work"


def test_delete_pod_handles_missing(dummy_runtime, monkeypatch):
    monkeypatch.setattr(
        dummy_runtime.k8s_client,
        "delete_namespaced_pod",
        lambda *a, **k: (_ for _ in ()).throw(Exception()),
    )
    dummy_runtime._cleanup_k8s_resources(namespace="forge", conversation_id="session1")


def test_generate_container_spec(dummy_runtime):
    pod_manifest = dummy_runtime._get_runtime_pod_manifest()
    containers = pod_manifest["kwargs"]["spec"]["kwargs"]["containers"]
    container = containers[0]
    assert container["_model"] == "V1Container"
    ports = container["kwargs"]["ports"]
    assert any(port["kwargs"]["container_port"] == 8080 for port in ports)


def test_build_service_spec(dummy_runtime):
    service = dummy_runtime._get_runtime_service_manifest()
    assert service["_model"] == "V1Service"
    assert service["kwargs"]["metadata"]["kwargs"]["name"].startswith("Forge-runtime")


def test_cleanup_resources_invoked_once(dummy_runtime):
    cleanup_calls: list[Callable[[], None]] = []
    patcher = pytest.MonkeyPatch()

    def _record_listener(callback: Callable[[], None]) -> str:
        cleanup_calls.append(callback)
        return "listener"

    patcher.setattr(kubernetes_runtime, "add_shutdown_listener", _record_listener)
    try:
        KubernetesRuntime._shutdown_listener_id = None
        KubernetesRuntime(dummy_runtime.config, None, None)
        assert cleanup_calls
    finally:
        patcher.undo()


def test_retry_helpers(dummy_runtime):
    dummy_runtime.k8s_client.read_namespaced_pod = (
        lambda name, namespace: types.SimpleNamespace(
            status=types.SimpleNamespace(
                phase="Running",
                conditions=[types.SimpleNamespace(type="Ready", status="True")],
            ),
        )
    )
    assert dummy_runtime._wait_until_ready() is True
    dummy_runtime.k8s_client.read_namespaced_pod = (
        lambda name, namespace: types.SimpleNamespace(
            status=types.SimpleNamespace(phase="Pending", conditions=[])
        )
    )
    with pytest.raises(TimeoutError):
        dummy_runtime._wait_until_ready()


def test_tolerations_invalid_format(dummy_runtime):
    dummy_runtime._k8s_config.tolerations_yaml = "{}"
    assert dummy_runtime.tolerations is None


def test_tolerations_yaml_error(dummy_runtime):
    dummy_runtime._k8s_config.tolerations_yaml = "- key: value: broken"
    assert dummy_runtime.tolerations is None


def test_attach_to_pod_not_ready(dummy_runtime):
    dummy_runtime.k8s_client.read_namespaced_pod = (
        lambda *a, **k: types.SimpleNamespace(
            status=types.SimpleNamespace(phase="Pending", conditions=[])
        )
    )
    dummy_runtime._wait_until_ready = lambda: (_ for _ in ()).throw(
        TimeoutError("still pending")
    )
    with pytest.raises(core_exceptions.AgentRuntimeDisconnectedError):
        dummy_runtime._attach_to_pod()


def test_attach_to_pod_api_exception(dummy_runtime):
    def _raise(*a, **k):
        raise client.rest.ApiException(status=500)

    dummy_runtime.k8s_client.read_namespaced_pod = _raise
    with pytest.raises(client.rest.ApiException):
        dummy_runtime._attach_to_pod()


def test_static_name_helpers(dummy_runtime):
    assert (
        dummy_runtime._get_vscode_tls_secret_name("Forge-runtime-abc")
        == "Forge-runtime-abc-tls-secret"
    )
    assert (
        dummy_runtime._get_vscode_ingress_name("Forge-runtime-abc")
        == "Forge-runtime-abc-ingress-code"
    )
    assert (
        dummy_runtime._get_vscode_svc_name("Forge-runtime-abc")
        == "Forge-runtime-abc-svc-code"
    )
    assert dummy_runtime._get_pvc_name("Forge-runtime-abc") == "Forge-runtime-abc-pvc"


def test_close_cleans_up(dummy_runtime):
    dummy_runtime.close()
    assert dummy_runtime._runtime_initialized is False


@pytest.mark.asyncio
async def test_delete_classmethod(monkeypatch):
    calls = []
    monkeypatch.setattr(
        kubernetes_runtime.KubernetesRuntime,
        "_cleanup_k8s_resources",
        classmethod(lambda cls, **kwargs: calls.append(kwargs)),
    )
    await kubernetes_runtime.KubernetesRuntime.delete("runtime-abc")
    assert calls and calls[0]["conversation_id"] == "runtime-abc"
    assert calls[0]["remove_pvc"] is True


@pytest.mark.asyncio
async def test_connect_attach_existing_success(dummy_config, monkeypatch):
    runtime = KubernetesRuntime(dummy_config, None, None, attach_to_existing=True)
    runtime._vscode_enabled = False
    monkeypatch.setattr(runtime, "_attach_to_pod", lambda: True)
    monkeypatch.setattr(runtime, "_wait_until_ready", lambda: True)
    await runtime.connect()
    assert runtime._runtime_initialized is True


@pytest.mark.asyncio
async def test_connect_attach_existing_failure(dummy_config, monkeypatch):
    runtime = KubernetesRuntime(dummy_config, None, None, attach_to_existing=True)
    monkeypatch.setattr(
        runtime,
        "_attach_to_pod",
        lambda: (_ for _ in ()).throw(client.rest.ApiException(status=404)),
    )
    with pytest.raises(core_exceptions.AgentRuntimeDisconnectedError):
        await runtime.connect()


@pytest.mark.asyncio
async def test_connect_init_failure(dummy_config, monkeypatch):
    runtime = KubernetesRuntime(dummy_config, None, None)
    runtime._vscode_enabled = False
    runtime.setup_initial_env = lambda: None
    monkeypatch.setattr(
        runtime,
        "_attach_to_pod",
        lambda: (_ for _ in ()).throw(client.rest.ApiException(status=404)),
    )
    monkeypatch.setattr(
        runtime,
        "_init_k8s_resources",
        lambda: (_ for _ in ()).throw(RuntimeError("init failed")),
    )
    with pytest.raises(core_exceptions.AgentRuntimeNotFoundError):
        await runtime.connect()


@pytest.mark.asyncio
async def test_connect_wait_failure(dummy_config, monkeypatch):
    runtime = KubernetesRuntime(dummy_config, None, None)
    runtime._vscode_enabled = False
    runtime.setup_initial_env = lambda: None
    monkeypatch.setattr(
        runtime,
        "_attach_to_pod",
        lambda: (_ for _ in ()).throw(client.rest.ApiException(status=404)),
    )
    monkeypatch.setattr(runtime, "_init_k8s_resources", lambda: None)
    monkeypatch.setattr(
        runtime,
        "_wait_until_ready",
        lambda: (_ for _ in ()).throw(TimeoutError("slow")),
    )
    with pytest.raises(core_exceptions.AgentRuntimeDisconnectedError):
        await runtime.connect()


def test_web_hosts_mapping(dummy_runtime):
    dummy_runtime._app_ports = [3000, 3001]
    hosts = dummy_runtime.web_hosts
    assert hosts[f"{dummy_runtime.k8s_local_url}:3000"] == 3000


def test_close_keep_runtime_alive(dummy_runtime, monkeypatch):
    dummy_runtime.config.sandbox.keep_runtime_alive = True
    called = []
    monkeypatch.setattr(
        kubernetes_runtime.KubernetesRuntime,
        "_cleanup_k8s_resources",
        classmethod(lambda cls, **k: called.append(k)),
    )
    dummy_runtime.close()
    assert not called


def test_vscode_url_generation(dummy_runtime, monkeypatch):
    dummy_runtime._vscode_enabled = True
    dummy_runtime._runtime_initialized = True
    dummy_runtime._k8s_config.ingress_tls_secret = "tls"
    monkeypatch.setattr(
        kubernetes_runtime.ActionExecutionClient,
        "get_vscode_token",
        lambda self: "abc123",
    )
    url = dummy_runtime.vscode_url
    assert url.startswith("https://") and "abc123" in url


def test_vscode_url_missing_token(dummy_runtime, monkeypatch):
    dummy_runtime._vscode_enabled = True
    monkeypatch.setattr(
        kubernetes_runtime.ActionExecutionClient, "get_vscode_token", lambda self: ""
    )
    assert dummy_runtime.vscode_url is None


def test_pvc_exists_handles_404(dummy_runtime):
    assert dummy_runtime._pvc_exists() is False
    dummy_runtime.k8s_client.read_namespaced_persistent_volume_claim = (
        lambda *a, **k: object()
    )
    assert dummy_runtime._pvc_exists() is not None


def test_pvc_exists_logs_error(dummy_runtime, monkeypatch):
    messages = []

    def _log(level: str, message: str, exc_info: bool | None = None):
        messages.append((level, message))

    monkeypatch.setattr(dummy_runtime, "log", _log)

    def _raise(*a, **k):
        raise ApiException(status=500)

    dummy_runtime.k8s_client.read_namespaced_persistent_volume_claim = _raise
    assert dummy_runtime._pvc_exists() is None
    assert messages and "Error checking PVC existence" in messages[-1][1]


def test_cleanup_k8s_resources(monkeypatch):
    api = CoreV1ApiStub()
    net = NetworkingV1ApiStub()

    def _init():
        return (api, net)

    monkeypatch.setattr(
        kubernetes_runtime.KubernetesRuntime,
        "_init_kubernetes_client",
        staticmethod(_init),
    )
    kubernetes_runtime.KubernetesRuntime._cleanup_k8s_resources(
        "forge", True, "session1"
    )
    assert any(item[0] == "pvc" for item in api.deleted)
    assert net.deleted_ingresses


def test_cleanup_k8s_resources_handles_errors(monkeypatch):
    patcher = pytest.MonkeyPatch()

    def _failing_init():
        raise RuntimeError("init broken")

    patcher.setattr(
        kubernetes_runtime.KubernetesRuntime,
        "_init_kubernetes_client",
        staticmethod(_failing_init),
    )
    try:
        kubernetes_runtime.KubernetesRuntime._cleanup_k8s_resources(
            "forge", True, "conversation"
        )
    finally:
        patcher.undo()


def test_close_handles_cleanup_exception(dummy_runtime, monkeypatch):
    dummy_runtime.config.sandbox.keep_runtime_alive = False
    dummy_runtime.attach_to_existing = False
    monkeypatch.setattr(
        kubernetes_runtime.KubernetesRuntime,
        "_cleanup_k8s_resources",
        classmethod(lambda *a, **k: (_ for _ in ()).throw(RuntimeError("cleanup"))),
    )
    dummy_runtime.close()


def test_init_k8s_resources_skips_pvc(monkeypatch, dummy_runtime):
    dummy_runtime._pvc_exists = lambda: True
    created = []
    dummy_runtime.k8s_client.create_namespaced_persistent_volume_claim = (
        lambda *a, **k: created.append("pvc")
    )
    dummy_runtime.k8s_client.create_namespaced_pod = lambda *a, **k: created.append(
        "pod"
    )
    dummy_runtime.k8s_client.create_namespaced_service = lambda *a, **k: created.append(
        "svc"
    )
    dummy_runtime.k8s_networking_client.create_namespaced_ingress = (
        lambda *a, **k: created.append("ingress")
    )
    dummy_runtime._wait_until_ready = lambda: None
    dummy_runtime._init_k8s_resources()
    assert "pvc" not in created and {"pod", "svc", "ingress"}.issubset(set(created))


def test_runtime_pod_manifest_includes_debug_and_secrets(dummy_runtime):
    dummy_runtime.config.debug = True
    dummy_runtime._k8s_config.image_pull_secret = "pull-secret"
    dummy_runtime.config.sandbox.runtime_startup_env_vars = {"FOO": "BAR"}
    pod = dummy_runtime._get_runtime_pod_manifest()
    spec = pod["kwargs"]["spec"]["kwargs"]
    container = spec["containers"][0]
    env_names = [env["kwargs"]["name"] for env in container["kwargs"]["env"]]
    assert "DEBUG" in env_names and "FOO" in env_names
    assert spec["image_pull_secrets"][0]["kwargs"]["name"] == "pull-secret"


def test_get_vscode_ingress_manifest_with_tls(dummy_runtime):
    dummy_runtime._k8s_config.ingress_tls_secret = "tls-secret"
    ingress = dummy_runtime._get_vscode_ingress_manifest()
    spec = ingress["kwargs"]["spec"]["kwargs"]
    assert spec["tls"][0]["kwargs"]["secret_name"] == "tls-secret"


def test_init_kubernetes_client_logs_error(monkeypatch):
    messages = []
    monkeypatch.setattr(
        logger_module.forge_logger,
        "error",
        lambda msg, *a: messages.append(msg % a if a else msg),
    )
    monkeypatch.setattr(
        kubernetes_runtime.config,
        "load_incluster_config",
        lambda: (_ for _ in ()).throw(RuntimeError("boom")),
    )
    monkeypatch.setattr(
        kubernetes_runtime.KubernetesRuntime,
        "_init_kubernetes_client",
        _ORIGINAL_INIT_CLIENT,
    )
    kubernetes_runtime.KubernetesRuntime._init_kubernetes_client.cache_clear()
    with pytest.raises(RuntimeError):
        kubernetes_runtime.KubernetesRuntime._init_kubernetes_client()
    assert any("Failed to initialize Kubernetes client" in msg for msg in messages)


@pytest.mark.asyncio
async def test_connect_success_flow(dummy_config, monkeypatch):
    runtime = KubernetesRuntime(dummy_config, None, None)
    runtime._vscode_enabled = False
    events = []

    def record_init():
        events.append("init")

    def record_setup():
        events.append("setup")

    monkeypatch.setattr(
        runtime,
        "_attach_to_pod",
        lambda: (_ for _ in ()).throw(ApiException(status=404)),
    )
    monkeypatch.setattr(runtime, "_init_k8s_resources", record_init)
    monkeypatch.setattr(runtime, "_wait_until_ready", lambda: True)
    runtime.setup_initial_env = record_setup
    await runtime.connect()
    assert runtime._runtime_initialized is True
    assert events == ["init", "setup"]


@pytest.mark.asyncio
async def test_delete_handles_cleanup_error(monkeypatch):
    messages = []
    monkeypatch.setattr(
        logger_module.forge_logger,
        "error",
        lambda msg, *a: messages.append(msg % a if a else msg),
    )
    monkeypatch.setattr(
        kubernetes_runtime.KubernetesRuntime,
        "_cleanup_k8s_resources",
        classmethod(lambda *a, **k: (_ for _ in ()).throw(RuntimeError("fail"))),
    )
    await kubernetes_runtime.KubernetesRuntime.delete("conversation")
    assert any("Error deleting resources" in msg for msg in messages)


def teardown_module(module):
    for name, original in _ORIGINAL_MODULES.items():
        if original is None:
            sys.modules.pop(name, None)
        else:
            sys.modules[name] = original
