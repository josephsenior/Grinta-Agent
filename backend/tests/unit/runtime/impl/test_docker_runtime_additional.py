from __future__ import annotations

import importlib
import importlib.machinery
import os
import sys
import types
from pathlib import Path
from typing import Any, Callable

import httpx
import pytest
import tenacity
from pydantic import BaseModel

###############################################################################
# Minimal stub implementations for heavy dependencies
###############################################################################

ROOT_DIR = Path(__file__).resolve().parents[4]

forge_pkg = types.ModuleType("forge")
forge_pkg.__path__ = [str(ROOT_DIR / "forge")]
sys.modules.setdefault("forge", forge_pkg)

runtime_pkg = types.ModuleType("forge.runtime")
runtime_pkg.__path__ = [str(ROOT_DIR / "forge" / "runtime")]
sys.modules.setdefault("forge.runtime", runtime_pkg)

impl_pkg = types.ModuleType("forge.runtime.impl")
impl_pkg.__path__ = [str(ROOT_DIR / "forge" / "runtime" / "impl")]
sys.modules.setdefault("forge.runtime.impl", impl_pkg)

docker_pkg = types.ModuleType("forge.runtime.impl.docker")
docker_pkg.__path__ = [str(ROOT_DIR / "forge" / "runtime" / "impl" / "docker")]
sys.modules.setdefault("forge.runtime.impl.docker", docker_pkg)

PORT_SEQUENCE: list[int] = [31000, 36000, 41000, 46000, 51000, 56000]


def _next_port() -> int:
    if not PORT_SEQUENCE:
        raise AssertionError("Port sequence exhausted")
    return PORT_SEQUENCE.pop(0)


# forge.core.exceptions -------------------------------------------------------
class _ExceptionsModule(types.ModuleType):
    AgentRuntimeDisconnectedError: type[Exception]
    AgentRuntimeNotFoundError: type[Exception]
    AgentRuntimeError: type[Exception]
    AgentRuntimeUnavailableError: type[Exception]
    MicroagentValidationError: type[Exception]
    AgentRuntimeBuildError: type[Exception]


exc_module = _ExceptionsModule("forge.core.exceptions")
exc_module.AgentRuntimeDisconnectedError = type(
    "AgentRuntimeDisconnectedError", (Exception,), {}
)
exc_module.AgentRuntimeNotFoundError = type(
    "AgentRuntimeNotFoundError", (Exception,), {}
)
exc_module.AgentRuntimeError = type("AgentRuntimeError", (Exception,), {})
exc_module.AgentRuntimeUnavailableError = type(
    "AgentRuntimeUnavailableError", (Exception,), {}
)
exc_module.MicroagentValidationError = type(
    "MicroagentValidationError", (Exception,), {}
)
exc_module.AgentRuntimeBuildError = type("AgentRuntimeBuildError", (Exception,), {})
sys.modules["forge.core.exceptions"] = exc_module


# forge.core.logger -----------------------------------------------------------
class _LoggerModule(types.ModuleType):
    forge_logger: types.SimpleNamespace
    LOG_DIR: str
    DEBUG: bool
    DEBUG_RUNTIME: bool
    RollingLogger: type["RollingLoggerStub"]


logger_module = _LoggerModule("forge.core.logger")
logger_module.forge_logger = types.SimpleNamespace(
    debug=lambda *a, **k: None,
    info=lambda *a, **k: None,
    warning=lambda *a, **k: None,
    warn=lambda *a, **k: None,
    error=lambda *a, **k: None,
)
logger_module.LOG_DIR = "/tmp"
logger_module.DEBUG = False
logger_module.DEBUG_RUNTIME = False


class RollingLoggerStub:
    def __init__(self, max_lines: int = 10) -> None:
        self.max_lines = max_lines
        self.lines: list[str] = []

    def add(self, line: str) -> None:
        self.lines.append(line)
        if len(self.lines) > self.max_lines:
            self.lines.pop(0)


logger_module.RollingLogger = RollingLoggerStub
sys.modules["forge.core.logger"] = logger_module


# forge.events stubs ---------------------------------------------------------
class _EventsPackage(types.ModuleType):
    __package__: str
    __path__: list[str]
    EventSource: type
    EventStream: type
    EventStreamSubscriber: type


events_pkg = _EventsPackage("forge.events")
events_pkg.__package__ = "forge"
events_pkg.__path__ = []
events_pkg.EventSource = type("EventSource", (), {})
events_pkg.EventStream = type("EventStream", (), {})
events_pkg.EventStreamSubscriber = type("EventStreamSubscriber", (), {})
sys.modules["forge.events"] = events_pkg


class _ActionEventsModule(types.ModuleType):
    __package__: str


action_events_module = _ActionEventsModule("forge.events.action")
action_events_module.__package__ = "forge.events"
for cls_name in [
    "Action",
    "ActionConfirmationStatus",
    "AgentThinkAction",
    "BrowseInteractiveAction",
    "BrowseURLAction",
    "CmdRunAction",
    "FileEditAction",
    "FileReadAction",
    "FileWriteAction",
    "IPythonRunCellAction",
]:
    setattr(action_events_module, cls_name, type(cls_name, (), {}))


def _create_action_attr(name: str):
    cls = type(name, (), {})
    setattr(action_events_module, name, cls)
    return cls


setattr(action_events_module, "__getattr__", _create_action_attr)
sys.modules["forge.events.action"] = action_events_module


class _ObservationEventsModule(types.ModuleType):
    __package__: str


observation_events_module = _ObservationEventsModule("forge.events.observation")
observation_events_module.__package__ = "forge.events"
for cls_name in [
    "Observation",
    "ErrorObservation",
    "AgentThinkObservation",
    "NullObservation",
    "UserRejectObservation",
]:
    setattr(observation_events_module, cls_name, type(cls_name, (), {}))


def _create_observation_attr(name: str):
    cls = type(name, (), {})
    setattr(observation_events_module, name, cls)
    return cls


setattr(observation_events_module, "__getattr__", _create_observation_attr)
sys.modules["forge.events.observation"] = observation_events_module


class _SerializationEventsModule(types.ModuleType):
    __package__: str
    event_to_dict: Callable[[object], dict[str, object]]
    observation_from_dict: Callable[[object], object]


serialization_events_module = _SerializationEventsModule("forge.events.serialization")
serialization_events_module.__package__ = "forge.events"
serialization_events_module.event_to_dict = lambda action: {"action": action}
serialization_events_module.observation_from_dict = lambda data: data
sys.modules["forge.events.serialization"] = serialization_events_module


class _SerializationActionModule(types.ModuleType):
    __package__: str
    ACTION_TYPE_TO_CLASS: dict[str, type]


