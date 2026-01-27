from __future__ import annotations

from datetime import datetime, timezone
from unittest.mock import AsyncMock

import pytest
from pydantic import SecretStr

from forge.integrations.github.github_service import GitHubService
from forge.integrations.service_types import Comment


class StubGitHubResolver(GitHubService):
    def __init__(self) -> None:
        super().__init__(token=SecretStr("token"))
        self._responses: list[tuple[dict | list, dict]] = []
        self._graphql_responses: list[dict] = []
        self._make_request = AsyncMock(side_effect=self._responses_handler)
        self.execute_graphql_query = AsyncMock(side_effect=self._graphql_handler)

    def prime_http(self, *responses: tuple[dict | list, dict]) -> None:
        self._responses.extend(responses)

    def prime_graphql(self, *responses: dict) -> None:
        self._graphql_responses.extend(responses)

    async def _responses_handler(self, *_, **__) -> tuple[dict | list, dict]:
        if not self._responses:
            raise AssertionError("No HTTP responses primed")
        return self._responses.pop(0)

    async def _graphql_handler(self, *_args, **_kwargs) -> dict:
        if not self._graphql_responses:
            raise AssertionError("No GraphQL responses primed")
        return self._graphql_responses.pop(0)


def _make_comment(
    comment_id: str,
    body: str,
    author: str = "octocat",
    created: str = "2024-01-01T00:00:00Z",
    updated: str | None = None,
) -> dict:
    return {
        "id": comment_id,
        "body": body,
        "author": {"login": author},
        "createdAt": created,
        "updatedAt": updated,
    }


@pytest.mark.asyncio
async def test_get_issue_or_pr_title_and_body() -> None:
    resolver = StubGitHubResolver()
    resolver.prime_http(({"title": "Bug", "body": "Details"}, {}))

    title, body = await resolver.get_issue_or_pr_title_and_body("owner/repo", 5)

    assert title == "Bug"
    assert body == "Details"
    resolver._make_request.assert_awaited_once()


@pytest.mark.asyncio
async def test_get_issue_or_pr_comments_paginates_and_truncates() -> None:
    resolver = StubGitHubResolver()
    page1 = (
        [
            _make_comment("1", "First comment"),
        ],
        {"Link": '<https://api?page=2>; rel="next"'},
    )
    page2 = (
        [
            _make_comment("2", "Second comment"),
        ],
        {},
    )
    resolver.prime_http(page1, page2)

    comments = await resolver.get_issue_or_pr_comments("owner/repo", 1, max_comments=3)

    assert [comment.id for comment in comments] == ["1", "2"]
    assert comments[0].body == "First comment"


@pytest.mark.asyncio
async def test_get_review_thread_comments_full_flow() -> None:
    resolver = StubGitHubResolver()
    comment_node = {
        "id": "comment-node",
        "replyTo": {"id": "root-comment"},
        "pullRequest": {"number": 42},
        "subject": {"repository": {"nameWithOwner": "owner/repo"}},
    }
    threads_data = {
        "data": {
            "repository": {
                "pullRequest": {
                    "reviewThreads": {
                        "nodes": [
                            {
                                "id": "thread-1",
                                "comments": {"nodes": [{"id": "root-comment"}]},
                            }
                        ],
                        "pageInfo": {"hasNextPage": False, "endCursor": None},
                    }
                }
            }
        }
    }
    resolver.prime_graphql({"data": {"node": comment_node}}, threads_data)
    resolver._get_all_thread_comments = AsyncMock(
        return_value=[
            {
                "id": "root-comment",
                "body": "Root",
                "author": {"login": "octocat"},
                "createdAt": "2024-01-01T00:00:00Z",
            },
            {
                "id": "reply",
                "body": "Reply",
                "author": {"login": "octocat"},
                "createdAt": "2024-01-02T00:00:00Z",
            },
        ],
    )

    comments = await resolver.get_review_thread_comments(
        "comment-node", "owner/repo", 42
    )

    assert [comment.id for comment in comments] == ["root-comment", "reply"]
    assert resolver.execute_graphql_query.await_count == 2


