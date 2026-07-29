"""Unit tests for backend.persistence.conversation.conversation_store."""

from __future__ import annotations

import pytest
from unittest.mock import AsyncMock

from backend.persistence.conversation.conversation_store import ConversationStore
from backend.persistence.data_models.conversation_metadata import ConversationMetadata
from backend.persistence.data_models.conversation_metadata_result_set import ConversationMetadataResultSet


class DummyConversationStore(ConversationStore):
    def __init__(self):
        self.store: dict[str, ConversationMetadata] = {}

    async def save_metadata(self, metadata: ConversationMetadata) -> None:
        self.store[metadata.conversation_id] = metadata

    async def get_metadata(self, conversation_id: str) -> ConversationMetadata:
        if conversation_id not in self.store:
            raise FileNotFoundError(f"Missing {conversation_id}")
        return self.store[conversation_id]

    async def delete_metadata(self, conversation_id: str) -> None:
        self.store.pop(conversation_id, None)

    async def delete_all_metadata(self) -> None:
        self.store.clear()

    async def exists(self, conversation_id: str) -> bool:
        return conversation_id in self.store

    async def search(self, page_id: str | None = None, limit: int = 20) -> ConversationMetadataResultSet:
        return ConversationMetadataResultSet(items=list(self.store.values()))

    @classmethod
    async def get_instance(cls, config, user_id):
        return cls()


@pytest.mark.asyncio
async def test_validate_metadata():
    store = DummyConversationStore()
    meta_user1 = ConversationMetadata(conversation_id="c1", user_id="user1", title="c1", selected_repository="repo")
    meta_anon = ConversationMetadata(conversation_id="c2", user_id=None, title="c2", selected_repository="repo")
    await store.save_metadata(meta_user1)
    await store.save_metadata(meta_anon)

    # Valid user match
    assert await store.validate_metadata("c1", "user1") is True
    # User mismatch
    assert await store.validate_metadata("c1", "user2") is False
    # Anonymous user metadata
    assert await store.validate_metadata("c2", "user1") is False


@pytest.mark.asyncio
async def test_get_all_metadata():
    store = DummyConversationStore()
    m1 = ConversationMetadata(conversation_id="c1", user_id="u1", title="c1", selected_repository="repo")
    m2 = ConversationMetadata(conversation_id="c2", user_id="u1", title="c2", selected_repository="repo")
    await store.save_metadata(m1)
    await store.save_metadata(m2)

    results = await store.get_all_metadata(["c1", "c2"])
    assert len(results) == 2
    assert results[0].conversation_id == "c1"
    assert results[1].conversation_id == "c2"

