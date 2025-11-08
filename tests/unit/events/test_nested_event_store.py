"""Unit tests for the NestedEventStore class.

These tests focus on the search_events method, which retrieves events from a remote API
and applies filtering based on various criteria.
"""

from typing import Any
from unittest.mock import MagicMock, patch
import pytest
from forge.events.action import MessageAction
from forge.events.event import EventSource
from forge.events.event_filter import EventFilter
from forge.events.nested_event_store import NestedEventStore


def create_mock_event(id: int, content: str, source: str = "user", hidden: bool = False) -> dict[str, Any]:
    """Create a properly formatted mock event dictionary."""
    event_dict = {"id": id, "action": "message", "args": {"content": content}, "source": source}
    if hidden:
        event_dict["hidden"] = True
    return event_dict


def create_mock_response(events: list[dict[str, Any]], has_more: bool = False) -> MagicMock:
    """Helper function to create a mock HTTP response."""
    mock_response = MagicMock()
    mock_response.json.return_value = {"events": events, "has_more": has_more}
    return mock_response


class TestNestedEventStore:
    """Tests for the NestedEventStore class."""

    @pytest.fixture
    def event_store(self):
        """Create a NestedEventStore instance for testing."""
        return NestedEventStore(
            base_url="http://test-api.example.com",
            sid="test-session",
            user_id="test-user",
            session_api_key="test-api-key",
        )

    @patch("httpx.get")
    def test_search_events_basic(self, mock_get, event_store):
        """Test basic event retrieval without filters."""
        mock_events = [create_mock_event(1, "Hello", "user"), create_mock_event(2, "World", "agent")]
        mock_get.return_value = create_mock_response(mock_events)
        events = list(event_store.search_events())
        assert len(events) == 2
        assert events[0].id == 1
        assert events[1].id == 2
        mock_get.assert_called_once_with(
            "http://test-api.example.com/events?start_id=0&reverse=False", headers={"X-Session-API-Key": "test-api-key"}
        )

    @patch("httpx.get")
    def test_search_events_with_limit(self, mock_get, event_store):
        """Test event retrieval with a limit."""
        mock_events = [create_mock_event(1, "Hello", "user"), create_mock_event(2, "World", "agent")]
        mock_get.return_value = create_mock_response(mock_events)
        events = list(event_store.search_events(limit=1))
        assert len(events) == 1
        assert events[0].id == 1
        mock_get.assert_called_once_with(
            "http://test-api.example.com/events?start_id=0&reverse=False&limit=1",
            headers={"X-Session-API-Key": "test-api-key"},
        )

    @patch("httpx.get")
    def test_search_events_with_start_id(self, mock_get, event_store):
        """Test event retrieval with a specific start_id."""
        mock_events = [create_mock_event(5, "Hello", "user"), create_mock_event(6, "World", "agent")]
        mock_get.return_value = create_mock_response(mock_events)
        events = list(event_store.search_events(start_id=5))
        assert len(events) == 2
        assert events[0].id == 5
        assert events[1].id == 6
        mock_get.assert_called_once_with(
            "http://test-api.example.com/events?start_id=5&reverse=False", headers={"X-Session-API-Key": "test-api-key"}
        )

    @patch("httpx.get")
    def test_search_events_reverse_order(self, mock_get, event_store):
        """Test event retrieval in reverse order."""
        mock_events = [create_mock_event(3, "World", "agent"), create_mock_event(2, "Hello", "user")]
        mock_get.return_value = create_mock_response(mock_events)
        events = list(event_store.search_events(reverse=True))
        assert len(events) == 2
        assert events[0].id == 3
        assert events[1].id == 2
        mock_get.assert_called_once_with(
            "http://test-api.example.com/events?start_id=0&reverse=True", headers={"X-Session-API-Key": "test-api-key"}
        )

    @patch("httpx.get")
    def test_search_events_with_end_id(self, mock_get, event_store):
        """Test event retrieval with a specific end_id."""
        mock_events = [
            create_mock_event(1, "Hello", "user"),
            create_mock_event(2, "World", "agent"),
            create_mock_event(3, "End", "user"),
        ]
        mock_get.return_value = create_mock_response(mock_events)
        events = list(event_store.search_events(end_id=3))
        assert len(events) == 3
        assert events[0].id == 1
        assert events[1].id == 2
        assert events[2].id == 3
        mock_get.assert_called_once_with(
            "http://test-api.example.com/events?start_id=0&reverse=False", headers={"X-Session-API-Key": "test-api-key"}
        )

    @patch("httpx.get")
    @patch("forge.events.event_filter.EventFilter.exclude")
    def test_search_events_with_filter(self, mock_exclude, mock_get, event_store):
        """Test event retrieval with an EventFilter."""
        mock_events = [
            create_mock_event(1, "Hello", "user"),
            create_mock_event(2, "World", "agent"),
            create_mock_event(3, "Hidden", "user"),
        ]
        mock_get.return_value = create_mock_response(mock_events)
        mock_exclude.side_effect = [False, False, True]
        event_filter = EventFilter()
        events = list(event_store.search_events(filter=event_filter))
        assert len(events) == 2
        assert events[0].id == 1
        assert events[1].id == 2
        mock_get.assert_called_once_with(
            "http://test-api.example.com/events?start_id=0&reverse=False", headers={"X-Session-API-Key": "test-api-key"}
        )

    @patch("httpx.get")
    def test_search_events_with_source_filter(self, mock_get, event_store):
        """Test event retrieval with a source filter."""
        mock_events = [
            create_mock_event(1, "Hello", "user"),
            create_mock_event(2, "World", "agent"),
            create_mock_event(3, "Another", "user"),
        ]
        mock_get.return_value = create_mock_response(mock_events)
        event_filter = EventFilter(source="user")
        events = list(event_store.search_events(filter=event_filter))
        assert len(events) == 2
        assert events[0].id == 1
        assert events[0].source == EventSource.USER
        assert events[1].id == 3
        assert events[1].source == EventSource.USER
        mock_get.assert_called_once_with(
            "http://test-api.example.com/events?start_id=0&reverse=False", headers={"X-Session-API-Key": "test-api-key"}
        )

    @patch("httpx.get")
    def test_search_events_with_type_filter(self, mock_get, event_store):
        """Test event retrieval with a type filter."""
        mock_events = [
            create_mock_event(1, "Hello", "user"),
            {"id": 2, "action": "read", "args": {"path": "/test/file.txt"}, "source": "agent"},
            create_mock_event(3, "Another", "user"),
        ]
        mock_get.return_value = create_mock_response(mock_events)
        event_filter = EventFilter(include_types=(MessageAction,))
        events = list(event_store.search_events(filter=event_filter))
        assert len(events) == 2
        assert events[0].id == 1
        assert events[1].id == 3
        mock_get.assert_called_once_with(
            "http://test-api.example.com/events?start_id=0&reverse=False", headers={"X-Session-API-Key": "test-api-key"}
        )

    @patch("httpx.get")
    def test_search_events_pagination(self, mock_get, event_store):
        """Test event retrieval with pagination (has_more=True)."""
        first_page_events = [create_mock_event(1, "Hello", "user"), create_mock_event(2, "World", "agent")]
        first_response = create_mock_response(first_page_events, has_more=True)
        second_page_events = [create_mock_event(3, "More", "user"), create_mock_event(4, "Data", "agent")]
        second_response = create_mock_response(second_page_events, has_more=False)
        mock_get.side_effect = [first_response, second_response]
        events = list(event_store.search_events())
        assert len(events) == 4
        assert events[0].id == 1
        assert events[1].id == 2
        assert events[2].id == 3
        assert events[3].id == 4
        assert mock_get.call_count == 2
        mock_get.assert_any_call(
            "http://test-api.example.com/events?start_id=0&reverse=False", headers={"X-Session-API-Key": "test-api-key"}
        )
        mock_get.assert_any_call(
            "http://test-api.example.com/events?start_id=3&reverse=False", headers={"X-Session-API-Key": "test-api-key"}
        )

    @patch("httpx.get")
    def test_search_events_no_session_api_key(self, mock_get):
        """Test event retrieval without a session API key."""
        event_store = NestedEventStore(base_url="http://test-api.example.com", sid="test-session", user_id="test-user")
        mock_events = [create_mock_event(1, "Hello", "user")]
        mock_get.return_value = create_mock_response(mock_events)
        events = list(event_store.search_events())
        assert len(events) == 1
        mock_get.assert_called_once_with("http://test-api.example.com/events?start_id=0&reverse=False", headers={})

    @patch("httpx.get")
    def test_search_events_with_query_filter(self, mock_get, event_store):
        """Test event retrieval with a text query filter."""
        mock_events = [
            create_mock_event(1, "Hello world", "user"),
            create_mock_event(2, "Python is great", "agent"),
            create_mock_event(3, "Hello Python", "user"),
        ]
        mock_get.return_value = create_mock_response(mock_events)
        event_filter = EventFilter(query="Python")
        events = list(event_store.search_events(filter=event_filter))
        assert len(events) == 2
        assert events[0].id == 2
        assert events[1].id == 3
        mock_get.assert_called_once_with(
            "http://test-api.example.com/events?start_id=0&reverse=False", headers={"X-Session-API-Key": "test-api-key"}
        )

    @patch("httpx.get")
    def test_search_events_reverse_pagination_multiple_pages(self, mock_get, event_store):
        """Ensure reverse pagination works across multiple server pages.

        We emulate the remote /events endpoint by using an in-memory EventStream as the
        backing store and having httpx.get return paginated JSON responses derived from it.
        """
        from urllib.parse import parse_qs, urlparse
        from forge.events.event import EventSource
        from forge.events.observation import NullObservation
        from forge.events.serialization.event import event_to_dict
        from forge.events.stream import EventStream
        from forge.storage.memory import InMemoryFileStore

        fs = InMemoryFileStore()
        server_stream = EventStream("test-session", fs, user_id="test-user")
        total_events = 50
        for i in range(total_events):
            server_stream.add_event(NullObservation(f"e{i}"), EventSource.AGENT)

        def server_side_get(url: str, headers: dict | None = None):
            parsed = urlparse(url)
            qs = parse_qs(parsed.query)
            start_id = int(qs.get("start_id", ["0"])[0])
            reverse = qs.get("reverse", ["False"])[0] == "True"
            end_id = int(qs["end_id"][0]) if "end_id" in qs else None
            limit = int(qs.get("limit", ["20"])[0])
            events = list(
                server_stream.search_events(start_id=start_id, end_id=end_id, reverse=reverse, limit=limit + 1)
            )
            has_more = len(events) > limit
            if has_more:
                events = events[:limit]
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.json.return_value = {"events": [event_to_dict(e) for e in events], "has_more": has_more}
            return mock_response

        mock_get.side_effect = server_side_get
        results = list(event_store.search_events(reverse=True))
        assert len(results) == total_events
        assert [e.id for e in results] == list(range(total_events - 1, -1, -1))
        assert mock_get.call_count >= 2
