"""Unit tests for `AgentSession`."""

from __future__ import annotations

import asyncio
import logging
import time
from types import MappingProxyType, SimpleNamespace
from typing import Any, Mapping, cast
import json

import pytest
from pydantic import SecretStr

from forge.integrations.provider import CustomSecret, ProviderToken, ProviderType
from forge.llm.llm_registry import LLMRegistry
from forge.server.services.conversation_stats import ConversationStats
from forge.server.session import agent_session as session_module
from forge.server.session.agent_session import AgentSession, AgentState
from forge.events.action import MessageAction
from forge.storage.files import FileStore
from forge.storage.memory import InMemoryFileStore


class DummyEventStream:
    def __init__(self, sid, file_store, user_id):
        self.sid = sid
        self.file_store = file_store
        self.user_id = user_id
        self.events = []
        self.closed = False

    def add_event(self, event, source):
        self.events.append((event, source))

    def get_latest_event_id(self):
        return len(self.events)

    def close(self):
        self.closed = True


class DummyRuntime:
    def __init__(self, **kwargs):
        self.kwargs = kwargs
        self.connected = False
        self.closed = False
        self.plugins = kwargs.get("plugins", [])
        self.security_analyzer = "security"
        self.clone_called = False
        self.setup_script_called = False
        self.git_hooks_called = False

    async def connect(self):
        self.connected = True

    async def clone_or_init_repo(self, *args, **kwargs):
        self.clone_called = True

    def maybe_run_setup_script(self):
        self.setup_script_called = True

    def maybe_setup_git_hooks(self):
        self.git_hooks_called = True

    def close(self):
        self.closed = True

    async def get_microagents_from_selected_repo(self, repo):
        return [f"microagent:{repo or 'default'}"]


class DummyRemoteRuntime(DummyRuntime):
    pass


class DummyProviderHandler:
    created: list["DummyProviderHandler"] = []

    def __init__(
        self,
        provider_tokens: MappingProxyType[ProviderType, ProviderToken] | None = None,
    ):
        self.provider_tokens = provider_tokens
        DummyProviderHandler.created.append(self)
        self.event_stream = None

    @staticmethod
    def get_provider_env_key(provider):
        if hasattr(provider, "name"):
            return f"{provider.name}_TOKEN"
        return f"{str(provider).upper()}_TOKEN"

    async def set_event_stream_secrets(self, event_stream):
        self.event_stream = event_stream

    async def get_env_vars(self, expose_secrets=False):
        if not self.provider_tokens:
            return {}
        return {
            f"ENV_{provider.name}": token.token.get_secret_value()
            if token.token
            else None
            for provider, token in self.provider_tokens.items()
        }


class DummyUserSecrets:
    def __init__(self, custom_secrets: Mapping[str, CustomSecret] | None):
        data = dict(custom_secrets) if custom_secrets else {}
        self.custom_secrets = MappingProxyType(data)
        self.event_stream = None

    def set_event_stream_secrets(self, event_stream):
        self.event_stream = event_stream

    def get_env_vars(self):
        return {
            f"SECRET_{k}": v.secret.get_secret_value()
            for k, v in self.custom_secrets.items()
        }

    def get_custom_secrets_descriptions(self):
        return {k: f"desc:{k}" for k in self.custom_secrets}


class DummyMemory:
    def __init__(self, **kwargs):
        self.kwargs = kwargs
        self.runtime_info = None
        self.instructions = None
        self.microagents = None
        self.repo_info = None

    def set_runtime_info(self, runtime, secrets, working_dir):
        self.runtime_info = (runtime, secrets, working_dir)

    def set_conversation_instructions(self, instructions):
        self.instructions = instructions

    def load_user_workspace_microagents(self, microagents):
        self.microagents = microagents

    def set_repository_info(self, repo, directory, branch):
        self.repo_info = (repo, directory, branch)


