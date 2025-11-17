from __future__ import annotations

import importlib.util
import os
import sys
import types
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pytest


ROOT = Path(__file__).resolve().parents[4]

if "forge.runtime.utils" not in sys.modules:
    sys.modules["forge.runtime.utils"] = types.ModuleType("forge.runtime.utils")

# Provide stub logger used by port_lock
logger_mod = sys.modules.setdefault(
    "forge.core.logger", types.ModuleType("forge.core.logger")
)
if not hasattr(logger_mod, "forge_logger"):

    class StubLogger:
        def __init__(self):
            self.debug_calls: list[Any] = []
            self.info_calls: list[Any] = []
            self.warning_calls: list[Any] = []
            self.error_calls: list[Any] = []

        def debug(self, msg, *args, **kwargs):
            self.debug_calls.append((msg, args, kwargs))

        def info(self, msg, *args, **kwargs):
            self.info_calls.append((msg, args, kwargs))

        def warning(self, msg, *args, **kwargs):
            self.warning_calls.append((msg, args, kwargs))

        def error(self, msg, *args, **kwargs):
            self.error_calls.append((msg, args, kwargs))

    setattr(logger_mod, "forge_logger", StubLogger())

# Provide stub fcntl so module sets HAS_FCNTL True deterministically
fcntl_mod = sys.modules.setdefault("fcntl", types.ModuleType("fcntl"))
if not hasattr(fcntl_mod, "LOCK_EX"):
    setattr(fcntl_mod, "LOCK_EX", 1)
    setattr(fcntl_mod, "LOCK_NB", 2)
    setattr(fcntl_mod, "LOCK_UN", 8)

    def _default_flock(fd, flags):
        return None

    setattr(fcntl_mod, "flock", _default_flock)

spec = importlib.util.spec_from_file_location(
    "forge.runtime.utils.port_lock",
    ROOT / "forge" / "runtime" / "utils" / "port_lock.py",
)
assert spec and spec.loader
port_lock_mod = importlib.util.module_from_spec(spec)
sys.modules["forge.runtime.utils.port_lock"] = port_lock_mod
spec.loader.exec_module(port_lock_mod)

PortLock = port_lock_mod.PortLock
find_available_port_with_lock = port_lock_mod.find_available_port_with_lock
cleanup_stale_locks = port_lock_mod.cleanup_stale_locks
_check_port_available = port_lock_mod._check_port_available


def _set_has_fcntl(value: bool) -> None:
    setattr(port_lock_mod, "HAS_FCNTL", value)


if not hasattr(port_lock_mod, "HAS_FCNTL"):
    _set_has_fcntl(False)


@pytest.fixture(autouse=True)
def reset_logger():
    stub_logger = sys.modules["forge.core.logger"].forge_logger  # type: ignore[attr-defined]
    stub_logger.debug_calls.clear()
    stub_logger.info_calls.clear()
    stub_logger.warning_calls.clear()
    stub_logger.error_calls.clear()
    yield stub_logger


@pytest.fixture
def temp_lock_dir(tmp_path):
    return tmp_path


def test_acquire_with_fcntl_success(monkeypatch, temp_lock_dir):
    _set_has_fcntl(True)
    fake_fd = 42
    write_calls: list[tuple[int, bytes]] = []
    fsync_calls: list[int] = []
    flock_calls: list[tuple[int, int]] = []

    def fake_open(path, flags):
        assert path.endswith("port_1234.lock")
        return fake_fd

    def fake_write(fd, data):
        write_calls.append((fd, data))

    def fake_fsync(fd):
        fsync_calls.append(fd)

    def fake_close(fd):
        assert fd == fake_fd

    def fake_flock(fd, flags):
        flock_calls.append((fd, flags))

    monkeypatch.setattr(port_lock_mod.os, "open", fake_open)
    monkeypatch.setattr(port_lock_mod.os, "write", fake_write)
    monkeypatch.setattr(port_lock_mod.os, "fsync", fake_fsync)
    monkeypatch.setattr(port_lock_mod.os, "close", fake_close)
    monkeypatch.setattr(port_lock_mod.fcntl, "flock", fake_flock)

    lock = PortLock(1234, lock_dir=str(temp_lock_dir))
    assert lock.acquire(timeout=0.1) is True
    assert lock.is_locked
    assert lock.lock_fd == fake_fd
    assert write_calls == [(fake_fd, b"1234\n")]
    assert fsync_calls == [fake_fd]
    assert flock_calls[0][0] == fake_fd


