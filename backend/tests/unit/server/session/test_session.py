"""Unit tests for `forge.server.session.session.Session`."""

from __future__ import annotations

import asyncio
import contextlib
from types import MappingProxyType, SimpleNamespace
from typing import Any, Mapping

import pytest
from pydantic import SecretStr

from forge.core.exceptions import MicroagentValidationError
from forge.core.schemas import AgentState
from forge.events.action import MessageAction, NullAction
from forge.events.event import EventSource
from forge.events.observation import (
    AgentStateChangedObservation,
    CmdOutputObservation,
    NullObservation,
)
from forge.events.observation.agent import RecallObservation
from forge.events.observation.error import ErrorObservation
from forge.events.serialization import event_to_dict
from forge.integrations.provider import CustomSecret, ProviderToken, ProviderType
from forge.llm.llm_registry import LLMRegistry
from forge.runtime.runtime_status import RuntimeStatus
from forge.server.constants import ROOM_KEY
import forge.core.config.condenser_config as condenser_config_module
import forge.experiments.experiment_manager as experiment_manager_module
import forge.metasop.router as metasop_router_module
from forge.server.session import session as session_module
from forge.server.session.conversation_init_data import ConversationInitData
from forge.server.session.session import Session
from forge.server.services.conversation_stats import ConversationStats
from forge.storage.data_models.settings import Settings
from forge.storage.data_models.user_secrets import UserSecrets
from forge.storage.files import FileStore
from forge.storage.memory import InMemoryFileStore
from forge.storage.secrets.secrets_store import SecretsStore
from forge.storage.settings.settings_store import SettingsStore


class DummyEventStream:
    def __init__(self):
        self.events: list[tuple[object, EventSource]] = []
        self.subscriptions: list[tuple] = []

    def subscribe(self, *args):
        self.subscriptions.append(args)

    def add_event(self, event, source):
        self.events.append((event, source))


class DummyController:
    def __init__(self, vision_disabled: bool = False, vision_active: bool = True):
        self.saved_states: list[AgentState] = []
        self.agent = SimpleNamespace(
            llm=SimpleNamespace(
                config=SimpleNamespace(
                    disable_vision=vision_disabled, base_url="url", model="model"
                ),
                vision_is_active=lambda: vision_active,
            )
        )

    async def close(self):
        pass

    async def set_agent_state_to(self, state):
        self.saved_states.append(state)

    def save_state(self):
        pass


class DummyAgentSession:
    def __init__(
        self,
        sid,
        file_store,
        llm_registry,
        conversation_stats,
        status_callback,
        user_id=None,
    ):
        self.sid = sid
        self.file_store = file_store
        self.llm_registry = llm_registry
        self.conversation_stats = conversation_stats
        self.status_callback = status_callback
        self.user_id = user_id
        self.event_stream = DummyEventStream()
        self.controller = DummyController()
        self.closed = False
        self.start_calls: list[dict] = []

    async def start(self, **kwargs):
        self.start_calls.append(kwargs)

    async def close(self):
        self.closed = True

    def is_closed(self):
        return self.closed


class DummyMCP:
    def __init__(self):
        self.shttp_servers: list[str] = []
        self.stdio_servers: list[str] = []
        self.other: object | None = None

    def merge(self, other):
        merged = DummyMCP()
        merged.shttp_servers = self.shttp_servers + ["merged_http"]
        merged.stdio_servers = self.stdio_servers + ["merged_stdio"]
        merged.other = other
        return merged


