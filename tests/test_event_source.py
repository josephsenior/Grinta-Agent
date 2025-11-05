import types
from openhands.metasop.events import EventEmitter, EventSource, StepEvent
from openhands.metasop.orchestrator import MetaSOPOrchestrator


def test_step_event_default_source():
    se = StepEvent(step_id="s1", role="engineer", status="attempt")
    assert se.source == EventSource.orchestrator


def test_event_emitter_preserves_explicit_source():
    emitter = EventEmitter(config=None, sop_name="test")
    evt = {"step_id": "s2", "role": "engineer", "status": "attempt", "source": EventSource.agent}
    emitter.emit(evt)
    evts = emitter.events
    assert len(evts) == 1
    assert evts[0]["source"] == EventSource.agent


def test_orchestrator_enforces_orchestrator_source():
    orch = MetaSOPOrchestrator(
        sop_name="feature_delivery",
        config=types.SimpleNamespace(extended=types.SimpleNamespace(metasop={}), runtime=types.SimpleNamespace()),
    )
    orch._emit_event({"step_id": "s3", "role": "engineer", "status": "attempt"})
    found = [e for e in orch.step_events if e.get("step_id") == "s3"]
    assert found, "Expected an event for step s3"
    assert found[0]["source"] == EventSource.orchestrator
    orch._emit_event({"step_id": "s4", "role": "engineer", "status": "attempt", "source": EventSource.agent})
    found2 = [e for e in orch.step_events if e.get("step_id") == "s4"]
    assert found2
    assert found2[0]["source"] == EventSource.agent
