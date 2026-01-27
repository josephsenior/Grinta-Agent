from __future__ import annotations

import asyncio
import types
from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest

from forge.controller.services.action_service import ActionService
from forge.controller.services.action_execution_service import ActionExecutionService
from forge.controller.services.pending_action_service import PendingActionService
from forge.controller.services.controller_context import ControllerContext
from forge.controller.services.lifecycle_service import LifecycleService
from forge.controller.services.observation_service import ObservationService
from forge.controller.services.recovery_service import RecoveryService, ErrorType
from forge.events import EventSource
from forge.events.action import MessageAction
from forge.events.observation import NullObservation
from forge.core.schemas import AgentState
from forge.controller.services.recovery_service import RecoveryService


class DummyPipeline:
    def __init__(self) -> None:
        self.verify_calls: list[Any] = []
        self.observe_calls: list[Any] = []

    async def run_verify(self, ctx):
        self.verify_calls.append(ctx)

    async def run_execute(self, ctx):
        pass

    async def run_observe(self, ctx, observation):
        self.observe_calls.append((ctx, observation))


def make_controller(**overrides):
    state = types.SimpleNamespace(
        confirmation_mode=False,
        agent_state=AgentState.RUNNING,
        budget_flag=types.SimpleNamespace(max_value=5),
        metrics=types.SimpleNamespace(
            token_usages=[], accumulated_token_usage=types.SimpleNamespace(prompt_tokens=0, completion_tokens=0)
        ),
        history=[],
        iteration_flag=types.SimpleNamespace(current_value=0),
        delegate_level=0,
        get_local_metrics=lambda: {"cost": 0},
    )
    controller = types.SimpleNamespace(
        state=state,
        agent=types.SimpleNamespace(
            config=types.SimpleNamespace(cli_mode=True),
            llm=types.SimpleNamespace(config=types.SimpleNamespace(max_message_chars=4096)),
            llm_registry=None,
        ),
        tool_pipeline=None,
        telemetry_service=MagicMock(),
        event_stream=MagicMock(),
        conversation_stats=types.SimpleNamespace(
            get_combined_metrics=lambda: types.SimpleNamespace(
                accumulated_cost=1,
                accumulated_token_usage={"prompt_tokens": 1, "completion_tokens": 2},
                max_budget_per_task=10,
            )
        ),
        log=lambda *a, **k: None,
        _bind_action_context=lambda *a, **k: None,
        _cleanup_action_context=lambda *a, **k: None,
        set_agent_state_to=AsyncMock(),
        state_tracker=types.SimpleNamespace(get_metrics_snapshot=lambda: {"snapshot": True}),
        id="session-1",
        user_id="user",
        event_stream_history=[],
        on_event=lambda *a, **k: None,
        set_initial_state=None,
        _run_or_schedule=None,
        agent_to_llm_config={},
        agent_configs={},
    )
    controller.event_stream.get_latest_event_id = lambda: 0
    controller.file_store = None
    controller.headless_mode = True
    controller.security_analyzer = None
    controller._initial_max_iterations = 5
    controller._initial_max_budget_per_task = 10.0
    def _set_initial_state(**kwargs):
        controller.state_tracker.state = state

    controller.set_initial_state = _set_initial_state

    def _run_or_schedule(coro):
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                loop.create_task(coro)
            else:
                loop.run_until_complete(coro)
        except RuntimeError:
            asyncio.run(coro)

    controller._run_or_schedule = _run_or_schedule
    controller.__dict__.update(overrides)
    return controller


def _recovery_stages(controller):
    calls = getattr(controller.event_stream, "add_event", None)
    if not calls:
        return []
    stages = []
    for call in controller.event_stream.add_event.call_args_list:
        if not call.args:
            continue
        event = call.args[0]
        if isinstance(event, dict) and event.get("type") == "controller_recovery":
            stages.append(event.get("stage"))
        else:
            content = getattr(event, "content", "")
            if isinstance(content, str) and content.startswith("[Recovery]"):
                for token in content.split():
                    if token.startswith("stage="):
                        stages.append(token.split("=", 1)[1])
                        break
    return stages


def test_lifecycle_service_initializes_core_attributes():
    controller = make_controller()
    event_stream = MagicMock()
    event_stream.sid = "sid-123"
    service = LifecycleService(controller)

    service.initialize_core_attributes(
        sid=None,
        event_stream=event_stream,
        agent=types.SimpleNamespace(name="agent"),
        user_id="user-1",
        file_store="store",
        headless_mode=True,
        is_delegate=False,
        conversation_stats=types.SimpleNamespace(),
        status_callback=None,
        security_analyzer="sec",
    )

    assert controller.id == "sid-123"
    event_stream.subscribe.assert_called_once()


def test_lifecycle_service_skips_subscription_for_delegate():
    controller = make_controller()
    event_stream = MagicMock()
    service = LifecycleService(controller)

    service.initialize_core_attributes(
        sid="override-id",
        event_stream=event_stream,
        agent=types.SimpleNamespace(name="agent"),
        user_id=None,
        file_store=None,
        headless_mode=False,
        is_delegate=True,
        conversation_stats=types.SimpleNamespace(),
        status_callback=None,
        security_analyzer=None,
    )

    assert controller.id == "override-id"
    event_stream.subscribe.assert_not_called()


def test_lifecycle_service_initializes_state_tracking():
    controller = make_controller()
    service = LifecycleService(controller)

    service.initialize_state_and_tracking(
        sid="sid",
        file_store="store",
        user_id="user",
        initial_state=types.SimpleNamespace(),
        conversation_stats=types.SimpleNamespace(),
        iteration_delta=3,
        budget_per_task_delta=5.0,
        confirmation_mode=True,
        replay_events=[types.SimpleNamespace(source=EventSource.AGENT)],
    )

    assert controller.state_tracker.state is controller.state


