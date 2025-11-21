from __future__ import annotations

import sys
from types import ModuleType, SimpleNamespace
from typing import Any

import pytest

import forge.controller  # ensure controller fully initialized before agenthub imports

import forge.agenthub.codeact_agent.codeact_agent as module
from forge.agenthub.codeact_agent.codeact_agent import CodeActAgent
from forge.core.config import AgentConfig
from forge.core.message import ImageContent, Message, TextContent
from forge.events.action import AgentFinishAction, MessageAction, CmdRunAction
from forge.events.observation.commands import CmdOutputObservation


class DummyLLM:
    def __init__(self) -> None:
        self.config = SimpleNamespace(model="dummy-model")


class DummyLLMRegistry:
    def __init__(self) -> None:
        self.requests: list[tuple[str, AgentConfig]] = []

    def get_llm_from_agent_config(self, service_id: str, config: AgentConfig) -> DummyLLM:
        self.requests.append((service_id, config))
        return DummyLLM()


class DummyResult:
    def __init__(self, actions=None, error=None, execution_time=0, response=None) -> None:
        self.actions = actions
        self.error = error
        self.execution_time = execution_time
        self.response = response


def _install_hallucination_stubs(monkeypatch: pytest.MonkeyPatch) -> None:
    from forge.agenthub.codeact_agent import anti_hallucination_system as anti_module
    from forge.agenthub.codeact_agent import hallucination_detector as detect_module

    class Anti:
        def __init__(self):
            self.turn_counter = 0

    class Detector:
        pass

    monkeypatch.setattr(anti_module, "AntiHallucinationSystem", Anti)
    monkeypatch.setattr(detect_module, "HallucinationDetector", Detector)


@pytest.fixture
def agent_factory(monkeypatch: pytest.MonkeyPatch):
    _install_hallucination_stubs(monkeypatch)

    refs: dict[str, Any] = {
        "memory": None,
        "planner": None,
        "executor": None,
    }

    class StubMemoryManager:
        def __init__(self, config, llm_registry):
            self.config = config
            self.llm_registry = llm_registry
            self.conversation_memory = object()
            self.saved_states: list[None] = []
            self.updated_states: list[Any] = []
            self.next_condensed = SimpleNamespace(events=[], pending_action=None)
            self.next_messages = [Message(role="user", content=[TextContent(text="hi")])]
            self.initial_message = MessageAction("user")
            self.next_ace_context = None

        def initialize(self, prompt_manager):
            self.prompt_manager = prompt_manager

        def save_context_state(self):
            self.saved_states.append(None)

        def update_context(self, state):
            self.updated_states.append(state)

        def condense_history(self, state):
            return self.next_condensed

        def get_initial_user_message(self, history):
            return self.initial_message

        def build_messages(self, condensed_history, initial_user_message, llm_config):
            return self.next_messages

        def get_ace_playbook_context(self, state):
            return self.next_ace_context

    class StubPlanner:
        def __init__(self, **kwargs):
            self.kwargs = kwargs
            self._llm = kwargs["llm"]
            self.params: list[Any] = []
            self.prompt_records: list[Any] = []

        def build_toolset(self):
            return ["tool"]

        def build_llm_params(self, messages, state, tools, ace_context):
            data = {
                "messages": messages,
                "state": state,
                "tools": tools,
                "ace": ace_context,
            }
            self.params.append(data)
            return data

        def record_prompt_execution(self, **kwargs):
            self.prompt_records.append(kwargs)

    class StubExecutor:
        def __init__(self, **kwargs):
            self.kwargs = kwargs
            self._llm = kwargs["llm"]
            self.calls: list[Any] = []
            self.next_result = DummyResult(
                actions=[MessageAction("plan-action")], error=None, execution_time=0
            )

        def execute(self, params, event_stream):
            self.calls.append((params, event_stream))
            return self.next_result

    def memory_factory(config, llm_registry):
        inst = StubMemoryManager(config, llm_registry)
        refs["memory"] = inst
        return inst

    def planner_factory(*args, **kwargs):
        inst = StubPlanner(**kwargs)
        refs["planner"] = inst
        return inst

    def executor_factory(*args, **kwargs):
        inst = StubExecutor(**kwargs)
        refs["executor"] = inst
        return inst

    monkeypatch.setattr(module, "CodeActMemoryManager", memory_factory)
    monkeypatch.setattr(module, "CodeActPlanner", planner_factory)
    monkeypatch.setattr(module, "CodeActExecutor", executor_factory)

    def _factory(**config_overrides):
        config = AgentConfig()
        for key, value in config_overrides.items():
            if hasattr(config, key):
                setattr(config, key, value)
            else:
                object.__setattr__(config, key, value)
        registry = DummyLLMRegistry()
        agent = CodeActAgent(config=config, llm_registry=registry)
        return agent, refs, registry

    return _factory


