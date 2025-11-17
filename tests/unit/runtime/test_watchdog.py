from __future__ import annotations

import time
from types import SimpleNamespace
from typing import Callable

import pytest

from forge.runtime.watchdog import runtime_watchdog


class DummyEventStream:
    def __init__(self, sid: str) -> None:
        self.sid = sid
        self.listeners: dict[str, Callable[[str], None]] = {}
        self.seq = 0

    def add_activity_listener(self, callback):
        handle = f"h{self.seq}"
        self.seq += 1
        self.listeners[handle] = callback
        return handle

    def remove_activity_listener(self, handle: str) -> None:
        self.listeners.pop(handle, None)

    def emit(self) -> None:
        for callback in list(self.listeners.values()):
            callback(self.sid)


class DummyRuntime:
    def __init__(self, sid: str = "runtime-sid") -> None:
        self.sid = sid
        self.config = SimpleNamespace(runtime="docker")
        self.event_stream = DummyEventStream(sid)
        self.closed = False

    def close(self) -> None:
        self.closed = True


@pytest.fixture(autouse=True)
def reset_watchdog():
    runtime_watchdog.reset_for_tests()
    runtime_watchdog.configure(max_active_seconds=3600.0, poll_interval=30.0)
    yield
    runtime_watchdog.reset_for_tests()
    runtime_watchdog.configure(max_active_seconds=3600.0, poll_interval=30.0)


def test_watchdog_disconnects_after_timeout():
    runtime_watchdog.configure(max_active_seconds=0.1, poll_interval=0.05)
    runtime = DummyRuntime()
    runtime_watchdog.watch_runtime(runtime, key="docker", session_id="sess")
    time.sleep(0.2)
    assert runtime.closed is True


def test_watchdog_heartbeat_prevents_disconnect():
    runtime_watchdog.configure(max_active_seconds=0.2, poll_interval=0.05)
    runtime = DummyRuntime()
    runtime_watchdog.watch_runtime(runtime, key="docker", session_id="sess")
    for _ in range(4):
        time.sleep(0.04)
        runtime.event_stream.emit()
    assert runtime.closed is False
    runtime_watchdog.unwatch_runtime(runtime)


def test_watchdog_stats_reports_watched_counts():
    runtime = DummyRuntime()
    runtime_watchdog.watch_runtime(runtime, key="docker", session_id="sess")
    stats = runtime_watchdog.stats()
    assert stats == {"docker": 1}
    runtime_watchdog.unwatch_runtime(runtime)

