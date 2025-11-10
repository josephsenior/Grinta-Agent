from __future__ import annotations

from datetime import datetime
from types import SimpleNamespace
from unittest.mock import AsyncMock

import httpx
import pytest
from pydantic import SecretStr

from forge.integrations.gitlab.gitlab_service import GitLabService
from forge.integrations.service_types import (
    Branch,
    Comment,
    PaginatedBranchesResponse,
    ProviderType,
    Repository,
    RequestMethod,
    ResourceNotFoundError,
    SuggestedTask,
    TaskType,
    UnknownException,
)
from forge.server.types import AppMode


class AsyncClientStub:
    async def __aenter__(self):
        return SimpleNamespace()

    async def __aexit__(self, exc_type, exc, tb):  # pragma: no cover - helper with no logic
        return False


class GraphQLClientStub:
    def __init__(self, responses: list["DummyHTTPResponse"]) -> None:
        self._responses = responses

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):  # pragma: no cover - helper with no logic
        return False

    async def post(self, url: str, headers: dict, json: dict):
        if not self._responses:
            raise AssertionError("Stub responses exhausted")
        return self._responses.pop(0)


class DummyHTTPResponse:
    def __init__(
        self,
        status_code: int = 200,
        headers: dict | None = None,
        json_data: dict | None = None,
        text_data: str = "",
    ) -> None:
        self.status_code = status_code
        self.headers = headers or {}
        self._json_data = json_data
        self._text_data = text_data

    def raise_for_status(self) -> None:
        if self.status_code >= 400:
            request = httpx.Request("GET", "https://example.com")
            response = httpx.Response(self.status_code, request=request)
            raise httpx.HTTPStatusError("error", request=request, response=response)

    def json(self) -> dict | None:
        return self._json_data

    @property
    def text(self) -> str:
        return self._text_data


def _make_gitlab_service(token: str = "token") -> GitLabService:
    return GitLabService(token=SecretStr(token))


@pytest.mark.asyncio
async def test_gitlab_service_domain_overrides() -> None:
    default_service = _make_gitlab_service()
    assert default_service.BASE_URL == "https://gitlab.com/api/v4"
    hosted_service = GitLabService(token=SecretStr("token"), base_domain="gitlab.internal")
    assert hosted_service.BASE_URL == "https://gitlab.internal/api/v4"
    https_service = GitLabService(token=SecretStr("token"), base_domain="https://self.hosted")
    assert https_service.BASE_URL == "https://self.hosted/api/v4"
    assert https_service.provider == ProviderType.GITLAB.value


@pytest.mark.asyncio
async def test_gitlab_make_request_handles_refresh_and_headers(monkeypatch: pytest.MonkeyPatch) -> None:
    service = _make_gitlab_service()
    service.refresh = True
    responses = [
        DummyHTTPResponse(status_code=401),
        DummyHTTPResponse(
            status_code=200,
            headers={"Link": "next", "X-Total": "3", "Content-Type": "application/json"},
            json_data={"value": 1},
        ),
    ]

    async def fake_execute_request(*args, **kwargs):
        return responses.pop(0)

    monkeypatch.setattr("forge.integrations.gitlab.service.base.httpx.AsyncClient", lambda: AsyncClientStub())
    service.execute_request = AsyncMock(side_effect=fake_execute_request)
    service.get_latest_token = AsyncMock(return_value=SecretStr("new"))

    data, headers = await service._make_request("https://example.com", {"page": "1"})

    assert data == {"value": 1}
    assert headers["Link"] == "next"
    assert headers["X-Total"] == "3"
    assert service.execute_request.await_count == 2
    service.get_latest_token.assert_awaited_once()


@pytest.mark.asyncio
async def test_gitlab_make_request_returns_text(monkeypatch: pytest.MonkeyPatch) -> None:
    service = _make_gitlab_service()
    response = DummyHTTPResponse(status_code=200, headers={"Content-Type": "text/plain"}, text_data="ok")
    service.execute_request = AsyncMock(return_value=response)
    monkeypatch.setattr("forge.integrations.gitlab.service.base.httpx.AsyncClient", lambda: AsyncClientStub())
    data, headers = await service._make_request("https://example.com")
    assert data == "ok"
    assert headers == {}


