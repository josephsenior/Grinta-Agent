import asyncio
from types import SimpleNamespace

import pytest
from starlette.requests import Request
from starlette.responses import Response

from forge.server.middleware.request_metrics import (
    RequestMetricsMiddleware,
    get_request_metrics_snapshot,
    reset_request_metrics,
)


def _make_request(
    path: str = "/test",
    method: str = "GET",
    headers: list[tuple[bytes, bytes]] | None = None,
) -> Request:
    scope = {
        "type": "http",
        "method": method.upper(),
        "path": path,
        "raw_path": path.encode(),
        "headers": headers or [],
        "query_string": b"",
        "client": ("127.0.0.1", 1234),
        "server": ("test", 80),
    }

    async def receive() -> dict:
        return {"type": "http.request"}

    request = Request(scope, receive)
    request.scope["route"] = SimpleNamespace(path="/route-template")
    return request


@pytest.mark.asyncio
async def test_request_metrics_success_flow():
    reset_request_metrics()
    middleware = RequestMetricsMiddleware()
    request = _make_request(headers=[(b"content-length", b"5")])
    response = Response(content=b"hello", media_type="text/plain")

    async def call_next(req: Request) -> Response:
        await asyncio.sleep(0)  # ensure timing path exercised
        return response

    await middleware(request, call_next)
    snapshot = get_request_metrics_snapshot()
    assert snapshot["request_count_total"] == 1
    assert snapshot["hist_count"] == 1
    assert snapshot["request_bytes_sum"] == 5
    assert snapshot["response_bytes_sum"] == len(response.body or b"")
    assert snapshot["by_method_status"]["GET:200"] == 1
    route_key = "GET|200|/route-template"
    assert snapshot["by_route_method_status"][route_key] == 1


@pytest.mark.asyncio
async def test_request_metrics_exception_flow():
    reset_request_metrics()
    middleware = RequestMetricsMiddleware()
    request = _make_request()

    async def call_next(req: Request) -> Response:
        raise RuntimeError("boom")

    with pytest.raises(RuntimeError):
        await middleware(request, call_next)

    snapshot = get_request_metrics_snapshot()
    assert snapshot["request_exceptions_total"] == 1
    assert snapshot["request_count_total"] == 1
    assert snapshot["hist_count"] == 0  # no duration recorded
    assert snapshot["by_method_status"]["GET:exception"] == 1
    assert snapshot["by_route_method_status"]["GET|exception|/route-template"] == 1

