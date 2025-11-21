from __future__ import annotations

import os
from unittest.mock import MagicMock

import pytest

from forge.events.stream import EventStream
from forge.events.action import MessageAction
from forge.events.event import EventSource


@pytest.fixture(autouse=True)
def clear_env(monkeypatch):
    for k in [
        "FORGE_EVENTSTREAM_MAX_QUEUE",
        "FORGE_EVENTSTREAM_POLICY",
        "FORGE_EVENTSTREAM_HWM_RATIO",
        "FORGE_EVENTSTREAM_BLOCK_TIMEOUT",
    ]:
        monkeypatch.delenv(k, raising=False)


def _make_stream(monkeypatch, maxsize: int, policy: str):
    monkeypatch.setenv("FORGE_EVENTSTREAM_MAX_QUEUE", str(maxsize))
    monkeypatch.setenv("FORGE_EVENTSTREAM_POLICY", policy)
    file_store = MagicMock()
    file_store.list.return_value = []
    file_store.write = MagicMock()
    file_store.read = MagicMock()
    stream = EventStream("sid", file_store, user_id=None)
    # Stop processing thread to keep items in the queue during tests
    stream._stop_flag.set()
    stream._queue_thread.join(timeout=1)
    return stream


def _enqueue(stream: EventStream, n: int) -> None:
    for i in range(n):
        evt = MessageAction(content=f"m{i}")
        stream.add_event(evt, EventSource.AGENT)


def test_drop_oldest_policy(monkeypatch):
    stream = _make_stream(monkeypatch, maxsize=3, policy="drop_oldest")
    try:
        _enqueue(stream, 4)
        stats = stream.get_stats()
        assert stats["dropped_oldest"] == 1
        assert stats["dropped_newest"] == 0
        assert stream._queue.qsize() == 3
    finally:
        stream.close()


def test_drop_newest_policy(monkeypatch):
    stream = _make_stream(monkeypatch, maxsize=3, policy="drop_newest")
    try:
        _enqueue(stream, 5)
        stats = stream.get_stats()
        assert stats["dropped_newest"] == 2
        assert stats["dropped_oldest"] == 0
        assert stream._queue.qsize() == 3
    finally:
        stream.close()


def test_block_policy_falls_back(monkeypatch):
    # With no consumer, block policy will timeout and drop newest
    monkeypatch.setenv("FORGE_EVENTSTREAM_BLOCK_TIMEOUT", "0.01")
    stream = _make_stream(monkeypatch, maxsize=2, policy="block")
    try:
        _enqueue(stream, 4)
        stats = stream.get_stats()
        assert stats["dropped_newest"] >= 1
        assert stream._queue.qsize() == 2
    finally:
        stream.close()
