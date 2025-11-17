from __future__ import annotations

import asyncio
import json
import threading
import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, AsyncIterator, Callable, Dict, Iterable, Optional, TYPE_CHECKING

from forge.events.event import EventSource
from forge.events.serialization.event import event_from_dict, event_to_dict
from forge.events.stream import EventStream, EventStreamSubscriber
from forge.storage.files import FileStore

if TYPE_CHECKING:
    from prometheus_client import Counter as PromCounter
    from prometheus_client import Histogram as PromHistogram
else:  # pragma: no cover - typing fallback
    PromCounter = PromHistogram = Any

_prometheus_client: Any | None
try:  # pragma: no cover - optional dependency
    import prometheus_client as _prometheus_client
except Exception:  # pragma: no cover
    _prometheus_client = None


_METRICS_REGISTERED = False
_EVENT_RPC_TOTAL: PromCounter | None = None
_EVENT_RPC_FAILURES: PromCounter | None = None
_EVENT_RPC_DURATION: PromHistogram | None = None

if _prometheus_client is not None and not _METRICS_REGISTERED:  # pragma: no cover - simple registration
    try:
        _EVENT_RPC_TOTAL = _prometheus_client.Counter(
            "metasop_eventservice_rpc_total",
            "Total EventService RPC invocations",
            labelnames=("rpc",),
        )
        _EVENT_RPC_FAILURES = _prometheus_client.Counter(
            "metasop_eventservice_rpc_failures_total",
            "Failed EventService RPC invocations",
            labelnames=("rpc",),
        )
        _EVENT_RPC_DURATION = _prometheus_client.Histogram(
            "metasop_eventservice_rpc_duration_seconds",
            "EventService RPC latency in seconds",
            labelnames=("rpc",),
            buckets=(0.05, 0.1, 0.25, 0.5, 1, 2.5, 5, 10, float("inf")),
        )
        _METRICS_REGISTERED = True
    except Exception:
        # In test environments, metrics might already be registered; disable to avoid import-time errors
        _EVENT_RPC_TOTAL = _EVENT_RPC_FAILURES = _EVENT_RPC_DURATION = None


def _record_rpc_metrics(rpc: str, success: bool, duration: float) -> None:
    if (
        _EVENT_RPC_TOTAL is None
        or _EVENT_RPC_FAILURES is None
        or _EVENT_RPC_DURATION is None
    ):
        return
    _EVENT_RPC_TOTAL.labels(rpc=rpc).inc()
    if not success:
        _EVENT_RPC_FAILURES.labels(rpc=rpc).inc()
    _EVENT_RPC_DURATION.labels(rpc=rpc).observe(duration)


@dataclass
class SessionInfo:
    """Lightweight mirror of the gRPC SessionInfo message."""

    session_id: str
    user_id: Optional[str] = None
    repository: Optional[str] = None
    branch: Optional[str] = None
    labels: Dict[str, str] = field(default_factory=dict)


@dataclass
class StartSessionRequest:
    session_id: Optional[str] = None
    user_id: Optional[str] = None
    repository: Optional[str] = None
    branch: Optional[str] = None
    labels: Dict[str, str] = field(default_factory=dict)


@dataclass
class EventEnvelope:
    session_id: str
    event_id: Optional[int]
    event_type: str
    payload: bytes
    trace_id: Optional[str] = None
    metadata: Dict[str, str] = field(default_factory=dict)


@dataclass
class PublishEventRequest:
    event: EventEnvelope


@dataclass
class SubscribeRequest:
    session_id: str
    event_types: Iterable[str] = ()
    cursor: Optional[int] = None


@dataclass
class ReplayRequest:
    session_id: str
    from_cursor: int = 0
    limit: int = 100


@dataclass
class ReplayChunk:
    events: Iterable[EventEnvelope]
    next_cursor: Optional[int]
    has_more: bool


