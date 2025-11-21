import asyncio
import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from forge.core import main as core_main
from forge.core.schemas import AgentState
from forge.events.action import MessageAction, NullAction
from forge.events.observation.agent import AgentStateChangedObservation
from forge.events import EventSource, EventStreamSubscriber
from forge.runtime.runtime_status import RuntimeStatus


class DummyLoop:
    def __init__(self) -> None:
        self.calls = []

    def call_soon(self, func, *args):
        self.calls.append((func, args))


class DummyEventStream:
    def __init__(self) -> None:
        self.added = []
        self.subscriptions = []
        self.sid = "sid"
        self.file_store = "store"
        self.user_id = "user"

    def add_event(self, event, source):
        self.added.append((event, source))

    def subscribe(self, subscriber, handler, sid):
        self.subscriptions.append((subscriber, handler, sid))


class DummyIterationFlag:
    def __init__(self, value: int = 5) -> None:
        self.current_value = value


class DummyController:
    def __init__(self) -> None:
        self.state = SimpleNamespace(
            agent_state=AgentState.RUNNING,
            last_error=None,
            iteration_flag=DummyIterationFlag(),
        )
        self._force_iteration_reset = False
        self.status_callback = None
        self._closed_with = None

    async def set_agent_state_to(self, new_state: AgentState) -> None:
        self.state.agent_state = new_state

    async def close(self, set_stop_state: bool = True) -> None:
        self._closed_with = set_stop_state

    def get_state(self):
        return self.state

    def get_trajectory(self, include_screenshots: bool):
        return ["trajectory", include_screenshots]


class DummyRuntime:
    def __init__(self) -> None:
        self.event_stream = DummyEventStream()
        self.status_callback = None

    def connect(self):
        return "connected"


class DummyMemory(SimpleNamespace):
    status_callback = None


class DummyAgent(SimpleNamespace):
    pass


@pytest.fixture
def dummy_config(tmp_path):
    sandbox = SimpleNamespace(selected_repo=None)
    return SimpleNamespace(
        sandbox=sandbox,
        workspace_mount_path_in_sandbox=str(tmp_path),
        mcp_host="host",
        file_store="disk",
        save_trajectory_path=str(tmp_path / "traj_dir"),
        save_screenshots_in_trajectory=False,
        cli_multiline_input=False,
    )


def test_setup_runtime_and_repo_with_selected_repo(monkeypatch, dummy_config):
    dummy_config.sandbox.selected_repo = "repo"
    runtime = DummyRuntime()
    tokens = {"token": "value"}
    calls = {}

    acquire_result = SimpleNamespace(runtime=runtime, repo_directory=None)

    def fake_acquire(**kwargs):
        calls["acquire_kwargs"] = kwargs
        repo_initializer = kwargs.get("repo_initializer")
        if repo_initializer:
            acquire_result.repo_directory = repo_initializer(runtime)
        return acquire_result

    monkeypatch.setattr(
        core_main._RUNTIME_ORCHESTRATOR, "acquire", lambda *args, **kwargs: fake_acquire(**kwargs)
    )
    monkeypatch.setattr(core_main, "get_provider_tokens", lambda: tokens)

    def fake_call_async(fn):
        calls["call_async"] = fn

    monkeypatch.setattr(core_main, "call_async_from_sync", fake_call_async)
    monkeypatch.setattr(
        core_main,
        "initialize_repository_for_runtime",
        lambda runtime_, immutable_provider_tokens, selected_repository: "repo-dir",
    )

    acquire_result = core_main._setup_runtime_and_repo(
        dummy_config,
        "session",
        llm_registry="llm",
        agent="agent",
        headless_mode=True,
    )

    assert acquire_result.runtime is runtime
    assert acquire_result.repo_directory == "repo-dir"
    assert calls["acquire_kwargs"]["git_provider_tokens"] == tokens
    assert calls["call_async"].__self__ is runtime


