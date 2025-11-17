"""Unit tests for monitoring routes and websockets."""

from __future__ import annotations

import asyncio
from datetime import datetime
from types import SimpleNamespace
from typing import Any, cast
import sys
import types

import pytest

from fastapi import HTTPException, FastAPI
from fastapi.testclient import TestClient
from starlette.websockets import WebSocket

from forge.server.routes import monitoring as monitoring_routes


class DummyCache:
    async def get_cache_stats(self) -> dict[str, Any]:
        return {"redis_available": True, "cache_type": "redis", "cached_users": 7}


class DummyWebSocket:
    def __init__(self, fail_close: bool = False) -> None:
        self.accepted: bool = False
        self.messages: list[Any] = []
        self.closed: bool = False
        self.fail_close = fail_close
        self.client = SimpleNamespace(host="127.0.0.1")

    async def accept(self) -> None:
        self.accepted = True

    async def send_json(self, data: Any) -> None:
        self.messages.append(data)
        if len(self.messages) >= 2:
            raise asyncio.CancelledError

    async def close(self) -> None:
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
        SimpleNamespace(
            get_active_conversations=fake_get_active_conversations,
            sessions={"s": object()},
        ),
    )

    async def fake_get_async_cache():
        return DummyCache()

    fake_cache_module = types.SimpleNamespace(
        get_async_smart_cache=fake_get_async_cache
    )
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

    fake_cache_module = types.SimpleNamespace(
        get_async_smart_cache=fake_get_async_cache
    )
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
        await monitoring_routes.live_metrics_stream(cast(WebSocket, ws))

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
        await monitoring_routes.live_metrics_stream(cast(WebSocket, ws))

    assert any("error" in msg for msg in ws.messages)


def test_runtime_orchestrator_prom_lines(monkeypatch):
    from forge.runtime import telemetry as telemetry_module

    fake = telemetry_module.RuntimeTelemetry()
    fake.record_acquire("local", reused=False)
    fake.record_acquire("docker", reused=True)
    fake.record_acquire("docker", reused=True)
    fake.record_release("local")
    fake.record_watchdog_termination("docker", "active_timeout")
    fake.record_scaling_signal("capacity_exhausted|docker", severity="warning")
    monkeypatch.setattr(telemetry_module, "runtime_telemetry", fake, raising=False)
    monkeypatch.setattr(
        monitoring_routes.runtime_orchestrator,
        "pool_stats",
        lambda: {"local": 1, "docker": 2},
    )
    monkeypatch.setattr(
        monitoring_routes.runtime_orchestrator,
        "delegate_stats",
        lambda: {"local": 3},
    )
    monkeypatch.setattr(
        monitoring_routes.runtime_orchestrator,
        "idle_reclaim_stats",
        lambda: {"docker": 2},
    )
    monkeypatch.setattr(
        monitoring_routes.runtime_orchestrator,
        "eviction_stats",
        lambda: {"docker": 1},
    )
    monkeypatch.setattr(
        monitoring_routes.runtime_watchdog,
        "stats",
        lambda: {"docker": 1},
    )

    lines = monitoring_routes._runtime_orchestrator_prom_lines()
    joined = "\n".join(lines)
    assert "forge_runtime_acquire_total 3" in joined
    assert 'forge_runtime_reuse{kind="docker"} 2' in joined
    assert "forge_runtime_release_total 1" in joined
    assert 'forge_runtime_pool_size{kind="docker"} 2' in joined
    assert "forge_runtime_pool_size_total 3" in joined
    assert 'forge_runtime_delegate_fork{parent="local"} 3' in joined
    assert "forge_runtime_watchdog_terminations_total 1" in joined
    assert (
        'forge_runtime_watchdog_terminations{kind="docker",reason="active_timeout"} 1'
        in joined
    )
    assert (
        'forge_runtime_scaling_signals{kind="docker",signal="capacity_exhausted"} 1'
        in joined
    )
    assert 'forge_runtime_watchdog_watched{kind="docker"} 1' in joined
    assert "forge_runtime_watchdog_watched_total 1" in joined
    assert 'forge_runtime_pool_idle_reclaim{kind="docker"} 2' in joined
    assert "forge_runtime_pool_idle_reclaim_total 2" in joined
    assert 'forge_runtime_pool_eviction{kind="docker"} 1' in joined
    assert "forge_runtime_pool_eviction_total 1" in joined
    fake.reset()


def test_config_schema_prom_lines(monkeypatch):
    monkeypatch.setattr(
        monitoring_routes.config_telemetry,
        "snapshot",
        lambda: {
            "schema_missing": 1,
            "schema_mismatch": {"1.0.0": 1},
            "invalid_agents": {"agent.Bad": 1},
            "invalid_base": 1,
        },
    )

    lines = monitoring_routes._config_schema_prom_lines()
    joined = "\n".join(lines)
    assert "forge_agent_config_schema_missing_total 1" in joined
    assert 'forge_agent_config_schema_mismatch{version="1.0.0"} 1' in joined
    assert 'forge_agent_config_invalid_section{agent="agent.Bad"} 1' in joined
    assert "forge_agent_config_invalid_base_total 1" in joined


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

    await monitoring_routes.live_metrics_stream(cast(WebSocket, ws))
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

    await monitoring_routes.live_metrics_stream(cast(WebSocket, ws))


def test_controller_health_endpoint(monkeypatch):
    client = _make_test_client()
    fake_controller = object()
    monkeypatch.setattr(
        monitoring_routes,
        "conversation_manager",
        SimpleNamespace(
            get_agent_session=lambda sid: SimpleNamespace(controller=fake_controller)
        ),
    )
    monkeypatch.setattr(
        monitoring_routes,
        "collect_controller_health",
        lambda controller: {"controller_id": "abc", "ok": True},
    )

    resp = client.get("/api/monitoring/controller/test-session/health")
    assert resp.status_code == 200
    assert resp.json()["ok"] is True


def test_controller_health_endpoint_missing_session(monkeypatch):
    client = _make_test_client()
    monkeypatch.setattr(
        monitoring_routes,
        "conversation_manager",
        SimpleNamespace(get_agent_session=lambda sid: None),
    )
    resp = client.get("/api/monitoring/controller/missing-session/health")
    assert resp.status_code == 404


def test_controller_health_endpoint_no_controller(monkeypatch):
    client = _make_test_client()
    monkeypatch.setattr(
        monitoring_routes,
        "conversation_manager",
        SimpleNamespace(
            get_agent_session=lambda sid: SimpleNamespace(controller=None)
        ),
    )
    resp = client.get("/api/monitoring/controller/no-controller/health")
    assert resp.status_code == 404


def test_process_manager_health_endpoint(monkeypatch):
    client = _make_test_client()
    fake_manager = SimpleNamespace(get_running_processes=lambda: [])
    monkeypatch.setattr(
        monitoring_routes,
        "conversation_manager",
        SimpleNamespace(process_manager=fake_manager),
    )
    monkeypatch.setattr(
        monitoring_routes,
        "get_process_manager_health_snapshot",
        lambda active_processes=None: {"metrics": {"active_processes": 0}},
    )
    resp = client.get("/api/monitoring/processes/health")
    assert resp.status_code == 200
    assert resp.json()["metrics"]["active_processes"] == 0