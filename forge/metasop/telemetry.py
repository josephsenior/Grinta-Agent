from __future__ import annotations

import contextlib
import logging
import os
import uuid
from typing import TYPE_CHECKING, Any, Callable, Optional, Union

from forge.metasop.metrics import start_metrics_server

if TYPE_CHECKING:
    from forge.core.logger import ForgeLoggerAdapter


def initialize_metrics_server(settings: Any, running_under_pytest: Callable[[], bool]) -> None:
    """Start the Prometheus metrics server when configured."""
    try:
        port = getattr(settings, "metrics_prometheus_port", None)
        if port is not None and not running_under_pytest():
            start_metrics_server(port)
    except (OSError, RuntimeError, ImportError):
        pass


def setup_logging_and_tracing(ctx: Any) -> Union[logging.Logger, "ForgeLoggerAdapter"]:
    """Configure structured logging, trace context, and OpenTelemetry bridge."""
    try:
        trace_id = str(uuid.uuid4())
        _ensure_extra_dict(ctx)
        ctx.extra["trace_id"] = trace_id

        logger = _bind_logger(trace_id)
        _set_global_trace_context(trace_id)
        _maybe_create_root_span(ctx, trace_id)
        return logger
    except (AttributeError, RuntimeError):
        return logging.getLogger("forge")


def emit_event(
    emitter: Any,
    event: dict[str, Any],
    ctx: Any,
    step_events: list[dict[str, Any]],
    callback: Optional[Callable[[str, str, str, int], None]],
) -> None:
    """Emit orchestration event and update in-memory mirrors safely."""
    try:
        _prepare_event(event, ctx)
        emitter.emit(event)
        _update_step_events(emitter, step_events)
        _call_step_event_callback(callback, event)
    except (RuntimeError, ValueError, AttributeError):
        logging.exception("Failed to emit event")


def _ensure_extra_dict(ctx: Any) -> None:
    """Ensure ctx.extra exists as a mutable dict."""
    if not hasattr(ctx, "extra") or not isinstance(ctx.extra, dict):
        ctx.extra = {}


def _bind_logger(trace_id: str) -> Union[logging.Logger, "ForgeLoggerAdapter"]:
    """Bind the Forge logger with trace context if available."""
    try:
        from forge.core.logger import FORGE_logger, bind_context

        return bind_context(FORGE_logger, trace_id=trace_id)
    except (AttributeError, RuntimeError, ImportError):
        return logging.getLogger("forge")


def _set_global_trace_context(trace_id: str) -> None:
    """Update the global trace context for downstream log filters."""
    try:
        from forge.core.logger import get_trace_context, set_trace_context

        existing = get_trace_context()
        existing.update({"trace_id": trace_id})
        set_trace_context(existing)
    except (ImportError, AttributeError, RuntimeError):
        pass


def _maybe_create_root_span(ctx: Any, trace_id: str) -> None:
    """Optionally create an OpenTelemetry root span for the orchestration run."""
    if (
        os.getenv("OTEL_INSTRUMENT_ORCHESTRATION", os.getenv("OTEL_ENABLED", "false"))
        .lower()
        not in {"true", "1", "yes"}
    ):
        return

    try:
        from opentelemetry import trace as _otel_trace  # type: ignore
        from opentelemetry.trace import SpanKind as _SpanKind  # type: ignore

        tracer = _otel_trace.get_tracer("forge.orchestration")
        span = tracer.start_span(name="conversation.run", kind=_SpanKind.INTERNAL)
        span.set_attribute("forge.trace_id", trace_id)
        if hasattr(ctx, "run_id"):
            span.set_attribute("conversation.run_id", getattr(ctx, "run_id"))
        if hasattr(ctx, "conversation_id"):
            span.set_attribute("conversation.id", getattr(ctx, "conversation_id", ""))
        _ensure_extra_dict(ctx)
        ctx.extra["_otel_root_span"] = span
    except Exception:
        pass


def _prepare_event(event: dict[str, Any], ctx: Any) -> None:
    """Add source metadata and trace identifiers to the event payload."""
    event.setdefault("source", "orchestrator")
    try:
        if ctx and isinstance(getattr(ctx, "extra", None), dict):
            trace_id = ctx.extra.get("trace_id")
            if trace_id and "trace_id" not in event:
                event["trace_id"] = trace_id
    except (AttributeError, TypeError, ValueError):
        pass


def _update_step_events(emitter: Any, step_events: list[dict[str, Any]]) -> None:
    """Maintain the in-memory copy of emitted events."""
    try:
        last_event = _get_last_event(emitter)
        if last_event is not None:
            step_events.append(last_event)
        else:
            _refresh_step_events(emitter, step_events)
    except (AttributeError, TypeError, RuntimeError):
        pass


def _get_last_event(emitter: Any) -> Optional[dict[str, Any]]:
    """Return the latest emitted event in public dict form if available."""
    try:
        events = getattr(emitter, "_events", None)
        if events:
            return events[-1].to_public_dict()
    except (AttributeError, IndexError, TypeError):
        return None
    return None


def _refresh_step_events(emitter: Any, step_events: list[dict[str, Any]]) -> None:
    """Refresh step events list from emitter when last-event snapshot unavailable."""
    with contextlib.suppress(AttributeError, TypeError):
        step_events.clear()
        step_events.extend(list(emitter.events))


def _call_step_event_callback(
    callback: Optional[Callable[[str, str, str, int], None]], event: dict[str, Any]
) -> None:
    """Invoke step-event callback for non-bootstrap events."""
    if not callback:
        return

    try:
        step_id = event.get("step_id")
        role = event.get("role")
        status = event.get("status")
        if step_id and role and status and step_id != "__bootstrap__":
            iteration = event.get("iteration")
            if iteration is None:
                iteration = event.get("retries", 0)
            callback(step_id, role, status, int(iteration or 0))
    except Exception:
        logging.exception("Failed to invoke step_event_callback")

