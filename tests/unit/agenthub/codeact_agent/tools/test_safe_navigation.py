"""Tests for safe navigation helpers and server readiness utilities."""

from __future__ import annotations

import types

import pytest

from forge.agenthub.codeact_agent.tools import safe_navigation
from forge.agenthub.codeact_agent.tools import server_readiness_helper as readiness


def test_safe_goto_localhost_returns_custom_code() -> None:
    code = safe_navigation.safe_goto_localhost("http://localhost:5000", max_wait=5, check_interval=0.5)
    assert "wait_for_server_ready" in code
    assert "goto(\"http://localhost:5000\")" in code


def test_safe_goto_localhost_passthrough_for_remote() -> None:
    assert safe_navigation.safe_goto_localhost("https://example.com") == "goto('https://example.com')"


def test_create_safe_navigation_browser_code_appends_actions() -> None:
    code = safe_navigation.create_safe_navigation_browser_code(
        "https://example.com",
        additional_actions="click('button')",
    )
    assert "goto('https://example.com')" in code
    assert "click('button')" in code


def test_wait_for_server_ready_success(monkeypatch: pytest.MonkeyPatch) -> None:
    responses = iter([
        types.SimpleNamespace(status_code=503),
        types.SimpleNamespace(status_code=200),
    ])

    def fake_head(url, timeout, allow_redirects):
        return next(responses)

    monkeypatch.setattr(readiness.requests, "head", fake_head)
    monkeypatch.setattr(readiness.time, "sleep", lambda *args, **kwargs: None)

    assert readiness.wait_for_server_ready("http://localhost:8000", max_wait_time=2, check_interval=0.01)


def test_wait_for_server_ready_timeout(monkeypatch: pytest.MonkeyPatch) -> None:
    def fake_head(url, timeout, allow_redirects):
        raise readiness.requests.exceptions.RequestException("down")

    monkeypatch.setattr(readiness.requests, "head", fake_head)
    monkeypatch.setattr(readiness.time, "sleep", lambda *args, **kwargs: None)
    assert readiness.wait_for_server_ready("http://localhost:8000", max_wait_time=0, check_interval=0.01) is False


def test_check_server_ready(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(readiness.requests, "head", lambda *args, **kwargs: types.SimpleNamespace(status_code=200))
    assert readiness.check_server_ready("http://localhost")

    def raising(*args, **kwargs):
        raise readiness.requests.exceptions.RequestException

    monkeypatch.setattr(readiness.requests, "head", raising)
    assert readiness.check_server_ready("http://localhost") is False


def test_safe_navigate_to_url_invalid_scheme(monkeypatch: pytest.MonkeyPatch) -> None:
    original = "goto('page')"
    result = readiness.safe_navigate_to_url(original, "ftp://invalid")
    assert result == original


def test_safe_navigate_to_url_wraps_browser_code(monkeypatch: pytest.MonkeyPatch) -> None:
    wrapped = readiness.safe_navigate_to_url("goto('page')", "https://example.com")
    assert "wait_for_server()" in wrapped
    assert "goto('page')" in wrapped


def test_create_safe_navigation_browser_code_includes_additional_actions() -> None:
    code = readiness.create_safe_navigation_browser_code(
        "https://example.com",
        additional_actions="click('button')",
    )
    assert "goto(\"https://example.com\")" in code
    assert "click('button')" in code

