"""Contract tests for EventServiceAdapter."""

from __future__ import annotations

import json
import uuid
from unittest.mock import MagicMock

import pytest

from forge.events.action import MessageAction
from forge.events.event import EventSource
from forge.events.serialization.event import event_to_dict
from forge.services.adapters.event_adapter import EventServiceAdapter
from forge.services.generated import event_service_pb2 as event_pb2


@pytest.fixture
def mock_file_store():
    """Mock FileStore factory."""
    mock_store = MagicMock()
    mock_factory = MagicMock(return_value=mock_store)
    return mock_factory


@pytest.fixture
def event_adapter(mock_file_store):
    """Create EventServiceAdapter instance."""
    return EventServiceAdapter(mock_file_store, use_grpc=False)


def test_start_session(event_adapter, mock_file_store):
    """Test starting a new session."""
    session_info = event_adapter.start_session(
        user_id="test-user",
        repository="test-repo",
        branch="main",
        labels={"env": "test"},
    )
    assert "session_id" in session_info
    assert session_info["user_id"] == "test-user"
    assert session_info["repository"] == "test-repo"
    assert session_info["branch"] == "main"
    assert session_info["labels"] == {"env": "test"}


def test_get_event_stream(event_adapter):
    """Test getting EventStream instance."""
    session_info = event_adapter.start_session()
    session_id = session_info["session_id"]
    # Then get the stream
    stream = event_adapter.get_event_stream(session_id)
    assert stream is not None


def test_get_event_stream_grpc_mode(mock_file_store):
    """Test that EventStream access fails in gRPC mode."""
    adapter = EventServiceAdapter(mock_file_store, use_grpc=True)
    with pytest.raises(RuntimeError, match="EventStream access not available in gRPC mode"):
        adapter.get_event_stream("test-session")


def test_publish_event(event_adapter):
    """Test publishing an event."""
    session_info = event_adapter.start_session()
    session_id = session_info["session_id"]
    action = MessageAction(content="hello world")
    action.source = EventSource.USER
    event_dict = event_to_dict(action)
    # Should not raise
    event_adapter.publish_event(session_id, event_dict)


def test_publish_event_grpc_mode(mock_file_store):
    """Test publishing via gRPC path."""
    adapter = EventServiceAdapter(
        mock_file_store,
        use_grpc=True,
        grpc_endpoint="localhost:50051",
    )
    stub = MagicMock()
    stub.PublishEvent.return_value = None
    stub.StartSession.return_value = event_pb2.SessionInfo(session_id="abc")
    adapter._require_grpc_stub = MagicMock(return_value=stub)  # type: ignore[attr-defined]
    adapter.publish_event("session-123", {"id": 1, "action": {"type": "test"}})
    stub.PublishEvent.assert_called_once()


def test_start_session_with_explicit_id(event_adapter):
    """Start session with explicit ID and verify session metadata."""
    session_id = "session-explicit"
    session_info = event_adapter.start_session(session_id=session_id, user_id="user-123")
    assert session_info["session_id"] == session_id
    stored_info = event_adapter.get_session_info(session_id)
    assert stored_info["session_id"] == session_id
    assert stored_info["user_id"] == "user-123"


def test_start_session_grpc_mode(mock_file_store):
    """Start session through gRPC stub."""
    adapter = EventServiceAdapter(
        mock_file_store,
        use_grpc=True,
        grpc_endpoint="localhost:50051",
    )
    stub = MagicMock()
    stub.StartSession.return_value = event_pb2.SessionInfo(
        session_id="session-explicit",
        user_id="user-456",
        repository="repo",
        branch="main",
    )
    adapter._require_grpc_stub = MagicMock(return_value=stub)  # type: ignore[attr-defined]

    result = adapter.start_session(
        session_id="session-explicit",
        user_id="user-456",
        repository="repo",
        branch="main",
        labels={"env": "test"},
    )

    stub.StartSession.assert_called_once()
    assert result["session_id"] == "session-explicit"
    assert result["user_id"] == "user-456"