class DummyAgentController:
    def __init__(self, **kwargs):
        self.kwargs = kwargs
        self.state = SimpleNamespace(
            agent_state=kwargs.get("initial_state", AgentState.RUNNING)
        )
        self.closed = False
        self.saved = False

    def save_state(self):
        self.saved = True

    async def close(self):
        self.closed = True

    async def set_agent_state_to(self, state):
        self.state.agent_state = state


class DummyReplayManager:
    @staticmethod
    def get_replay_events(data):
        return data


class DummyAgent:
    def __init__(self):
        self.name = "dummy-agent"
        self.config = SimpleNamespace(enable_mcp=True)
        self.llm = SimpleNamespace(
            config=SimpleNamespace(model="model", base_url="url")
        )
        self.sandbox_plugins = [SimpleNamespace(name="plugin")]


def _provider_tokens(**tokens: str) -> MappingProxyType[ProviderType, ProviderToken]:
    mapping = {
        ProviderType[key.upper()]: ProviderToken(token=SecretStr(value))
        for key, value in tokens.items()
    }
    return MappingProxyType(mapping)


def _custom_secret_mapping(**secrets: str) -> MappingProxyType[str, CustomSecret]:
    mapping = {
        key: CustomSecret(secret=SecretStr(value)) for key, value in secrets.items()
    }
    return MappingProxyType(mapping)


@pytest.fixture(autouse=True)
def patch_dependencies(monkeypatch):
    monkeypatch.setattr(session_module, "EventStream", DummyEventStream)
    monkeypatch.setattr(
        session_module,
        "forgeLoggerAdapter",
        lambda extra=None: logging.getLogger("agent-session-test"),
    )
    monkeypatch.setattr(session_module, "ProviderHandler", DummyProviderHandler)
    monkeypatch.setattr(session_module, "UserSecrets", DummyUserSecrets)
    monkeypatch.setattr(session_module, "Memory", DummyMemory)
    monkeypatch.setattr(session_module, "AgentController", DummyAgentController)
    monkeypatch.setattr(session_module, "ReplayManager", DummyReplayManager)

    async def noop_add_mcp(*args, **kwargs):
        return None

    monkeypatch.setattr(session_module, "add_mcp_tools_to_agent", noop_add_mcp)

    async def async_call_sync(func, *args, **kwargs):
        return func(*args, **kwargs)

    monkeypatch.setattr(session_module, "call_sync_from_async", async_call_sync)
    monkeypatch.setattr(session_module, "RemoteRuntime", DummyRemoteRuntime)

    class DummyEventAdapter:
        def __init__(self):
            self._streams: dict[str, DummyEventStream] = {}

        def start_session(self, session_id=None, user_id=None, **kwargs):
            sid = session_id or "dummy-session"
            if sid not in self._streams:
                self._streams[sid] = DummyEventStream(sid, InMemoryFileStore(), user_id)
            return {"session_id": sid, "user_id": user_id, "repository": None, "branch": None, "labels": kwargs.get("labels") or {}}

        def get_event_stream(self, session_id):
            return self._streams.setdefault(
                session_id, DummyEventStream(session_id, InMemoryFileStore(), "user")
            )

    dummy_adapter = DummyEventAdapter()
    monkeypatch.setattr(
        session_module, "get_event_service_adapter", lambda: dummy_adapter
    )
    yield
    DummyProviderHandler.created.clear()


def make_agent_session():
    file_store: FileStore = InMemoryFileStore()
    llm_registry = cast(LLMRegistry, SimpleNamespace())
    conversation_stats = ConversationStats(
        file_store, conversation_id="sid", user_id="user"
    )
    return AgentSession(
        sid="sid",
        file_store=file_store,
        llm_registry=llm_registry,
        conversation_stats=conversation_stats,
        status_callback=None,
        user_id="user",
    )


def make_agent():
    return DummyAgent()


@pytest.mark.asyncio
async def test_setup_runtime_and_providers_invokes_handlers(monkeypatch):
    session = make_agent_session()

    async def fake_create_runtime(*args, **kwargs):
        return True

    called: dict[str, Any] = {}

    async def fake_setup_handlers(*args, **kwargs):
        called["handled"] = True

    session._create_runtime = fake_create_runtime
    session._setup_provider_handlers = fake_setup_handlers

    result = await session._setup_runtime_and_providers(
        runtime_name="runtime",
        config=SimpleNamespace(),
        agent=make_agent(),
        git_provider_tokens=None,
        custom_secrets=None,
        selected_repository=None,
        selected_branch=None,
    )
    assert result is True
    assert called["handled"] is True


