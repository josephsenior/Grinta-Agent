import json
from types import SimpleNamespace
from unittest.mock import Mock, patch

import pytest

import forge.events.event  # Preload module to avoid rewrite issues
from forge.core import setup


class DummyEventStream:
    def __init__(self, sid="sid", file_store="store"):
        self.sid = sid
        self.file_store = file_store
        self.subscriptions = []

    def subscribe(self, subscriber, handler, sid):
        self.subscriptions.append((subscriber, handler, sid))

    def get_latest_event_id(self):
        return 0

    def search_events(self, **kwargs):
        return []


class DummyRuntime(SimpleNamespace):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.clone_args = None
        self.maybe_run_setup_calls = 0
        self.maybe_setup_git_calls = 0

    async def clone_or_init_repo(self, tokens, repo, *args):
        self.clone_args = (tokens, repo)
        return "repo-dir"

    def maybe_run_setup_script(self):
        self.maybe_run_setup_calls += 1

    def maybe_setup_git_hooks(self):
        self.maybe_setup_git_calls += 1

    def get_microagents_from_selected_repo(self, selected_repo):
        return [SimpleNamespace(name="micro", on_load=lambda: None)]

    def get_plugins(self):
        return []


class DummyMemory(SimpleNamespace):
    def __init__(self):
        super().__init__()
        self.runtime_info = None
        self.repo_info = None
        self.instructions = None

    def set_conversation_instructions(self, instructions):
        self.instructions = instructions

    def set_runtime_info(self, runtime, data, working_dir):
        self.runtime_info = (runtime, data, working_dir)

    def load_user_workspace_microagents(self, microagents):
        self.microagents = microagents

    def set_repository_info(self, repo, directory):
        self.repo_info = (repo, directory)


@pytest.fixture
def dummy_config():
    return SimpleNamespace(
        default_agent="test",
        runtime="local",
        file_store="memory",
        file_store_path=None,
        security=SimpleNamespace(confirmation_mode="none"),
        max_iterations=10,
        max_budget_per_task=5,
        workspace_mount_path_in_sandbox="/tmp",
        jwt_secret="secret",
        get_agent_config=lambda agent: SimpleNamespace(name=agent),
        get_llm_config_from_agent=lambda agent: None,
        get_agent_to_llm_config_map=lambda: {"test": "llm"},
    )


def test_create_runtime(monkeypatch, dummy_config):
    class DummyAgent(SimpleNamespace):
        sandbox_plugins = []

    monkeypatch.setattr(setup.Agent, "get_cls", lambda name: DummyAgent)
    created = []

    class DummyRuntimeCls(DummyRuntime):
        def __init__(self, **kwargs):
            super().__init__(**kwargs)
            created.append(kwargs)

    monkeypatch.setattr(setup, "get_runtime_cls", lambda runtime_name: DummyRuntimeCls)
    monkeypatch.setattr(
        setup,
        "EventStream",
        lambda sid, store: SimpleNamespace(sid=sid, file_store=store),
    )
    monkeypatch.setattr(
        setup, "LLMRegistry", lambda config: SimpleNamespace(config=config)
    )
    monkeypatch.setattr(setup, "get_file_store", lambda store, path: "filestore")

    runtime = setup.create_runtime(dummy_config, sid="sid123", headless_mode=False)
    assert runtime.sid == "sid123"
    assert created[0]["headless_mode"] is False


def test_get_provider_tokens(monkeypatch):
    monkeypatch.setenv("GITHUB_TOKEN", "gh")
    provider_tokens = setup.get_provider_tokens()
    assert provider_tokens is not None
    assert setup.ProviderType.GITHUB in provider_tokens


def test_get_provider_tokens_none(monkeypatch):
    monkeypatch.delenv("GITHUB_TOKEN", raising=False)
    assert setup.get_provider_tokens() is None


@pytest.mark.asyncio
async def test_initialize_repository_for_runtime(monkeypatch, dummy_config):
    runtime = DummyRuntime(event_stream=DummyEventStream(), security_analyzer="sec")
    monkeypatch.setattr(setup, "get_provider_tokens", lambda: {"token": "value"})
    monkeypatch.setattr(
        setup, "call_async_from_sync", lambda func, timeout, *args: "repo-path"
    )

    repo_dir = setup.initialize_repository_for_runtime(
        runtime, selected_repository="repo"
    )
    assert repo_dir == "repo-path"
    assert runtime.maybe_run_setup_calls == 1
    assert runtime.maybe_setup_git_calls == 1