class DummyConfig:
    def __init__(self):
        self.runtime = "dummy_runtime"
        self.security = SimpleNamespace(
            confirmation_mode=True, security_analyzer="default"
        )
        self.sandbox = SimpleNamespace(
            base_container_image="base", runtime_container_image="runtime", api_key=None
        )
        self.git_user_name = "user"
        self.git_user_email = "user@example.com"
        self.mcp_host = "localhost"
        self.mcp = DummyMCP()
        self.default_agent = "DummyAgent"
        self.max_iterations = 5
        self.max_budget_per_task = 100.0

    def get_agent_config(self, agent_cls):
        return SimpleNamespace(condenser=None)

    def get_llm_config_from_agent(self, agent_name):
        return SimpleNamespace(
            model="model",
            base_url="url",
            disable_vision=False,
            vision_is_active=lambda: True,
            log_completions=False,
            api_version="2023-08-01",
            api_type="openai",
            log_completions_folder=None,
            top_k=None,
            top_p=None,
            temperature=0.7,
            max_output_tokens=1024,
            custom_tokenizer=None,
            reasoning_effort=None,
            safety_settings=None,
            aws_region_name=None,
            aws_access_key_id=None,
            aws_secret_access_key=None,
            enable_prompt_caching=False,
            api_key=None,
            timeout=30,
            drop_params=None,
            seed=None,
            custom_llm_provider=None,
            num_retries=0,
            retry_min_wait=1,
            retry_max_wait=30,
            retry_multiplier=2,
        )

    def get_llm_config_from_agent_config(self, agent_config):
        del agent_config
        return SimpleNamespace(
            model="model",
            base_url="url",
            log_completions=False,
            api_version="2023-08-01",
            api_type="openai",
            log_completions_folder=None,
            top_k=None,
            top_p=None,
            temperature=0.7,
            max_output_tokens=1024,
            custom_tokenizer=None,
            reasoning_effort=None,
            safety_settings=None,
            aws_region_name=None,
            aws_access_key_id=None,
            aws_secret_access_key=None,
            enable_prompt_caching=False,
            api_key=None,
            timeout=30,
            drop_params=None,
            seed=None,
            custom_llm_provider=None,
            num_retries=0,
            retry_min_wait=1,
            retry_max_wait=30,
            retry_multiplier=2,
        )

    def get_agent_to_llm_config_map(self):
        return {"DummyAgent": "llm"}

    def get_agent_configs(self):
        return {"DummyAgent": {}}


class DummySIO:
    def __init__(self):
        self.emitted: list[tuple[str, dict, str | None]] = []
        self.manager = SimpleNamespace(rooms={"/": {}})

    async def emit(self, event, data, to=None):
        self.emitted.append((event, data, to))


class DummyAgent:
    def __init__(self, agent_config, llm_registry):
        self.config = agent_config
        self.llm_registry = llm_registry
        self.llm = SimpleNamespace(
            config=SimpleNamespace(disable_vision=False, base_url="url", model="model"),
            vision_is_active=lambda: True,
        )
        self.sandbox_plugins = []


def _provider_tokens(
    token: str = "token",
) -> MappingProxyType[ProviderType, ProviderToken]:
    return MappingProxyType(
        {ProviderType.GITHUB: ProviderToken(token=SecretStr(token), host="github.com")}
    )


def _custom_secrets(secret_value: str = "value") -> MappingProxyType[str, CustomSecret]:
    return MappingProxyType(
        {"secret": CustomSecret(secret=SecretStr(secret_value), description="test")}
    )


class DummySettingsStore(SettingsStore):
    def __init__(self) -> None:
        self.saved: list[Settings] = []
        self.to_return: Settings | None = None

    async def load(self) -> Settings | None:
        return self.to_return

    async def store(self, settings: Settings) -> None:
        self.saved.append(settings)

    @classmethod
    async def get_instance(cls, config: Any, user_id: str | None) -> SettingsStore:
        return cls()


class DummySecretsStore(SecretsStore):
    def __init__(self) -> None:
        self.saved: list[UserSecrets] = []
        self.to_return: UserSecrets | None = None

    async def load(self) -> UserSecrets | None:
        return self.to_return

    async def store(self, secrets: UserSecrets) -> None:
        self.saved.append(secrets)

    @classmethod
    async def get_instance(cls, config: Any, user_id: str | None) -> SecretsStore:
        return cls()


@pytest.fixture(autouse=True)
def patch_dependencies(monkeypatch):
    monkeypatch.setattr(session_module, "AgentSession", DummyAgentSession)

    class DummyExperimentManager:
        @staticmethod
        def run_config_variant_test(user_id, sid, config):
            return config

    monkeypatch.setattr(
        experiment_manager_module, "ExperimentManagerImpl", DummyExperimentManager
    )

    monkeypatch.setattr(
        session_module.ForgeMCPConfigImpl,
        "create_default_mcp_server_config",
        lambda host, config, user_id: ("default_http", ["stdio1", "stdio2"]),
    )

    monkeypatch.setattr(
        session_module.Agent, "get_cls", classmethod(lambda cls, name: DummyAgent)
    )
    yield


