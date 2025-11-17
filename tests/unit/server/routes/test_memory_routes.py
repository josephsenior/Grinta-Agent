"""Unit tests for Forge memory management routes."""

from __future__ import annotations

from datetime import datetime, timedelta
from types import SimpleNamespace
from typing import Any

import pytest

from fastapi import HTTPException

from forge.server.routes import memory as memory_routes


class DummySettingsStore:
    def __init__(self, settings: Any | None):
        self._settings: Any | None = settings
        self.saved_settings: Any | None = None

    async def load(self):
        return self._settings

    async def save(self, settings: Any):
        self.saved_settings = settings
        self._settings = settings


@pytest.mark.asyncio
async def test_list_memories_returns_settings_memories():
    settings = SimpleNamespace(MEMORIES=[{"id": "1"}])
    store = DummySettingsStore(settings)
    result = await memory_routes.list_memories(store)
    assert result == [{"id": "1"}]


@pytest.mark.asyncio
async def test_list_memories_handles_missing_settings():
    store = DummySettingsStore(None)
    result = await memory_routes.list_memories(store)
    assert result == []


@pytest.mark.asyncio
async def test_create_memory_initializes_memories_and_saves(monkeypatch):
    settings = SimpleNamespace()
    store = DummySettingsStore(settings)
    payload = memory_routes.CreateMemoryRequest(
        title="Memory",
        content="Important detail",
        category=memory_routes.MemoryCategory.FACT,
        tags=["tag1"],
    )
    response = await memory_routes.create_memory(payload, store)
    assert response["status"] == "success"
    assert store._settings is not None
    assert hasattr(store._settings, "MEMORIES")
    assert len(store._settings.MEMORIES) == 1
    assert store.saved_settings is not None
    saved = store.saved_settings.MEMORIES[0]
    assert saved["title"] == "Memory"


@pytest.mark.asyncio
async def test_create_memory_missing_settings_raises():
    store = DummySettingsStore(None)
    payload = memory_routes.CreateMemoryRequest(
        title="Memory",
        content="Content",
        category=memory_routes.MemoryCategory.FACT,
    )
    with pytest.raises(HTTPException) as exc:
        await memory_routes.create_memory(payload, store)
    assert exc.value.status_code == 500


@pytest.mark.asyncio
async def test_search_memories_applies_filters():
    memories = [
        {
            "id": "1",
            "title": "Python Tips",
            "content": "Use list comprehension",
            "category": memory_routes.MemoryCategory.TECHNICAL.value,
            "tags": ["python", "tips"],
            "usage_count": 5,
            "importance": memory_routes.MemoryImportance.HIGH.value,
        },
        {
            "id": "2",
            "title": "Lunch order",
            "content": "Prefers sushi",
            "category": memory_routes.MemoryCategory.PREFERENCE.value,
            "tags": ["food"],
            "usage_count": 1,
            "importance": memory_routes.MemoryImportance.LOW.value,
        },
    ]
    settings = SimpleNamespace(MEMORIES=memories)
    store = DummySettingsStore(settings)
    search = memory_routes.SearchMemoriesRequest(
        query="python",
        category=memory_routes.MemoryCategory.TECHNICAL,
        tags=["tips"],
        min_usage_count=5,
        importance=memory_routes.MemoryImportance.HIGH,
    )
    result = await memory_routes.search_memories(search, store)
    assert result == [memories[0]]


@pytest.mark.asyncio
async def test_search_memories_handles_missing_memories():
    store = DummySettingsStore(SimpleNamespace())
    search = memory_routes.SearchMemoriesRequest(query="anything")
    assert await memory_routes.search_memories(search, store) == []


def test_memory_matches_query_cases():
    memory = {"title": "Python", "content": "Details", "tags": ["tip"]}
    assert memory_routes._memory_matches_query(memory, None)
    assert memory_routes._memory_matches_query(memory, "python")
    assert memory_routes._memory_matches_query(memory, "tip")
    assert not memory_routes._memory_matches_query(memory, "java")


def test_memory_matches_category_tags_usage_importance():
    memory = {
        "category": memory_routes.MemoryCategory.PROJECT.value,
        "tags": ["proj", "urgent"],
        "usage_count": 3,
        "importance": memory_routes.MemoryImportance.MEDIUM.value,
    }
    assert memory_routes._memory_matches_category(memory, None)
    assert memory_routes._memory_matches_category(
        memory, memory_routes.MemoryCategory.PROJECT.value
    )
    assert not memory_routes._memory_matches_category(memory, "other")

    assert memory_routes._memory_matches_tags(memory, None)
    assert memory_routes._memory_matches_tags(memory, ["proj"])
    assert not memory_routes._memory_matches_tags(memory, ["missing"])

    assert memory_routes._memory_matches_usage_count(memory, None)
    assert memory_routes._memory_matches_usage_count(memory, 2)
    assert not memory_routes._memory_matches_usage_count(memory, 5)

    assert memory_routes._memory_matches_importance(memory, None)
    assert memory_routes._memory_matches_importance(
        memory, memory_routes.MemoryImportance.MEDIUM.value
    )
    assert not memory_routes._memory_matches_importance(
        memory, memory_routes.MemoryImportance.HIGH.value
    )


