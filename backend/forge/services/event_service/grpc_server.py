"""gRPC servicer implementation for the EventService."""

from __future__ import annotations

import asyncio
from typing import Iterable

from google.protobuf import empty_pb2

from forge.services.event_service.service import (
    EventEnvelope,
    EventServiceServer,
    PublishEventRequest,
    ReplayChunk,
    ReplayRequest,
    StartSessionRequest,
    SubscribeRequest,
)
from forge.services.generated import event_service_pb2 as event_pb2
from forge.services.generated import event_service_pb2_grpc as event_grpc


class EventServiceGrpcServicer(event_grpc.EventServiceServicer):
    """Bridge gRPC requests to the in-process EventServiceServer."""

    def __init__(self, backend: EventServiceServer) -> None:
        self._backend = backend

    def StartSession(
        self, request: event_pb2.StartSessionRequest, context
    ) -> event_pb2.SessionInfo:  # type: ignore[override]
        info = self._backend.start_session(
            StartSessionRequest(
                session_id=request.session_id or None,
                user_id=request.user_id or None,
                repository=request.repository or None,
                branch=request.branch or None,
                labels=dict(request.labels),
            )
        )
        return event_pb2.SessionInfo(
            session_id=info.session_id,
            user_id=info.user_id or "",
            repository=info.repository or "",
            branch=info.branch or "",
            labels=info.labels,
        )

    def PublishEvent(
        self, request: event_pb2.PublishEventRequest, context
    ):  # type: ignore[override]
        envelope = _from_proto_envelope(request.event)
        self._backend.publish_event(PublishEventRequest(event=envelope))
        return empty_pb2.Empty()

    def Subscribe(
        self, request: event_pb2.SubscribeRequest, context
    ) -> Iterable[event_pb2.EventEnvelope]:  # type: ignore[override]
        backend_req = SubscribeRequest(
            session_id=request.session_id,
            event_types=list(request.event_types),
            cursor=request.cursor or None,
        )

        async def _collect():
            events = []
            async for ev in self._backend.subscribe(backend_req):
                events.append(ev)
            return events

        for event in asyncio.run(_collect()):
            yield _to_proto_envelope(event)

    def Replay(
        self, request: event_pb2.ReplayRequest, context
    ) -> Iterable[event_pb2.ReplayChunk]:  # type: ignore[override]
        backend_req = ReplayRequest(
            session_id=request.session_id,
            from_cursor=request.from_cursor,
            limit=request.limit or 100,
        )
        chunk = self._backend.replay(backend_req)
        yield _to_proto_chunk(chunk)


def _from_proto_envelope(proto: event_pb2.EventEnvelope) -> EventEnvelope:
    metadata = dict(proto.metadata)
    return EventEnvelope(
        session_id=proto.session_id,
        event_id=int(proto.event_id) if proto.event_id else None,
        event_type=proto.event_type,
        payload=proto.payload,
        trace_id=proto.trace_id or None,
        metadata=metadata,
    )


def _to_proto_envelope(envelope: EventEnvelope) -> event_pb2.EventEnvelope:
    proto = event_pb2.EventEnvelope(
        session_id=envelope.session_id,
        event_type=envelope.event_type,
        payload=envelope.payload,
    )
    if envelope.event_id is not None:
        proto.event_id = envelope.event_id
    if envelope.trace_id:
        proto.trace_id = envelope.trace_id
    proto.metadata.update(envelope.metadata)
    return proto


def _to_proto_chunk(chunk: ReplayChunk) -> event_pb2.ReplayChunk:
    proto = event_pb2.ReplayChunk(has_more=chunk.has_more)
    proto.events.extend(_to_proto_envelope(ev) for ev in chunk.events)
    if chunk.next_cursor is not None:
        proto.next_cursor = int(chunk.next_cursor)
    return proto