def test_setup_runtime_and_repo_without_repo(monkeypatch, dummy_config):
    runtime = DummyRuntime()
    acquire_result = SimpleNamespace(runtime=runtime, repo_directory=None)
    monkeypatch.setattr(
        core_main._RUNTIME_ORCHESTRATOR, "acquire", lambda *args, **kwargs: acquire_result
    )
    monkeypatch.setattr(core_main, "get_provider_tokens", lambda: {})
    monkeypatch.setattr(core_main, "call_async_from_sync", lambda fn: None)

    init_called = False

    def fail_initialize(*args, **kwargs):
        nonlocal init_called
        init_called = True

    monkeypatch.setattr(core_main, "initialize_repository_for_runtime", fail_initialize)

    acquire_result = core_main._setup_runtime_and_repo(
        dummy_config, "sid", "llm", "agent", headless_mode=False
    )
    assert acquire_result.repo_directory is None
    assert init_called is False


@pytest.mark.asyncio
async def test_setup_memory_and_mcp_creates_memory(monkeypatch, dummy_config):
    runtime = DummyRuntime()
    runtime.config = SimpleNamespace(mcp=SimpleNamespace(stdio_servers=[]))
    agent = DummyAgent(config=SimpleNamespace(enable_mcp=True))
    created_memory = DummyMemory()
    created_memory.status_callback = None

    def fake_create_memory(**kwargs):
        fake_create_memory.kwargs = kwargs
        return created_memory

    monkeypatch.setattr(core_main, "create_memory", fake_create_memory)
    monkeypatch.setattr(
        core_main.ForgeMCPConfigImpl,
        "create_default_mcp_server_config",
        lambda host, config_, arg: (None, ["stdio"]),
    )
    mcp_added = {}

    async def fake_add_mcp(agent_, runtime_, memory_):
        mcp_added.setdefault("called", True)

    monkeypatch.setattr(core_main, "add_mcp_tools_to_agent", fake_add_mcp)

    result = await core_main._setup_memory_and_mcp(
        dummy_config,
        runtime,
        "session",
        repo_directory="repo",
        memory=None,
        conversation_instructions="instructions",
        agent=agent,
    )

    assert result is created_memory
    assert fake_create_memory.kwargs["conversation_instructions"] == "instructions"
    assert runtime.config.mcp.stdio_servers == ["stdio"]
    assert mcp_added["called"] is True


@pytest.mark.asyncio
async def test_setup_memory_and_mcp_existing_memory(monkeypatch, dummy_config):
    runtime = DummyRuntime()
    runtime.config = SimpleNamespace(mcp=SimpleNamespace(stdio_servers=[]))
    agent = DummyAgent(config=SimpleNamespace(enable_mcp=False))
    existing_memory = DummyMemory()

    monkeypatch.setattr(core_main, "create_memory", pytest.fail)

    result = await core_main._setup_memory_and_mcp(
        dummy_config,
        runtime,
        "session",
        repo_directory=None,
        memory=existing_memory,
        conversation_instructions=None,
        agent=agent,
    )

    assert result is existing_memory
    assert runtime.config.mcp.stdio_servers == []


def test_setup_replay_events(monkeypatch):
    config = SimpleNamespace(replay_trajectory_path="path")
    expected_events = (["event"], MessageAction(content="task"))
    monkeypatch.setattr(core_main, "load_replay_log", lambda path: expected_events)
    events, action = core_main._setup_replay_events(config, NullAction())
    assert events == expected_events[0]
    assert action is expected_events[1]

    config.replay_trajectory_path = None
    events, action = core_main._setup_replay_events(config, expected_events[1])
    assert events is None
    assert action is expected_events[1]


def test_create_early_status_callback_handles_error(monkeypatch):
    controller = DummyController()
    controller.state.iteration_flag = DummyIterationFlag(7)
    tasks = []
    monkeypatch.setattr(
        core_main.asyncio, "create_task", lambda coro: tasks.append(coro)
    )

    errors = []
    monkeypatch.setattr(core_main.logger, "error", lambda msg: errors.append(msg))
    infos = []
    monkeypatch.setattr(
        core_main.logger, "info", lambda msg, *args: infos.append((msg, args))
    )

    callback = core_main._create_early_status_callback(controller)
    callback("error", RuntimeStatus.ERROR_MEMORY, "oops")

    # Iteration is preserved; boundary recorded for downstream logic
    assert controller.state.iteration_flag.current_value == 7
    assert getattr(controller.state, "_memory_error_boundary") == 7
    assert any("oops" in e for e in errors)
    assert tasks, "Async create_task should be invoked"

    callback("info", RuntimeStatus.READY, "all good")
    assert any("all good" in info[0] for info in infos)


