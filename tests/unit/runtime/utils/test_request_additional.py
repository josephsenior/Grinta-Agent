from __future__ import annotations

import importlib.util
import json
import sys
import types
from pathlib import Path

import httpx
import pytest
import tenacity


ROOT = Path(__file__).resolve().parents[4]


if "forge.runtime.utils" not in sys.modules:
    sys.modules["forge.runtime.utils"] = types.ModuleType("forge.runtime.utils")

http_session_mod = sys.modules.setdefault(
    "forge.utils.http_session", types.ModuleType("forge.utils.http_session")
)
if not hasattr(http_session_mod, "HttpSession"):

    class HttpSession:
        def request(self, *args, **kwargs):
            raise NotImplementedError

    setattr(http_session_mod, "HttpSession", HttpSession)

if "forge.utils.tenacity_stop" not in sys.modules:
    tenacity_stop_stub = types.ModuleType("forge.utils.tenacity_stop")

    def stop_if_should_exit():
        from tenacity import stop

        return stop.stop_never

    setattr(tenacity_stop_stub, "stop_if_should_exit", stop_if_should_exit)
    sys.modules["forge.utils.tenacity_stop"] = tenacity_stop_stub

logger_mod = sys.modules.setdefault(
    "forge.core.logger", types.ModuleType("forge.core.logger")
)
if not hasattr(logger_mod, "forge_logger"):

    class StubLogger:
        def debug(self, *args, **kwargs):
            pass

        def info(self, *args, **kwargs):
            pass

        def warning(self, *args, **kwargs):
            pass

    setattr(logger_mod, "forge_logger", StubLogger())

spec = importlib.util.spec_from_file_location(
    "forge.runtime.utils.request",
    ROOT / "forge" / "runtime" / "utils" / "request.py",
)
assert spec and spec.loader
request_mod = importlib.util.module_from_spec(spec)
sys.modules["forge.runtime.utils.request"] = request_mod
spec.loader.exec_module(request_mod)

RequestHTTPError = request_mod.RequestHTTPError
is_retryable_error = request_mod.is_retryable_error
send_request = request_mod.send_request


class DummySession:
    def __init__(self, responses):
        self.responses = list(responses)
        self.calls = []

    def request(self, method, url, timeout=60, **kwargs):
        self.calls.append((method, url, timeout, kwargs))
        return self.responses.pop(0)


def make_response(status: int, *, json_body: dict | None = None) -> httpx.Response:
    request = httpx.Request("GET", "https://example.com")
    content = None
    if json_body is not None:
        content = json.dumps(json_body).encode("utf-8")
    return httpx.Response(status, request=request, content=content)


def test_request_http_error_str_includes_details():
    request = httpx.Request("GET", "https://example.com")
    response = httpx.Response(400, request=request)
    error = RequestHTTPError(
        "message", request=request, response=response, detail={"info": "bad"}
    )
    assert "Details" in str(error)
    assert "info" in str(error)


def test_request_http_error_str_without_details():
    request = httpx.Request("GET", "https://example.com")
    response = httpx.Response(400, request=request)
    error = RequestHTTPError("message", request=request, response=response)
    assert "Details" not in str(error)


def test_is_retryable_error_only_for_429():
    request = httpx.Request("GET", "https://example.com")
    response = httpx.Response(429, request=request)
    exc = httpx.HTTPStatusError("Too Many Requests", request=request, response=response)
    assert is_retryable_error(exc) is True
    response_other = httpx.Response(500, request=request)
    exc_other = httpx.HTTPStatusError(
        "Server Error", request=request, response=response_other
    )
    assert is_retryable_error(exc_other) is False
    assert is_retryable_error(RuntimeError("boom")) is False


def test_send_request_success_uses_response_directly():
    response = make_response(200)
    session = DummySession([response])
    result = send_request.__wrapped__(session, "GET", "https://example.com", timeout=10)
    assert result is response
    assert session.calls == [("GET", "https://example.com", 10, {})]


def test_send_request_http_status_error_with_json_detail():
    response = make_response(400, json_body={"detail": {"error": "bad"}})
    session = DummySession([response])
    with pytest.raises(RequestHTTPError) as exc:
        send_request.__wrapped__(session, "POST", "https://example.com", data="{}")
    err = exc.value
    assert err.detail == {"error": "bad"}
    assert response.is_closed


def test_send_request_http_status_error_without_json_detail():
    response = make_response(404)
    session = DummySession([response])
    with pytest.raises(RequestHTTPError) as exc:
        send_request.__wrapped__(session, "DELETE", "https://example.com")
    err = exc.value
    assert err.detail is None
    assert response.is_closed


def test_send_request_http_error_re_raises(monkeypatch):
    class DummyResponse(httpx.Response):
        def __init__(self):
            super().__init__(
                status_code=200, request=httpx.Request("GET", "https://example.com")
            )

        def raise_for_status(self):
            raise httpx.ReadError("boom")

    response = DummyResponse()
    session = DummySession([response])
    with pytest.raises(httpx.ReadError):
        send_request.__wrapped__(session, "GET", "https://example.com")
    assert response.is_closed


def test_send_request_retries_on_429(monkeypatch):
    request = httpx.Request("GET", "https://example.com")
    first = httpx.Response(429, request=request)
    second = httpx.Response(200, request=request)
    session = DummySession([first, second])

    # Prevent tenacity sleep to keep test fast
    monkeypatch.setattr(
        "tenacity.nap.sleep", lambda *args, **kwargs: None, raising=False
    )

    result = send_request(session, "GET", "https://example.com")
    assert result is second
    assert len(session.calls) == 2


def test_send_request_retries_then_raises(monkeypatch):
    request = httpx.Request("GET", "https://example.com")
    responses = [
        httpx.Response(429, request=request),
        httpx.Response(429, request=request),
        httpx.Response(429, request=request),
    ]
    session = DummySession(responses)
    monkeypatch.setattr(
        "tenacity.nap.sleep", lambda *args, **kwargs: None, raising=False
    )

    with pytest.raises(tenacity.RetryError) as exc:
        send_request(session, "GET", "https://example.com")
    assert len(session.calls) == 3
    final_exc = exc.value.last_attempt.exception()
    assert isinstance(final_exc, RequestHTTPError)
