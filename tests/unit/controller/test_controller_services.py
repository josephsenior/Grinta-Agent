from __future__ import annotations

import types
from typing import TYPE_CHECKING, Any, cast
from unittest.mock import MagicMock

import pytest

from forge.controller.services.autonomy_service import AutonomyService
from forge.controller.services.circuit_breaker_service import CircuitBreakerService
from forge.controller.services.lifecycle_service import LifecycleService
from forge.controller.services.retry_service import RetryService
from forge.controller.services.stuck_detection_service import StuckDetectionService
from forge.controller.services.telemetry_service import TelemetryService
from forge.controller.tool_pipeline import ToolInvocationContext

if TYPE_CHECKING:
    from forge.controller.agent import Agent
    from forge.controller.agent_controller import AgentController
    from forge.controller.tool_pipeline import ToolInvocationPipeline
    from forge.controller.stuck_detection_service import StuckDetector
    from forge.controller.state.state_tracker import StateTracker
    from forge.controller.services.retry_service import RetryService as RetryServiceType
    from forge.controller.services.stuck_detection_service import (
        StuckDetectionService as StuckDetectionServiceType,
    )
    from forge.controller.services.autonomy_service import AutonomyService as AutonomyServiceType
    from forge.controller.services.circuit_breaker_service import (
        CircuitBreakerService as CircuitBreakerServiceType,
    )
    from forge.controller.services.telemetry_service import TelemetryService as TelemetryServiceType
    from forge.controller.services.lifecycle_service import LifecycleService as LifecycleServiceType
    from forge.controller.state.state import State
    from forge.controller.state.state_tracker import StateTracker
    from forge.controller.replay import ReplayManager
    from forge.events import Event
    from forge.events.action import Action
    from forge.events.observation import Observation
    from forge.server.services.conversation_stats import ConversationStats
    from forge.storage.files import FileStore


class DummyEventStream:
    def __init__(self, sid: str = "session-123") -> None:
        self.sid = sid
        self.subscriptions: list[tuple] = []
        self.events: list[tuple] = []

    def subscribe(self, *args: object) -> None:
        self.subscriptions.append(args)

    def add_event(self, event: object, source: object) -> None:
        self.events.append((event, source))


def test_lifecycle_service_core_initialization(monkeypatch: pytest.MonkeyPatch) -> None:
    stream = DummyEventStream()
    controller = cast(
        "AgentController",
        types.SimpleNamespace(on_event=lambda *a, **k: None),
    )

    service = LifecycleService(controller)
    service.initialize_core_attributes(
        sid=None,
        event_stream=stream,
        agent=cast("Agent", types.SimpleNamespace()),
        user_id="user",
        file_store=cast("FileStore", types.SimpleNamespace()),
        headless_mode=True,
        is_delegate=False,
        conversation_stats=cast("ConversationStats", types.SimpleNamespace()),
        status_callback=lambda *a, **k: None,
        security_analyzer=types.SimpleNamespace(),
    )

    assert controller.event_stream is stream
    assert controller.id == stream.sid
    assert controller.user_id == "user"
    assert controller._closed is False
    assert stream.subscriptions, "subscription should be registered when not delegate"


