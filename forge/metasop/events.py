"""Event schema and emission helpers for MetaSOP orchestration telemetry."""

from __future__ import annotations
import contextlib
import json
import logging
import time
from enum import Enum
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field, field_validator

from forge.core.pydantic_compat import get_model_field_names, model_to_dict

from .metrics import record_event as _record_metrics_event

EVENT_VERSION = 1


class EventSource(str, Enum):
    """Canonical emitter identity for StepEvents.

    Consumers should prefer events where `source == EventSource.orchestrator` as
    the canonical orchestration-level view. Agents and other components may
    emit lower-level logs with `source == EventSource.agent` or
    `source == EventSource.internal`.
    """

    orchestrator = "orchestrator"
    agent = "agent"
    internal = "internal"
    __test__ = False


class StepEventStatus(str, Enum):
    """Lifecycle statuses emitted for each orchestration step attempt."""
    skipped = "skipped"
    attempt = "attempt"
    executed = "executed"
    executed_shaped = "executed_shaped"
    advisory = "advisory"
    warning = "warning"
    failed = "failed"
    suppressed_error = "suppressed_error"
    timeout = "timeout"
    micro_iter = "micro_iter"
    micro_iter_summary = "micro_iter_summary"
    patch_candidate_score = "patch_candidate_score"
    patch_candidate_selected = "patch_candidate_selected"
    executed_cached = "executed_cached"
    cache_store = "cache_store"
    __test__ = False


class StepEvent(BaseModel):
    """Typed representation of a step-level event emitted during orchestration.

    Fields are intentionally permissive for optional metadata while ensuring
    core keys are validated. Additional keys can be added via the `extra_data` map.
    """

    event_version: int = Field(default=EVENT_VERSION, description="Schema version for consumers")
    step_id: str
    role: str
    status: StepEventStatus
    timestamp: float = Field(default_factory=lambda: time.time())
    duration_ms: int | None = None
    retries: int | None = None
    attempt_index: int | None = None
    reason: str | None = None
    severity: int | None = None
    artifact_hash: str | None = None
    step_hash: str | None = None
    failure_type: str | None = None
    remediation: Any | None = None
    verification_result: dict | None = None
    total_tokens: int | None = None
    model: str | None = None
    candidate_index: int | None = None
    composite: float | None = None
    warning: str | None = None
    consumed_tokens: int | None = None
    hard_budget: int | None = None
    soft_budget: int | None = None
    keywords: list[str] | None = None
    message: str | None = None
    meta: dict[str, Any] | None = None
    error: str | None = None
    extra_data: dict[str, Any] | None = Field(default=None, description="Arbitrary extension map")
    source: EventSource = Field(
        default=EventSource.orchestrator,
        description="Emitter/source of this event; consumers should treat 'orchestrator' as canonical",
    )
    context_hash: str | None = Field(
        default=None,
        description="Deterministic hash of the step attempt context (retrieval, prior artifacts, role capabilities, env signature)",
    )
    __test__ = False

    class Config:
        """Pydantic configuration enforcing validation while allowing extras."""
        validate_assignment = True
        extra = "allow"

    @field_validator("duration_ms")
    @classmethod
    def non_negative_duration(cls, v):
        """Ensure duration is non-negative when provided."""
        if v is not None and v < 0:
            msg = "duration_ms must be >= 0"
            raise ValueError(msg)
        return v

    def to_public_dict(self) -> dict[str, Any]:
        """Convert event to serializable dict with Enum values coerced to primitives."""
        data = model_to_dict(self)
        for k, v in list(data.items()):
            try:
                if isinstance(v, Enum):
                    data[k] = v.value
            except Exception:
                pass
        return {k: v for k, v in data.items() if v is not None}


