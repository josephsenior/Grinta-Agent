"""Simple retry with exponential backoff utility.

Usage:
from forge.core.utils.retry import retry

@retry(max_attempts=3, base_delay=0.5, max_delay=5)
def flaky_call(...):
    ...

Or:
result = retry(lambda: some_call(), max_attempts=3)
"""

from __future__ import annotations

import random
import time
from typing import Callable, TypeVar

try:
    from forge.metasop.metrics import record_event as _record_metrics_event
except Exception:

    def _record_metrics_event(ev: dict) -> None:
        return


import contextlib

from forge.utils.metrics_labels import sanitize_operation_label

T = TypeVar("T")


class RetryError(Exception):
    """Exception raised when all retry attempts have been exhausted."""
    pass


def _record_attempt_metrics(op_name: str, attempt: int, max_attempts: int) -> None:
    """Record metrics for retry attempt."""
    with contextlib.suppress(Exception):
        _record_metrics_event(
            {"status": "attempt", "operation": op_name, "attempt_index": attempt, "max_attempts": max_attempts},
        )


def _record_success_metrics(op_name: str, attempt: int, max_attempts: int) -> None:
    """Record metrics for successful retry."""
    with contextlib.suppress(Exception):
        _record_metrics_event(
            {"status": "retry_success", "operation": op_name, "attempts": attempt, "max_attempts": max_attempts},
        )


def _record_error_metrics(op_name: str, attempt: int, max_attempts: int, error: Exception) -> None:
    """Record metrics for retry error."""
    with contextlib.suppress(Exception):
        _record_metrics_event(
            {
                "status": "attempt",
                "operation": op_name,
                "attempt_index": attempt,
                "max_attempts": max_attempts,
                "error": str(error)[:300],
            },
        )


def _log_retry_attempt(logger, attempt: int, max_attempts: int, error: Exception) -> None:
    """Log retry attempt if logger is provided."""
    if logger:
        with contextlib.suppress(Exception):
            logger.debug("Retry attempt %d/%d failed: %s", attempt, max_attempts, str(error))


def _should_retry_exception(error: Exception, allowed_exceptions: tuple[type, ...] | None) -> bool:
    """Check if exception should be retried."""
    if allowed_exceptions is None:
        return True
    return isinstance(error, allowed_exceptions)


def _calculate_sleep_time(attempt: int, base_delay: float, max_delay: float, jitter: float) -> float:
    """Calculate sleep time for retry with exponential backoff and jitter."""
    backoff = min(max_delay, base_delay * 2 ** (attempt - 1))
    jitter_amt = backoff * jitter * (random.random() * 2 - 1)
    return max(0.0, backoff + jitter_amt)


def retry(
    fn: Callable[[], T],
    max_attempts: int = 3,
    base_delay: float = 0.5,
    max_delay: float = 8.0,
    jitter: float = 0.1,
    allowed_exceptions: tuple[type, ...] | None = None,
    operation: str | None = None,
    logger=None,
) -> T:
    """Execute fn with retries and exponential backoff.

    Args:
        fn: zero-arg callable to execute.
        max_attempts: total attempts including the first.
        base_delay: initial backoff in seconds.
        max_delay: maximum backoff between retries.
        jitter: fraction of randomness to apply to backoff.
        allowed_exceptions: if provided, only these exceptions will be retried.
        operation: optional name for the operation being retried.
        logger: optional logger to emit retry events (should accept debug/info).

    Raises:
        RetryError if all attempts fail.

    """
    attempt = 1
    last_exc: Exception | None = None
    time.time()
    op_name = sanitize_operation_label(operation or getattr(fn, "__name__", "callable"))

    while attempt <= max_attempts:
        _record_attempt_metrics(op_name, attempt, max_attempts)

        try:
            res = fn()
            _record_success_metrics(op_name, attempt, max_attempts)
            return res
        except Exception as e:
            last_exc = e

            if not _should_retry_exception(e, allowed_exceptions):
                raise

            _log_retry_attempt(logger, attempt, max_attempts, e)
            _record_error_metrics(op_name, attempt, max_attempts, e)

            if attempt == max_attempts:
                break

            sleep_time = _calculate_sleep_time(attempt, base_delay, max_delay, jitter)
            time.sleep(sleep_time)
            attempt += 1
    msg = f"Operation failed after {max_attempts} attempts"
    raise RetryError(msg) from last_exc
