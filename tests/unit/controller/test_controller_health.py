from __future__ import annotations

from types import SimpleNamespace

from forge.controller.health import collect_controller_health
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