serialization_action_events_module = _SerializationActionModule(
    "forge.events.serialization.action"
)
serialization_action_events_module.__package__ = "forge.events.serialization"
serialization_action_events_module.ACTION_TYPE_TO_CLASS = {}
sys.modules["forge.events.serialization.action"] = serialization_action_events_module


class _EventModule(types.ModuleType):
    __package__: str
    Event: type
    EventSource: type
    RecallType: type


event_module = _EventModule("forge.events.event")
event_module.__package__ = "forge.events"
event_module.Event = type("Event", (), {})
event_module.EventSource = type("EventSource", (), {})
event_module.RecallType = type("RecallType", (), {})
sys.modules["forge.events.event"] = event_module


class _ToolModule(types.ModuleType):
    __package__: str
    ToolCallMetadata: type


tool_module = _ToolModule("forge.events.tool")
tool_module.__package__ = "forge.events"
tool_module.ToolCallMetadata = type("ToolCallMetadata", (), {})
sys.modules["forge.events.tool"] = tool_module


class _FilesModule(types.ModuleType):
    FileEditAction: type


files_module = _FilesModule("forge.events.action.files")
files_module.FileEditAction = type("FileEditAction", (), {})
sys.modules["forge.events.action.files"] = files_module


class _CommandsModule(types.ModuleType):
    CmdRunAction: type


commands_module = _CommandsModule("forge.events.action.commands")
commands_module.CmdRunAction = type("CmdRunAction", (), {})
sys.modules["forge.events.action.commands"] = commands_module

# litellm stub ---------------------------------------------------------------
from pydantic import BaseModel


class LiteLLMModelResponse(BaseModel):
    model: str | None = None
    choices: list[Any] = []


class LiteLLMModelInfo(BaseModel):
    model_name: str | None = None


class LiteLLMPromptTokensDetails(BaseModel):
    cached_tokens: int | None = None


class LiteLLMChatCompletionToolParam(BaseModel):
    name: str | None = None
    description: str | None = None
    parameters: dict[str, Any] = {}


async def _litellm_acompletion(*args, **kwargs) -> dict[str, Any]:
    return {}


def _litellm_completion(*args, **kwargs) -> dict[str, Any]:
    return {}


class _LiteLLMError(Exception):
    pass


class LiteLLMAPIConnectionError(_LiteLLMError):
    pass


class LiteLLMContentPolicyViolationError(_LiteLLMError):
    pass


class LiteLLMRateLimitError(_LiteLLMError):
    pass


class LiteLLMServiceUnavailableError(_LiteLLMError):
    pass


class LiteLLMTimeout(_LiteLLMError):
    pass


class LiteLLMInternalServerError(_LiteLLMError):
    pass


class LiteLLMCostPerToken(BaseModel):
    input_cost_per_token: float | None = None
    output_cost_per_token: float | None = None


class LiteLLMUsage(BaseModel):
    prompt_tokens: int | None = None
    completion_tokens: int | None = None
    total_tokens: int | None = None


class _LiteLLMUtilsModule(types.ModuleType):
    create_pretrained_tokenizer: Callable[..., Any]
    get_model_info: Callable[..., Any]


litellm_utils_module = _LiteLLMUtilsModule("litellm.utils")
litellm_utils_module.create_pretrained_tokenizer = lambda *args, **kwargs: None
litellm_utils_module.get_model_info = lambda *args, **kwargs: {}


class _LiteLLMExceptionsModule(types.ModuleType):
    APIConnectionError: type[Exception]
    ContentPolicyViolationError: type[Exception]
    RateLimitError: type[Exception]
    ServiceUnavailableError: type[Exception]
    Timeout: type[Exception]
    InternalServerError: type[Exception]


exceptions_module = _LiteLLMExceptionsModule("litellm.exceptions")
exceptions_module.APIConnectionError = LiteLLMAPIConnectionError
exceptions_module.ContentPolicyViolationError = LiteLLMContentPolicyViolationError
exceptions_module.RateLimitError = LiteLLMRateLimitError
exceptions_module.ServiceUnavailableError = LiteLLMServiceUnavailableError
exceptions_module.Timeout = LiteLLMTimeout
exceptions_module.InternalServerError = LiteLLMInternalServerError


class _LiteLLMTypesUtilsModule(types.ModuleType):
    CostPerToken: type[LiteLLMCostPerToken]
    ModelResponse: type[LiteLLMModelResponse]
    Usage: type[LiteLLMUsage]


types_utils_module = _LiteLLMTypesUtilsModule("litellm.types.utils")
types_utils_module.CostPerToken = LiteLLMCostPerToken
types_utils_module.ModelResponse = LiteLLMModelResponse
types_utils_module.Usage = LiteLLMUsage


class _LiteLLMModule(types.ModuleType):
    ModelResponse: type[LiteLLMModelResponse]
    ModelInfo: type[LiteLLMModelInfo]
    PromptTokensDetails: type[LiteLLMPromptTokensDetails]
    ChatCompletionToolParam: type[LiteLLMChatCompletionToolParam]
    acompletion: Callable[..., Any]
    completion: Callable[..., Any]
    completion_cost: Callable[..., Any]
    APIConnectionError: type[Exception]
    ContentPolicyViolationError: type[Exception]
    RateLimitError: type[Exception]
    ServiceUnavailableError: type[Exception]
    Timeout: type[Exception]
    InternalServerError: type[Exception]
    CostPerToken: type[LiteLLMCostPerToken]
    Usage: type[LiteLLMUsage]
    suppress_debug_info: bool
    set_verbose: bool
    utils: _LiteLLMUtilsModule
    exceptions: _LiteLLMExceptionsModule
    create_pretrained_tokenizer: Callable[..., Any]
    get_model_info: Callable[..., Any]


litellm_module = _LiteLLMModule("litellm")
litellm_module.ModelResponse = LiteLLMModelResponse
litellm_module.ModelInfo = LiteLLMModelInfo
litellm_module.PromptTokensDetails = LiteLLMPromptTokensDetails
litellm_module.ChatCompletionToolParam = LiteLLMChatCompletionToolParam
litellm_module.acompletion = _litellm_acompletion
litellm_module.completion = _litellm_completion
litellm_module.completion_cost = lambda *args, **kwargs: 0
litellm_module.APIConnectionError = LiteLLMAPIConnectionError
litellm_module.ContentPolicyViolationError = LiteLLMContentPolicyViolationError
litellm_module.RateLimitError = LiteLLMRateLimitError
litellm_module.ServiceUnavailableError = LiteLLMServiceUnavailableError
litellm_module.Timeout = LiteLLMTimeout
litellm_module.InternalServerError = LiteLLMInternalServerError
litellm_module.CostPerToken = LiteLLMCostPerToken
litellm_module.Usage = LiteLLMUsage
litellm_module.suppress_debug_info = True
litellm_module.set_verbose = False
litellm_module.utils = litellm_utils_module
litellm_module.exceptions = exceptions_module
litellm_module.create_pretrained_tokenizer = (
    litellm_utils_module.create_pretrained_tokenizer
)
litellm_module.get_model_info = litellm_utils_module.get_model_info
sys.modules["litellm"] = litellm_module
sys.modules["litellm.utils"] = litellm_utils_module
sys.modules["litellm.exceptions"] = exceptions_module
sys.modules["litellm.types.utils"] = types_utils_module


