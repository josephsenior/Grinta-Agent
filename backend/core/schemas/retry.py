"""Retry-related schemas and enums."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Optional

from backend.core.schemas.enums import RetryStrategy


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
