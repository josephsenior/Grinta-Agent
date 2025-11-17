"""Isolated tests for CSRFProtection middleware.

These tests avoid importing the full forge application (and its heavy
runtime/conversation dependencies) by constructing a minimal FastAPI
app instance with the CSRFProtection middleware only.
"""

from fastapi import FastAPI
from fastapi.testclient import TestClient
from starlette.middleware.base import BaseHTTPMiddleware

from forge.server.middleware.security_headers import CSRFProtection


def build_app(csrf_enabled: bool) -> TestClient:
    app = FastAPI()
    # Add CSRF middleware with desired enabled flag
    app.add_middleware(
        BaseHTTPMiddleware, dispatch=CSRFProtection(enabled=csrf_enabled)
    )

    @app.post("/submit")
    def submit():  # pragma: no cover - trivial handler
        return {"ok": True}

    return TestClient(app)


def test_csrf_disabled_allows_post_without_headers():
    client = build_app(csrf_enabled=False)
    r = client.post("/submit")
    # Should succeed (200) when disabled, not 403
    assert r.status_code == 200


def test_csrf_enabled_blocks_missing_headers():
    client = build_app(csrf_enabled=True)
    r = client.post("/submit")
    assert r.status_code == 403
    assert r.json()["detail"].startswith("CSRF validation failed: Missing")


def test_csrf_enabled_allows_valid_origin():
    client = build_app(csrf_enabled=True)
    headers = {"Origin": "http://testserver"}
    r = client.post("/submit", headers=headers)
    assert r.status_code == 200


def test_csrf_enabled_allows_valid_referer():
    client = build_app(csrf_enabled=True)
    headers = {"Referer": "http://testserver/page"}
    r = client.post("/submit", headers=headers)
    assert r.status_code == 200