async def make_session(config=None, sio=None):
    config = config or DummyConfig()
    file_store: FileStore = InMemoryFileStore()
    llm_registry = LLMRegistry(config)
    conversation_stats = ConversationStats(
        file_store, conversation_id="sid", user_id="user"
    )
    sio = sio or DummySIO()
    sio.manager.rooms.setdefault("/", {})[ROOM_KEY.format(sid="sid")] = {"client"}
    session = Session(
        sid="sid",
        config=config,
        llm_registry=llm_registry,
        conversation_stats=conversation_stats,
        file_store=file_store,
        sio=sio,
        user_id="user",
    )
    return session, sio, config, llm_registry


@pytest.mark.asyncio
async def test_close_emits_and_cancels():
    session, sio, *_ = await make_session()
    await session.close()
    assert any(entry[0] == "oh_event" for entry in sio.emitted)
    assert session.agent_session.closed is True
    await asyncio.sleep(0)
    assert (
        session._monitor_publish_queue_task.cancelled()
        or session._monitor_publish_queue_task.done()
    )


@pytest.mark.asyncio
async def test_configure_security_settings_updates():
    session, *_ = await make_session()
    settings = SimpleNamespace(confirmation_mode=False, security_analyzer="custom")
    session._configure_security_settings(settings)
    assert session.config.security.confirmation_mode is False
    assert session.config.security.security_analyzer == "custom"
    await session.close()


@pytest.mark.asyncio
async def test_configure_sandbox_settings():
    session, *_ = await make_session()
    settings = SimpleNamespace(
        sandbox_base_container_image="newbase",
        sandbox_runtime_container_image="newruntime",
        sandbox_api_key=SimpleNamespace(get_secret_value=lambda: "secret"),
    )
    session._configure_sandbox_settings(settings)
    assert session.config.sandbox.base_container_image == "newbase"
    assert session.config.sandbox.runtime_container_image == "newruntime"
    assert session.config.sandbox.api_key == "secret"
    await session.close()


@pytest.mark.asyncio
async def test_configure_git_settings():
    session, *_ = await make_session()
    settings = SimpleNamespace(
        git_user_name="gituser", git_user_email="git@example.com"
    )
    session._configure_git_settings(settings)
    assert session.config.git_user_name == "gituser"
    assert session.config.git_user_email == "git@example.com"
    await session.close()


@pytest.mark.asyncio
async def test_configure_mcp_settings():
    session, *_ = await make_session()
    custom_mcp = SimpleNamespace()
    settings = SimpleNamespace(mcp_config=custom_mcp)
    session._configure_mcp_settings(settings)
    assert "default_http" in session.config.mcp.shttp_servers
    assert set(session.config.mcp.stdio_servers) >= {"stdio1", "stdio2"}
    await session.close()


@pytest.mark.asyncio
async def test_configure_agent_condenser(monkeypatch):
    session, *_ = await make_session()

    monkeypatch.setattr(
        condenser_config_module,
        "CondenserPipelineConfig",
        lambda condensers: {"condensers": condensers},
    )
    monkeypatch.setattr(
        condenser_config_module,
        "ConversationWindowCondenserConfig",
        lambda: "conversation",
    )
    monkeypatch.setattr(
        condenser_config_module,
        "BrowserOutputCondenserConfig",
        lambda attention_window: ("browser", attention_window),
    )
    monkeypatch.setattr(
        condenser_config_module,
        "LLMSummarizingCondenserConfig",
        lambda llm_config, keep_first, max_size: (
            "llm",
            llm_config.model,
            keep_first,
            max_size,
        ),
    )

    agent_config = session.config.get_agent_config("DummyAgent")
    llm_config = session.config.get_llm_config_from_agent("DummyAgent")
    settings = SimpleNamespace(enable_default_condenser=True, condenser_max_size=150)
    session._configure_agent_condenser(settings, agent_config, llm_config)
    assert agent_config.condenser["condensers"][0] == "conversation"
    await session.close()


