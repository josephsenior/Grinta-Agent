"""Helper to emit operation-labeled metrics from tenacity retry hooks.

Provides a small factory to create a `before_sleep` callable suitable for
passing into tenacity.retry(..., before_sleep=...). The callable records an
`attempt` metric and, on final success/failure, emits `retry_success` or
`retry_failure` events via the MetaSOP metrics facade.
"""

from __future__ import annotations

import contextlib
from typing import Any, Callable

from openhands.utils.metrics_labels import sanitize_operation_label


def call_tenacity_hooks(
    before: Callable[[Any], None] | None,
    after: Callable[[Any], None] | None,
    retry_state: Any,
) -> None:
    """Safely call provided tenacity hook callables.

    This is useful for sites that programmatically invoke the generated
    hook functions (rather than passing them to tenacity). Keeps a single
    safe pattern so instrumentation cannot raise.
    """
    try:
        if before:
            with contextlib.suppress(Exception):
                before(retry_state)
        if after:
            with contextlib.suppress(Exception):
                after(retry_state)
    except Exception:
        pass


def _record_metrics_event_runtime(ev: dict) -> None:
    """Record a metrics event using the project's metrics facade.

    Imported at call time to avoid import-order/circular-imports causing the
    module-level binding to silently become a no-op during test/import time.
    """
    try:
        from openhands.metasop.metrics import record_event as _rec

        _rec(ev)
    except Exception:
        return


def tenacity_before_sleep_factory(operation: str) -> Callable[[Any, BaseException], None]:
    """Return a before_sleep(retry_state, exception) function for tenacity.

    Args:
        operation: stable operation name used as the `operation` label in metrics.

    Returns:
        Callable suitable for tenacity `before_sleep` hook.
    """

    def _before_sleep(retry_state: Any) -> None:
        with contextlib.suppress(Exception):
            _record_metrics_event_runtime(
                {
                    "status": "attempt",
                    "operation": sanitize_operation_label(operation),
                    "attempt_index": getattr(retry_state, "attempt_number", None),
                    "max_attempts": getattr(retry_state, "stop", None)
                    and getattr(retry_state.stop, "max_attempts", None),
                },
            )

    return _before_sleep


def tenacity_after_factory(operation: str) -> Callable[[Any, Any], None]:
    """Return an `after(retry_state)` hook for tenacity that records final.

    success or failure events when retries complete.

    The hook is safe to attach for all tenacity retries; it will record a
    `retry_success` when the retry outcome is successful and a `retry_failure`
    when retries are exhausted.
    """

    def _after(retry_state: Any) -> None:
        try:
            op = sanitize_operation_label(operation)
            outcome = getattr(retry_state, "outcome", None)
            try:
                if outcome is not None and hasattr(outcome, "successful") and outcome.successful():
                    _record_metrics_event_runtime({"status": "retry_success", "operation": op})
                    return
            except Exception:
                pass
            attempt_idx = getattr(retry_state, "attempt_number", None)
            max_attempts = getattr(retry_state, "stop", None) and getattr(
                retry_state.stop,
                "max_attempts",
                None,
            )
            if isinstance(attempt_idx, int) and isinstance(max_attempts, int) and (attempt_idx >= max_attempts):
                _record_metrics_event_runtime(
                    {
                        "status": "retry_failure",
                        "operation": op,
                        "attempt_index": attempt_idx,
                        "max_attempts": max_attempts,
                        "error": str(
                            getattr(retry_state, "outcome", None) or getattr(retry_state, "exception", None) or "",
                        ),
                    },
                )
        except Exception:
            pass

    return _after
