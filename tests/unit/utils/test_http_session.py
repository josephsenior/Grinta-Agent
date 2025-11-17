from unittest.mock import MagicMock

import pytest

from forge.utils import http_session
from forge.utils.http_session import HttpSession


@pytest.fixture(autouse=True)
def reset_client(monkeypatch):
    client = MagicMock()
    monkeypatch.setattr(http_session, "CLIENT", client)
    logger = MagicMock()
    monkeypatch.setattr(http_session, "logger", logger)
    yield client, logger


def test_http_session_request_merges_headers(reset_client):
    client, _ = reset_client
    session = HttpSession()
    session.headers["X-Default"] = "one"
    session.request("GET", "http://example.com", headers={"X-Custom": "two"})
    client.request.assert_called_once()
    args, kwargs = client.request.call_args
    assert args[0] == "GET"
    assert kwargs["headers"] == {"X-Default": "one", "X-Custom": "two"}
    assert session._is_closed is False


def test_http_session_stream_merges_headers(reset_client):
    client, _ = reset_client
    session = HttpSession()
    session.headers["X-Default"] = "one"
    session.stream("GET", "http://example.com", headers={"X-Custom": "two"})
    client.stream.assert_called_once()
    _, kwargs = client.stream.call_args
    assert kwargs["headers"] == {"X-Default": "one", "X-Custom": "two"}


def test_http_session_reuse_after_close_logs(reset_client):
    client, logger = reset_client
    session = HttpSession()
    session.close()
    session.get("http://example.com")
    logger.error.assert_called_once()
    client.request.assert_called_once()
    assert session._is_closed is False


def test_http_session_stream_reuse_after_close_logs(reset_client):
    client, logger = reset_client
    session = HttpSession()
    session.close()
    session.stream("GET", "http://example.com")
    logger.error.assert_called_once()
    client.stream.assert_called_once()
    assert session._is_closed is False


def test_http_session_verbs_delegate(reset_client):
    client, _ = reset_client
    session = HttpSession()
    session.post("http://example.com", json={"a": 1})
    session.patch("http://example.com")
    session.put("http://example.com")
    session.delete("http://example.com")
    session.options("http://example.com")
    assert client.request.call_count == 5
