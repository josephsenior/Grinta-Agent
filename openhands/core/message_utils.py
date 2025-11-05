from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from openhands.events.event import Event
    from openhands.llm.metrics import Metrics, TokenUsage


def _get_tool_response_id(event: Event) -> str | None:
    """Extract tool response ID from event if available."""
    if not event.tool_call_metadata or not event.tool_call_metadata.model_response:
        return None
    return event.tool_call_metadata.model_response.get("id")


def _find_usage_by_response_id(metrics: Metrics, response_id: str) -> TokenUsage | None:
    """Find token usage record by response ID."""
    return next((u for u in metrics.token_usages if u.response_id == response_id), None)


def get_token_usage_for_event(event: Event, metrics: Metrics) -> TokenUsage | None:
    """Returns at most one token usage record for either:.

    - `tool_call_metadata.model_response.id`, if possible
    - otherwise event.response_id, if set.

    If neither exist or none matches in metrics.token_usages, returns None.
    """
    if tool_response_id := _get_tool_response_id(event):
        usage_rec = _find_usage_by_response_id(metrics, tool_response_id)
        if usage_rec is not None:
            return usage_rec

    # Fall back to event response ID
    if event.response_id:
        return _find_usage_by_response_id(metrics, event.response_id)

    return None


def _find_event_index_by_id(events: list[Event], event_id: int) -> int | None:
    """Find the index of an event by its ID."""
    return next((i for i, e in enumerate(events) if e.id == event_id), None)


def _search_backwards_for_token_usage(events: list[Event], start_idx: int, metrics: Metrics) -> TokenUsage | None:
    """Search backwards from start_idx for the first token usage."""
    for i in range(start_idx, -1, -1):
        usage = get_token_usage_for_event(events[i], metrics)
        if usage is not None:
            return usage
    return None


def get_token_usage_for_event_id(events: list[Event], event_id: int, metrics: Metrics) -> TokenUsage | None:
    """Starting from the event with .id == event_id and moving backwards in `events`,.

    find the first TokenUsage record (if any) associated either with:
    - tool_call_metadata.model_response.id, or
    - event.response_id

    Returns the first match found, or None if none is found.
    """
    idx = _find_event_index_by_id(events, event_id)
    if idx is None:
        return None

    return _search_backwards_for_token_usage(events, idx, metrics)
