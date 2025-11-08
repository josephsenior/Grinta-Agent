import sys
import types
if "tenacity.stop.stop_base" not in sys.modules:
    stub_tenacity = types.ModuleType("tenacity.stop.stop_base")
    stub_tenacity.StopBase = type("StopBase", (), {})
    sys.modules["tenacity.stop.stop_base"] = stub_tenacity


import pytest

from forge.runtime.utils import git_changes


def test_normalize_status_unknown_raises():
    with pytest.raises(RuntimeError):
        git_changes._normalize_status("X", "file.txt", ["X file.txt"])


@pytest.mark.parametrize(
    ("status", "path", "expected"),
    [
        ("??", "new.txt", {"status": "A", "path": "new.txt"}),
        ("*", "file.txt", {"status": "M", "path": "file.txt"}),
        ("M", "edit.txt", {"status": "M", "path": "edit.txt"}),
    ],
)
def test_normalize_status_variants(status, path, expected):
    assert git_changes._normalize_status(status, path, []) == expected


def test_parse_git_status_line_handles_rename():
    line = "R100 old.py new.py"
    result = git_changes._parse_git_status_line(line, [line])
    assert result == [{"status": "D", "path": "old.py"}, {"status": "A", "path": "new.py"}]


def test_parse_git_status_line_invalid_raises():
    with pytest.raises(RuntimeError):
        git_changes._parse_git_status_line("", [])


def test_parse_git_status_line_regular():
    line = "M app.py"
    result = git_changes._parse_git_status_line(line, [line])
    assert result == [{"status": "M", "path": "app.py"}]


def test_get_valid_ref_prefers_current_branch(monkeypatch):
    commands = []

    def fake_run(cmd, cwd):
        commands.append(cmd)
        if "abbrev-ref HEAD" in cmd:
            return "main"
        if "rev-parse --verify origin/main" in cmd:
            return "abc123"
        raise RuntimeError("missing")

    monkeypatch.setattr(git_changes, "run", fake_run)
    ref = git_changes.get_valid_ref("/repo")

    assert ref == "abc123"
    assert any("rev-parse --verify origin/main" in cmd for cmd in commands)


def test_run_success_and_failure(monkeypatch):
    class Result:
        def __init__(self, code, stdout=b"", stderr=b""):
            self.returncode = code
            self.stdout = stdout
            self.stderr = stderr

    calls = []

    def fake_subprocess_run(**kwargs):
        calls.append(kwargs["args"])
        if kwargs["args"] == ["git", "--version"]:
            return Result(0, stdout=b"git version")
        return Result(1, stderr=b"boom")

    monkeypatch.setattr(git_changes.subprocess, "run", fake_subprocess_run)
    assert git_changes.run("git --version", "/tmp") == "git version"

    with pytest.raises(RuntimeError):
        git_changes.run("git status", "/tmp")


def test_get_changes_in_repo_combines_status(monkeypatch):
    def fake_run(cmd, cwd):
        if "abbrev-ref HEAD" in cmd:
            return "main"
        if "rev-parse --verify origin/main" in cmd:
            return "abc123"
        if "diff --name-status" in cmd:
            return "M app.py\nR100 old.py new.py"
        if "ls-files" in cmd:
            return "extra.txt\n"
        raise RuntimeError("unexpected")

    monkeypatch.setattr(git_changes, "run", fake_run)
    changes = git_changes.get_changes_in_repo("/repo")

    assert {"status": "M", "path": "app.py"} in changes
    assert {"status": "D", "path": "old.py"} in changes
    assert {"status": "A", "path": "new.py"} in changes
    assert {"status": "A", "path": "extra.txt"} in changes

