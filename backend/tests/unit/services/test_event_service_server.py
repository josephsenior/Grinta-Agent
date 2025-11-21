from __future__ import annotations

import asyncio
import json
from types import SimpleNamespace
from typing import Any, Iterable

import pytest

from forge.events.event import EventSource
from forge.services.event_service import service as event_service


class DummyFileStore:
    pass


class FakeStream:
    def __init__(self, session_id: str, file_store: Any, user_id: str | None) -> None:
        self.session_id = session_id
        self.file_store = file_store
        self.user_id = user_id
        self.added_events: list[tuple[Any, EventSource]] = []
        self.subscribers: dict[str, Any] = {}
        self.cur_id = 0
        self._search_events: Iterable[Any] = []

    def add_event(self, event: Any, source: EventSource) -> None:
        self.added_events.append((event, source))
        self.cur_id += 1

    def subscribe(self, subscriber, callback, callback_id):
        self.subscribers[callback_id] = callback

    def unsubscribe(self, subscriber, callback_id):
        self.subscribers.pop(callback_id, None)

    def emit(self, event: Any):
        for callback in list(self.subscribers.values()):
            callback(event)

    def search_events(self, start_id: int, limit: int):
        return self._search_events


@pytest.fixture(autouse=True)
def no_metrics(monkeypatch):
    monkeypatch.setattr(event_service, "_record_rpc_metrics", lambda *args, **kwargs: None)


def make_server(monkeypatch, stream: FakeStream | None = None):
    created_streams = {}

    def fake_event_stream(session_id, file_store, user_id):
        if stream is not None:
            created_streams[session_id] = stream
            return stream
        fake = FakeStream(session_id, file_store, user_id)
        created_streams[session_id] = fake
        return fake

    monkeypatch.setattr(event_service, "EventStream", fake_event_stream)
    server = event_service.EventServiceServer(lambda _: DummyFileStore())
    return server, created_streams


def test_start_session_creates_stream(monkeypatch):
    server, created = make_server(monkeypatch)
    info = server.start_session(event_service.StartSessionRequest(user_id="user", labels={"env": "prod"}))

    assert info.user_id == "user"
    assert info.labels == {"env": "prod"}
    assert info.session_id in created


def test_start_session_reuses_existing_session(monkeypatch):
    server, created = make_server(monkeypatch)
    info1 = server.start_session(event_service.StartSessionRequest(session_id="sess", user_id="user"))
    info2 = server.start_session(event_service.StartSessionRequest(session_id="sess"))
    assert info1.session_id == info2.session_id
    assert created["sess"]


def test_publish_event_adds_to_stream(monkeypatch):
    fake_stream = FakeStream("sess", DummyFileStore(), "user")
    server, created = make_server(monkeypatch, stream=fake_stream)
    server._streams["sess"] = fake_stream

    sample_event = {"source": "agent", "id": 1, "action": {"type": "CMD"}}
    monkeypatch.setattr(event_service, "event_from_dict", lambda data: SimpleNamespace(source=data.get("source")))
    monkeypatch.setattr(event_service, "event_to_dict", lambda event: sample_event)

    envelope = event_service.EventEnvelope(session_id="sess", event_id=1, event_type="cmd", payload=json.dumps(sample_event).encode(), metadata={})
    server.publish_event(event_service.PublishEventRequest(event=envelope))

    assert fake_stream.added_events
    event, source = fake_stream.added_events[0]
    assert source == EventSource.AGENT


@pytest.mark.asyncio
async def test_subscribe_yields_filtered_events(monkeypatch):
    fake_stream = FakeStream("sess", DummyFileStore(), None)
    server, _ = make_server(monkeypatch, stream=fake_stream)
    server._streams["sess"] = fake_stream

    event_payload = {"id": 1, "action": {"type": "CMD"}}
    fake_event = SimpleNamespace()
    monkeypatch.setattr(event_service, "event_to_dict", lambda ev: event_payload)
    monkeypatch.setattr(event_service, "EventStreamSubscriber", SimpleNamespace(SERVER="srv"))

    async def consume():
        agen = server.subscribe(event_service.SubscribeRequest(session_id="sess", event_types=["CMD"]))
        fake_stream.emit(fake_event)
        fake_stream.emit(fake_event)
        result = await agen.__anext__()
        return result

    envelope = await consume()
    assert envelope.event_type == "CMD"


def test_replay_returns_chunk(monkeypatch):
    fake_stream = FakeStream("sess", DummyFileStore(), None)
    event_payload = {"id": 1, "action": {"type": "CMD"}}
    fake_event = SimpleNamespace()
    fake_stream._search_events = [fake_event]
    monkeypatch.setattr(event_service, "event_to_dict", lambda ev: event_payload)
    server, _ = make_server(monkeypatch, stream=fake_stream)
    server._streams["sess"] = fake_stream

    chunk = server.replay(event_service.ReplayRequest(session_id="sess", from_cursor=0, limit=10))
    assert list(chunk.events)[0].event_type == "CMD"
    assert chunk.next_cursor is None or chunk.next_cursor >= 0

