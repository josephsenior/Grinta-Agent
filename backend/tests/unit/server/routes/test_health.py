"""Unit tests for health endpoints."""

from __future__ import annotations

from fastapi import FastAPI
from fastapi.testclient import TestClient

from forge.server.routes.health import add_health_endpoints


def _build_client():
    app = FastAPI()
    add_health_endpoints(app)
    return TestClient(app)


def test_alive_endpoint_returns_status_ok():
    client = _build_client()
    response = client.get("/alive")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_health_endpoint_is_deprecated_and_points_to_monitoring():
    client = _build_client()
    response = client.get("/health")
    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "deprecated"
    assert payload["use"] == "/api/monitoring/health"


def test_server_info_returns_mocked_data(monkeypatch):
    client = _build_client()

    def fake_system_info():
        return {"cpu": 10, "memory": 20}

    monkeypatch.setattr("forge.server.routes.health.get_system_info", fake_system_info)

    response = client.get("/server_info")
    assert response.status_code == 200
    assert response.json() == {"cpu": 10, "memory": 20}
