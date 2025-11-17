from __future__ import annotations

import time
from typing import TYPE_CHECKING, Dict, Tuple

from forge.core.logger import forge_logger as logger

if TYPE_CHECKING:  # pragma: no cover
    from forge.metasop.models import SopStep
    from forge.metasop.orchestrator import MetaSOPOrchestrator


class GuardrailService:
    """Centralizes MetaSOP guardrails (concurrency caps, step runtime telemetry)."""

    def __init__(self, orchestrator: "MetaSOPOrchestrator") -> None:
        self._orch = orchestrator
        self._active_start: Dict[str, Tuple[float, "SopStep"]] = {}

    # ------------------------------------------------------------------
    # Step lifecycle tracking
    # ------------------------------------------------------------------
    def on_step_start(self, step: "SopStep") -> None:
        """Register a step entering execution."""

        self._orch.context_manager.add_active_step(step)
        self._active_start[step.id] = (time.time(), step)
        self._maybe_emit_concurrency_event(step)

    def on_step_complete(
        self, step_id: str, *, success: bool | None = None
    ) -> None:
        """Register a step finishing execution."""

        start_info = self._active_start.pop(step_id, None)
        step_ref = start_info[1] if start_info else None
        duration_ms: int | None = None
        if start_info:
            started_at = start_info[0]
            duration_ms = int(max(0.0, (time.time() - started_at) * 1000))

        self._orch.context_manager.remove_active_step(step_id)
        if step_ref and duration_ms is not None:
            self._emit_runtime_metrics(step_ref, duration_ms, success)

    # ------------------------------------------------------------------
    # Concurrency + telemetry helpers
    # ------------------------------------------------------------------
    def _maybe_emit_concurrency_event(self, step: "SopStep") -> None:
        limit = self._current_concurrency_limit()
        if limit is None:
            return
        active = len(self._orch.active_steps)
        if active <= limit:
            return

        payload = {
            "type": "guardrail_concurrency",
            "status": "guardrail_concurrency",
            "step_id": getattr(step, "id", None),
            "role": getattr(step, "role", None),
            "active_steps": active,
            "limit": limit,
        }
        self._emit_event(payload)
        logger.warning(
            "MetaSOP concurrency guardrail tripped (active=%s limit=%s step=%s)",
            active,
            limit,
            getattr(step, "id", None),
        )

    def _emit_runtime_metrics(
        self, step: "SopStep", duration_ms: int, success: bool | None
    ) -> None:
        payload = {
            "type": "step_runtime_metrics",
            "status": "step_runtime_metrics",
            "step_id": getattr(step, "id", None),
            "role": getattr(step, "role", None),
            "duration_ms": duration_ms,
            "active_steps_remaining": len(self._orch.active_steps),
            "success": bool(success) if success is not None else None,
        }
        self._emit_event(payload)

    def _current_concurrency_limit(self) -> int | None:
        settings = getattr(self._orch, "settings", None)
        if not settings:
            return None
        if getattr(settings, "enable_async_execution", False):
            limit = getattr(settings, "async_max_concurrent_steps", None)
            return int(limit) if isinstance(limit, int) and limit > 0 else 1
        if getattr(settings, "enable_parallel_execution", False):
            limit = getattr(settings, "max_parallel_workers", None)
            return int(limit) if isinstance(limit, int) and limit > 0 else 1
        # Sequential mode – guardrail only fires if more than one step somehow runs.
        return 1

    def _emit_event(self, payload: dict) -> None:
        event_service = getattr(self._orch, "event_service", None)
        if event_service:
            try:
                event_service.emit_event(payload)
            except Exception:  # pragma: no cover - defensive
                logger.debug("Failed to emit guardrail event: %s", payload)


