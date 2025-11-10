import asyncio
import json
import threading
from typing import Any, Iterable

import httpx
import pytest

from forge.events.action.message import MessageAction
from forge.events.async_event_store_wrapper import AsyncEventStoreWrapper
from forge.events.event import EventSource
from forge.events.event_filter import EventFilter
from forge.events.event_store import EventStore, _CachePage
from forge.events.event_store_abc import EventStoreABC
from forge.events.nested_event_store import NestedEventStore
from forge.events.serialization.event import event_from_dict, event_to_dict
from forge.events.stream import EventStream, EventStreamSubscriber, session_exists
from forge.events.tool import ToolCallMetadata
from forge.llm.metrics import Metrics


class FakeFileStore:
    """In-memory file store used to simulate persistent storage."""

    def __init__(self):
        self.storage: dict[str, str] = {}

    def write(self, path: str, content: str) -> None:
        self.storage[path] = content

    def read(self, path: str) -> str:
        if path not in self.storage:
            raise FileNotFoundError(path)
        return self.storage[path]

    def list(self, directory: str) -> list[str]:
        entries = []
        for path in self.storage:
            if path.startswith(directory):
                entries.append(path[len(directory) :])
        if not entries:
            raise FileNotFoundError(directory)
        return entries


def _create_message_event(content: str, source: EventSource, event_id: int) -> dict[str, Any]:
    action = MessageAction(content=content)
    action._id = event_id
    action._sequence = event_id
    action._timestamp = f"2024-01-0{event_id}T00:00:00"
    action._source = source
    return event_to_dict(action)


def test_cache_page_helpers_cover_basic_paths():
    action = MessageAction(content="cached")
    action._id = 1
    data = event_to_dict(action)
    page = _CachePage(events=[data], start=1, end=2)
    assert page.covers(1) is True
    assert page.covers(2) is False
    retrieved = page.get_event(1)
    assert isinstance(retrieved, MessageAction)

    dummy_page = _CachePage(None, 1, -1)
    assert dummy_page.get_event(1) is None


def test_event_store_reads_and_filters_events(tmp_path):
    file_store = FakeFileStore()
    store = EventStore("sid", file_store, user_id=None, cache_size=2)

    # Populate persistent storage with two events
    for idx, source in enumerate([EventSource.AGENT, EventSource.USER]):
        data = _create_message_event(f"event{idx}", source, idx)
        filename = store._get_filename_for_id(idx, user_id=None)
        file_store.write(filename, json.dumps(data))

    # cache page to speed future lookups
    cache_filename = store._get_filename_for_cache(0, 2)
    cache_events = [_create_message_event("event0", EventSource.AGENT, 0), _create_message_event("event1", EventSource.USER, 1)]
    file_store.write(cache_filename, json.dumps(cache_events))

    events = list(store.search_events())
    assert len(events) == 2
    assert store.get_latest_event_id() == 1
    assert store.get_latest_event().message == "event1"

    filtered = list(store.filtered_events_by_source(EventSource.AGENT))
    assert len(filtered) == 1
    assert filtered[0].message == "event0"

    ids = [store._get_id_from_filename("invalid"), store._get_id_from_filename("sessions/sid/events/3.json")]
    assert ids == [-1, 3]


def test_event_filter_supports_queries_and_dates():
    event = MessageAction(content="Hello World", image_urls=[])
    event._source = EventSource.AGENT
    event._timestamp = "2024-01-01T00:00:00"

    filt = EventFilter(query="world", source="agent")
    assert filt.include(event) is True

    filt = EventFilter(include_types=(MessageAction,), exclude_hidden=True)
    event.hidden = True
    assert filt.include(event) is False

    filt = EventFilter(start_date="2025-01-01T00:00:00")
    assert filt.include(event) is False


@pytest.mark.asyncio
async def test_async_event_store_wrapper_iterates_events():
    file_store = FakeFileStore()
    store = EventStore("sid", file_store, user_id=None)
    data = _create_message_event("async", EventSource.AGENT, 0)
    file_store.write(store._get_filename_for_id(0, None), json.dumps(data))

    wrapper = AsyncEventStoreWrapper(store)
    results = []
    async for event in wrapper:
        results.append(event.message)
    assert results == ["async"]


