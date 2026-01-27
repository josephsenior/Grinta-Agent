import sys
import types

if "tenacity.stop.stop_base" not in sys.modules:

    class _StopModule(types.ModuleType):
        StopBase: type

    stub_tenacity = _StopModule("tenacity.stop.stop_base")
    setattr(stub_tenacity, "StopBase", type("StopBase", (), {}))
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
    assert result == [
        {"status": "D", "path": "old.py"},
        {"status": "A", "path": "new.py"},
    ]


def test_parse_git_status_line_invalid_raises():
    with pytest.raises(RuntimeError):
        git_changes._parse_git_status_line("", [])


def test_parse_git_status_line_regular():
    line = "M app.py"
    result = git_changes._parse_git_status_line(line, [line])
    assert result == [{"status": "M", "path": "app.py"}]


def test_parse_git_status_line_extra_parts_raises():
    line = "M app.py extra"
    with pytest.raises(RuntimeError):
        git_changes._parse_git_status_line(line, [line])


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


def test_get_valid_ref_uses_default_branch(monkeypatch):
    responses = {
        "git --no-pager rev-parse --abbrev-ref HEAD": "feature",
        'git --no-pager remote show origin | grep "HEAD branch"': "  HEAD branch: main",
        'git --no-pager rev-parse --verify $(git --no-pager merge-base HEAD "$(git --no-pager rev-parse --abbrev-ref origin/main)")': RuntimeError(
            "missing"
        ),
        "git --no-pager rev-parse --verify origin/main": "def456",
    }

    def fake_run(cmd, cwd):
        value = responses.get(cmd)
        if isinstance(value, RuntimeError):
            raise value
        if value is None:
            raise RuntimeError("unexpected")
        return value

    monkeypatch.setattr(git_changes, "run", fake_run)
    ref = git_changes.get_valid_ref("/repo")
    assert ref == "def456"


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


def test_get_changes_in_repo_no_ref(monkeypatch):
    monkeypatch.setattr(git_changes, "get_valid_ref", lambda _: None)
    assert git_changes.get_changes_in_repo("/repo") == []


def test_get_valid_ref_handles_all_failures(monkeypatch):
    monkeypatch.setattr(
        git_changes,
        "run",
        lambda *args, **kwargs: (_ for _ in ()).throw(RuntimeError("boom")),
    )
    assert git_changes.get_valid_ref("/repo") is None


def test_parse_git_status_line_copy(monkeypatch):
    line = "C100 orig.py copy.py"
    result = git_changes._parse_git_status_line(line, [line])
    assert result == [{"status": "A", "path": "copy.py"}]


def test_parse_git_status_line_copy_duplicate(monkeypatch):
    line = "C100 orig.py copy.py"
    result = git_changes._parse_git_status_line(line, [line])
    assert result == [{"status": "A", "path": "copy.py"}]


def test_parse_git_status_line_invalid_status_raises():
    with pytest.raises(RuntimeError):
        git_changes._normalize_status("Z", "file.txt", ["Z file.txt"])


def test_parse_git_status_line_single_token():
    with pytest.raises(RuntimeError):
        git_changes._parse_git_status_line("M", ["M"])


def test_get_git_changes_filters_subrepos(monkeypatch):
    monkeypatch.setattr(
        git_changes.glob, "glob", lambda pattern, root_dir, recursive: ["./sub/.git"]
    )

    def fake_get_changes(path):
        if path.endswith("sub"):
            return [{"status": "M", "path": "nested.txt"}]
        return [
            {"status": "M", "path": "sub/file.txt"},
            {"status": "A", "path": "root.txt"},
        ]

    monkeypatch.setattr(git_changes, "get_changes_in_repo", fake_get_changes)
    changes = git_changes.get_git_changes("/repo")
    assert {"status": "A", "path": "root.txt"} in changes
    assert {"status": "M", "path": "sub/nested.txt"} in changes
    assert all(change["path"] != "sub/file.txt" for change in changes)


def test_script_main_prints_json(monkeypatch):
    monkeypatch.setattr(
        git_changes,
        "get_git_changes",
        lambda cwd: [{"status": "M", "path": "file.txt"}],
    )
    captured = []

    class IOStub(types.ModuleType):
        def print_json_stdout(self, data):
            captured.append(data)

    sys.modules["forge.core.io"] = IOStub("forge.core.io")
    git_changes._main()
    assert captured == [[{"status": "M", "path": "file.txt"}]]


def test_script_main_fallback_stdout(monkeypatch):
    from io import StringIO

    monkeypatch.setattr(
        git_changes, "get_git_changes", lambda cwd: [{"status": "A", "path": "new.txt"}]
    )
    sys.modules.pop("forge.core.io", None)
    buffer = StringIO()
    monkeypatch.setattr(sys, "stdout", buffer)
    git_changes._main()
    assert '"path":"new.txt"' in buffer.getvalue()


def test_script_main_error_with_json(monkeypatch):
    monkeypatch.setattr(
        git_changes,
        "get_git_changes",
        lambda cwd: (_ for _ in ()).throw(RuntimeError("fail")),
    )
    captured = []

    class IOStub(types.ModuleType):
        def print_json_stdout(self, data):
            captured.append(data)

    sys.modules["forge.core.io"] = IOStub("forge.core.io")
    git_changes._main()
    assert captured == [{"error": "fail"}]


def test_script_main_error_fallback(monkeypatch):
    from io import StringIO

    monkeypatch.setattr(
        git_changes,
        "get_git_changes",
        lambda cwd: (_ for _ in ()).throw(RuntimeError("fail")),
    )
    sys.modules.pop("forge.core.io", None)
    buffer = StringIO()
    monkeypatch.setattr(sys, "stdout", buffer)
    git_changes._main()
    assert '"error":"fail"' in buffer.getvalue()