def test_validate_initial_action_invalid():
    with pytest.raises(AssertionError):
        core_main._validate_initial_action(SimpleNamespace())

    qa_action = SimpleNamespace(message="hello")
    core_main._validate_initial_action(qa_action)


def test_setup_initial_events_handles_previous_error(monkeypatch):
    event_stream = DummyEventStream()
    initial_state = SimpleNamespace(last_error="bad")

    def raise_runtime_error():
        raise RuntimeError("no loop")

    monkeypatch.setattr(core_main.asyncio, "get_running_loop", raise_runtime_error)

    core_main._setup_initial_events(
        event_stream, MessageAction(content="ignored"), initial_state
    )
    assert event_stream.added
    event, source = event_stream.added[0]
    assert isinstance(event, MessageAction)
    assert source is EventSource.USER


def test_setup_initial_events_uses_loop(monkeypatch):
    event_stream = DummyEventStream()
    loop = DummyLoop()
    monkeypatch.setattr(core_main.asyncio, "get_running_loop", lambda: loop)

    core_main._setup_initial_events(
        event_stream, MessageAction(content="hi"), initial_state=None
    )
    assert loop.calls
    func, args = loop.calls[0]
    func(*args)  # execute the scheduled callback
    assert event_stream.added[0][0].content == "hi"


def test_setup_initial_events_direct_without_loop(monkeypatch):
    event_stream = DummyEventStream()

    def raise_runtime_error():
        raise RuntimeError("no loop")

    monkeypatch.setattr(core_main.asyncio, "get_running_loop", raise_runtime_error)

    core_main._setup_initial_events(
        event_stream, MessageAction(content="hi"), initial_state=None
    )
    assert event_stream.added[0][0].content == "hi"


def test_create_event_handler_paths(monkeypatch):
    config = SimpleNamespace(cli_multiline_input=False)
    controller = SimpleNamespace(get_state=lambda: "state")
    event_stream = DummyEventStream()

    monkeypatch.setattr(core_main, "read_input", lambda multiline: "typed")

    handler = core_main._create_event_handler(
        config,
        exit_on_message=True,
        fake_user_response_fn=None,
        controller=controller,
        event_stream=event_stream,
    )
    handler(
        AgentStateChangedObservation(
            agent_state=AgentState.AWAITING_USER_INPUT, content=""
        )
    )
    assert event_stream.added[-1][0].content == "/exit"

    handler = core_main._create_event_handler(
        config,
        exit_on_message=False,
        fake_user_response_fn=lambda state: "auto",
        controller=controller,
        event_stream=event_stream,
    )
    handler(
        AgentStateChangedObservation(
            agent_state=AgentState.AWAITING_USER_INPUT, content=""
        )
    )
    assert event_stream.added[-1][0].content == "auto"

    handler = core_main._create_event_handler(
        config,
        exit_on_message=False,
        fake_user_response_fn=None,
        controller=controller,
        event_stream=event_stream,
    )
    handler(
        AgentStateChangedObservation(
            agent_state=AgentState.AWAITING_USER_INPUT, content=""
        )
    )
    assert event_stream.added[-1][0].content == "typed"

    handler = core_main._create_event_handler(
        config,
        exit_on_message=False,
        fake_user_response_fn=None,
        controller=controller,
        event_stream=event_stream,
    )
    handler(MessageAction(content="ignored"))
    # Non observation events should not add entries
    assert event_stream.added[-1][0].content == "typed"


def test_save_trajectory_directory(tmp_path):
    config = SimpleNamespace(
        save_trajectory_path=str(tmp_path), save_screenshots_in_trajectory=False
    )
    controller = DummyController()
    session_id = "session"
    core_main._save_trajectory(config, session_id, controller)
    saved_file = tmp_path / f"{session_id}.json"
    assert saved_file.exists()
    data = json.loads(saved_file.read_text())
    assert data[0] == "trajectory"


def test_save_trajectory_file(tmp_path):
    save_path = tmp_path / "custom.json"
    config = SimpleNamespace(
        save_trajectory_path=str(save_path), save_screenshots_in_trajectory=False
    )
    controller = DummyController()
    core_main._save_trajectory(config, "session", controller)
    assert save_path.exists()


