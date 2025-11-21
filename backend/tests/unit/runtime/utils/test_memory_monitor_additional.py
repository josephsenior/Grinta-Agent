from __future__ import annotations

import importlib.util
import sys
import types
from pathlib import Path
from typing import Any

import pytest


ROOT = Path(__file__).resolve().parents[4]

if "forge.runtime.utils" not in sys.modules:
    sys.modules["forge.runtime.utils"] = types.ModuleType("forge.runtime.utils")

# Stub forge.core.logger to avoid heavy dependencies
logger_mod = sys.modules.setdefault(
    "forge.core.logger", types.ModuleType("forge.core.logger")
)
if not hasattr(logger_mod, "forge_logger"):

    class StubLogger:
        def __init__(self):
            self.info_calls: list[Any] = []
            self.error_calls: list[Any] = []

        def info(self, msg, *args, **kwargs):
            self.info_calls.append((msg, args, kwargs))

        def error(self, msg, *args, **kwargs):
            self.error_calls.append((msg, args, kwargs))

    setattr(logger_mod, "forge_logger", StubLogger())

# Stub memory_profiler
memory_profiler_mod = sys.modules.setdefault(
    "memory_profiler", types.ModuleType("memory_profiler")
)
if not hasattr(memory_profiler_mod, "memory_usage"):

    def _default_memory_usage(*args, **kwargs):
        return []

    setattr(memory_profiler_mod, "memory_usage", _default_memory_usage)


spec = importlib.util.spec_from_file_location(
    "forge.runtime.utils.memory_monitor",
    ROOT / "forge" / "runtime" / "utils" / "memory_monitor.py",
)
assert spec and spec.loader
memory_monitor_mod = importlib.util.module_from_spec(spec)
sys.modules["forge.runtime.utils.memory_monitor"] = memory_monitor_mod
spec.loader.exec_module(memory_monitor_mod)

LogStream = memory_monitor_mod.LogStream
MemoryMonitor = memory_monitor_mod.MemoryMonitor


class DummyThread:
    def __init__(self, target=None, daemon=False):
        self.target = target
        self.daemon = daemon
        self.started = False

    def start(self):
        self.started = True
        if self.target:
            self.target()

    def is_alive(self):
        return False


@pytest.fixture(autouse=True)
def reset_logger():
    logger_stub = sys.modules["forge.core.logger"].forge_logger  # type: ignore[attr-defined]
    logger_stub.info_calls.clear()
    logger_stub.error_calls.clear()
    yield


@pytest.fixture
def patch_thread(monkeypatch):
    import threading

    monkeypatch.setattr(
        memory_monitor_mod,
        "threading",
        types.SimpleNamespace(Thread=DummyThread, Event=threading.Event),
    )
    yield


@pytest.fixture
def memory_usage_stub(monkeypatch):
    calls: dict[str, Any] = {
        "args": [],
        "kwargs": [],
        "side_effect": None,
        "return": [10, 12],
    }

    def fake_memory_usage(*args, **kwargs):
        calls["args"].append(args)
        calls["kwargs"].append(kwargs)
        if calls["side_effect"]:
            raise calls["side_effect"]
        return calls["return"]

    monkeypatch.setattr(memory_monitor_mod, "memory_usage", fake_memory_usage)
    return calls


def test_log_stream_write_filters_empty():
    logger = sys.modules["forge.core.logger"].forge_logger  # type: ignore[attr-defined]
    stream = LogStream()
    stream.write("  ")
    stream.write("line\n")
    assert logger.info_calls == [("[Memory usage] %s", ("line",), {})]


def test_log_stream_flush_noop():
    stream = LogStream()
    stream.flush()  # Should not raise


def test_start_monitoring_no_enable(patch_thread, memory_usage_stub):
    monitor = MemoryMonitor(enable=False)
    monitor.start_monitoring()
    assert memory_usage_stub["args"] == []


def test_start_monitoring_already_running(patch_thread, memory_usage_stub):
    monitor = MemoryMonitor(enable=True)
    monitor.start_monitoring()
    first_calls = list(memory_usage_stub["args"])
    monitor.start_monitoring()
    assert memory_usage_stub["args"] == first_calls


def test_start_monitoring_records_usage(patch_thread, memory_usage_stub):
    monitor = MemoryMonitor(enable=True)
    monitor.start_monitoring()

    logger = sys.modules["forge.core.logger"].forge_logger  # type: ignore[attr-defined]
    assert memory_usage_stub["args"]
    args = memory_usage_stub["args"][0]
    kwargs = memory_usage_stub["kwargs"][0]
    assert args == (-1,)
    assert kwargs["stream"] is monitor.log_stream
    assert kwargs["backend"] == "psutil_pss"
    info_messages = [call[0] for call in logger.info_calls]
    assert "Memory monitoring started" in info_messages
    assert any("Memory usage across time" in call[0] for call in logger.info_calls)


def test_start_monitoring_handles_exception(patch_thread, memory_usage_stub):
    monitor = MemoryMonitor(enable=True)
    memory_usage_stub["side_effect"] = RuntimeError("bad")
    monitor.start_monitoring()

    logger = sys.modules["forge.core.logger"].forge_logger  # type: ignore[attr-defined]
    assert any("Memory monitoring failed" in call[0] for call in logger.error_calls)


def test_stop_monitoring_resets_state(patch_thread, memory_usage_stub):
    monitor = MemoryMonitor(enable=True)
    monitor.start_monitoring()
    monitor.stop_monitoring()

    logger = sys.modules["forge.core.logger"].forge_logger  # type: ignore[attr-defined]
    assert monitor._monitoring_thread is None
    assert any("Memory monitoring stopped" in call[0] for call in logger.info_calls)


def test_stop_monitoring_no_enable():
    monitor = MemoryMonitor(enable=False)
    monitor.stop_monitoring()  # Should return early without logging
