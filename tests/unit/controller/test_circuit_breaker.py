from __future__ import annotations

from types import SimpleNamespace

import pytest

from forge.controller.circuit_breaker import CircuitBreaker, CircuitBreakerConfig
from forge.events.action import ActionSecurityRisk
from forge.events.observation import ErrorObservation


def _state_with_history(events):
    return SimpleNamespace(history=events)


def test_circuit_breaker_disabled_returns_continue():
    cb = CircuitBreaker(CircuitBreakerConfig(enabled=False))
    result = cb.check(_state_with_history([]))
    assert not result.tripped
    assert result.action == "continue"


def test_circuit_breaker_trips_on_consecutive_errors():
    cb = CircuitBreaker(CircuitBreakerConfig(max_consecutive_errors=2))
    cb.record_error(RuntimeError("boom"))
    cb.record_error(RuntimeError("boom"))
    result = cb.check(_state_with_history([]))
    assert result.tripped
    assert "consecutive errors" in result.reason


def test_circuit_breaker_trips_on_high_risk_actions():
    cb = CircuitBreaker(CircuitBreakerConfig(max_high_risk_actions=1))
    cb.record_high_risk_action(ActionSecurityRisk.HIGH)
    result = cb.check(_state_with_history([]))
    assert result.tripped
    assert "high-risk actions" in result.reason


def test_circuit_breaker_trips_on_stuck_detection():
    cb = CircuitBreaker(CircuitBreakerConfig(max_stuck_detections=1))
    cb.record_stuck_detection()
    result = cb.check(_state_with_history([]))
    assert result.tripped
    assert result.action == "stop"


def test_circuit_breaker_trips_on_error_rate():
    config = CircuitBreakerConfig(
        max_consecutive_errors=10,
        max_error_rate=0.5,
        error_rate_window=4,
    )
    cb = CircuitBreaker(config)
    errors = [ErrorObservation(content="err", error_id="E") for _ in range(4)]
    for _ in range(4):
        cb.record_error(RuntimeError("err"))
    result = cb.check(_state_with_history(errors))
    assert result.tripped
    assert "Error rate too high" in result.reason


def test_circuit_breaker_reset_and_success():
    cb = CircuitBreaker(CircuitBreakerConfig())
    cb.record_error(RuntimeError("err"))
    cb.record_success()
    assert cb.consecutive_errors == 0
    cb.record_high_risk_action(ActionSecurityRisk.LOW)
    assert cb.high_risk_action_count == 0
    cb.record_stuck_detection()
    cb.reset()
    assert cb.consecutive_errors == 0
    assert cb.high_risk_action_count == 0
    assert cb.stuck_detection_count == 0
