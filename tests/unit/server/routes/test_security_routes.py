"""Unit tests for security proxy routes."""

from __future__ import annotations

from types import SimpleNamespace
from typing import Any, cast

import pytest

from fastapi import HTTPException, Request

from forge.server.routes import security as security_routes
from forge.server.session.conversation import ServerConversation


class DummyAnalyzer:
    def __init__(self):
        self.called_with = None

    async def handle_api_request(self, request: Request) -> str:
        self.called_with = request
        return "ok"


@pytest.mark.asyncio
async def test_security_api_proxies_request(monkeypatch):
    analyzer = DummyAnalyzer()
    conversation = cast(ServerConversation, SimpleNamespace(security_analyzer=analyzer))
    request = cast(Request, SimpleNamespace())
    response = await security_routes.security_api(request, conversation)
    assert response == "ok"
    assert analyzer.called_with is request


@pytest.mark.asyncio
async def test_security_api_missing_analyzer():
    conversation = cast(ServerConversation, SimpleNamespace(security_analyzer=None))
    with pytest.raises(HTTPException) as exc:
        await security_routes.security_api(
            cast(Request, SimpleNamespace()), conversation
        )
    assert exc.value.status_code == 404
