import asyncio
import io
import json
import os
import sys
import tempfile
from pathlib import Path
from types import SimpleNamespace
from typing import Any, cast

import httpx
import pytest
from fastapi import HTTPException, UploadFile
from fastapi.responses import FileResponse, JSONResponse

from forge.core.exceptions import AgentRuntimeUnavailableError
from forge.events.action import FileReadAction
from forge.events.action.files import FileWriteAction
from forge.events.observation import ErrorObservation, FileReadObservation
from forge.server.routes import files as files_routes


class DummyRuntime:
    def __init__(self, list_result=None, config_path="/workspace"):
        self.list_result = list_result or []
        self.config = SimpleNamespace(workspace_mount_path_in_sandbox=config_path)
        self.run_action_calls: list[Any] = []
        self.run_action_result: Any = None
        self.run_action_error: Exception | None = None
        self.copy_from_calls: list[str] = []
        self.copy_from_return: Path = Path(config_path)
        self.copy_from_error: Exception | None = None
        self.git_diff_calls: list[tuple[str, str]] = []

    def list_files(self, path=None):
        if isinstance(self.list_result, Exception):
            raise self.list_result
        return self.list_result

    def copy_from(self, path):
        if self.copy_from_error:
            raise self.copy_from_error
        self.copy_from_calls.append(path)
        return self.copy_from_return

    def get_git_diff(self, path, cwd):
        if isinstance(self.git_diff_calls, Exception):
            raise self.git_diff_calls
        self.git_diff_calls.append((path, cwd))
        return {"path": path, "cwd": cwd}

    def run_action(self, action):
        self.run_action_calls.append(action)
        if self.run_action_error:
            raise self.run_action_error
        return self.run_action_result


def make_conversation(runtime=None):
    return SimpleNamespace(runtime=runtime)


def test_sanitize_file_path_valid():
    assert files_routes._sanitize_file_path("foo/bar.txt") == "foo/bar.txt"


@pytest.mark.parametrize("path", ["", "../../etc/passwd", "../secret", "/abs/path"])
def test_sanitize_file_path_invalid(path):
    with pytest.raises(ValueError):
        files_routes._sanitize_file_path(path)


@pytest.mark.asyncio
async def test_list_files_no_runtime():
    result = await files_routes.list_files(
        path=None, conversation=make_conversation(runtime=None)
    )
    assert result == []


@pytest.mark.asyncio
async def test_list_files_success(monkeypatch):
    runtime = DummyRuntime(list_result=["file1.txt"])
    monkeypatch.setattr(files_routes, "FILES_TO_IGNORE", {"system32"})

    async def fake_call(func, *args, **kwargs):
        return func(*args, **kwargs)

    monkeypatch.setattr(files_routes, "call_sync_from_async", fake_call)

    result = await files_routes.list_files(
        path="sub", conversation=make_conversation(runtime)
    )
    assert result == [os.path.join("sub", "file1.txt")]


@pytest.mark.asyncio
async def test_list_files_runtime_unavailable(monkeypatch):
    runtime = DummyRuntime(list_result=httpx.ConnectError("boom"))

    async def fake_call(func, *args, **kwargs):
        error = runtime.list_result
        assert isinstance(error, Exception)
        raise error

    monkeypatch.setattr(files_routes, "call_sync_from_async", fake_call)
    response = await files_routes.list_files(
        path=None, conversation=make_conversation(runtime)
    )
    assert isinstance(response, JSONResponse)
    assert response.status_code == 503


@pytest.mark.asyncio
async def test_list_files_agent_error(monkeypatch):
    runtime = DummyRuntime(list_result=AgentRuntimeUnavailableError("down"))

    async def fake_call(func, *args, **kwargs):
        error = runtime.list_result
        assert isinstance(error, Exception)
        raise error

    monkeypatch.setattr(files_routes, "call_sync_from_async", fake_call)
    response = await files_routes.list_files(
        path=None, conversation=make_conversation(runtime)
    )
    assert isinstance(response, JSONResponse)
    assert response.status_code == 500


@pytest.mark.asyncio
async def test_select_file_invalid_path():
    response = await files_routes.select_file(
        file="../bad", conversation=make_conversation(runtime=None)
    )
    assert isinstance(response, JSONResponse)
    assert response.status_code == 400


@pytest.mark.asyncio
async def test_select_file_runtime_not_ready():
    response = await files_routes.select_file(
        file="valid.txt", conversation=make_conversation(runtime=None)
    )
    assert isinstance(response, JSONResponse)
    assert response.status_code == 503


@pytest.mark.asyncio
async def test_select_file_success(monkeypatch):
    runtime = DummyRuntime()
    runtime.run_action_result = FileReadObservation(
        path="/workspace/file.txt", content="hello"
    )

    async def fake_call(func, *args, **kwargs):
        return func(*args, **kwargs)

    monkeypatch.setattr(files_routes, "call_sync_from_async", fake_call)

    response = await files_routes.select_file(
        file="file.txt", conversation=make_conversation(runtime)
    )
    assert isinstance(response, JSONResponse)
    assert response.status_code == 200
    assert json.loads(response.body)["code"] == "hello"
    assert isinstance(runtime.run_action_calls[0], FileReadAction)


