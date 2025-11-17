from fastapi import FastAPI
from fastapi.testclient import TestClient
from starlette.middleware.base import BaseHTTPMiddleware

from forge.server.routes.monitoring import app as monitoring_router
from forge.server.middleware.request_metrics import RequestMetricsMiddleware


def _make_client() -> TestClient:
    test_app = FastAPI()
    test_app.include_router(monitoring_router)
    test_app.add_middleware(
        BaseHTTPMiddleware,
        dispatch=RequestMetricsMiddleware(enabled=True),
    )
    return TestClient(test_app)


def test_readiness_basic():
    client = _make_client()
    r = client.get("/api/monitoring/readiness")
    assert r.status_code == 200
    data = r.json()
    assert data["status"] in {"ready", "degraded"}
    assert "checks" in data
    # Redis and MCP may be skipped in local dev without envs
    assert "redis" in data["checks"]
    assert "mcp" in data["checks"]


def test_prometheus_inflight_metric_present():
    client = _make_client()
    # Trigger a couple of requests first
    client.get("/api/monitoring/health")
    r = client.get("/api/monitoring/metrics-prom")
    assert r.status_code == 200
    body = r.text
    assert "forge_requests_in_flight" in body