@pytest.mark.asyncio
async def test_action_service_emits_events_and_metrics():
    controller = make_controller()
    context = ControllerContext(controller)
    observation_service = MagicMock()
    safety_service = MagicMock()
    pending_service = PendingActionService(context, timeout=10)
    confirmation_service = types.SimpleNamespace(
        evaluate_action=AsyncMock(),
        handle_pending_confirmation=AsyncMock(return_value=False),
    )
    service = ActionService(
        context,
        observation_service,
        pending_service,
        confirmation_service,
    )

    action = MessageAction(content="ping")
    await service.run(action, None)

    observation_service.prepare_metrics_for_action.assert_called_once_with(action)
    controller.event_stream.add_event.assert_called_once_with(
        action, action.source or EventSource.AGENT
    )


@pytest.mark.asyncio
async def test_action_service_handles_blocked_context():
    controller = make_controller()
    pipeline = types.SimpleNamespace(
        run_plan=AsyncMock(),
        run_verify=AsyncMock(side_effect=lambda ctx: setattr(ctx, "blocked", True)),
    )
    controller.tool_pipeline = pipeline
    ctx = types.SimpleNamespace(blocked=False)
    action = MessageAction(content="needs verify")
    action.runnable = True  # override default to exercise verify path

    context = ControllerContext(controller)
    observation_service = MagicMock()
    pending_service = PendingActionService(context, timeout=10)
    confirmation_service = types.SimpleNamespace(
        evaluate_action=AsyncMock(),
        handle_pending_confirmation=AsyncMock(return_value=False),
    )
    service = ActionService(
        context,
        observation_service,
        pending_service,
        confirmation_service,
    )

    await service.run(action, ctx)

    controller.telemetry_service.handle_blocked_invocation.assert_called_once_with(action, ctx)
    controller.event_stream.add_event.assert_not_called()


@pytest.mark.asyncio
async def test_observation_service_routes_pending_action():
    pipeline = DummyPipeline()
    controller = make_controller(tool_pipeline=pipeline)
    controller._action_contexts_by_event_id = {5: "ctx5"}
    context = ControllerContext(controller)
    obs_service = ObservationService(context)
    fake_action_service = MagicMock()
    pending = MessageAction(content="pending")
    pending.id = 5
    fake_action_service.get_pending_action.return_value = pending
    obs_service.set_action_service(fake_action_service)

    observation = NullObservation("done")
    observation.cause = 5
    await obs_service.handle_observation(observation)

    fake_action_service.set_pending_action.assert_called_once_with(None)
    assert pipeline.observe_calls == [("ctx5", observation)]


def test_observation_service_prepares_metrics_snapshot():
    controller = make_controller()
    context = ControllerContext(controller)
    obs_service = ObservationService(context)
    action = MessageAction(content="metrics")
    obs_service.prepare_metrics_for_action(action)

    assert action.llm_metrics.accumulated_cost == 1
    assert action.llm_metrics.max_budget_per_task == 5


@pytest.mark.asyncio
async def test_recovery_service_handles_retry(monkeypatch):
    controller = make_controller()
    controller.state.last_error = ""
    controller.status_callback = None
    controller.circuit_breaker_service = MagicMock()
    controller.set_agent_state_to = AsyncMock()

    retry_service = types.SimpleNamespace(
        retry_count=0,
        increment_retry_count=lambda: None,
        schedule_retry_after_failure=AsyncMock(return_value=True),
    )
    context = ControllerContext(controller)
    service = RecoveryService(context, retry_service)

    monkeypatch.setattr(
        "forge.controller.services.recovery_service.ErrorRecoveryStrategy.classify_error",
        lambda exc: ErrorType.UNKNOWN_ERROR,
    )
    monkeypatch.setattr(
        "forge.controller.services.recovery_service.RecoveryService._try_error_recovery",
        AsyncMock(return_value=False),
    )

    exc = RuntimeError("boom")
    await service.react_to_exception(exc)
    await asyncio.sleep(0)

    controller.set_agent_state_to.assert_awaited_with(AgentState.PAUSED)
    stages = _recovery_stages(controller)
    assert "start" in stages
    assert "retry_deferred" in stages


@pytest.mark.asyncio
async def test_recovery_service_handles_non_recoverable(monkeypatch):
    controller = make_controller()
    controller.status_callback = None
    controller.circuit_breaker_service = MagicMock()
    controller.set_agent_state_to = AsyncMock()

    retry_service = types.SimpleNamespace(
        retry_count=0,
        increment_retry_count=lambda: None,
        schedule_retry_after_failure=AsyncMock(return_value=False),
    )
    context = ControllerContext(controller)
    service = RecoveryService(context, retry_service)

    monkeypatch.setattr(
        "forge.controller.services.recovery_service.ErrorRecoveryStrategy.classify_error",
        lambda exc: ErrorType.UNKNOWN_ERROR,
    )
    monkeypatch.setattr(
        "forge.controller.services.recovery_service.RecoveryService._try_error_recovery",
        AsyncMock(return_value=False),
    )

    exc = RuntimeError("fail-fast")
    await service.react_to_exception(exc)
    await asyncio.sleep(0)

    controller.set_agent_state_to.assert_awaited_with(AgentState.ERROR)
    stages = _recovery_stages(controller)
    assert "start" in stages
    assert "halted" in stages


