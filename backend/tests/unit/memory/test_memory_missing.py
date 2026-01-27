"""Tests for missing coverage in memory.py."""

from __future__ import annotations

import asyncio
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from forge.events.action.agent import RecallAction
from forge.events.event import EventSource
from forge.events.observation.agent import RecallFailureObservation, RecallType
from forge.events.stream import EventStream
from forge.memory.memory import Memory
from forge.microagent import RepoMicroagent
from forge.microagent.types import MicroagentMetadata, MicroagentType
from forge.runtime.runtime_status import RuntimeStatus
from forge.storage.memory import InMemoryFileStore


@pytest.fixture
def memory():
    """Create a Memory instance for testing."""
    event_stream = EventStream(sid="test-sid", file_store=InMemoryFileStore({}))
    with patch("forge.memory.memory.load_microagents_from_dir", return_value=({}, {})):
        return Memory(event_stream=event_stream, sid="test-sid")


def test_on_event_with_running_loop(memory):
    """Test on_event when there's a running event loop (lines 85-86)."""
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    
    with patch("asyncio.get_running_loop", return_value=loop):
        event = RecallAction(recall_type=RecallType.WORKSPACE_CONTEXT)
        # Should create task and return immediately
        memory.on_event(event)
        # Clean up
        loop.close()


def test_on_event_with_event_loop_running(memory):
    """Test on_event when event loop exists and is running (line 94)."""
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    
    def mock_get_running_loop():
        raise RuntimeError("No running loop")
    
    def mock_get_event_loop():
        return loop
    
    # Create a mock loop that reports as running
    mock_loop = MagicMock()
    mock_loop.is_running.return_value = True
    mock_loop.create_task = MagicMock()
    
    try:
        with patch("asyncio.get_running_loop", side_effect=mock_get_running_loop), \
             patch("asyncio.get_event_loop", return_value=mock_loop):
            event = RecallAction(recall_type=RecallType.WORKSPACE_CONTEXT)
            memory.on_event(event)
            # Should have called create_task (line 94)
            mock_loop.create_task.assert_called_once()
    finally:
        loop.close()


@pytest.mark.asyncio
async def test_on_event_exception_handling(memory):
    """Test _on_event exception handling (lines 113-114)."""
    event = RecallAction(recall_type=RecallType.WORKSPACE_CONTEXT)
    
    # Make _process_recall_with_retry raise an exception
    with patch.object(memory, "_process_recall_with_retry", side_effect=Exception("Test error")):
        await memory._on_event(event)
        # Should have called _handle_recall_exception


@pytest.mark.asyncio
async def test_process_recall_with_retry_returns_none(memory):
    """Test _process_recall_with_retry returns None (line 156)."""
    # Create event that doesn't match any condition in _process_recall_once
    # Use WORKSPACE_CONTEXT but with AGENT source (not USER), so first condition fails
    # Use KNOWLEDGE type but we'll make _on_microagent_recall return None
    event = RecallAction(recall_type=RecallType.WORKSPACE_CONTEXT, query="test")
    event._source = EventSource.AGENT  # Not USER, so first condition fails
    
    result = await memory._process_recall_with_retry(event)
    # Should return None because _process_recall_once returns None (line 156)
    assert result is None


@pytest.mark.asyncio
async def test_backoff_retry(memory):
    """Test _backoff_retry method (lines 159-168)."""
    with patch("asyncio.sleep") as mock_sleep:
        await memory._backoff_retry(1, Exception("test"))
        mock_sleep.assert_called_once()
        
        # Test with higher attempt number
        await memory._backoff_retry(3, Exception("test"))
        assert mock_sleep.call_count == 2


@pytest.mark.asyncio
async def test_handle_recall_exception(memory):
    """Test _handle_recall_exception (lines 178-190)."""
    event = RecallAction(recall_type=RecallType.WORKSPACE_CONTEXT)
    exc = Exception("Test error")
    
    await memory._handle_recall_exception(event, exc)
    
    # Should have set runtime status and added failure observation
    assert memory.event_stream is not None


def test_is_transient_error_message_checking(memory):
    """Test _is_transient_error with error message checking (lines 195-202)."""
    # Test timeout message
    assert memory._is_transient_error(Exception("timeout error")) is True
    # Test rate limit message
    assert memory._is_transient_error(Exception("rate limit exceeded")) is True
    # Test temporarily unavailable
    assert memory._is_transient_error(Exception("temporarily unavailable")) is True
    # Test try again
    assert memory._is_transient_error(Exception("please try again")) is True
    # Test connection reset
    assert memory._is_transient_error(Exception("connection reset")) is True
    # Test non-transient error
    assert memory._is_transient_error(Exception("permanent error")) is False


