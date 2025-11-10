"""Event stream implementation with pub/sub and persistence helpers."""

from __future__ import annotations

import asyncio
import queue
import threading
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from enum import Enum
from functools import partial
from typing import TYPE_CHECKING, Any, Callable

from forge.core.logger import forge_logger as logger
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


async def session_exists(sid: str, file_store: FileStore, user_id: str | None = None) -> bool:
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
    _queue: queue.Queue[Event]
    _queue_thread: threading.Thread
    _queue_loop: asyncio.AbstractEventLoop | None
    _thread_pools: dict[str, dict[str, ThreadPoolExecutor]]
    _thread_loops: dict[str, dict[str, asyncio.AbstractEventLoop]]
    _write_page_cache: list[dict]

    def __init__(self, sid: str, file_store: FileStore, user_id: str | None = None) -> None:
        """Initialize event stream with subscriber management.
        
        Args:
            sid: Session ID for this event stream
            file_store: File storage backend for persisting events
            user_id: Optional user ID for scoping

        """
        super().__init__(sid, file_store, user_id)
        self._stop_flag = threading.Event()
        self._queue: queue.Queue[Event] = queue.Queue()
        self._thread_pools = {}
        self._thread_loops = {}
        self._queue_loop = None
        self._queue_thread = threading.Thread(target=self._run_queue_loop)
        self._queue_thread.daemon = True
        self._queue_thread.start()
        self._subscribers = {}
        self._lock = threading.Lock()
        self.secrets = {}
        self._write_page_cache = []

    def _init_thread_loop(self, subscriber_id: str, callback_id: str) -> None:
        """Initialize dedicated event loop for subscriber callback.
        
        Args:
            subscriber_id: Subscriber identifier
            callback_id: Callback identifier within subscriber

        """
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        if subscriber_id not in self._thread_loops:
            self._thread_loops[subscriber_id] = {}
        self._thread_loops[subscriber_id][callback_id] = loop

    def close(self) -> None:
        """Close event stream, stopping queue processing and cleaning up subscribers."""
        self._stop_flag.set()
        if self._queue_thread.is_alive():
            self._queue_thread.join()
        subscriber_ids = list(self._subscribers.keys())
        for subscriber_id in subscriber_ids:
            callback_ids = list(self._subscribers[subscriber_id].keys())
            for callback_id in callback_ids:
                self._clean_up_subscriber(subscriber_id, callback_id)
        while not self._queue.empty():
            self._queue.get()

    def _cleanup_thread_loop(self, subscriber_id: str, callback_id: str) -> None:
        """Clean up thread loop for a specific subscriber callback."""
        if subscriber_id not in self._thread_loops or callback_id not in self._thread_loops[subscriber_id]:
            return

        loop = self._thread_loops[subscriber_id][callback_id]
        current_task = asyncio.current_task(loop)
        pending = [task for task in asyncio.all_tasks(loop) if task is not current_task]

        for task in pending:
            task.cancel()

        try:
            loop.stop()
            loop.close()
        except Exception as e:
            logger.warning("Error closing loop for %s/%s: %s", subscriber_id, callback_id, e)

        del self._thread_loops[subscriber_id][callback_id]

    def _cleanup_thread_pool(self, subscriber_id: str, callback_id: str) -> None:
        """Clean up thread pool for a specific subscriber callback."""
        if subscriber_id not in self._thread_pools or callback_id not in self._thread_pools[subscriber_id]:
            return

        pool = self._thread_pools[subscriber_id][callback_id]
        pool.shutdown()
        del self._thread_pools[subscriber_id][callback_id]

    def _clean_up_subscriber(self, subscriber_id: str, callback_id: str) -> None:
        """Clean up a specific subscriber callback."""
        if subscriber_id not in self._subscribers:
            logger.warning("Subscriber not found during cleanup: %s", subscriber_id)
            return
        if callback_id not in self._subscribers[subscriber_id]:
            logger.warning("Callback not found during cleanup: %s", callback_id)
            return

        self._cleanup_thread_loop(subscriber_id, callback_id)
        self._cleanup_thread_pool(subscriber_id, callback_id)
        del self._subscribers[subscriber_id][callback_id]

    def subscribe(
        self,
        subscriber_id: EventStreamSubscriber,
        callback: Callable[[Event], None],
        callback_id: str,
    ) -> None:
        """Subscribe to event stream with a callback function.
        
        Creates dedicated thread pool and event loop for this callback.
        
        Args:
            subscriber_id: Unique subscriber identifier
            callback: Function to call for each event
            callback_id: Unique callback identifier within subscriber
            
        Raises:
            ValueError: If callback_id already exists for this subscriber

        """
        initializer = partial(self._init_thread_loop, subscriber_id, callback_id)
        pool = ThreadPoolExecutor(max_workers=1, initializer=initializer)
        if subscriber_id not in self._subscribers:
            self._subscribers[subscriber_id] = {}
            self._thread_pools[subscriber_id] = {}
        if callback_id in self._subscribers[subscriber_id]:
            msg = f"Callback ID on subscriber {subscriber_id} already exists: {callback_id}"
            raise ValueError(msg)
        self._subscribers[subscriber_id][callback_id] = callback
        self._thread_pools[subscriber_id][callback_id] = pool

    def unsubscribe(self, subscriber_id: EventStreamSubscriber, callback_id: str) -> None:
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
        """Add event to stream with automatic ID assignment and persistence.
        
        Thread-safe. Assigns ID, timestamp, source, and queues for subscriber delivery.
        
        Args:
            event: Event to add (must not have ID set)
            source: Source of the event (USER, AGENT, etc.)
            
        Raises:
            ValueError: If event already has an ID (indicates resubmission)

        """
        evt_id = getattr(event, "id", Event.INVALID_ID)
        if not isinstance(evt_id, int):
            evt_id = Event.INVALID_ID
        if evt_id != Event.INVALID_ID:
            msg = f"Event already has an ID:{evt_id}. It was probably added back to the EventStream from inside a handler, triggering a loop."
            raise ValueError(
                msg,
            )
        from forge.events.action import ChangeAgentStateAction  # local import to avoid global cycle

        event.timestamp = datetime.now()
        event.source = source
        with self._lock:
            event.id = self.cur_id
            # 🔢 CRITICAL FIX: Add sequence number for guaranteed ordering
            # Sequence ensures events render in correct order even if network delays cause out-of-order delivery
            event.sequence = self.cur_id
            self.cur_id += 1
            current_write_page = self._write_page_cache
            data = event_to_dict(event)
            data = self._replace_secrets(data)
            event = event_from_dict(data)
            if isinstance(event, ChangeAgentStateAction):
                logger.debug(
                    "Queued ChangeAgentStateAction id=%s state=%s source=%s",
                    event.id,
                    getattr(event, "agent_state", None),
                    source,
                )
            current_write_page.append(data)
            if len(current_write_page) == self.cache_size:
                self._write_page_cache = []
        if event.id is not None:
            event_json = json.dumps(data)
            filename = self._get_filename_for_id(event.id, self.user_id)
            if len(event_json) > 1000000:
                logger.warning(
                    "Saving event JSON over 1MB: %s bytes, filename: %s",
                    len(event_json),
                    filename,
                    extra={"user_id": self.user_id, "session_id": self.sid, "size": len(event_json)},
                )
            self.file_store.write(filename, event_json)
            self._store_cache_page(current_write_page)
        self._queue.put(event)

    def _store_cache_page(self, current_write_page: list[dict]) -> None:
        """Store a page in the cache. Reading individual events is slow when there are a lot of them, so we use pages."""
        if len(current_write_page) < self.cache_size:
            return
        start = current_write_page[0]["id"]
        end = start + self.cache_size
        contents = json.dumps(current_write_page)
        cache_filename = self._get_filename_for_cache(start, end)
        self.file_store.write(cache_filename, contents)

    def set_secrets(self, secrets: dict[str, str]) -> None:
        """Set secrets dictionary for masking sensitive values in events.
        
        Args:
            secrets: Dictionary of secrets to mask

        """
        self.secrets = secrets.copy()

    def update_secrets(self, secrets: dict[str, str]) -> None:
        """Update secrets dictionary with additional values.
        
        Args:
            secrets: Additional secrets to add

        """
        self.secrets.update(secrets)

    def _replace_secrets(self, data: dict[str, Any], is_top_level: bool = True) -> dict[str, Any]:
        """Recursively replace secret values in event data with masked placeholder.
        
        Protects top-level event fields from masking to preserve event structure.
        
        Args:
            data: Event data dictionary
            is_top_level: Whether this is the top-level call
            
        Returns:
            Data with secrets replaced

        """
        TOP_LEVEL_PROTECTED_FIELDS = {"timestamp", "id", "source", "cause", "action", "observation", "message"}
        for key in data:
            if is_top_level and key in TOP_LEVEL_PROTECTED_FIELDS:
                continue
            if isinstance(data[key], dict):
                data[key] = self._replace_secrets(data[key], is_top_level=False)
            elif isinstance(data[key], str):
                for secret in self.secrets.values():
                    data[key] = data[key].replace(secret, "<secret_hidden>")
        return data

    def _run_queue_loop(self) -> None:
        """Start event loop in queue processing thread."""
        self._queue_loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self._queue_loop)
        try:
            self._queue_loop.run_until_complete(self._process_queue())
        finally:
            self._queue_loop.close()

    async def _process_queue(self) -> None:
        """Process events from queue and deliver to subscribers.
        
        Runs in background thread, polling queue for new events and dispatching
        to subscriber callbacks via dedicated thread pools.
        """
        while should_continue() and (not self._stop_flag.is_set()):
            event = None
            try:
                # Reduced from 100ms to 10ms for 10x faster real-time streaming
                event = self._queue.get(timeout=0.01)
            except queue.Empty:
                continue
            
            # Log event streaming performance
            event_type = event.__class__.__name__
            logger.debug(f"⚡ Streaming event: {event_type} (id={getattr(event, 'id', 'N/A')})")
            
            for key in sorted(self._subscribers.keys()):
                callbacks = self._subscribers[key]
                callback_ids = list(callbacks.keys())
                for callback_id in callback_ids:
                    if callback_id in callbacks:
                        callback = callbacks[callback_id]
                        pool = self._thread_pools[key][callback_id]
                        future = pool.submit(callback, event)
                        future.add_done_callback(self._make_error_handler(callback_id, key))

    def _make_error_handler(self, callback_id: str, subscriber_id: str) -> Callable[[Any], None]:

        def _handle_callback_error(fut: Any) -> None:
            try:
                fut.result()
            except Exception as e:
                logger.error("Error in event callback %s for subscriber %s: %s", callback_id, subscriber_id, str(e))
                raise

        return _handle_callback_error