# forge.events.action.mcp ----------------------------------------------------
class _MCPModule(types.ModuleType):
    MCPAction: type


mcp_module = _MCPModule("forge.events.action.mcp")
mcp_module.MCPAction = type("MCPAction", (), {})
sys.modules["forge.events.action.mcp"] = mcp_module


# forge.runtime.utils ---------------------------------------------------------
class _RuntimeUtilsModule(types.ModuleType):
    __path__: list[str]
    find_available_tcp_port: Callable[[int, int], int]
    find_available_port_with_lock: Callable[..., tuple[int, Any]]


runtime_utils_module = _RuntimeUtilsModule("forge.runtime.utils")
runtime_utils_module.__path__ = []


def find_available_tcp_port(min_port: int, max_port: int) -> int:
    return min_port


def find_available_port_with_lock(
    *,
    min_port: int,
    max_port: int,
    max_attempts: int,
    bind_address: str,
    lock_timeout: float,
):
    return (_next_port(), PortLockStub())


runtime_utils_module.find_available_tcp_port = find_available_tcp_port
runtime_utils_module.find_available_port_with_lock = find_available_port_with_lock
sys.modules["forge.runtime.utils"] = runtime_utils_module


class _RuntimeUtilsSystemModule(types.ModuleType):
    check_port_available: Callable[[int, str], bool]
    find_available_tcp_port: Callable[[int, int], int]


utils_system_module = _RuntimeUtilsSystemModule("forge.runtime.utils.system")


def _check_port_available(port: int, host: str = "localhost") -> bool:
    del port, host
    return True


utils_system_module.check_port_available = _check_port_available
utils_system_module.find_available_tcp_port = find_available_tcp_port
sys.modules["forge.runtime.utils.system"] = utils_system_module


# forge.runtime.utils.port_lock -----------------------------------------------
class _PortLockModule(types.ModuleType):
    PortLock: type["PortLockStub"]
    find_available_port_with_lock: Callable[..., tuple[int, Any]]


port_lock_module = _PortLockModule("forge.runtime.utils.port_lock")


class PortLockStub:
    def __init__(self) -> None:
        self.released = False

    def release(self) -> None:
        self.released = True


port_lock_module.PortLock = PortLockStub
port_lock_module.find_available_port_with_lock = find_available_port_with_lock
sys.modules["forge.runtime.utils.port_lock"] = port_lock_module


# forge.runtime.utils.runtime_build -------------------------------------------
class _RuntimeBuildModule(types.ModuleType):
    build_runtime_image: Callable[..., str]


runtime_build_module = _RuntimeBuildModule("forge.runtime.utils.runtime_build")
runtime_build_module.build_runtime_image = lambda *a, **k: "forge/runtime:image"
sys.modules["forge.runtime.utils.runtime_build"] = runtime_build_module


# forge.runtime.utils.log_streamer --------------------------------------------
class _LogStreamerModule(types.ModuleType):
    LogStreamer: type["LogStreamerStub"]


log_streamer_module = _LogStreamerModule("forge.runtime.utils.log_streamer")


class LogStreamerStub:
    def __init__(self, container, log_func) -> None:
        self.container = container
        self.log_func = log_func


log_streamer_module.LogStreamer = LogStreamerStub
sys.modules["forge.runtime.utils.log_streamer"] = log_streamer_module


# forge.runtime.impl.docker.containers ----------------------------------------
class _ContainersModule(types.ModuleType):
    stop_all_containers: Callable[[str], None]


containers_module = _ContainersModule("forge.runtime.impl.docker.containers")
STOP_CALLS: list[str] = []


def _stop_all_containers(prefix: str) -> None:
    STOP_CALLS.append(prefix)


containers_module.stop_all_containers = _stop_all_containers
sys.modules["forge.runtime.impl.docker.containers"] = containers_module


# forge.utils.shutdown_listener -----------------------------------------------
class _ShutdownModule(types.ModuleType):
    add_shutdown_listener: Callable[[Callable[[], None]], str]
    should_continue: Callable[[], bool]


shutdown_module = _ShutdownModule("forge.utils.shutdown_listener")
SHUTDOWN_LISTENERS: list[Callable[[], None]] = []


def _add_shutdown_listener(callback: Callable[[], None]) -> str:
    SHUTDOWN_LISTENERS.append(callback)
    return f"listener-{len(SHUTDOWN_LISTENERS)}"


shutdown_module.add_shutdown_listener = _add_shutdown_listener
shutdown_module.should_continue = lambda: True
sys.modules["forge.utils.shutdown_listener"] = shutdown_module


# forge.utils.async_utils -----------------------------------------------------
class _AsyncUtilsModule(types.ModuleType):
    call_sync_from_async: Callable[..., Any]
    EXECUTOR: Any


async_utils_module = _AsyncUtilsModule("forge.utils.async_utils")


async def _call_sync_from_async(fn, *args, **kwargs):
    return fn(*args, **kwargs)


async_utils_module.call_sync_from_async = _call_sync_from_async
async_utils_module.EXECUTOR = types.SimpleNamespace(submit=lambda *a, **k: None)
sys.modules["forge.utils.async_utils"] = async_utils_module


# forge.utils.tenacity_metrics ------------------------------------------------
class _TenacityMetricsModule(types.ModuleType):
    tenacity_after_factory: Callable[[str], Callable[[Any], None]]
    tenacity_before_sleep_factory: Callable[[str], Callable[[Any], None]]
    call_tenacity_hooks: Callable[
        [Callable[[Any], None] | None, Callable[[Any], None] | None, Any], Any
    ]


metrics_module = _TenacityMetricsModule("forge.utils.tenacity_metrics")


def _tenacity_after_factory(operation: str) -> Callable[[Any], None]:
    return lambda state: None


def _tenacity_before_sleep_factory(operation: str) -> Callable[[Any], None]:
    return lambda state: None


def _call_tenacity_hooks(
    before: Callable[[Any], None] | None,
    after: Callable[[Any], None] | None,
    state: Any,
) -> None:
    if before:
        before(state)
    if after:
        after(state)


metrics_module.tenacity_after_factory = _tenacity_after_factory
metrics_module.tenacity_before_sleep_factory = _tenacity_before_sleep_factory
metrics_module.call_tenacity_hooks = _call_tenacity_hooks
sys.modules["forge.utils.tenacity_metrics"] = metrics_module


