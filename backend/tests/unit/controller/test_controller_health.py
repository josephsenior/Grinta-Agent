from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import Mock

import pytest

from forge.controller.health import (
    _agent_state_warnings,
    _budget_health,
    _budget_warnings,
    _circuit_breaker_health,
    _circuit_near_limit,
    _circuit_warnings,
    _collect_event_stream_stats,
    _controller_state,
    _extract_agent_state,
    _is_stuck,
    _iteration_health,
    _iteration_warnings,
    _retry_health,
    _retry_warnings,
    _stuck_warnings,
    _sync_budget_metrics,
    BudgetHealth,
    CircuitBreakerHealth,
    collect_controller_health,
    IterationHealth,
    RetryHealth,
)
from forge.core.schemas import AgentState


class DummyIterationFlag:
    def __init__(self, current: int, max_value: int) -> None:
        self.current_value = current
        self.max_value = max_value


class DummyBudgetFlag:
    def __init__(self, current: float, max_value: float) -> None:
        self.current_value = current
        self.max_value = max_value


class DummyRetryService:
    def __init__(self) -> None:
        self._retry_queue = object()
        self._retry_worker_task = SimpleNamespace(done=lambda: False)
        self._retry_pending = True
        self._retry_count = 2

    @property
    def retry_pending(self) -> bool:
        return self._retry_pending

    @property
    def retry_count(self) -> int:
        return self._retry_count


class DummyCircuitBreakerService:
    def __init__(self) -> None:
        self.circuit_breaker = SimpleNamespace(
            config=SimpleNamespace(
                max_consecutive_errors=5,
                max_high_risk_actions=10,
                max_stuck_detections=3,
                error_rate_window=10,
            ),
            consecutive_errors=4,
            high_risk_action_count=1,
            stuck_detection_count=0,
        )

    def check(self):
        return SimpleNamespace(tripped=False, reason="ok", action="continue")


class DummyStuckService:
    def __init__(self, stuck: bool) -> None:
        self._stuck = stuck

    def is_stuck(self) -> bool:
        return self._stuck


class DummyStateTracker:
    def sync_budget_flag_with_metrics(self) -> None:  # pragma: no cover - noop
        return None


class DummyEventStream:
    def get_stats(self) -> dict[str, int]:
        return {"queue_size": 3, "enqueued": 10}


def test_collect_controller_health_snapshot():
    state = SimpleNamespace(
        agent_state=AgentState.RUNNING,
        last_error="LLMError",
        iteration_flag=DummyIterationFlag(current=12, max_value=10),
        budget_flag=DummyBudgetFlag(current=15.0, max_value=10.0),
    )
    controller = SimpleNamespace(
        id="session-123",
        state=state,
        state_tracker=DummyStateTracker(),
        retry_service=DummyRetryService(),
        circuit_breaker_service=DummyCircuitBreakerService(),
        stuck_detection_service=DummyStuckService(stuck=True),
        event_stream=DummyEventStream(),
        _pending_action=None,
    )

    snapshot = collect_controller_health(controller)

    assert snapshot["controller_id"] == "session-123"
    assert snapshot["state"]["agent_state"] == AgentState.RUNNING.value
    assert snapshot["state"]["iteration"]["limit_hit"] is True
    assert snapshot["state"]["budget"]["limit_hit"] is True
    assert snapshot["services"]["retry"]["pending"] is True
    assert snapshot["services"]["circuit_breaker"]["enabled"] is True
    assert snapshot["services"]["stuck_detection"]["is_stuck"] is True
    assert snapshot["event_stream"]["queue_size"] == 3
    assert "iteration_limit_reached" in snapshot["warnings"]
    assert "budget_limit_reached" in snapshot["warnings"]
    assert "retry_pending" in snapshot["warnings"]
    assert "stuck_detector_triggered" in snapshot["warnings"]


def test_iteration_health_no_flag():
    state = SimpleNamespace()
    result = _iteration_health(state)
    assert result is None


def test_budget_health_no_flag():
    state = SimpleNamespace()
    result = _budget_health(state)
    assert result is None


def test_retry_health_no_service():
    controller = SimpleNamespace()
    result = _retry_health(controller)
    assert result is None


def test_circuit_breaker_health_no_service():
    controller = SimpleNamespace()
    result = _circuit_breaker_health(controller)
    assert result is None