def test_memory_matches_filters_failure_cases():
    memory = {
        "title": "Alpha",
        "content": "Data",
        "category": memory_routes.MemoryCategory.FACT.value,
        "tags": ["alpha"],
        "usage_count": 1,
        "importance": memory_routes.MemoryImportance.LOW.value,
    }
    base_search = memory_routes.SearchMemoriesRequest(query="alpha")
    assert not memory_routes._memory_matches_filters(
        memory,
        base_search.model_copy(
            update={"category": memory_routes.MemoryCategory.PROJECT}
        ),
    )
    assert not memory_routes._memory_matches_filters(
        memory, base_search.model_copy(update={"tags": ["beta"]})
    )
    assert not memory_routes._memory_matches_filters(
        memory, base_search.model_copy(update={"min_usage_count": 5})
    )
    assert not memory_routes._memory_matches_filters(
        memory,
        base_search.model_copy(
            update={"importance": memory_routes.MemoryImportance.HIGH}
        ),
    )


@pytest.mark.asyncio
async def test_get_memory_stats_with_data():
    today_iso = datetime.now().isoformat()
    older_iso = (datetime.now() - timedelta(days=1)).isoformat()
    memories = [
        {
            "category": memory_routes.MemoryCategory.TECHNICAL.value,
            "usage_count": 10,
            "last_used": today_iso,
        },
        {
            "category": memory_routes.MemoryCategory.PREFERENCE.value,
            "usage_count": 1,
            "last_used": older_iso,
        },
        {
            "category": memory_routes.MemoryCategory.TECHNICAL.value,
            "usage_count": 3,
        },
    ]
    store = DummySettingsStore(SimpleNamespace(MEMORIES=memories))
    stats = await memory_routes.get_memory_stats(store)
    assert stats.total == 3
    assert stats.by_category[memory_routes.MemoryCategory.TECHNICAL.value] == 2
    assert stats.used_today == 1
    assert stats.most_used[0]["usage_count"] == 10
    assert stats.recently_used[0]["last_used"] == today_iso


@pytest.mark.asyncio
async def test_get_memory_stats_no_data():
    store = DummySettingsStore(None)
    stats = await memory_routes.get_memory_stats(store)
    assert stats.total == 0
    assert stats.by_category == {}


@pytest.mark.asyncio
async def test_track_memory_usage_updates_existing():
    memories = [{"id": "1", "usage_count": 0}]
    store = DummySettingsStore(SimpleNamespace(MEMORIES=memories))
    response = await memory_routes.track_memory_usage("1", store)
    assert response["status"] == "success"
    assert memories[0]["usage_count"] == 1
    assert memories[0]["last_used"] is not None


@pytest.mark.asyncio
async def test_track_memory_usage_missing_memory():
    store = DummySettingsStore(SimpleNamespace(MEMORIES=[]))
    with pytest.raises(HTTPException) as exc:
        await memory_routes.track_memory_usage("missing", store)
    assert exc.value.status_code == 404


@pytest.mark.asyncio
async def test_track_memory_usage_no_memories():
    store = DummySettingsStore(None)
    with pytest.raises(HTTPException) as exc:
        await memory_routes.track_memory_usage("1", store)
    assert exc.value.status_code == 404


@pytest.mark.asyncio
async def test_export_memories_includes_stats(monkeypatch):
    memories = [{"id": "1"}]
    store = DummySettingsStore(SimpleNamespace(MEMORIES=memories))

    async def fake_stats(_store):
        return memory_routes.MemoryStats(
            total=1, by_category={}, used_today=0, most_used=[], recently_used=[]
        )

    monkeypatch.setattr(memory_routes, "get_memory_stats", fake_stats)
    result = await memory_routes.export_memories(store)
    assert result["memories"] == memories
    assert result["stats"]["total"] == 1


@pytest.mark.asyncio
async def test_export_memories_handles_missing_data(monkeypatch):
    store = DummySettingsStore(None)

    async def fake_stats(_store):
        return memory_routes.MemoryStats(
            total=0, by_category={}, used_today=0, most_used=[], recently_used=[]
        )

    monkeypatch.setattr(memory_routes, "get_memory_stats", fake_stats)
    result = await memory_routes.export_memories(store)
    assert result["memories"] == []


@pytest.mark.asyncio
async def test_import_memories_replace(monkeypatch):
    settings = SimpleNamespace(MEMORIES=[{"id": "existing"}])
    store = DummySettingsStore(settings)
    data = {"memories": [{"id": "new"}]}
    result = await memory_routes.import_memories(
        data, merge=False, settings_store=store
    )
    assert result["imported"] == 1
    assert store._settings is not None
    assert store._settings.MEMORIES == [{"id": "new"}]


