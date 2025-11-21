"""Documentation-style test stub for healthcheck readiness logic.

This does not run docker-compose. It simply ensures the readiness endpoint
returns a JSON with expected keys so the compose healthcheck will succeed.
"""

from fastapi.testclient import TestClient
from forge.server.app import app

client = TestClient(app)


def test_readiness_shape():
    r = client.get("/api/monitoring/readiness")
    assert r.status_code == 200
    data = r.json()
    assert set(data.keys()) == {"status", "timestamp", "checks"}
    assert "redis" in data["checks"]
    assert "mcp" in data["checks"]
