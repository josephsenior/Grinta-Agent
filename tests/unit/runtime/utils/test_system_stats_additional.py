from __future__ import annotations

import importlib.util
import sys
import types
from pathlib import Path

import pytest


MODULE_PATH = (
    Path(__file__).resolve().parents[4]
    / "forge"
    / "runtime"
    / "utils"
    / "system_stats.py"
)
spec = importlib.util.spec_from_file_location(
    "forge.runtime.utils.system_stats", MODULE_PATH
)
assert spec and spec.loader
system_stats = importlib.util.module_from_spec(spec)
sys.modules["forge.runtime.utils.system_stats"] = system_stats
spec.loader.exec_module(system_stats)


def test_get_system_info(monkeypatch):
    monkeypatch.setattr(system_stats, "_start_time", 1000)
    monkeypatch.setattr(system_stats, "_last_execution_time", 995)
    monkeypatch.setattr(system_stats.time, "time", lambda: 1005, raising=False)
    sentinel = {"cpu_percent": 0}
    monkeypatch.setattr(
        system_stats, "get_system_stats", lambda: sentinel, raising=False
    )
    info = system_stats.get_system_info()
    assert info["uptime"] == 5
    assert info["idle_time"] == 10
    assert info["resources"] is sentinel


def test_update_last_execution_time(monkeypatch):
    monkeypatch.setattr(system_stats.time, "time", lambda: 2000, raising=False)
    system_stats.update_last_execution_time()
    assert system_stats._last_execution_time == 2000


def test_get_system_stats(monkeypatch):
    class DummyProcess:
        def __init__(self):
            self.pid = 123
            self._cpu_calls = 0

        def cpu_percent(self):
            self._cpu_calls += 1
            return 12.5 if self._cpu_calls > 1 else 0.0

        def memory_info(self):
            return types.SimpleNamespace(rss=1024, vms=2048)

        def memory_percent(self):
            return 33.3

        def oneshot(self):
            return self

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            pass

    monkeypatch.setattr(
        system_stats.psutil, "Process", lambda: DummyProcess(), raising=False
    )
    monkeypatch.setattr(system_stats.time, "sleep", lambda _: None, raising=False)
    monkeypatch.setattr(
        system_stats.psutil,
        "disk_usage",
        lambda path: types.SimpleNamespace(total=10, used=4, free=6, percent=40.0),
        raising=False,
    )

    def fake_open(path, mode):
        assert path.endswith("/proc/123/io")
        lines = [
            b"read_bytes: 100\n",
            b"write_bytes: 200\n",
            b"ignored line\n",
        ]

        class DummyFile:
            def __enter__(self_inner):
                return iter(lines)

            def __exit__(self_inner, exc_type, exc, tb):
                pass

        return DummyFile()

    monkeypatch.setattr(system_stats, "open", fake_open, raising=False)
    stats = system_stats.get_system_stats()
    assert stats["cpu_percent"] == 12.5
    assert stats["memory"]["rss"] == 1024
    assert stats["memory"]["percent"] == 33.3
    assert stats["disk"]["used"] == 4
    assert stats["io"]["read_bytes"] == 100
    assert stats["io"]["write_bytes"] == 200


def test_get_system_stats_io_fallback(monkeypatch):
    class DummyProcess:
        pid = 123

        def cpu_percent(self):
            return 0.0

        def memory_info(self):
            return types.SimpleNamespace(rss=0, vms=0)

        def memory_percent(self):
            return 0.0

        def oneshot(self):
            return self

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            pass

    monkeypatch.setattr(
        system_stats.psutil, "Process", lambda: DummyProcess(), raising=False
    )
    monkeypatch.setattr(system_stats.time, "sleep", lambda _: None, raising=False)
    monkeypatch.setattr(
        system_stats.psutil,
        "disk_usage",
        lambda path: types.SimpleNamespace(total=1, used=0, free=1, percent=0.0),
        raising=False,
    )

    def raise_file_not_found(*args, **kwargs):
        raise FileNotFoundError()

    monkeypatch.setattr(system_stats, "open", raise_file_not_found, raising=False)
    stats = system_stats.get_system_stats()
    assert stats["io"]["read_bytes"] == 0
    assert stats["io"]["write_bytes"] == 0
