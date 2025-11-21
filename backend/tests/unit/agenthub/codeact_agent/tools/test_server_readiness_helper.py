from __future__ import annotations

from types import SimpleNamespace

import pytest

from forge.agenthub.codeact_agent.tools import server_readiness_helper as helper


class FakeTime:
    def __init__(self):
        self.now = 0.0

    def time(self) -> float:
        return self.now

    def sleep(self, interval: float) -> None:
        self.now += interval


def test_wait_for_server_ready_eventual_success(monkeypatch: pytest.MonkeyPatch) -> None:
    fake_time = FakeTime()
    responses = iter(
        [
            helper.requests.exceptions.RequestException("not ready"),
            SimpleNamespace(status_code=503),
            SimpleNamespace(status_code=200),
        ]
    )

    def fake_head(url, timeout, allow_redirects):
        result = next(responses)
        if isinstance(result, Exception):
            raise result
        return result

    monkeypatch.setattr(helper, "time", fake_time)
    monkeypatch.setattr(helper.requests, "head", fake_head)

    assert helper.wait_for_server_ready(
        "http://localhost:1234", max_wait_time=5, check_interval=0.5
    )


def test_wait_for_server_ready_timeout(monkeypatch: pytest.MonkeyPatch) -> None:
    fake_time = FakeTime()

    def fake_head(url, timeout, allow_redirects):
        raise helper.requests.exceptions.RequestException("down")

    monkeypatch.setattr(helper, "time", fake_time)
    monkeypatch.setattr(helper.requests, "head", fake_head)

    assert (
        helper.wait_for_server_ready(
            "http://localhost:9000", max_wait_time=0.5, check_interval=0.25
        )
        is False
    )


def test_check_server_ready(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        helper.requests,
        "head",
        lambda *_args, **_kwargs: SimpleNamespace(status_code=200),
    )
    assert helper.check_server_ready("http://localhost")

    def raising(*_args, **_kwargs):
        raise helper.requests.exceptions.RequestException

    monkeypatch.setattr(helper.requests, "head", raising)
    assert helper.check_server_ready("http://localhost") is False


def test_safe_navigate_to_url_invalid_scheme() -> None:
    original = "goto('page')"
    result = helper.safe_navigate_to_url(original, "ftp://invalid")
    assert result == original


def test_safe_navigate_to_url_wraps_browser_code() -> None:
    wrapped = helper.safe_navigate_to_url("goto('page')", "https://example.com")
    assert "wait_for_server()" in wrapped
    assert "goto('page')" in wrapped


def test_create_safe_navigation_browser_code_appends_actions() -> None:
    code = helper.create_safe_navigation_browser_code(
        "https://example.com",
        additional_actions="click('button')",
    )
    assert 'goto("https://example.com")' in code
    assert "click('button')" in code