def test_initialize_session_components(monkeypatch, dummy_config):
    monkeypatch.setattr(
        core_main, "generate_sid", lambda config_, name=None: "generated"
    )
    monkeypatch.setattr(
        core_main,
        "create_registry_and_conversation_stats",
        lambda config_, session, _none: (
            "registry",
            "stats",
            SimpleNamespace(extra=True),
        ),
    )
    monkeypatch.setattr(
        core_main,
        "create_agent",
        lambda config_, registry: DummyAgent(
            name="agent", llm=SimpleNamespace(config=SimpleNamespace(model="m"))
        ),
    )

    session_id, llm_registry, conversation_stats, config_out, agent = (
        core_main._initialize_session_components(dummy_config, None)
    )
    assert session_id == "generated"
    assert llm_registry == "registry"
    assert conversation_stats == "stats"
    assert config_out.extra is True
    assert agent.name == "agent"


def test_setup_runtime_for_controller_existing(monkeypatch, dummy_config):
    runtime = DummyRuntime()
    result_runtime, repo, acquire_result = core_main._setup_runtime_for_controller(
        dummy_config, "llm", "session", True, DummyAgent(), runtime
    )
    assert result_runtime is runtime
    assert repo is None
    assert acquire_result is None


def test_setup_runtime_for_controller_new(monkeypatch, dummy_config):
    runtime = DummyRuntime()
    acquire_result = SimpleNamespace(runtime=runtime, repo_directory="repo-dir")
    monkeypatch.setattr(
        core_main, "_setup_runtime_and_repo", lambda *args, **kwargs: acquire_result
    )

    result_runtime, repo_dir, result_handle = core_main._setup_runtime_for_controller(
        dummy_config, "llm", "session", False, DummyAgent(), runtime=None
    )
    assert result_runtime is runtime
    assert repo_dir == "repo-dir"
    assert result_handle is acquire_result


@pytest.mark.asyncio
async def test_run_controller_missing_arguments(dummy_config):
    with pytest.raises(TypeError):
        await core_main.run_controller(initial_action=NullAction())
    with pytest.raises(TypeError):
        await core_main.run_controller(config_=dummy_config, initial_action=None)


@pytest.mark.asyncio
async def test_run_controller_success(monkeypatch, dummy_config, tmp_path):
    agent = DummyAgent(
        name="agent",
        llm=SimpleNamespace(config=SimpleNamespace(model="model")),
        config=SimpleNamespace(enable_mcp=False),
    )
    dummy_state = SimpleNamespace(
        agent_state=AgentState.RUNNING,
        iteration_flag=DummyIterationFlag(10),
        _force_iteration_reset=False,
    )

    def save_to_session(sid, store, user_id):
        save_to_session.called = (sid, store, user_id)

    dummy_state.save_to_session = save_to_session

    controller = DummyController()
    controller.state = dummy_state
    controller._force_iteration_reset = True

    async def close_stub(set_stop_state=False):
        controller._closed_with = set_stop_state

    controller.close = close_stub
    controller.get_state = lambda: dummy_state
    controller.get_trajectory = lambda include: ["traj", include]

    runtime = DummyRuntime()
    memory = DummyMemory()

    monkeypatch.setattr(
        core_main,
        "_initialize_session_components",
        lambda config_, session_id: ("sess", "llm", "stats", dummy_config, agent),
    )
    acquire_result = SimpleNamespace(runtime=runtime, repo_directory="repo")
    monkeypatch.setattr(
        core_main,
        "_setup_runtime_for_controller",
        lambda *args, **kwargs: (runtime, "repo", acquire_result),
    )

    async def fake_setup_memory(*args, **kwargs):
        return memory

    monkeypatch.setattr(core_main, "_setup_memory_and_mcp", fake_setup_memory)
    monkeypatch.setattr(
        core_main, "_setup_replay_events", lambda config_, action: (None, action)
    )
    monkeypatch.setattr(
        core_main,
        "create_controller",
        lambda agent_, runtime_, config_, stats, replay_events=None: (
            controller,
            SimpleNamespace(last_error=None),
        ),
    )
    scheduled = []

    def subscribe(subscriber, handler, sid):
        scheduled.append((subscriber, handler, sid))

    runtime.event_stream.subscribe = subscribe
    runtime.event_stream.sid = "sid"
    runtime.event_stream.file_store = tmp_path
    runtime.event_stream.user_id = "user"

    async def fake_run_agent_until_done(controller_, runtime_, memory_, end_states):
        controller_.state.agent_state = AgentState.FINISHED

    monkeypatch.setattr(core_main, "run_agent_until_done", fake_run_agent_until_done)
    monkeypatch.setattr(core_main.logger, "debug", lambda *args, **kwargs: None)
    monkeypatch.setattr(core_main.logger, "error", lambda *args, **kwargs: None)

    saved = {}
    monkeypatch.setattr(
        core_main,
        "_save_trajectory",
        lambda config_, session_id, controller_: saved.setdefault(
            "called", (config_, session_id, controller_)
        ),
    )

    release_called = {}

    def fake_release(result):
        release_called["result"] = result

    monkeypatch.setattr(core_main._RUNTIME_ORCHESTRATOR, "release", fake_release)

    state = await core_main.run_controller(
        config_=dummy_config, initial_action=MessageAction(content="start")
    )

    assert state.iteration_flag.current_value == 0
    assert controller._closed_with is False
    assert scheduled and scheduled[0][0] is EventStreamSubscriber.MAIN
    assert save_to_session.called == ("sid", tmp_path, "user")
    assert saved["called"][1] == "sess"
    assert release_called["result"] is acquire_result