@pytest.mark.asyncio
async def test_start_success(monkeypatch):
    session = make_agent_session()
    session._validate_session_state = lambda: True
    startup_state = {
        "started_at": time.time(),
        "finished": False,
        "restored_state": False,
    }
    session._initialize_session_startup = lambda: startup_state
    events: dict[str, bool] = {}

    async def fake_setup_runtime(*args, **kwargs):
        return True

    async def fake_setup_memory(*args, **kwargs):
        events["memory"] = True

    async def fake_setup_controller(*args, **kwargs):
        return SimpleNamespace(content="hello")

    session._setup_runtime_and_providers = fake_setup_runtime
    session._setup_memory_and_mcp_tools = fake_setup_memory
    session._setup_controller_and_handle_replay = fake_setup_controller
    recorded: dict[str, Any] = {}
    session._start_agent_execution = lambda msg: recorded.setdefault("msg", msg)
    finalize_calls: dict[str, Any] = {}
    session._finalize_session_startup = (
        lambda state, runtime_connected: finalize_calls.setdefault(
            "called", (state, runtime_connected)
        )
    )

    await session.start(
        runtime_name="runtime",
        config=SimpleNamespace(),
        agent=make_agent(),
        max_iterations=5,
        git_provider_tokens=None,
    )

    assert recorded["msg"].content == "hello"
    assert finalize_calls["called"][1] is True


@pytest.mark.asyncio
async def test_start_handles_exception(monkeypatch):
    session = make_agent_session()
    session._validate_session_state = lambda: True
    session._initialize_session_startup = lambda: {
        "started_at": time.time(),
        "finished": False,
        "restored_state": False,
    }

    async def failing_setup(*args, **kwargs):
        raise RuntimeError("boom")

    finalize: dict[str, Any] = {}
    session._setup_runtime_and_providers = failing_setup
    session._finalize_session_startup = (
        lambda state, runtime_connected: finalize.setdefault(
            "called", (state, runtime_connected)
        )
    )

    with pytest.raises(RuntimeError):
        await session.start(
            runtime_name="runtime",
            config=SimpleNamespace(),
            agent=make_agent(),
            max_iterations=1,
        )

    assert finalize["called"][1] is False


def test_create_controller(monkeypatch):
    session = make_agent_session()
    session.runtime = DummyRuntime()
    controller, restored = session._create_controller(
        agent=make_agent(),
        confirmation_mode=False,
        max_iterations=5,
        max_budget_per_task=None,
        agent_to_llm_config=None,
        agent_configs=None,
        replay_events=None,
    )
    assert isinstance(controller, DummyAgentController)
    assert restored is False


def test_run_replay(monkeypatch):
    session = make_agent_session()
    session.runtime = DummyRuntime()
    events = [MessageAction(content="hi"), SimpleNamespace()]
    monkeypatch.setattr(session_module.json, "loads", lambda data: events)
    session._create_controller = lambda *a, **k: (DummyAgentController(), False)
    result = session._run_replay(
        initial_message=None,
        replay_json="{}",
        agent=make_agent(),
        config=SimpleNamespace(security=SimpleNamespace(confirmation_mode=False)),
        max_iterations=5,
        max_budget_per_task=None,
        agent_to_llm_config=None,
        agent_configs=None,
    )
    assert isinstance(result, MessageAction)


def test_maybe_restore_state(monkeypatch):
    session = make_agent_session()
    monkeypatch.setattr(
        session_module.State,
        "restore_from_session",
        lambda *args, **kwargs: SimpleNamespace(),
    )
    restored = session._maybe_restore_state()
    assert restored is not None

    calls: dict[str, int] = {"count": 0}

    def raise_restore(*args, **kwargs):
        calls["count"] += 1
        raise ValueError("fail")

    session.event_stream.get_latest_event_id = lambda: 0
    monkeypatch.setattr(session_module.State, "restore_from_session", raise_restore)
    assert session._maybe_restore_state() is None