# forge.utils.tenacity_stop ---------------------------------------------------
class _TenacityStopModule(types.ModuleType):
    stop_if_should_exit: Callable[[], Callable[[Any], bool]]


tenacity_stop_module = _TenacityStopModule("forge.utils.tenacity_stop")
tenacity_stop_module.stop_if_should_exit = lambda: (lambda retry_state: False)
sys.modules["forge.utils.tenacity_stop"] = tenacity_stop_module


# forge.runtime.utils.request -------------------------------------------------
class _RequestModule(types.ModuleType):
    send_request: Callable[..., httpx.Response]


request_module = _RequestModule("forge.runtime.utils.request")
REQUEST_QUEUE: list[Any] = []


def send_request(session, method: str, url: str, **kwargs):
    if REQUEST_QUEUE:
        result = REQUEST_QUEUE.pop(0)
        if isinstance(result, Exception):
            raise result
        return result
    return httpx.Response(status_code=200, json={})


request_module.send_request = send_request
sys.modules["forge.runtime.utils.request"] = request_module


# forge.runtime.utils.command -------------------------------------------------
class _CommandModule(types.ModuleType):
    DEFAULT_MAIN_MODULE: str
    get_action_execution_server_startup_command: Callable[..., list[str]]


command_module = _CommandModule("forge.runtime.utils.command")
command_module.DEFAULT_MAIN_MODULE = "forge.runtime.action_execution_server"


def get_action_execution_server_startup_command(
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
    get_action_execution_server_startup_command
)
sys.modules["forge.runtime.utils.command"] = command_module

# Docker client stubs ---------------------------------------------------------


class DockerError(Exception):
    pass


class NotFound(DockerError):
    pass


class ContainerStub:
    def __init__(self, name: str = "container") -> None:
        self.name = name
        self.status = "running"
        self.ports: dict[str, Any] = {}
        self.attrs: dict[str, Any] = {"NetworkSettings": {"Networks": {}}}
        self.stopped = False
        self.started = False
        self.removed = False

    def reload(self) -> None:
        pass

    def stop(self) -> None:
        self.stopped = True

    def start(self) -> None:
        self.started = True

    def remove(self, force: bool = False) -> None:
        self.removed = True


class ContainersManager:
    def __init__(self) -> None:
        self._containers: list[ContainerStub] = []
        self.run_hook: Callable[..., ContainerStub] | None = None
        self.get_hook: Callable[[str], ContainerStub] | None = None

    def list(self) -> list[ContainerStub]:
        return list(self._containers)

    def run(self, *args, **kwargs) -> ContainerStub:
        container = (
            self.run_hook(*args, **kwargs)
            if self.run_hook
            else ContainerStub(kwargs.get("name", "container"))
        )
        self._containers.append(container)
        return container

    def get(self, name: str) -> ContainerStub:
        if self.get_hook:
            return self.get_hook(name)
        for container in self._containers:
            if container.name == name:
                return container
        raise NotFound(name)


class NetworkStub:
    def __init__(self, name: str) -> None:
        self.name = name
        self.connected: list[ContainerStub] = []

    def connect(self, container: ContainerStub) -> None:
        self.connected.append(container)


class NetworksManager:
    def __init__(self) -> None:
        self._store: dict[str, NetworkStub] = {}

    def get(self, name: str) -> NetworkStub:
        return self._store.setdefault(name, NetworkStub(name))


class DockerClientStub:
    def __init__(self) -> None:
        self.containers = ContainersManager()
        self.networks = NetworksManager()

    def version(self) -> dict[str, Any]:
        return {
            "ApiVersion": "1.43",
            "Version": "25.0.0",
            "Components": [{"Name": "Docker Engine"}],
        }

    def close(self) -> None:
        return None


# docker.types stub
class _DockerTypesModule(types.ModuleType):
    DriverConfig: Callable[[str, dict[str, Any]], Any]
    Mount: Callable[..., Any]
    DeviceRequest: Callable[..., Any]


DockerTypesModule = _DockerTypesModule("docker.types")
DockerTypesModule.DriverConfig = lambda name, options: types.SimpleNamespace(
    name=name, options=options
)
DockerTypesModule.Mount = lambda **kwargs: types.SimpleNamespace(**kwargs)
DockerTypesModule.DeviceRequest = lambda **kwargs: types.SimpleNamespace(**kwargs)
sys.modules["docker.types"] = DockerTypesModule


def docker_from_env() -> DockerClientStub:
    return DockerClientStub()


class _DockerModule(types.ModuleType):
    from_env: Callable[[], DockerClientStub]
    DockerClient: type[DockerClientStub]
    errors: Any
    types: _DockerTypesModule


docker_module = _DockerModule("docker")
docker_module.from_env = docker_from_env
docker_module.DockerClient = DockerClientStub
docker_module.errors = types.SimpleNamespace(
    NotFound=NotFound, DockerException=DockerError
)
docker_module.types = DockerTypesModule
dock_errors = docker_module.errors
dock_errors.APIError = DockerError
sys.modules["docker"] = docker_module


# ActionExecutionClient stub --------------------------------------------------
class _ActionExecutionModule(types.ModuleType):
    ActionExecutionClient: type["ActionExecutionClientStub"]


action_exec_module = _ActionExecutionModule(
    "forge.runtime.impl.action_execution.action_execution_client"
)


class _Semaphore:
    def __enter__(self):
        return None

    def __exit__(self, exc_type, exc, tb):
        return False


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
        self.plugins = list(plugins or [])
        self.attach_to_existing = attach_to_existing
        self.initial_env_vars = dict(env_vars or {})
        self.session = types.SimpleNamespace(headers={})
        self.action_semaphore = _Semaphore()
        self._runtime_closed = False
        self._last_status = None
        self._vscode_enabled = True
        self._alive_checks = 0

    def set_runtime_status(self, status) -> None:
        self._last_status = status

    def log(self, level: str, message: str, exc_info: bool | None = None) -> None:
        pass

    def setup_initial_env(self) -> None:
        return None

    def get_vscode_token(self) -> str | None:
        return "token"

    def wait_until_alive(self) -> None:
        return None

    def close(self) -> None:
        self._runtime_closed = True

    def check_if_alive(self) -> None:
        self._alive_checks += 1

    def _send_action_server_request(
        self, method: str, url: str, **kwargs
    ):  # pragma: no cover - unused in tests
        return types.SimpleNamespace(json=lambda: {})


action_exec_module.ActionExecutionClient = ActionExecutionClientStub
sys.modules["forge.runtime.impl.action_execution.action_execution_client"] = (
    action_exec_module
)
sys.modules.setdefault(
    "forge.runtime.impl.action_execution",
    types.ModuleType("forge.runtime.impl.action_execution"),
)

