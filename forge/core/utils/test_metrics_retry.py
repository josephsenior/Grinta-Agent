"""Unit tests covering retry metrics integration utilities."""

from __future__ import annotations

import contextlib
from typing import NoReturn

from forge.core.utils.retry import RetryError, retry
from forge.metasop.metrics import get_metrics_registry


def test_retry_success_increments_metrics() -> None:
    """Test that successful retries increment metrics correctly.
    
    Verifies that retry_attempts and retry_successes counters are incremented
    when a flaky function eventually succeeds after retry.
    """
    reg = get_metrics_registry()
    snap_before = reg.snapshot()
    before_attempts = snap_before.get("retry_attempts", 0)
    before_successes = snap_before.get("retry_successes", 0)
    state = {"calls": 0}

    def flaky() -> NoReturn:
        """Fail once to simulate recovery and trigger success metrics."""
        state["calls"] += 1
        # Simulate flaky behavior: fail on first call, succeed on retry
        raise ValueError("temporary") if state["calls"] == 1 else None

    res = retry(flaky, max_attempts=3, base_delay=0.01, max_delay=0.02)
    assert res == "ok"
    snap_after = reg.snapshot()
    assert snap_after.get("retry_attempts", 0) >= before_attempts + 1
    assert snap_after.get("retry_successes", 0) >= before_successes + 1


def test_retry_failure_increments_metrics() -> None:
    """Test that failed retries increment failure metrics correctly.
    
    Verifies that retry_attempts and retry_failures counters are incremented
    when a function fails all retry attempts.
    """
    reg = get_metrics_registry()
    snap_before = reg.snapshot()
    before_attempts = snap_before.get("retry_attempts", 0)
    before_failures = snap_before.get("retry_failures", 0)

    def always_fail() -> NoReturn:
        """Always raise to ensure retry failure metrics increment."""
        msg = "boom"
        raise RuntimeError(msg)

    with contextlib.suppress(RetryError):
        retry(always_fail, max_attempts=2, base_delay=0.01, max_delay=0.02)
    snap_after = reg.snapshot()
    assert snap_after.get("retry_attempts", 0) >= before_attempts + 2
    assert snap_after.get("retry_failures", 0) >= before_failures + 1
