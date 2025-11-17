"""Unit tests for feedback submission route."""

from __future__ import annotations

import json
from dataclasses import dataclass
from types import SimpleNamespace
from typing import Any, cast

import pytest

from fastapi import Request, status
from fastapi.responses import JSONResponse
from starlette.types import Message, Receive, Scope

from forge.server.routes import feedback as feedback_routes
from forge.server.session.conversation import ServerConversation


class FakeEventStore:
    def __init__(self, events: list[Any]):
        self._events = events

    def search_events(self, *args: Any, **kwargs: Any) -> list[Any]:
        return self._events


@dataclass
class FakeEvent:
    message: str
    sequence: int = 1


def _make_request(body: dict[str, Any]) -> Request:
    payload = json.dumps(body).encode("utf-8")

    async def receive() -> Message:
        return {"type": "http.request", "body": payload, "more_body": False}

    scope: Scope = {
        "type": "http",
        "method": "POST",
        "path": "/feedback",
        "query_string": b"",
        "headers": [],
        "client": None,
        "server": None,
    }
    return Request(scope, cast(Receive, receive))


def _make_conversation(events: list[Any]) -> ServerConversation:
    convo = SimpleNamespace(sid="session-123", event_stream=FakeEventStore(events))
    return cast(ServerConversation, convo)


@pytest.mark.asyncio
async def test_submit_feedback_success(monkeypatch):
    events = [FakeEvent(message="hello", sequence=42)]
    conversation = _make_conversation(events)
    request = _make_request(
        {
            "email": "user@example.com",
            "version": "1.0.0",
            "permissions": "public",
            "polarity": "positive",
            "feedback": "Great experience!",
        }
    )

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
    assert payload == {
        "stored": True,
        "trajectory": [{"message": "hello", "sequence": 42}],
    }


@pytest.mark.asyncio
async def test_submit_feedback_uses_defaults(monkeypatch):
    conversation = _make_conversation([])
    request = _make_request({})

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
    request = _make_request({"feedback": "bad"})

    async def failing_call_sync(func, feedback):
        raise RuntimeError("datastore down")

    monkeypatch.setattr(feedback_routes, "call_sync_from_async", failing_call_sync)
    monkeypatch.setattr(feedback_routes, "event_to_dict", lambda event: event)

    response = await feedback_routes.submit_feedback(request, conversation)
    assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
    assert json.loads(response.body) == {"error": "Failed to submit feedback"}