@pytest.mark.asyncio
async def test_gitlab_make_request_wraps_http_errors(monkeypatch: pytest.MonkeyPatch) -> None:
    service = _make_gitlab_service()
    error_response = DummyHTTPResponse(status_code=404)
    service.execute_request = AsyncMock(return_value=error_response)
    monkeypatch.setattr("forge.integrations.gitlab.service.base.httpx.AsyncClient", lambda: AsyncClientStub())
    with pytest.raises(ResourceNotFoundError):
        await service._make_request("https://example.com")


@pytest.mark.asyncio
async def test_gitlab_make_request_wraps_http_error(monkeypatch: pytest.MonkeyPatch) -> None:
    service = _make_gitlab_service()
    service.execute_request = AsyncMock(side_effect=httpx.HTTPError("boom"))
    monkeypatch.setattr("forge.integrations.gitlab.service.base.httpx.AsyncClient", lambda: AsyncClientStub())
    with pytest.raises(UnknownException):
        await service._make_request("https://example.com")


@pytest.mark.asyncio
async def test_gitlab_get_latest_token_returns_existing() -> None:
    service = _make_gitlab_service()
    token = await service.get_latest_token()
    assert token.get_secret_value() == "token"


@pytest.mark.asyncio
async def test_gitlab_get_headers_fetches_latest_token(monkeypatch: pytest.MonkeyPatch) -> None:
    service = _make_gitlab_service()
    service.token = None
    monkeypatch.setattr(service, "get_latest_token", AsyncMock(return_value=SecretStr("new")))
    headers = await service._get_headers()
    assert headers["Authorization"] == "Bearer new"
    latest = await service.get_latest_token()
    assert latest.get_secret_value() == "new"


@pytest.mark.asyncio
async def test_gitlab_execute_graphql_query_handles_refresh(monkeypatch: pytest.MonkeyPatch) -> None:
    service = _make_gitlab_service()
    service.refresh = True
    responses = [
        DummyHTTPResponse(status_code=401, headers={"Content-Type": "application/json"}, json_data={"data": None}),
        DummyHTTPResponse(
            status_code=200,
            headers={"Content-Type": "application/json"},
            json_data={"data": {"currentUser": {}}},
        ),
    ]
    monkeypatch.setattr(
        "forge.integrations.gitlab.service.base.httpx.AsyncClient",
        lambda: GraphQLClientStub(responses),
    )
    service.get_latest_token = AsyncMock(return_value=SecretStr("refresh"))
    result = await service.execute_graphql_query("query { currentUser { id } }", {"var": 1})
    assert result == {"currentUser": {}}
    service.get_latest_token.assert_awaited_once()


@pytest.mark.asyncio
async def test_gitlab_execute_graphql_query_raises_on_errors(monkeypatch: pytest.MonkeyPatch) -> None:
    service = _make_gitlab_service()
    responses = [
        DummyHTTPResponse(
            status_code=200,
            headers={"Content-Type": "application/json"},
            json_data={"errors": [{"message": "failed"}]},
        ),
    ]
    monkeypatch.setattr(
        "forge.integrations.gitlab.service.base.httpx.AsyncClient",
        lambda: GraphQLClientStub(responses),
    )
    with pytest.raises(UnknownException):
        await service.execute_graphql_query("query { test }")


@pytest.mark.asyncio
async def test_gitlab_execute_graphql_query_wraps_http_error(monkeypatch: pytest.MonkeyPatch) -> None:
    service = _make_gitlab_service()
    class FailingClient(GraphQLClientStub):
        async def post(self, url: str, headers: dict, json: dict):
            raise httpx.HTTPError("boom")

    monkeypatch.setattr(
        "forge.integrations.gitlab.service.base.httpx.AsyncClient",
        lambda: FailingClient([]),
    )
    with pytest.raises(UnknownException):
        await service.execute_graphql_query("query { test }")


