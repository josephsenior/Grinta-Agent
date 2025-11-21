"""Unit tests for trajectory routes."""

from __future__ import annotations

import json

import pytest

from fastapi.responses import JSONResponse

from forge.server.routes import trajectory as trajectory_routes


@pytest.mark.asyncio
async def test_get_trajectory_returns_empty(monkeypatch, caplog):
    caplog.set_level("INFO")
    response = await trajectory_routes.get_trajectory("conversation-123")
    assert isinstance(response, JSONResponse)
    assert response.status_code == 200
    payload = json.loads(response.body)
    assert payload == {"trajectory": []}
