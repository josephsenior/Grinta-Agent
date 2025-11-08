import asyncio
import sys
import types
from pathlib import Path, PurePosixPath
if "tenacity.stop.stop_base" not in sys.modules:
    stub_tenacity = types.ModuleType("tenacity.stop.stop_base")
    stub_tenacity.StopBase = type("StopBase", (), {})
    sys.modules["tenacity.stop.stop_base"] = stub_tenacity


import pytest

from forge.runtime.utils import files


def test_normalize_posix_path_handles_relative_and_absolute():
    rel = files._normalize_posix_path(PurePosixPath("a/./b/../c"))
    abs_posix = files._normalize_posix_path(PurePosixPath("/workspace/../etc/passwd"))

    assert str(rel) == "a/c"
    assert str(abs_posix) == "/etc/passwd"


def test_validate_path_access_outside_workspace_raises():
    sandbox_root = Path("/sandbox/workspace")
    outside = Path("/sandbox/../etc")

    with pytest.raises(PermissionError):
        files._validate_path_access(outside, sandbox_root, "../etc/passwd")


def test_resolve_path_converts_to_host_path(tmp_path):
    workspace_base = tmp_path
    workdir = "/sandbox/workspace/project"
    mount = "/sandbox/workspace"

    resolved = files.resolve_path("src/main.py", workdir, str(workspace_base), mount)

    assert resolved == workspace_base / "project" / "src" / "main.py"


def test_resolve_path_denies_escape(tmp_path):
    workspace_base = tmp_path
    workdir = "/sandbox/workspace/project"
    mount = "/sandbox/workspace"

    with pytest.raises(PermissionError):
        files.resolve_path("../../etc/passwd", workdir, str(workspace_base), mount)


def test_read_lines_bounds():
    lines = [f"line {i}\n" for i in range(5)]
    assert files.read_lines(lines, start=1, end=3) == ["line 1\n", "line 2\n"]
    assert files.read_lines(lines, start=10) == []


@pytest.mark.asyncio
async def test_read_file_success(tmp_path):
    workspace_base = tmp_path
    mount = "/sandbox/workspace"
    workdir = f"{mount}/project"
    target = workspace_base / "project"
    target.mkdir()
    file_path = target / "hello.txt"
    file_path.write_text("hello\nworld\n", encoding="utf-8")

    result = await files.read_file("hello.txt", workdir, str(workspace_base), mount, start=0, end=1)

    assert result.path == "hello.txt"
    assert result.content == "hello\n"


@pytest.mark.asyncio
async def test_read_file_permission_error(tmp_path):
    workspace_base = tmp_path
    mount = "/sandbox/workspace"
    workdir = f"{mount}/project"

    result = await files.read_file("../../secret.txt", workdir, str(workspace_base), mount)
    assert "not allowed" in result.message


@pytest.mark.asyncio
async def test_read_file_not_found(tmp_path):
    workspace_base = tmp_path
    mount = "/sandbox/workspace"
    workdir = f"{mount}/project"
    (workspace_base / "project").mkdir()

    result = await files.read_file("missing.txt", workdir, str(workspace_base), mount)
    assert "File not found" in result.message


@pytest.mark.asyncio
async def test_read_file_unicode_error(tmp_path):
    workspace_base = tmp_path
    mount = "/sandbox/workspace"
    workdir = f"{mount}/project"
    target = workspace_base / "project"
    target.mkdir()
    binary_path = target / "binary.dat"
    binary_path.write_bytes(b"\xff\xfe")

    result = await files.read_file("binary.dat", workdir, str(workspace_base), mount)
    assert "decoded as utf-8" in result.message


@pytest.mark.asyncio
async def test_read_file_directory_error(tmp_path, monkeypatch):
    workspace_base = tmp_path
    mount = "/sandbox/workspace"
    workdir = f"{mount}/project"
    directory = workspace_base / "project" / "dir"
    directory.mkdir(parents=True)

    monkeypatch.setattr(files, "resolve_path", lambda *args, **kwargs: directory)

    def fake_open(*args, **kwargs):
        raise IsADirectoryError("dir")

    monkeypatch.setattr("builtins.open", fake_open)

    result = await files.read_file("dir", workdir, str(workspace_base), mount)
    assert "directory" in result.message


@pytest.mark.asyncio
async def test_write_file_creates_and_inserts(tmp_path):
    workspace_base = tmp_path
    mount = "/sandbox/workspace"
    workdir = f"{mount}/project"
    target_dir = workspace_base / "project"
    target_dir.mkdir()
    file_path = target_dir / "greeting.txt"
    file_path.write_text("hello\nworld\n", encoding="utf-8")

    await files.write_file("greeting.txt", workdir, str(workspace_base), mount, "NEW", start=1, end=2)

    assert file_path.read_text(encoding="utf-8") == "hello\nNEW\n"


@pytest.mark.asyncio
async def test_write_file_permission_error(tmp_path):
    workspace_base = tmp_path
    mount = "/sandbox/workspace"
    workdir = f"{mount}/project"

    result = await files.write_file("../../secret.txt", workdir, str(workspace_base), mount, "data")
    assert "Permission error" in result.message


@pytest.mark.asyncio
async def test_write_file_directory_error(tmp_path):
    workspace_base = tmp_path
    mount = "/sandbox/workspace"
    workdir = f"{mount}/project"
    directory = workspace_base / "project" / "dir"
    directory.mkdir(parents=True)

    result = await files.write_file("dir", workdir, str(workspace_base), mount, "data")
    assert "directory" in result.message

