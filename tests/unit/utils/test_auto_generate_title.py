"""Tests for the auto-generate title functionality."""

from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch
import pytest
from forge.core.config.forge_config import ForgeConfig
from forge.events.action import MessageAction
from forge.events.event import EventSource
from forge.events.event_store import EventStore
from forge.llm.llm_registry import LLMRegistry
from forge.server.conversation_manager.standalone_conversation_manager import StandaloneConversationManager
from forge.server.monitoring import MonitoringListener
from forge.storage.data_models.settings import Settings
from forge.storage.memory import InMemoryFileStore
from forge.utils.conversation_summary import auto_generate_title


@pytest.mark.asyncio
async def test_auto_generate_title_with_llm():
    """Test auto-generating a title using LLM."""
    file_store = InMemoryFileStore()
    llm_registry = MagicMock(spec=LLMRegistry)
    conversation_id = "test-conversation"
    user_id = "test-user"
    user_message = MessageAction(content="Help me write a Python script to analyze data")
    user_message._source = EventSource.USER
    user_message._id = 1
    user_message._timestamp = datetime.now(timezone.utc).isoformat()
    with patch("forge.utils.conversation_summary.EventStore") as mock_event_store_cls:
        mock_event_store = MagicMock(spec=EventStore)
        mock_event_store.search_events.return_value = [user_message]
        mock_event_store_cls.return_value = mock_event_store
        llm_registry.request_extraneous_completion.return_value = "Python Data Analysis Script"
        settings = Settings(llm_model="test-model", llm_api_key="test-key", llm_base_url="test-url")
        title = await auto_generate_title(conversation_id, user_id, file_store, settings, llm_registry)
        assert title == "Python Data Analysis Script"
        mock_event_store_cls.assert_called_once_with(conversation_id, file_store, user_id)
        llm_registry.request_extraneous_completion.assert_called_once()


@pytest.mark.asyncio
async def test_auto_generate_title_fallback():
    """Test auto-generating a title with fallback to truncation when LLM fails."""
    file_store = InMemoryFileStore()
    llm_registry = MagicMock(spec=LLMRegistry)
    conversation_id = "test-conversation"
    user_id = "test-user"
    long_message = "This is a very long message that should be truncated when used as a title because it exceeds the maximum length allowed for titles"
    user_message = MessageAction(content=long_message)
    user_message._source = EventSource.USER
    user_message._id = 1
    user_message._timestamp = datetime.now(timezone.utc).isoformat()
    with patch("forge.utils.conversation_summary.EventStore") as mock_event_store_cls:
        mock_event_store = MagicMock(spec=EventStore)
        mock_event_store.search_events.return_value = [user_message]
        mock_event_store_cls.return_value = mock_event_store
        llm_registry.request_extraneous_completion.side_effect = Exception("Test error")
        settings = Settings(llm_model="test-model", llm_api_key="test-key", llm_base_url="test-url")
        title = await auto_generate_title(conversation_id, user_id, file_store, settings, llm_registry)
        assert title == "This is a very long message th..."
        assert len(title) <= 35
        mock_event_store_cls.assert_called_once_with(conversation_id, file_store, user_id)


@pytest.mark.asyncio
async def test_auto_generate_title_no_messages():
    """Test auto-generating a title when there are no user messages."""
    file_store = InMemoryFileStore()
    llm_registry = MagicMock(spec=LLMRegistry)
    conversation_id = "test-conversation"
    user_id = "test-user"
    with patch("forge.utils.conversation_summary.EventStore") as mock_event_store_cls:
        mock_event_store = MagicMock(spec=EventStore)
        mock_event_store.search_events.return_value = []
        mock_event_store_cls.return_value = mock_event_store
        settings = Settings(llm_model="test-model", llm_api_key="test-key", llm_base_url="test-url")
        title = await auto_generate_title(conversation_id, user_id, file_store, settings, llm_registry)
        assert title == ""
        mock_event_store_cls.assert_called_once_with(conversation_id, file_store, user_id)


@pytest.mark.asyncio
async def test_update_conversation_with_title():
    """Test that _update_conversation_for_event updates the title when needed."""
    sio = MagicMock()
    sio.emit = AsyncMock()
    file_store = InMemoryFileStore()
    server_config = MagicMock()
    llm_registry = MagicMock(spec=LLMRegistry)
    conversation_id = "test-conversation"
    user_id = "test-user"
    settings = Settings(llm_model="test-model", llm_api_key="test-key", llm_base_url="test-url")
    mock_conversation_store = AsyncMock()
    mock_metadata = MagicMock()
    mock_metadata.title = f"Conversation {conversation_id[:5]}"
    mock_conversation_store.get_metadata.return_value = mock_metadata
    manager = StandaloneConversationManager(
        sio=sio,
        config=ForgeConfig(),
        file_store=file_store,
        server_config=server_config,
        monitoring_listener=MonitoringListener(),
    )
    manager._get_conversation_store = AsyncMock(return_value=mock_conversation_store)
    with patch(
        "forge.server.conversation_manager.standalone_conversation_manager.auto_generate_title",
        AsyncMock(return_value="Generated Title"),
    ):
        await manager._update_conversation_for_event(user_id, conversation_id, settings, llm_registry)
        assert mock_metadata.title == "Generated Title"
        sio.emit.assert_called_once()
        call_args = sio.emit.call_args[0]
        assert call_args[0] == "oh_event"
        assert call_args[1]["status_update"] is True
        assert call_args[1]["type"] == "info"
        assert call_args[1]["message"] == conversation_id
        assert call_args[1]["conversation_title"] == "Generated Title"