@pytest.mark.asyncio
async def test_extract_conversation_data():
    session, *_ = await make_session()
    default = session._extract_conversation_data(SimpleNamespace())
    assert default == (None, None, None, None, None)

    data = ConversationInitData(
        git_provider_tokens=_provider_tokens("token"),
        selected_repository="repo",
        selected_branch="main",
        custom_secrets=_custom_secrets("value"),
        conversation_instructions="instr",
    )
    extracted = session._extract_conversation_data(data)
    provider_tokens = extracted[0]
    assert isinstance(provider_tokens, Mapping)
    provider = provider_tokens[ProviderType.GITHUB]
    assert provider.token is not None
    assert provider.token.get_secret_value() == "token"
    assert extracted[1] == "repo"
    assert extracted[2] == "main"
    secrets = extracted[3]
    assert isinstance(secrets, Mapping)
    secret = secrets["secret"]
    assert isinstance(secret, CustomSecret)
    assert secret.secret.get_secret_value() == "value"
    assert extracted[4] == "instr"
    await session.close()


@pytest.mark.asyncio
async def test_start_agent_session_success():
    session, *_ = await make_session()
    await session._start_agent_session(
        agent=SimpleNamespace(),
        max_iterations=2,
        max_budget_per_task=10,
        git_provider_tokens=_provider_tokens("token"),
        custom_secrets=_custom_secrets("value"),
        selected_repository="repo",
        selected_branch="main",
        initial_message=None,
        conversation_instructions="instr",
        replay_json=None,
    )
    assert session.agent_session.start_calls
    await session.close()


@pytest.mark.asyncio
async def test_start_agent_session_microagent_error():
    session, *_ = await make_session()

    async def fail_start(**kwargs):
        raise MicroagentValidationError("invalid microagent")

    session.agent_session.start = fail_start
    errors: list[str] = []

    async def send_error(message):
        errors.append(message)

    session.send_error = send_error
    await session._start_agent_session(
        SimpleNamespace(), 1, None, None, None, None, None, None, None, None
    )
    assert "invalid microagent" in errors[0]
    await session.close()


@pytest.mark.asyncio
async def test_start_agent_session_value_error():
    session, *_ = await make_session()

    async def fail_start(**kwargs):
        raise ValueError("microagent not found")

    session.agent_session.start = fail_start
    errors = []

    async def send_error(message):
        errors.append(message)

    session.send_error = send_error
    await session._start_agent_session(
        SimpleNamespace(), 1, None, None, None, None, None, None, None, None
    )
    assert "microagent not found" in errors[0]
    await session.close()


@pytest.mark.asyncio
async def test_start_agent_session_value_error_generic():
    session, *_ = await make_session()

    async def fail_start(**kwargs):
        raise ValueError("something else")

    session.agent_session.start = fail_start
    errors = []

    async def send_error(message):
        errors.append(message)

    session.send_error = send_error
    await session._start_agent_session(
        SimpleNamespace(), 1, None, None, None, None, None, None, None, None
    )
    assert errors[0] == "Failed to create agent session: ValueError"
    await session.close()


@pytest.mark.asyncio
async def test_start_agent_session_generic_error():
    session, *_ = await make_session()

    async def fail_start(**kwargs):
        raise RuntimeError("boom")

    session.agent_session.start = fail_start
    errors = []

    async def send_error(message):
        errors.append(message)

    session.send_error = send_error
    await session._start_agent_session(
        SimpleNamespace(), 1, None, None, None, None, None, None, None, None
    )
    assert errors[0] == "Failed to create agent session: RuntimeError"
    await session.close()


