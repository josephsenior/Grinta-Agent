"""Unit tests for global export/import routes."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from fastapi import HTTPException, status
from fastapi.responses import JSONResponse

from forge.server.routes import global_export as export_routes


@pytest.fixture
def temp_workspace(tmp_path, monkeypatch):
    monkeypatch.setattr(export_routes.config, "workspace_base", str(tmp_path))
    return tmp_path


def test_load_json_files_reads_all(temp_workspace):
    data_dir = temp_workspace / "memories"
    data_dir.mkdir(parents=True, exist_ok=True)
    (data_dir / "a.json").write_text(json.dumps({"id": "a"}), encoding="utf-8")
    (data_dir / "b.json").write_text(json.dumps({"id": "b"}), encoding="utf-8")

    result = export_routes._load_json_files("memories")
    assert len(result) == 2
    assert {entry["id"] for entry in result} == {"a", "b"}


def test_load_json_files_missing_directory(temp_workspace):
    assert export_routes._load_json_files("does-not-exist") == []


def test_load_json_files_logs_error(temp_workspace, monkeypatch):
    data_dir = temp_workspace / "prompts"
    data_dir.mkdir(parents=True, exist_ok=True)
    (data_dir / "bad.json").write_text("not json", encoding="utf-8")

    result = export_routes._load_json_files("prompts")
    assert result == []


def test_save_json_files_creates_and_updates(temp_workspace):
    data_dir = temp_workspace / "snippets"
    data_dir.mkdir(parents=True, exist_ok=True)
    existing = data_dir / "existing.json"
    existing.write_text(json.dumps({"id": "existing"}), encoding="utf-8")

    imported, updated = export_routes._save_json_files(
        "snippets",
        [
            {"id": "new", "content": 1},
            {"id": "existing", "content": 2},
            {"content": 3},
        ],
    )
    assert imported == 1
    assert updated == 1
    assert (
        json.loads((data_dir / "existing.json").read_text(encoding="utf-8"))["content"]
        == 2
    )


def test_save_json_files_logs_error(temp_workspace, monkeypatch):
    def fake_dump(*args, **kwargs):
        raise RuntimeError("fail")

    monkeypatch.setattr(export_routes.json, "dump", fake_dump)

    imported, updated = export_routes._save_json_files("templates", [{"id": "x"}])
    assert imported == 0 and updated == 0


@pytest.mark.asyncio
async def test_export_all_data_success(monkeypatch):
    async def fake_load(directory):
        return [
            {"id": f"{directory}-1"},
            {"id": f"{directory}-2"},
        ]

    monkeypatch.setattr(export_routes, "_load_json_files", lambda d: [{"id": f"{d}-1"}])
    response = await export_routes.export_all_data()
    assert isinstance(response, JSONResponse)
    assert response.status_code == status.HTTP_200_OK
    payload = json.loads(response.body)
    assert payload["memories"] == [{"id": "memories-1"}]
    assert "Content-Disposition" in response.headers


@pytest.mark.asyncio
async def test_export_all_data_handles_exception(monkeypatch):
    def failing_load(directory):
        raise RuntimeError("boom")

    monkeypatch.setattr(export_routes, "_load_json_files", failing_load)
    with pytest.raises(HTTPException) as exc:
        await export_routes.export_all_data()
    assert exc.value.status_code == 500


@pytest.mark.asyncio
async def test_import_all_data_success(monkeypatch):
    call_log = {}

    def fake_save(directory, data):
        call_log[directory] = len(data)
        return (1, 2)

    monkeypatch.setattr(export_routes, "_save_json_files", fake_save)
    payload = export_routes.GlobalExportData(
        version="1.0.0",
        memories=[{"id": "m"}],
        prompts=[{"id": "p"}],
        snippets=[{"id": "s"}],
        templates=[{"id": "t"}],
    )

    result = await export_routes.import_all_data(payload)
    assert call_log == {
        "memories": 1,
        "prompts": 1,
        "snippets": 1,
        "templates": 1,
    }
    assert result["memories"] == {"imported": 1, "updated": 2}


@pytest.mark.asyncio
async def test_import_all_data_handles_exception(monkeypatch):
    def failing_save(directory, data):
        raise RuntimeError("error")

    monkeypatch.setattr(export_routes, "_save_json_files", failing_save)
    payload = export_routes.GlobalExportData(version="1.0.0", memories=[{"id": "m"}])

    with pytest.raises(HTTPException) as exc:
        await export_routes.import_all_data(payload)
    assert exc.value.status_code == 500
