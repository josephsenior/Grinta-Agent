from __future__ import annotations

import importlib.util
import sys
import types
from pathlib import Path, PurePosixPath

import pytest


if "forge.events.observation" not in sys.modules:
    obs_module = types.ModuleType("forge.events.observation")

    class Observation:
        def __init__(self, content: str | None = None, path: str | None = None):
            self.content = content
            self.path = path

    class ErrorObservation(Observation):
        pass

    class FileReadObservation(Observation):
        pass

    class FileWriteObservation(Observation):
        pass

    setattr(obs_module, "Observation", Observation)
    setattr(obs_module, "ErrorObservation", ErrorObservation)
    setattr(obs_module, "FileReadObservation", FileReadObservation)
    setattr(obs_module, "FileWriteObservation", FileWriteObservation)
    sys.modules["forge.events.observation"] = obs_module
obs_module = sys.modules["forge.events.observation"]
ObservationType = getattr(obs_module, "Observation")
ErrorObservationType = getattr(obs_module, "ErrorObservation")
FileReadObservationType = getattr(obs_module, "FileReadObservation")
FileWriteObservationType = getattr(obs_module, "FileWriteObservation")


MODULE_PATH = (
    Path(__file__).resolve().parents[4] / "forge" / "runtime" / "utils" / "files.py"
)
spec = importlib.util.spec_from_file_location("forge.runtime.utils.files", MODULE_PATH)
assert spec and spec.loader
files_mod = importlib.util.module_from_spec(spec)
sys.modules["forge.runtime.utils.files"] = files_mod
spec.loader.exec_module(files_mod)


def test_resolve_path_success(tmp_path):
    workspace_base = tmp_path / "workspace"
    workspace_base.mkdir()
    path = files_mod.resolve_path(
        "src/main.py",
        str(workspace_base),
        str(workspace_base),
    )
    assert path == (workspace_base / "src" / "main.py").resolve()


def test_resolve_path_variants(tmp_path):
    workspace_base = tmp_path / "workspace"
    nested = workspace_base / "project" / "sub"
    nested.mkdir(parents=True)
    host = str(workspace_base)

    rel = files_mod.resolve_path(
        "project/sub/test.txt", host, host
    )
    assert rel == workspace_base / "project" / "sub" / "test.txt"

    nested_rel = files_mod.resolve_path(
        "test.txt", str(workspace_base / "project"), host
    )
    assert nested_rel == workspace_base / "project" / "test.txt"


def test_resolve_path_permission_error(tmp_path):
    with pytest.raises(PermissionError):
        files_mod.resolve_path(
            "../outside.txt",
            str(tmp_path / "workspace"),
            str(tmp_path / "workspace"),
        )


def test_read_lines():
    lines = ["a\n", "b\n", "c\n", "d\n"]
    assert files_mod.read_lines(lines, 1, 3) == ["b\n", "c\n"]
    assert files_mod.read_lines(lines, 10, -1) == []
    assert files_mod.read_lines(lines, 0, -1) == lines


@pytest.mark.asyncio
async def test_read_file_success(tmp_path):
    workspace_base = tmp_path / "workspace"
    workspace_base.mkdir()
    file_path = workspace_base / "file.txt"
    file_path.write_text("line1\nline2\nline3\n", encoding="utf-8")
    obs = await files_mod.read_file(
        "file.txt",
        str(workspace_base),
        str(workspace_base),
        start=1,
        end=3,
    )
    assert isinstance(obs, FileReadObservationType)
    assert obs.content == "line2\nline3\n"


@pytest.mark.asyncio
async def test_read_file_permission_error(tmp_path):
    workspace_base = tmp_path / "workspace"
    workspace_base.mkdir()
    obs = await files_mod.read_file(
        "../outside.txt",
        str(workspace_base),
        str(workspace_base),
    )
    assert isinstance(obs, ErrorObservationType)
    assert "not allowed" in obs.content


@pytest.mark.asyncio
async def test_read_file_not_found(tmp_path):
    workspace_base = tmp_path / "workspace"
    workspace_base.mkdir()
    obs = await files_mod.read_file(
        "missing.txt",
        str(workspace_base),
        str(workspace_base),
    )
    assert isinstance(obs, ErrorObservationType)
    assert "File not found" in obs.content


@pytest.mark.asyncio
async def test_read_file_unicode_error(tmp_path):
    workspace_base = tmp_path / "workspace"
    workspace_base.mkdir()
    file_path = workspace_base / "binary.dat"
    file_path.write_bytes(b"\xff\xfe")
    obs = await files_mod.read_file(
        "binary.dat",
        str(workspace_base),
        str(workspace_base),
    )
    assert isinstance(obs, ErrorObservationType)
    assert "utf-8" in obs.content


