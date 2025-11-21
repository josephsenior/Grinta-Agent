"""Tests for the auto-generate title functionality."""

from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from pydantic import SecretStr
from typing import cast

from forge.core.config import LLMConfig
from forge.core.config.forge_config import ForgeConfig
from forge.events.action import MessageAction
from forge.events.event import EventSource
from forge.events.event_store import EventStore
from forge.llm.llm_registry import LLMRegistry
from forge.server.conversation_manager.standalone_conversation_manager import (
    StandaloneConversationManager,
)
from forge.server.monitoring import MonitoringListener
from forge.storage.data_models.settings import Settings
from forge.storage.memory import InMemoryFileStore
from forge.utils.conversation_summary import (
    _try_llm_title_generation,
    auto_generate_title,
    generate_conversation_title,
    get_default_conversation_title,
)


@pytest.mark.asyncio
async def test_auto_generate_title_with_llm():
    """Test auto-generating a title using LLM."""
    file_store = InMemoryFileStore()
    llm_registry = MagicMock(spec=LLMRegistry)
    conversation_id = "test-conversation"
    user_id = "test-user"
    user_message = MessageAction(
        content="Help me write a Python script to analyze data"
    )
    user_message._source = EventSource.USER
    user_message._id = 1
    user_message._timestamp = datetime.now(timezone.utc).isoformat()
    with patch("forge.utils.conversation_summary.EventStore") as mock_event_store_cls:
        mock_event_store = MagicMock(spec=EventStore)
        mock_event_store.search_events.return_value = [user_message]
        mock_event_store_cls.return_value = mock_event_store
        llm_registry.request_extraneous_completion.return_value = (
            "Python Data Analysis Script"
        )
        settings = Settings(
            llm_model="test-model",
            llm_api_key=SecretStr("test-key"),
            llm_base_url="test-url",
        )
        title = await auto_generate_title(
            conversation_id, user_id, file_store, settings, llm_registry
        )
        assert title == "Python Data Analysis Script"
        mock_event_store_cls.assert_called_once_with(
            conversation_id, file_store, user_id
        )
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
        settings = Settings(
            llm_model="test-model",
            llm_api_key=SecretStr("test-key"),
            llm_base_url="test-url",
        )
        title = await auto_generate_title(
            conversation_id, user_id, file_store, settings, llm_registry
        )
        assert title == "This is a very long message th..."
        assert len(title) <= 35
        mock_event_store_cls.assert_called_once_with(
            conversation_id, file_store, user_id
        )


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
        settings = Settings(
            llm_model="test-model",
            llm_api_key=SecretStr("test-key"),
            llm_base_url="test-url",
        )
        title = await auto_generate_title(
            conversation_id, user_id, file_store, settings, llm_registry
        )
        assert title == ""
        mock_event_store_cls.assert_called_once_with(
            conversation_id, file_store, user_id
        )


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
    settings = Settings(
        llm_model="test-model",
        llm_api_key=SecretStr("test-key"),
        llm_base_url="test-url",
    )
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
    with patch.object(
        manager,
        "_get_conversation_store",
        AsyncMock(return_value=mock_conversation_store),
    ):
        with patch(
            "forge.server.conversation_manager.standalone_conversation_manager.auto_generate_title",
            AsyncMock(return_value="Generated Title"),
        ):
            await manager._update_conversation_for_event(
                user_id, conversation_id, settings, llm_registry
            )
        assert mock_metadata.title == "Generated Title"
        sio.emit.assert_called_once()
        call_args = sio.emit.call_args[0]
        assert call_args[0] == "oh_event"
        assert call_args[1]["status_update"] is True
        assert call_args[1]["type"] == "info"
        assert call_args[1]["message"] == conversation_id
        assert call_args[1]["conversation_title"] == "Generated Title"


@pytest.mark.asyncio
async def test_generate_conversation_title_blank_message():
    llm_registry = MagicMock(spec=LLMRegistry)
    llm_config = LLMConfig(model="test-model")
    assert await generate_conversation_title("   ", llm_config, llm_registry) is None


@pytest.mark.asyncio
async def test_generate_conversation_title_truncates(monkeypatch):
    llm_registry = MagicMock(spec=LLMRegistry)
    llm_registry.request_extraneous_completion.return_value = "x" * 40
    long_message = "A" * 1100
    llm_config = LLMConfig(model="test-model")
    result = await generate_conversation_title(
        long_message, llm_config, llm_registry, max_length=10
    )
    assert result == "x" * 7 + "..."
    args = llm_registry.request_extraneous_completion.call_args[0]
    assert "conversation_title_creator" == args[0]
    user_prompt = args[2][1]["content"]
    assert "(truncated)" in user_prompt


@pytest.mark.asyncio
async def test_generate_conversation_title_handles_exception():
    llm_registry = MagicMock(spec=LLMRegistry)
    llm_registry.request_extraneous_completion.side_effect = RuntimeError("boom")
    llm_config = LLMConfig(model="test-model")
    assert await generate_conversation_title("hello", llm_config, llm_registry) is None


@pytest.mark.asyncio
async def test_auto_generate_title_handles_internal_errors(monkeypatch):
    file_store = InMemoryFileStore()
    llm_registry = MagicMock(spec=LLMRegistry)
    settings = Settings(llm_model="model", llm_api_key=SecretStr("key"))
    monkeypatch.setattr(
        "forge.utils.conversation_summary._get_first_user_message",
        MagicMock(side_effect=RuntimeError("boom")),
    )
    title = await auto_generate_title(
        "conversation", "user", file_store, settings, llm_registry
    )
    assert title == ""


def test_get_default_conversation_title():
    assert get_default_conversation_title("abcdef12345").startswith("Conversation ")
    assert get_default_conversation_title("abcdef12345").endswith("abcde")


@pytest.mark.asyncio
async def test_try_llm_title_generation_without_model():
    assert (
        await _try_llm_title_generation(
            "msg", cast(Settings, None), MagicMock(spec=LLMRegistry)
        )
        is None
    )
    settings = Settings(llm_model=None, llm_api_key=None)
    assert (
        await _try_llm_title_generation("msg", settings, MagicMock(spec=LLMRegistry))
        is None
    )


@pytest.mark.asyncio
async def test_try_llm_title_generation_handles_exception(monkeypatch):
    settings = Settings(llm_model="model", llm_api_key=SecretStr("key"))
    llm_registry = MagicMock(spec=LLMRegistry)

    async def fake_generate(message, llm_config, registry):
        raise RuntimeError("boom")

    monkeypatch.setattr(
        "forge.utils.conversation_summary.generate_conversation_title",
        fake_generate,
    )
    assert await _try_llm_title_generation("msg", settings, llm_registry) is None
