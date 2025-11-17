from fastapi.testclient import TestClient

from forge.server.app import app


def test_live_metrics_websocket_streams_message():
    client = TestClient(app)
    with client.websocket_connect("/api/monitoring/ws/live") as ws:
        msg = ws.receive_json()
        assert isinstance(msg, dict)
        assert "timestamp" in msg
        assert "metrics" in msg
        metrics = msg["metrics"]
        assert isinstance(metrics, dict)
        assert "system" in metrics


def test_live_metrics_websocket_multiple_messages(monkeypatch):
    # Speed up server-side loop by monkeypatching asyncio.sleep in monitoring module
    import forge.server.routes.monitoring as monitoring

    original_sleep = monitoring.asyncio.sleep

    async def fast_sleep(_seconds: float):
        # Yield control but return immediately
        await original_sleep(0)

    monkeypatch.setattr(monitoring.asyncio, "sleep", fast_sleep, raising=True)

    client = TestClient(app)
    with client.websocket_connect("/api/monitoring/ws/live") as ws:
        metrics_messages = 0
        attempts = 0
        # Collect up to 5 frames, require at least 2 metrics payloads
        while attempts < 5 and metrics_messages < 2:
            msg = ws.receive_json()
            assert isinstance(msg, dict)
            assert "timestamp" in msg
            if "metrics" in msg and isinstance(msg["metrics"], dict):
                metrics = msg["metrics"]
                assert "system" in metrics
                metrics_messages += 1
            attempts += 1
        assert metrics_messages >= 2, "Expected at least two metrics messages"
