import importlib
import sys
from types import ModuleType, SimpleNamespace

import pytest

from forge.core.utils import retry as retry_mod


@pytest.fixture(autouse=True)
def patch_sleep(monkeypatch):
    slept = []
    monkeypatch.setattr(
        retry_mod.time, "sleep", lambda duration: slept.append(duration)
    )
    return slept


def test_calculate_sleep_time(monkeypatch):
    monkeypatch.setattr(retry_mod.random, "random", lambda: 0.5)
    sleep = retry_mod._calculate_sleep_time(
        attempt=2, base_delay=1.0, max_delay=8.0, jitter=0.1
    )
    assert 1.0 <= sleep <= 8.0


def test_should_retry_exception():
    err = ValueError("fail")
    assert retry_mod._should_retry_exception(err, (ValueError,)) is True
    assert retry_mod._should_retry_exception(err, (KeyError,)) is False
    assert retry_mod._should_retry_exception(err, None) is True


def test_log_retry_attempt(monkeypatch):
    called: dict[str, list[tuple[str, tuple]]] = {}

    class Logger(SimpleNamespace):
        def debug(self, msg, *args):
            called.setdefault("messages", []).append((msg, args))

    retry_mod._log_retry_attempt(Logger(), 1, 3, RuntimeError("boom"))
    assert called["messages"]


def test_record_metrics_helpers_swallow_errors(monkeypatch):
    monkeypatch.setattr(
        retry_mod,
        "_record_metrics_event",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(RuntimeError("fail")),
    )
    # Ensure helper functions do not raise when underlying event recording fails
    retry_mod._record_attempt_metrics("op", 1, 3)
    retry_mod._record_success_metrics("op", 1, 3)
    retry_mod._record_error_metrics("op", 1, 3, RuntimeError("err"))


def test_retry_success(monkeypatch):
    calls = {"count": 0}
    monkeypatch.setattr(retry_mod, "sanitize_operation_label", lambda name: name)

    def flaky():
        calls["count"] += 1
        if calls["count"] < 2:
            raise RuntimeError("try again")
        return "ok"

    result = retry_mod.retry(
        flaky, max_attempts=3, base_delay=0.01, max_delay=0.02, jitter=0.0
    )
    assert result == "ok"
    assert calls["count"] == 2


def test_retry_respects_allowed_exceptions(monkeypatch):
    attempts = {"count": 0}

    def flaky():
        attempts["count"] += 1
        raise ValueError("bad")

    with pytest.raises(ValueError):
        retry_mod.retry(flaky, max_attempts=2, allowed_exceptions=(RuntimeError,))
    assert attempts["count"] == 1


def test_retry_raises_after_max_attempts(monkeypatch, patch_sleep):
    monkeypatch.setattr(retry_mod, "sanitize_operation_label", lambda name: name)

    def always_fail():
        raise RuntimeError("nope")

    with pytest.raises(retry_mod.RetryError):
        retry_mod.retry(
            always_fail, max_attempts=3, base_delay=0.01, max_delay=0.02, jitter=0.0
        )
    assert patch_sleep  # sleep called at least once


def test_retry_operation_name_uses_callable(monkeypatch):
    monkeypatch.setattr(
        retry_mod, "sanitize_operation_label", lambda name: f"sanitized:{name}"
    )

    def succeed():
        return "done"

    result = retry_mod.retry(succeed)
    assert result == "done"
