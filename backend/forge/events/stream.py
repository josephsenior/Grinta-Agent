"""Event stream implementation with pub/sub and persistence helpers.

Backpressure: Implements a bounded queue with configurable drop/slow-path policy
to prevent unbounded memory growth under load.
"""

from __future__ import annotations

import asyncio
import inspect
import os
import re
import threading
import weakref
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from enum import Enum
from typing import TYPE_CHECKING, Any, Callable, ClassVar, cast

from forge.core.logger import forge_logger as logger
from forge.events.durable_writer import DurableEventWriter, PersistedEvent
from forge.events.event import Event, EventSource
from forge.events.event_store import EventStore
from forge.events.serialization.event import event_from_dict, event_to_dict
from forge.io import json
from forge.storage.locations import get_conversation_dir
from forge.utils.async_utils import call_sync_from_async
from forge.utils.shutdown_listener import should_continue

if TYPE_CHECKING:
    from forge.storage import FileStore


class EventStreamSubscriber(str, Enum):
    """Lightweight wrapper attaching callbacks to event stream broadcast queue."""

    AGENT_CONTROLLER = "agent_controller"
    RESOLVER = "FORGE_resolver"
    SERVER = "server"
    RUNTIME = "runtime"
    MEMORY = "memory"
    MAIN = "main"
    TEST = "test"


async def session_exists(
    sid: str, file_store: FileStore, user_id: str | None = None
) -> bool:
    """Check if a session exists in file storage.

    Args:
        sid: Session ID to check
        file_store: File storage backend
        user_id: Optional user ID for scoping

    Returns:
        True if session directory exists

    """
    try:
        await call_sync_from_async(file_store.list, get_conversation_dir(sid, user_id))
        return True
    except FileNotFoundError:
        return False


