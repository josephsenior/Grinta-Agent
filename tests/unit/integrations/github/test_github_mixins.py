from __future__ import annotations

import base64
from datetime import datetime
from types import SimpleNamespace
from unittest.mock import AsyncMock

import httpx
import pytest
from pydantic import SecretStr

from forge.integrations.github.github_service import GitHubService
from forge.integrations.service_types import ProviderType, SuggestedTask, TaskType
from forge.server.types import AppMode


class DummyResponse:
    def __init__(
        self,
        status_code: int = 200,
        payload: dict | list | None = None,
        headers: dict | None = None,
    ):
        self.status_code = status_code
        self._payload = payload or {}
        self.headers = headers or {}

    def json(self):
        return self._payload

    def raise_for_status(self) -> None:
        if self.status_code >= 400:
            raise httpx.HTTPStatusError("error", request=None, response=None)


@pytest.mark.asyncio
async def test_github_get_latest_token_returns_current() -> None:
    token = SecretStr("token")
    service = GitHubService(token=token)

    latest = await service.get_latest_token()

    assert latest is token


def test_github_custom_base_domain_updates_urls() -> None:
    service = GitHubService(token=SecretStr("token"), base_domain="github.example.com")
    assert service.BASE_URL == "https://github.example.com/api/v3"
    assert service.GRAPHQL_URL == "https://github.example.com/api/graphql"


def test_github_provider_property() -> None:
    service = GitHubService(token=SecretStr("token"))
    assert service.provider == ProviderType.GITHUB.value


