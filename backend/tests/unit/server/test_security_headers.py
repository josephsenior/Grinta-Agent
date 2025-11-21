import os
from fastapi.testclient import TestClient

from forge.server.app import app
from fastapi import FastAPI
from starlette.middleware.base import BaseHTTPMiddleware
from forge.server.middleware.security_headers import SecurityHeadersMiddleware


def _get_headers(path: str = "/health"):
    client = TestClient(app)
    resp = client.get(path)
    return resp.headers


def test_security_headers_permissive(monkeypatch):
    monkeypatch.setenv("CSP_POLICY", "permissive")
    monkeypatch.delenv("CSP_REPORT_ONLY", raising=False)
    h = _get_headers()
    assert "Content-Security-Policy" in h
    # Expect unsafe-inline present in permissive mode
    assert "unsafe-inline" in h["Content-Security-Policy"]
    assert "Content-Security-Policy-Report-Only" not in h


def test_security_headers_strict_isolation():
    # Build isolated app with strict profile to avoid global env coupling
    local_app = FastAPI()
    local_app.add_middleware(
        BaseHTTPMiddleware,
        dispatch=SecurityHeadersMiddleware(enabled=True, csp_profile="strict"),
    )

    @local_app.get("/ping")
    def ping():
        return {"ok": True}

    client = TestClient(local_app)
    r = client.get("/ping")
    assert r.status_code == 200
    csp = r.headers.get("Content-Security-Policy")
    assert csp and "unsafe-inline" not in csp


def test_security_headers_report_only_isolation():
    # In isolation, middleware reads env at call-time for report-only and report-uri
    os.environ["CSP_REPORT_ONLY"] = "1"
    os.environ["CSP_REPORT_URI"] = "https://example.com/csp-report"
    try:
        local_app = FastAPI()
        local_app.add_middleware(
            BaseHTTPMiddleware,
            dispatch=SecurityHeadersMiddleware(enabled=True, csp_profile="strict"),
        )

        @local_app.get("/ping")
        def ping():
            return {"ok": True}

        client = TestClient(local_app)
        r = client.get("/ping")
        assert "Content-Security-Policy" not in r.headers
        ro = r.headers.get("Content-Security-Policy-Report-Only")
        assert ro and "report-uri https://example.com/csp-report" in ro
    finally:
        os.environ.pop("CSP_REPORT_ONLY", None)
        os.environ.pop("CSP_REPORT_URI", None)


def test_hsts_sent_on_https(monkeypatch):
    # Simulate https by monkeypatching request URL scheme via TestClient base_url
    client = TestClient(app, base_url="https://testserver")
    r = client.get("/health")
    # Strict-Transport-Security only if https
    assert "Strict-Transport-Security" in r.headers


def test_no_hsts_on_http(monkeypatch):
    client = TestClient(app, base_url="http://testserver")
    r = client.get("/health")
    assert "Strict-Transport-Security" not in r.headers
