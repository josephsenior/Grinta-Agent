from __future__ import annotations

import json
import os
import sys
import types
from pathlib import Path

import importlib.util
import pytest

if "forge.runtime.utils" not in sys.modules:
    sys.modules["forge.runtime.utils"] = types.ModuleType("forge.runtime.utils")

root_dir = Path(__file__).resolve().parents[4]
_GIT_DIFF_SPEC = importlib.util.spec_from_file_location(
    "forge.runtime.utils.git_diff",
    root_dir / "forge" / "runtime" / "utils" / "git_diff.py",
)
assert _GIT_DIFF_SPEC is not None
git_diff = importlib.util.module_from_spec(_GIT_DIFF_SPEC)
sys.modules["forge.runtime.utils.git_diff"] = git_diff
assert _GIT_DIFF_SPEC.loader is not None
_GIT_DIFF_SPEC.loader.exec_module(git_diff)


def test_get_closest_git_repo(tmp_path):
    repo = tmp_path / "repo"
    repo.mkdir()
    (repo / ".git").mkdir()
    nested = repo / "nested" / "dir"
    nested.mkdir(parents=True)
    assert git_diff.get_closest_git_repo(nested / "file.txt") == repo


def test_get_closest_git_repo_none(tmp_path):
    path = tmp_path / "folder"
    path.mkdir()
    assert git_diff.get_closest_git_repo(path / "file.txt") is None


def test_run_success(monkeypatch):
    class Result:
        returncode = 0
        stdout = b"ok"
        stderr = b""

    monkeypatch.setattr(git_diff.subprocess, "run", lambda **kwargs: Result())
    assert git_diff.run("echo ok", "/repo") == "ok"


def test_run_failure(monkeypatch):
    class Result:
        returncode = 1
        stdout = b""
        stderr = b"boom"

    monkeypatch.setattr(git_diff.subprocess, "run", lambda **kwargs: Result())
    with pytest.raises(RuntimeError, match="error_running_cmd:1:boom"):
        git_diff.run("fail", "/repo")


def test_get_valid_ref_prefers_origin(monkeypatch):
    commands = []

    def fake_run(cmd, cwd):
        commands.append(cmd)
        data = {
            "git --no-pager rev-parse --abbrev-ref HEAD": "main",
            "git --no-pager rev-parse --verify origin/main": "abc123",
        }
        if cmd in data:
            return data[cmd]
        raise RuntimeError("missing")

    monkeypatch.setattr(git_diff, "run", fake_run)
    ref = git_diff.get_valid_ref("/repo")
    assert ref == "abc123"
    assert "git --no-pager rev-parse --verify origin/main" in commands


def test_get_valid_ref_none(monkeypatch):
    monkeypatch.setattr(
        git_diff,
        "run",
        lambda *args, **kwargs: (_ for _ in ()).throw(RuntimeError("fail")),
    )
    assert git_diff.get_valid_ref("/repo") is None


def test_get_valid_ref_uses_default_branch(monkeypatch):
    sequence = {
        "git --no-pager rev-parse --abbrev-ref HEAD": "feature",
        "git --no-pager rev-parse --verify origin/feature": RuntimeError("missing"),
        'git --no-pager remote show origin | grep "HEAD branch"': "  HEAD branch: main",
        'git --no-pager rev-parse --verify $(git --no-pager merge-base HEAD "$(git --no-pager rev-parse --abbrev-ref origin/main)")': RuntimeError(
            "missing"
        ),
        "git --no-pager rev-parse --verify origin/main": "def456",
    }
    calls = []

    def fake_run(cmd, cwd):
        calls.append(cmd)
        value = sequence.get(cmd)
        if isinstance(value, RuntimeError):
            raise value
        if value is None:
            raise RuntimeError("unexpected")
        return value

    monkeypatch.setattr(git_diff, "run", fake_run)
    assert git_diff.get_valid_ref("/repo") == "def456"
    assert 'git --no-pager remote show origin | grep "HEAD branch"' in calls


def test_get_git_diff_file_too_large(tmp_path, monkeypatch):
    file_path = tmp_path / "big.txt"
    file_path.write_bytes(b"x" * 10)
    monkeypatch.setattr(git_diff, "MAX_FILE_SIZE_FOR_GIT_DIFF", 1)
    monkeypatch.setattr(os, "getcwd", lambda: str(tmp_path))
    with pytest.raises(ValueError, match="file_to_large"):
        git_diff.get_git_diff("big.txt")


