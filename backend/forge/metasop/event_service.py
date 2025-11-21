"""Event emission utilities for MetaSOP."""

from __future__ import annotations

import logging
from typing import Any, Callable, Optional

from .event_emitter import MetaSOPEventEmitter
from .models import Artifact, SopStep, StepResult


class MetaSOPEVentService:
    """Centralizes MetaSOP event / telemetry emission."""

    def __init__(self, runtime_adapter) -> None:
        self._runtime_adapter = runtime_adapter
        self._event_emitter: Optional[MetaSOPEventEmitter] = None

    # ------------------------------------------------------------------ #
    # Socket event wiring
    # ------------------------------------------------------------------ #
    def set_event_emitter(self, emitter: MetaSOPEventEmitter | None) -> None:
        self._event_emitter = emitter
        if emitter:
            self._runtime_adapter.set_step_event_callback(self._emit_step_event)
        else:
            self._runtime_adapter.set_step_event_callback(None)

    def _emit_step_event(
        self, step_id: str, role: str, status: str, retries: int
    ) -> None:
        if not self._event_emitter:
            return
        try:
            if status == "running":
                self._event_emitter.emit_step_start(step_id, role)
            elif status == "executed":
                self._event_emitter.emit_step_complete(step_id, role, retries=retries)
            elif status == "failed":
                self._event_emitter.emit_step_failed(
                    step_id, role, error="step failed", retries=retries
                )
        except Exception as exc:  # pragma: no cover - defensive debug log
            logging.debug(
                "MetaSOP event emission failed for step %s: %s", step_id, exc
            )

    # ------------------------------------------------------------------ #
    # Runtime adapter passthroughs
    # ------------------------------------------------------------------ #
    def emit_event(self, event: dict[str, Any]) -> None:
        self._runtime_adapter.emit_event(event)

    def emit_stuck_thread_event(
        self,
        step: SopStep,
        timeout_seconds: float,
        worker,
        stacks: dict,
    ) -> None:
        self._runtime_adapter.emit_stuck_thread_event(
            step, timeout_seconds, worker, stacks
        )

    def handle_stuck_thread_error(self, error: Exception) -> None:
        self._runtime_adapter.handle_stuck_thread_error(error)

    # ------------------------------------------------------------------ #
    # Helper wrappers around runtime_adapter.emit_event for common shapes
    # ------------------------------------------------------------------ #
    def emit_qa_timeout(self, step: SopStep) -> None:
        self.emit_event(
            {
                "type": "qa_timeout",
                "step_id": step.id,
                "role": step.role,
            }
        )

    def emit_qa_success(self, step: SopStep, qa_artifact: Artifact) -> None:
        self.emit_event(
            {
                "type": "qa_success",
                "step_id": step.id,
                "role": step.role,
                "artifact": qa_artifact.model_dump(mode="json"),
            }
        )

    def emit_success(
        self,
        step: SopStep,
        retries: int,
        verification: dict | None,
    ) -> None:
        self.emit_event(
            {
                "type": "step_success",
                "step_id": step.id,
                "role": step.role,
                "retries": retries,
                "verification": verification,
            }
        )

    def emit_failure(
        self,
        step: SopStep,
        retries: int,
        result: StepResult,
        error: Exception | None,
    ) -> None:
        self.emit_event(
            {
                "type": "step_failure",
                "step_id": step.id,
                "role": step.role,
                "retries": retries,
                "error": str(error) if error else None,
                "result": result.model_dump(mode="json"),
            }
        )





