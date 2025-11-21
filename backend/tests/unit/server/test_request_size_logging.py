import logging
from fastapi import FastAPI
from fastapi.testclient import TestClient
from starlette.middleware.base import BaseHTTPMiddleware

from forge.server.middleware.request_tracing import RequestTracingMiddleware
from forge.server.middleware.request_size import RequestSizeLoggingMiddleware
from forge.core.logger import ACCESS_logger


class _ListHandler(logging.Handler):
    def __init__(self):
        super().__init__()
        self.records = []

    def emit(self, record: logging.LogRecord) -> None:
        self.records.append(record)


def test_request_size_logging_headers_only():
    app = FastAPI()
    app.add_middleware(
        BaseHTTPMiddleware, dispatch=RequestTracingMiddleware(enabled=True)
    )
    app.add_middleware(
        BaseHTTPMiddleware, dispatch=RequestSizeLoggingMiddleware(enabled=True)
    )

    @app.post("/echo")
    def echo(data: dict):
        return {"received": True, "len": len(str(data))}

    client = TestClient(app)
    h = _ListHandler()
    ACCESS_logger.addHandler(h)
    try:
        payload = {"hello": "world", "n": 123}
        r = client.post("/echo", json=payload)
        assert r.status_code == 200
        # Find the size log record
        size_records = [rec for rec in h.records if rec.getMessage() == "Request sizes"]
        assert size_records, "Expected a 'Request sizes' log entry"
        # Validate fields are present, integers or None
        found = False
        for rec in size_records:
            if getattr(rec, "path", None) == "/echo":
                req_len = getattr(rec, "request_content_length", None)
                resp_len = getattr(rec, "response_content_length", None)
                # Content-Length headers should be present and positive
                assert isinstance(req_len, int) and req_len > 0
                assert isinstance(resp_len, int) and resp_len > 0
                found = True
                break
        assert found, "Did not find size record for /echo"
    finally:
        ACCESS_logger.removeHandler(h)