@pytest.mark.asyncio
async def test_gitlab_execute_graphql_query_http_status_error(monkeypatch: pytest.MonkeyPatch) -> None:
    service = _make_gitlab_service()
    responses = [DummyHTTPResponse(status_code=500)]
    monkeypatch.setattr(
        "forge.integrations.gitlab.service.base.httpx.AsyncClient",
        lambda: GraphQLClientStub(responses),
    )
    with pytest.raises(UnknownException):
        await service.execute_graphql_query("query { foo }")


@pytest.mark.asyncio
async def test_gitlab_get_user_parses_response(monkeypatch: pytest.MonkeyPatch) -> None:
    service = _make_gitlab_service()
    user_payload = (
        {
            "id": 5,
            "username": "alice",
            "avatar_url": "https://avatar",
            "name": "Alice",
            "email": "alice@example.com",
            "organization": "Org",
        },
        {},
    )
    monkeypatch.setattr(service, "_make_request", AsyncMock(return_value=user_payload))
    user = await service.get_user()
    assert user.id == "5"
    assert user.login == "alice"
    assert user.company == "Org"


def test_gitlab_extract_project_id_handles_custom_domains() -> None:
    service = _make_gitlab_service()
    assert service._extract_project_id("group/repo") == "group%2Frepo"
    assert service._extract_project_id("gitlab.example.com/group/repo") == "group%2Frepo"
    assert service._extract_project_id("plain-repo") == "plain-repo"


@pytest.mark.asyncio
async def test_gitlab_branches_pagination(monkeypatch: pytest.MonkeyPatch) -> None:
    service = _make_gitlab_service()
    first = (
        [
            {"name": "main", "commit": {"id": "1", "committed_date": "2024"}, "protected": True},
        ],
        {"Link": ""},
    )
    second = ([], {})
    monkeypatch.setattr(service, "_make_request", AsyncMock(side_effect=[first, second]))
    branches = await service.get_branches("group/repo")
    assert len(branches) == 1
    assert branches[0].protected is True


@pytest.mark.asyncio
async def test_gitlab_get_paginated_branches_includes_total(monkeypatch: pytest.MonkeyPatch) -> None:
    service = _make_gitlab_service()
    payload = (
        [
            {"name": "main", "commit": {"id": "1"}, "protected": False},
        ],
        {"Link": "", "X-Total": "7"},
    )
    monkeypatch.setattr(service, "_make_request", AsyncMock(return_value=payload))
    result = await service.get_paginated_branches("group/repo", page=2, per_page=5)
    assert isinstance(result, PaginatedBranchesResponse)
    assert result.branches[0].name == "main"
    assert result.total_count == 7


@pytest.mark.asyncio
async def test_gitlab_search_branches_passes_params(monkeypatch: pytest.MonkeyPatch) -> None:
    service = _make_gitlab_service()
    mock_request = AsyncMock(return_value=([
        {"name": "feature", "commit": {"id": "2"}}
    ], {}))
    monkeypatch.setattr(service, "_make_request", mock_request)
    branches = await service.search_branches("group/repo", "feat", per_page=20)
    assert branches[0].name == "feature"
    args = mock_request.call_args[0]
    assert args[0].endswith("repository/branches")
    assert args[1]["search"] == "feat"
    assert args[1]["per_page"] == "20"


@pytest.mark.asyncio
async def test_gitlab_feature_microagent_helpers() -> None:
    service = _make_gitlab_service()
    assert (await service._get_cursorrules_url("group/repo")).endswith("repository/files/.cursorrules/raw")
    assert (await service._get_microagents_directory_url("group/repo", "path")).endswith("repository/tree")
    assert service._get_microagents_directory_params("dir") == {"path": "dir", "recursive": "true"}
    item = {"type": "blob", "name": "example.md", "path": "dir/example.md"}
    assert service._is_valid_microagent_file(item) is True
    assert service._get_file_name_from_item(item) == "example.md"
    assert service._get_file_path_from_item(item, "dir") == "dir/example.md"


