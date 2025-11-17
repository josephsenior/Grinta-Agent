"""Tests for forge.resolver.interfaces.bitbucket.BitbucketIssueHandler."""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import MagicMock

import httpx
import pytest

from forge.resolver.interfaces.bitbucket import BitbucketIssueHandler


def _make_handler(
    token: str = "token", username: str | None = None
) -> BitbucketIssueHandler:
    return BitbucketIssueHandler(
        owner="owner", repo="repo", token=token, username=username
    )


def test_get_headers_bearer():
    handler = _make_handler(token="plain-token")
    headers = handler.get_headers()
    assert headers["Authorization"] == "Bearer plain-token"


def test_get_headers_basic():
    handler = _make_handler(token="user:token")
    headers = handler.get_headers()
    assert headers["Authorization"].startswith("Basic ")
    assert headers["Accept"] == "application/json"


@pytest.mark.asyncio
async def test_get_issue(monkeypatch):
    payload = {"id": 42, "title": "Issue title", "content": {"raw": "Details"}}

    class DummyResponse:
        def __init__(self):
            self._json = payload

        def raise_for_status(self):
            return None

        def json(self):
            return self._json

    class DummyClient:
        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, tb):
            return False

        async def get(self, url, headers):
            assert "issues/42" in url
            return DummyResponse()

    monkeypatch.setattr(httpx, "AsyncClient", lambda: DummyClient())
    handler = _make_handler()
    issue = await handler.get_issue(42)
    assert issue.number == 42
    assert issue.title == "Issue title"
    assert issue.body == "Details"


def test_create_pr(monkeypatch):
    response = MagicMock()
    response.raise_for_status.return_value = None
    response.json.return_value = {"links": {"html": {"href": "https://bb/pr/1"}}}
    monkeypatch.setattr(httpx, "post", lambda *a, **k: response)

    handler = _make_handler()
    url = handler.create_pr("title", "body", "feature", "main")
    assert url == "https://bb/pr/1"


def test_create_pull_request(monkeypatch):
    response = MagicMock()
    response.raise_for_status.return_value = None
    response.json.return_value = {
        "links": {"html": {"href": "https://bb/pr/2"}},
        "id": 2,
    }
    monkeypatch.setattr(httpx, "post", lambda *a, **k: response)

    handler = _make_handler()
    pr = handler.create_pull_request(
        {"title": "T", "description": "D", "source_branch": "s", "target_branch": "t"},
    )
    assert pr["html_url"] == "https://bb/pr/2"
    assert pr["number"] == 2


def test_send_comment_msg(monkeypatch):
    response = MagicMock(status_code=201)
    response.raise_for_status.return_value = None
    monkeypatch.setattr(httpx, "post", lambda *a, **k: response)

    handler = _make_handler()
    handler.send_comment_msg(10, "Looks good!")


def test_collect_issue_references():
    handler = _make_handler()
    refs = handler._collect_issue_references(
        issue_body="Fixes #1 and #2",
        review_comments=["Mention #3"],
        review_threads=[SimpleNamespace(comment="Thread mention #4")],
        thread_comments=["Another #5"],
    )
    assert sorted(refs) == [1, 2, 3, 4, 5]


def test_fetch_issue_content_success(monkeypatch):
    response = MagicMock()
    response.raise_for_status.return_value = None
    response.json.return_value = {"content": {"raw": "Body"}}
    monkeypatch.setattr(httpx, "get", lambda *a, **k: response)

    handler = _make_handler()
    body = handler._fetch_issue_content(7)
    assert body == "Body"


def test_fetch_issue_content_http_error(monkeypatch):
    def raise_error(*args, **kwargs):
        raise httpx.HTTPError("boom")

    monkeypatch.setattr(httpx, "get", raise_error)
    handler = _make_handler()
    assert handler._fetch_issue_content(8) is None


def test_get_urls_and_branch_helpers():
    handler = _make_handler()
    assert handler.get_repo_url() == "https://bitbucket.org/owner/repo"
    assert (
        handler.get_branch_url("feature")
        == "https://bitbucket.org/owner/repo/branch/feature"
    )
    assert (
        handler.get_compare_url("feature")
        == "https://bitbucket.org/owner/repo/compare/master...feature"
    )
    assert handler.get_branch_name("feature") == "feature-owner"
    assert handler.get_authorize_url() == "https://oauth2:token@bitbucket.org/"