def test_nested_event_store_fetches_and_filters(monkeypatch):
    events = [
        _create_message_event("remote0", EventSource.AGENT, 0),
        _create_message_event("remote1", EventSource.USER, 1),
    ]
    responses = [
        {"events": events, "has_more": False},
    ]

    def fake_get(url: str, headers: dict | None = None):
        assert "start_id=" in url
        content = responses.pop(0) if responses else {"events": [], "has_more": False}
        return httpx.Response(200, json=content)

    monkeypatch.setattr(httpx, "get", fake_get)
    nested = NestedEventStore(base_url="http://example", sid="sid", user_id=None)
    fetched = list(nested.search_events(limit=10))
    assert len(fetched) == 2
    assert fetched[0].message == "remote0"

    responses.extend([{"events": events[:1], "has_more": False}])
    monkeypatch.setattr(httpx, "get", fake_get)
    latest = nested.get_latest_event()
    assert latest.message == "remote0"

    responses.extend([{"events": [], "has_more": False}])
    monkeypatch.setattr(httpx, "get", fake_get)
    with pytest.raises(FileNotFoundError):
        nested.get_event(99)


def test_nested_event_store_helper_logic(monkeypatch):
    nested = NestedEventStore(base_url="http://example", sid="sid", user_id=None)
    params = nested._build_search_params(5, 10, True, 150)
    assert params["reverse"] is True and params["limit"] == 100 and params["end_id"] == 10

    responses = [
        {"events": [_create_message_event("reverse", EventSource.AGENT, 3)], "has_more": False},
    ]
    recorded = []

    def fake_request(search_params):
        recorded.append(search_params)
        return responses.pop(0) if responses else {"events": [], "has_more": False}

    monkeypatch.setattr(nested, "_make_api_request", fake_request)
    fetched = list(nested.search_events(start_id=3, end_id=2, reverse=True, limit=5))
    assert fetched[0].message == "reverse"
    assert recorded[0]["reverse"] is True

    # limit countdown path should not stop immediately when limit > 1
    event = event_from_dict(_create_message_event("limit", EventSource.AGENT, 5))
    should_yield, should_stop = nested._process_event(event, end_id=None, filter=None, limit=2)
    assert should_yield is True and should_stop is False

    # `_make_api_request` returning None yields no events
    monkeypatch.setattr(
        nested,
        "_make_api_request",
        lambda search_params: None,
    )
    assert list(nested.search_events()) == []

    # `_update_cursors` forward progression branch
    start_cursor, end_cursor = nested._update_cursors(False, None, 7, 2)
    assert start_cursor == 7 and end_cursor is None

    # Filter exclusion path
    filt = EventFilter(query="missing")
    should_yield, should_stop = nested._process_event(event, end_id=None, filter=filt, limit=2)
    assert should_yield is False and should_stop is False


def test_nested_event_store_headers_and_error_paths(monkeypatch):
    captured_headers = {}

    def fake_get(url: str, headers: dict | None = None):
        captured_headers["headers"] = headers
        return httpx.Response(404)

    monkeypatch.setattr(httpx, "get", fake_get)
    nested = NestedEventStore(base_url="http://example", sid="sid", user_id=None, session_api_key="api-key")
    assert nested._make_api_request({"start_id": 0}) is None
    assert captured_headers["headers"]["X-Session-API-Key"] == "api-key"

    monkeypatch.setattr(
        nested,
        "_make_api_request",
        lambda params: {"events": [], "has_more": False},
    )
    with pytest.raises(FileNotFoundError):
        nested.get_latest_event()

    monkeypatch.setattr(
        nested,
        "_make_api_request",
        lambda params: {"events": [_create_message_event("latest", EventSource.AGENT, 9)], "has_more": False},
    )
    assert nested.get_latest_event_id() == 9