def test_run_controller_rejects_legacy_kwargs(dummy_config):
    with pytest.raises(TypeError):
        asyncio.run(
            core_main.run_controller(
                config_=dummy_config,
                initial_action=MessageAction(content="hi"),
                unexpected=True,
            )
        )


def test_auto_continue_response():
    reply = core_main.auto_continue_response(SimpleNamespace())
    assert "continue" in reply.lower()


def test_load_replay_log_success(tmp_path, monkeypatch):
    path = tmp_path / "trajectory.json"
    data = [{"content": "task"}, {"content": "follow-up"}]
    path.write_text(json.dumps(data))
    monkeypatch.setattr(
        core_main.ReplayManager,
        "get_replay_events",
        lambda payload: [MessageAction(content="task"), MessageAction(content="next")],
    )
    events, first_action = core_main.load_replay_log(str(path))
    assert isinstance(first_action, MessageAction)
    assert events == [MessageAction(content="next")]


def test_load_replay_log_errors(tmp_path):
    path = tmp_path / "missing.json"
    with pytest.raises(ValueError):
        core_main.load_replay_log(str(path))

    directory = tmp_path / "dir"
    directory.mkdir()
    with pytest.raises(ValueError):
        core_main.load_replay_log(str(directory))

    bad_file = tmp_path / "bad.json"
    bad_file.write_text("not json")
    with pytest.raises(ValueError):
        core_main.load_replay_log(str(bad_file))


def test_create_early_status_callback_handles_iteration_exception(monkeypatch):
    controller = DummyController()

    class FailingFlag:
        def __init__(self):
            self._value = 5

        @property
        def current_value(self):
            return self._value

        @current_value.setter
        def current_value(self, value):
            raise RuntimeError("cannot reset")

    controller.state.iteration_flag = FailingFlag()
    monkeypatch.setattr(core_main.asyncio, "create_task", lambda coro: None)
    callback = core_main._create_early_status_callback(controller)
    callback("error", RuntimeStatus.ERROR_MEMORY, "oops")
    assert controller.state.last_error == "oops"


def test_setup_initial_events_error_with_loop(monkeypatch):
    event_stream = DummyEventStream()
    loop = DummyLoop()
    monkeypatch.setattr(core_main.asyncio, "get_running_loop", lambda: loop)
    initial_state = SimpleNamespace(last_error="bad")
    core_main._setup_initial_events(
        event_stream, MessageAction(content="ignored"), initial_state
    )
    assert loop.calls
    func, args = loop.calls[0]
    func(*args)
    assert isinstance(event_stream.added[0][0], MessageAction)