def install_prompt_opt_stubs(monkeypatch: pytest.MonkeyPatch):
    stubs: dict[str, Any] = {}

    def _mod(name: str) -> ModuleType:
        mod = ModuleType(name)
        monkeypatch.setitem(sys.modules, name, mod)
        return mod

    pkg = ModuleType("forge.prompt_optimization")
    pkg.__path__ = []
    monkeypatch.setitem(sys.modules, "forge.prompt_optimization", pkg)
    models = _mod("forge.prompt_optimization.models")
    tracker_mod = _mod("forge.prompt_optimization.tracker")
    registry_mod = _mod("forge.prompt_optimization.registry")
    optimizer_mod = _mod("forge.prompt_optimization.optimizer")
    storage_mod = _mod("forge.prompt_optimization.storage")
    tool_opt_mod = _mod("forge.prompt_optimization.tool_optimizer")

    class OptimizationConfig:
        def __init__(self, **kwargs):
            stubs["opt_config"] = kwargs
            for key, value in kwargs.items():
                setattr(self, key, value)

    class PromptRegistry:
        pass

    class PerformanceTracker:
        def __init__(self, weights, history_path=None, history_auto_flush=False):
            stubs["tracker"] = {"weights": weights, "history_path": history_path}

    class PromptOptimizer:
        def __init__(self, registry, tracker, opt_config):
            stubs["optimizer"] = (registry, tracker, opt_config)

    class PromptStorage:
        def __init__(self, config, registry, tracker):
            self.load_calls = 0
            stubs["storage"] = self

        def load_all(self):
            self.load_calls += 1

    class ToolOptimizer:
        def __init__(self, registry, tracker, optimizer):
            stubs["tool_optimizer"] = (registry, tracker, optimizer)

    models.OptimizationConfig = OptimizationConfig
    registry_mod.PromptRegistry = PromptRegistry
    tracker_mod.PerformanceTracker = PerformanceTracker
    optimizer_mod.PromptOptimizer = PromptOptimizer
    storage_mod.PromptStorage = PromptStorage
    tool_opt_mod.ToolOptimizer = ToolOptimizer
    return stubs


def test_prompt_manager_fallback_adds_prefix(agent_factory, monkeypatch):
    monkeypatch.setattr(module.os.path, "exists", lambda _: False)
    agent, _, _ = agent_factory(system_prompt_filename="missing.j2")
    message = agent.prompt_manager.get_system_message(goal="Goal")
    assert message.startswith("You are Forge agent.")


def test_prompt_manager_adds_prefix_when_missing(monkeypatch, agent_factory):
    def fake_get_system_message(self, **context):
        return "Hello world"

    monkeypatch.setattr(
        module.PromptManager, "get_system_message", fake_get_system_message
    )
    agent, _, _ = agent_factory()
    manager = agent._create_prompt_manager()
    result = manager.get_system_message()
    assert result == "You are Forge agent.\nHello world"


def test_initialize_prompt_optimization_sets_components(monkeypatch, agent_factory):
    stubs = install_prompt_opt_stubs(monkeypatch)
    agent, _, _ = agent_factory(enable_prompt_optimization=True)
    assert agent.prompt_optimizer is not None
    assert stubs["storage"].load_calls == 1
    assert agent.tool_optimizer is not None