@pytest.mark.asyncio
async def test_select_file_binary_error(monkeypatch):
    runtime = DummyRuntime()
    runtime.run_action_result = ErrorObservation(content="ERROR_BINARY_FILE")

    async def fake_call(func, *args, **kwargs):
        return func(*args, **kwargs)

    monkeypatch.setattr(files_routes, "call_sync_from_async", fake_call)
    response = await files_routes.select_file(
        file="file.txt", conversation=make_conversation(runtime)
    )
    assert isinstance(response, JSONResponse)
    assert response.status_code == 415


@pytest.mark.asyncio
async def test_select_file_agent_error(monkeypatch):
    runtime = DummyRuntime()
    runtime.run_action_error = AgentRuntimeUnavailableError("down")

    async def fake_call(func, *args, **kwargs):
        raise runtime.run_action_result

    monkeypatch.setattr(files_routes, "call_sync_from_async", fake_call)
    response = await files_routes.select_file("file.txt", make_conversation(runtime))
    assert isinstance(response, JSONResponse)
    assert response.status_code == 500


@pytest.mark.asyncio
async def test_select_file_unexpected(monkeypatch):
    runtime = DummyRuntime()
    runtime.run_action_result = object()

    async def fake_call(func, *args, **kwargs):
        return func(*args, **kwargs)

    monkeypatch.setattr(files_routes, "call_sync_from_async", fake_call)
    response = await files_routes.select_file("file.txt", make_conversation(runtime))
    assert isinstance(response, JSONResponse)
    assert response.status_code == 500


def test_zip_current_workspace_success(monkeypatch, tmp_path):
    tmp_file = tmp_path / "workspace.zip"
    tmp_file.write_text("zip")
    runtime = DummyRuntime()
    runtime.copy_from_return = tmp_file

    response = files_routes.zip_current_workspace(make_conversation(runtime))
    assert isinstance(response, FileResponse)
    assert runtime.copy_from_calls == [runtime.config.workspace_mount_path_in_sandbox]


def test_zip_current_workspace_agent_error():
    runtime = DummyRuntime()
    runtime.copy_from_error = AgentRuntimeUnavailableError("down")
    response = files_routes.zip_current_workspace(make_conversation(runtime))
    assert isinstance(response, JSONResponse)
    assert response.status_code == 500


def test_zip_current_workspace_general_error():
    with pytest.raises(HTTPException):
        files_routes.zip_current_workspace(make_conversation(runtime=None))


@pytest.mark.asyncio
async def test_git_changes_success(monkeypatch, tmp_path):
    workspace = tmp_path
    runtime = DummyRuntime(config_path=str(workspace))
    conversation = SimpleNamespace(runtime=runtime)

    async def attach(conv_id, user):
        return conversation

    async def detach(conv):
        return None

    async def fake_call(func, *args):
        return [{"path": "file"}]

    monkeypatch.setattr(files_routes, "call_sync_from_async", fake_call)
    monkeypatch.setitem(
        sys.modules,
        "forge.server.shared",
        SimpleNamespace(
            conversation_manager=SimpleNamespace(
                attach_to_conversation=attach, detach_from_conversation=detach
            )
        ),
    )

    result = await files_routes.git_changes("conv")
    assert result == [{"path": "file"}]


@pytest.mark.asyncio
async def test_git_changes_workspace_missing(monkeypatch, tmp_path):
    runtime = DummyRuntime(config_path=str(tmp_path / "missing"))
    conversation = SimpleNamespace(runtime=runtime)

    async def attach(conv_id, user):
        return conversation

    async def detach(conv):
        return None

    monkeypatch.setitem(
        sys.modules,
        "forge.server.shared",
        SimpleNamespace(
            conversation_manager=SimpleNamespace(
                attach_to_conversation=attach, detach_from_conversation=detach
            )
        ),
    )
    response = await files_routes.git_changes("conv")
    assert isinstance(response, JSONResponse)
    assert response.status_code == 200
    assert json.loads(response.body) == []


@pytest.mark.asyncio
async def test_git_changes_not_repo(monkeypatch, tmp_path):
    workspace = tmp_path
    runtime = DummyRuntime(config_path=str(workspace))
    conversation = SimpleNamespace(runtime=runtime)

    async def attach(conv_id, user):
        return conversation

    async def detach(conv):
        return None

    async def fake_call(func, cwd):
        return None

    monkeypatch.setattr(files_routes, "call_sync_from_async", fake_call)
    monkeypatch.setitem(
        sys.modules,
        "forge.server.shared",
        SimpleNamespace(
            conversation_manager=SimpleNamespace(
                attach_to_conversation=attach, detach_from_conversation=detach
            )
        ),
    )

    response = await files_routes.git_changes("conv")
    assert isinstance(response, JSONResponse)
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_git_changes_git_missing(monkeypatch, tmp_path):
    workspace = tmp_path
    runtime = DummyRuntime(config_path=str(workspace))
    conversation = SimpleNamespace(runtime=runtime)

    async def attach(conv_id, user):
        return conversation

    async def detach(conv):
        return None

    async def fake_call(func, cwd):
        raise FileNotFoundError("git not found")

    monkeypatch.setattr(files_routes, "call_sync_from_async", fake_call)
    monkeypatch.setitem(
        sys.modules,
        "forge.server.shared",
        SimpleNamespace(
            conversation_manager=SimpleNamespace(
                attach_to_conversation=attach, detach_from_conversation=detach
            )
        ),
    )

    response = await files_routes.git_changes("conv")
    assert isinstance(response, JSONResponse)
    assert response.status_code == 200