def test_validate_session_state(monkeypatch):
    session = make_agent_session()
    session.controller = object()
    with pytest.raises(RuntimeError):
        session._validate_session_state()

    session.controller = None
    session._closed = True
    assert session._validate_session_state() is False


def test_initialize_and_finalize_startup():
    session = make_agent_session()
    state = session._initialize_session_startup()
    assert session._starting is True
    assert "started_at" in state

    state["finished"] = True
    session._finalize_session_startup(state, runtime_connected=True)
    assert session._starting is False


def test_finalize_session_startup_failure():
    session = make_agent_session()
    state = session._initialize_session_startup()
    state["finished"] = False
    session._finalize_session_startup(state, runtime_connected=False)


def test_override_provider_tokens_with_custom_secret():
    session = make_agent_session()
    tokens = MappingProxyType(
        {
            ProviderType.GITHUB: ProviderToken(token=SecretStr("token")),
            ProviderType.ENTERPRISE_SSO: ProviderToken(token=SecretStr("token2")),
        }
    )
    secrets = MappingProxyType(
        {"GITHUB_TOKEN": CustomSecret(secret=SecretStr("custom"))}
    )
    filtered = session.override_provider_tokens_with_custom_secret(tokens, secrets)
    assert filtered is not None
    assert ProviderType.GITHUB not in filtered
    assert ProviderType.ENTERPRISE_SSO in filtered

    assert session.override_provider_tokens_with_custom_secret(None, None) is None


def test_validate_session_state_default():
    session = make_agent_session()
    assert session._validate_session_state() is True


@pytest.mark.asyncio
async def test_setup_provider_handlers(monkeypatch):
    session = make_agent_session()
    secrets = _custom_secret_mapping(foo="bar")
    await session._setup_provider_handlers(_provider_tokens(github="token"), secrets)
    assert DummyProviderHandler.created
    handler = DummyProviderHandler.created[0]
    assert handler.provider_tokens is not None
    assert handler.event_stream is session.event_stream


@pytest.mark.asyncio
async def test_setup_memory_and_mcp_tools(monkeypatch):
    session = make_agent_session()
    session.runtime = DummyRuntime()
    agent = make_agent()
    await session._setup_memory_and_mcp_tools(
        selected_repository="repo/owner",
        selected_branch="main",
        conversation_instructions="instruction",
        custom_secrets=_custom_secret_mapping(foo="bar"),
        config=SimpleNamespace(workspace_mount_path_in_sandbox="/workspace"),
        agent=agent,
    )
    memory = session.memory
    assert isinstance(memory, DummyMemory)
    assert memory.runtime_info is not None
    assert memory.runtime_info[0] is session.runtime
    assert memory.repo_info == ("repo/owner", "owner", "main")


@pytest.mark.asyncio
async def test_setup_controller_and_handle_replay(monkeypatch):
    session = make_agent_session()
    session.runtime = DummyRuntime()
    session._run_replay = lambda *a, **k: SimpleNamespace(content="replayed")
    session._create_controller = lambda *a, **k: (DummyAgentController(), False)

    msg = await session._setup_controller_and_handle_replay(
        replay_json="[{}]",
        initial_message=None,
        agent=make_agent(),
        config=SimpleNamespace(security=SimpleNamespace(confirmation_mode=False)),
        max_iterations=5,
        max_budget_per_task=None,
        agent_to_llm_config=None,
        agent_configs=None,
    )
    assert isinstance(msg, SimpleNamespace)

    called = {}

    def fake_create(agent, confirmation_mode, max_iterations, **kwargs):
        called["args"] = (agent, confirmation_mode, max_iterations)
        return DummyAgentController(), False

    session._create_controller = fake_create
    session._run_replay = lambda *a, **k: None

    msg2 = await session._setup_controller_and_handle_replay(
        replay_json=None,
        initial_message=None,
        agent=make_agent(),
        config=SimpleNamespace(security=SimpleNamespace(confirmation_mode=True)),
        max_iterations=3,
        max_budget_per_task=None,
        agent_to_llm_config=None,
        agent_configs=None,
    )
    assert called["args"][1] is True
    assert msg2 is None


