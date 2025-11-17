"""Unit tests for conversation template routes."""

from __future__ import annotations

import json
from datetime import datetime, timedelta
from pathlib import Path
from types import SimpleNamespace

import pytest

from forge.server.routes import templates as templates_routes
from forge.storage.data_models.conversation_template import (
    ConversationTemplate,
    CreateTemplateRequest,
    TemplateCategory,
    UpdateTemplateRequest,
)


@pytest.fixture()
def temp_workspace(tmp_path, monkeypatch):
    workspace = tmp_path / "workspace"
    monkeypatch.setattr(templates_routes.config, "workspace_base", str(workspace))
    return workspace


def _write_template(base: Path, template: ConversationTemplate) -> None:
    templates_dir = base / "templates"
    templates_dir.mkdir(parents=True, exist_ok=True)
    file_path = templates_dir / f"{template.id}.json"
    file_path.write_text(
        json.dumps(template.model_dump(), default=str), encoding="utf-8"
    )


def test_get_templates_dir_creates_directory(temp_workspace):
    path = templates_routes._get_templates_dir()
    assert path.exists()
    assert path.is_dir()


def test_get_template_file(temp_workspace):
    file_path = templates_routes._get_template_file("abc")
    assert file_path.name == "abc.json"
    assert file_path.parent == temp_workspace / "templates"


def test_load_template_success(temp_workspace):
    template = ConversationTemplate(
        id="t1",
        title="Title",
        description="Desc",
        category=TemplateCategory.CUSTOM,
        prompt="Prompt",
        icon="icon",
        is_favorite=False,
        usage_count=1,
        created_at=datetime.now(),
        updated_at=datetime.now(),
    )
    _write_template(temp_workspace, template)

    loaded = templates_routes._load_template("t1")
    assert loaded == template


def test_load_template_missing_returns_none(temp_workspace):
    assert templates_routes._load_template("missing") is None


def test_load_template_handles_exception(temp_workspace, monkeypatch, caplog):
    caplog.set_level("ERROR")
    target_file = templates_routes._get_template_file("any")
    target_file.write_text("{}", encoding="utf-8")

    def fake_open(*args, **kwargs):  # pylint: disable=unused-argument
        raise ValueError("boom")

    monkeypatch.setattr("builtins.open", fake_open)
    assert templates_routes._load_template("any") is None


def test_save_template_success(temp_workspace):
    template = ConversationTemplate(
        id="t1",
        title="Title",
        description="Desc",
        category=TemplateCategory.CUSTOM,
        prompt="Prompt",
        icon="icon",
        is_favorite=True,
        usage_count=2,
        created_at=datetime.now(),
        updated_at=datetime.now(),
    )
    templates_routes._save_template(template)
    stored = templates_routes._load_template("t1")
    assert stored == template


def test_save_template_handles_exception(temp_workspace, monkeypatch):
    template = ConversationTemplate(
        id="t2",
        title="Title",
        description="Desc",
        category=TemplateCategory.CUSTOM,
        prompt="Prompt",
        icon="icon",
        is_favorite=False,
        usage_count=0,
        created_at=datetime.now(),
        updated_at=datetime.now(),
    )

    def fake_open(*args, **kwargs):  # pylint: disable=unused-argument
        raise OSError("fail")

    monkeypatch.setattr("builtins.open", fake_open)

    with pytest.raises(templates_routes.HTTPException) as exc:
        templates_routes._save_template(template)
    assert exc.value.status_code == 500


def test_load_all_templates_filters_bad_files(temp_workspace, caplog):
    caplog.set_level("ERROR")
    valid = ConversationTemplate(
        id="good",
        title="Title",
        description="Desc",
        category=TemplateCategory.CUSTOM,
        prompt="Prompt",
        icon="icon",
        is_favorite=False,
        usage_count=0,
        created_at=datetime.now(),
        updated_at=datetime.now(),
    )
    _write_template(temp_workspace, valid)
    bad_path = templates_routes._get_templates_dir() / "bad.json"
    bad_path.write_text("not json", encoding="utf-8")

    loaded = templates_routes._load_all_templates()
    assert [t.id for t in loaded] == ["good"]