class EventEmitter:
    """Collects, validates, and emits structured step events."""

    def __init__(self, config, sop_name: str) -> None:
        """Initialize the emitter with configuration-driven logging destinations."""
        self._logger = logging.getLogger("forge.metasop")
        self._events: list[StepEvent] = []
        self.invalid_events: list[dict] = []
        self._stream_path: Path | None = None
        try:
            metasop_cfg = getattr(getattr(config, "extended", None), "metasop", {}) if config else {}
            if isinstance(metasop_cfg, dict) and metasop_cfg.get("log_events_jsonl"):
                base_dir = Path.home() / ".Forge" / "runs"
                base_dir.mkdir(parents=True, exist_ok=True)
                self._stream_path = base_dir / f"metasop_events_{sop_name}_{int(time.time())}.jsonl"
        except Exception:
            pass

    @property
    def events(self) -> list[dict]:
        """Return previously emitted events as sanitized dictionaries."""
        return [e.to_public_dict() for e in self._events]

    def _prepare_dict_event(self, event: dict) -> StepEvent:
        """Prepare a dictionary event for conversion to StepEvent."""
        model_field_names = get_model_field_names(StepEvent)
        base_fields = {k: v for k, v in event.items() if k in model_field_names}

        # Handle extra fields
        if extras := {k: v for k, v in event.items() if k not in base_fields}:
            base_fields["extra_data"] = extras

        # Set default values
        base_fields.setdefault("step_id", event.get("step_id", "unknown"))
        base_fields.setdefault("role", event.get("role", "unknown"))

        # Handle status field
        raw_status = event.get("status") or base_fields.get("status")
        try:
            if raw_status is None:
                base_fields["status"] = StepEventStatus.warning
            else:
                base_fields["status"] = (
                    raw_status if isinstance(raw_status, StepEventStatus) else StepEventStatus(raw_status)
                )
        except Exception:
            base_fields["status"] = StepEventStatus.warning

        return self._create_step_event_from_fields(base_fields, event)

    def _create_step_event_from_fields(self, base_fields: dict, original_event: dict) -> StepEvent:
        """Create a StepEvent from base fields, handling validation errors."""
        try:
            return StepEvent(**base_fields)
        except Exception as e:
            return self._handle_event_validation_error(base_fields, original_event, e)

    def _handle_event_validation_error(self, base_fields: dict, original_event: dict, error: Exception) -> StepEvent:
        """Handle event validation errors by creating a fallback StepEvent."""
        # Try to create a readable event string for logging
        event_str = self._get_event_string_for_logging(original_event)

        # Log the error
        self._log_event_validation_error(event_str, error)

        # Add to invalid events
        self._add_to_invalid_events(original_event)

        # Create fallback StepEvent
        return StepEvent(
            step_id=str(base_fields.get("step_id", "unknown")),
            role=str(base_fields.get("role", "unknown")),
            status=StepEventStatus.warning,
            reason="event_validation_error",
            extra_data={"original_event": original_event},
        )

    def _get_event_string_for_logging(self, event: dict) -> str:
        """Get a string representation of the event for logging."""
        try:
            return json.dumps(event, default=str, ensure_ascii=False)
        except Exception:
            try:
                return repr(event)
            except Exception:
                return "<unserializable-event>"

    def _log_event_validation_error(self, event_str: str, error: Exception) -> None:
        """Log event validation error."""
        with contextlib.suppress(Exception):
            self._logger.exception("Event validation failed for event: %s -- error: %s", event_str, error)

    def _add_to_invalid_events(self, event: dict) -> None:
        """Add event to invalid events list."""
        try:
            self.invalid_events.append(event if isinstance(event, dict) else {"event_repr": repr(event)})
        except Exception:
            with contextlib.suppress(Exception):
                self.invalid_events.append({"event_repr": repr(event)})

    def _record_event_metrics(self, payload: dict) -> None:
        """Record event metrics."""
        with contextlib.suppress(Exception):
            _record_metrics_event(payload)

    def _log_event(self, payload: dict) -> None:
        """Log the event."""
        try:
            self._logger.info(json.dumps({"metasop_event": payload}, ensure_ascii=False, default=str))
        except Exception:
            with contextlib.suppress(Exception):
                self._logger.info(
                    "metasop_event emitted step_id=%s status=%s",
                    payload.get("step_id"),
                    payload.get("status"),
                )

    def _write_to_stream(self, payload: dict) -> None:
        """Write event to stream file."""
        if not self._stream_path:
            return

        try:
            with self._stream_path.open("a", encoding="utf-8") as f:
                f.write(json.dumps(payload, ensure_ascii=False, default=str) + "\n")
        except Exception:
            try:
                with self._stream_path.open("a", encoding="utf-8") as f:
                    f.write(repr(payload) + "\n")
            except Exception:
                pass

    def emit(self, event: dict | StepEvent) -> None:
        """Emit an event, converting it to StepEvent if necessary and recording it."""
        # Convert dict to StepEvent if needed
        if not isinstance(event, StepEvent):
            event_obj = self._prepare_dict_event(event)
        else:
            event_obj = event

        # Add to events list
        self._events.append(event_obj)

        # Get payload for external operations
        payload = event_obj.to_public_dict()

        # Record metrics, log, and write to stream
        self._record_event_metrics(payload)
        self._log_event(payload)
        self._write_to_stream(payload)

    __test__ = False
