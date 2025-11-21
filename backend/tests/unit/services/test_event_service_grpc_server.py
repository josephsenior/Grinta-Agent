from __future__ import annotations

import asyncio
from typing import AsyncIterator, List, Optional

import pytest

from forge.services.event_service.grpc_server import (
    EventEnvelope,
    EventServiceGrpcServicer,
    PublishEventRequest,
    ReplayChunk,
    ReplayRequest,
    StartSessionRequest,
    SubscribeRequest,
    _from_proto_envelope,
    _to_proto_chunk,
    _to_proto_envelope,
)
from forge.services.event_service.service import SessionInfo
from forge.services.generated import event_service_pb2 as event_pb2


class FakeBackend:
    def __init__(self) -> None:
        self.start_request: Optional[StartSessionRequest] = None
        self.published: List[PublishEventRequest] = []
        self.subscribe_requests: List[SubscribeRequest] = []
        self.replay_requests: List[ReplayRequest] = []
        self.events: List[EventEnvelope] = []

    def start_session(self, request: StartSessionRequest) -> SessionInfo:
        self.start_request = request
        return SessionInfo(session_id="sess-123", labels={"env": "prod"})

    def publish_event(self, request: PublishEventRequest) -> None:
        self.published.append(request)

    async def subscribe(self, request: SubscribeRequest) -> AsyncIterator[EventEnvelope]:
        self.subscribe_requests.append(request)
        for event in self.events:
            yield event

    def replay(self, request: ReplayRequest) -> ReplayChunk:
        self.replay_requests.append(request)
        return ReplayChunk(events=self.events, next_cursor=42, has_more=True)


def make_envelope(session_id: str = "sess", payload: bytes = b"{}") -> EventEnvelope:
    return EventEnvelope(session_id=session_id, event_id=1, event_type="TYPE", payload=payload, metadata={"foo": "bar"})


def test_from_and_to_proto_envelope_round_trip() -> None:
    proto_envelope = event_pb2.EventEnvelope(
        session_id="sess",
        event_id=5,
        event_type="TYPE",
        payload=b"{}",
        trace_id="trace",
    )
    proto_envelope.metadata["foo"] = "bar"

    envelope = _from_proto_envelope(proto_envelope)
    assert envelope.event_id == 5
    assert envelope.metadata == {"foo": "bar"}

    rebuilt = _to_proto_envelope(envelope)
    assert rebuilt.session_id == "sess"
    assert rebuilt.metadata["foo"] == "bar"


def test_to_proto_chunk_includes_optional_cursor() -> None:
    chunk = ReplayChunk(events=[make_envelope()], next_cursor=99, has_more=True)
    proto = _to_proto_chunk(chunk)
    assert proto.has_more is True
    assert proto.next_cursor == 99
    assert len(proto.events) == 1


def test_start_session_bridges_request_fields() -> None:
    backend = FakeBackend()
    servicer = EventServiceGrpcServicer(backend)
    request = event_pb2.StartSessionRequest(session_id="", user_id="user", repository="repo", branch="")
    request.labels["env"] = "prod"

    response = servicer.StartSession(request, None)

    assert response.session_id == "sess-123"
    assert response.user_id == ""
    assert backend.start_request is not None
    assert backend.start_request.session_id is None
    assert backend.start_request.user_id == "user"
    assert backend.start_request.labels == {"env": "prod"}


def test_publish_event_converts_proto_to_backend() -> None:
    backend = FakeBackend()
    servicer = EventServiceGrpcServicer(backend)
    envelope = event_pb2.EventEnvelope(session_id="sess", event_type="TYPE", payload=b"{}")
    envelope.metadata["foo"] = "bar"
    request = event_pb2.PublishEventRequest(event=envelope)

    servicer.PublishEvent(request, None)

    assert len(backend.published) == 1
    published_env = backend.published[0].event
    assert published_env.metadata == {"foo": "bar"}


def test_subscribe_collects_async_events(monkeypatch: pytest.MonkeyPatch) -> None:
    backend = FakeBackend()
    backend.events = [
        make_envelope(payload=b'{"index": 1}'),
        make_envelope(payload=b'{"index": 2}'),
    ]

    def fake_run(coro):
        loop = asyncio.new_event_loop()
        try:
            return loop.run_until_complete(coro)
        finally:
            loop.close()

    monkeypatch.setattr(asyncio, "run", fake_run)

    servicer = EventServiceGrpcServicer(backend)
    request = event_pb2.SubscribeRequest(session_id="sess", event_types=["TYPE"])

    events = list(servicer.Subscribe(request, None))
    assert len(events) == 2
    assert backend.subscribe_requests[0].session_id == "sess"


def test_replay_returns_proto_chunk() -> None:
    backend = FakeBackend()
    backend.events = [make_envelope()]
    servicer = EventServiceGrpcServicer(backend)
    request = event_pb2.ReplayRequest(session_id="sess", from_cursor=0, limit=10)

    chunks = list(servicer.Replay(request, None))

    assert len(chunks) == 1
    chunk = chunks[0]
    assert chunk.has_more is True
    assert chunk.next_cursor == 42
    assert len(chunk.events) == 1
    assert backend.replay_requests[0].limit == 10