def test_acquire_with_fcntl_timeout(monkeypatch, temp_lock_dir):
    _set_has_fcntl(True)
    fake_fd = 10
    times = [0.0, 0.05, 0.2, 1.5]

    def fake_time():
        return times.pop(0)

    def fake_sleep(delay):
        pass

    def fake_open(path, flags):
        return fake_fd

    def fake_close(fd):
        pass

    def fake_flock(fd, flags):
        raise OSError("locked")

    monkeypatch.setattr(port_lock_mod.time, "time", fake_time)
    monkeypatch.setattr(port_lock_mod.time, "sleep", fake_sleep)
    monkeypatch.setattr(port_lock_mod.os, "open", fake_open)
    monkeypatch.setattr(port_lock_mod.os, "close", fake_close)
    monkeypatch.setattr(port_lock_mod.fcntl, "flock", fake_flock)

    lock = PortLock(2222, lock_dir=str(temp_lock_dir))
    assert lock.acquire(timeout=0.5) is False
    assert lock.lock_fd is None
    assert not lock.is_locked


def test_acquire_without_fcntl_success(monkeypatch, temp_lock_dir):
    _set_has_fcntl(False)
    fake_fd = 55
    open_calls = []

    def fake_open(path, flags):
        open_calls.append(path)
        return fake_fd

    def fake_write(fd, data):
        pass

    def fake_fsync(fd):
        pass

    monkeypatch.setattr(port_lock_mod.os, "open", fake_open)
    monkeypatch.setattr(port_lock_mod.os, "write", fake_write)
    monkeypatch.setattr(port_lock_mod.os, "fsync", fake_fsync)

    lock = PortLock(3333, lock_dir=str(temp_lock_dir))
    assert lock.acquire(timeout=0.1)
    assert lock.is_locked
    assert open_calls


def test_acquire_without_fcntl_failure(monkeypatch, temp_lock_dir):
    _set_has_fcntl(False)
    times = [0.0, 0.05, 0.2]

    def fake_time():
        return times.pop(0)

    def fake_sleep(delay):
        pass

    def fake_open(path, flags):
        raise OSError("busy")

    monkeypatch.setattr(port_lock_mod.time, "time", fake_time)
    monkeypatch.setattr(port_lock_mod.time, "sleep", fake_sleep)
    monkeypatch.setattr(port_lock_mod.os, "open", fake_open)

    lock = PortLock(4444, lock_dir=str(temp_lock_dir))
    assert lock.acquire(timeout=0.1) is False
    assert not lock.is_locked


def test_acquire_exception_triggers_cleanup(monkeypatch, temp_lock_dir):
    _set_has_fcntl(True)
    cleanup_called = []

    def fake_open(path, flags):
        raise RuntimeError("boom")

    def fake_cleanup(self):
        cleanup_called.append(True)

    monkeypatch.setattr(port_lock_mod.os, "open", fake_open)
    monkeypatch.setattr(PortLock, "_cleanup_on_failure", fake_cleanup, raising=False)

    lock = PortLock(5555, lock_dir=str(temp_lock_dir))
    assert lock.acquire(timeout=0.1) is False
    assert cleanup_called
    assert not lock.is_locked


