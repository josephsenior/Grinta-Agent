"""Additional tests for forge.controller.circuit_breaker."""

from __future__ import annotations

from types import SimpleNamespace

from forge.controller.circuit_breaker import (
    CircuitBreaker,
    CircuitBreakerConfig,
    CircuitBreakerResult,
)
from forge.events.action import ActionSecurityRisk
from forge.events.observation import ErrorObservation


def make_state(history: list) -> SimpleNamespace:
    """Create a lightweight state with history for circuit breaker tests."""
    return SimpleNamespace(history=history)


def test_circuit_breaker_disabled():
    """When disabled, circuit breaker should never trip."""
    breaker = CircuitBreaker(CircuitBreakerConfig(enabled=False))
    result = breaker.check(make_state(history=[]))
    assert isinstance(result, CircuitBreakerResult)
    assert result.tripped is False
    assert result.action == "continue"


def test_circuit_breaker_trips_on_consecutive_errors():
    """Consecutive errors beyond threshold should pause execution."""
    config = CircuitBreakerConfig(max_consecutive_errors=2)
    breaker = CircuitBreaker(config)

    breaker.record_error(Exception("failure 1"))
    breaker.record_error(Exception("failure 2"))
    result = breaker.check(make_state(history=[]))
    assert result.tripped is True
    assert "consecutive errors" in result.reason
    assert result.action == "pause"


def test_circuit_breaker_trips_on_high_risk_actions():
    """High-risk actions beyond threshold should pause execution."""
    config = CircuitBreakerConfig(max_high_risk_actions=1)
    breaker = CircuitBreaker(config)
    breaker.record_high_risk_action(ActionSecurityRisk.HIGH)
    result = breaker.check(make_state(history=[]))
    assert result.tripped is True
    assert "high-risk actions" in result.reason


def test_circuit_breaker_trips_on_stuck_detection():
    """Multiple stuck detections should stop the agent."""
    config = CircuitBreakerConfig(max_stuck_detections=1)
    breaker = CircuitBreaker(config)
    breaker.record_stuck_detection()
    result = breaker.check(make_state(history=[]))
    assert result.tripped is True
    assert result.action == "stop"


def test_circuit_breaker_error_rate_trigger():
    """High error rate in recent actions should pause execution."""
    config = CircuitBreakerConfig(max_error_rate=0.25, error_rate_window=4)
    breaker = CircuitBreaker(config)
    breaker.recent_actions_success = [False, False, True, False]
    result = breaker.check(make_state(history=[]))
    assert result.tripped is True
    assert "Error rate too high" in result.reason


def test_circuit_breaker_updates_from_state_history():
    """_update_metrics should count error observations from history."""
    breaker = CircuitBreaker(CircuitBreakerConfig(max_consecutive_errors=1))
    history = [ErrorObservation(content="fail"), ErrorObservation(content="fail2")]
    result = breaker.check(make_state(history=history))
    assert breaker.consecutive_errors >= 1
    assert isinstance(result, CircuitBreakerResult)
