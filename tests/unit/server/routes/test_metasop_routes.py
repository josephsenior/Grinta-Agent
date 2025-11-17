"""Unit tests for MetaSOP routes and helpers."""

from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest

from fastapi import HTTPException

from forge.server.routes import metasop as metasop_routes


@pytest.fixture
def logs_dir(tmp_path, monkeypatch):
    logs = tmp_path / "logs"
    logs.mkdir()
    monkeypatch.setattr(metasop_routes, "Path", lambda p: tmp_path / p)
    return logs


def _write_metasop_file(logs_dir: Path, payload: dict[str, Any]) -> Path:
    last_run_file = logs_dir / "metasop_last_run.json"
    last_run_file.write_text(json.dumps(payload), encoding="utf-8")
    return last_run_file


@pytest.mark.asyncio
async def test_get_orchestration_data_not_found(monkeypatch, tmp_path):
    monkeypatch.setattr(metasop_routes, "Path", lambda p: tmp_path / p)
    response = await metasop_routes.get_orchestration_data("cid-123")
    data = json.loads(response.body)
    assert data["status"] == "not_found"


@pytest.mark.asyncio
async def test_get_orchestration_data_success(logs_dir):
    payload: dict[str, Any] = {
        "ok": True,
        "summary": "Successful run",
        "artifacts": {"step1": {"content": {}}},
        "report": {
            "events": [
                {
                    "step_id": "pm_spec",
                    "role": "PM",
                    "status": "executed",
                    "retries": 1,
                },
                {"step_id": "eng_impl", "role": "Engineer", "status": "failed"},
            ],
        },
    }
    _write_metasop_file(logs_dir, payload)

    response = await metasop_routes.get_orchestration_data("cid")
    data = json.loads(response.body)
    assert data["status"] == "success"
    assert "graph TD" in data["diagram"]
    assert "Engineer" in data["diagram"]


@pytest.mark.asyncio
async def test_get_orchestration_data_error(monkeypatch, logs_dir):
    last_run_file = logs_dir / "metasop_last_run.json"
    last_run_file.write_text("{invalid json", encoding="utf-8")

    with pytest.raises(HTTPException) as exc:
        await metasop_routes.get_orchestration_data("cid")
    assert exc.value.status_code == 500


def test_generate_mermaid_diagram_with_events():
    diagram = metasop_routes._generate_mermaid_diagram(
        {
            "events": [
                {"step_id": "a", "role": "PM", "status": "executed", "retries": 2},
                {"step_id": "b", "role": "Arch", "status": "skipped"},
                {"step_id": "c", "role": "Eng", "status": "unknown"},
            ]
        },
        {},
    )
    assert "classDef executed" in diagram
    assert "classDef skipped" in diagram
    assert "node0" in diagram and "node1" in diagram and "node2" in diagram


def test_generate_mermaid_diagram_no_events():
    diagram = metasop_routes._generate_mermaid_diagram({}, {})
    assert "MetaSOP" in diagram


def test_generate_mermaid_diagram_error(monkeypatch):
    monkeypatch.setattr(
        metasop_routes,
        "_get_node_style_class",
        lambda status: (_ for _ in ()).throw(RuntimeError()),
    )
    diagram = metasop_routes._generate_mermaid_diagram(
        {"events": [{"status": "executed"}]}, {}
    )
    assert "MetaSOP" in diagram


def test_get_node_style_class_unknown():
    assert metasop_routes._get_node_style_class("executed") == "executed"
    assert metasop_routes._get_node_style_class("custom") == "pending"


def test_generate_default_diagram():
    assert "graph TD" in metasop_routes._generate_default_diagram()


@pytest.mark.asyncio
async def test_get_step_artifact_success(logs_dir):
    payload: dict[str, Any] = {"artifacts": {"step1": {"content": "artifact"}}}
    _write_metasop_file(logs_dir, payload)

    response = await metasop_routes.get_step_artifact("cid", "step1")
    data = json.loads(response.body)
    assert data["artifact"] == {"content": "artifact"}


@pytest.mark.asyncio
async def test_get_step_artifact_no_file(monkeypatch, tmp_path):
    monkeypatch.setattr(metasop_routes, "Path", lambda p: tmp_path / p)
    with pytest.raises(HTTPException) as exc:
        await metasop_routes.get_step_artifact("cid", "step1")
    assert exc.value.status_code == 404


@pytest.mark.asyncio
async def test_get_step_artifact_missing_step(logs_dir):
    payload: dict[str, Any] = {"artifacts": {}}
    _write_metasop_file(logs_dir, payload)
    with pytest.raises(HTTPException) as exc:
        await metasop_routes.get_step_artifact("cid", "missing")
    assert exc.value.status_code == 404


@pytest.mark.asyncio
async def test_get_step_artifact_internal_error(monkeypatch, logs_dir):
    payload: dict[str, Any] = {"artifacts": {"step1": {}}}
    _write_metasop_file(logs_dir, payload)

    monkeypatch.setattr(
        metasop_routes.json,
        "loads",
        lambda *_: (_ for _ in ()).throw(ValueError("bad json")),
    )
    with pytest.raises(HTTPException) as exc:
        await metasop_routes.get_step_artifact("cid", "step1")
    assert exc.value.status_code == 500