class EventStream(EventStore):
    """Thread-safe event stream with pub/sub functionality.

    Extends EventStore with subscriber management and async event delivery.
    Events are queued and dispatched to subscribers in background threads
    with dedicated event loops for each callback.
    """

    secrets: dict[str, str]
    _subscribers: dict[str, dict[str, Callable]]
    _lock: threading.Lock
    _async_queue: asyncio.Queue[Event | object] | None
    _queue_thread: threading.Thread
    _queue_loop: asyncio.AbstractEventLoop | None
    _delivery_pool: ThreadPoolExecutor
    _workers: list[asyncio.Task[Any]]
    _stop_event: asyncio.Event | None
    _queue_ready: threading.Event
    _worker_count: int
    _stop_sentinel: object
    _write_page_cache: list[dict]
    _max_queue_size: int
    _drop_policy: str
    _hwm_ratio: float
    _block_timeout: float
    _stats: dict[str, int]
    # Global weak registry for metrics aggregation
    _GLOBAL_STREAMS: ClassVar[weakref.WeakSet["EventStream"]] = weakref.WeakSet()

    def __init__(
        self, sid: str, file_store: FileStore, user_id: str | None = None
    ) -> None:
        """Initialize event stream with subscriber management.

        Args:
            sid: Session ID for this event stream
            file_store: File storage backend for persisting events
            user_id: Optional user ID for scoping

        """
        super().__init__(sid, file_store, user_id)
        self._stop_flag = threading.Event()
        # Backpressure configuration (env-based to avoid broad config wiring)
        self._max_queue_size = int(os.getenv("FORGE_EVENTSTREAM_MAX_QUEUE", "2000"))
        self._drop_policy = os.getenv("FORGE_EVENTSTREAM_POLICY", "drop_oldest").lower()
        if self._drop_policy not in {"drop_oldest", "drop_newest", "block"}:
            self._drop_policy = "drop_oldest"
        self._hwm_ratio = max(
            0.1, min(0.99, float(os.getenv("FORGE_EVENTSTREAM_HWM_RATIO", "0.8")))
        )
        self._block_timeout = float(os.getenv("FORGE_EVENTSTREAM_BLOCK_TIMEOUT", "0.1"))
        self._stats = {
            "enqueued": 0,
            "dropped_oldest": 0,
            "dropped_newest": 0,
            "high_watermark_hits": 0,
        }
        self._queue_loop: asyncio.AbstractEventLoop | None = None
        self._async_queue: asyncio.Queue[Event | object] | None = None
        self._queue_size = 0
        self._queue_ready = threading.Event()
        self._worker_count = max(
            1, int(os.getenv("FORGE_EVENTSTREAM_WORKERS", "8"))
        )
        self._delivery_pool = ThreadPoolExecutor(max_workers=self._worker_count)
        self._workers: list[asyncio.Task[Any]] = []
        self._stop_event: asyncio.Event | None = None
        self._stop_sentinel = object()
        self._queue_thread = threading.Thread(target=self._run_queue_loop, daemon=True)
        self._queue_thread.start()
        self._subscribers = {}
        self._lock = threading.Lock()
        self.secrets: dict[str, str] = {}
        self._activity_listeners: dict[str, Callable[[str], None]] = {}
        self._activity_listener_lock = threading.RLock()
        self._activity_listener_seq = 0
        self._secret_pattern: re.Pattern[str] | None = None
        self._secret_bytes: list[bytes] = []
        self._write_page_cache = []
        self._async_persistence_enabled = (
            os.getenv("FORGE_EVENTSTREAM_ASYNC_WRITE", "false").lower()
            in ("1", "true", "yes")
        )
        self._durable_writer: DurableEventWriter | None = None
        if self._async_persistence_enabled:
            try:
                self._durable_writer = DurableEventWriter(self.file_store)
                self._durable_writer.start()
            except Exception as exc:  # pragma: no cover - safety fallback
                logger.warning(
                    "Failed to start DurableEventWriter, falling back to sync persistence: %s",
                    exc,
                )
                self._durable_writer = None
        # Register this instance for global metrics aggregation
        try:  # pragma: no cover - defensive
            EventStream._GLOBAL_STREAMS.add(self)
        except Exception:
            pass

    def close(self) -> None:
        """Close event stream, stopping queue processing and cleaning up subscribers."""
        self._stop_flag.set()
        if self._queue_loop and self._stop_event:
            future = asyncio.run_coroutine_threadsafe(
                self._initiate_shutdown(), self._queue_loop
            )
            try:
                future.result(timeout=5)
            except Exception as exc:  # pragma: no cover - defensive
                logger.debug("Error shutting down event queue: %s", exc)
        if self._queue_thread.is_alive():
            self._queue_thread.join()
        self._subscribers.clear()
        if self._durable_writer:
            self._durable_writer.stop()

    def _clean_up_subscriber(self, subscriber_id: str, callback_id: str) -> None:
        """Clean up a specific subscriber callback."""
        if subscriber_id not in self._subscribers:
            logger.warning("Subscriber not found during cleanup: %s", subscriber_id)
            return
        if callback_id not in self._subscribers[subscriber_id]:
            logger.warning("Callback not found during cleanup: %s", callback_id)
            return

        del self._subscribers[subscriber_id][callback_id]
        if not self._subscribers[subscriber_id]:
            del self._subscribers[subscriber_id]

    def subscribe(
        self,
        subscriber_id: EventStreamSubscriber,
        callback: Callable[[Event], None],
        callback_id: str,
    ) -> None:
        """Subscribe to event stream with a callback function.

        Args:
            subscriber_id: Unique subscriber identifier
            callback: Function to call for each event
            callback_id: Unique callback identifier within subscriber

        Raises:
            ValueError: If callback_id already exists for this subscriber

        """
        if subscriber_id not in self._subscribers:
            self._subscribers[subscriber_id] = {}
        if callback_id in self._subscribers[subscriber_id]:
            msg = f"Callback ID on subscriber {subscriber_id} already exists: {callback_id}"
            raise ValueError(msg)
        self._subscribers[subscriber_id][callback_id] = callback

    def unsubscribe(
        self, subscriber_id: EventStreamSubscriber, callback_id: str
    ) -> None:
        """Unsubscribe callback from event stream and clean up resources.

        Args:
            subscriber_id: Subscriber identifier
            callback_id: Callback identifier to remove

        """
        if subscriber_id not in self._subscribers:
            logger.warning("Subscriber not found during unsubscribe: %s", subscriber_id)
            return
        if callback_id not in self._subscribers[subscriber_id]:
            logger.warning("Callback not found during unsubscribe: %s", callback_id)
            return
        self._clean_up_subscriber(subscriber_id, callback_id)

    def add_event(self, event: Event, source: EventSource) -> None:
        """Add event to stream with automatic ID assignment and persistence."""
        if self._should_drop_due_to_shutdown(event, source):
            return

        self._ensure_event_can_be_added(event)
        event.timestamp = datetime.now()
        event.source = source

        sanitized_event, payload, cache_page_data = self._serialize_and_cache_event(
            event
        )
        cache_payload = self._build_cache_payload(cache_page_data)

        if sanitized_event.id is not None:
            self._persist_event(payload, sanitized_event.id, cache_payload)

        self._enqueue_serialized_event(sanitized_event)
        self._notify_activity_listeners()

    def _should_drop_due_to_shutdown(
        self, event: Event, source: EventSource
    ) -> bool:
        if not self._stop_flag.is_set():
            return False
        logger.debug(
            "EventStream closed; dropping event id=%s from source=%s",
            getattr(event, "id", None),
            source,
        )
        return True

    def _ensure_event_can_be_added(self, event: Event) -> None:
        evt_id = getattr(event, "id", Event.INVALID_ID)
        if not isinstance(evt_id, int):
            evt_id = Event.INVALID_ID
        if evt_id != Event.INVALID_ID:
            msg = (
                f"Event already has an ID:{evt_id}. It was probably added back to the "
                "EventStream from inside a handler, triggering a loop."
            )
            raise ValueError(msg)

    def _serialize_and_cache_event(
        self, event: Event
    ) -> tuple[Event, dict[str, Any], list[dict[str, Any]] | None]:
        from forge.events.action import (  # local import to avoid global cycle
            ChangeAgentStateAction,
        )

        cache_page_data: list[dict[str, Any]] | None = None
        with self._lock:
            event.id = self.cur_id
            event.sequence = self.cur_id
            self.cur_id += 1

            data = self._replace_secrets(event_to_dict(event))
            sanitized_event = event_from_dict(data)

            if isinstance(sanitized_event, ChangeAgentStateAction):
                logger.debug(
                    "Queued ChangeAgentStateAction id=%s state=%s source=%s",
                    sanitized_event.id,
                    getattr(sanitized_event, "agent_state", None),
                    sanitized_event.source,
                )

            current_write_page = self._write_page_cache
            current_write_page.append(data)
            if len(current_write_page) == self.cache_size:
                cache_page_data = current_write_page
                self._write_page_cache = []

        return sanitized_event, data, cache_page_data

    def _enqueue_serialized_event(self, event: Event) -> None:
        if not self._queue_ready.wait(timeout=2):
            logger.warning("EventStream queue not ready; dropping event id=%s", event.id)
            return

        if not self._queue_loop or not self._async_queue:
            logger.warning(
                "EventStream queue loop missing; dropping event id=%s", event.id
            )
            return

        try:
            future = asyncio.run_coroutine_threadsafe(
                self._enqueue_event(event), self._queue_loop
            )
            future.result()
        except Exception as exc:  # pragma: no cover - defensive
            logger.warning("Failed to enqueue event id=%s: %s", event.id, exc)

    def get_stats(self) -> dict[str, int]:
        """Return snapshot of backpressure stats for monitoring/tests."""
        out = dict(self._stats)
        out["queue_size"] = self._queue_size
        return out

    def add_activity_listener(self, callback: Callable[[str], None]) -> str:
        """Register a callback invoked whenever a new event is added."""
        with self._activity_listener_lock:
            handle = f"listener-{self._activity_listener_seq}"
            self._activity_listener_seq += 1
            self._activity_listeners[handle] = callback
            return handle

    def remove_activity_listener(self, handle: str) -> None:
        with self._activity_listener_lock:
            self._activity_listeners.pop(handle, None)

    def _notify_activity_listeners(self) -> None:
        with self._activity_listener_lock:
            listeners = list(self._activity_listeners.values())
        for callback in listeners:
            try:
                callback(self.sid)
            except Exception as exc:
                logger.debug("Activity listener raised: %s", exc)

    def _build_cache_payload(
        self, current_write_page: list[dict] | None
    ) -> tuple[str, str] | None:
        """Return cache filename + contents when a page is ready."""
        if not current_write_page or len(current_write_page) < self.cache_size:
            return None
        start = current_write_page[0]["id"]
        end = start + self.cache_size
        contents = json.dumps(current_write_page)
        cache_filename = self._get_filename_for_cache(start, end)
        return cache_filename, contents

    def _persist_event(
        self,
        payload: dict[str, Any],
        event_id: int,
        cache_payload: tuple[str, str] | None,
    ) -> None:
        filename = self._get_filename_for_id(event_id, self.user_id)
        writer = self._durable_writer
        if writer:
            persisted = PersistedEvent(
                event_id=event_id,
                payload=payload,
                filename=filename,
                cache_filename=cache_payload[0] if cache_payload else None,
                cache_contents=cache_payload[1] if cache_payload else None,
            )
            if writer.enqueue(persisted):
                return

        self._write_event_sync(filename, payload, cache_payload)

    def _write_event_sync(
        self,
        filename: str,
        payload: dict[str, Any],
        cache_payload: tuple[str, str] | None,
    ) -> None:
        event_json = json.dumps(payload)
        if len(event_json) > 1000000:
            logger.warning(
                "Saving event JSON over 1MB: %s bytes, filename: %s",
                len(event_json),
                filename,
                extra={
                    "user_id": self.user_id,
                    "session_id": self.sid,
                    "size": len(event_json),
                },
            )
        self.file_store.write(filename, event_json)
        if cache_payload:
            cache_filename, cache_contents = cache_payload
            self.file_store.write(cache_filename, cache_contents)

    def set_secrets(self, secrets: dict[str, str]) -> None:
        """Set secrets dictionary for masking sensitive values in events.

        Args:
            secrets: Dictionary of secrets to mask

        """
        self.secrets = secrets.copy()
        self._rebuild_secret_cache()

    def update_secrets(self, secrets: dict[str, str]) -> None:
        """Update secrets dictionary with additional values.

        Args:
            secrets: Additional secrets to add

        """
        self.secrets.update(secrets)
        self._rebuild_secret_cache()

    def _rebuild_secret_cache(self) -> None:
        """Precompile patterns for fast masking."""
        tokens = [
            str(secret)
            for secret in self.secrets.values()
            if isinstance(secret, str) and secret
        ]
        unique_tokens = sorted(set(tokens), key=len, reverse=True)
        if unique_tokens:
            pattern = "|".join(re.escape(token) for token in unique_tokens)
            self._secret_pattern = re.compile(pattern, flags=re.IGNORECASE)
            self._secret_bytes = [token.encode("utf-8") for token in unique_tokens]
        else:
            self._secret_pattern = None
            self._secret_bytes = []

    def _replace_secrets(
        self, data: dict[str, Any], is_top_level: bool = True
    ) -> dict[str, Any]:
        """Recursively replace secret values in event data with masked placeholder.

        Protects top-level event fields from masking to preserve event structure.

        Args:
            data: Event data dictionary
            is_top_level: Whether this is the top-level call

        Returns:
            Data with secrets replaced

        """
        TOP_LEVEL_PROTECTED_FIELDS = {
            "timestamp",
            "id",
            "source",
            "cause",
            "action",
            "observation",
            "message",
        }
        for key in list(data.keys()):
            if is_top_level and key in TOP_LEVEL_PROTECTED_FIELDS:
                continue
            data[key] = self._sanitize_value(data[key])
        return data

    def _sanitize_value(self, value: Any) -> Any:
        if isinstance(value, dict):
            return self._replace_secrets(value, is_top_level=False)
        if isinstance(value, list):
            return [self._sanitize_value(item) for item in value]
        if isinstance(value, tuple):
            return tuple(self._sanitize_value(item) for item in value)
        if isinstance(value, str):
            return self._mask_string(value)
        if isinstance(value, bytes):
            return self._mask_bytes(value)
        return value

    def _mask_string(self, value: str) -> str:
        if not value or not self._secret_pattern:
            return value
        return self._secret_pattern.sub("<secret_hidden>", value)

    def _mask_bytes(self, value: bytes) -> bytes:
        if not value or not self._secret_bytes:
            return value
        masked = value
        for token in self._secret_bytes:
            if token:
                masked = masked.replace(token, b"<secret_hidden>")
        return masked

    def _run_queue_loop(self) -> None:
        """Start event loop in queue processing thread."""
        self._queue_loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self._queue_loop)
        self._async_queue = asyncio.Queue(maxsize=self._max_queue_size)
        self._stop_event = asyncio.Event()
        self._workers = [
            self._queue_loop.create_task(self._worker_loop(worker_id))
            for worker_id in range(self._worker_count)
        ]
        self._queue_ready.set()
        try:
            self._queue_loop.run_until_complete(self._stop_event.wait())
        finally:
            for worker in self._workers:
                worker.cancel()
            self._queue_loop.run_until_complete(
                asyncio.gather(*self._workers, return_exceptions=True)
            )
            self._delivery_pool.shutdown(wait=True)
            self._queue_loop.close()

    async def _worker_loop(self, worker_id: int) -> None:
        """Consume events from the queue and dispatch them to subscribers."""
        if not self._async_queue:
            return
        queue = self._async_queue
        while should_continue() and not self._stop_flag.is_set():
            try:
                event = await queue.get()
            except asyncio.CancelledError:
                break
            if event is self._stop_sentinel:
                queue.task_done()
                break
            try:
                await self._dispatch_event(cast(Event, event))
            finally:
                queue.task_done()
                self._queue_size = queue.qsize()

    async def _dispatch_event(self, event: Event) -> None:
        """Dispatch a single event to all registered subscribers."""
        callbacks = self._snapshot_subscribers()
        if not callbacks:
            return
        loop = asyncio.get_running_loop()
        tasks = [
            loop.run_in_executor(
                self._delivery_pool,
                self._execute_callback,
                callback,
                event,
                subscriber_id,
                callback_id,
            )
            for subscriber_id, callback_id, callback in callbacks
        ]
        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)

    def _execute_callback(
        self,
        callback: Callable[[Event], Any],
        event: Event,
        subscriber_id: str,
        callback_id: str,
    ) -> None:
        """Execute subscriber callback inside thread pool with error handling."""
        try:
            result = callback(event)
            if inspect.isawaitable(result):
                asyncio.run(self._await_result(result))  # type: ignore[arg-type]
        except Exception as exc:  # pragma: no cover - defensive logging
            logger.error(
                "Error in event callback %s for subscriber %s: %s",
                callback_id,
                subscriber_id,
                exc,
            )

    async def _await_result(self, awaitable: Any) -> None:
        """Await a coroutine returned from a synchronous callback wrapper."""
        await awaitable

    def _snapshot_subscribers(self) -> list[tuple[str, str, Callable[[Event], None]]]:
        """Create a snapshot of current subscribers to avoid holding locks."""
        with self._lock:
            return [
                (str(subscriber_id), callback_id, callback)
                for subscriber_id, callbacks in self._subscribers.items()
                for callback_id, callback in callbacks.items()
            ]

    async def _enqueue_event(self, event: Event) -> None:
        """Enqueue event with backpressure handling inside the event loop."""
        if not self._async_queue:
            return
        queue = self._async_queue
        if (
            self._max_queue_size > 0
            and queue.qsize() / self._max_queue_size >= self._hwm_ratio
        ):
            self._stats["high_watermark_hits"] += 1
            logger.debug(
                "EventStream queue high-watermark: size=%s max=%s policy=%s",
                queue.qsize(),
                self._max_queue_size,
                self._drop_policy,
            )

        if queue.full():
            if self._drop_policy == "drop_oldest":
                try:
                    _ = queue.get_nowait()
                    queue.task_done()
                    self._stats["dropped_oldest"] += 1
                except asyncio.QueueEmpty:
                    self._stats["dropped_newest"] += 1
                    logger.warning("EventStream full; dropped newest (empty on get)")
                    return
                queue.put_nowait(event)
                self._stats["enqueued"] += 1
                self._queue_size = queue.qsize()
                return
            if self._drop_policy == "block":
                try:
                    await asyncio.wait_for(
                        queue.put(event), timeout=self._block_timeout
                    )
                    self._stats["enqueued"] += 1
                    self._queue_size = queue.qsize()
                    return
                except asyncio.TimeoutError:
                    self._stats["dropped_newest"] += 1
                    logger.warning(
                        "EventStream full after blocking %.3fs; dropped newest",
                        self._block_timeout,
                    )
                    return
            self._stats["dropped_newest"] += 1
            logger.warning("EventStream full; dropped newest")
            return

        queue.put_nowait(event)
        self._stats["enqueued"] += 1
        self._queue_size = queue.qsize()

    async def _initiate_shutdown(self) -> None:
        """Flush pending events and signal workers to shut down."""
        if not self._async_queue or not self._stop_event:
            return
        # Wait for all currently enqueued events to be processed
        await self._async_queue.join()
        for _ in range(self._worker_count):
            await self._async_queue.put(self._stop_sentinel)
        self._stop_event.set()


def get_aggregated_event_stream_stats() -> dict[str, int]:
    """Aggregate stats across all live EventStream instances.

    Returns:
        Dictionary with summed counters and total queue size.
    """
    totals: dict[str, int] = {
        "streams": 0,
        "enqueued": 0,
        "dropped_oldest": 0,
        "dropped_newest": 0,
        "high_watermark_hits": 0,
        "queue_size": 0,
    }
    # Copy to list to avoid mutation during iteration
    for stream in list(EventStream._GLOBAL_STREAMS):  # type: ignore[attr-defined]
        try:
            stats = stream.get_stats()
            totals["streams"] += 1
            totals["enqueued"] += stats.get("enqueued", 0)
            totals["dropped_oldest"] += stats.get("dropped_oldest", 0)
            totals["dropped_newest"] += stats.get("dropped_newest", 0)
            totals["high_watermark_hits"] += stats.get("high_watermark_hits", 0)
            totals["queue_size"] += stats.get("queue_size", 0)
        except Exception:  # pragma: no cover - defensive
            continue
    return totals


__all__ = [
    "EventStream",
    "EventStreamSubscriber",
    "get_aggregated_event_stream_stats",
]
