from __future__ import annotations

import importlib.util
import os
import subprocess
import sys
import types
from collections.abc import Iterator
from typing import Any, cast

import pytest


ROOT = os.path.join(os.path.dirname(__file__), "..", "..", "..", "..")


class DummyLogger:
    def __init__(self) -> None:
        self.debug_calls: list[tuple[str, tuple[Any, ...]]] = []
        self.info_calls: list[tuple[str, tuple[Any, ...]]] = []
        self.warning_calls: list[tuple[str, tuple[Any, ...]]] = []
        self.error_calls: list[tuple[str, tuple[Any, ...]]] = []

    def debug(self, msg: str, *args: Any) -> None:
        self.debug_calls.append((msg, args))

    def info(self, msg: str, *args: Any) -> None:
        self.info_calls.append((msg, args))

    def warning(self, msg: str, *args: Any) -> None:
        self.warning_calls.append((msg, args))

    def error(self, msg: str, *args: Any) -> None:
        self.error_calls.append((msg, args))


if "forge.runtime.utils" not in sys.modules:
    sys.modules["forge.runtime.utils"] = types.ModuleType("forge.runtime.utils")

if "forge.core.logger" not in sys.modules:
    logger_stub = types.ModuleType("forge.core.logger")
    setattr(logger_stub, "forge_logger", DummyLogger())
    sys.modules["forge.core.logger"] = logger_stub


spec = importlib.util.spec_from_file_location(
    "forge.runtime.utils.runtime_init",
    os.path.join(ROOT, "forge", "runtime", "utils", "runtime_init.py"),
)
assert spec and spec.loader
runtime_init = importlib.util.module_from_spec(spec)
sys.modules["forge.runtime.utils.runtime_init"] = runtime_init
spec.loader.exec_module(runtime_init)


def make_logger() -> DummyLogger:
    return cast(DummyLogger, getattr(sys.modules["forge.core.logger"], "forge_logger"))


@pytest.fixture(autouse=True)
def reset_logger() -> Iterator[DummyLogger]:
    logger = make_logger()
    logger.debug_calls.clear()
    logger.info_calls.clear()
    logger.warning_calls.clear()
    logger.error_calls.clear()
    yield logger


def test_init_user_windows_creates_directory(monkeypatch, tmp_path):
    monkeypatch.setattr(runtime_init.sys, "platform", "win32", raising=False)
    created = []

    def fake_makedirs(path, exist_ok=False):
        created.append((path, exist_ok))

    monkeypatch.setattr(runtime_init.os, "makedirs", fake_makedirs, raising=False)
    result = runtime_init.init_user_and_working_directory(
        "user", 1000, str(tmp_path / "workspace")
    )
    assert result is None
    assert created == [(str(tmp_path / "workspace"), True)]


def test_init_user_skips_if_current_user(monkeypatch):
    monkeypatch.setattr(runtime_init.sys, "platform", "linux", raising=False)
    monkeypatch.setenv("USER", "alice")
    monkeypatch.setattr(runtime_init.os, "geteuid", lambda: 0, raising=False)
    result = runtime_init.init_user_and_working_directory("alice", 1000, "/tmp/work")
    assert result is None


def test_init_user_no_root_privileges(monkeypatch):
    monkeypatch.setattr(runtime_init.sys, "platform", "linux", raising=False)
    monkeypatch.setenv("USER", "root")
    monkeypatch.setattr(runtime_init.os, "geteuid", lambda: 1, raising=False)
    result = runtime_init.init_user_and_working_directory("agent", 1001, "/tmp/work")
    assert result is None


def test_init_user_existing_user_same_uid(monkeypatch):
    monkeypatch.setattr(runtime_init.sys, "platform", "linux", raising=False)
    monkeypatch.setattr(runtime_init.os, "geteuid", lambda: 0, raising=False)

    class FakeCompleted:
        def __init__(self, stdout, returncode=0):
            self.stdout = stdout.encode()
            self.stderr = b""
            self.returncode = returncode

    calls = []

    def fake_run(cmd, shell=False, check=False, capture_output=False):
        calls.append(cmd)
        if cmd[:2] == ["id", "-u"]:
            return FakeCompleted("1001", returncode=0)
        return FakeCompleted("", returncode=0)

    monkeypatch.setattr(runtime_init.subprocess, "run", fake_run, raising=False)
    result = runtime_init.init_user_and_working_directory("agent", 1001, "/tmp/work")
    assert result is None


def test_init_user_existing_user_different_uid(monkeypatch):
    monkeypatch.setattr(runtime_init.sys, "platform", "linux", raising=False)
    monkeypatch.setattr(runtime_init.os, "geteuid", lambda: 0, raising=False)

    class FakeCompleted:
        def __init__(self, stdout, returncode=0):
            self.stdout = stdout.encode()
            self.stderr = b""
            self.returncode = returncode

    def fake_run(cmd, shell=False, check=False, capture_output=False):
        if cmd[:2] == ["id", "-u"]:
            return FakeCompleted("2000", returncode=0)
        raise AssertionError("subprocess.run should not continue beyond UID mismatch")

    monkeypatch.setattr(runtime_init.subprocess, "run", fake_run, raising=False)
    result = runtime_init.init_user_and_working_directory("agent", 1001, "/tmp/work")
    assert result == 2000