@pytest.mark.asyncio
async def test_get_all_thread_comments_paginates(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    resolver = StubGitHubResolver()
    thread_comments_page1 = {
        "data": {
            "node": {
                "comments": {
                    "nodes": [
                        _make_comment("root-comment", "Root"),
                    ],
                    "pageInfo": {"hasNextPage": True, "endCursor": "cursor"},
                }
            }
        }
    }
    thread_comments_page2 = {
        "data": {
            "node": {
                "comments": {
                    "nodes": [
                        _make_comment("reply", "Reply"),
                    ],
                    "pageInfo": {"hasNextPage": False, "endCursor": None},
                }
            }
        }
    }
    resolver.prime_graphql(thread_comments_page1, thread_comments_page2)

    raw_comments = await resolver._get_all_thread_comments("thread-1")
    comments = resolver._process_raw_comments(raw_comments)

    assert [comment.id for comment in comments] == ["root-comment", "reply"]
    assert comments[0].created_at.tzinfo == timezone.utc


@pytest.mark.asyncio
async def test_find_thread_id_paginates(monkeypatch: pytest.MonkeyPatch) -> None:
    resolver = StubGitHubResolver()
    threads_page1 = {
        "data": {
            "repository": {
                "pullRequest": {
                    "reviewThreads": {
                        "nodes": [],
                        "pageInfo": {"hasNextPage": True, "endCursor": "cursor-1"},
                    }
                }
            }
        }
    }
    threads_page2 = {
        "data": {
            "repository": {
                "pullRequest": {
                    "reviewThreads": {
                        "nodes": [
                            {
                                "id": "thread-42",
                                "comments": {"nodes": [{"id": "root-comment"}]},
                            }
                        ],
                        "pageInfo": {"hasNextPage": False, "endCursor": None},
                    }
                }
            }
        }
    }
    resolver.prime_graphql(threads_page1, threads_page2)

    thread_id = await resolver._find_thread_id("root-comment", "owner", "repo", 7)

    assert thread_id == "thread-42"


@pytest.mark.asyncio
async def test_get_all_thread_comments_handles_missing_node() -> None:
    resolver = StubGitHubResolver()
    resolver.prime_graphql({"data": {"node": None}})

    comments = await resolver._get_all_thread_comments("thread-1")

    assert comments == []


@pytest.mark.asyncio
async def test_get_review_thread_comments_missing_comment_node() -> None:
    resolver = StubGitHubResolver()
    resolver.prime_graphql({"data": {"node": None}})

    comments = await resolver.get_review_thread_comments("comment", "owner/repo", 10)

    assert comments == []


@pytest.mark.asyncio
async def test_get_review_thread_comments_missing_thread_logs(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    resolver = StubGitHubResolver()
    resolver.prime_graphql(
        {"data": {"node": {"id": "comment", "replyTo": None}}},
        {
            "data": {
                "repository": {
                    "pullRequest": {
                        "reviewThreads": {
                            "nodes": [],
                            "pageInfo": {"hasNextPage": False, "endCursor": None},
                        }
                    }
                }
            }
        },
    )
    warnings: list[str] = []

    def capture_warning(message: str, *_, **__):
        warnings.append(message)

    monkeypatch.setattr(
        "forge.integrations.github.service.resolver.logger.warning", capture_warning
    )

    comments = await resolver.get_review_thread_comments("comment", "owner/repo", 10)

    assert comments == []
    assert warnings


def test_find_root_comment_id_prefers_reply_to() -> None:
    resolver = GitHubService(token=SecretStr("token"))
    comment_node = {"replyTo": {"id": "root"}}
    assert resolver._find_root_comment_id(comment_node, "original") == "root"
    assert resolver._find_root_comment_id({}, "original") == "original"


def test_search_threads_for_root_comment() -> None:
    resolver = GitHubService(token=SecretStr("token"))
    threads = [{"id": "thread", "comments": {"nodes": [{"id": "root"}]}}]
    assert resolver._search_threads_for_root_comment(threads, "root") == "thread"
    assert resolver._search_threads_for_root_comment(threads, "missing") is None


def test_process_raw_comments_orders_and_limits() -> None:
    resolver = GitHubService(token=SecretStr("token"))
    comments = [
        _make_comment("1", "First", created="2024-01-01T00:00:00Z"),
        _make_comment("2", "Second", created="2024-01-02T00:00:00Z"),
        _make_comment("3", "Third", created="2024-01-03T00:00:00Z"),
        {
            "id": "4",
            "body": "Legacy user comment",
            "user": {"login": "legacy"},
            "createdAt": "2024-01-04T00:00:00Z",
        },
    ]
    processed = resolver._process_raw_comments(comments, max_comments=2)
    assert [c.id for c in processed] == ["3", "4"]
    assert all(isinstance(c, Comment) for c in processed)
