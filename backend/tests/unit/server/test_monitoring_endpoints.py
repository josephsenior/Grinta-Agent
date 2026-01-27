import re
from fastapi import FastAPI
from fastapi.testclient import TestClient
from starlette.middleware.base import BaseHTTPMiddleware

from forge.server.routes.monitoring import app as monitoring_router
from forge.server.middleware.request_metrics import RequestMetricsMiddleware


def _make_monitoring_client() -> TestClient:
    test_app = FastAPI()
    test_app.include_router(monitoring_router)
    test_app.add_middleware(
        BaseHTTPMiddleware,
        dispatch=RequestMetricsMiddleware(enabled=True),
    )
    return TestClient(test_app)


def test_metrics_endpoint_basic_shape():
    client = _make_monitoring_client()
    r = client.get("/api/monitoring/metrics")
    assert r.status_code == 200
    body = r.json()
    # Top-level keys
    assert set(body.keys()) == {"system", "agents"}
    system = body["system"]
    # Required system fields
    for key in [
        "timestamp",
        "active_conversations",
        "total_actions_today",
        "avg_response_time_ms",
        "cache_stats",
        "parallel_execution_stats",
        "tool_usage",
        "failure_distribution",
    ]:
        assert key in system
    assert isinstance(body["agents"], list)


def test_prometheus_metrics_contains_build_and_request_histogram():
    client = _make_monitoring_client()
    r = client.get("/api/monitoring/metrics-prom")
    assert r.status_code == 200
    text = r.text
    # Build info line
    assert any(line.startswith("forge_build_info{") for line in text.splitlines())
    # Request metrics counters
    assert re.search(r"^forge_request_total \d+", text, re.MULTILINE)
    assert re.search(r"^forge_request_exceptions_total \d+", text, re.MULTILINE)
    # Histogram buckets and sum/count
    assert any("forge_request_duration_ms_bucket" in line for line in text.splitlines())
    assert re.search(
        r"^forge_request_duration_ms_sum \d+(?:\.\d+)?", text, re.MULTILINE
    )
    assert re.search(r"^forge_request_duration_ms_count \d+", text, re.MULTILINE)
    assert re.search(
        r"^forge_runtime_running_sessions_total \d+", text, re.MULTILINE
    )
    assert re.search(r"^forge_runtime_warm_pool_total \d+", text, re.MULTILINE)


def test_health_endpoint():
    client = _make_monitoring_client()
    r = client.get("/api/monitoring/health")
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "healthy"
    assert "services" in body and isinstance(body["services"], dict)