@pytest.mark.asyncio
async def test_initialize_agent(monkeypatch):
    session, *_ = await make_session()
    flags = {"security": False, "sandbox": False, "git": False, "mcp": False}

    session._configure_security_settings = lambda settings: flags.__setitem__(
        "security", True
    )
    session._configure_sandbox_settings = lambda settings: flags.__setitem__(
        "sandbox", True
    )
    session._configure_git_settings = lambda settings: flags.__setitem__("git", True)
    session._configure_mcp_settings = lambda settings: flags.__setitem__("mcp", True)

    settings = SimpleNamespace(
        agent="DummyAgent",
        max_iterations=3,
        max_budget_per_task=None,
        enable_default_condenser=True,
        condenser_max_size=None,
        git_provider_tokens=None,
        custom_secrets=None,
        selected_repository=None,
        selected_branch=None,
        conversation_instructions=None,
    )
    await session.initialize_agent(settings, None, None)
    assert all(flags.values())
    assert (
        session.agent_session.event_stream.events[0][0].agent_state
        == AgentState.LOADING
    )
    await session.close()


@pytest.mark.asyncio
async def test_notify_on_llm_retry():
    session, *_ = await make_session()
    messages = []
    session.queue_status_message = lambda msg_type, status, message: messages.append(
        (msg_type, status, message)
    )
    session._notify_on_llm_retry(2, 5)
    assert messages[0][1] == RuntimeStatus.LLM_RETRY
    await session.close()


@pytest.mark.asyncio
async def test_on_event_branches(monkeypatch):
    session, *_ = await make_session()
    sent = []

    async def fake_send(payload):
        sent.append(payload)

    session.send = fake_send
    await session._on_event(NullAction())
    await session._on_event(NullObservation(content=""))

    msg = MessageAction(content="hello")
    msg._source = EventSource.AGENT  # type: ignore[attr-defined]
    await session._on_event(msg)
    assert sent, "Expected send to be called for agent/user events"
    payload = sent[-1]
    if "message" in payload:
        assert payload["message"] == "hello"
    else:
        assert payload.get("args", {}).get("content") == "hello"

    cmd = CmdOutputObservation(command="ls", output="files", content="files")
    cmd._source = EventSource.ENVIRONMENT  # type: ignore[attr-defined]
    await session._on_event(cmd)
    assert sent[-1]["source"] == EventSource.AGENT

    state = AgentStateChangedObservation(
        reason="error", agent_state=AgentState.ERROR.value, content=""
    )
    state._source = EventSource.ENVIRONMENT  # type: ignore[attr-defined]
    await session._on_event(state)
    error = ErrorObservation(content="boom")
    await session._on_event(error)
    payload = sent[-1]
    if isinstance(payload, dict):
        extras = payload.get("extras", {})
        args = payload.get("args", {})
    else:
        extras = {}
        args = {}
    assert (
        "boom" in str(payload)
        or extras.get("error") == "boom"
        or args.get("content") == "boom"
    )
    await session.close()


@pytest.mark.asyncio
async def test_dispatch_flow(monkeypatch):
    session, *_ = await make_session()
    captured = []

    async def no_metasop(event):
        return False

    async def no_image(event):
        return False

    session._handle_metasop_dispatch = no_metasop
    session._handle_image_validation = no_image
    session.agent_session.event_stream.add_event = (
        lambda event, source: captured.append((event, source))
    )
    await session.dispatch(event_to_dict(MessageAction(content="hi")))
    assert captured[0][1] == EventSource.USER
    await session.close()


@pytest.mark.asyncio
async def test_dispatch_metasop_short_circuit():
    session, *_ = await make_session()

    async def handled(event):
        return True

    session._handle_metasop_dispatch = handled
    await session.dispatch(event_to_dict(MessageAction(content="SOP: run")))
    assert not session.agent_session.event_stream.events
    await session.close()


@pytest.mark.asyncio
async def test_dispatch_image_validation():
    session, *_ = await make_session()

    async def no_meta(event):
        return False

    async def image_block(event):
        return True

    session._handle_metasop_dispatch = no_meta
    session._handle_image_validation = image_block
    await session.dispatch(
        event_to_dict(MessageAction(content="hi", image_urls=["url"]))
    )
    assert not session.agent_session.event_stream.events
    await session.close()


@pytest.mark.asyncio
async def test_handle_metasop_dispatch_success(monkeypatch):
    session, *_ = await make_session()
    statuses = []

    async def record_status(msg_type, status, message):
        statuses.append((msg_type, status, message))

    session._send_status_message = record_status
    created_tasks = []
    monkeypatch.setattr(asyncio, "create_task", lambda coro: created_tasks.append(coro))
    event = MessageAction(content="SOP: run plan")
    handled = await session._handle_metasop_dispatch(event)
    assert handled is True
    assert statuses[0][1] == RuntimeStatus.READY
    assert created_tasks
    await session.close()


