from __future__ import annotations

from types import SimpleNamespace

from forge.metasop.budget_monitor_service import BudgetMonitorService, BudgetStatus
from forge.metasop.models import (
    StepResult,
    StepTrace,
    Artifact,
    SopStep,
    StepOutputSpec,
)


class DummyEventService:
    def __init__(self) -> None:
        self.events: list[dict] = []

    def emit_event(self, payload: dict) -> None:
        self.events.append(payload)


def make_step(step_id: str = "step-1") -> SopStep:
    return SopStep(
        id=step_id,
        role="engineer",
        task="implement feature",
        outputs=StepOutputSpec(schema="designer.schema.json"),
    )


def test_budget_monitor_emits_soft_limit_event():
    event_service = DummyEventService()
    monitor = BudgetMonitorService(event_service)
    monitor.configure_run(soft_limit=50, hard_limit=0)

    trace = StepTrace(step_id="step-1", role="engineer", total_tokens=60)
    result = StepResult(ok=True, artifact=Artifact(step_id="step-1", role="engineer", content={}), trace=trace)

    status = monitor.record_step_result(make_step(), result)

    assert status == BudgetStatus.SOFT_LIMIT
    assert monitor.consumed_tokens == 60
    assert any(evt["type"] == "budget_soft_limit_reached" for evt in event_service.events)


def test_budget_monitor_emits_hard_limit_event_once():
    event_service = DummyEventService()
    monitor = BudgetMonitorService(event_service)
    monitor.configure_run(soft_limit=0, hard_limit=100)

    def make_result(tokens: int) -> StepResult:
        trace = StepTrace(step_id="step-1", role="engineer", total_tokens=tokens)
        return StepResult(ok=True, artifact=Artifact(step_id="step-1", role="engineer", content={}), trace=trace)

    status = monitor.record_step_result(make_step(), make_result(80))
    assert status == BudgetStatus.OK

    status = monitor.record_step_result(make_step("step-2"), make_result(30))
    assert status == BudgetStatus.HARD_LIMIT
    assert monitor.hard_limit_reached is True
    hard_events = [evt for evt in event_service.events if evt["type"] == "budget_hard_limit_exceeded"]
    assert len(hard_events) == 1

