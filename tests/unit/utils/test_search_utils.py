import json
import pytest
from openhands.storage.conversation.file_conversation_store import FileConversationStore
from openhands.storage.locations import get_conversation_metadata_filename
from openhands.storage.memory import InMemoryFileStore
from openhands.utils.search_utils import iterate, offset_to_page_id, page_id_to_offset


def test_offset_to_page_id():
    assert bool(offset_to_page_id(10, True))
    assert bool(offset_to_page_id(0, True))
    assert offset_to_page_id(10, False) is None
    assert offset_to_page_id(0, False) is None


def test_page_id_to_offset():
    assert page_id_to_offset(None) == 0


def test_bidirectional_conversion():
    test_offsets = [0, 1, 10, 100, 1000]
    for offset in test_offsets:
        page_id = offset_to_page_id(offset, True)
        assert page_id_to_offset(page_id) == offset


@pytest.mark.asyncio
async def test_iterate_empty():
    store = FileConversationStore(InMemoryFileStore({}))
    results = []
    async for result in iterate(store.search):
        results.append(result)
    assert not results


@pytest.mark.asyncio
async def test_iterate_single_page():
    store = FileConversationStore(
        InMemoryFileStore(
            {
                get_conversation_metadata_filename("conv1"): json.dumps(
                    {
                        "conversation_id": "conv1",
                        "github_user_id": "123",
                        "user_id": "123",
                        "selected_repository": "repo1",
                        "title": "First conversation",
                        "created_at": "2025-01-16T19:51:04Z",
                    }
                ),
                get_conversation_metadata_filename("conv2"): json.dumps(
                    {
                        "conversation_id": "conv2",
                        "github_user_id": "123",
                        "user_id": "123",
                        "selected_repository": "repo1",
                        "title": "Second conversation",
                        "created_at": "2025-01-17T19:51:04Z",
                    }
                ),
            }
        )
    )
    results = []
    async for result in iterate(store.search):
        results.append(result)
    assert len(results) == 2
    assert results[0].conversation_id == "conv2"
    assert results[1].conversation_id == "conv1"


@pytest.mark.asyncio
async def test_iterate_multiple_pages():
    store = FileConversationStore(
        InMemoryFileStore(
            {
                get_conversation_metadata_filename(f"conv{i}"): json.dumps(
                    {
                        "conversation_id": f"conv{i}",
                        "github_user_id": "123",
                        "user_id": "123",
                        "selected_repository": "repo1",
                        "title": f"ServerConversation {i}",
                        "created_at": f"2025-01-{
                            15 +
                            i}T19:51:04Z",
                    }
                )
                for i in range(1, 6)
            }
        )
    )
    results = []
    async for result in iterate(store.search, limit=2):
        results.append(result)
    assert len(results) == 5
    assert [r.conversation_id for r in results] == ["conv5", "conv4", "conv3", "conv2", "conv1"]


@pytest.mark.asyncio
async def test_iterate_with_invalid_conversation():
    store = FileConversationStore(
        InMemoryFileStore(
            {
                get_conversation_metadata_filename("conv1"): json.dumps(
                    {
                        "conversation_id": "conv1",
                        "github_user_id": "123",
                        "user_id": "123",
                        "selected_repository": "repo1",
                        "title": "Valid conversation",
                        "created_at": "2025-01-16T19:51:04Z",
                    }
                ),
                get_conversation_metadata_filename("conv2"): "invalid json",
            }
        )
    )
    results = []
    async for result in iterate(store.search):
        results.append(result)
    assert len(results) == 1
    assert results[0].conversation_id == "conv1"