@pytest.mark.asyncio
async def test_run_controller_legacy_kwargs(monkeypatch, dummy_config):
    agent = DummyAgent(
        name="agent",
        llm=SimpleNamespace(config=SimpleNamespace(model="model")),
        config=SimpleNamespace(enable_mcp=False),
    )
    controller = DummyController()
    controller.state.save_to_session = lambda *args: None
    runtime = DummyRuntime()
    memory = DummyMemory()

    async def fake_setup_memory(*args, **kwargs):
        return memory

    monkeypatch.setattr(
        core_main,
        "_initialize_session_components",
        lambda config_, session_id: ("legacy", "llm", "stats", dummy_config, agent),
    )
    monkeypatch.setattr(
        core_main,
        "_setup_runtime_for_controller",
        lambda *args, **kwargs: (runtime, "repo", None),
    )
    monkeypatch.setattr(core_main, "_setup_memory_and_mcp", fake_setup_memory)
    monkeypatch.setattr(
        core_main, "_setup_replay_events", lambda config_, action: (None, action)
    )
    monkeypatch.setattr(
        core_main,
        "create_controller",
        lambda agent_, runtime_, config_, stats, replay_events=None: (
            controller,
            SimpleNamespace(last_error=None),
        ),
    )
    runtime.event_stream.subscribe = lambda subscriber, handler, sid: None
    runtime.event_stream.sid = "sid"
    runtime.event_stream.file_store = "store"
    runtime.event_stream.user_id = "user"

    async def fake_run_agent(controller_, runtime_, memory_, end_states):
        controller_.state.agent_state = AgentState.FINISHED

    monkeypatch.setattr(core_main, "run_agent_until_done", fake_run_agent)
    monkeypatch.setattr(core_main.logger, "debug", lambda *args, **kwargs: None)
    monkeypatch.setattr(core_main.logger, "error", lambda *args, **kwargs: None)
    monkeypatch.setattr(core_main, "_save_trajectory", lambda *args, **kwargs: None)

    state = await core_main.run_controller(
        config_=None,
        initial_action=None,
        config=dummy_config,
        initial_user_action=MessageAction(content="legacy"),
        sid="legacy-sid",
        headless=False,
    )

    assert state.agent_state == AgentState.FINISHED


@pytest.mark.asyncio
async def test_run_controller_logs_exception(monkeypatch, dummy_config):
    agent = DummyAgent(
        name="agent",
        llm=SimpleNamespace(config=SimpleNamespace(model="model")),
        config=SimpleNamespace(enable_mcp=False),
    )
    controller = DummyController()
    controller.state.save_to_session = lambda *args: None
    runtime = DummyRuntime()
    memory = DummyMemory()

    async def fake_setup_memory(*args, **kwargs):
        return memory

    monkeypatch.setattr(
        core_main,
        "_initialize_session_components",
        lambda config_, session_id: ("sess", "llm", "stats", dummy_config, agent),
    )
    monkeypatch.setattr(
        core_main,
        "_setup_runtime_for_controller",
        lambda *args, **kwargs: (runtime, "repo", None),
    )
    monkeypatch.setattr(core_main, "_setup_memory_and_mcp", fake_setup_memory)
    monkeypatch.setattr(
        core_main, "_setup_replay_events", lambda config_, action: (None, action)
    )
    monkeypatch.setattr(
        core_main,
        "create_controller",
        lambda agent_, runtime_, config_, stats, replay_events=None: (
            controller,
            SimpleNamespace(last_error=None),
        ),
    )
    runtime.event_stream.subscribe = lambda subscriber, handler, sid: None
    runtime.event_stream.sid = "sid"
    runtime.event_stream.file_store = "store"
    runtime.event_stream.user_id = "user"

    async def failing_run_agent(*_args, **_kwargs):
        raise RuntimeError("boom")

    monkeypatch.setattr(core_main, "run_agent_until_done", failing_run_agent)
    errors = []
    monkeypatch.setattr(
        core_main.logger,
        "error",
        lambda msg, *args: errors.append(msg % args if args else msg),
    )
    monkeypatch.setattr(core_main.logger, "debug", lambda *args, **kwargs: None)
    monkeypatch.setattr(core_main, "_save_trajectory", lambda *args, **kwargs: None)

    controller.state.save_to_session = lambda *args: None

    state = await core_main.run_controller(
        config_=dummy_config, initial_action=MessageAction(content="start")
    )
    assert "Exception in main loop" in errors[-1]
    assert state.agent_state is not None
