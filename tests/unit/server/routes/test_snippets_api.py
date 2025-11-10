"""Unit tests for snippets routes covering helpers and API endpoints."""

import json
import os
from datetime import datetime, timedelta
from types import SimpleNamespace

import pytest
from fastapi import HTTPException

from forge.server.routes import snippets as snippets_routes
from forge.server.shared import config
from forge.storage.data_models.code_snippet import (
    CodeSnippet,
    CreateSnippetRequest,
    SearchSnippetsRequest,
    SnippetCategory,
    SnippetCollection,
    SnippetLanguage,
    UpdateSnippetRequest,
)
from forge.server.routes.snippets import SnippetUsageEvent


@pytest.fixture
def snippets_workspace(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "workspace_base", str(tmp_path))
    monkeypatch.setattr(snippets_routes.AppConfig, "workspace_base", str(tmp_path))
    return tmp_path


def make_snippet(snippet_id="s1", **overrides) -> CodeSnippet:
    base = dict(
        id=snippet_id,
        title="Snippet",
        description="Test snippet",
        language=SnippetLanguage.PYTHON,
        category=SnippetCategory.UTILITY,
        code="print('hi')",
        tags=["tag1", "tag2"],
        is_favorite=True,
        usage_count=3,
        created_at=datetime.now() - timedelta(days=1),
        updated_at=datetime.now(),
        dependencies=["dep"],
        source_url="http://example.com",
        license="MIT",
    )
    base.update(overrides)
    return CodeSnippet(**base)


def test_get_snippets_dir(snippets_workspace):
    path = snippets_routes._get_snippets_dir()
    assert path.exists()
    assert path.parent == snippets_workspace


def test_save_and_load_snippet(snippets_workspace):
    snippet = make_snippet()
    snippets_routes._save_snippet(snippet)
    loaded = snippets_routes._load_snippet(snippet.id)
    assert loaded and loaded.title == snippet.title


def test_save_snippet_error(monkeypatch):
    snippet = make_snippet()

    def bad_path(_):
        raise RuntimeError("boom")

    monkeypatch.setattr(snippets_routes, "_get_snippet_file_path", bad_path)
    with pytest.raises(HTTPException):
        snippets_routes._save_snippet(snippet)


def test_load_snippet_missing(snippets_workspace):
    assert snippets_routes._load_snippet("missing") is None


def test_load_snippet_error(monkeypatch):
    monkeypatch.setattr(snippets_routes, "_get_snippet_file_path", lambda _: 1 / 0)
    assert snippets_routes._load_snippet("bad") is None


def test_delete_snippet_file(snippets_workspace):
    snippet = make_snippet("deltest")
    snippets_routes._save_snippet(snippet)
    snippets_routes._delete_snippet_file(snippet.id)
    assert snippets_routes._load_snippet(snippet.id) is None


def test_delete_snippet_file_error(monkeypatch):
    monkeypatch.setattr(snippets_routes, "_get_snippet_file_path", lambda _: 1 / 0)
    with pytest.raises(HTTPException):
        snippets_routes._delete_snippet_file("bad")


def test_load_all_snippets_skips_invalid(snippets_workspace):
    valid = make_snippet("valid")
    snippets_routes._save_snippet(valid)
    invalid_file = snippets_routes._get_snippets_dir() / "bad.json"
    invalid_file.write_text("not-json")
    snippets = snippets_routes._load_all_snippets()
    assert any(s.id == "valid" for s in snippets)


def test_usage_events_roundtrip(snippets_workspace):
    events = [{"id": 1}]
    snippets_routes._save_usage_events(events)
    assert snippets_routes._load_usage_events() == events


def test_usage_events_invalid(snippets_workspace):
    path = snippets_routes._get_usage_events_path()
    path.write_text(json.dumps(["bad", {"ok": True}]))
    assert snippets_routes._load_usage_events() == [{"ok": True}]


def test_apply_list_filters(snippets_workspace):
    snippet = make_snippet()
    filtered = snippets_routes._apply_list_filters(
        [snippet],
        language=SnippetLanguage.PYTHON,
        category=SnippetCategory.UTILITY,
        is_favorite=True,
    )
    assert filtered == [snippet]


def test_sort_and_paginate(snippets_workspace):
    snippets = [
        make_snippet("a", title="B", usage_count=1, updated_at=datetime.now()),
        make_snippet("b", title="A", usage_count=5, updated_at=datetime.now() - timedelta(days=1)),
    ]
    by_usage = snippets_routes._sort_snippets(snippets, "usage")
    assert by_usage[0].id == "b"
    by_title = snippets_routes._sort_snippets(snippets, "title")
    assert by_title[0].title == "A"
    assert snippets_routes._paginate_results(by_usage, 0, 1)[0].id == "b"


