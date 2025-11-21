from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import MagicMock

from forge.metasop.retry_service import StepRetryService
from forge.metasop.models import Artifact, StepResult


def _step():
    return SimpleNamespace(id="s1", role="builder")


def test_handle_success_emits_events_and_returns_artifact():
    orch = MagicMock()
    service = StepRetryService(orch)
    artifact = Artifact(step_id="s1", role="builder", content={"foo": "bar"})
    result = StepResult(ok=True, artifact=artifact)

    success, artifacts = service.handle_success(_step(), result, {}, retries=0)

    assert success is True
    assert artifacts["s1"] is artifact
    orch.event_service.emit_success.assert_called_once()


def test_handle_failure_emits_retry_events():
    orch = MagicMock()
    service = StepRetryService(orch)
    result = StepResult(ok=False, error="boom")

    success, _ = service.handle_failure(_step(), result, retries=0, max_retries=1)

    assert success is False
    orch.event_service.emit_failure.assert_called_once()
    orch._get_failure_handler.return_value.emit_retry_event.assert_called_once()


def test_handle_exception_uses_retry_count():
    orch = MagicMock()
    service = StepRetryService(orch)

    success, _ = service.handle_exception(
        _step(), RuntimeError("boom"), retries=0, max_retries=1
    )

    assert success is False
    orch.event_service.emit_failure.assert_called_once()