@pytest.mark.asyncio
async def test_create_runtime_remote(monkeypatch):
    session = make_agent_session()
    agent = make_agent()
    monkeypatch.setattr(
        session_module, "get_runtime_cls", lambda name: DummyRemoteRuntime
    )

    connected = await session._create_runtime(
        runtime_name="remote",
        config=SimpleNamespace(),
        agent=agent,
        git_provider_tokens=_provider_tokens(github="token"),
        custom_secrets=_custom_secret_mapping(GITHUB_TOKEN="override"),
        selected_repository="owner/repo",
        selected_branch="main",
    )

    assert connected is True
    assert isinstance(session.runtime, DummyRemoteRuntime)
    assert session.runtime.connected is True
    assert session.runtime.clone_called is True


@pytest.mark.asyncio
async def test_create_runtime_non_remote(monkeypatch):
    session = make_agent_session()
    agent = make_agent()
    monkeypatch.setattr(session_module, "get_runtime_cls", lambda name: DummyRuntime)

    connected = await session._create_runtime(
        runtime_name="local",
        config=SimpleNamespace(),
        agent=agent,
        git_provider_tokens=_provider_tokens(github="token"),
        custom_secrets=None,
        selected_repository=None,
        selected_branch=None,
    )
    assert connected is True
    last_handler = DummyProviderHandler.created[-1]
    assert last_handler.provider_tokens is not None
    token = last_handler.provider_tokens[ProviderType.GITHUB]
    assert token.token is not None
    assert token.token.get_secret_value() == "token"


@pytest.mark.asyncio
async def test_create_runtime_handles_unavailable(monkeypatch):
    session = make_agent_session()

    class FailingRuntime(DummyRuntime):
        async def connect(self):
            raise session_module.AgentRuntimeUnavailableError("offline")

    monkeypatch.setattr(session_module, "get_runtime_cls", lambda name: FailingRuntime)

    status_calls: list[tuple[str, Any, Any]] = []
    session._status_callback = lambda msg_type, status, message: status_calls.append(
        (msg_type, status, message)
    )

    connected = await session._create_runtime(
        runtime_name="failing",
        config=SimpleNamespace(),
        agent=make_agent(),
    )
    assert connected is False
    assert status_calls


@pytest.mark.asyncio
async def test_create_runtime_raises_when_duplicate(monkeypatch):
    session = make_agent_session()
    session.runtime = DummyRuntime()
    with pytest.raises(RuntimeError):
        await session._create_runtime("any", SimpleNamespace(), make_agent())


def test_start_agent_execution():
    session = make_agent_session()
    msg = SimpleNamespace()
    session._start_agent_execution(msg)
    assert session.event_stream.events[0][0] is msg
    session.event_stream.events.clear()
    session._start_agent_execution(None)
    action = session.event_stream.events[0][0]
    assert action.agent_state == AgentState.AWAITING_USER_INPUT


def test_get_state_and_close(monkeypatch):
    session = make_agent_session()
    session.controller = DummyAgentController()
    assert session.get_state() == AgentState.RUNNING
    session.controller = None
    session._started_at = time.time() - session_module.WAIT_TIME_BEFORE_CLOSE - 1
    assert session.get_state() == AgentState.ERROR

    monkeypatch.setattr(session_module, "should_continue", lambda: False)
    runtime = DummyRuntime()
    session.runtime = runtime
    controller = DummyAgentController()
    session.controller = controller
    session.event_stream = DummyEventStream("sid", "fs", "user")

    async def close_session():
        await session.close()

    asyncio.get_event_loop().run_until_complete(close_session())
    assert session.event_stream.closed is True
    assert controller.saved is True
    assert runtime.closed is True