def test_release_with_fcntl(monkeypatch, temp_lock_dir):
    _set_has_fcntl(True)
    fake_fd = 90
    unlock_calls = []
    closed = []
    removed = []

    def fake_flock(fd, flags):
        unlock_calls.append((fd, flags))

    def fake_close(fd):
        closed.append(fd)

    def fake_unlink(path):
        removed.append(path)

    monkeypatch.setattr(port_lock_mod.fcntl, "flock", fake_flock)
    monkeypatch.setattr(port_lock_mod.os, "close", fake_close)
    monkeypatch.setattr(port_lock_mod.os, "unlink", fake_unlink)

    lock = PortLock(7777, lock_dir=str(temp_lock_dir))
    lock.lock_fd = fake_fd
    lock._locked = True
    lock.release()

    assert unlock_calls and unlock_calls[0][0] == fake_fd
    assert closed == [fake_fd]
    assert removed and removed[0].endswith("port_7777.lock")
    assert not lock.is_locked


def test_release_without_fd(monkeypatch):
    _set_has_fcntl(False)
    lock = PortLock(8888)
    lock.lock_fd = None
    lock.release()  # Should not raise


def test_context_manager_success(monkeypatch, temp_lock_dir):
    _set_has_fcntl(False)

    def fake_open(path, flags):
        return 11

    monkeypatch.setattr(port_lock_mod.os, "open", fake_open)
    monkeypatch.setattr(port_lock_mod.os, "write", lambda fd, data: None)
    monkeypatch.setattr(port_lock_mod.os, "fsync", lambda fd: None)

    with PortLock(9999, lock_dir=str(temp_lock_dir)) as lock:
        assert lock.is_locked
    assert not lock.is_locked


def test_context_manager_failure(monkeypatch):
    monkeypatch.setattr(
        PortLock, "acquire", lambda self, timeout=1.0: False, raising=False
    )
    lock = PortLock(1010)
    with pytest.raises(OSError):
        lock.__enter__()


def test_find_available_port_random_success(monkeypatch):
    sequence = [
        32000,
        32000,
        32000,
    ]  # First randint for random attempt, others for start_port

    class FakeRandom:
        def randint(self, a, b):
            if sequence:
                return sequence.pop(0)
            return a

    created_locks: list[Any] = []

    @dataclass
    class FakeLock:
        port: int

        def __post_init__(self):
            created_locks.append(self)
            self.acquired = False
            self.released = False

        def acquire(self, timeout=1.0):
            self.acquired = True
            return True

        def release(self):
            self.released = True

    monkeypatch.setattr(port_lock_mod.random, "SystemRandom", lambda: FakeRandom())
    monkeypatch.setattr(port_lock_mod, "PortLock", FakeLock)
    monkeypatch.setattr(
        port_lock_mod,
        "_check_port_available",
        lambda port, bind_address="0.0.0.0": True,
    )

    result = find_available_port_with_lock(
        min_port=32000, max_port=32010, max_attempts=4
    )
    assert result is not None
    port, lock = result
    assert port == 32000
    assert lock.acquired
    assert not lock.released


def test_find_available_port_releases_when_unavailable(monkeypatch):
    sequence = [33000, 33000, 33000]

    class FakeRandom:
        def randint(self, a, b):
            if sequence:
                return sequence.pop(0)
            return a

    created_locks: list[Any] = []

    @dataclass
    class FakeLock:
        port: int
        acquired: bool = False
        released: bool = False

        def acquire(self, timeout=1.0):
            self.acquired = True
            return True

        def release(self):
            self.released = True

    def make_lock(port):
        lock = FakeLock(port)
        created_locks.append(lock)
        return lock

    monkeypatch.setattr(port_lock_mod.random, "SystemRandom", lambda: FakeRandom())
    monkeypatch.setattr(port_lock_mod, "PortLock", make_lock)
    monkeypatch.setattr(
        port_lock_mod,
        "_check_port_available",
        lambda port, bind_address="0.0.0.0": False,
    )

    result = find_available_port_with_lock(
        min_port=33000, max_port=33005, max_attempts=2
    )
    assert result is None
    assert created_locks
    assert all(lock.released for lock in created_locks if lock.acquired)


