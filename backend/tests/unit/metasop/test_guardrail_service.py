from __future__ import annotations

import types
from unittest.mock import MagicMock

from forge.metasop.guardrail_service import GuardrailService
from forge.metasop.metrics import get_metrics_registry


class DummyEventService:
    def __init__(self) -> None:
        self.events: list[dict] = []

    def emit_event(self, payload: dict) -> None:
        self.events.append(payload)


class DummyContextManager:
    def __init__(self, orch) -> None:
        self._orch = orch

    def add_active_step(self, step):
        self._orch.active_steps[step.id] = step

    def remove_active_step(self, step_id: str):
        self._orch.active_steps.pop(step_id, None)


def make_orchestrator(
    *,
    parallel: bool = True,
    limit: int = 1,
) -> tuple[types.SimpleNamespace, DummyEventService]:
    active = {}
    event_service = DummyEventService()
    settings = types.SimpleNamespace(
        enable_async_execution=not parallel,
        enable_parallel_execution=parallel,
        max_parallel_workers=limit,
        async_max_concurrent_steps=limit,
    )
    orch = types.SimpleNamespace(
        settings=settings,
        event_service=event_service,
        context_manager=None,
        active_steps=active,
        _logger=MagicMock(),
    )
    orch.context_manager = DummyContextManager(orch)
    return orch, event_service


def test_guardrail_emits_concurrency_event_when_limit_exceeded():
    orch, events = make_orchestrator(parallel=True, limit=1)
    guardrails = GuardrailService(orch)

    step_one = types.SimpleNamespace(id="step-1", role="dev")
    guardrails.on_step_start(step_one)

    step_two = types.SimpleNamespace(id="step-2", role="qa")
    guardrails.on_step_start(step_two)

    concurrency_events = [
        evt for evt in events.events if evt.get("type") == "guardrail_concurrency"
    ]
    assert concurrency_events
    assert concurrency_events[-1]["active_steps"] == 2
    assert concurrency_events[-1]["limit"] == 1


def test_guardrail_emits_runtime_metrics_on_completion():
    orch, events = make_orchestrator(parallel=True, limit=2)
    guardrails = GuardrailService(orch)

    step = types.SimpleNamespace(id="step-xyz", role="planner")
    guardrails.on_step_start(step)
    guardrails.on_step_complete(step.id, success=True)

    runtime_events = [
        evt for evt in events.events if evt.get("type") == "step_runtime_metrics"
    ]
    assert runtime_events
    event = runtime_events[-1]
    assert event["step_id"] == "step-xyz"
    assert event["success"] is True
    assert event["active_steps_remaining"] == 0


def test_metrics_registry_tracks_guardrail_events(monkeypatch):
    reg = get_metrics_registry()
    # reset internal state
    reg._state = type(reg._state)()  # type: ignore[attr-defined]

    reg.record_event(
        {
            "type": "guardrail_concurrency",
            "active_steps": 5,
            "limit": 3,
        }
    )
    reg.record_event(
        {
            "type": "step_runtime_metrics",
            "duration_ms": 1200,
            "success": False,
        }
    )
    snap = reg.snapshot()
    assert snap["guardrail_concurrency_events"] == 1
    assert snap["guardrail_concurrency_peak_active"] == 5
    assert snap["guardrail_runtime_events"] == 1
    assert snap["guardrail_runtime_failures"] == 1
    assert snap["guardrail_runtime_max_ms"] == 1200

