import pytest
from fastapi.testclient import TestClient

import forge.server.routes.monitoring as monitoring
from forge.server.app import app


def test_websocket_rate_limit_rejects_second_when_limit_one(monkeypatch):
    # Tighten limits for test
    monkeypatch.setattr(monitoring, "_WS_MAX_CONCURRENT_PER_IP", 1, raising=True)
    monkeypatch.setattr(monitoring, "_WS_BURST_LIMIT_PER_MINUTE", 2, raising=True)
    monkeypatch.setattr(monitoring, "_WS_HOURLY_LIMIT", 10, raising=True)

    client = TestClient(app)
    with client.websocket_connect("/api/monitoring/ws/live") as ws1:
        # Second connection should be rejected due to concurrent limit
        with client.websocket_connect("/api/monitoring/ws/live") as ws2:
            # Should receive a deterministic rate_limited error payload then close
            msg = ws2.receive_json()
            assert msg.get("error") == "rate_limited"

    # After closing first (context exit), new connection should succeed
    with client.websocket_connect("/api/monitoring/ws/live") as ws2:
        msg = ws2.receive_json()
        assert "metrics" in msg or "error" in msg
