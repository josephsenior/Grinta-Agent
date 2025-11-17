"""Tests for compression middleware behavior."""

from __future__ import annotations

import gzip
from unittest.mock import AsyncMock

import pytest

from starlette.requests import Request
from starlette.responses import Response

from forge.server.middleware.compression import (
    CompressionMiddleware,
    ResponseSizeOptimizer,
)


def _make_request(
    path: str, method: str = "GET", headers: dict[str, str] | None = None
) -> Request:
    headers_list = []
    headers = headers or {}
    for key, value in headers.items():
        headers_list.append((key.encode("latin-1"), value.encode("latin-1")))

    scope = {
        "type": "http",
        "http_version": "1.1",
        "method": method,
        "path": path,
        "raw_path": path.encode(),
        "query_string": b"",
        "headers": headers_list,
        "client": ("test", 123),
        "server": ("test", 80),
        "scheme": "http",
    }
    return Request(scope)


@pytest.mark.parametrize(
    "path, expected",
    [
        ("/assets/app.js", CompressionMiddleware.CACHE_LONG),
        ("/favicon.ico", CompressionMiddleware.CACHE_LONG),
    ],
)
def test_add_cache_headers_static(path, expected):
    middleware = CompressionMiddleware()
    request = _make_request(path)
    response = Response(content="static content", media_type="text/plain")
    middleware._add_cache_headers(request, response)
    assert response.headers["Cache-Control"].startswith("public, max-age")
    assert str(expected) in response.headers["Cache-Control"]
    assert response.headers["Vary"] == "Accept-Encoding"


def test_add_cache_headers_cacheable_api():
    middleware = CompressionMiddleware()
    request = _make_request("/api/prompts/list")
    response = Response(content="{}", media_type="application/json")
    middleware._add_cache_headers(request, response)
    assert response.headers["Cache-Control"].startswith("public, max-age")
    assert "ETag" in response.headers


def test_add_cache_headers_default():
    middleware = CompressionMiddleware()
    request = _make_request("/dynamic/page", method="POST")
    response = Response(content="dynamic", media_type="text/html")
    middleware._add_cache_headers(request, response)
    assert response.headers["Cache-Control"] == "no-cache, no-store, must-revalidate"
    assert response.headers["Pragma"] == "no-cache"
    assert response.headers["Expires"] == "0"


@pytest.mark.asyncio
async def test_compression_middleware_compresses(monkeypatch):
    middleware = CompressionMiddleware()
    body = b"{" + b" " * 2048 + b"}"

    async def call_next(request):  # pylint: disable=unused-argument
        response = Response(content=body, media_type="application/json")
        response.headers["Content-Length"] = str(len(body))
        return response

    request = _make_request("/api/data", headers={"accept-encoding": "gzip"})
    response = await middleware(request, call_next)
    assert response.headers["Content-Encoding"] == "gzip"
    assert int(response.headers["Content-Length"]) < len(body)


@pytest.mark.asyncio
async def test_compression_middleware_skips_when_not_smaller(monkeypatch):
    middleware = CompressionMiddleware()

    # Monkeypatch gzip.compress to return a larger payload
    monkeypatch.setattr(gzip, "compress", lambda data, compresslevel=6: data + b"pad")

    async def call_next(request):  # pylint: disable=unused-argument
        response = Response(content=b"small" * 300, media_type="application/json")
        response.headers["Content-Length"] = str(len(response.body))
        return response

    request = _make_request("/api/data", headers={"accept-encoding": "gzip"})
    response = await middleware(request, call_next)
    assert "Content-Encoding" not in response.headers


def test_should_compress_checks(monkeypatch):
    middleware = CompressionMiddleware()
    request = _make_request("/api/data", headers={"accept-encoding": "gzip"})
    response = Response(content=b"{}", media_type="application/json")

    # No content-length but body smaller than threshold
    response.headers["Content-Length"] = "1"
    assert not middleware._should_compress(request, response)

    # Already encoded
    if "Content-Length" in response.headers:
        del response.headers["Content-Length"]
    response.headers["Content-Encoding"] = "gzip"
    assert not middleware._should_compress(request, response)

    # Unsupported content type
    del response.headers["Content-Encoding"]
    response.headers["content-type"] = "image/png"
    assert not middleware._should_compress(request, response)

    # No gzip accepted
    request_no_gzip = _make_request(
        "/api/data", headers={"accept-encoding": "identity"}
    )
    response.headers["content-type"] = "application/json"
    assert not middleware._should_compress(request_no_gzip, response)

    # No body present
    empty_response = Response(content=b"", media_type="application/json")
    empty_response.headers["content-type"] = "application/json"
    if "content-length" in empty_response.headers:
        del empty_response.headers["content-length"]
    assert not middleware._should_compress(request, empty_response)


@pytest.mark.asyncio
async def test_compress_response_handles_exception(monkeypatch, caplog):
    middleware = CompressionMiddleware()
    response = Response(
        content=b"{" + b" " * 2048 + b"}", media_type="application/json"
    )

    def boom(*args, **kwargs):  # pylint: disable=unused-argument
        raise RuntimeError("boom")

    monkeypatch.setattr(gzip, "compress", boom)

    await middleware._compress_response(response)


def test_response_size_optimizer_optimize_list():
    items = [
        {"id": 1, "created_at": "now", "value": "keep"},
        {"id": 2, "updated_at": "later", "__v": 0, "value": "keep"},
    ]
    optimized = ResponseSizeOptimizer.optimize_list_response(items, {"id"})
    assert all("id" not in item for item in optimized)
    assert all("value" in item for item in optimized)

    default_optimized = ResponseSizeOptimizer.optimize_list_response(items)
    assert all(
        key not in ResponseSizeOptimizer.EXCLUDE_FIELDS
        for item in default_optimized
        for key in item.keys()
    )


def test_response_size_optimizer_paginate():
    items = list(range(10))
    result = ResponseSizeOptimizer.paginate_response(
        items, page=2, page_size=3, max_page_size=5
    )
    assert result["items"] == [3, 4, 5]
    meta = result["pagination"]
    assert meta["page"] == 2
    assert meta["has_prev"] is True
    assert meta["has_next"] is True