@pytest.mark.asyncio
async def test_list_snippets(snippets_workspace):
    snippets_routes._save_snippet(make_snippet("ls1"))
    results = await snippets_routes.list_snippets(limit=10, offset=0)
    assert results and results[0].id == "ls1"


@pytest.mark.asyncio
async def test_list_snippets_error(monkeypatch):
    monkeypatch.setattr(snippets_routes, "_load_all_snippets", lambda: (_ for _ in ()).throw(RuntimeError("boom")))
    with pytest.raises(HTTPException):
        await snippets_routes.list_snippets()


@pytest.mark.asyncio
async def test_create_snippet(snippets_workspace):
    request = CreateSnippetRequest(title="New", code="print(1)")
    snippet = await snippets_routes.create_snippet(request)
    assert snippet.title == "New"


@pytest.mark.asyncio
async def test_create_snippet_error(monkeypatch):
    monkeypatch.setattr(snippets_routes, "_save_snippet", lambda snippet: (_ for _ in ()).throw(RuntimeError("boom")))
    with pytest.raises(HTTPException):
        await snippets_routes.create_snippet(CreateSnippetRequest(title="Err", code=""))


@pytest.mark.asyncio
async def test_search_snippets(snippets_workspace):
    snippet = make_snippet("search", tags=["alpha"], code="print('alpha')")
    snippets_routes._save_snippet(snippet)
    request = SearchSnippetsRequest(query="alpha", language=SnippetLanguage.PYTHON)
    results = await snippets_routes.search_snippets(request)
    assert results and results[0].id == "search"


@pytest.mark.asyncio
async def test_search_snippets_error(monkeypatch):
    monkeypatch.setattr(snippets_routes, "_load_all_snippets", lambda: (_ for _ in ()).throw(RuntimeError("boom")))
    with pytest.raises(HTTPException):
        await snippets_routes.search_snippets(SearchSnippetsRequest(query="x"))


def test_filter_helpers(snippets_workspace):
    snippets = [
        make_snippet("f1", language=SnippetLanguage.PYTHON, category=SnippetCategory.API, is_favorite=True),
        make_snippet("f2", language=SnippetLanguage.JAVA, category=SnippetCategory.UTILITY, is_favorite=False, tags=["tag"]),
    ]
    assert len(snippets_routes._filter_by_language(snippets, SnippetLanguage.PYTHON)) == 1
    assert len(snippets_routes._filter_by_category(snippets, SnippetCategory.API)) == 1
    assert len(snippets_routes._filter_by_favorite(snippets, True)) == 1
    assert len(snippets_routes._filter_by_tags(snippets, ["tag"])) == 1
    assert len(snippets_routes._filter_by_query(snippets, "print")) == 2


@pytest.mark.asyncio
async def test_get_snippet_stats(snippets_workspace):
    snippets_routes._save_snippet(make_snippet("stats", tags=["x"]))
    stats = await snippets_routes.get_snippet_stats()
    assert stats.total_snippets >= 1


@pytest.mark.asyncio
async def test_get_snippet_stats_error(monkeypatch):
    monkeypatch.setattr(snippets_routes, "_load_all_snippets", lambda: (_ for _ in ()).throw(RuntimeError("boom")))
    with pytest.raises(HTTPException):
        await snippets_routes.get_snippet_stats()


def test_count_helpers(snippets_workspace):
    snippet = make_snippet("count")
    assert snippets_routes._count_snippets_by_language([snippet])[snippet.language.value] == 1
    assert snippets_routes._count_snippets_by_category([snippet])[snippet.category.value] == 1
    assert snippets_routes._count_favorites([snippet]) == 1
    assert snippets_routes._count_unique_tags([snippet]) == len(set(snippet.tags))
    assert snippets_routes._get_most_used_snippets([snippet])[0][0] == snippet.id


@pytest.mark.asyncio
async def test_export_snippets(snippets_workspace):
    snippets_routes._save_snippet(make_snippet("exp"))
    response = await snippets_routes.export_snippets()
    assert json.loads(response.body)["metadata"]["total_snippets"] >= 1


@pytest.mark.asyncio
async def test_export_snippets_error(monkeypatch):
    monkeypatch.setattr(snippets_routes, "_load_all_snippets", lambda: (_ for _ in ()).throw(RuntimeError("boom")))
    with pytest.raises(HTTPException):
        await snippets_routes.export_snippets()


def test_build_collection(snippets_workspace):
    snippet = make_snippet("col")
    collection = snippets_routes._build_snippet_collection([snippet])
    assert collection.metadata["total_snippets"] == 1


def test_create_export_response(snippets_workspace):
    collection = SnippetCollection(name="test", snippets=[make_snippet("resp")])
    response = snippets_routes._create_export_response(collection)
    assert "snippets" in response.body.decode("utf-8")


@pytest.mark.asyncio
async def test_import_snippets(snippets_workspace):
    snippet = make_snippet("imp")
    collection = SnippetCollection(name="test", snippets=[snippet])
    result = await snippets_routes.import_snippets(collection)
    assert result["imported"] == 1