def test_init_user_handles_id_failure(monkeypatch):
    monkeypatch.setattr(runtime_init.sys, "platform", "linux", raising=False)
    monkeypatch.setattr(runtime_init.os, "geteuid", lambda: 0, raising=False)

    class FakeCalledProcessError(subprocess.CalledProcessError):
        def __init__(self, returncode):
            super().__init__(returncode, cmd=["id", "-u"])

    call_sequence = []

    def fake_run(cmd, shell=False, check=False, capture_output=False):
        call_sequence.append(cmd)
        if cmd[:2] == ["id", "-u"]:
            raise FakeCalledProcessError(1)
        return types.SimpleNamespace(returncode=0, stdout=b"", stderr=b"")

    monkeypatch.setattr(runtime_init.subprocess, "run", fake_run, raising=False)
    result = runtime_init.init_user_and_working_directory("agent", 1001, "/tmp/work")
    assert result is None
    assert any(
        "%sudo ALL=(ALL) NOPASSWD:ALL" in cmd[-1]
        for cmd in call_sequence
        if isinstance(cmd, list)
    )


def test_init_user_creates_user(monkeypatch):
    monkeypatch.setattr(runtime_init.sys, "platform", "linux", raising=False)
    monkeypatch.setattr(runtime_init.os, "geteuid", lambda: 0, raising=False)

    commands = []

    class FakeCompleted:
        def __init__(self, returncode=0):
            self.returncode = returncode
            self.stdout = b""
            self.stderr = b""

    def fake_run(cmd, shell=False, check=False, capture_output=False):
        commands.append(cmd)
        if cmd[:2] == ["id", "-u"]:
            raise subprocess.CalledProcessError(1, cmd)
        if cmd and cmd[0] == "useradd":
            return FakeCompleted(0)
        return FakeCompleted(0)

    monkeypatch.setattr(runtime_init.subprocess, "run", fake_run, raising=False)
    result = runtime_init.init_user_and_working_directory("agent", 1001, "/tmp/work")
    assert result is None
    assert any(cmd and cmd[0] == "useradd" for cmd in commands)


def test_init_user_useradd_failure(monkeypatch):
    monkeypatch.setattr(runtime_init.sys, "platform", "linux", raising=False)
    monkeypatch.setattr(runtime_init.os, "geteuid", lambda: 0, raising=False)

    commands = []

    class FakeCompleted:
        def __init__(self, returncode=0, stderr=b""):
            self.returncode = returncode
            self.stdout = b""
            self.stderr = stderr

    def fake_run(cmd, shell=False, check=False, capture_output=False):
        commands.append(cmd)
        if cmd[:2] == ["id", "-u"]:
            raise subprocess.CalledProcessError(1, cmd)
        if cmd and cmd[0] == "useradd":
            return FakeCompleted(returncode=1, stderr=b"failed")
        return FakeCompleted(0)

    monkeypatch.setattr(runtime_init.subprocess, "run", fake_run, raising=False)
    result = runtime_init.init_user_and_working_directory("agent", 1001, "/tmp/work")
    assert result is None
    logger = make_logger()
    assert any("Failed to create user" in msg for msg, _ in logger.warning_calls)


def test_init_user_handles_unexpected_id_error(monkeypatch):
    monkeypatch.setattr(runtime_init.sys, "platform", "linux", raising=False)
    monkeypatch.setattr(runtime_init.os, "geteuid", lambda: 0, raising=False)

    class FakeCalledProcessError(subprocess.CalledProcessError):
        def __init__(self, returncode):
            super().__init__(returncode, cmd=["id", "-u"])

    def fake_run(cmd, shell=False, check=False, capture_output=False):
        if cmd[:2] == ["id", "-u"]:
            raise FakeCalledProcessError(2)
        return types.SimpleNamespace(returncode=0, stdout=b"", stderr=b"")

    monkeypatch.setattr(runtime_init.subprocess, "run", fake_run, raising=False)
    with pytest.raises(subprocess.CalledProcessError):
        runtime_init.init_user_and_working_directory("agent", 1001, "/tmp/work")


def test_init_user_sudoer_failure(monkeypatch):
    monkeypatch.setattr(runtime_init.sys, "platform", "linux", raising=False)
    monkeypatch.setattr(runtime_init.os, "geteuid", lambda: 0, raising=False)
    sequence = []

    class FakeCompleted:
        def __init__(self, returncode=0, stdout=b"", stderr=b""):
            self.returncode = returncode
            self.stdout = stdout
            self.stderr = stderr

    def fake_run(cmd, shell=False, check=False, capture_output=False):
        sequence.append(cmd)
        if cmd[:2] == ["id", "-u"]:
            raise subprocess.CalledProcessError(1, cmd)
        if "%sudo ALL=(ALL) NOPASSWD:ALL" in cmd[-1]:
            return FakeCompleted(returncode=1, stderr=b"nope")
        return FakeCompleted()

    monkeypatch.setattr(runtime_init.subprocess, "run", fake_run, raising=False)
    runtime_init.init_user_and_working_directory("agent", 1001, "/tmp/work")
    logger = make_logger()
    assert any("Failed to add sudoer entry" in msg for msg, _ in logger.warning_calls)


def test_init_user_directory_commands(monkeypatch):
    monkeypatch.setattr(runtime_init.sys, "platform", "linux", raising=False)
    monkeypatch.setattr(runtime_init.os, "geteuid", lambda: 0, raising=False)

    executed = []

    class FakeCompleted:
        def __init__(self, returncode=0, stdout=b"output", stderr=b""):
            self.returncode = returncode
            self.stdout = stdout
            self.stderr = stderr

    def fake_run(cmd, shell=False, check=False, capture_output=False):
        executed.append(cmd)
        if cmd[:2] == ["id", "-u"]:
            raise subprocess.CalledProcessError(1, cmd)
        return FakeCompleted()

    monkeypatch.setattr(runtime_init.subprocess, "run", fake_run, raising=False)
    runtime_init.init_user_and_working_directory("agent", 1001, "/workspace")
    assert executed[-3][0] == "sh"  # umask/mkdir command
    assert executed[-2][0] == "chown"
    assert executed[-1][0] == "chmod"
