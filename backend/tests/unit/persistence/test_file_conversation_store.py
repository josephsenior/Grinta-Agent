"""Unit tests for backend.persistence.conversation.file_conversation_store."""

from __future__ import annotations

import json
from datetime import datetime
from unittest.mock import MagicMock

import pytest

from backend.persistence.conversation.file_conversation_store import FileConversationStore
from backend.persistence.data_models.conversation_metadata import ConversationMetadata


class MemoryFileStore:
    def __init__(self):
        self.files: dict[str, str] = {}

    def write(self, path: str, content: str) -> None:
        self.files[path] = content

    def read(self, path: str) -> str:
        if path not in self.files:
            raise FileNotFoundError(f"File not found: {path}")
        return self.files[path]

    def delete(self, path: str) -> None:
        p = path.rstrip("/")
        to_delete = [k for k in self.files if k == p or k.startswith(p + "/")]
        for k in to_delete:
            del self.files[k]

    def list(self, directory: str) -> list[str]:
        prefix = directory.rstrip("/") + "/"
        found = set()
        for path in self.files:
            if path.startswith(prefix):
                rel = path[len(prefix):]
                parts = rel.split("/")
                found.add(directory.rstrip("/") + "/" + parts[0])
        if not found:
            raise FileNotFoundError(f"Directory not found: {directory}")
        return list(found)


@pytest.fixture
def memory_file_store():
    return MemoryFileStore()


@pytest.fixture
def store(memory_file_store):
    config = MagicMock()
    config.file_store = "local"
    return FileConversationStore(file_store=memory_file_store, config=config, user_id="user_123")


@pytest.mark.asyncio
async def test_save_and_get_metadata(store):
    meta = ConversationMetadata(
        conversation_id="conv_1",
        title="Test Conv",
        selected_repository="repo_1",
        user_id="user_123",
        created_at=datetime.now(),
    )
    await store.save_metadata(meta)
    loaded = await store.get_metadata("conv_1")
    assert loaded.conversation_id == "conv_1"
    assert loaded.title == "Test Conv"


@pytest.mark.asyncio
async def test_get_metadata_creates_if_missing(store):
    meta = await store.get_metadata("conv_new", create_if_missing=True)
    assert meta.conversation_id == "conv_new"
    assert meta.title == "New Conversation"


@pytest.mark.asyncio
async def test_get_metadata_raises_when_create_false(store):
    with pytest.raises(FileNotFoundError):
        await store.get_metadata("conv_missing", create_if_missing=False)


@pytest.mark.asyncio
async def test_exists(store):
    assert await store.exists("c1") is False
    meta = ConversationMetadata(
        conversation_id="c1",
        title="C1",
        selected_repository="r",
        user_id="user_123",
        created_at=datetime.now(),
    )
    await store.save_metadata(meta)
    assert await store.exists("c1") is True


@pytest.mark.asyncio
async def test_search_and_pagination(store):
    m1 = ConversationMetadata(
        conversation_id="c1",
        title="C1",
        selected_repository="r",
        user_id="user_123",
        created_at=datetime.now(),
    )
    m2 = ConversationMetadata(
        conversation_id="c2",
        title="C2",
        selected_repository="r",
        user_id="user_123",
        created_at=datetime.now(),
    )
    await store.save_metadata(m1)
    await store.save_metadata(m2)

    res = await store.search(limit=10)
    assert len(res.results) == 2



@pytest.mark.asyncio
async def test_delete_all_metadata(store):
    m1 = ConversationMetadata(
        conversation_id="c1",
        title="C1",
        selected_repository="r",
        user_id="user_123",
        created_at=datetime.now(),
    )
    await store.save_metadata(m1)
    assert await store.exists("c1") is True

    await store.delete_all_metadata()
    assert await store.exists("c1") is False