def test_circuit_breaker_health_no_breaker():
    service = SimpleNamespace(circuit_breaker=None)
    controller = SimpleNamespace(circuit_breaker_service=service)
    result = _circuit_breaker_health(controller)
    assert result is not None
    assert result.enabled is False


def test_circuit_breaker_health_with_config():
    config = SimpleNamespace(
        max_consecutive_errors=5,
        max_high_risk_actions=10,
        max_stuck_detections=3,
        error_rate_window=10,
    )
    breaker = SimpleNamespace(
        config=config,
        consecutive_errors=4,
        high_risk_action_count=1,
        stuck_detection_count=0,
    )
    service = SimpleNamespace(
        circuit_breaker=breaker,
        check=lambda: SimpleNamespace(tripped=True, reason="test", action="stop"),
    )
    controller = SimpleNamespace(circuit_breaker_service=service)
    result = _circuit_breaker_health(controller)
    assert result is not None
    assert result.enabled is True
    assert result.max_consecutive_errors == 5
    assert result.max_high_risk_actions == 10
    assert result.max_stuck_detections == 3
    assert result.error_rate_window == 10
    assert result.last_check is not None
    assert result.last_check["tripped"] is True


def test_circuit_breaker_health_check_exception():
    breaker = SimpleNamespace(
        config=None,
        consecutive_errors=4,
        high_risk_action_count=1,
        stuck_detection_count=0,
    )
    service = SimpleNamespace(
        circuit_breaker=breaker,
        check=lambda: (_ for _ in ()).throw(Exception("test error")),
    )
    controller = SimpleNamespace(circuit_breaker_service=service)
    result = _circuit_breaker_health(controller)
    assert result is not None
    assert result.enabled is True
    assert result.last_check is None


def test_circuit_breaker_health_check_returns_none():
    breaker = SimpleNamespace(
        config=None,
        consecutive_errors=4,
        high_risk_action_count=1,
        stuck_detection_count=0,
    )
    service = SimpleNamespace(circuit_breaker=breaker, check=lambda: None)
    controller = SimpleNamespace(circuit_breaker_service=service)
    result = _circuit_breaker_health(controller)
    assert result is not None
    assert result.enabled is True
    assert result.last_check is None


def test_sync_budget_metrics_exception():
    state_tracker = Mock()
    state_tracker.sync_budget_flag_with_metrics.side_effect = Exception("test")
    controller = SimpleNamespace(state_tracker=state_tracker)
    _sync_budget_metrics(controller)
    state_tracker.sync_budget_flag_with_metrics.assert_called_once()


def test_sync_budget_metrics_no_tracker():
    controller = SimpleNamespace()
    _sync_budget_metrics(controller)


def test_collect_event_stream_stats_no_stream():
    controller = SimpleNamespace()
    result = _collect_event_stream_stats(controller)
    assert result == {}


def test_collect_event_stream_stats_no_get_stats():
    controller = SimpleNamespace(event_stream=SimpleNamespace())
    result = _collect_event_stream_stats(controller)
    assert result == {}


def test_collect_event_stream_stats_exception():
    event_stream = Mock()
    event_stream.get_stats.side_effect = Exception("test")
    controller = SimpleNamespace(event_stream=event_stream)
    result = _collect_event_stream_stats(controller)
    assert result == {}


def test_is_stuck_no_service():
    controller = SimpleNamespace()
    result = _is_stuck(controller)
    assert result is False


def test_is_stuck_no_method():
    controller = SimpleNamespace(stuck_detection_service=SimpleNamespace())
    result = _is_stuck(controller)
    assert result is False


def test_is_stuck_exception():
    stuck_service = Mock()
    stuck_service.is_stuck.side_effect = Exception("test")
    controller = SimpleNamespace(stuck_detection_service=stuck_service)
    result = _is_stuck(controller)
    assert result is False


def test_iteration_warnings_limit_hit():
    iteration = IterationHealth(current=10, max=10, limit_hit=True)
    result = _iteration_warnings(iteration)
    assert result == ["iteration_limit_reached"]


def test_budget_warnings_limit_hit():
    budget = BudgetHealth(current=10.0, max=10.0, limit_hit=True)
    result = _budget_warnings(budget)
    assert result == ["budget_limit_reached"]


def test_retry_warnings_pending():
    retry = RetryHealth(enabled=True, pending=True, retry_count=1, worker_running=False)
    result = _retry_warnings(retry)
    assert result == ["retry_pending"]