###############################################################################
# Import DockerRuntime with stubs in place
###############################################################################

spec = importlib.util.spec_from_file_location(
    "forge.runtime.impl.docker.docker_runtime",
    ROOT_DIR / "forge" / "runtime" / "impl" / "docker" / "docker_runtime.py",
)
if spec is None or spec.loader is None:
    raise RuntimeError("Failed to load docker runtime module spec")

DockerRuntimeModule = importlib.util.module_from_spec(spec)
sys.modules["forge.runtime.impl.docker.docker_runtime"] = DockerRuntimeModule
spec.loader.exec_module(DockerRuntimeModule)
DockerRuntime = DockerRuntimeModule.DockerRuntime
setattr(
    DockerRuntimeModule, "call_sync_from_async", async_utils_module.call_sync_from_async
)
if not hasattr(DockerRuntimeModule, "DEBUG_RUNTIME"):
    setattr(DockerRuntimeModule, "DEBUG_RUNTIME", False)

###############################################################################
# Fixtures
###############################################################################


@pytest.fixture(autouse=True)
def reset_state(monkeypatch):
    global PORT_SEQUENCE
    PORT_SEQUENCE = [31000, 36000, 41000, 46000, 51000, 56000]
    STOP_CALLS.clear()
    SHUTDOWN_LISTENERS.clear()
    DockerRuntime._shutdown_listener_id = None
    if hasattr(DockerRuntime._init_docker_client, "cache_clear"):
        DockerRuntime._init_docker_client.cache_clear()
    monkeypatch.delenv("DOCKER_HOST_ADDR", raising=False)
    monkeypatch.delenv("SANDBOX_VOLUME_OVERLAYS", raising=False)
    yield
    if hasattr(DockerRuntime._init_docker_client, "cache_clear"):
        DockerRuntime._init_docker_client.cache_clear()


@pytest.fixture
def config(tmp_path):
    sandbox = types.SimpleNamespace(
        local_runtime_url="http://localhost",
        runtime_startup_env_vars={"BASE": "1"},
        runtime_container_image="runtime:image",
        base_container_image="base:image",
        platform="linux/amd64",
        runtime_extra_build_args={},
        force_rebuild_runtime=False,
        runtime_extra_deps=[],
        runtime_binding_address=None,
        use_host_network=False,
        additional_networks=[],
        volumes=None,
        workspace_mount_path=None,
        workspace_mount_path_in_sandbox="/workspace",
        vscode_port=None,
        enable_gpu=False,
        cuda_visible_devices=None,
        docker_runtime_kwargs={},
        rm_all_containers=False,
        keep_runtime_alive=False,
        runtime_extra_args={},
        user_id=None,
    )
    cfg = types.SimpleNamespace(
        sandbox=sandbox,
        workspace_base=None,
        workspace_mount_path=str(tmp_path / "workspace"),
        workspace_mount_path_in_sandbox="/workspace",
        enable_browser=False,
        debug=False,
    )
    return cfg


def make_response(status: int, data: dict) -> httpx.Response:
    return httpx.Response(status_code=status, json=data)


###############################################################################
# Tests
###############################################################################


def test_retryable_error_recursion():
    inner_error = httpx.ConnectTimeout("timeout")

    class FakeRetryError(tenacity.RetryError):
        def __init__(self, exc: BaseException) -> None:
            future = tenacity.Future(attempt_number=1)  # type: ignore[call-arg]
            future.set_exception(exc)
            self.last_attempt = future

    wrapped = FakeRetryError(inner_error)
    assert DockerRuntimeModule._is_retryablewait_until_alive_error(inner_error) is True
    assert DockerRuntimeModule._is_retryablewait_until_alive_error(wrapped) is True
    assert (
        DockerRuntimeModule._is_retryablewait_until_alive_error(ValueError("boom"))
        is False
    )


def test_init_registers_shutdown_listener(monkeypatch, config):
    monkeypatch.setenv("DOCKER_HOST_ADDR", "10.0.0.5")
    runtime = DockerRuntime(config, types.SimpleNamespace(), types.SimpleNamespace())
    assert DockerRuntime._shutdown_listener_id == "listener-1"
    assert runtime.config.sandbox.local_runtime_url == "http://10.0.0.5"


def test_select_container_ip_branches(config):
    runtime = DockerRuntime(config, types.SimpleNamespace(), types.SimpleNamespace())
    networks = {
        "forge-network": {"IPAddress": "172.20.0.2"},
        "bridge": {"IPAddress": "172.17.0.2"},
    }
    assert runtime._select_container_ip(networks) == "172.20.0.2"
    networks = {
        "custom": {"IPAddress": "10.1.0.5"},
        "bridge": {"IPAddress": "172.17.0.2"},
    }
    assert runtime._select_container_ip(networks) == "10.1.0.5"
    assert runtime._select_container_ip({}) is None


def test_allocate_ports_with_custom_vscode(config):
    config.sandbox.vscode_port = 2222
    runtime = DockerRuntime(config, types.SimpleNamespace(), types.SimpleNamespace())
    runtime._vscode_enabled = True
    runtime._find_available_port_with_lock = lambda rng, max_attempts=5: (
        1234,
        PortLockStub(),
    )
    runtime._allocate_ports()
    assert runtime._vscode_port == 2222


def test_find_available_port_with_lock_fallback(config):
    runtime = DockerRuntime(config, types.SimpleNamespace(), types.SimpleNamespace())
    runtime.docker_client.containers._containers.append(ContainerStub(name="existing"))
    runtime._is_port_in_use_docker = lambda port: True if port == 30000 else False
    runtime._find_available_port_with_lock = (
        DockerRuntime._find_available_port_with_lock.__get__(runtime)
    )
    port, lock = runtime._find_available_port_with_lock((30000, 30005), max_attempts=2)
    assert port >= 30000


def test_configure_network_modes(config):
    runtime = DockerRuntime(config, types.SimpleNamespace(), types.SimpleNamespace())
    runtime._container_port = 31000
    runtime._host_port = 32000
    runtime._vscode_port = 33000
    runtime._app_ports = [34000, 35000]
    runtime._vscode_enabled = True
    mode, mapping = runtime._configure_network_and_ports()
    assert mode is None
    assert mapping[f"{runtime._container_port}/tcp"] == ("0.0.0.0", runtime._host_port)

    config.sandbox.use_host_network = True
    runtime = DockerRuntime(config, types.SimpleNamespace(), types.SimpleNamespace())
    mode, mapping = runtime._configure_network_and_ports()
    assert mode == "host"
    assert mapping is None


def test_build_container_environment(config):
    config.debug = True
    config.sandbox.runtime_startup_env_vars = {"EXTRA": "VALUE"}
    runtime = DockerRuntime(config, types.SimpleNamespace(), types.SimpleNamespace())
    runtime._container_port = 32000
    runtime._vscode_port = 33000
    runtime._app_ports = [34000, 35000]
    env = runtime._build_container_environment()
    assert env["port"] == "32000"
    assert env["EXTRA"] == "VALUE"
    assert env["DEBUG"] == "true"