def test_gitlab_feature_determine_task_type() -> None:
    service = _make_gitlab_service()
    assert service._determine_merge_request_task_type({"conflicts": True}) == TaskType.MERGE_CONFLICTS
    failing = {"pipelines": {"nodes": [{"status": "FAILED"}]}}
    assert service._determine_merge_request_task_type(failing) == TaskType.FAILING_CHECKS
    unresolved = {
        "discussions": {"nodes": [{"notes": {"nodes": [{"resolvable": True, "resolved": False}]}}]},
    }
    assert service._determine_merge_request_task_type(unresolved) == TaskType.UNRESOLVED_COMMENTS
    assert service._determine_merge_request_task_type({}) == TaskType.OPEN_PR


def test_gitlab_feature_has_unresolved_comments() -> None:
    service = _make_gitlab_service()
    discussions = {
        "discussions": {"nodes": [{"notes": {"nodes": [{"resolvable": True, "resolved": False}]}}]},
    }
    assert service._has_unresolved_comments(discussions) is True
    assert service._has_unresolved_comments({"discussions": {"nodes": []}}) is False


@pytest.mark.asyncio
async def test_gitlab_feature_process_helpers(monkeypatch: pytest.MonkeyPatch) -> None:
    service = _make_gitlab_service()
    mrs = [{"conflicts": True, "project": {"fullPath": "group/repo"}, "iid": 1, "title": "MR"}]
    tasks = await service._process_merge_requests(mrs)
    assert tasks[0].task_type == TaskType.MERGE_CONFLICTS
    issues_payload = ([{"references": {"full": "group/repo#1"}, "iid": 2, "title": "Issue"}], {})
    monkeypatch.setattr(service, "_make_request", AsyncMock(return_value=issues_payload))
    issue_tasks = await service._process_assigned_issues("alice")
    assert issue_tasks[0].task_type == TaskType.OPEN_ISSUE


@pytest.mark.asyncio
async def test_gitlab_feature_get_suggested_tasks_happy_path(monkeypatch: pytest.MonkeyPatch) -> None:
    service = _make_gitlab_service()
    service.get_user = AsyncMock(return_value=SimpleNamespace(login="alice"))
    service.execute_graphql_query = AsyncMock(return_value={"currentUser": {"authoredMergeRequests": {"nodes": []}}})
    suggested = SuggestedTask(
        git_provider=ProviderType.GITLAB,
        task_type=TaskType.MERGE_CONFLICTS,
        repo="group/repo",
        issue_number=1,
        title="Fix",
    )
    service._process_merge_requests = AsyncMock(return_value=[suggested])
    service._process_assigned_issues = AsyncMock(return_value=[suggested])
    tasks = await service.get_suggested_tasks()
    assert len(tasks) == 2


@pytest.mark.asyncio
async def test_gitlab_feature_get_suggested_tasks_handles_errors(monkeypatch: pytest.MonkeyPatch) -> None:
    service = _make_gitlab_service()
    service.get_user = AsyncMock(side_effect=RuntimeError("boom"))
    tasks = await service.get_suggested_tasks()
    assert tasks == []


@pytest.mark.asyncio
async def test_gitlab_feature_get_microagent_content(monkeypatch: pytest.MonkeyPatch) -> None:
    service = _make_gitlab_service()
    response = ({"content": "text"}, {})
    monkeypatch.setattr(service, "_make_request", AsyncMock(return_value=response))
    monkeypatch.setattr(service, "_parse_microagent_content", lambda payload, path: "parsed")
    result = await service.get_microagent_content("group/repo", "file.md")
    assert result == "parsed"


@pytest.mark.asyncio
async def test_gitlab_pr_create_and_status(monkeypatch: pytest.MonkeyPatch) -> None:
    service = _make_gitlab_service()
    monkeypatch.setattr(service, "_make_request", AsyncMock(return_value=({"web_url": "https://gitlab/mr/1"}, {})))
    url = await service.create_mr("group/repo", "feature", "main", "Title")
    assert url.endswith("/1")
    service.get_pr_details = AsyncMock(return_value={"state": "opened"})
    assert await service.is_pr_open("group/repo", 1) is True
    service.get_pr_details = AsyncMock(return_value={"state": "closed"})
    assert await service.is_pr_open("group/repo", 1) is False
    service.get_pr_details = AsyncMock(return_value={"merged_at": None, "closed_at": None})
    assert await service.is_pr_open("group/repo", 1) is True
    service.get_pr_details = AsyncMock(return_value={"unexpected": True})
    assert await service.is_pr_open("group/repo", 1) is True
    service.get_pr_details = AsyncMock(side_effect=RuntimeError("boom"))
    assert await service.is_pr_open("group/repo", 1) is True


