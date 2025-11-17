import logging
from fastapi import FastAPI
from fastapi.testclient import TestClient
from starlette.middleware.base import BaseHTTPMiddleware

from forge.server.middleware.request_tracing import RequestTracingMiddleware
from forge.core.logger import ACCESS_logger


class _ListHandler(logging.Handler):
    def __init__(self):
        super().__init__()
        self.records = []

    def emit(self, record: logging.LogRecord) -> None:
        self.records.append(record)


def test_access_logger_emits_basic_lines():
    app = FastAPI()
    app.add_middleware(
        BaseHTTPMiddleware, dispatch=RequestTracingMiddleware(enabled=True)
    )

    @app.get("/ping")
    def ping():
        return {"ok": True}

    client = TestClient(app)
    h = _ListHandler()
    ACCESS_logger.addHandler(h)
    try:
        r = client.get("/ping", headers={"User-Agent": "pytest"})
        assert r.status_code == 200
        messages = [rec.getMessage() for rec in h.records]
        assert any("Request started: GET /ping" in m for m in messages)
        assert any("Request completed: GET /ping" in m for m in messages)
    finally:
        ACCESS_logger.removeHandler(h)
