"""Retry utilities with exponential backoff and jitter.

Provides robust retry logic for external service calls with:
- Exponential backoff
- Jitter to prevent thundering herd
- Configurable retry strategies
- Circuit breaker integration
"""

from __future__ import annotations

import asyncio
import random
import time
from dataclasses import dataclass
from enum import Enum
from typing import TYPE_CHECKING, Callable, Optional, TypeVar, Any

from forge.core.logger import forge_logger as logger

if TYPE_CHECKING:
    pass

T = TypeVar("T")


class RetryStrategy(str, Enum):
    """Retry strategies for different failure scenarios."""

    EXPONENTIAL = "exponential"  # Exponential backoff with jitter
    LINEAR = "linear"  # Linear backoff
    FIXED = "fixed"  # Fixed delay
    IMMEDIATE = "immediate"  # No delay between retries


@dataclass
class RetryConfig:
    """Configuration for retry behavior."""

    max_attempts: int = 3
    initial_delay: float = 1.0  # seconds
    max_delay: float = 60.0  # seconds
    exponential_base: float = 2.0
    jitter: bool = True
    jitter_range: tuple[float, float] = (0.0, 0.3)  # 0-30% jitter
    strategy: RetryStrategy = RetryStrategy.EXPONENTIAL
    retryable_exceptions: tuple[type[Exception], ...] = (Exception,)
    on_retry: Optional[Callable[[int, Exception], None]] = None


class RetryExhaustedError(Exception):
    """Raised when all retry attempts are exhausted."""

    def __init__(self, attempts: int, last_exception: Exception):
        self.attempts = attempts
        self.last_exception = last_exception
        super().__init__(
            f"Retry exhausted after {attempts} attempts. Last error: {last_exception}"
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
        delay = config.initial_delay * (config.exponential_base ** attempt)

    # Apply max delay cap
    delay = min(delay, config.max_delay)

    # Apply jitter if enabled
    if config.jitter:
        jitter_min, jitter_max = config.jitter_range
        jitter = random.uniform(jitter_min, jitter_max)
        delay = delay * (1 + jitter)

    return delay


async def retry_async(
    func: Callable[..., Any],
    *args,
    config: Optional[RetryConfig] = None,
    **kwargs,
) -> Any:
    """Retry an async function with exponential backoff.

    Args:
        func: Async function to retry
        *args: Function arguments
        config: Retry configuration (uses default if None)
        **kwargs: Function keyword arguments

    Returns:
        Function result

    Raises:
        RetryExhaustedError: If all retry attempts fail
        Exception: Last exception if retries exhausted
    """
    if config is None:
        config = RetryConfig()

    last_exception: Optional[Exception] = None

    for attempt in range(config.max_attempts):
        try:
            result = await func(*args, **kwargs)
            if attempt > 0:
                logger.info(f"Retry succeeded on attempt {attempt + 1}")
            return result
        except config.retryable_exceptions as e:
            last_exception = e

            # Don't retry on last attempt
            if attempt == config.max_attempts - 1:
                break

            # Calculate backoff delay
            delay = calculate_backoff(attempt, config)

            # Call retry callback if provided
            if config.on_retry:
                try:
                    config.on_retry(attempt + 1, e)
                except Exception:
                    pass  # Don't fail on callback error

            logger.warning(
                f"Retry attempt {attempt + 1}/{config.max_attempts} after {delay:.2f}s. Error: {e}"
            )

            # Wait before retry
            if delay > 0:
                await asyncio.sleep(delay)
        except Exception as e:
            # Non-retryable exception, re-raise immediately
            logger.error(f"Non-retryable exception: {e}")
            raise

    # All retries exhausted
    if last_exception:
        raise RetryExhaustedError(config.max_attempts, last_exception) from last_exception
    raise RetryExhaustedError(config.max_attempts, Exception("Unknown error"))


def retry_sync(
    func: Callable[..., Any],
    *args,
    config: Optional[RetryConfig] = None,
    **kwargs,
) -> Any:
    """Retry a sync function with exponential backoff.

    Args:
        func: Sync function to retry
        *args: Function arguments
        config: Retry configuration (uses default if None)
        **kwargs: Function keyword arguments

    Returns:
        Function result

    Raises:
        RetryExhaustedError: If all retry attempts fail
        Exception: Last exception if retries exhausted
    """
    if config is None:
        config = RetryConfig()

    last_exception: Optional[Exception] = None

    for attempt in range(config.max_attempts):
        try:
            result = func(*args, **kwargs)
            if attempt > 0:
                logger.info(f"Retry succeeded on attempt {attempt + 1}")
            return result
        except config.retryable_exceptions as e:
            last_exception = e

            # Don't retry on last attempt
            if attempt == config.max_attempts - 1:
                break

            # Calculate backoff delay
            delay = calculate_backoff(attempt, config)

            # Call retry callback if provided
            if config.on_retry:
                try:
                    config.on_retry(attempt + 1, e)
                except Exception:
                    pass  # Don't fail on callback error

            logger.warning(
                f"Retry attempt {attempt + 1}/{config.max_attempts} after {delay:.2f}s. Error: {e}"
            )

            # Wait before retry
            if delay > 0:
                time.sleep(delay)
        except Exception as e:
            # Non-retryable exception, re-raise immediately
            logger.error(f"Non-retryable exception: {e}")
            raise

    # All retries exhausted
    if last_exception:
        raise RetryExhaustedError(config.max_attempts, last_exception) from last_exception
    raise RetryExhaustedError(config.max_attempts, Exception("Unknown error"))


def retry_decorator(config: Optional[RetryConfig] = None):
    """Decorator to add retry logic to a function.

    Args:
        config: Retry configuration (uses default if None)

    Example:
        @retry_decorator(RetryConfig(max_attempts=5))
        async def my_function():
            ...
    """

    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        import asyncio

        if asyncio.iscoroutinefunction(func):

            async def async_wrapper(*args, **kwargs) -> T:
                return await retry_async(func, *args, config=config, **kwargs)

            return async_wrapper
        else:

            def sync_wrapper(*args, **kwargs) -> T:
                return retry_sync(func, *args, config=config, **kwargs)

            return sync_wrapper

    return decorator