@pytest.mark.asyncio
async def test_gitlab_pr_create_includes_labels(monkeypatch: pytest.MonkeyPatch) -> None:
    service = _make_gitlab_service()
    mock_request = AsyncMock(return_value=({"web_url": "https://gitlab/mr/2"}, {}))
    monkeypatch.setattr(service, "_make_request", mock_request)
    await service.create_mr("group/repo", "feature", "main", "Title", labels=["bug", "fix"])
    params = mock_request.call_args.kwargs["params"]
    assert params["labels"] == "bug,fix"


@pytest.mark.asyncio
async def test_gitlab_get_pr_details_fetches_data(monkeypatch: pytest.MonkeyPatch) -> None:
    service = _make_gitlab_service()
    monkeypatch.setattr(service, "_make_request", AsyncMock(return_value=({"state": "opened"}, {})))
    result = await service.get_pr_details("group/repo", 1)
    assert result["state"] == "opened"


@pytest.mark.asyncio
async def test_gitlab_repos_helpers(monkeypatch: pytest.MonkeyPatch) -> None:
    service = _make_gitlab_service()
    repo_payload = (
        [
            {
                "id": 1,
                "path_with_namespace": "group/repo",
                "star_count": 5,
                "visibility": "public",
                "namespace": {"kind": "group"},
                "default_branch": "main",
            }
        ],
        {"Link": "next"},
    )
    monkeypatch.setattr(service, "_make_request", AsyncMock(return_value=repo_payload))
    repos = await service.get_paginated_repos(1, 10, "pushed", None, query="repo")
    assert repos[0].full_name == "group/repo"
    assert repos[0].link_header == "next"

    all_repos_payload = [repo_payload, ([], {})]
    monkeypatch.setattr(service, "_make_request", AsyncMock(side_effect=all_repos_payload))
    all_repos = await service.get_all_repositories("pushed", AppMode.SAAS)
    assert all_repos[0].owner_type.name == "ORGANIZATION"

    monkeypatch.setattr(service, "_make_request", AsyncMock(return_value=({"id": 1, "path_with_namespace": "group/repo"}, {})))
    repo = await service.get_repository_details_from_repo_name("group/repo")
    assert repo.full_name == "group/repo"


@pytest.mark.asyncio
async def test_gitlab_get_all_repositories_breaks_on_empty(monkeypatch: pytest.MonkeyPatch) -> None:
    service = _make_gitlab_service()
    monkeypatch.setattr(service, "_make_request", AsyncMock(return_value=([], {})))
    result = await service.get_all_repositories("pushed", AppMode.SAAS)
    assert result == []


@pytest.mark.asyncio
async def test_gitlab_search_repositories_public_and_private(monkeypatch: pytest.MonkeyPatch) -> None:
    service = _make_gitlab_service()
    repo = Repository(id="1", full_name="group/repo", git_provider=ProviderType.GITLAB, is_public=True)
    monkeypatch.setattr(service, "get_repository_details_from_repo_name", AsyncMock(return_value=repo))
    result = await service.search_repositories("https://gitlab.com/group/repo", public=True)
    assert result == [repo]
    monkeypatch.setattr(service, "get_repository_details_from_repo_name", AsyncMock(side_effect=Exception("boom")))
    with pytest.raises(Exception):
        await service.search_repositories("https://gitlab.com/group/repo", public=True)
    monkeypatch.setattr(service, "get_repository_details_from_repo_name", AsyncMock(return_value=repo))
    monkeypatch.setattr(service, "get_paginated_repos", AsyncMock(return_value=[repo]))
    private = await service.search_repositories("repo", public=False)
    assert private == [repo]


