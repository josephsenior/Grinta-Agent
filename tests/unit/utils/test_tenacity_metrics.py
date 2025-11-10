import sys
from types import ModuleType, SimpleNamespace
from unittest.mock import MagicMock

import pytest

from forge.utils import tenacity_metrics
from forge.utils.tenacity_metrics import (
    call_tenacity_hooks,
    tenacity_after_factory,
    tenacity_before_sleep_factory,
)


def test_call_tenacity_hooks_suppresses_exceptions():
    state = SimpleNamespace()
    before = MagicMock(side_effect=RuntimeError("boom"))
    after = MagicMock(side_effect=RuntimeError("boom"))
    call_tenacity_hooks(before, after, state)
    before.assert_called_once_with(state)
    after.assert_called_once_with(state)


def test_call_tenacity_hooks_handles_none():
    state = SimpleNamespace()
    call_tenacity_hooks(None, None, state)


def test_call_tenacity_hooks_captures_outer_errors():
    class Problematic:
        def __bool__(self):
            raise RuntimeError("bad")

        def __call__(self, *args, **kwargs):
            return None

    state = SimpleNamespace()
    call_tenacity_hooks(Problematic(), None, state)


def test_record_metrics_event_runtime(monkeypatch):
    recorded = []

    def fake_record(event):
        recorded.append(event)

    module = SimpleNamespace(record_event=fake_record)
    monkeypatch.setitem(sys.modules, "forge.metasop.metrics", module)
    tenacity_metrics._record_metrics_event_runtime({"status": "attempt"})
    assert recorded == [{"status": "attempt"}]
    bad_module = ModuleType("forge.metasop.metrics")
    monkeypatch.setitem(sys.modules, "forge.metasop.metrics", bad_module)
    tenacity_metrics._record_metrics_event_runtime({"status": "ignored"})
    monkeypatch.setitem(sys.modules, "forge.metasop.metrics", module)


def test_tenacity_before_sleep_factory(monkeypatch):
    events = []
    monkeypatch.setattr(tenacity_metrics, "_record_metrics_event_runtime", lambda event: events.append(event))
    state = SimpleNamespace(attempt_number=2, stop=SimpleNamespace(max_attempts=5))
    before = tenacity_before_sleep_factory("operation name")
    before(state)
    assert events == [
        {"status": "attempt", "operation": "operation_name", "attempt_index": 2, "max_attempts": 5},
    ]


def test_tenacity_after_factory_success(monkeypatch):
    events = []
    monkeypatch.setattr(tenacity_metrics, "_record_metrics_event_runtime", lambda event: events.append(event))

    class SuccessOutcome:
        def successful(self):
            return True

    state = SimpleNamespace(outcome=SuccessOutcome(), attempt_number=1, stop=SimpleNamespace(max_attempts=3))
    after = tenacity_after_factory("op")
    after(state)
    assert events == [{"status": "retry_success", "operation": "op"}]


def test_tenacity_after_factory_failure(monkeypatch):
    events = []
    monkeypatch.setattr(tenacity_metrics, "_record_metrics_event_runtime", lambda event: events.append(event))
    state = SimpleNamespace(
        outcome=None,
        exception=RuntimeError("boom"),
        attempt_number=3,
        stop=SimpleNamespace(max_attempts=3),
    )
    after = tenacity_after_factory("op spaced")
    after(state)
    assert events == [
        {
            "status": "retry_failure",
            "operation": "op_spaced",
            "attempt_index": 3,
            "max_attempts": 3,
            "error": "boom",
        },
    ]


def test_tenacity_after_factory_success_error(monkeypatch):
    events = []
    monkeypatch.setattr(tenacity_metrics, "_record_metrics_event_runtime", lambda event: events.append(event))

    class BadOutcome:
        def successful(self):
            raise RuntimeError("nope")

        def __str__(self):
            return "bad-outcome"

    state = SimpleNamespace(
        outcome=BadOutcome(),
        exception=None,
        attempt_number=2,
        stop=SimpleNamespace(max_attempts=2),
    )
    after = tenacity_after_factory("op")
    after(state)
    assert events == [
        {
            "status": "retry_failure",
            "operation": "op",
            "attempt_index": 2,
            "max_attempts": 2,
            "error": "bad-outcome",
        },
    ]


def test_tenacity_after_factory_outer_exception(monkeypatch):
    events = []
    monkeypatch.setattr(tenacity_metrics, "_record_metrics_event_runtime", lambda event: events.append(event))

    def raising(_operation: str):
        raise ValueError("boom")

    monkeypatch.setattr(tenacity_metrics, "sanitize_operation_label", raising)
    state = SimpleNamespace(attempt_number=1, stop=SimpleNamespace(max_attempts=1), outcome=None, exception=None)
    after = tenacity_after_factory("op")
    after(state)
    assert events == []