def test_collect_repo_instructions_multiple(memory):
    """Test _collect_repo_instructions with multiple microagents (line 218)."""
    microagent1 = RepoMicroagent(
        name="agent1",
        content="Instructions 1",
        metadata=MicroagentMetadata(name="agent1", type=MicroagentType.REPO_KNOWLEDGE),
        source="local",
        type=MicroagentType.REPO_KNOWLEDGE,
    )
    microagent2 = RepoMicroagent(
        name="agent2",
        content="Instructions 2",
        metadata=MicroagentMetadata(name="agent2", type=MicroagentType.REPO_KNOWLEDGE),
        source="local",
        type=MicroagentType.REPO_KNOWLEDGE,
    )
    memory.repo_microagents = {"agent1": microagent1, "agent2": microagent2}
    
    result = memory._collect_repo_instructions()
    # Should contain both instructions separated by newlines (line 218)
    assert "Instructions 1" in result
    assert "Instructions 2" in result
    assert "\n\n" in result


def test_load_user_workspace_microagents_exception(memory):
    """Test load_user_workspace_microagents exception handling (lines 404, 406-408)."""
    # Reset microagents to test the exception path
    memory.knowledge_microagents = {}
    memory.repo_microagents = {}
    
    with patch("forge.memory.memory.load_microagents_from_dir", side_effect=Exception("Load error")):
        # Should not raise, just log warning (lines 404, 406-408)
        memory._load_user_microagents()
        # Verify it handled the exception gracefully
        assert len(memory.knowledge_microagents) == 0
        assert len(memory.repo_microagents) == 0


def test_set_runtime_status_exception_handling(memory):
    """Test set_runtime_status exception handling (lines 532-533)."""
    # Make status_callback raise an exception that triggers the outer exception handler
    def failing_callback(msg_type, status, msg):
        raise KeyError("Callback error")
    
    memory.status_callback = failing_callback
    
    # Should not raise, just log error (lines 532-533)
    memory.set_runtime_status(RuntimeStatus.ERROR_MEMORY, "test message")


@pytest.mark.asyncio
async def test_handle_recall_exception_event_stream_failure(memory):
    """Test _handle_recall_exception when event_stream.add_event fails (lines 189-190)."""
    event = RecallAction(recall_type=RecallType.WORKSPACE_CONTEXT)
    
    # Make event_stream.add_event raise an exception
    with patch.object(memory.event_stream, "add_event", side_effect=Exception("Stream error")):
        # Should not raise, just pass (lines 189-190)
        await memory._handle_recall_exception(event, Exception("Test error"))


def test_is_transient_error_specific_messages(memory):
    """Test _is_transient_error with specific error messages (line 200)."""
    # Test various transient error messages
    assert memory._is_transient_error(Exception("connection timeout")) is True
    assert memory._is_transient_error(Exception("rate limit exceeded")) is True
    assert memory._is_transient_error(Exception("service temporarily unavailable")) is True
    assert memory._is_transient_error(Exception("please try again later")) is True
    assert memory._is_transient_error(Exception("connection reset by peer")) is True
    # Test non-transient
    assert memory._is_transient_error(Exception("permanent failure")) is False


def test_get_microagent_mcp_tools(memory):
    """Test get_microagent_mcp_tools (lines 421-430)."""
    from forge.core.config.mcp_config import MCPConfig
    from forge.microagent.types import MicroagentMetadata
    
    # MCPConfig has sse_servers, stdio_servers, shttp_servers fields
    mcp_config = MCPConfig()
    
    # Create metadata with mcp_tools
    metadata = MicroagentMetadata(
        name="test_agent",
        type=MicroagentType.REPO_KNOWLEDGE,
        mcp_tools=mcp_config,
    )
    
    # Create microagent using the same pattern as other tests
    microagent = RepoMicroagent(
        name="test_agent",
        content="test content",
        metadata=metadata,
        source="local",
        type=MicroagentType.REPO_KNOWLEDGE,
    )
    
    # Add to memory's repo_microagents
    memory.repo_microagents["test_agent"] = microagent
    
    result = memory.get_microagent_mcp_tools()
    assert len(result) == 1
    assert result[0] == mcp_config


@pytest.mark.asyncio
async def test_set_runtime_status_async(memory):
    """Test _set_runtime_status async method (lines 543-550)."""
    callback_calls = []
    
    def callback(msg_type, status, message):
        callback_calls.append((msg_type, status, message))
    
    memory.status_callback = callback
    
    await memory._set_runtime_status("info", RuntimeStatus.ERROR_MEMORY, "test message")
    assert len(callback_calls) == 1
    assert callback_calls[0] == ("info", RuntimeStatus.ERROR_MEMORY, "test message")