@pytest.mark.asyncio
async def test_close_waits_for_initialization(monkeypatch):
    session = make_agent_session()
    session._starting = True
    session._started_at = time.time()
    calls = iter([True, False])
    monkeypatch.setattr(session_module, "should_continue", lambda: next(calls, False))
    session.event_stream = DummyEventStream("sid", "fs", "user")
    session.controller = DummyAgentController()
    session.runtime = DummyRuntime()

    await session.close()
    assert session.event_stream.closed is True


def test_is_closed_flag():
    session = make_agent_session()
    assert session.is_closed() is False
    session._closed = True
    assert session.is_closed() is True


@pytest.mark.asyncio
async def test_close_noop_when_already_closed():
    session = make_agent_session()
    session._closed = True
    await session.close()


def test_create_controller_raises_without_runtime():
    session = make_agent_session()
    session.runtime = None
    with pytest.raises(RuntimeError):
        session._create_controller(make_agent(), False, 1)

    session.runtime = DummyRuntime()
    session.controller = DummyAgentController()
    with pytest.raises(RuntimeError):
        session._create_controller(make_agent(), False, 1)


def test_maybe_restore_state_warning(monkeypatch):
    session = make_agent_session()
    session.event_stream.add_event("event", "source")

    def raise_restore(*args, **kwargs):
        raise ValueError("boom")

    monkeypatch.setattr(session_module.State, "restore_from_session", raise_restore)
    assert session._maybe_restore_state() is None


@pytest.mark.asyncio
async def test_start_returns_when_invalid(monkeypatch):
    session = make_agent_session()
    calls: dict[str, bool] = {}

    def fake_validate():
        calls["called"] = True
        return False

    session._validate_session_state = fake_validate
    called: dict[str, Any] = {}
    session._setup_runtime_and_providers = lambda *a, **k: called.setdefault(
        "runtime", True
    )

    await session.start(
        runtime_name="runtime",
        config=SimpleNamespace(),
        agent=make_agent(),
        max_iterations=1,
    )
    assert calls["called"] is True
    assert "runtime" not in called


@pytest.mark.asyncio
async def test_start_respects_closed(monkeypatch):
    session = make_agent_session()
    session._initialize_session_startup = lambda: {
        "started_at": time.time(),
        "finished": False,
        "restored_state": False,
    }

    async def fake_setup_runtime(*args, **kwargs):
        return True

    async def fake_setup_memory(*args, **kwargs):
        return True

    async def fake_setup_controller(*args, **kwargs):
        return SimpleNamespace(content="hello")

    session._setup_runtime_and_providers = fake_setup_runtime
    session._setup_memory_and_mcp_tools = fake_setup_memory
    session._setup_controller_and_handle_replay = fake_setup_controller
    recorded: dict[str, Any] = {}
    session._start_agent_execution = lambda msg: recorded.setdefault("msg", msg)
    finalize_calls: dict[str, Any] = {}
    session._finalize_session_startup = (
        lambda state, runtime_connected: finalize_calls.setdefault(
            "called", (state, runtime_connected)
        )
    )

    await session.start(
        runtime_name="runtime",
        config=SimpleNamespace(),
        agent=make_agent(),
        max_iterations=5,
        git_provider_tokens=None,
    )

    assert recorded["msg"].content == "hello"
    assert finalize_calls["called"][1] is True

    session._closed = True
    session._initialize_session_startup = lambda: {
        "started_at": time.time(),
        "finished": False,
        "restored_state": False,
    }
    recorded.clear()
    await session.start(
        runtime_name="runtime",
        config=SimpleNamespace(),
        agent=make_agent(),
        max_iterations=1,
    )
    assert recorded == {}


def test_get_state_timeout_paths(monkeypatch):
    session = make_agent_session()
    session.controller = None
    session._started_at = 0
    monkeypatch.setattr(
        session_module.time, "time", lambda: session_module.WAIT_TIME_BEFORE_CLOSE + 1
    )
    assert session.get_state() == AgentState.ERROR
    monkeypatch.setattr(session_module.time, "time", lambda: 0)
    assert session.get_state() is None
