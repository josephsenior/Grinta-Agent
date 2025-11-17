from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import MagicMock

from forge.metasop.event_service import MetaSOPEVentService
from forge.metasop.models import StepResult


def _make_step(step_id: str = "s1", role: str = "builder") -> SimpleNamespace:
    return SimpleNamespace(id=step_id, role=role)


def test_set_event_emitter_registers_step_callback() -> None:
    runtime = MagicMock()
    service = MetaSOPEVentService(runtime)
    emitter = MagicMock()

    service.set_event_emitter(emitter)

    runtime.set_step_event_callback.assert_called_once()
    callback = runtime.set_step_event_callback.call_args[0][0]

    callback("s1", "builder", "running", 0)
    emitter.emit_step_start.assert_called_once_with("s1", "builder")


def test_emit_event_passes_through_to_runtime() -> None:
    runtime = MagicMock()
    service = MetaSOPEVentService(runtime)
    payload = {"type": "custom"}

    service.emit_event(payload)

    runtime.emit_event.assert_called_once_with(payload)


def test_emit_failure_serializes_result() -> None:
    runtime = MagicMock()
    service = MetaSOPEVentService(runtime)
    step = _make_step()
    result = StepResult(ok=False, error="boom")

    service.emit_failure(step, retries=2, result=result, error=ValueError("boom"))

    emitted = runtime.emit_event.call_args[0][0]
    assert emitted["type"] == "step_failure"
    assert emitted["error"] == "boom"
    assert emitted["result"]["ok"] is False