@pytest.mark.asyncio
async def test_handle_metasop_dispatch_error():
    session, *_ = await make_session()

    async def failing_send(*args, **kwargs):
        raise RuntimeError("fail")

    session._send_status_message = failing_send
    await session._handle_metasop_dispatch(MessageAction(content="SOP:"))
    await session.close()


@pytest.mark.asyncio
async def test_run_metasop_orchestration(monkeypatch):
    session, *_ = await make_session()
    called = []

    async def recording_runner(**kwargs):
        called.append(kwargs)

    monkeypatch.setattr(
        metasop_router_module, "run_metasop_for_conversation", recording_runner
    )
    await session._run_metasop_orchestration("SOP: run")
    assert called
    await session.close()


@pytest.mark.asyncio
async def test_run_metasop_orchestration_error(monkeypatch):
    session, *_ = await make_session()
    errors = []
    session._handle_metasop_runner_error = lambda error: errors.append(str(error))

    async def failing_runner(**kwargs):
        raise RuntimeError("boom")

    monkeypatch.setattr(
        metasop_router_module, "run_metasop_for_conversation", failing_runner
    )
    await session._run_metasop_orchestration("SOP")
    assert errors[0] == "boom"
    await session.close()


@pytest.mark.asyncio
async def test_handle_image_validation(monkeypatch):
    session, *_ = await make_session()

    assert (
        await session._handle_image_validation(MessageAction(content="no images"))
        is False
    )

    session.agent_session.controller = None
    assert (
        await session._handle_image_validation(
            MessageAction(content="", image_urls=["img"])
        )
        is False
    )

    controller = DummyController(vision_disabled=True)
    session.agent_session.controller = controller
    errors = []

    async def record_error(message):
        errors.append(message)

    session.send_error = record_error
    assert (
        await session._handle_image_validation(
            MessageAction(content="", image_urls=["img"])
        )
        is True
    )

    controller = DummyController(vision_disabled=False, vision_active=False)
    session.agent_session.controller = controller
    assert (
        await session._handle_image_validation(
            MessageAction(content="", image_urls=["img"])
        )
        is True
    )

    controller = DummyController(vision_disabled=False, vision_active=True)
    session.agent_session.controller = controller
    assert (
        await session._handle_image_validation(
            MessageAction(content="", image_urls=["img"])
        )
        is False
    )
    await session.close()


@pytest.mark.asyncio
async def test_send_and_monitor():
    session, *_ = await make_session()
    sent = []

    async def record_send(data):
        sent.append(data)

    session.send = record_send
    await session.send({"key": "value"})
    await asyncio.sleep(0.05)
    assert sent
    await session.close()


@pytest.mark.asyncio
async def test_send_error():
    session, *_ = await make_session()
    captured = []

    async def record_send(data):
        captured.append(data)

    session.send = record_send
    await session.send_error("oops")
    assert captured[0]["error"] is True
    await session.close()


@pytest.mark.asyncio
async def test_send_status_message_sets_error(monkeypatch):
    session, *_ = await make_session()
    session.agent_session.controller = DummyController()
    await session._send_status_message("error", RuntimeStatus.ERROR, "bad")
    assert session.agent_session.controller.saved_states[-1] == AgentState.ERROR
    await session.close()


@pytest.mark.asyncio
async def test_queue_status_message(monkeypatch):
    session, *_ = await make_session()
    captured = []

    def fake_run(coro, loop):
        captured.append(coro)
        return SimpleNamespace(result=lambda timeout=None: None)

    monkeypatch.setattr(asyncio, "run_coroutine_threadsafe", fake_run)
    session.queue_status_message("info", RuntimeStatus.READY, "ready")
    assert captured
    await session.close()


@pytest.mark.asyncio
async def test_send_should_drop_and_emit():
    session, sio, *_ = await make_session()
    assert await session._send({"observation": "null"}) is True
    session.sio = None
    assert await session._send({}) is True
    await session.close()