@pytest.mark.asyncio
async def test_initialize_repository_for_runtime_with_tokens(monkeypatch):
    runtime = DummyRuntime(event_stream=DummyEventStream(), security_analyzer="sec")
    monkeypatch.setattr(
        setup, "call_async_from_sync", lambda func, timeout, *args: "repo-2"
    )
    repo_dir = setup.initialize_repository_for_runtime(
        runtime,
        immutable_provider_tokens={"token": "provided"},
        selected_repository=None,
    )
    assert repo_dir == "repo-2"


def test_create_memory(monkeypatch):
    runtime = DummyRuntime(
        event_stream=DummyEventStream(), security_analyzer="analyzer"
    )
    memory = DummyMemory()
    monkeypatch.setattr(setup, "Memory", lambda **kwargs: memory)

    result = setup.create_memory(
        runtime=runtime,
        event_stream=DummyEventStream(),
        sid="sid",
        selected_repository="repo",
        repo_directory="dir",
        conversation_instructions="instructions",
        working_dir="/work",
    )

    assert result.instructions == "instructions"
    assert result.runtime_info[2] == "/work"
    assert result.repo_info == ("repo", "dir")


def test_create_agent(monkeypatch, dummy_config):
    class DummyAgentCls(SimpleNamespace):
        def __init__(self, config, llm_registry):
            super().__init__(config=config, llm_registry=llm_registry)

    monkeypatch.setattr(setup.Agent, "get_cls", lambda name: DummyAgentCls)
    llm_registry = SimpleNamespace()
    agent = setup.create_agent(dummy_config, llm_registry)
    assert agent.config.name == "test"
    assert agent.llm_registry is llm_registry


def test_create_controller_restores_state(monkeypatch, dummy_config):
    restored = SimpleNamespace(
        iteration_flag=SimpleNamespace(current_value=1),
        start_id=0,
        end_id=0,
    )
    monkeypatch.setattr(
        setup.State, "restore_from_session", lambda sid, store: restored
    )
    logs = []
    monkeypatch.setattr(
        setup.logger,
        "debug",
        lambda msg, *args: logs.append(msg % args if args else msg),
    )

    runtime = DummyRuntime(event_stream=DummyEventStream(), security_analyzer="sec")
    agent = SimpleNamespace()
    controller, initial_state = setup.create_controller(
        agent=agent,
        runtime=runtime,
        config=dummy_config,
        conversation_stats=SimpleNamespace(),
    )

    assert initial_state is restored
    assert controller.security_analyzer == "sec"
    assert any("restore" in message for message in logs)


def test_create_controller_handles_restore_failure(monkeypatch, dummy_config):
    monkeypatch.setattr(
        setup.State,
        "restore_from_session",
        lambda *args, **kwargs: (_ for _ in ()).throw(RuntimeError("fail")),
    )
    logs = []
    monkeypatch.setattr(
        setup.logger,
        "debug",
        lambda msg, *args: logs.append(msg % args if args else msg),
    )

    runtime = DummyRuntime(event_stream=DummyEventStream(), security_analyzer="sec")
    agent = SimpleNamespace()
    controller, initial_state = setup.create_controller(
        agent=agent,
        runtime=runtime,
        config=dummy_config,
        conversation_stats=SimpleNamespace(),
    )

    assert initial_state is None
    assert any("Cannot restore" in message for message in logs)


def test_generate_sid_length(dummy_config):
    session_id = setup.generate_sid(dummy_config, session_name="short")
    assert len(session_id) <= 32
    assert session_id.startswith("short-")


def test_generate_sid_long_name(dummy_config):
    long_name = "a" * 40
    session_id = setup.generate_sid(dummy_config, session_name=long_name)
    assert len(session_id) == 32
    assert session_id.startswith("a" * 16)