@pytest.mark.asyncio
async def test_list_templates_filters_and_sorts(temp_workspace):
    now = datetime.now()
    older = now - timedelta(days=1)
    templates = [
        ConversationTemplate(
            id="fav",
            title="Fav",
            description="",
            category=TemplateCategory.CUSTOM,
            prompt="",
            icon="",
            is_favorite=True,
            usage_count=1,
            created_at=older,
            updated_at=older,
        ),
        ConversationTemplate(
            id="sec",
            title="Sec",
            description="",
            category=TemplateCategory.DOCUMENT,
            prompt="",
            icon="",
            is_favorite=False,
            usage_count=0,
            created_at=now,
            updated_at=now,
        ),
    ]
    for tpl in templates:
        _write_template(temp_workspace, tpl)

    all_templates = await templates_routes.list_templates()
    assert [t.id for t in all_templates] == ["sec", "fav"]

    filtered = await templates_routes.list_templates(category=TemplateCategory.DOCUMENT)
    assert len(filtered) == 1 and filtered[0].id == "sec"

    favorites = await templates_routes.list_templates(is_favorite=True)
    assert len(favorites) == 1 and favorites[0].id == "fav"


@pytest.mark.asyncio
async def test_create_template_success(temp_workspace, monkeypatch):
    monkeypatch.setattr(templates_routes, "uuid4", lambda: "id-123")
    created = await templates_routes.create_template(
        CreateTemplateRequest(
            title="Title",
            description="Desc",
            category=TemplateCategory.CUSTOM,
            prompt="Prompt",
            icon="icon",
            is_favorite=True,
        ),
    )
    assert created.id == "id-123"
    stored = templates_routes._load_template("id-123")
    assert stored is not None and stored.prompt == "Prompt"


@pytest.mark.asyncio
async def test_get_template_found_and_missing(temp_workspace):
    template = ConversationTemplate(
        id="found",
        title="Title",
        description="Desc",
        category=TemplateCategory.CUSTOM,
        prompt="Prompt",
        icon="icon",
        is_favorite=False,
        usage_count=0,
        created_at=datetime.now(),
        updated_at=datetime.now(),
    )
    _write_template(temp_workspace, template)

    result = await templates_routes.get_template("found")
    assert result.id == "found"

    with pytest.raises(templates_routes.HTTPException) as exc:
        await templates_routes.get_template("missing")
    assert exc.value.status_code == 404


@pytest.mark.asyncio
async def test_update_template_success(temp_workspace):
    template = ConversationTemplate(
        id="upd",
        title="Old",
        description="Old",
        category=TemplateCategory.CUSTOM,
        prompt="Old",
        icon="old",
        is_favorite=False,
        usage_count=0,
        created_at=datetime.now(),
        updated_at=datetime.now(),
    )
    _write_template(temp_workspace, template)

    updated = await templates_routes.update_template(
        "upd",
        UpdateTemplateRequest(
            title="New",
            description="New",
            category=TemplateCategory.DEBUG,
            prompt="New",
            icon="new",
            is_favorite=True,
        ),
    )
    assert updated.title == "New"
    assert updated.category == TemplateCategory.DEBUG
    assert updated.is_favorite is True
    assert updated.updated_at >= template.updated_at


@pytest.mark.asyncio
async def test_update_template_not_found(temp_workspace):
    with pytest.raises(templates_routes.HTTPException) as exc:
        await templates_routes.update_template("missing", UpdateTemplateRequest())
    assert exc.value.status_code == 404


@pytest.mark.asyncio
async def test_delete_template_success_and_missing(temp_workspace):
    template = ConversationTemplate(
        id="del",
        title="Title",
        description="Desc",
        category=TemplateCategory.CUSTOM,
        prompt="Prompt",
        icon="icon",
        is_favorite=False,
        usage_count=0,
        created_at=datetime.now(),
        updated_at=datetime.now(),
    )
    _write_template(temp_workspace, template)

    await templates_routes.delete_template("del")
    assert not (templates_routes._get_templates_dir() / "del.json").exists()

    with pytest.raises(templates_routes.HTTPException) as exc:
        await templates_routes.delete_template("missing")
    assert exc.value.status_code == 404


@pytest.mark.asyncio
async def test_track_template_usage(temp_workspace):
    template = ConversationTemplate(
        id="use",
        title="Title",
        description="Desc",
        category=TemplateCategory.CUSTOM,
        prompt="Prompt",
        icon="icon",
        is_favorite=False,
        usage_count=5,
        created_at=datetime.now(),
        updated_at=datetime.now(),
    )
    _write_template(temp_workspace, template)

    updated = await templates_routes.track_template_usage("use")
    assert updated.usage_count == 6

    with pytest.raises(templates_routes.HTTPException) as exc:
        await templates_routes.track_template_usage("missing")
    assert exc.value.status_code == 404