@pytest.mark.asyncio
async def test_pass_to_codeact_success(logs_dir):
    artifacts: dict[str, Any] = {
        "pm_spec": {"content": {"user_stories": "Story"}},
        "arch_design": {"content": {"architecture": "Microservices"}},
        "engineer_impl": {
            "content": {
                "file_structure": {"name": "src", "type": "folder", "children": []},
                "implementation_plan": "Plan",
                "dependencies": ["pytest"],
                "run_results": {"setup_commands": ["npm install"]},
            }
        },
        "ui_design": {"content": {"component_hierarchy": "App"}},
    }
    payload: dict[str, Any] = {"artifacts": artifacts}
    _write_metasop_file(logs_dir, payload)

    response = await metasop_routes.pass_to_codeact(
        metasop_routes.PassToCodeActRequest(
            conversation_id="cid", user_request="Build", repo_root="/repo"
        )
    )
    data = json.loads(response.body)
    assert data["success"] is True
    assert "Implementation" in data["prompt"]
    assert data["artifacts_count"] == len(artifacts)


@pytest.mark.asyncio
async def test_pass_to_codeact_no_file(monkeypatch, tmp_path):
    monkeypatch.setattr(metasop_routes, "Path", lambda p: tmp_path / p)
    with pytest.raises(HTTPException) as exc:
        await metasop_routes.pass_to_codeact(
            metasop_routes.PassToCodeActRequest(
                conversation_id="cid", user_request="Do"
            )
        )
    assert exc.value.status_code == 404


@pytest.mark.asyncio
async def test_pass_to_codeact_no_artifacts(logs_dir):
    payload: dict[str, Any] = {"artifacts": {}}
    _write_metasop_file(logs_dir, payload)
    with pytest.raises(HTTPException) as exc:
        await metasop_routes.pass_to_codeact(
            metasop_routes.PassToCodeActRequest(
                conversation_id="cid", user_request="Do"
            )
        )
    assert exc.value.status_code == 400


@pytest.mark.asyncio
async def test_pass_to_codeact_internal_error(monkeypatch, logs_dir):
    payload: dict[str, Any] = {"artifacts": {"pm_spec": {}}}
    _write_metasop_file(logs_dir, payload)
    monkeypatch.setattr(
        metasop_routes,
        "_format_artifacts_for_codeact",
        lambda *args, **kwargs: (_ for _ in ()).throw(RuntimeError("fail")),
    )
    with pytest.raises(HTTPException) as exc:
        await metasop_routes.pass_to_codeact(
            metasop_routes.PassToCodeActRequest(
                conversation_id="cid", user_request="Do"
            )
        )
    assert exc.value.status_code == 500


def test_format_pm_artifact():
    lines = metasop_routes._format_pm_artifact({"content": {"user_stories": ["story"]}})
    assert "Product Manager" in "\n".join(lines)


def test_format_arch_artifact():
    artifact = {
        "content": {
            "architecture": "Layered",
            "technical_decisions": [{"decision": "DB", "rationale": "Scale"}],
        }
    }
    lines = metasop_routes._format_arch_artifact(artifact)
    assert any("Layered" in line for line in lines)


def test_format_engineer_artifact():
    artifact = {
        "content": {
            "file_structure": {
                "name": "src",
                "type": "folder",
                "children": [{"name": "app.py"}],
            },
            "implementation_plan": "Plan",
            "dependencies": ["pytest"],
            "technical_decisions": [{"decision": "API", "rationale": "REST"}],
            "run_results": {"setup_commands": ["pip install -r requirements.txt"]},
        }
    }
    lines = metasop_routes._format_engineer_artifact(artifact)
    joined = "\n".join(lines)
    assert "File Structure" in joined
    assert "pip install" in joined


def test_format_ui_artifact():
    lines = metasop_routes._format_ui_artifact(
        {"content": {"component_hierarchy": "App"}}
    )
    assert any("UI Designer" in line for line in lines)


def test_format_run_commands():
    lines = metasop_routes._format_run_commands(
        {
            "setup_commands": ["npm install"],
            "test_commands": [],
            "dev_commands": ["npm run dev"],
        }
    )
    joined = "\n".join(lines)
    assert "npm install" in joined and "npm run dev" in joined


def test_format_final_instructions_with_repo():
    lines = metasop_routes._format_final_instructions("/repo")
    assert any("Working Directory" in line for line in lines)


def test_format_artifacts_for_codeact_full():
    artifacts = {
        "pm_spec": {"content": {"user_stories": "Story"}},
        "arch_design": {"content": {"architecture": "Layered"}},
        "engineer_impl": {"content": {}},
        "ui_design": {"content": {"component_hierarchy": "App"}},
    }
    prompt = metasop_routes._format_artifacts_for_codeact(
        artifacts, "Do work", repo_root="/repo"
    )
    assert "Original Request" in prompt
    assert "Layered" in prompt


def test_format_file_tree_variants():
    tree = {
        "name": "src",
        "type": "folder",
        "description": "Main source",
        "children": [
            {"name": "app.py"},
            {"root": {"name": "nested", "children": []}},
        ],
    }
    text = metasop_routes._format_file_tree(tree)
    assert "src" in text and "app.py" in text
    assert metasop_routes._format_file_tree([tree]).count("src") >= 1
    assert "No files" in metasop_routes._format_file_tree(None)