def test_gpu_device_requests(config):
    runtime = DockerRuntime(config, types.SimpleNamespace(), types.SimpleNamespace())
    assert runtime._get_gpu_device_requests() is None

    config.sandbox.enable_gpu = True
    runtime = DockerRuntime(config, types.SimpleNamespace(), types.SimpleNamespace())
    assert runtime._get_gpu_device_requests()[0].count == -1

    config.sandbox.cuda_visible_devices = "0,1"
    runtime = DockerRuntime(config, types.SimpleNamespace(), types.SimpleNamespace())
    assert runtime._get_gpu_device_requests()[0].device_ids == ["0", "1"]


def test_maybe_build_runtime_container_image(config, monkeypatch):
    config.sandbox.runtime_container_image = None
    runtime = DockerRuntime(config, types.SimpleNamespace(), types.SimpleNamespace())
    calls = {"count": 0}

    def build(*args, **kwargs):
        calls["count"] += 1
        return "built:image"

    monkeypatch.setattr(runtime_build_module, "build_runtime_image", build)
    monkeypatch.setattr(DockerRuntimeModule, "build_runtime_image", build)
    runtime.maybe_build_runtime_container_image()
    assert runtime.runtime_container_image == "built:image"
    assert calls["count"] == 1

    config.sandbox.runtime_container_image = None
    config.sandbox.base_container_image = None
    runtime = DockerRuntime(config, types.SimpleNamespace(), types.SimpleNamespace())
    with pytest.raises(ValueError):
        runtime.maybe_build_runtime_container_image()

    config.sandbox.base_container_image = "base:image"
    runtime = DockerRuntime(config, types.SimpleNamespace(), types.SimpleNamespace())

    def raise_error(*a, **k):
        raise RuntimeError("build fail")

    monkeypatch.setattr(runtime_build_module, "build_runtime_image", raise_error)
    monkeypatch.setattr(DockerRuntimeModule, "build_runtime_image", raise_error)
    with pytest.raises(RuntimeError):
        runtime.maybe_build_runtime_container_image()
    assert runtime._last_status == DockerRuntimeModule.RuntimeStatus.ERROR


def test_process_overlay_mounts(tmp_path, config, monkeypatch):
    base = tmp_path / "overlay"
    monkeypatch.setenv("SANDBOX_VOLUME_OVERLAYS", str(base))
    host_spec = r"\\\\localhost\\forge-overlay"
    config.sandbox.volumes = f"{host_spec}:/container:overlay"
    runtime = DockerRuntime(config, types.SimpleNamespace(), types.SimpleNamespace())
    mounts = runtime._process_overlay_mounts()
    assert mounts


def test_web_hosts_and_vscode_url(config, monkeypatch):
    monkeypatch.setenv("DOCKER_HOST_ADDR", "192.0.2.1")
    runtime = DockerRuntime(config, types.SimpleNamespace(), types.SimpleNamespace())
    runtime._app_ports = [40000, 50000]
    hosts = runtime.web_hosts
    assert list(hosts.keys())[0].startswith("http://192.0.2.1")
    runtime._vscode_port = 1234
    assert runtime.vscode_url.endswith("folder=/workspace")


def test_pause_resume_errors(config):
    runtime = DockerRuntime(config, types.SimpleNamespace(), types.SimpleNamespace())
    runtime.container = None
    with pytest.raises(RuntimeError):
        runtime.pause()
    with pytest.raises(RuntimeError):
        runtime.resume()


@pytest.mark.asyncio
async def test_handle_container_attachment_attach(config):
    runtime = DockerRuntime(
        config,
        types.SimpleNamespace(),
        types.SimpleNamespace(),
        attach_to_existing=True,
    )
    runtime.container = ContainerStub("existing")
    runtime.docker_client.containers._containers.append(runtime.container)

    def attach():
        return None

    runtime._attach_to_container = attach
    await runtime._handle_container_attachment()
    assert runtime.container is not None


@pytest.mark.asyncio
async def test_handle_container_attachment_not_found(monkeypatch, config):
    runtime = DockerRuntime(config, types.SimpleNamespace(), types.SimpleNamespace())

    def attach():
        raise NotFound("missing")

    runtime._attach_to_container = attach
    flags: dict[str, bool] = {"built": False, "init": False}

    def mark_built() -> None:
        flags["built"] = True

    runtime.maybe_build_runtime_container_image = mark_built

    container = ContainerStub("new")
    container.attrs["NetworkSettings"]["Networks"] = {
        "forge-network": {"IPAddress": "172.20.0.2"}
    }

    def mark_init() -> None:
        flags["init"] = True
        runtime._container_port = 31000
        runtime.container = container

    runtime.init_container = mark_init
    monkeypatch.setattr("time.sleep", lambda _: None)

    await runtime._handle_container_attachment()
    assert flags["built"] and flags["init"]
    assert runtime.api_url == "http://172.20.0.2:31000"


@pytest.mark.asyncio
async def test_wait_for_runtime_ready(config):
    runtime = DockerRuntime(config, types.SimpleNamespace(), types.SimpleNamespace())
    called = {"setup": False}
    runtime.wait_until_alive = lambda: None
    runtime.setup_initial_env = lambda: called.__setitem__("setup", True)
    await runtime._wait_for_runtime_ready()
    assert called["setup"] is True


@pytest.mark.asyncio
async def test_delete_success(monkeypatch, config):
    client = DockerClientStub()
    container = ContainerStub("Forge-runtime-test")
    client.containers._containers.append(container)
    monkeypatch.setattr(
        DockerRuntime, "_init_docker_client", staticmethod(lambda: client)
    )
    await DockerRuntime.delete("test")
    assert container.removed is True


@pytest.mark.asyncio
async def test_delete_not_found(monkeypatch):
    client = DockerClientStub()
    client.containers.get_hook = lambda name: (_ for _ in ()).throw(NotFound(name))
    monkeypatch.setattr(
        DockerRuntime, "_init_docker_client", staticmethod(lambda: client)
    )
    await DockerRuntime.delete("missing")


