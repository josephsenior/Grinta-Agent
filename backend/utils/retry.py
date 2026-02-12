"""Retry utilities with exponential backoff and jitter.

Provides robust retry logic for external service calls with:
- Exponential backoff, linear, fixed, and immediate strategies
- Jitter to prevent thundering herd
- Configurable retry strategies via RetryConfig
- Metrics recording and logging
- Support for both sync and async functions
"""

from __future__ import annotations

import asyncio
import contextlib
import random
import time
from typing import Any, Callable, Coroutine, Optional, TypeVar, Any

from backend.core.logger import forge_logger as logger
from backend.core.schemas import RetryConfig, RetryStrategy
from backend.utils.metrics_labels import sanitize_operation_label

T = TypeVar("T")


class RetryError(Exception):
    """Exception raised when all retry attempts have been exhausted."""

    pass


class RetryExhaustedError(RetryError):
    """Raised when all retry attempts are exhausted with specific attempt count."""

    def __init__(self, attempts: int, last_exception: Exception | None):
        self.attempts = attempts
        self.last_exception = last_exception
        super().__init__(
            f"Retry exhausted after {attempts} attempts. Last error: {last_exception}"
        )


def _noop_record_event(ev: dict[str, Any]) -> None:
    """No-op metrics recorder."""
    return


_record_metrics_event = _noop_record_event


def _record_attempt_metrics(op_name: str, attempt: int, max_attempts: int) -> None:
    """Record metrics for retry attempt."""
    with contextlib.suppress(Exception):
        _record_metrics_event(
            {
                "status": "attempt",
                "operation": op_name,
                "attempt_index": attempt,
                "max_attempts": max_attempts,
            },
        )


def _record_success_metrics(op_name: str, attempt: int, max_attempts: int) -> None:
    """Record metrics for successful retry."""
    with contextlib.suppress(Exception):
        _record_metrics_event(
            {
                "status": "retry_success",
                "operation": op_name,
                "attempts": attempt,
                "max_attempts": max_attempts,
            },
        )


def _record_error_metrics(
    op_name: str, attempt: int, max_attempts: int, error: Exception
) -> None:
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


def calculate_backoff(attempt: int, config: RetryConfig) -> float:
    """Calculate backoff delay for a retry attempt.

    Args:
        attempt: Current attempt number (0-indexed)
        config: Retry configuration

    Returns:
        Delay in seconds
    """
    if config.strategy == RetryStrategy.IMMEDIATE:
        return 0.0
    elif config.strategy == RetryStrategy.FIXED:
        delay = config.initial_delay
    elif config.strategy == RetryStrategy.LINEAR:
        delay = config.initial_delay * (attempt + 1)
    else:  # EXPONENTIAL
        delay = config.initial_delay * (config.exponential_base**attempt)

    # Apply max delay cap
    delay = min(delay, config.max_delay)

    # Apply jitter if enabled
    if config.jitter:
        jitter_min, jitter_max = config.jitter_range
        jitter = random.uniform(jitter_min, jitter_max)
        delay = delay * (1 + jitter)

    return delay


def retry(
    func: Callable[..., T] | None = None,
    *,
    config: Optional[RetryConfig] = None,
    # Legacy arguments for backward compatibility
    max_attempts: int = 3,
    base_delay: float = 1.0,
    max_delay: float = 10.0,
    jitter: float = 0.1,
    allowed_exceptions: tuple[type[Exception], ...] | None = None,
    operation_name: str | None = None,
) -> Any:
    """Retry a function with configurable backoff.

    Supports both sync and async functions, and can be used as a decorator or wrapper.

    Args:
        func: Function to retry (None if used as decorator)
        config: Retry configuration (overrides legacy arguments if provided)
        max_attempts: Maximum number of attempts (legacy)
        base_delay: Initial delay between retries (legacy)
        max_delay: Maximum delay between retries (legacy)
        jitter: Random jitter factor (legacy)
        allowed_exceptions: Tuple of exceptions to retry on (legacy)
        operation_name: Optional name for metrics/logging

    Returns:
        The result of the function call, or a decorator if func is None.
    """
    if config is None:
        config = RetryConfig(
            max_attempts=max_attempts,
            initial_delay=base_delay,
            max_delay=max_delay,
            jitter=True,
            jitter_range=(0.0, jitter),
            retryable_exceptions=allowed_exceptions or (Exception,),
        )

    def decorator(f: Callable[..., Any]) -> Callable[..., Any]:
        op_name = operation_name or sanitize_operation_label(f.__name__)

        if asyncio.iscoroutinefunction(f):

            async def async_wrapper(*args: Any, **kwargs: Any) -> Any:
                last_error: Exception | None = None
                for attempt in range(config.max_attempts):
                    _record_attempt_metrics(op_name, attempt + 1, config.max_attempts)
                    try:
                        result = await f(*args, **kwargs)
                        if attempt > 0:
                            logger.info(f"Retry succeeded on attempt {attempt + 1}")
                        _record_success_metrics(
                            op_name, attempt + 1, config.max_attempts
                        )
                        return result
                    except config.retryable_exceptions as e:
                        last_error = e
                        _record_error_metrics(op_name, attempt + 1, config.max_attempts, e)
                        
                        if attempt == config.max_attempts - 1:
                            break
                        
                        delay = calculate_backoff(attempt, config)
                        if config.on_retry:
                            with contextlib.suppress(Exception):
                                config.on_retry(attempt + 1, e)
                        
                        logger.warning(
                            f"Retry attempt {attempt + 1}/{config.max_attempts} after {delay:.2f}s. Error: {e}"
                        )
                        await asyncio.sleep(delay)
                    except Exception as e:
                        logger.error(f"Non-retryable exception in {op_name}: {e}")
                        raise

                raise RetryExhaustedError(config.max_attempts, last_error)

            return async_wrapper
        else:

            def sync_wrapper(*args: Any, **kwargs: Any) -> Any:
                last_error: Exception | None = None
                for attempt in range(config.max_attempts):
                    _record_attempt_metrics(op_name, attempt + 1, config.max_attempts)
                    try:
                        result = f(*args, **kwargs)
                        if attempt > 0:
                            logger.info(f"Retry succeeded on attempt {attempt + 1}")
                        _record_success_metrics(
                            op_name, attempt + 1, config.max_attempts
                        )
                        return result
                    except config.retryable_exceptions as e:
                        last_error = e
                        _record_error_metrics(op_name, attempt + 1, config.max_attempts, e)
                        
                        if attempt == config.max_attempts - 1:
                            break
                        
                        delay = calculate_backoff(attempt, config)
                        if config.on_retry:
                            with contextlib.suppress(Exception):
                                config.on_retry(attempt + 1, e)
                        
                        logger.warning(
                            f"Retry attempt {attempt + 1}/{config.max_attempts} after {delay:.2f}s. Error: {e}"
                        )
                        time.sleep(delay)
                    except Exception as e:
                        logger.error(f"Non-retryable exception in {op_name}: {e}")
                        raise

                raise RetryExhaustedError(config.max_attempts, last_error)

            return sync_wrapper

    if func is None:
        return decorator
    return decorator(func)
