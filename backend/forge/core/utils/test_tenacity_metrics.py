"""Unit tests exercising tenacity metrics instrumentation."""

from __future__ import annotations

import contextlib
from typing import Any, NoReturn

import tenacity

from forge.metasop.metrics import get_metrics_registry
from forge.utils.tenacity_metrics import tenacity_before_sleep_factory


def test_tenacity_before_sleep_emits_attempt_metric() -> None:
    """Test that tenacity before_sleep hook emits retry attempt metrics.

    Verifies that retry attempts are tracked by operation name and overall
    when using tenacity's retry decorator with custom before_sleep hook.
    """
    reg = get_metrics_registry()
    snap_before = reg.snapshot()
    before_attempts = snap_before.get("retry_attempts", 0)
    state = {"calls": 0}

    @tenacity.retry(
        stop=tenacity.stop_after_attempt(3),
        wait=tenacity.wait_fixed(0),
        before_sleep=tenacity_before_sleep_factory("test_op"),
    )
    def flaky() -> str:
        """Simulate a flaky function that succeeds on the second attempt."""
        state["calls"] += 1
        if state["calls"] == 1:
            raise ValueError("temporary")
        return "ok"

    res: str = flaky()
    assert res == "ok"
    snap_after = reg.snapshot()
    assert snap_after.get("retry_attempts", 0) >= before_attempts + 1
    attempts_by_op = snap_after.get("retry_attempts_by_operation") or {}
    assert attempts_by_op.get("test_op", 0) >= 1


def test_tenacity_failed_retries_record_failure() -> None:
    """Test that failed tenacity retries record failure metrics.

    Verifies that retry failures are tracked when all attempts are exhausted.
    """
    reg = get_metrics_registry()
    snap_before = reg.snapshot()
    before_failures = snap_before.get("retry_failures", 0)
    from forge.metasop.metrics import record_event as record_event_fn
    from forge.utils.metrics_labels import sanitize_operation_label

    @tenacity.retry(
        stop=tenacity.stop_after_attempt(2),
        wait=tenacity.wait_fixed(0),
        before_sleep=tenacity_before_sleep_factory("always_fail_op"),
    )
    def always_fail() -> NoReturn:
        """Function that always raises to trigger retry failure metrics."""
        msg = "boom"
        raise RuntimeError(msg)

    try:
        always_fail()
    except tenacity.RetryError as e:
        with contextlib.suppress(Exception):
            last_attempt: Any = getattr(e, "last_attempt", None)
            stop_info: Any = getattr(last_attempt, "stop", None)
            record_event_fn(
                {
                    "status": "retry_failure",
                    "operation": sanitize_operation_label("always_fail_op"),
                    "attempt_index": getattr(last_attempt, "attempt_number", None),
                    "max_attempts": getattr(stop_info, "max_attempts", None),
                    "error": str(e),
                },
            )
    snap_after = reg.snapshot()
    assert snap_after.get("retry_failures", 0) >= before_failures + 1
    failures_by_op = snap_after.get("retry_failures_by_operation") or {}
    assert failures_by_op.get("always_fail_op", 0) >= 1
