from __future__ import annotations

from types import SimpleNamespace

import pytest

from forge.agenthub.codeact_agent.executor import CodeActExecutor
from forge.agenthub.codeact_agent.planner import CodeActPlanner
from forge.agenthub.codeact_agent.safety import CodeActSafetyManager
from forge.controller.tool_pipeline import (
    TelemetryMiddleware,
    ToolInvocationPipeline,
)
from forge.controller.tool_telemetry import ToolTelemetry
from forge.events.action import MessageAction


@pytest.fixture(autouse=True)
def reset_tool_telemetry():
    telemetry = ToolTelemetry.get_instance()
    telemetry.reset_for_test()
    yield
    telemetry.reset_for_test()


class _SafetyStub:
    def __init__(self) -> None:
        self.turn_counter = 0

    def should_enforce_tools(self, last_user_message, state, default: str) -> str:
        return default

    def validate_response(self, response_text, actions):
        return True, None

    def inject_verification_commands(self, actions, turn: int):
        self.turn_counter = turn
        return actions

    def detect_text_hallucination(self, response_text, tools_called, actions):
        return {"hallucinated": False}


def _make_basic_config(**overrides):
    defaults = dict(
        enable_cmd=True,
        enable_think=True,
        enable_finish=True,
        enable_condensation_request=False,
        enable_browsing=True,
        enable_plan_mode=True,
        enable_ultimate_editor=False,
        enable_llm_editor=False,
        enable_editor=True,
    )
    defaults.update(overrides)
    return SimpleNamespace(**defaults)


def _tool_names(tools) -> list[str]:
    names: list[str] = []
    for tool in tools:
        if isinstance(tool, dict):
            names.append(tool["function"]["name"])
        else:
            names.append(getattr(tool, "__name__", tool.__class__.__name__))
    return names


def test_planner_build_toolset_respects_flags():
    config = _make_basic_config(enable_plan_mode=True, enable_editor=True)
    llm = SimpleNamespace(config=SimpleNamespace(model="test-model"))
    safety = _SafetyStub()
    planner = CodeActPlanner(
        config=config,
        llm=llm,
        safety_manager=safety,
    )

    tools = planner.build_toolset()
    names = _tool_names(tools)

    assert "execute_bash" in names
    assert "think" in names
    assert "finish" in names
    assert "task_tracker" in names
    assert "str_replace_editor" in names


def test_executor_fallback_on_stream_error(monkeypatch):
    sentinel_action = object()

    class _LLMStub:
        def __init__(self) -> None:
            self.stream_calls = 0

        def completion(self, **params):
            if params.get("stream", False):
                self.stream_calls += 1
                raise RuntimeError("boom")
            return SimpleNamespace()

    def fake_response_to_actions(response, mcp_tool_names):
        return [sentinel_action]

    monkeypatch.setattr(
        "forge.agenthub.codeact_agent.executor.codeact_function_calling.response_to_actions",
        fake_response_to_actions,
    )

    llm = _LLMStub()
    safety = SimpleNamespace(
        apply=lambda response_text, actions: (True, actions),
    )
    planner = SimpleNamespace(track_tool_usage=lambda actions: None)
    executor = CodeActExecutor(
        llm=llm,
        safety_manager=safety,
        planner=planner,
        mcp_tool_name_provider=lambda: [],
    )

    params = {"messages": [{"role": "user", "content": "Hi"}], "stream": True}
    result = executor.execute(params, event_stream=None)

    assert result.error == "boom"
    assert result.actions == [sentinel_action]


def test_safety_manager_blocks_invalid_actions():
    class _AntiStub:
        def __init__(self) -> None:
            self.turn_counter = 0

        def validate_response(self, response_text, actions):
            return False, "blocked"

        def inject_verification_commands(self, actions, turn):
            self.turn_counter = turn
            return actions

        def should_enforce_tools(self, message, state, default):
            return default

    anti = _AntiStub()
    detector = SimpleNamespace(
        detect_text_hallucination=lambda *args, **kwargs: {"hallucinated": False}
    )
    safety = CodeActSafetyManager(anti, detector)

    proceed, actions = safety.apply("response", [])
    assert proceed is False
    assert isinstance(actions[0], MessageAction)
    assert "blocked" in actions[0].content


def test_safety_manager_adds_warning_for_high_severity():
    class _AntiStub:
        def __init__(self) -> None:
            self.turn_counter = 0

        def validate_response(self, response_text, actions):
            return True, None

        def inject_verification_commands(self, actions, turn):
            self.turn_counter = turn
            return actions

        def should_enforce_tools(self, message, state, default):
            return default

    def fake_detect(*args, **kwargs):
        return {
            "hallucinated": True,
            "severity": "high",
            "claimed_operations": ["edit file"],
            "missing_tools": ["str_replace_editor"],
        }

    safety = CodeActSafetyManager(_AntiStub(), SimpleNamespace(detect_text_hallucination=fake_detect))
    proceed, actions = safety.apply("response", [MessageAction(content="")])

    assert proceed is True
    assert isinstance(actions[0], MessageAction)
    assert "RELIA" in actions[0].content  # contains reliability warning


@pytest.mark.asyncio
async def test_telemetry_middleware_records_success():
    telemetry = ToolTelemetry.get_instance()

    class _DummyController:
        def __init__(self) -> None:
            self.id = "session"
            self.user_id = "user"
            self.event_stream = SimpleNamespace(add_event=lambda *args, **kwargs: None)
            self.agent = SimpleNamespace(
                llm=SimpleNamespace(metrics=SimpleNamespace(accumulated_cost=0.0))
            )

        def log(self, level, message, extra=None):
            return None

        def _get_log_level(self):
            return "info"

    class _DummyAction:
        runnable = True

        def __init__(self) -> None:
            self.action = "dummy_tool"

    controller = _DummyController()
    pipeline = ToolInvocationPipeline(controller, [TelemetryMiddleware(controller)])
    ctx = pipeline.create_context(_DummyAction(), SimpleNamespace())

    await pipeline.run_plan(ctx)
    await pipeline.run_execute(ctx)
    await pipeline.run_observe(ctx, None)

    recent = telemetry.recent_events()
    assert recent, "telemetry should record at least one event"
    recorded = recent[-1]
    assert recorded["tool"] == "dummy_tool"
    assert recorded["outcome"] == "success"