@pytest.mark.asyncio
async def test_gitlab_search_repositories_public_invalid(monkeypatch: pytest.MonkeyPatch) -> None:
    service = _make_gitlab_service()
    result = await service.search_repositories("https://gitlab.com/invalid", public=True)
    assert result == []


def test_gitlab_parse_gitlab_url_variants() -> None:
    service = _make_gitlab_service()
    assert service._parse_gitlab_url("https://gitlab.com/group/repo") == "group/repo"
    assert service._parse_gitlab_url("https://gitlab.com/") is None
    assert service._parse_gitlab_url("https://gitlab.com/group/") is None
    assert service._parse_gitlab_url("invalid") is None
    assert service._parse_gitlab_url(None) is None


@pytest.mark.asyncio
async def test_gitlab_resolver_review_comments(monkeypatch: pytest.MonkeyPatch) -> None:
    service = _make_gitlab_service()
    gitlab_client = SimpleNamespace(get_review_thread_comments=AsyncMock(return_value={"notes": [1, 2]}))
    monkeypatch.setattr(
        service,
        "_process_raw_comments",
        lambda comments, max_comments=10: [
            Comment(
                id="1",
                body="",
                author="",
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow(),
            )
        ],
    )
    comments = await service.get_review_thread_comments(gitlab_client, 1)
    assert len(comments) == 1


@pytest.mark.asyncio
async def test_gitlab_resolver_issue_and_mr_helpers(monkeypatch: pytest.MonkeyPatch) -> None:
    service = _make_gitlab_service()
    issue_payload = ({"title": "Issue", "description": "Body"}, {})
    mr_payload = ({"title": "MR", "description": "Body"}, {})
    monkeypatch.setattr(service, "_make_request", AsyncMock(side_effect=[issue_payload, mr_payload]))
    title, body = await service.get_issue_or_mr_title_and_body("group%2Frepo", 1)
    assert title == "Issue"
    mr_title, _ = await service.get_issue_or_mr_title_and_body("group%2Frepo", 1, is_mr=True)
    assert mr_title == "MR"


@pytest.mark.asyncio
async def test_gitlab_resolver_comments_with_pagination(monkeypatch: pytest.MonkeyPatch) -> None:
    service = _make_gitlab_service()
    issue_comments = ([{"id": 1, "body": "test", "author": {"username": "alice"}, "created_at": "2024-01-01T00:00:00Z"}], {"Link": ""})
    mr_discussions = ([{"notes": [{"id": 2, "body": "mr", "author": {"username": "bob"}, "created_at": "2024-01-02T00:00:00Z"}]}], {"Link": ""})
    monkeypatch.setattr(service, "_make_request", AsyncMock(side_effect=[issue_comments, mr_discussions]))
    issue_result = await service.get_issue_or_mr_comments("project", 1, max_comments=5, is_mr=False)
    assert isinstance(issue_result[0], Comment)
    mr_result = await service.get_issue_or_mr_comments("project", 1, max_comments=5, is_mr=True)
    assert isinstance(mr_result[0], Comment)


@pytest.mark.asyncio
async def test_gitlab_resolver_comments_handles_next_pages(monkeypatch: pytest.MonkeyPatch) -> None:
    service = _make_gitlab_service()
    first = (
        [{"notes": [{"id": 3, "body": "first", "author": {"username": "dev"}, "created_at": "2024-01-03T00:00:00Z"}]}],
        {"Link": '<next>; rel="next"'},
    )
    second = ([], {})
    monkeypatch.setattr(service, "_make_request", AsyncMock(side_effect=[first, second]))
    result = await service.get_issue_or_mr_comments("project", 2, max_comments=5, is_mr=True)
    assert len(result) == 1


def test_gitlab_resolver_process_raw_comments_truncates() -> None:
    service = _make_gitlab_service()
    comments = [
        {"id": 1, "body": "a", "author": {"username": "one"}, "created_at": "2024-01-01T00:00:00Z"},
        {"id": 2, "body": "b", "author": {"username": "two"}, "created_at": "2024-01-02T00:00:00Z"},
    ]
    processed = service._process_raw_comments(comments, max_comments=1)
    assert len(processed) == 1
    assert processed[0].author == "two"