@pytest.mark.asyncio
async def test_import_memories_merge_avoids_duplicates():
    settings = SimpleNamespace(MEMORIES=[{"id": "existing"}])
    store = DummySettingsStore(settings)
    data = {"memories": [{"id": "existing"}, {"id": "new"}]}
    result = await memory_routes.import_memories(data, merge=True, settings_store=store)
    assert result["imported"] == 1
    assert store._settings is not None
    assert len(store._settings.MEMORIES) == 2


@pytest.mark.asyncio
async def test_import_memories_initializes_memories_when_missing():
    settings = SimpleNamespace()
    store = DummySettingsStore(settings)
    data = {"memories": [{"id": "new"}]}
    result = await memory_routes.import_memories(data, merge=True, settings_store=store)
    assert result["total"] == 1


@pytest.mark.asyncio
async def test_import_memories_missing_settings_raises():
    store = DummySettingsStore(None)
    with pytest.raises(HTTPException) as exc:
        await memory_routes.import_memories({"memories": []}, settings_store=store)
    assert exc.value.status_code == 500


@pytest.mark.asyncio
async def test_import_memories_invalid_payload():
    store = DummySettingsStore(SimpleNamespace())
    with pytest.raises(HTTPException) as exc:
        await memory_routes.import_memories({}, settings_store=store)
    assert exc.value.status_code == 400


@pytest.mark.asyncio
async def test_get_memory_success():
    memory = {"id": "1"}
    store = DummySettingsStore(SimpleNamespace(MEMORIES=[memory]))
    assert await memory_routes.get_memory("1", store) == memory


@pytest.mark.asyncio
async def test_get_memory_not_found():
    store = DummySettingsStore(SimpleNamespace(MEMORIES=[]))
    with pytest.raises(HTTPException) as exc:
        await memory_routes.get_memory("missing", store)
    assert exc.value.status_code == 404


@pytest.mark.asyncio
async def test_update_memory_success(monkeypatch):
    memory = {"id": "1", "title": "Old", "content": "Old"}
    settings = SimpleNamespace(MEMORIES=[memory])
    store = DummySettingsStore(settings)
    updates = memory_routes.UpdateMemoryRequest(
        title="New", tags=["tag"], importance=memory_routes.MemoryImportance.HIGH
    )
    response = await memory_routes.update_memory("1", updates, store)
    assert response["status"] == "success"
    assert memory["title"] == "New"
    assert memory["tags"] == ["tag"]
    assert memory["importance"] == memory_routes.MemoryImportance.HIGH
    assert store.saved_settings is settings


@pytest.mark.asyncio
async def test_update_memory_not_found():
    settings = SimpleNamespace(MEMORIES=[{"id": "1"}])
    store = DummySettingsStore(settings)
    with pytest.raises(HTTPException) as exc:
        await memory_routes.update_memory(
            "missing", memory_routes.UpdateMemoryRequest(title="New"), store
        )
    assert exc.value.status_code == 404


@pytest.mark.asyncio
async def test_update_memory_no_settings():
    store = DummySettingsStore(None)
    with pytest.raises(HTTPException) as exc:
        await memory_routes.update_memory(
            "1", memory_routes.UpdateMemoryRequest(title="New"), store
        )
    assert exc.value.status_code == 404


def test_apply_memory_updates_individual_fields():
    memory: dict[str, Any] = {}
    updates = memory_routes.UpdateMemoryRequest(
        title="Title",
        content="Content",
        category=memory_routes.MemoryCategory.CUSTOM,
        tags=["tag"],
        importance=memory_routes.MemoryImportance.LOW,
    )
    memory_routes._apply_memory_updates(memory, updates)
    assert memory["title"] == "Title"
    assert memory["category"] == memory_routes.MemoryCategory.CUSTOM


@pytest.mark.asyncio
async def test_delete_memory_success():
    settings = SimpleNamespace(MEMORIES=[{"id": "1"}, {"id": "2"}])
    store = DummySettingsStore(settings)
    response = await memory_routes.delete_memory("1", store)
    assert response["status"] == "success"
    assert store._settings is not None
    assert len(store._settings.MEMORIES) == 1


@pytest.mark.asyncio
async def test_delete_memory_not_found():
    settings = SimpleNamespace(MEMORIES=[{"id": "1"}])
    store = DummySettingsStore(settings)
    with pytest.raises(HTTPException) as exc:
        await memory_routes.delete_memory("missing", store)
    assert exc.value.status_code == 404


@pytest.mark.asyncio
async def test_delete_memory_no_settings():
    store = DummySettingsStore(None)
    with pytest.raises(HTTPException) as exc:
        await memory_routes.delete_memory("1", store)
    assert exc.value.status_code == 404


@pytest.mark.asyncio
async def test_get_memory_missing_settings():
    store = DummySettingsStore(None)
    with pytest.raises(HTTPException) as exc:
        await memory_routes.get_memory("1", store)
    assert exc.value.status_code == 404
