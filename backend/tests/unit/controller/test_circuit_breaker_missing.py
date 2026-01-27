"""Tests for missing coverage in circuit_breaker.py."""

from __future__ import annotations

from types import SimpleNamespace

from forge.controller.circuit_breaker import (
    CircuitBreaker,
    CircuitBreakerConfig,
)
from forge.events.action import ActionSecurityRisk


def make_state(history: list) -> SimpleNamespace:
    """Create a lightweight state with history for circuit breaker tests."""
    return SimpleNamespace(history=history)


def test_circuit_breaker_all_checks_passed():
    """Test circuit breaker returns 'All checks passed' when no conditions are met."""
    config = CircuitBreakerConfig(
        max_consecutive_errors=10,
        max_high_risk_actions=10,
        max_stuck_detections=10,
        max_error_rate=1.0,
    )
    breaker = CircuitBreaker(config)
    result = breaker.check(make_state(history=[]))
    assert result.tripped is False
    assert result.reason == "All checks passed"
    assert result.action == "continue"


def test_record_error_window_trimming():
    """Test record_error trims window when it exceeds limit."""
    config = CircuitBreakerConfig(error_rate_window=2)
    breaker = CircuitBreaker(config)
    # Fill beyond window * 2
    for i in range(10):
        breaker.record_error(Exception(f"error {i}"))
    # Should be trimmed to window * 2 = 4
    assert len(breaker.recent_actions_success) <= 4
    # recent_errors is a list that doesn't get trimmed, only recent_actions_success does
    assert len(breaker.recent_errors) == 10


def test_record_success_window_trimming():
    """Test record_success trims window when it exceeds limit."""
    config = CircuitBreakerConfig(error_rate_window=2)
    breaker = CircuitBreaker(config)
    # Fill beyond window * 2
    for i in range(10):
        breaker.record_success()
    # Should be trimmed to window * 2 = 4
    assert len(breaker.recent_actions_success) <= 4


def test_calculate_error_rate_empty_list():
    """Test _calculate_error_rate returns 0.0 when recent_actions_success is empty."""
    breaker = CircuitBreaker(CircuitBreakerConfig())
    breaker.recent_actions_success = []
    error_rate = breaker._calculate_error_rate()
    assert error_rate == 0.0

