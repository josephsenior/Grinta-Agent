from __future__ import annotations

import importlib.util
import sys
import types
from pathlib import Path

import pytest
import requests


MODULE_PATH = (
    Path(__file__).resolve().parents[4]
    / "forge"
    / "runtime"
    / "utils"
    / "server_detector.py"
)
spec = importlib.util.spec_from_file_location(
    "forge.runtime.utils.server_detector", MODULE_PATH
)
assert spec and spec.loader
server_detector = importlib.util.module_from_spec(spec)
sys.modules["forge.runtime.utils.server_detector"] = server_detector
spec.loader.exec_module(server_detector)

extract_port_from_output = server_detector.extract_port_from_output
is_port_listening = server_detector.is_port_listening
health_check_http = server_detector.health_check_http
detect_server_from_output = server_detector.detect_server_from_output
DetectedServer = server_detector.DetectedServer


def test_extract_port_from_output_detects_port(caplog):
    output = "Server is listening on port 34567\n"
    result = extract_port_from_output(output)
    assert result == (34567, "http", "Server is listening on port 34567")


def test_extract_port_from_output_ignores_low_port():
    output = "Server running at http://localhost:80"
    result = extract_port_from_output(output)
    assert result is None


def test_extract_port_from_output_no_match():
    output = "Nothing to see here"
    assert extract_port_from_output(output) is None


def test_extract_port_handles_invalid_pattern(monkeypatch):
    original = server_detector.SERVER_START_PATTERNS
    monkeypatch.setattr(
        server_detector,
        "SERVER_START_PATTERNS",
        original + [("broken pattern", "http")],
        raising=False,
    )
    assert extract_port_from_output("broken pattern") is None


def test_is_port_listening_true(monkeypatch):
    class DummySocket:
        def __init__(self, *args, **kwargs):
            self.closed = False

        def settimeout(self, timeout):
            self.timeout = timeout

        def connect_ex(self, addr):
            return 0

        def close(self):
            self.closed = True

    monkeypatch.setattr(
        server_detector.socket,
        "socket",
        lambda *args, **kwargs: DummySocket(),
        raising=False,
    )
    assert is_port_listening(40000) is True


def test_is_port_listening_false(monkeypatch):
    class DummySocket:
        def settimeout(self, timeout):
            self.timeout = timeout

        def connect_ex(self, addr):
            return 1

        def close(self):
            pass

    monkeypatch.setattr(
        server_detector.socket,
        "socket",
        lambda *args, **kwargs: DummySocket(),
        raising=False,
    )
    assert is_port_listening(40001) is False


def test_is_port_listening_oserror(monkeypatch):
    class DummySocket:
        def settimeout(self, timeout):
            pass

        def connect_ex(self, addr):
            raise OSError("boom")

        def close(self):
            pass

    monkeypatch.setattr(
        server_detector.socket,
        "socket",
        lambda *args, **kwargs: DummySocket(),
        raising=False,
    )
    assert is_port_listening(40002) is False


def test_health_check_http_success(monkeypatch):
    class DummyResponse:
        def __init__(self, status_code):
            self.status_code = status_code

    monkeypatch.setattr(
        server_detector.requests,
        "get",
        lambda *args, **kwargs: DummyResponse(200),
        raising=False,
    )
    assert health_check_http(35555) == "healthy"


def test_health_check_http_failure(monkeypatch):
    class DummyResponse:
        def __init__(self, status_code):
            self.status_code = status_code

    monkeypatch.setattr(
        server_detector.requests,
        "get",
        lambda *args, **kwargs: DummyResponse(502),
        raising=False,
    )
    assert health_check_http(35556) == "unhealthy"


def test_health_check_http_exception(monkeypatch):
    def raise_exc(*args, **kwargs):
        raise requests.RequestException("boom")

    monkeypatch.setattr(server_detector.requests, "get", raise_exc, raising=False)
    assert health_check_http(35557) == "unhealthy"


def test_detect_server_success(monkeypatch):
    output = "Server listening on port 34567"
    monkeypatch.setattr(
        server_detector, "is_port_listening", lambda port: True, raising=False
    )
    monkeypatch.setattr(
        server_detector, "health_check_http", lambda port: "healthy", raising=False
    )
    server = detect_server_from_output(output, perform_health_check=True)
    assert isinstance(server, DetectedServer)
    assert server.port == 34567
    assert server.health_status == "healthy"


def test_detect_server_port_not_listening(monkeypatch):
    output = "Server listening on port 34567"
    monkeypatch.setattr(
        server_detector, "is_port_listening", lambda port: False, raising=False
    )
    assert detect_server_from_output(output) is None


def test_detect_server_unhealthy(monkeypatch):
    output = "Server listening on port 34567"
    monkeypatch.setattr(
        server_detector, "is_port_listening", lambda port: True, raising=False
    )
    monkeypatch.setattr(
        server_detector, "health_check_http", lambda port: "unhealthy", raising=False
    )
    server = detect_server_from_output(output, perform_health_check=True)
    assert server is not None
    assert server.health_status == "unhealthy"


def test_detect_server_no_pattern(monkeypatch):
    monkeypatch.setattr(
        server_detector, "extract_port_from_output", lambda output: None, raising=False
    )
    assert detect_server_from_output("no server here") is None
