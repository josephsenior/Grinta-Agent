from __future__ import annotations

import logging
import sys
import threading
import traceback
from typing import TYPE_CHECKING, Any, Callable

from forge.metasop.telemetry import emit_event
from forge.metasop.strategies import (
    BaseFailureClassifier,
    BaseQAExecutor,
    BaseStepExecutor,
    DefaultFailureClassifier,
    DefaultQAExecutor,
    DefaultStepExecutor,
    TimeoutQAExecutor,
    TimeoutStepExecutor,
)

from .failure_handling import FailureHandler

if TYPE_CHECKING:  # pragma: no cover
    from forge.metasop.models import OrchestrationContext, SopStep
    from forge.metasop.orchestrator import MetaSOPOrchestrator


class RuntimeAdapter:
    """Encapsulates runtime executor setup, event emission, and stuck-thread handling."""

    def __init__(self, orchestrator: "MetaSOPOrchestrator") -> None:
        self._orch = orchestrator
        self._event_sinks: list[Callable[[dict[str, Any]], None]] = []

    # ------------------------------------------------------------------
    # Executor / failure handler management
    # ------------------------------------------------------------------
    def initialize_execution_components(self) -> None:
        """Initialize step and QA executors with timeout wrappers when configured."""

        orch = self._orch

        # Step executor
        orch.step_executor = DefaultStepExecutor()
        if getattr(orch.settings, "step_timeout_seconds", None):
            orch.step_executor = TimeoutStepExecutor(
                orch.step_executor,
                orch.settings.step_timeout_seconds,
                stuck_callback=self.handle_stuck_thread,
                stuck_threshold=getattr(orch.settings, "stuck_threshold_seconds", None),
            )

        # QA executor
        orch.qa_executor = DefaultQAExecutor()
        if getattr(orch.settings, "qa_timeout_seconds", None):
            orch.qa_executor = TimeoutQAExecutor(
                orch.qa_executor,
                orch.settings.qa_timeout_seconds,
                stuck_callback=self.handle_stuck_thread,
                stuck_threshold=getattr(orch.settings, "stuck_threshold_seconds", None),
            )

        # Failure classifier
        orch.failure_classifier = DefaultFailureClassifier()

    def get_failure_handler(self) -> FailureHandler:
        """Return the FailureHandler, creating or updating it as needed."""

        orch = self._orch
        failure_handler = getattr(orch, "failure_handler", None)
        emit_callback = getattr(orch, "_emit_event", None)
        if not callable(emit_callback):
            event_service = getattr(orch, "event_service", None)
            if event_service is not None:
                emit_callback = event_service.emit_event
            else:
                emit_callback = lambda _: None

        if failure_handler is None:
            failure_handler = FailureHandler(
                orch.settings,
                orch.failure_classifier,
                emit_callback,
            )
            orch.failure_handler = failure_handler
        else:
            failure_handler.update_failure_classifier(orch.failure_classifier)
        return failure_handler

    # ------------------------------------------------------------------
    # Event / callback helpers
    # ------------------------------------------------------------------
    def set_step_event_callback(self, callback: Callable[[str, str, str, int], None]) -> None:
        """Register callback for real-time step events."""

        self._orch.step_event_callback = callback

    def emit_event(self, event: dict[str, Any]) -> None:
        """Emit orchestration event via telemetry helper."""

        emit_event(
            self._orch._emitter,
            event,
            getattr(self._orch, "_ctx", None),
            self._orch.step_events,
            self._orch.step_event_callback,
        )
        for sink in list(self._event_sinks):
            try:
                sink(dict(event))
            except Exception:
                logging.exception("Event sink failed")

    def register_event_sink(self, sink: Callable[[dict[str, Any]], None]) -> None:
        """Register a sink that receives emitted events."""

        self._event_sinks.append(sink)

    def clear_event_sinks(self) -> None:
        """Remove all registered event sinks."""

        self._event_sinks.clear()

    # ------------------------------------------------------------------
    # Stuck thread handling
    # ------------------------------------------------------------------
    def handle_stuck_thread(
        self,
        step: "SopStep",
        ctx: "OrchestrationContext",
        worker: threading.Thread,
        timeout_seconds: float,
    ) -> None:
        """Best-effort handling for worker threads that remain alive after a timeout."""

        try:
            stacks = self.capture_thread_stacks()
            stacks = self.truncate_stacks(stacks)
            self.emit_stuck_thread_event(step, timeout_seconds, worker, stacks)
        except (RuntimeError, AttributeError, TypeError) as exc:
            self.handle_stuck_thread_error(exc)

    def capture_thread_stacks(self) -> dict:
        """Capture thread stack frames for debugging."""

        try:
            return {
                str(tid): traceback.format_stack(frame)
                for tid, frame in sys._current_frames().items()
            }
        except (OSError, RuntimeError, AttributeError):
            return {"error": "failed_to_capture_frames"}

    def truncate_stacks(self, stacks: dict) -> dict:
        """Truncate large stack traces to the most recent frames."""

        try:
            for key, value in list(stacks.items()):
                if isinstance(value, list):
                    stacks[key] = value[-20:]
        except (TypeError, AttributeError):
            pass
        return stacks

    def emit_stuck_thread_event(
        self,
        step: "SopStep",
        timeout_seconds: float,
        worker: threading.Thread,
        stacks: dict,
    ) -> None:
        """Emit structured stuck-thread event."""

        self.emit_event(
            {
                "step_id": getattr(step, "id", None) or "__unknown__",
                "role": getattr(step, "role", None) or "__unknown__",
                "status": "stuck",
                "reason": "step_thread_stuck",
                "meta": {
                    "timeout_seconds": timeout_seconds,
                    "thread_alive": worker.is_alive(),
                    "stack_snapshot": stacks,
                },
            }
        )

    def handle_stuck_thread_error(self, error: Exception) -> None:
        """Log errors encountered during stuck-thread handling."""

        try:
            if getattr(self._orch, "_logger", None):
                try:
                    self._orch._logger.exception("Failed to handle stuck thread")
                except (AttributeError, RuntimeError):
                    logging.exception("Failed to handle stuck thread")
            else:
                logging.exception("Failed to handle stuck thread")
        except (AttributeError, RuntimeError):
            pass


__all__ = ["RuntimeAdapter"]
