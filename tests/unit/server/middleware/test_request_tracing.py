"""Unit tests for request tracing middleware."""

from __future__ import annotations

import logging
from collections import deque

import pytest

from starlette.requests import Request
from starlette.responses import Response

from forge.server.middleware.request_tracing import (
    RequestTracingMiddleware,
    RequestIDFilter,
    EnhancedJSONFormatter,
    get_current_request_id,
    _request_id_ctx_var,
    logger as tracing_logger,
    time as tracing_time,
)


def _make_request(path: str = "/api/test", method: str = "GET") -> Request:
    scope = {
        "type": "http",
        "http_version": "1.1",
        "method": method,
        "path": path,
        "raw_path": path.encode(),
        "query_string": b"",
        "headers": [],
        "client": ("127.0.0.1", 12345),
        "server": ("localhost", 80),
        "scheme": "http",
    }
    request = Request(scope)
    return request


@pytest.mark.asyncio
async def test_request_tracing_assigns_request_id(monkeypatch):
    middleware = RequestTracingMiddleware(enabled=True)

    async def call_next(request):
        assert get_current_request_id() == request.state.request_id
        return Response(content="ok")

    request = _make_request()
    response = await middleware(request, call_next)
    assert "X-Request-ID" in response.headers
    assert "X-Response-Time" in response.headers
    _request_id_ctx_var.set(None)
    assert get_current_request_id() is None


@pytest.mark.asyncio
async def test_request_tracing_respects_existing_id():
    middleware = RequestTracingMiddleware()

    async def call_next(request):
        assert request.state.request_id == "abc-123"
        return Response(content="ok")

    request = _make_request()
    request.headers.__dict__["_list"].append((b"x-request-id", b"abc-123"))
    response = await middleware(request, call_next)
    assert response.headers["X-Request-ID"] == "abc-123"


@pytest.mark.asyncio
async def test_request_tracing_disabled():
    middleware = RequestTracingMiddleware(enabled=False)

    async def call_next(request):
        return Response(content="ok")

    response = await middleware(_make_request(), call_next)
    assert "X-Request-ID" not in response.headers


@pytest.mark.asyncio
async def test_request_tracing_logs_error():
    middleware = RequestTracingMiddleware()
    captured = []

    class Handler(logging.Handler):
        def emit(self, record):
            captured.append(record)

    handler = Handler()
    tracing_logger.addHandler(handler)
    previous_level = tracing_logger.level
    tracing_logger.setLevel(logging.INFO)

    async def call_next(request):
        raise RuntimeError("boom")

    try:
        with pytest.raises(RuntimeError):
            await middleware(_make_request(), call_next)
    finally:
        tracing_logger.removeHandler(handler)
        tracing_logger.setLevel(previous_level)

    assert any("Request failed" in record.getMessage() for record in captured)


@pytest.mark.asyncio
async def test_request_tracing_warns_on_slow_request(monkeypatch):
    middleware = RequestTracingMiddleware()

    class FakeTime:
        def __init__(self):
            self.calls = 0

        def __call__(self):
            self.calls += 1
            if self.calls == 1:
                return 0.0
            return 2.0  # simulate 2 second duration

    monkeypatch.setattr(tracing_time, "time", FakeTime())

    captured = []

    class Handler(logging.Handler):
        def emit(self, record):
            captured.append(record)

    handler = Handler()
    tracing_logger.addHandler(handler)
    previous_level = tracing_logger.level
    tracing_logger.setLevel(logging.INFO)

    async def call_next(request):
        return Response(content="ok")

    try:
        response = await middleware(_make_request(), call_next)
        assert response.headers["X-Response-Time"].endswith("ms")
    finally:
        tracing_logger.removeHandler(handler)
        tracing_logger.setLevel(previous_level)

    assert any("Slow request detected" in record.getMessage() for record in captured)


def test_request_id_filter_injects_id():
    _request_id_ctx_var.set("req-1")
    record = logging.LogRecord("name", logging.INFO, __file__, 1, "msg", args=(), exc_info=None)
    log_filter = RequestIDFilter()
    assert log_filter.filter(record)
    assert record.request_id == "req-1"
    _request_id_ctx_var.set(None)


def test_enhanced_json_formatter_adds_fields():
    formatter = EnhancedJSONFormatter()
    record = logging.LogRecord("name", logging.INFO, "file.py", 10, "test", args=(), exc_info=None)
    record.request_id = "req-2"
    log_record = {}
    formatter.add_fields(log_record, record, {})
    assert log_record["request_id"] == "req-2"
    assert "timestamp" in log_record
    assert log_record["location"] == "file.py:10"