class EventServiceServer:
    """In-process implementation of the EventService contract."""

    def __init__(
        self,
        file_store_factory: Callable[[Optional[str]], FileStore],
    ) -> None:
        self._file_store_factory = file_store_factory
        self._streams: Dict[str, EventStream] = {}
        self._session_metadata: Dict[str, SessionInfo] = {}
        self._lock = threading.Lock()

    # ------------------------------------------------------------------
    # Session management
    # ------------------------------------------------------------------
    def start_session(self, request: StartSessionRequest) -> SessionInfo:
        start = time.perf_counter()
        success = False
        try:
            session_id = request.session_id or str(uuid.uuid4())
            file_store = self._file_store_factory(request.user_id)

            with self._lock:
                if session_id in self._streams:
                    info = self._session_metadata.get(session_id)
                    if info is None:
                        info = SessionInfo(
                            session_id=session_id,
                            user_id=request.user_id,
                            repository=request.repository,
                            branch=request.branch,
                            labels=dict(request.labels),
                        )
                        self._session_metadata[session_id] = info
                    success = True
                    return info

                stream = EventStream(session_id, file_store, request.user_id)
                self._streams[session_id] = stream
                info = SessionInfo(
                    session_id=session_id,
                    user_id=request.user_id,
                    repository=request.repository,
                    branch=request.branch,
                    labels=dict(request.labels),
                )
                self._session_metadata[session_id] = info
                success = True
                return info
        finally:
            duration = time.perf_counter() - start
            _record_rpc_metrics("StartSession", success, duration)

    # ------------------------------------------------------------------
    # Publish / Subscribe
    # ------------------------------------------------------------------
    def publish_event(self, request: PublishEventRequest) -> None:
        start = time.perf_counter()
        success = False
        try:
            envelope = request.event
            stream = self._get_stream(envelope.session_id)

            event_dict = json.loads(envelope.payload.decode("utf-8"))
            event = event_from_dict(event_dict)
            source = getattr(event, "source", None)
            if not isinstance(source, EventSource):
                try:
                    source = EventSource(str(source))
                except Exception:
                    source = EventSource.ENVIRONMENT
            stream.add_event(event, source)
            success = True
        finally:
            duration = time.perf_counter() - start
            _record_rpc_metrics("PublishEvent", success, duration)

    async def subscribe(self, request: SubscribeRequest) -> AsyncIterator[EventEnvelope]:
        stream = self._get_stream(request.session_id)
        queue: asyncio.Queue[EventEnvelope] = asyncio.Queue()
        callback_id = str(uuid.uuid4())

        def _on_event(event) -> None:
            event_env = self._to_envelope(event, request.session_id)
            queue.put_nowait(event_env)

        stream.subscribe(
            EventStreamSubscriber.SERVER,
            _on_event,
            callback_id,
        )

        try:
            while True:
                envelope = await queue.get()
                if request.event_types and envelope.event_type not in request.event_types:
                    continue
                yield envelope
        finally:
            stream.unsubscribe(EventStreamSubscriber.SERVER, callback_id)

    # ------------------------------------------------------------------
    # Replay
    # ------------------------------------------------------------------
    def replay(self, request: ReplayRequest) -> ReplayChunk:
        start = time.perf_counter()
        success = False
        try:
            stream = self._get_stream(request.session_id)
            events = []
            next_cursor = request.from_cursor

            for idx, event in enumerate(
                stream.search_events(start_id=request.from_cursor, limit=request.limit)
            ):
                events.append(self._to_envelope(event, request.session_id))
                next_cursor = request.from_cursor + idx + 1

            has_more = next_cursor < stream.cur_id
            success = True
            return ReplayChunk(
                events=events,
                next_cursor=next_cursor if has_more else None,
                has_more=has_more,
            )
        finally:
            duration = time.perf_counter() - start
            _record_rpc_metrics("Replay", success, duration)

    # ------------------------------------------------------------------
    # Utilities
    # ------------------------------------------------------------------
    def _get_stream(self, session_id: str) -> EventStream:
        with self._lock:
            if session_id not in self._streams:
                raise KeyError(f"Unknown session_id: {session_id}")
            return self._streams[session_id]

    def get_session_info(self, session_id: str) -> SessionInfo:
        with self._lock:
            info = self._session_metadata.get(session_id)
            if info is None:
                raise KeyError(f"Unknown session_id: {session_id}")
            return info

    @staticmethod
    def _to_envelope(event, session_id: str) -> EventEnvelope:
        data = event_to_dict(event)
        payload = json.dumps(data).encode("utf-8")
        event_type = EventServiceServer._extract_event_type(data)
        trace_id = data.get("trace_id") or data.get("metadata", {}).get("trace_id")
        metadata = {
            "source": data.get("source", ""),
            "sequence": str(data.get("sequence", "")),
        }
        return EventEnvelope(
            session_id=session_id,
            event_id=data.get("id"),
            event_type=event_type,
            payload=payload,
            trace_id=trace_id,
            metadata=metadata,
        )

    @staticmethod
    def _extract_event_type(event_dict: dict[str, Any]) -> str:
        action_field = event_dict.get("action")
        if isinstance(action_field, dict):
            event_type = action_field.get("type")
            if event_type:
                return str(event_type)
        if isinstance(action_field, Enum):
            return str(action_field.value)
        if isinstance(action_field, str):
            return action_field

        observation_field = event_dict.get("observation")
        if isinstance(observation_field, dict):
            event_type = observation_field.get("type")
            if event_type:
                return str(event_type)
        if isinstance(observation_field, Enum):
            return str(observation_field.value)
        if isinstance(observation_field, str):
            return observation_field

        return "unknown"