def test_get_git_diff_no_repo(tmp_path, monkeypatch):
    file_path = tmp_path / "file.txt"
    file_path.write_text("content")
    monkeypatch.setattr(os, "getcwd", lambda: str(tmp_path))
    monkeypatch.setattr(git_diff, "MAX_FILE_SIZE_FOR_GIT_DIFF", 1024)
    with pytest.raises(ValueError, match="no_repository"):
        git_diff.get_git_diff("file.txt")


def test_get_git_diff_success(tmp_path, monkeypatch):
    repo = tmp_path / "repo"
    repo.mkdir()
    (repo / ".git").mkdir()
    file_path = repo / "file.txt"
    file_path.write_text("hello\nworld\n")

    monkeypatch.setattr(os, "getcwd", lambda: str(repo))
    monkeypatch.setattr(git_diff, "MAX_FILE_SIZE_FOR_GIT_DIFF", 1024)
    monkeypatch.setattr(git_diff, "get_closest_git_repo", lambda _: repo)
    monkeypatch.setattr(git_diff, "get_valid_ref", lambda _: "abc123")

    called = {}

    def fake_run(cmd, cwd):
        called["cmd"] = cmd
        return "old\ncontent"

    monkeypatch.setattr(git_diff, "run", fake_run)
    diff = git_diff.get_git_diff("file.txt")
    assert diff["original"] == "old\ncontent"
    assert diff["modified"] == "hello\nworld"
    assert Path("file.txt").as_posix() in called["cmd"]


def test_get_git_diff_missing_original(tmp_path, monkeypatch):
    repo = tmp_path / "repo"
    repo.mkdir()
    (repo / ".git").mkdir()
    file_path = repo / "file.txt"
    file_path.write_text("hello\n")

    monkeypatch.setattr(os, "getcwd", lambda: str(repo))
    monkeypatch.setattr(git_diff, "MAX_FILE_SIZE_FOR_GIT_DIFF", 1024)
    monkeypatch.setattr(git_diff, "get_closest_git_repo", lambda _: repo)
    monkeypatch.setattr(git_diff, "get_valid_ref", lambda _: "abc123")
    monkeypatch.setattr(
        git_diff,
        "run",
        lambda *args, **kwargs: (_ for _ in ()).throw(RuntimeError("fail")),
    )

    diff = git_diff.get_git_diff("file.txt")
    assert diff["original"] == ""
    assert diff["modified"] == "hello"


def test_get_git_diff_missing_file(tmp_path, monkeypatch):
    repo = tmp_path / "repo"
    repo.mkdir()
    (repo / ".git").mkdir()
    monkeypatch.setattr(os, "getcwd", lambda: str(repo))
    monkeypatch.setattr(os.path, "getsize", lambda _: 0)
    monkeypatch.setattr(git_diff, "MAX_FILE_SIZE_FOR_GIT_DIFF", 1024)
    monkeypatch.setattr(git_diff, "get_closest_git_repo", lambda _: repo)
    monkeypatch.setattr(git_diff, "get_valid_ref", lambda _: "abc123")
    monkeypatch.setattr(git_diff, "run", lambda *args, **kwargs: "orig")

    diff = git_diff.get_git_diff("missing.txt")
    assert diff["original"] == "orig"
    assert diff["modified"] == ""


def test_main_uses_print_json(monkeypatch):
    repo = Path("/repo")
    monkeypatch.setattr(git_diff, "get_git_diff", lambda path: {"result": path})
    captured = []

    class IOStub(types.ModuleType):
        def print_json_stdout(self, data):
            captured.append(data)

    sys.modules["forge.core.io"] = IOStub("forge.core.io")
    monkeypatch.setattr(sys, "argv", ["git_diff.py", "file.txt"])
    git_diff._main()
    assert captured == [{"result": "file.txt"}]


def test_main_fallback_stdout(monkeypatch):
    repo = Path("/repo")
    monkeypatch.setattr(git_diff, "get_git_diff", lambda path: {"result": path})
    sys.modules.pop("forge.core.io", None)
    buffer = []

    class Writer:
        def write(self, data):
            buffer.append(data)

        def flush(self):
            buffer.append("flush")

    monkeypatch.setattr(sys, "stdout", Writer())
    monkeypatch.setattr(sys, "argv", ["git_diff.py", "file.txt"])
    git_diff._main()
    assert any(
        '"result":"file.txt"' in chunk for chunk in buffer if isinstance(chunk, str)
    )
    assert "flush" in buffer