def test_event_stream_adds_event_and_notifies_subscriber(monkeypatch):
    file_store = FakeFileStore()
    stream = EventStream("sid", file_store, user_id=None)
    stream.cache_size = 2  # small cache for test

    received = []
    event_ready = threading.Event()

    def callback(event):
        received.append(event.message)
        event_ready.set()

    stream.subscribe(EventStreamSubscriber.TEST, callback, "cb1")
    stream.set_secrets({"token": "SECRET"})

    action = MessageAction(content="token SECRET should hide")
    stream.add_event(action, EventSource.USER)

    event_ready.wait(timeout=2)
    stream.close()

    assert received, "Expected callback to run"
    stored_files = [path for path in file_store.storage if path.endswith(".json")]
    assert stored_files, "Event json should be written"
    saved_json = json.loads(file_store.storage[stored_files[0]])
    assert "<secret_hidden>" in saved_json["args"]["content"]


def test_event_stream_secret_replacement_and_unsubscribe(monkeypatch):
    file_store = FakeFileStore()
    stream = EventStream("sid", file_store, user_id=None)
    stream.cache_size = 1

    stream.subscribe(EventStreamSubscriber.TEST, lambda event: None, "cb1")
    stream.unsubscribe(EventStreamSubscriber.TEST, "cb1")
    stream.unsubscribe(EventStreamSubscriber.TEST, "cb1")  # warn path
    stream.unsubscribe(EventStreamSubscriber.SERVER, "missing")
    stream._cleanup_thread_loop(EventStreamSubscriber.TEST, "missing")
    stream._cleanup_thread_pool(EventStreamSubscriber.TEST, "missing")

    stream.set_secrets({"token": "A"})
    stream.update_secrets({"other": "B"})
    nested = stream._replace_secrets({"data": {"value": "B"}}, is_top_level=False)
    assert nested["data"]["value"] == "<secret_hidden>"

    action = MessageAction(content="token A")
    stream.add_event(action, EventSource.AGENT)
    stream.close()

    cache_files = [path for path in file_store.storage if "event_cache" in path]
    assert cache_files, "Expected cache page to be written when page size reached"


def test_event_stream_error_handler_logs_error(monkeypatch):
    file_store = FakeFileStore()
    stream = EventStream("sid", file_store, user_id=None)
    stream.cache_size = 2

    triggered = threading.Event()

    def bad_callback(event):
        triggered.set()
        raise RuntimeError("boom")

    errors = []
    monkeypatch.setattr("forge.events.stream.logger.error", lambda *args, **kwargs: errors.append(args[0]))

    stream.subscribe(EventStreamSubscriber.TEST, bad_callback, "cb1")
    stream.add_event(MessageAction(content="hi"), EventSource.AGENT)
    triggered.wait(timeout=2)
    stream.close()

    assert errors, "Expected error handler to log callback exception"


def test_event_store_abc_helpers_cover_deprecated_paths():
    class StubStore(EventStoreABC):
        def __init__(self, events):
            self._events = events

        def search_events(self, *args, **kwargs) -> Iterable:
            return iter(self._events)

        def get_event(self, id: int):
            return self._events[id]

        def get_latest_event(self):
            return self._events[-1]

        def get_latest_event_id(self):
            return len(self._events) - 1

    events = [_create_message_event("e0", EventSource.AGENT, 0)]
    stub = StubStore([event_from_dict(events[0])])
    collected = list(stub.get_events())
    assert len(collected) == 1

    by_source = list(stub.filtered_events_by_source(EventSource.AGENT))
    assert by_source

    matches = stub.get_matching_events(query="e0", limit=1)
    assert len(matches) == 1

    with pytest.raises(ValueError):
        stub.get_matching_events(limit=0)

    with pytest.raises(ValueError):
        stub.get_matching_events(limit=101)


def test_session_exists_checks_storage(monkeypatch):
    file_store = FakeFileStore()
    file_store.write("sessions/sid/events/0.json", "{}")
    assert asyncio.run(session_exists("sid", file_store))

    def raising_list(*args, **kwargs):
        raise FileNotFoundError

    monkeypatch.setattr(file_store, "list", raising_list)
    assert asyncio.run(session_exists("sid2", file_store)) is False