def test_lifecycle_service_state_initialization(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: dict[str, object] = {}

    class StubTracker:
        def __init__(self, sid, file_store, user_id) -> None:
            self.state = "tracker-state"
            self.args = (sid, file_store, user_id)

    monkeypatch.setattr(
        "forge.controller.services.lifecycle_service.StateTracker", StubTracker
    )
    monkeypatch.setattr(
        "forge.controller.services.lifecycle_service.ReplayManager",
        lambda events: ("replay-manager", events),
    )

    def set_initial_state(**kwargs):
        calls.update(kwargs)

    controller = cast(
        "AgentController",
        types.SimpleNamespace(set_initial_state=set_initial_state),
    )
    service = LifecycleService(controller)
    service.initialize_state_and_tracking(
        sid="abc",
        file_store=cast("FileStore", types.SimpleNamespace()),
        user_id="user",
        initial_state=cast("State", types.SimpleNamespace()),
        conversation_stats=cast("ConversationStats", types.SimpleNamespace()),
        iteration_delta=10,
        budget_per_task_delta=1.5,
        confirmation_mode=True,
        replay_events=[cast("Event", types.SimpleNamespace())],
    )

    tracker = cast(Any, controller.state_tracker)
    assert tracker.args == ("abc", "fs", "user")
    assert controller.state == "tracker-state"
    assert controller._replay_manager == ("replay-manager", ["event"])
    assert not hasattr(controller, "_stuck_detector")
    assert calls["state"] == "initial"
    assert calls["max_iterations"] == 10
    assert calls["max_budget_per_task"] == 1.5
    assert controller.confirmation_mode is True


def test_autonomy_service_with_missing_config(monkeypatch: pytest.MonkeyPatch) -> None:
    controller = cast(
        "AgentController",
        types.SimpleNamespace(
            retry_service=MagicMock(),
            circuit_breaker_service=MagicMock(),
            _add_system_message=lambda: None,
        ),
    )

    class FakeAgent:
        config = None

    service = AutonomyService(controller)
    service.initialize(cast(Any, FakeAgent()))

    retry_service = cast(Any, controller.retry_service)
    circuit_service = cast(Any, controller.circuit_breaker_service)
    retry_service.reset_retry_metrics.assert_called_once()
    circuit_service.reset.assert_called_once()
    circuit_service.configure.assert_not_called()
    assert controller.autonomy_controller is None
    assert controller.safety_validator is None
    assert controller.task_validator is None
    assert controller.PENDING_ACTION_TIMEOUT == 120.0


def test_autonomy_service_with_full_config(monkeypatch: pytest.MonkeyPatch) -> None:
    controller = cast(
        "AgentController",
        types.SimpleNamespace(
            retry_service=MagicMock(),
            circuit_breaker_service=MagicMock(),
            _add_system_message=lambda: None,
        ),
    )

    monkeypatch.setattr(
        "forge.controller.autonomy.AutonomyController",
        lambda config: ("autonomy", config),
    )
    monkeypatch.setattr(
        "forge.controller.safety_validator.SafetyValidator",
        lambda config: ("safety", config),
    )
    monkeypatch.setattr(
        "forge.validation.task_validator.CompositeValidator",
        lambda validators, min_confidence, require_all_pass: (
            "validator",
            len(validators),
            min_confidence,
            require_all_pass,
        ),
    )
    monkeypatch.setattr(
        "forge.validation.task_validator.GitDiffValidator",
        lambda: "git",
    )
    monkeypatch.setattr(
        "forge.validation.task_validator.TestPassingValidator",
        lambda: "tests",
    )

    class FakeAgentConfig:
        pass

    monkeypatch.setattr(
        "forge.core.config.agent_config.AgentConfig", FakeAgentConfig, raising=False
    )

    class AgentConfigStub(FakeAgentConfig):
        safety = types.SimpleNamespace(enable_mandatory_validation=True)
        enable_completion_validation = True
        enable_circuit_breaker = True
        max_consecutive_errors = 7
        max_high_risk_actions = 9
        max_stuck_detections = 2

    class FakeAgent:
        config = AgentConfigStub()

    service = AutonomyService(controller)
    service.initialize(cast(Any, FakeAgent()))

    auto = cast(Any, controller.autonomy_controller)
    safety = cast(Any, controller.safety_validator)
    task_validator = cast(Any, controller.task_validator)
    retry_service = cast(Any, controller.retry_service)
    circuit_service = cast(Any, controller.circuit_breaker_service)

    assert auto[0] == "autonomy"
    assert safety[0] == "safety"
    assert task_validator[0] == "validator"
    retry_service.reset_retry_metrics.assert_called_once()
    circuit_service.reset.assert_called_once()
    circuit_service.configure.assert_called_once()
    configured_arg = circuit_service.configure.call_args.args[0]
    assert isinstance(configured_arg, AgentConfigStub)


def test_telemetry_service_handle_blocked_invocation(monkeypatch: pytest.MonkeyPatch) -> None:
    telemetry_calls: list[tuple] = []

    class StubTelemetry:
        def on_blocked(self, ctx, reason=None) -> None:
            telemetry_calls.append((ctx, reason))

    monkeypatch.setattr(
        "forge.controller.tool_telemetry.ToolTelemetry",
        types.SimpleNamespace(get_instance=lambda: StubTelemetry()),
    )

    controller = cast(
        "AgentController",
        types.SimpleNamespace(
            _cleanup_action_context=lambda ctx, action=None: telemetry_calls.append(
                ("cleanup", action)
            ),
            event_stream=types.SimpleNamespace(
                add_event=lambda *args: telemetry_calls.append(("event", args))
            ),
            _pending_action=None,
        ),
    )

    action = cast("Action", types.SimpleNamespace(id=1))
    ctx = ToolInvocationContext(
        controller=controller,
        action=action,
        state=cast("State", types.SimpleNamespace()),
    )
    ctx.block_reason = "blocked"
    service = TelemetryService(controller)
    service.handle_blocked_invocation(action=action, ctx=ctx)

    assert telemetry_calls[0][0] == "cleanup"
    assert telemetry_calls[1][0] is ctx
    assert telemetry_calls[-1][0] == "event"
    assert controller._pending_action is None


def test_retry_service_counters() -> None:
    controller = cast(
        "AgentController",
        types.SimpleNamespace(
            _closed=False,
        ),
    )
    service = RetryService(controller)
    assert service.retry_count == 0
    service.increment_retry_count()
    assert service.retry_count == 1
    service.reset_retry_metrics()
    assert service.retry_count == 0
    assert service.retry_pending is False


@pytest.mark.asyncio
async def test_retry_service_schedule_without_queue(monkeypatch: pytest.MonkeyPatch) -> None:
    controller = cast(
        "AgentController",
        types.SimpleNamespace(
            _closed=False,
        ),
    )
    service = RetryService(controller)
    monkeypatch.setattr(
        "forge.controller.services.retry_service.get_retry_queue", lambda: None
    )

    result = await service.schedule_retry_after_failure(RuntimeError("boom"))
    assert result is False


def test_stuck_detection_service_basic(monkeypatch: pytest.MonkeyPatch) -> None:
    detector = MagicMock()
    detector.is_stuck.return_value = True
    monkeypatch.setattr(
        "forge.controller.services.stuck_detection_service.StuckDetector",
        lambda state: detector,
    )

    controller = cast(
        "AgentController",
        types.SimpleNamespace(
            state=cast("State", types.SimpleNamespace()), headless_mode=True, delegate=None
        ),
    )
    service = StuckDetectionService(controller)
    service.initialize(controller.state)

    assert service.is_stuck() is True
    detector.is_stuck.assert_called_once()


def test_stuck_detection_service_considers_delegate(monkeypatch: pytest.MonkeyPatch) -> None:
    detector = MagicMock()
    detector.is_stuck.return_value = False
    monkeypatch.setattr(
        "forge.controller.services.stuck_detection_service.StuckDetector",
        lambda state: detector,
    )

    delegate_service = MagicMock()
    delegate_service.is_stuck.return_value = True
    delegate = types.SimpleNamespace(stuck_service=delegate_service)
    controller = cast(
        "AgentController",
        types.SimpleNamespace(
            state=cast("State", types.SimpleNamespace()),
            headless_mode=False,
            delegate=delegate,
        ),
    )

    service = StuckDetectionService(controller)
    service.initialize(controller.state)

    assert service.is_stuck() is True
    delegate_service.is_stuck.assert_called_once()


def test_circuit_breaker_service_configuration(monkeypatch: pytest.MonkeyPatch) -> None:
    circuit_breaker = MagicMock()

    def record_config(**kwargs: Any) -> types.SimpleNamespace:
        return types.SimpleNamespace(**kwargs)

    monkeypatch.setattr(
        "forge.controller.circuit_breaker.CircuitBreaker",
        lambda config: circuit_breaker,
    )
    monkeypatch.setattr(
        "forge.controller.circuit_breaker.CircuitBreakerConfig",
        record_config,
    )

    controller = cast(
        "AgentController",
        types.SimpleNamespace(state=cast("State", types.SimpleNamespace())),
    )
    service = CircuitBreakerService(controller)

    service.reset()
    assert service.circuit_breaker is None
    assert getattr(controller, "circuit_breaker") is None

    agent_config = cast(
        Any,
        types.SimpleNamespace(
            enable_circuit_breaker=True,
            max_consecutive_errors=7,
            max_high_risk_actions=9,
            max_stuck_detections=2,
        ),
    )
    circuit_breaker.check.return_value = "check-result"

    service.configure(agent_config)
    assert service.check() == "check-result"
    service.record_error(RuntimeError("oops"))
    cast(Any, circuit_breaker).record_error.assert_called_once()
    service.record_success()
    cast(Any, circuit_breaker).record_success.assert_called_once()
    service.record_high_risk_action("HIGH")
    cast(Any, circuit_breaker).record_high_risk_action.assert_called_once_with("HIGH")
    service.record_stuck_detection()
    cast(Any, circuit_breaker).record_stuck_detection.assert_called_once()