@pytest.mark.asyncio
async def test_git_changes_runtime_unavailable(monkeypatch, tmp_path):
    runtime = DummyRuntime(config_path=str(tmp_path))
    conversation = SimpleNamespace(runtime=runtime)

    async def attach(conv_id, user):
        raise AgentRuntimeUnavailableError("down")

    monkeypatch.setitem(
        sys.modules,
        "forge.server.shared",
        SimpleNamespace(
            conversation_manager=SimpleNamespace(attach_to_conversation=attach)
        ),
    )
    response = await files_routes.git_changes("conv")
    assert isinstance(response, JSONResponse)
    assert response.status_code == 500


@pytest.mark.asyncio
async def test_git_changes_general_error(monkeypatch, tmp_path):
    runtime = DummyRuntime(config_path=str(tmp_path))
    conversation = SimpleNamespace(runtime=runtime)

    async def attach(conv_id, user):
        return conversation

    async def detach(conv):
        raise RuntimeError("boom")

    async def fake_call(func, cwd):
        raise RuntimeError("boom")

    monkeypatch.setattr(files_routes, "call_sync_from_async", fake_call)
    monkeypatch.setitem(
        sys.modules,
        "forge.server.shared",
        SimpleNamespace(
            conversation_manager=SimpleNamespace(
                attach_to_conversation=attach, detach_from_conversation=detach
            )
        ),
    )
    response = await files_routes.git_changes("conv")
    assert isinstance(response, JSONResponse)
    assert response.status_code == 500


@pytest.mark.asyncio
async def test_git_diff_invalid_path():
    response = await files_routes.git_diff(
        path="", conversation_store=None, conversation=make_conversation(DummyRuntime())
    )
    assert isinstance(response, JSONResponse)
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_git_diff_sanitization_error():
    response = await files_routes.git_diff(
        path="../bad",
        conversation_store=None,
        conversation=make_conversation(DummyRuntime()),
    )
    assert isinstance(response, JSONResponse)
    assert response.status_code == 400


@pytest.mark.asyncio
async def test_git_diff_success(monkeypatch):
    runtime = DummyRuntime()
    runtime.git_diff_calls = []

    async def fake_call(func, *args):
        return func(*args)

    monkeypatch.setattr(files_routes, "call_sync_from_async", fake_call)
    response = await files_routes.git_diff(
        path="file.txt",
        conversation_store=None,
        conversation=make_conversation(runtime),
    )
    assert response == {
        "path": "file.txt",
        "cwd": runtime.config.workspace_mount_path_in_sandbox,
    }


@pytest.mark.asyncio
async def test_git_diff_agent_error(monkeypatch):
    runtime = DummyRuntime()

    async def fake_call(func, *args, **kwargs):
        raise AgentRuntimeUnavailableError("down")

    monkeypatch.setattr(files_routes, "call_sync_from_async", fake_call)
    response = await files_routes.git_diff(
        path="file.txt",
        conversation_store=None,
        conversation=make_conversation(runtime),
    )
    assert isinstance(response, JSONResponse)
    assert response.status_code == 500


@pytest.mark.asyncio
async def test_upload_files_success(monkeypatch):
    runtime = DummyRuntime()
    runtime.config.workspace_mount_path_in_sandbox = "/workspace"
    runtime.run_action_result = None

    async def fake_call(func, *args, **kwargs):
        return func(*args, **kwargs)

    monkeypatch.setattr(files_routes, "call_sync_from_async", fake_call)

    upload = UploadFile(filename="valid.txt", file=io.BytesIO(b"content"))

    response = await files_routes.upload_files([upload], make_conversation(runtime))
    assert isinstance(response, JSONResponse)
    assert response.status_code == 200
    body = json.loads(response.body)
    assert body["uploaded_files"] == [os.path.join("/workspace", "valid.txt")]
    assert isinstance(runtime.run_action_calls[0], FileWriteAction)


@pytest.mark.asyncio
async def test_upload_files_invalid_filename(monkeypatch):
    runtime = DummyRuntime()
    upload = UploadFile(filename="../bad", file=io.BytesIO(b"content"))
    response = await files_routes.upload_files([upload], make_conversation(runtime))
    assert isinstance(response, JSONResponse)
    assert response.status_code == 200
    body = json.loads(response.body)
    assert body["skipped_files"][0]["name"] == "../bad"