def test_find_available_port_logs_failure(monkeypatch):
    class FakeRandom:
        def randint(self, a, b):
            return a

    class FakeLock:
        def __init__(self, port):
            self.port = port

        def acquire(self, timeout=1.0):
            return False

        def release(self):
            pass

    monkeypatch.setattr(port_lock_mod.random, "SystemRandom", lambda: FakeRandom())
    monkeypatch.setattr(port_lock_mod, "PortLock", FakeLock)
    monkeypatch.setattr(
        port_lock_mod, "_check_port_available", lambda *args, **kwargs: False
    )

    result = find_available_port_with_lock(
        min_port=34000, max_port=34002, max_attempts=2
    )
    assert result is None
    logger = sys.modules["forge.core.logger"].forge_logger  # type: ignore[attr-defined]
    assert logger.error_calls


def test_check_port_available_success(monkeypatch):
    bind_calls: list[Any] = []

    class FakeSocket:
        def __init__(self, *args, **kwargs):
            bind_calls.append(("create", args, kwargs))

        def setsockopt(self, *args):
            pass

        def bind(self, addr):
            bind_calls.append(("bind", addr))

        def close(self):
            bind_calls.append(("close", None))

    monkeypatch.setattr(
        port_lock_mod.socket,
        "socket",
        lambda *args, **kwargs: FakeSocket(*args, **kwargs),
    )
    assert _check_port_available(40000)
    assert ("bind", ("0.0.0.0", 40000)) in bind_calls
    assert ("close", None) in bind_calls


def test_check_port_available_failure(monkeypatch):
    class FakeSocket:
        def setsockopt(self, *args):
            pass

        def bind(self, addr):
            raise OSError("busy")

        def close(self):
            pass

    monkeypatch.setattr(
        port_lock_mod.socket, "socket", lambda *args, **kwargs: FakeSocket()
    )
    assert _check_port_available(45000) is False


def test_cleanup_stale_locks(monkeypatch, temp_lock_dir):
    base_dir = temp_lock_dir
    lock_dir = base_dir / "FORGE_port_locks"
    lock_dir.mkdir()
    old_file = base_dir / "port_1.lock"
    new_file = base_dir / "port_2.lock"
    other_file = base_dir / "ignore.txt"
    (lock_dir / old_file.name).write_text("")
    (lock_dir / new_file.name).write_text("")
    (lock_dir / other_file.name).write_text("")
    now = 1000.0
    os.utime(lock_dir / old_file.name, (now - 400, now - 400))
    os.utime(lock_dir / new_file.name, (now - 100, now - 100))

    monkeypatch.setattr(port_lock_mod.tempfile, "gettempdir", lambda: str(base_dir))
    monkeypatch.setattr(port_lock_mod.time, "time", lambda: now)

    cleaned = cleanup_stale_locks(max_age_seconds=200)
    assert cleaned == 1
    assert not (lock_dir / old_file.name).exists()
    assert (lock_dir / new_file.name).exists()
    logger = sys.modules["forge.core.logger"].forge_logger  # type: ignore[attr-defined]
    assert any(
        call[0] == "Cleaned up %s stale port lock files" and call[1] and call[1][0] == 1
        for call in logger.info_calls
    )


def test_cleanup_stale_locks_handles_oserror(monkeypatch):
    monkeypatch.setattr(port_lock_mod.os.path, "exists", lambda path: True)
    monkeypatch.setattr(
        port_lock_mod.os, "listdir", lambda path: (_ for _ in ()).throw(OSError("fail"))
    )
    assert cleanup_stale_locks() == 0