def test_init_container_starts_container(config):
    config.sandbox.workspace_mount_path_in_sandbox = "/mnt/workspace"
    runtime = DockerRuntime(config, types.SimpleNamespace(), types.SimpleNamespace())

    runtime._allocate_ports = lambda: (
        runtime.__setattr__("_host_port", 31000),
        runtime.__setattr__("_container_port", 31000),
        runtime.__setattr__("_vscode_port", 32000),
        runtime.__setattr__("_app_ports", [33000, 34000]),
    )
    runtime._configure_network_and_ports = lambda: (
        "bridge",
        {"31000/tcp": ("0.0.0.0", 31000)},
    )
    runtime._build_container_environment = lambda: {"port": "31000"}
    runtime._process_volumes = lambda: {}
    runtime.get_action_execution_server_startup_command = lambda: [
        "python",
        "-m",
        "server",
        "--port",
        "31000",
    ]
    runtime._process_overlay_mounts = lambda: ["overlay"]
    runtime._get_gpu_device_requests = lambda: ["gpu"]

    captured: dict[str, Any] = {}

    def run_hook(image, **kwargs):
        captured["image"] = image
        captured["kwargs"] = kwargs
        return ContainerStub("runtime-container")

    runtime.docker_client.containers.run_hook = run_hook
    runtime.init_container()

    assert captured["image"] == "runtime:image"
    assert captured["kwargs"]["mounts"] == ["overlay"]
    assert runtime.container.name == "runtime-container"
    assert runtime._last_status == DockerRuntimeModule.RuntimeStatus.RUNTIME_STARTED


def test_init_container_failure_calls_close(config):
    runtime = DockerRuntime(config, types.SimpleNamespace(), types.SimpleNamespace())
    runtime.runtime_container_image = None
    runtime._allocate_ports = lambda: None
    runtime._configure_network_and_ports = lambda: ("bridge", {})
    runtime._build_container_environment = lambda: {}
    runtime._process_volumes = lambda: {}
    runtime.get_action_execution_server_startup_command = lambda: []
    runtime._process_overlay_mounts = lambda: []
    runtime._get_gpu_device_requests = lambda: None

    closed = {"called": False}
    runtime.close = lambda: closed.__setitem__("called", True)

    with pytest.raises(ValueError):
        runtime.init_container()

    assert closed["called"] is True


def test_validate_container_status(config):
    runtime = DockerRuntime(config, types.SimpleNamespace(), types.SimpleNamespace())
    container = ContainerStub("exited")
    container.status = "exited"
    with pytest.raises(docker_module.errors.NotFound):
        runtime._validate_container_status(container)
    assert container.removed is True

    container = ContainerStub("paused")
    container.status = "paused"
    with pytest.raises(docker_module.errors.NotFound):
        runtime._validate_container_status(container)


def test_extract_port_config(config):
    runtime = DockerRuntime(config, types.SimpleNamespace(), types.SimpleNamespace())
    cfg = {
        "Env": ["port=1234", "VSCODE_PORT=5678", "OTHER=1"],
        "ExposedPorts": {"1234/tcp": {}, "4321/tcp": {}, "5678/tcp": {}},
    }
    runtime._extract_port_config(cfg)
    assert runtime._host_port == 1234
    assert runtime._container_port == 1234
    assert runtime._vscode_port == 5678
    assert runtime._app_ports == [4321]


def test_setup_api_url_from_container_variants(config):
    runtime = DockerRuntime(config, types.SimpleNamespace(), types.SimpleNamespace())
    runtime._container_port = 31000
    container = ContainerStub("runtime")
    container.attrs["NetworkSettings"]["Networks"] = {
        "forge": {"IPAddress": "172.20.0.5"}
    }
    runtime._setup_api_url_from_container(container)
    assert runtime.api_url == "http://172.20.0.5:31000"

    container.attrs["NetworkSettings"]["Networks"] = {}
    runtime._setup_api_url_from_container(container)
    assert (
        runtime.api_url
        == f"{runtime.config.sandbox.local_runtime_url}:{runtime._container_port}"
    )

    runtime.config.sandbox.use_host_network = True
    runtime._setup_api_url_from_container(container)
    assert (
        runtime.api_url
        == f"{runtime.config.sandbox.local_runtime_url}:{runtime._container_port}"
    )


def test_attach_to_container_invokes_helpers(config):
    runtime = DockerRuntime(config, types.SimpleNamespace(), types.SimpleNamespace())
    container = ContainerStub("attached")
    container.attrs["Config"] = {"Env": ["port=1234"], "ExposedPorts": {}}
    runtime.docker_client.containers.get_hook = lambda name: container

    calls = {"validate": 0, "extract": 0, "setup": 0}

    def _mark_validate(container: ContainerStub) -> None:
        del container
        calls["validate"] += 1

    def _mark_extract(config_dict: dict[str, Any]) -> None:
        del config_dict
        calls["extract"] += 1

    def _mark_setup(container: ContainerStub) -> None:
        del container
        calls["setup"] += 1

    runtime._validate_container_status = _mark_validate
    runtime._extract_port_config = _mark_extract
    runtime._setup_api_url_from_container = _mark_setup

    runtime._attach_to_container()
    assert runtime.container is container
    assert calls == {"validate": 1, "extract": 1, "setup": 1}


def test_wait_until_alive_success_and_errors(config):
    runtime = DockerRuntime(config, types.SimpleNamespace(), types.SimpleNamespace())
    runtime.docker_client.containers.get_hook = lambda name: ContainerStub("runtime")
    runtime.wait_until_alive()
    assert runtime._alive_checks == 1

    container = ContainerStub("exited")
    container.status = "exited"
    runtime.docker_client.containers.get_hook = lambda name: container
    with pytest.raises(DockerRuntimeModule.AgentRuntimeDisconnectedError):
        runtime.wait_until_alive()

    runtime.docker_client.containers.get_hook = lambda name: (_ for _ in ()).throw(
        docker_module.errors.NotFound(name)
    )
    with pytest.raises(DockerRuntimeModule.AgentRuntimeNotFoundError):
        runtime.wait_until_alive()


def test_close_releases_resources(config):
    runtime = DockerRuntime(config, types.SimpleNamespace(), types.SimpleNamespace())
    close_calls: list[bool] = []
    runtime.log_streamer = types.SimpleNamespace(close=lambda: close_calls.append(True))
    host_lock = PortLockStub()
    vscode_lock = PortLockStub()
    app_lock = PortLockStub()
    runtime._host_port_lock = host_lock
    runtime._vscode_port_lock = vscode_lock
    runtime._app_port_locks = [app_lock]
    runtime._app_ports = [40000]
    STOP_CALLS.clear()

    runtime.close()

    assert close_calls == [True]
    assert STOP_CALLS[-1] == runtime.container_name
    assert host_lock.released and vscode_lock.released and app_lock.released


def test_close_skips_when_keep_alive_or_attach(config):
    STOP_CALLS.clear()
    runtime = DockerRuntime(config, types.SimpleNamespace(), types.SimpleNamespace())
    runtime.config.sandbox.keep_runtime_alive = True
    runtime.close()
    assert STOP_CALLS == []

    STOP_CALLS.clear()
    runtime = DockerRuntime(
        config,
        types.SimpleNamespace(),
        types.SimpleNamespace(),
        attach_to_existing=True,
    )
    runtime.close()
    assert STOP_CALLS == []