def test_initialize_prompt_optimization_handles_import_error(agent_factory, monkeypatch):
    real_import = __import__

    def fake_import(name, *args, **kwargs):
        if name.startswith("forge.prompt_optimization"):
            raise ImportError("missing")
        return real_import(name, *args, **kwargs)

    monkeypatch.setattr("builtins.__import__", fake_import)
    agent, _, _ = agent_factory(enable_prompt_optimization=True)
    assert agent.prompt_optimizer is None
    assert agent.tool_optimizer is None


def test_initialize_prompt_optimization_handles_general_exception(agent_factory, monkeypatch):
    install_prompt_opt_stubs(monkeypatch)

    class BadStorage:
        def __init__(self, *args, **kwargs):
            raise RuntimeError("boom")

    monkeypatch.setattr(
        sys.modules["forge.prompt_optimization.storage"], "PromptStorage", BadStorage
    )
    agent, _, _ = agent_factory(enable_prompt_optimization=True)
    assert agent.prompt_optimizer is None
    assert agent.tool_optimizer is None


def test_run_production_health_check_executes(monkeypatch, agent_factory):
    stub_mod = ModuleType("forge.agenthub.codeact_agent.tools.health_check")
    calls: list[bool] = []

    def run_production_health_check(raise_on_failure):
        calls.append(raise_on_failure)

    stub_mod.run_production_health_check = run_production_health_check
    monkeypatch.setitem(
        sys.modules, "forge.agenthub.codeact_agent.tools.health_check", stub_mod
    )

    agent, _, _ = agent_factory(
        production_health_check=True, health_check_prompts=["ping"]
    )
    assert calls == [True]
    assert agent.production_health_check_enabled is True


def test_run_production_health_check_handles_import_error(
    agent_factory, monkeypatch
):
    real_import = __import__

    def fake_import(name, *args, **kwargs):
        if name == "forge.agenthub.codeact_agent.tools.health_check":
            raise ImportError("missing")
        return real_import(name, *args, **kwargs)

    monkeypatch.setattr("builtins.__import__", fake_import)
    agent, _, _ = agent_factory(
        production_health_check=True, health_check_prompts=["ping"]
    )
    assert agent.production_health_check_enabled is True


def test_run_production_health_check_raises_on_runtime_error(
    agent_factory, monkeypatch
):
    stub_mod = ModuleType("forge.agenthub.codeact_agent.tools.health_check")

    def failing_check(*_, **__):
        raise RuntimeError("fail")

    stub_mod.run_production_health_check = failing_check
    monkeypatch.setitem(
        sys.modules, "forge.agenthub.codeact_agent.tools.health_check", stub_mod
    )

    with pytest.raises(RuntimeError):
        agent_factory(production_health_check=True, health_check_prompts=["ping"])


def test_reset_saves_and_updates_context(agent_factory):
    agent, refs, _ = agent_factory()
    state = SimpleNamespace(history=[])
    agent.reset(state)
    assert refs["memory"].saved_states
    assert refs["memory"].updated_states[-1] is state


def test_reset_without_state(agent_factory):
    agent, refs, _ = agent_factory()
    agent.reset()
    assert refs["memory"].updated_states == []


class DummyState:
    def __init__(self, history=None, last_user_message=None):
        self.history = history or []
        self._last = last_user_message

    def get_last_user_message(self):
        return self._last


def test_step_returns_exit_action(agent_factory):
    user = MessageAction("/exit")
    state = DummyState(history=[user], last_user_message=user)
    agent, _, _ = agent_factory()
    result = agent.step(state)
    assert isinstance(result, AgentFinishAction)


def test_step_returns_pending_action(agent_factory):
    agent, _, _ = agent_factory()
    agent.pending_actions.append(MessageAction("pending"))
    result = agent.step(DummyState(history=[]))
    assert result.content == "pending"


def test_step_returns_condensed_pending_action(agent_factory, monkeypatch):
    agent, refs, _ = agent_factory()
    action = MessageAction("from-condensed")
    refs["memory"].next_condensed = SimpleNamespace(events=[], pending_action=action)
    result = agent.step(DummyState(history=[]))
    assert result is action


