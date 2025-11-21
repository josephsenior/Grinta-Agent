"""Backward-compatible shim for legacy imports.

Deprecated: import from `forge.events.stream` instead.
This module re-exports the public API to avoid breaking older code/tests.
"""
from __future__ import annotations

# Re-export from the canonical module
from .stream import (
    EventStream,
    EventStreamSubscriber,
    session_exists,
    get_aggregated_event_stream_stats,
)
# Some legacy code may expect EventSource alongside EventStream here
from .event import EventSource  # noqa: F401

__all__ = [
    "EventStream",
    "EventStreamSubscriber",
    "session_exists",
    "get_aggregated_event_stream_stats",
    "EventSource",
]
