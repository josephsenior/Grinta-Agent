"""Tests for the conversation summary generator."""

from unittest.mock import MagicMock
import pytest
from openhands.core.config import LLMConfig
from openhands.utils.conversation_summary import generate_conversation_title


@pytest.mark.asyncio
async def test_generate_conversation_title_empty_message():
    """Test that an empty message returns None."""
    mock_llm_registry = MagicMock()
    mock_llm_config = LLMConfig(model="test-model")
    result = await generate_conversation_title("", mock_llm_config, mock_llm_registry)
    assert result is None
    result = await generate_conversation_title("   ", mock_llm_config, mock_llm_registry)
    assert result is None


@pytest.mark.asyncio
async def test_generate_conversation_title_success():
    """Test successful title generation."""
    mock_llm_registry = MagicMock()
    mock_llm_registry.request_extraneous_completion.return_value = "Generated Title"
    mock_llm_config = LLMConfig(model="test-model")
    result = await generate_conversation_title("Can you help me with Python?", mock_llm_config, mock_llm_registry)
    assert result == "Generated Title"
    mock_llm_registry.request_extraneous_completion.assert_called_once()


@pytest.mark.asyncio
async def test_generate_conversation_title_long_title():
    """Test that long titles are truncated."""
    mock_llm_registry = MagicMock()
    mock_llm_registry.request_extraneous_completion.return_value = (
        "This is a very long title that should be truncated because it exceeds the maximum length"
    )
    mock_llm_config = LLMConfig(model="test-model")
    result = await generate_conversation_title(
        "Can you help me with Python?", mock_llm_config, mock_llm_registry, max_length=30
    )
    assert len(result) <= 30
    assert result.endswith("...")


@pytest.mark.asyncio
async def test_generate_conversation_title_exception():
    """Test that exceptions are handled gracefully."""
    mock_llm_registry = MagicMock()
    mock_llm_registry.request_extraneous_completion.side_effect = Exception("Test error")
    mock_llm_config = LLMConfig(model="test-model")
    result = await generate_conversation_title("Can you help me with Python?", mock_llm_config, mock_llm_registry)
    assert result is None