@pytest.mark.asyncio
async def test_handle_container_attachment_existing_missing(config):
    runtime = DockerRuntime(
        config,
        types.SimpleNamespace(),
        types.SimpleNamespace(),
        attach_to_existing=True,
    )

    def raise_not_found():
        raise docker_module.errors.NotFound("missing")

    runtime._attach_to_container = raise_not_found
    with pytest.raises(DockerRuntimeModule.AgentRuntimeDisconnectedError):
        await runtime._handle_container_attachment()


@pytest.mark.asyncio
async def test_connect_flow(config):
    runtime = DockerRuntime(config, types.SimpleNamespace(), types.SimpleNamespace())
    steps: list[str] = []

    async def fake_attach():
        steps.append("attach")

    async def fake_wait():
        steps.append("wait_ready")

    runtime._handle_container_attachment = fake_attach
    runtime._setup_log_streamer = lambda: steps.append("log_streamer")
    runtime._wait_for_runtime_ready = fake_wait
    runtime._log_initialization_info = lambda: steps.append("log_info")
    runtime._connect_to_additional_networks = lambda: steps.append("extra_net")
    statuses: list[Any] = []
    runtime.set_runtime_status = lambda status: statuses.append(status)
    runtime.log = lambda *a, **k: steps.append("log")

    await runtime.connect()

    assert steps[:2] == ["attach", "log_streamer"]
    assert "log_info" in steps and "extra_net" in steps
    assert runtime._runtime_initialized is True
    assert statuses[0] == DockerRuntimeModule.RuntimeStatus.STARTING_RUNTIME
    assert statuses[-1] == DockerRuntimeModule.RuntimeStatus.READY


@pytest.mark.asyncio
async def test_connect_warm_start(config):
    runtime = DockerRuntime(
        config,
        types.SimpleNamespace(),
        types.SimpleNamespace(),
        attach_to_existing=True,
    )

    async def noop_attach():
        return None

    async def noop_wait():
        return None

    runtime._handle_container_attachment = noop_attach
    runtime._setup_log_streamer = lambda: None
    runtime._wait_for_runtime_ready = noop_wait
    runtime._log_initialization_info = lambda: None
    runtime._connect_to_additional_networks = lambda: None
    statuses: list[Any] = []
    runtime.set_runtime_status = lambda status: statuses.append(status)
    runtime.log = lambda *a, **k: None

    await runtime.connect()

    assert statuses == [DockerRuntimeModule.RuntimeStatus.STARTING_RUNTIME]


def test_setup_log_streamer_variants(config):
    runtime = DockerRuntime(config, types.SimpleNamespace(), types.SimpleNamespace())
    runtime.container = ContainerStub("runtime")
    original_flag = getattr(DockerRuntimeModule, "DEBUG_RUNTIME", False)
    try:
        setattr(DockerRuntimeModule, "DEBUG_RUNTIME", True)
        runtime._setup_log_streamer()
        assert isinstance(runtime.log_streamer, LogStreamerStub)

        setattr(DockerRuntimeModule, "DEBUG_RUNTIME", False)
        runtime._setup_log_streamer()
        assert runtime.log_streamer is None
    finally:
        setattr(DockerRuntimeModule, "DEBUG_RUNTIME", original_flag)


def test_connect_to_additional_networks(config):
    runtime = DockerRuntime(config, types.SimpleNamespace(), types.SimpleNamespace())
    runtime.container = ContainerStub("runtime")
    runtime.config.sandbox.additional_networks = ["good", "bad"]

    class GoodNetwork:
        def __init__(self) -> None:
            self.connected: list[Any] = []

        def connect(self, container) -> None:
            self.connected.append(container)

    good_network = GoodNetwork()

    def get_network(name: str):
        if name == "good":
            return good_network
        raise RuntimeError("missing")

    runtime.docker_client.networks.get = get_network
    logs: list[tuple[str, str]] = []
    runtime.log = lambda level, message, *args: logs.append((level, message))

    runtime._connect_to_additional_networks()

    assert good_network.connected == [runtime.container]
    assert any("Failed to connect" in message for _, message in logs)


def test_process_volumes_variants(config):
    config.sandbox.volumes = "volume:named:/named:rw,relative:/rel:ro"
    runtime = DockerRuntime(config, types.SimpleNamespace(), types.SimpleNamespace())
    volumes = runtime._process_volumes()
    assert volumes["volume"]["bind"] == "relative" or "volume" in volumes
    assert volumes["relative"]["bind"] == "/rel"


def test_process_overlay_mounts_conditions(monkeypatch, config):
    runtime = DockerRuntime(config, types.SimpleNamespace(), types.SimpleNamespace())
    config.sandbox.volumes = None
    monkeypatch.delenv("SANDBOX_VOLUME_OVERLAYS", raising=False)
    assert runtime._process_overlay_mounts() == []

    config.sandbox.volumes = "relative:/container:overlay"
    monkeypatch.delenv("SANDBOX_VOLUME_OVERLAYS", raising=False)
    assert runtime._process_overlay_mounts() == []


def test_is_port_in_use_docker(config):
    runtime = DockerRuntime(config, types.SimpleNamespace(), types.SimpleNamespace())
    container = ContainerStub("ports")
    container.ports = {"1234/tcp": [{"HostPort": "1234"}]}
    runtime.docker_client.containers._containers.append(container)
    assert runtime._is_port_in_use_docker(1234) is True
    assert runtime._is_port_in_use_docker(9999) is False


def test_find_available_port_with_lock_retries(monkeypatch, config):
    runtime = DockerRuntime(config, types.SimpleNamespace(), types.SimpleNamespace())

    locks = [PortLockStub(), None]

    def fake_find_available_port_with_lock(
        *, min_port, max_port, max_attempts, bind_address, lock_timeout
    ):
        lock = locks.pop(0)
        if lock is None:
            return (min_port + 2, None)
        return (min_port + 1, lock)

    monkeypatch.setattr(
        DockerRuntimeModule,
        "find_available_port_with_lock",
        fake_find_available_port_with_lock,
    )
    runtime._is_port_in_use_docker = lambda port: port == 30001

    port, lock = runtime._find_available_port_with_lock((30000, 30010), max_attempts=2)
    assert port == 30002
    assert lock is None


def test_log_initialization_info(config):
    runtime = DockerRuntime(config, types.SimpleNamespace(), types.SimpleNamespace())
    runtime.plugins = [
        types.SimpleNamespace(name="plugin1"),
        types.SimpleNamespace(name="plugin2"),
    ]
    messages: list[str] = []
    runtime.log = lambda level, message: messages.append(message)
    runtime._log_initialization_info()
    assert "plugin1" in messages[0] and "plugin2" in messages[0]