@pytest.mark.asyncio
async def test_import_snippets_updates(snippets_workspace):
    snippet = make_snippet("update")
    snippets_routes._save_snippet(snippet)
    snippet.code = "print('updated')"
    collection = SnippetCollection(name="test", snippets=[snippet])
    result = await snippets_routes.import_snippets(collection)
    assert result["updated"] == 1


@pytest.mark.asyncio
async def test_import_snippets_error(monkeypatch):
    monkeypatch.setattr(snippets_routes, "_save_snippet", lambda snippet: (_ for _ in ()).throw(RuntimeError("boom")))
    collection = SnippetCollection(name="bad", snippets=[make_snippet("bad")])
    with pytest.raises(HTTPException):
        await snippets_routes.import_snippets(collection)


@pytest.mark.asyncio
async def test_mark_snippet_used(snippets_workspace):
    snippet = make_snippet("used", usage_count=0)
    snippets_routes._save_snippet(snippet)
    response = await snippets_routes.mark_snippet_used("used")
    assert json.loads(response.body)["usage_count"] == 1


@pytest.mark.asyncio
async def test_mark_snippet_used_missing(snippets_workspace):
    with pytest.raises(HTTPException) as exc:
        await snippets_routes.mark_snippet_used("none")
    assert exc.value.status_code == 404


@pytest.mark.asyncio
async def test_mark_snippet_used_error(monkeypatch, snippets_workspace):
    snippet = make_snippet("err")
    snippets_routes._save_snippet(snippet)
    monkeypatch.setattr(snippets_routes, "_save_snippet", lambda snippet: (_ for _ in ()).throw(RuntimeError("boom")))
    with pytest.raises(HTTPException):
        await snippets_routes.mark_snippet_used("err")


@pytest.mark.asyncio
async def test_track_snippet_usage(snippets_workspace):
    event = SnippetUsageEvent(snippet_id="s", action="use")
    response = await snippets_routes.track_snippet_usage(event)
    assert response.status_code == 201
    assert snippets_routes._load_usage_events()


@pytest.mark.asyncio
async def test_get_snippet(snippets_workspace):
    snippet = make_snippet("get")
    snippets_routes._save_snippet(snippet)
    loaded = await snippets_routes.get_snippet("get")
    assert loaded.id == "get"


@pytest.mark.asyncio
async def test_get_snippet_missing(snippets_workspace):
    with pytest.raises(HTTPException) as exc:
        await snippets_routes.get_snippet("missing")
    assert exc.value.status_code == 404


@pytest.mark.asyncio
async def test_get_snippet_error(monkeypatch):
    monkeypatch.setattr(snippets_routes, "_load_snippet", lambda snippet_id: (_ for _ in ()).throw(RuntimeError("boom")))
    with pytest.raises(HTTPException):
        await snippets_routes.get_snippet("bad")


@pytest.mark.asyncio
async def test_update_snippet(snippets_workspace):
    snippet = make_snippet("upd")
    snippets_routes._save_snippet(snippet)
    request = UpdateSnippetRequest(title="Updated")
    updated = await snippets_routes.update_snippet("upd", request)
    assert updated.title == "Updated"


@pytest.mark.asyncio
async def test_update_snippet_missing(snippets_workspace):
    with pytest.raises(HTTPException) as exc:
        await snippets_routes.update_snippet("missing", UpdateSnippetRequest(title="x"))
    assert exc.value.status_code == 404


@pytest.mark.asyncio
async def test_update_snippet_error(monkeypatch, snippets_workspace):
    snippet = make_snippet("upd_err")
    snippets_routes._save_snippet(snippet)
    monkeypatch.setattr(snippets_routes, "_save_snippet", lambda snippet: (_ for _ in ()).throw(RuntimeError("boom")))
    with pytest.raises(HTTPException):
        await snippets_routes.update_snippet("upd_err", UpdateSnippetRequest(title="y"))


@pytest.mark.asyncio
async def test_delete_snippet(snippets_workspace):
    snippet = make_snippet("del")
    snippets_routes._save_snippet(snippet)
    await snippets_routes.delete_snippet("del")
    assert snippets_routes._load_snippet("del") is None


@pytest.mark.asyncio
async def test_delete_snippet_missing(snippets_workspace):
    with pytest.raises(HTTPException) as exc:
        await snippets_routes.delete_snippet("missing")
    assert exc.value.status_code == 404


@pytest.mark.asyncio
async def test_delete_snippet_error(monkeypatch, snippets_workspace):
    snippet = make_snippet("del_err")
    snippets_routes._save_snippet(snippet)
    monkeypatch.setattr(snippets_routes, "_delete_snippet_file", lambda snippet_id: (_ for _ in ()).throw(RuntimeError("boom")))
    with pytest.raises(HTTPException):
        await snippets_routes.delete_snippet("del_err")