def test_cleanup_stale_locks_handles_stat_error(monkeypatch, temp_lock_dir):
    base_dir = temp_lock_dir
    lock_dir = base_dir / "FORGE_port_locks"
    lock_dir.mkdir()
    (lock_dir / "port_err.lock").write_text("")
    real_stat = port_lock_mod.os.stat

    def fake_stat(path):
        if str(path).endswith("port_err.lock"):
            raise OSError("stat fail")
        return real_stat(path)

    monkeypatch.setattr(port_lock_mod.tempfile, "gettempdir", lambda: str(base_dir))
    monkeypatch.setattr(port_lock_mod.time, "time", lambda: 1000.0)
    monkeypatch.setattr(port_lock_mod.os, "stat", fake_stat)
    cleanup_stale_locks(max_age_seconds=10)


def test_write_lock_info_requires_fd():
    lock = PortLock(5000)
    with pytest.raises(RuntimeError):
        lock._write_lock_info()


def test_cleanup_on_failure_closes_descriptor(monkeypatch):
    lock = PortLock(6000)
    lock.lock_fd = 777
    closed = []
    monkeypatch.setattr(port_lock_mod.os, "close", lambda fd: closed.append(fd))
    lock._cleanup_on_failure()
    assert closed == [777]
    assert lock.lock_fd is None


def test_acquire_returns_true_when_already_locked():
    lock = PortLock(6100)
    lock._locked = True
    assert lock.acquire() is True


def test_release_logs_warning_on_error(monkeypatch):
    _set_has_fcntl(False)
    lock = PortLock(6200)
    lock.lock_fd = 888
    lock._locked = True
    monkeypatch.setattr(
        port_lock_mod.os,
        "close",
        lambda fd: (_ for _ in ()).throw(OSError("close failed")),
    )
    monkeypatch.setattr(port_lock_mod.os, "unlink", lambda path: None)
    lock.release()
    logger = sys.modules["forge.core.logger"].forge_logger  # type: ignore[attr-defined]
    assert any(
        "Error releasing lock for port" in call[0] for call in logger.warning_calls
    )
    assert lock.lock_fd is None
    assert not lock.is_locked


def test_find_available_port_sequential_wraparound(monkeypatch):
    sequence = [11, 11, 11]

    class FakeRandom:
        def randint(self, a, b):
            if sequence:
                return sequence.pop(0)
            return a

    @dataclass
    class FakeLock:
        port: int
        released: bool = False

        def acquire(self, timeout=1.0):
            return self.port == 10

        def release(self):
            self.released = True

    def check_port(port, bind_address="0.0.0.0"):
        return port == 10

    monkeypatch.setattr(port_lock_mod.random, "SystemRandom", lambda: FakeRandom())
    monkeypatch.setattr(port_lock_mod, "PortLock", FakeLock)
    monkeypatch.setattr(port_lock_mod, "_check_port_available", check_port)

    result = find_available_port_with_lock(min_port=10, max_port=11, max_attempts=4)
    assert result is not None
    port, lock = result
    assert port == 10
    assert isinstance(lock, FakeLock)


def test_port_lock_import_without_fcntl(monkeypatch, tmp_path):
    original_fcntl = sys.modules.pop("fcntl", None)
    module_name = "forge.runtime.utils.port_lock_no_fcntl"
    try:
        spec = importlib.util.spec_from_file_location(
            module_name, ROOT / "forge" / "runtime" / "utils" / "port_lock.py"
        )
        assert spec and spec.loader
        module = importlib.util.module_from_spec(spec)
        sys.modules[module_name] = module
        spec.loader.exec_module(module)
        assert module.HAS_FCNTL is False
        lock = module.PortLock(7000, lock_dir=str(tmp_path))
        with pytest.raises(RuntimeError):
            lock._acquire_with_fcntl(timeout=0.01)
    finally:
        sys.modules.pop(module_name, None)
        if original_fcntl is not None:
            sys.modules["fcntl"] = original_fcntl
        else:
            sys.modules.pop("fcntl", None)


def test_cleanup_stale_locks_no_dir(monkeypatch):
    monkeypatch.setattr(port_lock_mod.os.path, "exists", lambda path: False)
    assert cleanup_stale_locks() == 0
