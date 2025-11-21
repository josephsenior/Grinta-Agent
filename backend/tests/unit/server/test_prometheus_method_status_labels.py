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


def test_prometheus_includes_method_status_labels():
    client = _make_client()
    # Trigger a request to a known endpoint
    r = client.get("/api/monitoring/health")
    assert r.status_code == 200

    # Fetch prom metrics and assert labeled line exists
    prom = client.get("/api/monitoring/metrics-prom")
    assert prom.status_code == 200
    body = prom.text
    # Look for GET/200 labeled total metric
    assert 'forge_request_total{method="GET",status="200"}' in body
