"""Unit tests for monitoring routes and websockets."""

from __future__ import annotations

import asyncio
from datetime import datetime
from types import SimpleNamespace
import sys
import types

import pytest

from fastapi import HTTPException, FastAPI
from fastapi.testclient import TestClient

from forge.server.routes import monitoring as monitoring_routes


class DummyCache:
    async def get_cache_stats(self):
        return {"redis_available": True, "cache_type": "redis", "cached_users": 7}


class DummyWebSocket:
    def __init__(self, fail_close: bool = False):
        self.accepted = False
        self.messages = []
        self.closed = False
        self.fail_close = fail_close

    async def accept(self):
        self.accepted = True

    async def send_json(self, data):
        self.messages.append(data)
        if len(self.messages) >= 2:
            raise asyncio.CancelledError

    async def close(self):
        self.closed = True
        if self.fail_close:
            raise RuntimeError("close failed")


def _make_test_client() -> TestClient:
    app = FastAPI()
    app.include_router(monitoring_routes.app)
    return TestClient(app)


@pytest.mark.asyncio
async def test_get_metrics_success(monkeypatch):
    async def fake_get_active_conversations():
        return ["cid1", "cid2"]

    monkeypatch.setattr(
        monitoring_routes,
        "conversation_manager",
        SimpleNamespace(get_active_conversations=fake_get_active_conversations, sessions={"s": object()}),
    )

    async def fake_get_async_cache():
        return DummyCache()

    fake_cache_module = types.SimpleNamespace(get_async_smart_cache=fake_get_async_cache)
    monkeypatch.setitem(sys.modules, "forge.core.cache", fake_cache_module)

    metrics = await monitoring_routes.get_metrics()
    assert metrics.system.active_conversations == 2
    assert metrics.system.cache_stats["async_smart_cache"]["redis_available"] is True


@pytest.mark.asyncio
async def test_get_metrics_handles_errors(monkeypatch):
    async def failing_active_convos():
        raise RuntimeError("boom")

    monkeypatch.setattr(
        monitoring_routes,
        "conversation_manager",
        SimpleNamespace(get_active_conversations=failing_active_convos, sessions={}),
    )

    def failing_system_metrics(*args, **kwargs):
        raise RuntimeError("system fail")

    monkeypatch.setattr(monitoring_routes, "SystemMetrics", failing_system_metrics)

    async def fake_cache_failure():
        raise RuntimeError("cache fail")

    fake_cache_module = types.SimpleNamespace(get_async_smart_cache=fake_cache_failure)
    monkeypatch.setitem(sys.modules, "forge.core.cache", fake_cache_module)

    with pytest.raises(HTTPException):
        await monitoring_routes.get_metrics()


@pytest.mark.asyncio
async def test_get_metrics_uses_sessions_fallback(monkeypatch):
    monkeypatch.setattr(
        monitoring_routes,
        "conversation_manager",
        SimpleNamespace(sessions={"cid1": object(), "cid2": object()}),
    )

    async def fake_get_async_cache():
        return DummyCache()

    fake_cache_module = types.SimpleNamespace(get_async_smart_cache=fake_get_async_cache)
    monkeypatch.setitem(sys.modules, "forge.core.cache", fake_cache_module)

    metrics = await monitoring_routes.get_metrics()
    assert metrics.system.active_conversations == 2


def test_static_endpoints():
    client = _make_test_client()
    assert client.get("/api/monitoring/health").status_code == 200
    assert client.get("/api/monitoring/agents/performance").json() == []
    assert "file_cache" in client.get("/api/monitoring/cache/stats").json()
    assert "schema_validation" in client.get("/api/monitoring/failures/taxonomy").json()
    assert client.get("/api/monitoring/ace/metrics").json() is None
    assert client.get("/api/monitoring/parallel/stats").json()["enabled"] is True


@pytest.mark.asyncio
async def test_live_metrics_stream_happy_path(monkeypatch):
    ws = DummyWebSocket()

    async def fake_get_metrics():
        return monitoring_routes.MetricsResponse(
            system=monitoring_routes.SystemMetrics(
                timestamp=datetime.now(),
                active_conversations=1,
                total_actions_today=0,
                avg_response_time_ms=0.0,
                cache_stats={},
                parallel_execution_stats={},
                tool_usage={},
                failure_distribution={},
            ),
            agents=[],
        )

    monkeypatch.setattr(monitoring_routes, "get_metrics", fake_get_metrics)

    async def cancel_soon(_):
        raise asyncio.CancelledError

    monkeypatch.setattr(monitoring_routes.asyncio, "sleep", cancel_soon)

    with pytest.raises(asyncio.CancelledError):
        await monitoring_routes.live_metrics_stream(ws)

    assert ws.accepted is True
    assert len(ws.messages) >= 1


@pytest.mark.asyncio
async def test_live_metrics_stream_collect_error(monkeypatch):
    ws = DummyWebSocket()

    async def failing_get_metrics():
        raise RuntimeError("collect fail")

    monkeypatch.setattr(monitoring_routes, "get_metrics", failing_get_metrics)

    async def cancel_soon(_):
        raise asyncio.CancelledError

    monkeypatch.setattr(monitoring_routes.asyncio, "sleep", cancel_soon)

    with pytest.raises(asyncio.CancelledError):
        await monitoring_routes.live_metrics_stream(ws)

    assert any("error" in msg for msg in ws.messages)


@pytest.mark.asyncio
async def test_live_metrics_stream_disconnect(monkeypatch):
    ws = DummyWebSocket()

    async def dummy_get_metrics():
        return monitoring_routes.MetricsResponse(
            system=monitoring_routes.SystemMetrics(
                timestamp=datetime.now(),
                active_conversations=0,
                total_actions_today=0,
                avg_response_time_ms=0.0,
                cache_stats={},
                parallel_execution_stats={},
                tool_usage={},
                failure_distribution={},
            ),
            agents=[],
        )

    monkeypatch.setattr(monitoring_routes, "get_metrics", dummy_get_metrics)

    async def raise_disconnect(_):
        raise monitoring_routes.WebSocketDisconnect

    monkeypatch.setattr(monitoring_routes.asyncio, "sleep", raise_disconnect)

    await monitoring_routes.live_metrics_stream(ws)
    assert ws.accepted is True


@pytest.mark.asyncio
async def test_live_metrics_stream_close_failure(monkeypatch):
    ws = DummyWebSocket(fail_close=True)

    async def failing_get_metrics():
        raise RuntimeError("fail")

    monkeypatch.setattr(monitoring_routes, "get_metrics", failing_get_metrics)

    async def raise_runtime(_):
        raise RuntimeError("loop fail")

    monkeypatch.setattr(monitoring_routes.asyncio, "sleep", raise_runtime)

    await monitoring_routes.live_metrics_stream(ws)
