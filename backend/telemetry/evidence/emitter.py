"""Fail-open bridge from runtime instrumentation to session.jsonl."""

from __future__ import annotations

from typing import Any

from backend.core.logging.logger import app_logger as logger

from .schema import Correlation, EvidenceKind, ExecutionEvidence


def emit_execution_evidence(
    kind: EvidenceKind | str,
    data: dict[str, Any],
    *,
    correlation: Correlation | None = None,
) -> None:
    """Emit one compact record. Instrumentation is strictly observational."""
    try:
        from backend.core.logging.session_event_logger import emit_session_event

        evidence = ExecutionEvidence(
            kind=kind, data=data, correlation=correlation or Correlation()
        )
        emit_session_event('EXECUTION_EVIDENCE', evidence.to_dict())
    except Exception:
        logger.debug('Execution evidence emission failed', exc_info=True)


def emit_control_intervention(
    intervention: str,
    *,
    exception: Exception | None = None,
    **data: Any,
) -> None:
    """Record an existing recovery decision without influencing it."""
    try:
        from .fingerprint import fingerprint_text

        payload = {'intervention': intervention, **data}
        if exception is not None:
            payload['exception_type'] = type(exception).__name__
            payload['failure_fingerprint'] = fingerprint_text(str(exception))
        emit_execution_evidence(EvidenceKind.CONTROL_INTERVENTION, payload)
    except Exception:
        logger.debug('Control-intervention evidence emission failed', exc_info=True)