@pytest.mark.asyncio
async def test_read_file_directory_error(tmp_path, monkeypatch):
    workspace_base = tmp_path / "workspace"
    workspace_base.mkdir()
    directory = workspace_base / "folder"
    directory.mkdir()
    
    # We need to make sure resolve_path returns the directory
    monkeypatch.setattr(
        files_mod, "resolve_path", lambda path, workdir, workspace_root: directory, raising=False
    )

    def fake_open(*args, **kwargs):
        raise IsADirectoryError("directory")

    monkeypatch.setattr("builtins.open", fake_open)
    obs = await files_mod.read_file(
        "folder",
        str(workspace_base),
        str(workspace_base),
    )
    assert isinstance(obs, ErrorObservationType)
    assert "directory" in obs.content


def test_insert_lines():
    result = files_mod.insert_lines(["x", "y"], ["a\n", "b\n", "c\n"], start=1, end=2)
    assert result == ["a\n", "x\n", "y\n", "c\n"]


@pytest.mark.asyncio
async def test_write_file_new(tmp_path):
    workspace_base = tmp_path / "workspace"
    workspace_base.mkdir()
    obs = await files_mod.write_file(
        "nested/new.txt",
        str(workspace_base),
        str(workspace_base),
        "hello",
    )
    assert isinstance(obs, FileWriteObservationType)
    assert (workspace_base / "nested" / "new.txt").read_text(
        encoding="utf-8"
    ) == "hello\n"


@pytest.mark.asyncio
async def test_write_file_insert(tmp_path):
    workspace_base = tmp_path / "workspace"
    workspace_base.mkdir()
    file_path = workspace_base / "file.txt"
    file_path.parent.mkdir(parents=True, exist_ok=True)
    file_path.write_text("a\nb\nc\n", encoding="utf-8")
    obs = await files_mod.write_file(
        "file.txt",
        str(workspace_base),
        str(workspace_base),
        "x\ny",
        start=1,
        end=2,
    )
    assert isinstance(obs, FileWriteObservationType)
    assert file_path.read_text(encoding="utf-8") == "a\nx\ny\nc\n"


@pytest.mark.asyncio
async def test_write_file_permission_error(tmp_path, monkeypatch):
    workspace_base = tmp_path / "workspace"
    workspace_base.mkdir()
    monkeypatch.setattr(
        files_mod,
        "resolve_path",
        lambda *args, **kwargs: (_ for _ in ()).throw(PermissionError("denied")),
        raising=False,
    )
    obs = await files_mod.write_file(
        "file.txt",
        str(workspace_base),
        str(workspace_base),
        "content",
    )
    assert isinstance(obs, ErrorObservationType)
    assert "Permission error" in obs.content


@pytest.mark.asyncio
async def test_write_file_directory_error(tmp_path, monkeypatch):
    workspace_base = tmp_path / "workspace"
    workspace_base.mkdir(parents=True, exist_ok=True)
    directory = workspace_base / "dir"
    directory.mkdir()
    monkeypatch.setattr(
        files_mod, "resolve_path", lambda *args, **kwargs: directory, raising=False
    )

    def fake_open(*args, **kwargs):
        raise IsADirectoryError("directory")

    monkeypatch.setattr("builtins.open", fake_open)
    obs = await files_mod.write_file(
        "dir",
        str(workspace_base),
        str(workspace_base),
        "content",
    )
    assert isinstance(obs, ErrorObservationType)
    assert "directory" in obs.content


@pytest.mark.asyncio
async def test_write_file_unicode_error(tmp_path, monkeypatch):
    workspace_base = tmp_path / "workspace"
    workspace_base.mkdir()
    file_path = workspace_base / "file.txt"
    file_path.write_bytes(b"\xff\xfe")

    def fake_open(*args, **kwargs):
        raise UnicodeDecodeError("utf-8", b"", 0, 1, "error")

    monkeypatch.setattr(
        files_mod, "resolve_path", lambda *args, **kwargs: file_path, raising=False
    )
    monkeypatch.setattr("builtins.open", fake_open)
    obs = await files_mod.write_file(
        "file.txt",
        str(workspace_base),
        str(workspace_base),
        "content",
    )
    assert isinstance(obs, ErrorObservationType)
    assert "utf-8" in obs.content


@pytest.mark.asyncio
async def test_write_file_file_not_found(tmp_path, monkeypatch):
    workspace_base = tmp_path / "workspace"
    workspace_base.mkdir()

    def fake_open(*args, **kwargs):
        raise FileNotFoundError("missing")

    monkeypatch.setattr(
        files_mod,
        "resolve_path",
        lambda *args, **kwargs: workspace_base / "file.txt",
        raising=False,
    )
    monkeypatch.setattr("builtins.open", fake_open)
    obs = await files_mod.write_file(
        "file.txt",
        str(workspace_base),
        str(workspace_base),
        "content",
    )
    assert isinstance(obs, ErrorObservationType)
    assert "File not found" in obs.content