@pytest.mark.asyncio
async def test_send_handles_runtime_error():
    session, *_ = await make_session()
    session._emit_to_client = lambda data: (_ for _ in ()).throw(RuntimeError("boom"))
    result = await session._send({})
    assert result is False
    assert session.is_alive is False
    await session.close()


@pytest.mark.asyncio
async def test_wait_for_client_connection():
    session, sio, *_ = await make_session()
    sio.manager.rooms["/"][ROOM_KEY.format(sid="sid")] = set()
    session._wait_websocket_initial_complete = True
    await session._wait_for_client_connection()
    await session.close()


@pytest.mark.asyncio
async def test_should_drop_event():
    session, *_ = await make_session()
    assert session._should_drop_event({"observation": "null"}) is True
    assert session._should_drop_event({}) is False
    await session.close()


@pytest.mark.asyncio
async def test_emit_to_client():
    session, sio, *_ = await make_session()
    await session._emit_to_client({"id": 1})
    assert sio.emitted[-1][0] == "oh_event"
    await session.close()


@pytest.mark.asyncio
async def test_on_event_wrapper_invokes_loop(monkeypatch):
    session, *_ = await make_session()
    captured = []

    class DummyLoop:
        def run_until_complete(self, coro):
            captured.append(coro)

    monkeypatch.setattr(asyncio, "get_running_loop", lambda: (_ for _ in ()).throw(RuntimeError()))
    monkeypatch.setattr(asyncio, "get_event_loop", lambda: DummyLoop())
    session.on_event(MessageAction(content="wrapper"))
    assert captured
    await session.close()


@pytest.mark.asyncio
async def test_handle_metasop_dispatch_non_message():
    session, *_ = await make_session()
    result = await session._handle_metasop_dispatch(NullAction())
    assert result is False
    await session.close()


@pytest.mark.asyncio
async def test_handle_metasop_dispatch_non_sop():
    session, *_ = await make_session()
    result = await session._handle_metasop_dispatch(MessageAction(content="hello"))
    assert result is False
    await session.close()


@pytest.mark.asyncio
async def test_handle_metasop_runner_error_logs(monkeypatch):
    session, *_ = await make_session()
    logged = []
    session.logger.exception = lambda message: logged.append(message)
    session._handle_metasop_runner_error(RuntimeError("boom"))
    assert logged
    await session.close()


@pytest.mark.asyncio
async def test_send_returns_false_when_dead():
    session, *_ = await make_session()
    session.is_alive = False
    result = await session._send({})
    assert result is False
    await session.close()


@pytest.mark.asyncio
async def test_wait_for_client_connection_short_circuits():
    session, original_sio, *_ = await make_session()
    session.sio = None
    await session._wait_for_client_connection()
    session.sio = SimpleNamespace(manager=None)
    await session._wait_for_client_connection()
    session.sio = original_sio
    await session.close()


@pytest.mark.asyncio
async def test_emit_to_client_state_logging(monkeypatch):
    session, sio, *_ = await make_session()
    infos = []
    session.logger.info = lambda message, extra=None: infos.append(message)
    await session._emit_to_client(
        {"observation": "agent_state_changed", "extras": {"agent_state": "READY"}}
    )
    assert any("Agent state changed" in msg for msg in infos)
    await session.close()


@pytest.mark.asyncio
async def test_emit_to_client_without_sio_warns():
    session, *_ = await make_session()
    warnings = []
    session.logger.warning = lambda message, extra=None: warnings.append(message)
    session.sio = None
    await session._emit_to_client({"id": 2})
    assert any("dropping event" in msg for msg in warnings)
    await session.close()


@pytest.mark.asyncio
async def test_monitor_publish_queue_processes():
    session, *_ = await make_session()
    session._monitor_publish_queue_task.cancel()
    with contextlib.suppress(asyncio.CancelledError):
        await session._monitor_publish_queue_task
    processed = []

    async def fake_send(data):
        processed.append(data)

    session._send = fake_send
    worker = asyncio.create_task(session._monitor_publish_queue())
    await session.send({"data": 1})
    await asyncio.sleep(0.05)
    worker.cancel()
    with contextlib.suppress(asyncio.CancelledError):
        await worker
    assert processed
    await session.close()
