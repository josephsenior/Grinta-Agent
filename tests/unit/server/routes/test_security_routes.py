"""Unit tests for security proxy routes."""

from __future__ import annotations

from types import SimpleNamespace

import pytest

from fastapi import HTTPException

from forge.server.routes import security as security_routes


class DummyAnalyzer:
    def __init__(self):
        self.called_with = None

    async def handle_api_request(self, request):
        self.called_with = request
        return "ok"


@pytest.mark.asyncio
async def test_security_api_proxies_request(monkeypatch):
    analyzer = DummyAnalyzer()
    conversation = SimpleNamespace(security_analyzer=analyzer)
    request = SimpleNamespace()
    response = await security_routes.security_api(request, conversation)
    assert response == "ok"
    assert analyzer.called_with is request


@pytest.mark.asyncio
async def test_security_api_missing_analyzer():
    conversation = SimpleNamespace(security_analyzer=None)
    with pytest.raises(HTTPException) as exc:
        await security_routes.security_api(SimpleNamespace(), conversation)
    assert exc.value.status_code == 404
