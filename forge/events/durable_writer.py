from __future__ import annotations

import json
import queue
import threading
from dataclasses import dataclass
from typing import Any, Protocol

from forge.core.logger import forge_logger as logger


class FileStore(Protocol):
    def write(self, filename: str, content: str) -> None: ...


@dataclass(slots=True)
class PersistedEvent:
    """Payload handed to the durable writer thread."""

    event_id: int
    payload: dict[str, Any]
    filename: str
    cache_filename: str | None = None
    cache_contents: str | None = None


class DurableEventWriter:
    """Serializes and persists events in a dedicated thread to avoid blocking producers."""

    def __init__(
        self,
        file_store: FileStore,
        *,
        max_queue_size: int = 4096,
    ) -> None:
        self._file_store = file_store
        self._queue: queue.Queue[PersistedEvent | None] = queue.Queue(maxsize=max_queue_size)
        self._thread: threading.Thread | None = None
        self._stop_flag = threading.Event()
        self._drops = 0

    def start(self) -> None:
        if self._thread and self._thread.is_alive():
            return
        self._stop_flag.clear()
        self._thread = threading.Thread(target=self._run, name="forge-event-writer", daemon=True)
        self._thread.start()

    def stop(self, timeout: float = 2.0) -> None:
        if not self._thread:
            return
        try:
            self._queue.join()
        except Exception:
            pass
        self._stop_flag.set()
        try:
            self._queue.put_nowait(None)
        except queue.Full:
            pass
        self._thread.join(timeout=timeout)
        self._thread = None

    def enqueue(self, persisted_event: PersistedEvent) -> bool:
        if not self._thread or not self._thread.is_alive():
            return False
        try:
            self._queue.put_nowait(persisted_event)
            return True
        except queue.Full:
            self._drops += 1
            logger.warning(
                "DurableEventWriter queue full; dropped event id=%s filename=%s",
                persisted_event.event_id,
                persisted_event.filename,
            )
            return False

    def _run(self) -> None:
        while not self._stop_flag.is_set():
            try:
                item = self._queue.get(timeout=0.1)
            except queue.Empty:
                continue
            if item is None:
                self._queue.task_done()
                break
            try:
                self._flush_event(item)
            except Exception as exc:  # pragma: no cover - persistence must not crash thread
                logger.error(
                    "Failed to persist event id=%s filename=%s: %s",
                    item.event_id,
                    item.filename,
                    exc,
                )
            finally:
                self._queue.task_done()

    def _flush_event(self, persisted_event: PersistedEvent) -> None:
        serialized = json.dumps(persisted_event.payload)
        self._file_store.write(persisted_event.filename, serialized)
        if (
            persisted_event.cache_filename
            and persisted_event.cache_contents is not None
        ):
            try:
                self._file_store.write(
                    persisted_event.cache_filename, persisted_event.cache_contents
                )
            except Exception as exc:  # pragma: no cover - cache best effort
                logger.debug(
                    "Cache page write failed for event %s: %s",
                    persisted_event.event_id,
                    exc,
                )