def test_filter_plugins_by_config_config_get_agent_config_exception():
    """Test filter_plugins_by_config when config.get_agent_config raises exception."""
    agent = None
    config = SimpleNamespace()
    config.get_agent_config = Mock(side_effect=Exception("config error"))
    plugins = [SimpleNamespace(name="test")]
    
    # Should not raise, just use all plugins
    result = setup.filter_plugins_by_config(plugins, agent=agent, config=config, agent_cls_name="test_agent")
    assert len(result) == 1


def test_filter_plugins_by_config_no_agent_config():
    """Test filter_plugins_by_config when no agent config is available."""
    agent = None
    config = SimpleNamespace()
    config.get_agent_config = Mock(return_value=None)
    plugins = [SimpleNamespace(name="test")]
    
    result = setup.filter_plugins_by_config(plugins, agent=agent, config=config, agent_cls_name="test_agent")
    # Should use all plugins when no config
    assert len(result) == 1


def test_ensure_agent_class_available_already_registered():
    """Test _ensure_agent_class_available when agent is already registered."""
    with patch("forge.core.setup.Agent._registry", {"test_agent": Mock()}):
        # Should return early if agent is already registered
        setup._ensure_agent_class_available("test_agent")
        # No exception should be raised


def test_create_runtime_with_existing_event_stream(monkeypatch):
    """Test create_runtime when event_stream is provided."""
    config = SimpleNamespace(
        default_agent="test",
        file_store="memory",
        file_store_path=None,
    )
    event_stream = SimpleNamespace(sid="existing-sid")
    
    class TestAgent:
        sandbox_plugins = []
        __name__ = "TestAgent"
    
    monkeypatch.setattr(setup.Agent, "get_cls", lambda name: TestAgent)
    monkeypatch.setattr(setup, "get_runtime_cls", lambda runtime_name: DummyRuntime)
    
    runtime = setup.create_runtime(config, sid="new-sid", event_stream=event_stream)
    
    # Should use existing event_stream's sid (line 143)
    assert runtime.event_stream.sid == "existing-sid"


def test_ensure_agent_class_available_import_fails(monkeypatch):
    """Test _ensure_agent_class_available when import fails."""
    import importlib
    
    monkeypatch.setattr(setup.Agent, "_registry", {})
    original_import = importlib.import_module
    
    def failing_import(name):
        if name == "forge.agenthub":
            raise ImportError("module not found")
        return original_import(name)
    
    monkeypatch.setattr(importlib, "import_module", failing_import)
    
    # Should raise AgentNotRegisteredError if agent still not found after import attempt (lines 293-298)
    with pytest.raises(AgentNotRegisteredError):
        setup._ensure_agent_class_available("nonexistent_agent")


def test_create_agent_agent_not_registered(monkeypatch):
    """Test create_agent when agent is not registered initially."""
    class TestAgent:
        def __init__(self, config, llm_registry):
            self.config = config
            self.llm_registry = llm_registry
    
    config = SimpleNamespace(
        default_agent="test_agent",
        get_agent_config=lambda x: SimpleNamespace(),
        get_llm_config_from_agent=lambda x: None,
    )
    
    call_count = [0]
    def mock_get_cls(name):
        call_count[0] += 1
        if call_count[0] == 1:
            raise AgentNotRegisteredError("test_agent")
        return TestAgent
    
    ensure_called = [False]
    def mock_ensure(name):
        ensure_called[0] = True
    
    monkeypatch.setattr(setup.Agent, "get_cls", mock_get_cls)
    monkeypatch.setattr(setup, "_ensure_agent_class_available", mock_ensure)
    
    llm_registry = SimpleNamespace()
    agent = setup.create_agent(config, llm_registry)
    
    assert ensure_called[0]
    assert agent is not None
    assert isinstance(agent, TestAgent)


def test_create_controller_no_event_stream():
    """Test create_controller when runtime has no event_stream."""
    runtime = SimpleNamespace(event_stream=None)
    agent = SimpleNamespace()
    config = SimpleNamespace()
    
    # Should raise RuntimeError when event_stream is None (line 348)
    with pytest.raises(RuntimeError, match="Runtime does not have an initialized event stream"):
        setup.create_controller(
            agent=agent,
            runtime=runtime,
            config=config,
            conversation_stats=SimpleNamespace(),
        )