@pytest.mark.asyncio
async def test_github_verify_access_calls_make_request(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    service = GitHubService(token=SecretStr("token"))
    service._make_request = AsyncMock(return_value=({}, {}))

    result = await service.verify_access()

    assert result is True
    service._make_request.assert_awaited_once()


@pytest.mark.asyncio
async def test_github_get_headers_fetches_latest_token(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    service = GitHubService(token=None)
    latest = SecretStr("latest-token")
    monkeypatch.setattr(service, "get_latest_token", AsyncMock(return_value=latest))

    headers = await service._get_headers()

    service.get_latest_token.assert_awaited_once()
    assert headers["Authorization"] == f"Bearer {latest.get_secret_value()}"
    assert headers["Accept"] == "application/vnd.github.v3+json"


@pytest.mark.asyncio
async def test_github_make_request_refreshes_and_preserves_link(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    service = GitHubService(token=SecretStr("stale"))
    service.refresh = True
    response_401 = DummyResponse(status_code=401, payload={})
    response_ok = DummyResponse(
        status_code=200, payload={"ok": True}, headers={"Link": '<next>; rel="next"'}
    )
    service.execute_request = AsyncMock(side_effect=[response_401, response_ok])
    monkeypatch.setattr(service, "_has_token_expired", lambda status: status == 401)
    monkeypatch.setattr(
        service, "get_latest_token", AsyncMock(return_value=SecretStr("fresh"))
    )

    payload, headers = await service._make_request("https://example.com/api")

    assert payload == {"ok": True}
    assert headers["Link"] == '<next>; rel="next"'
    service.get_latest_token.assert_awaited_once()
    assert service.execute_request.await_count == 2


@pytest.mark.asyncio
async def test_github_make_request_handles_http_status_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    service = GitHubService(token=SecretStr("token"))
    request = httpx.Request("GET", "https://example.com")
    response = httpx.Response(status_code=401, request=request)
    error = httpx.HTTPStatusError("unauthorized", request=request, response=response)
    service.execute_request = AsyncMock(side_effect=error)
    monkeypatch.setattr(
        service, "handle_http_status_error", lambda exc: RuntimeError("status")
    )

    with pytest.raises(RuntimeError):
        await service._make_request("https://example.com")


@pytest.mark.asyncio
async def test_github_make_request_handles_http_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    service = GitHubService(token=SecretStr("token"))
    request = httpx.Request("GET", "https://example.com")
    error = httpx.HTTPError("network")
    service.execute_request = AsyncMock(side_effect=error)
    monkeypatch.setattr(
        service, "handle_http_error", lambda exc: RuntimeError("http-error")
    )

    with pytest.raises(RuntimeError):
        await service._make_request("https://example.com")


@pytest.mark.asyncio
async def test_github_execute_graphql_query_success(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    service = GitHubService(token=SecretStr("token"))

    class GraphQLClient:
        def __init__(self) -> None:
            self.called_with: dict | None = None

        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, tb):
            return False

        async def post(self, url: str, headers: dict, json: dict):
            self.called_with = {"url": url, "json": json}
            return DummyResponse(payload={"data": {"ok": True}})

    graphql_client = GraphQLClient()
    monkeypatch.setattr(httpx, "AsyncClient", lambda: graphql_client)

    result = await service.execute_graphql_query("query", {"a": 1})

    assert result == {"data": {"ok": True}}
    assert graphql_client.called_with["json"]["query"] == "query"


@pytest.mark.asyncio
async def test_github_execute_graphql_query_raises_unknown(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    service = GitHubService(token=SecretStr("token"))

    class ErrorClient:
        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, tb):
            return False

        async def post(self, url: str, headers: dict, json: dict):
            return DummyResponse(payload={"errors": [{"message": "boom"}]})

    monkeypatch.setattr(httpx, "AsyncClient", ErrorClient)

    with pytest.raises(Exception):
        await service.execute_graphql_query("query", {})


@pytest.mark.asyncio
async def test_github_execute_graphql_query_handles_http_status_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    service = GitHubService(token=SecretStr("token"))

    class ErrorClient:
        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, tb):
            return False

        async def post(self, *_args, **_kwargs):
            request = httpx.Request("POST", "https://api.github.com/graphql")
            response = httpx.Response(status_code=500, request=request)
            raise httpx.HTTPStatusError("server", request=request, response=response)

    monkeypatch.setattr(
        service, "handle_http_status_error", lambda exc: RuntimeError("graphql-status")
    )
    monkeypatch.setattr(httpx, "AsyncClient", ErrorClient)

    with pytest.raises(RuntimeError):
        await service.execute_graphql_query("query", {})


@pytest.mark.asyncio
async def test_github_execute_graphql_query_handles_http_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    service = GitHubService(token=SecretStr("token"))

    class ErrorClient:
        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, tb):
            return False

        async def post(self, *_args, **_kwargs):
            request = httpx.Request("POST", "https://api.github.com/graphql")
            raise httpx.HTTPError("network")

    monkeypatch.setattr(
        service, "handle_http_error", lambda exc: RuntimeError("graphql-http-error")
    )
    monkeypatch.setattr(httpx, "AsyncClient", ErrorClient)

    with pytest.raises(RuntimeError):
        await service.execute_graphql_query("query", {})


@pytest.mark.asyncio
async def test_github_get_user_parses_profile(monkeypatch: pytest.MonkeyPatch) -> None:
    service = GitHubService(token=SecretStr("token"))
    service._make_request = AsyncMock(
        return_value=(
            {
                "id": 123,
                "login": "octocat",
                "avatar_url": "https://avatars/1",
                "company": "GitHub",
                "name": "Octo Cat",
                "email": "cat@example.com",
            },
            {},
        )
    )

    user = await service.get_user()

    assert user.id == "123"
    assert user.login == "octocat"
    assert user.avatar_url.endswith("/1")
    assert user.company == "GitHub"


@pytest.mark.asyncio
async def test_github_get_branches_paginates(monkeypatch: pytest.MonkeyPatch) -> None:
    service = GitHubService(token=SecretStr("token"))
    page1 = (
        [
            {
                "name": "main",
                "commit": {
                    "sha": "a",
                    "commit": {"committer": {"date": "2024-01-01T00:00:00Z"}},
                },
            },
        ],
        {"Link": '<next>; rel="next"'},
    )
    page2 = (
        [
            {
                "name": "dev",
                "commit": {
                    "sha": "b",
                    "commit": {"committer": {"date": "2024-02-01T00:00:00Z"}},
                },
            },
        ],
        {},
    )
    service._make_request = AsyncMock(side_effect=[page1, page2])

    branches = await service.get_branches("owner/repo")

    assert [branch.name for branch in branches] == ["main", "dev"]
    assert branches[0].last_push_date == "2024-01-01T00:00:00Z"


@pytest.mark.asyncio
async def test_github_get_branches_handles_empty_response(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    service = GitHubService(token=SecretStr("token"))
    service._make_request = AsyncMock(return_value=([], {}))

    branches = await service.get_branches("owner/repo")

    assert branches == []
    service._make_request.assert_awaited_once()


@pytest.mark.asyncio
async def test_github_get_paginated_branches_sets_next(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    service = GitHubService(token=SecretStr("token"))
    response = (
        [
            {
                "name": "main",
                "commit": {
                    "sha": "a",
                    "commit": {"committer": {"date": "2024-01-01T00:00:00Z"}},
                },
            },
        ],
        {"Link": '<next>; rel="next"'},
    )
    service._make_request = AsyncMock(return_value=response)

    result = await service.get_paginated_branches("owner/repo", page=2, per_page=5)

    assert result.has_next_page is True
    assert result.current_page == 2
    assert result.per_page == 5


@pytest.mark.asyncio
async def test_github_search_branches_processes_nodes(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    service = GitHubService(token=SecretStr("token"))
    graph_response = {
        "data": {
            "repository": {
                "refs": {
                    "nodes": [
                        {
                            "name": "feature",
                            "target": {
                                "__typename": "Commit",
                                "oid": "abc",
                                "committedDate": "2024-01-05T00:00:00Z",
                            },
                            "branchProtectionRule": {},
                        }
                    ]
                }
            }
        }
    }
    monkeypatch.setattr(
        service, "execute_graphql_query", AsyncMock(return_value=graph_response)
    )

    branches = await service.search_branches("owner/repo", "feat", per_page=10)

    assert len(branches) == 1
    assert branches[0].protected is True
    service.execute_graphql_query.assert_awaited_once()


@pytest.mark.asyncio
async def test_github_search_branches_invalid_returns_empty(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    service = GitHubService(token=SecretStr("token"))

    result = await service.search_branches("invalid", "", per_page=10)

    assert result == []


@pytest.mark.asyncio
async def test_github_execute_branch_search_query_handles_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    service = GitHubService(token=SecretStr("token"))
    monkeypatch.setattr(
        service, "execute_graphql_query", AsyncMock(side_effect=RuntimeError("boom"))
    )

    result = await service._execute_branch_search_query("owner", "repo", "feat", 10)

    assert result is None


@pytest.mark.asyncio
async def test_github_search_branches_missing_refs(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    service = GitHubService(token=SecretStr("token"))
    monkeypatch.setattr(
        service,
        "execute_graphql_query",
        AsyncMock(return_value={"data": {"repository": {}}}),
    )

    branches = await service.search_branches("owner/repo", "feat")

    assert branches == []


@pytest.mark.asyncio
async def test_github_search_branches_missing_refs_nodes(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    service = GitHubService(token=SecretStr("token"))
    monkeypatch.setattr(
        service,
        "execute_graphql_query",
        AsyncMock(return_value={"data": {"repository": {"refs": None}}}),
    )

    branches = await service.search_branches("owner/repo", "feat")

    assert branches == []


@pytest.mark.asyncio
async def test_github_search_branches_returns_empty_when_query_fails(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    service = GitHubService(token=SecretStr("token"))
    monkeypatch.setattr(
        service, "_execute_branch_search_query", AsyncMock(return_value=None)
    )

    branches = await service.search_branches("owner/repo", "feature")

    assert branches == []


@pytest.mark.asyncio
async def test_github_search_branches_missing_repo_parts(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    service = GitHubService(token=SecretStr("token"))

    branches = await service.search_branches("invalid", "feat")

    assert branches == []


def _make_pr(
    state: str = "OPEN",
    mergeable: str = "MERGEABLE",
    status_state: str | None = None,
    review_state: str | None = None,
) -> dict:
    pr = {
        "state": state,
        "mergeable": mergeable,
        "repository": {"nameWithOwner": "owner/repo"},
        "number": 1,
        "title": "PR Title",
        "commits": {
            "nodes": [{"commit": {"statusCheckRollup": {"state": status_state}}}]
        },
        "reviews": {"nodes": []},
    }
    if review_state:
        pr["reviews"]["nodes"].append({"state": review_state})
    return pr


def test_github_determine_pr_task_type() -> None:
    service = GitHubService(token=SecretStr("token"))
    assert (
        service._determine_pr_task_type(_make_pr(mergeable="CONFLICTING"))
        == TaskType.MERGE_CONFLICTS
    )
    assert (
        service._determine_pr_task_type(
            _make_pr(status_state="FAILURE", mergeable="MERGEABLE")
        )
        == TaskType.FAILING_CHECKS
    )
    assert (
        service._determine_pr_task_type(
            _make_pr(review_state="CHANGES_REQUESTED", mergeable="MERGEABLE")
        )
        == TaskType.UNRESOLVED_COMMENTS
    )
    assert service._determine_pr_task_type(_make_pr()) == TaskType.OPEN_PR


@pytest.mark.asyncio
async def test_github_process_pull_requests_creates_tasks(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    service = GitHubService(token=SecretStr("token"))
    monkeypatch.setattr(
        service,
        "execute_graphql_query",
        AsyncMock(
            return_value={
                "data": {
                    "user": {
                        "pullRequests": {
                            "nodes": [
                                _make_pr(mergeable="CONFLICTING"),
                                _make_pr(status_state="FAILURE"),
                                _make_pr(review_state="COMMENTED"),
                                _make_pr(),  # Should be skipped
                            ]
                        }
                    }
                }
            }
        ),
    )

    tasks = await service._process_pull_requests({"login": "me"})

    assert [task.task_type for task in tasks] == [
        TaskType.MERGE_CONFLICTS,
        TaskType.FAILING_CHECKS,
        TaskType.UNRESOLVED_COMMENTS,
    ]


@pytest.mark.asyncio
async def test_github_process_issues_creates_tasks(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    service = GitHubService(token=SecretStr("token"))
    monkeypatch.setattr(
        service,
        "execute_graphql_query",
        AsyncMock(
            return_value={
                "data": {
                    "user": {
                        "issues": {
                            "nodes": [
                                {
                                    "repository": {"nameWithOwner": "owner/repo"},
                                    "number": 7,
                                    "title": "Issue title",
                                }
                            ]
                        }
                    }
                }
            }
        ),
    )

    tasks = await service._process_issues({"login": "me"})

    assert len(tasks) == 1
    assert tasks[0].task_type == TaskType.OPEN_ISSUE


@pytest.mark.asyncio
async def test_github_process_pull_requests_logs_on_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    service = GitHubService(token=SecretStr("token"))
    monkeypatch.setattr(
        service, "execute_graphql_query", AsyncMock(side_effect=RuntimeError("fail"))
    )
    logged: list[str] = []
    monkeypatch.setattr(
        "forge.integrations.github.service.features.logger.info",
        lambda *args, **kwargs: logged.append(args[0]),
    )

    tasks = await service._process_pull_requests({"login": "me"})

    assert tasks == []
    assert logged


@pytest.mark.asyncio
async def test_github_process_issues_logs_on_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    service = GitHubService(token=SecretStr("token"))
    monkeypatch.setattr(
        service, "execute_graphql_query", AsyncMock(side_effect=RuntimeError("fail"))
    )
    logged: list[str] = []
    monkeypatch.setattr(
        "forge.integrations.github.service.features.logger.info",
        lambda *args, **kwargs: logged.append(args[0]),
    )

    tasks = await service._process_issues({"login": "me"})

    assert tasks == []
    assert logged


@pytest.mark.asyncio
async def test_github_microagent_helper_methods() -> None:
    service = GitHubService(token=SecretStr("token"))
    assert (
        await service._get_cursorrules_url("owner/repo")
        == "https://api.github.com/repos/owner/repo/contents/.cursorrules"
    )
    assert (
        await service._get_microagents_directory_url("owner/repo", ".Forge")
        == "https://api.github.com/repos/owner/repo/contents/.Forge"
    )
    item = {"type": "file", "name": "agent.md"}
    assert service._is_valid_microagent_file(item) is True
    assert service._get_file_name_from_item(item) == "agent.md"
    assert service._get_file_path_from_item(item, ".Forge") == ".Forge/agent.md"
    assert service._get_microagents_directory_params(".Forge") is None


@pytest.mark.asyncio
async def test_github_get_suggested_tasks_combines(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    service = GitHubService(token=SecretStr("token"))
    monkeypatch.setattr(
        service, "get_user", AsyncMock(return_value=SimpleNamespace(login="me"))
    )
    monkeypatch.setattr(
        service,
        "execute_graphql_query",
        AsyncMock(
            side_effect=[
                {
                    "data": {
                        "user": {
                            "pullRequests": {
                                "nodes": [_make_pr(mergeable="CONFLICTING")]
                            }
                        }
                    }
                },
                {
                    "data": {
                        "user": {
                            "issues": {
                                "nodes": [
                                    {
                                        "repository": {"nameWithOwner": "owner/repo"},
                                        "number": 5,
                                        "title": "Issue",
                                    }
                                ]
                            }
                        }
                    }
                },
            ]
        ),
    )

    tasks = await service.get_suggested_tasks()

    assert len(tasks) == 2
    assert {task.task_type for task in tasks} == {
        TaskType.MERGE_CONFLICTS,
        TaskType.OPEN_ISSUE,
    }


@pytest.mark.asyncio
async def test_github_get_microagent_content_decodes(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    service = GitHubService(token=SecretStr("token"))
    encoded = base64.b64encode(b"# Title").decode("utf-8")
    service._make_request = AsyncMock(return_value=({"content": encoded}, {}))
    monkeypatch.setattr(
        service,
        "_parse_microagent_content",
        lambda content, path: {"content": content, "path": path},
    )

    result = await service.get_microagent_content("owner/repo", "microagents/file.md")

    assert result["content"] == "# Title"
    assert result["path"] == "microagents/file.md"


@pytest.mark.asyncio
async def test_github_fetch_paginated_repos_respects_limit(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    service = GitHubService(token=SecretStr("token"))
    response1 = (
        {"repositories": [{"id": 1}, {"id": 2}]},
        {"Link": '<next>; rel="next"'},
    )
    response2 = ({"repositories": [{"id": 3}]}, {})
    service._make_request = AsyncMock(side_effect=[response1, response2])

    repos = await service._fetch_paginated_repos(
        "url", {}, max_repos=2, extract_key="repositories"
    )

    assert len(repos) == 2
    service._make_request.assert_awaited()


def test_github_parse_repository() -> None:
    service = GitHubService(token=SecretStr("token"))
    repo = service._parse_repository(
        {
            "id": 1,
            "full_name": "owner/repo",
            "stargazers_count": 5,
            "private": False,
            "owner": {"type": "Organization"},
            "default_branch": "main",
        },
        link_header="<next>",
    )

    assert repo.full_name == "owner/repo"
    assert repo.owner_type.name == "ORGANIZATION"
    assert repo.link_header == "<next>"


@pytest.mark.asyncio
async def test_github_get_installations_returns_string_ids() -> None:
    service = GitHubService(token=SecretStr("token"))
    service._make_request = AsyncMock(
        return_value=({"installations": [{"id": 1}, {"id": 2}]}, {})
    )

    ids = await service.get_installations()

    assert ids == ["1", "2"]


@pytest.mark.asyncio
async def test_github_get_paginated_repos_installation(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    service = GitHubService(token=SecretStr("token"))
    service._make_request = AsyncMock(
        return_value=(
            {
                "repositories": [
                    {
                        "id": 1,
                        "full_name": "owner/repo",
                        "private": False,
                        "owner": {"type": "User"},
                    }
                ]
            },
            {"Link": ""},
        )
    )

    repos = await service.get_paginated_repos(
        page=1, per_page=30, sort="pushed", installation_id="42"
    )

    assert repos[0].full_name == "owner/repo"
    service._make_request.assert_awaited_once()


@pytest.mark.asyncio
async def test_github_get_all_repositories_saas(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    service = GitHubService(token=SecretStr("token"))
    monkeypatch.setattr(service, "get_installations", AsyncMock(return_value=["1"]))
    monkeypatch.setattr(
        service,
        "_fetch_paginated_repos",
        AsyncMock(
            return_value=[
                {
                    "id": 1,
                    "full_name": "owner/repo",
                    "private": False,
                    "owner": {"type": "User"},
                    "pushed_at": "2024-01-01T00:00:00Z",
                }
            ]
        ),
    )

    repos = await service.get_all_repositories("pushed", AppMode.SAAS)

    assert repos[0].full_name == "owner/repo"
    service._fetch_paginated_repos.assert_awaited()


@pytest.mark.asyncio
async def test_github_get_all_repositories_user(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    service = GitHubService(token=SecretStr("token"))
    monkeypatch.setattr(
        service,
        "_fetch_paginated_repos",
        AsyncMock(
            return_value=[
                {
                    "id": 2,
                    "full_name": "owner/repo2",
                    "private": True,
                    "owner": {"type": "User"},
                }
            ]
        ),
    )

    repos = await service.get_all_repositories("updated", AppMode.OSS)

    assert repos[0].full_name == "owner/repo2"


@pytest.mark.asyncio
async def test_github_get_paginated_repos_without_installation(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    service = GitHubService(token=SecretStr("token"))
    service._make_request = AsyncMock(
        return_value=(
            [
                {
                    "id": 3,
                    "full_name": "owner/repo3",
                    "private": False,
                    "owner": {"type": "Organization"},
                }
            ],
            {"Link": '<next>; rel="next"'},
        )
    )

    repos = await service.get_paginated_repos(
        page=2, per_page=20, sort="updated", installation_id=None
    )

    service._make_request.assert_awaited_once()
    called_url, called_params = service._make_request.call_args.args
    assert called_url.endswith("/user/repos")
    assert called_params["sort"] == "updated"
    assert repos[0].link_header.endswith('rel="next"')


@pytest.mark.asyncio
async def test_github_fetch_paginated_repos_breaks_on_empty() -> None:
    service = GitHubService(token=SecretStr("token"))
    service._make_request = AsyncMock(return_value=({}, {}))

    repos = await service._fetch_paginated_repos(
        "url", {}, max_repos=5, extract_key="repositories"
    )

    assert repos == []


@pytest.mark.asyncio
async def test_github_fetch_paginated_repos_no_next_link() -> None:
    service = GitHubService(token=SecretStr("token"))
    service._make_request = AsyncMock(return_value=([{"id": 1}], {}))

    repos = await service._fetch_paginated_repos("url", {}, max_repos=5)

    assert repos == [{"id": 1}]
    service._make_request.assert_awaited_once()


@pytest.mark.asyncio
async def test_github_get_all_repositories_sorts_pushed(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    service = GitHubService(token=SecretStr("token"))
    monkeypatch.setattr(service, "get_installations", AsyncMock(return_value=["1"]))
    monkeypatch.setattr(
        service,
        "_fetch_paginated_repos",
        AsyncMock(
            return_value=[
                {
                    "id": 1,
                    "full_name": "owner/old",
                    "private": False,
                    "owner": {"type": "User"},
                    "pushed_at": "2023-01-01T00:00:00Z",
                },
                {
                    "id": 2,
                    "full_name": "owner/new",
                    "private": False,
                    "owner": {"type": "User"},
                    "pushed_at": "2024-01-01T00:00:00Z",
                },
            ]
        ),
    )

    repos = await service.get_all_repositories("pushed", AppMode.SAAS)

    assert [repo.full_name for repo in repos] == ["owner/new", "owner/old"]


@pytest.mark.asyncio
async def test_github_get_all_repositories_stops_at_max(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    service = GitHubService(token=SecretStr("token"))
    large_payload = [
        {
            "id": str(i),
            "full_name": f"owner/repo{i}",
            "private": False,
            "owner": {"type": "User"},
        }
        for i in range(1000)
    ]
    monkeypatch.setattr(
        service, "get_installations", AsyncMock(return_value=["1", "2"])
    )
    monkeypatch.setattr(
        service,
        "_fetch_paginated_repos",
        AsyncMock(side_effect=[large_payload, [{"id": "extra"}]]),
    )

    repos = await service.get_all_repositories("updated", AppMode.SAAS)

    assert len(repos) == 1000
    assert service._fetch_paginated_repos.await_count == 1


@pytest.mark.asyncio
async def test_github_get_user_organizations_handles_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    service = GitHubService(token=SecretStr("token"))
    service._make_request = AsyncMock(side_effect=RuntimeError("boom"))

    orgs = await service.get_user_organizations()

    assert orgs == []


@pytest.mark.asyncio
async def test_github_get_user_organizations_success(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    service = GitHubService(token=SecretStr("token"))
    service._make_request = AsyncMock(return_value=([{"login": "org"}], {}))

    orgs = await service.get_user_organizations()

    assert orgs == ["org"]


def test_github_fuzzy_match_org_name() -> None:
    service = GitHubService(token=SecretStr("token"))
    assert service._fuzzy_match_org_name("My Org", "my-org") is True
    assert service._fuzzy_match_org_name("xyz", "abc") is False


def test_github_build_public_search_params() -> None:
    service = GitHubService(token=SecretStr("token"))
    params, is_public = service._build_public_search_params(
        "https://github.com/org/repo", {}
    )
    assert is_public is True
    assert "org/repo" in params["q"]


def test_github_build_public_search_params_invalid() -> None:
    service = GitHubService(token=SecretStr("token"))
    params, is_public = service._build_public_search_params("invalid", {})
    assert is_public is False
    assert params == {}


@pytest.mark.asyncio
async def test_github_search_user_repositories(monkeypatch: pytest.MonkeyPatch) -> None:
    service = GitHubService(token=SecretStr("token"))
    service._make_request = AsyncMock(
        return_value=({"items": [{"full_name": "owner/repo"}]}, {})
    )
    user = SimpleNamespace(login="octocat")

    results = await service._search_user_repositories("url", "repo", {}, user)

    assert results == [{"full_name": "owner/repo"}]
    service._make_request.assert_awaited_once()


@pytest.mark.asyncio
async def test_github_search_user_repositories_handles_exception(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    service = GitHubService(token=SecretStr("token"))
    service._make_request = AsyncMock(side_effect=RuntimeError("fail"))

    results = await service._search_user_repositories(
        "url", "repo", {}, SimpleNamespace(login="me")
    )

    assert results == []


@pytest.mark.asyncio
async def test_github_search_organization_repositories_handles_errors(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    service = GitHubService(token=SecretStr("token"))
    service._make_request = AsyncMock(
        side_effect=[({"items": [{"full_name": "org/repo"}]}, {}), RuntimeError("boom")]
    )

    results = await service._search_organization_repositories(
        "url", "repo", {}, ["org1", "org2"]
    )

    assert {"full_name": "org/repo"} in results


@pytest.mark.asyncio
async def test_github_search_fuzzy_matched_orgs(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    service = GitHubService(token=SecretStr("token"))
    service._make_request = AsyncMock(
        return_value=({"items": [{"full_name": "org/repo"}]}, {})
    )

    repos = await service._search_fuzzy_matched_orgs("url", "org", {}, ["org"])

    assert repos == [{"full_name": "org/repo"}]


@pytest.mark.asyncio
async def test_github_search_fuzzy_matched_orgs_handles_exception(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    service = GitHubService(token=SecretStr("token"))
    service._make_request = AsyncMock(side_effect=RuntimeError("fail"))
    monkeypatch.setattr(service, "_fuzzy_match_org_name", lambda query, org: True)
    warnings: list[str] = []
    monkeypatch.setattr(
        "forge.integrations.github.service.repos.logger.warning",
        lambda *args, **kwargs: warnings.append(args[0]),
    )

    repos = await service._search_fuzzy_matched_orgs("url", "repo", {}, ["org"])

    assert repos == []
    assert warnings


@pytest.mark.asyncio
async def test_github_search_repositories_public_invalid_returns_empty(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    service = GitHubService(token=SecretStr("token"))

    repos = await service.search_repositories(
        "invalid", per_page=5, sort="stars", order="desc", public=True
    )

    assert repos == []


@pytest.mark.asyncio
async def test_github_search_repositories_public_success(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    service = GitHubService(token=SecretStr("token"))
    service._make_request = AsyncMock(
        return_value=({"items": [{"id": 1, "full_name": "owner/repo"}]}, {})
    )

    repos = await service.search_repositories(
        "https://github.com/org/repo",
        per_page=5,
        sort="stars",
        order="desc",
        public=True,
    )

    assert repos[0].full_name == "owner/repo"


@pytest.mark.asyncio
async def test_github_search_repositories_with_slash(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    service = GitHubService(token=SecretStr("token"))
    service._make_request = AsyncMock(
        return_value=({"items": [{"id": 1, "full_name": "owner/repo"}]}, {})
    )

    repos = await service.search_repositories(
        "owner/repo", per_page=5, sort="updated", order="desc", public=False
    )

    service._make_request.assert_awaited_once()
    assert repos[0].full_name == "owner/repo"


@pytest.mark.asyncio
async def test_github_search_repositories_combines_sources(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    service = GitHubService(token=SecretStr("token"))
    monkeypatch.setattr(
        service, "get_user", AsyncMock(return_value=SimpleNamespace(login="me"))
    )
    monkeypatch.setattr(
        service, "get_user_organizations", AsyncMock(return_value=["org"])
    )
    monkeypatch.setattr(
        service,
        "_search_user_repositories",
        AsyncMock(return_value=[{"id": 1, "full_name": "me/repo"}]),
    )
    monkeypatch.setattr(
        service,
        "_search_organization_repositories",
        AsyncMock(return_value=[{"id": 2, "full_name": "org/repo"}]),
    )
    monkeypatch.setattr(
        service,
        "_search_fuzzy_matched_orgs",
        AsyncMock(return_value=[{"id": 3, "full_name": "fuzzy/repo"}]),
    )

    repos = await service.search_repositories(
        "repo", per_page=5, sort="stars", order="desc", public=False
    )

    assert [repo.full_name for repo in repos] == ["me/repo", "org/repo", "fuzzy/repo"]


@pytest.mark.asyncio
async def test_github_get_repository_details_from_repo_name(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    service = GitHubService(token=SecretStr("token"))
    service._make_request = AsyncMock(
        return_value=(
            {
                "id": 1,
                "full_name": "owner/repo",
                "private": False,
                "owner": {"type": "User"},
            },
            {},
        )
    )

    repo = await service.get_repository_details_from_repo_name("owner/repo")

    assert repo.full_name == "owner/repo"
