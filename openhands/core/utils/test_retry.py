from typing import NoReturn

from openhands.core.utils.retry import RetryError, retry


def test_retry_success_after_failure() -> None:
    """Test that retry succeeds after initial failure.
    
    Verifies that the retry mechanism correctly handles transient failures
    and returns success when the function eventually succeeds.
    """
    attempts = {"count": 0}

    def flaky() -> NoReturn:
        attempts["count"] += 1
        # Simulate flaky behavior: fail on first attempt, succeed on second
        raise ValueError("fail") if attempts["count"] < 2 else None

    result = retry(flaky, max_attempts=3, base_delay=0.01, max_delay=0.02)
    assert result == "ok"
    assert attempts["count"] == 2


def test_retry_gives_up() -> None:
    """Test that retry gives up after max attempts.
    
    Verifies that RetryError is raised when all retry attempts are exhausted.
    """

    def always_fail() -> NoReturn:
        msg = "nope"
        raise RuntimeError(msg)

    try:
        retry(always_fail, max_attempts=2, base_delay=0.01, max_delay=0.02)
        msg = "should have raised RetryError"
        raise AssertionError(msg)
    except RetryError:
        pass