def test_circuit_warnings_none():
    result = _circuit_warnings(None)
    assert result == []


def test_circuit_warnings_tripped():
    circuit_breaker = CircuitBreakerHealth(
        enabled=True,
        last_check={"tripped": True, "reason": "test", "action": "stop"},
    )
    result = _circuit_warnings(circuit_breaker)
    assert result == ["circuit_breaker_tripped"]


def test_circuit_warnings_near_limit():
    circuit_breaker = CircuitBreakerHealth(
        enabled=True,
        consecutive_errors=4,
        max_consecutive_errors=5,
        last_check={"tripped": False},
    )
    result = _circuit_warnings(circuit_breaker)
    assert result == ["circuit_breaker_near_limit"]


def test_circuit_warnings_not_near_limit():
    circuit_breaker = CircuitBreakerHealth(
        enabled=True,
        consecutive_errors=2,
        max_consecutive_errors=5,
        last_check={"tripped": False},
    )
    result = _circuit_warnings(circuit_breaker)
    assert result == []


def test_circuit_near_limit_none_errors():
    circuit_breaker = CircuitBreakerHealth(
        enabled=True,
        consecutive_errors=None,
        max_consecutive_errors=5,
    )
    result = _circuit_near_limit(circuit_breaker)
    assert result is False


def test_circuit_near_limit_none_max():
    circuit_breaker = CircuitBreakerHealth(
        enabled=True,
        consecutive_errors=4,
        max_consecutive_errors=None,
    )
    result = _circuit_near_limit(circuit_breaker)
    assert result is False


def test_stuck_warnings_true():
    result = _stuck_warnings(True)
    assert result == ["stuck_detector_triggered"]


def test_stuck_warnings_false():
    result = _stuck_warnings(False)
    assert result == []


def test_agent_state_warnings_error():
    result = _agent_state_warnings(AgentState.ERROR.value)
    assert result == ["agent_state_error"]


def test_agent_state_warnings_other():
    result = _agent_state_warnings(AgentState.RUNNING.value)
    assert result == []


def test_controller_state_no_state():
    controller = SimpleNamespace()
    with pytest.raises(ValueError, match="Controller lacks state"):
        _controller_state(controller)


def test_extract_agent_state_enum():
    state = SimpleNamespace(agent_state=AgentState.RUNNING)
    result = _extract_agent_state(state)
    assert result == AgentState.RUNNING.value


def test_extract_agent_state_string():
    state = SimpleNamespace(agent_state="custom_state")
    result = _extract_agent_state(state)
    assert result == "custom_state"


def test_extract_agent_state_default():
    state = SimpleNamespace()
    result = _extract_agent_state(state)
    assert result == AgentState.LOADING.value


def test_collect_controller_health_no_state():
    controller = SimpleNamespace()
    with pytest.raises(ValueError, match="Controller lacks state"):
        collect_controller_health(controller)


def test_collect_controller_health_minimal():
    state = SimpleNamespace(agent_state=AgentState.RUNNING)
    controller = SimpleNamespace(
        id="test-123",
        state=state,
        _pending_action=None,
    )
    snapshot = collect_controller_health(controller)
    assert snapshot["controller_id"] == "test-123"
    assert snapshot["state"]["agent_state"] == AgentState.RUNNING.value
    assert snapshot["state"]["iteration"] is None
    assert snapshot["state"]["budget"] is None
    assert snapshot["services"]["retry"] is None
    assert snapshot["services"]["circuit_breaker"] is None


def test_collect_controller_health_with_pending_action():
    state = SimpleNamespace(agent_state=AgentState.RUNNING)
    controller = SimpleNamespace(
        id="test-123",
        state=state,
        _pending_action=Mock(),
    )
    snapshot = collect_controller_health(controller)
    assert snapshot["state"]["pending_action"] is True


def test_collect_controller_health_error_state():
    state = SimpleNamespace(agent_state=AgentState.ERROR, last_error="Test error")
    controller = SimpleNamespace(
        id="test-123",
        state=state,
        _pending_action=None,
    )
    snapshot = collect_controller_health(controller)
    assert snapshot["state"]["agent_state"] == AgentState.ERROR.value
    assert snapshot["state"]["last_error"] == "Test error"
    assert "agent_state_error" in snapshot["warnings"]

