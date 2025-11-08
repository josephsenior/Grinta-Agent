"""Tests for `forge.llm.retry_mixin.RetryMixin`."""

from __future__ import annotations

import types

import pytest
from tenacity import RetryError

from forge.core.exceptions import LLMNoResponseError
from forge.llm.retry_mixin import RetryMixin


class DummyRetry(RetryMixin):
    def __init__(self) -> None:
        self.logged_attempts: list[int] = []

    def log_retry_attempt(self, retry_state):  # noqa: D401 - overriding mixin method
        super().log_retry_attempt(retry_state)
        self.logged_attempts.append(retry_state.attempt_number)


def test_retry_decorator_adjusts_temperature(monkeypatch) -> None:
    dummy = DummyRetry()
    attempts = []
    listener_calls = []

    def fake_before_sleep_factory(name):
        raise RuntimeError("metrics unavailable")

    monkeypatch.setattr("forge.llm.retry_mixin.tenacity_before_sleep_factory", fake_before_sleep_factory)
    monkeypatch.setattr("forge.llm.retry_mixin.tenacity_after_factory", lambda name: None)

    @dummy.retry_decorator(
        num_retries=2,
        retry_exceptions=(LLMNoResponseError,),
        retry_min_wait=0,
        retry_max_wait=0,
        retry_multiplier=0,
        retry_listener=lambda attempt, total: listener_calls.append((attempt, total)),
    )
    def flaky_call(**kwargs):
        attempts.append(kwargs.get("temperature"))
        raise LLMNoResponseError("fail")

    with pytest.raises(LLMNoResponseError):
        flaky_call(temperature=0)

    assert attempts == [0, 1.0]
    assert listener_calls == [(1, 2)]
    assert dummy.logged_attempts == [1]


def test_log_retry_attempt_sets_metadata() -> None:
    dummy = DummyRetry()
    exc = LLMNoResponseError("boom")
    retry_state = types.SimpleNamespace(
        outcome=types.SimpleNamespace(exception=lambda: exc),
        attempt_number=3,
        retry_object=types.SimpleNamespace(stop=types.SimpleNamespace(max_attempts=5)),
    )

    dummy.log_retry_attempt(retry_state)
    assert getattr(exc, "retry_attempt") == 3
    assert getattr(exc, "max_retries") == 5

