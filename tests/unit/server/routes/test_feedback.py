"""Unit tests for feedback submission route."""

from __future__ import annotations

import json
from dataclasses import dataclass
from types import SimpleNamespace
from typing import Any

import pytest

from fastapi import status
from fastapi.responses import JSONResponse

from forge.server.routes import feedback as feedback_routes


class DummyRequest:
    def __init__(self, body: dict[str, Any]):
        self._body = body

    async def json(self) -> dict[str, Any]:
        return self._body


class FakeEventStore:
    def __init__(self, events: list[Any]):
        self._events = events

    def search_events(self, *args: Any, **kwargs: Any):
        return self._events


@dataclass
class FakeEvent:
    message: str
    sequence: int = 1


def _make_conversation(events: list[Any]) -> SimpleNamespace:
    return SimpleNamespace(sid="session-123", event_stream=FakeEventStore(events))


@pytest.mark.asyncio
async def test_submit_feedback_success(monkeypatch):
    events = [FakeEvent(message="hello", sequence=42)]
    conversation = _make_conversation(events)
    request = DummyRequest({
        "email": "user@example.com",
        "version": "1.0.0",
        "permissions": "public",
        "polarity": "positive",
        "feedback": "Great experience!",
    })

    async def fake_call_sync(func, feedback):
        assert func is feedback_routes.store_feedback
        assert feedback.session_id == conversation.sid
        assert feedback.permissions == "public"
        assert feedback.trajectory == [{"message": "hello", "sequence": 42}]
        return {"stored": True, "trajectory": feedback.trajectory}

    monkeypatch.setattr(feedback_routes, "call_sync_from_async", fake_call_sync)
    monkeypatch.setattr(
        feedback_routes,
        "event_to_dict",
        lambda event: {"message": event.message, "sequence": event.sequence},
    )

    response = await feedback_routes.submit_feedback(request, conversation)
    assert isinstance(response, JSONResponse)
    assert response.status_code == status.HTTP_200_OK
    payload = json.loads(response.body)
    assert payload == {"stored": True, "trajectory": [{"message": "hello", "sequence": 42}]}


@pytest.mark.asyncio
async def test_submit_feedback_uses_defaults(monkeypatch):
    conversation = _make_conversation([])
    request = DummyRequest({})

    async def fake_call_sync(func, feedback):
        assert feedback.email == ""
        assert feedback.version == ""
        assert feedback.permissions == "private"
        assert feedback.feedback == ""
        assert feedback.polarity == ""
        assert feedback.trajectory == []
        return {"ok": True}

    monkeypatch.setattr(feedback_routes, "call_sync_from_async", fake_call_sync)
    monkeypatch.setattr(feedback_routes, "event_to_dict", lambda event: event)

    response = await feedback_routes.submit_feedback(request, conversation)
    assert response.status_code == status.HTTP_200_OK
    assert json.loads(response.body) == {"ok": True}


@pytest.mark.asyncio
async def test_submit_feedback_handles_failure(monkeypatch):
    conversation = _make_conversation([])
    request = DummyRequest({"feedback": "bad"})

    async def failing_call_sync(func, feedback):
        raise RuntimeError("datastore down")

    monkeypatch.setattr(feedback_routes, "call_sync_from_async", failing_call_sync)
    monkeypatch.setattr(feedback_routes, "event_to_dict", lambda event: event)

    response = await feedback_routes.submit_feedback(request, conversation)
    assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
    assert json.loads(response.body) == {"error": "Failed to submit feedback"}