def test_step_builds_fallback_when_no_actions(agent_factory):
    agent, refs, _ = agent_factory()
    refs["executor"].next_result = DummyResult(
        actions=[],
        response=SimpleNamespace(
            choices=[SimpleNamespace(message=SimpleNamespace(content="fallback"))]
        ),
        error=None,
    )
    result = agent.step(DummyState(history=[]))
    assert isinstance(result, MessageAction)
    assert result.content == "fallback"


def test_build_fallback_action_handles_missing_response(agent_factory):
    agent, _, _ = agent_factory()
    result = DummyResult(actions=[], response=None, error="error")
    fallback = agent._build_fallback_action(result)
    assert fallback.content == ""


def test_step_queues_additional_actions(agent_factory):
    agent, refs, _ = agent_factory()
    refs["executor"].next_result = DummyResult(
        actions=[MessageAction("one"), MessageAction("two")], error=None
    )
    result = agent.step(DummyState(history=[]))
    assert result.content == "one"
    assert agent.pending_actions[0].content == "two"


def test_serialize_messages_handles_non_serializable(agent_factory):
    agent, _, _ = agent_factory()

    class DummyMessage:
        def __init__(self):
            self.role = "user"
            self.content = [TextContent(text="value")]

    serialized = agent._serialize_messages([DummyMessage()])
    assert serialized[0]["content"] == "value"


def test_serialize_messages_handles_message_objects(agent_factory):
    agent, _, _ = agent_factory()
    msg = Message(role="user", content=[TextContent(text="text")])
    serialized = agent._serialize_messages([msg])
    assert serialized[0]["content"] == "text"


def test_sync_executor_llm_updates_reference(agent_factory):
    agent, refs, _ = agent_factory()
    refs["executor"]._llm = object()
    agent._sync_executor_llm()
    assert refs["executor"]._llm is agent.llm


def test_sync_executor_llm_handles_exception(agent_factory):
    agent, _, _ = agent_factory()

    class BadExecutor:
        def __init__(self):
            self._llm = object()

        def __setattr__(self, name, value):
            if name == "_llm" and hasattr(self, "_llm"):
                raise RuntimeError("fail")
            super().__setattr__(name, value)

    agent.executor = BadExecutor()
    agent._sync_executor_llm()


def test_queue_additional_actions(agent_factory):
    agent, _, _ = agent_factory()
    agent._queue_additional_actions([MessageAction("extra")])
    assert agent.pending_actions[0].content == "extra"


def test_check_exit_command_no_exit(agent_factory):
    agent, _, _ = agent_factory()
    action = agent._check_exit_command(DummyState(history=[], last_user_message=None))
    assert action is None


def test_response_to_actions_delegates(monkeypatch, agent_factory):
    recorded: list[Any] = []

    def fake_response_to_actions(response, mcp_tool_names):
        recorded.append((response, mcp_tool_names))
        return ["ok"]

    monkeypatch.setattr(module.codeact_function_calling, "response_to_actions", fake_response_to_actions)
    agent, _, _ = agent_factory()
    agent.mcp_tools = {"tool-a": object()}
    result = agent.response_to_actions("resp")
    assert result == ["ok"]
    assert recorded[0][1] == ["tool-a"]


def test_get_messages_injects_placeholders(agent_factory):
    agent, refs, _ = agent_factory()
    run = CmdRunAction(command="ls")
    obs = CmdOutputObservation(content="done", command="ls")
    metadata = SimpleNamespace(
        tool_call_id="abc", function_name="cmd", total_calls_in_response=1
    )
    run.tool_call_metadata = metadata
    obs.tool_call_metadata = metadata
    messages = agent._get_messages([run, obs], MessageAction("user"))
    assert messages[-2].role == "assistant"
    assert messages[-1].role == "tool"


def test_step_uses_ace_context(agent_factory):
    agent, refs, _ = agent_factory()
    refs["memory"].next_ace_context = "ACE"
    agent.step(DummyState(history=[]))
    assert refs["planner"].params[-1]["ace"] == "ACE"

