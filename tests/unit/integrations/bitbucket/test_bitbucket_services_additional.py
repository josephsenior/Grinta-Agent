from __future__ import annotations

import base64
from types import SimpleNamespace
from unittest.mock import AsyncMock

import httpx
import pytest
from pydantic import SecretStr

from forge.integrations.bitbucket.bitbucket_service import BitBucketService
from forge.integrations.service_types import (
    Branch,
    PaginatedBranchesResponse,
    ProviderType,
    Repository,
    RequestMethod,
    ResourceNotFoundError,
    UnknownException,
)
from forge.server.types import AppMode


class StubBitbucketService(BitBucketService):
    def __init__(
        self, responses: list[tuple[dict, dict]], token_value: str = "user:pass"
    ) -> None:
        super().__init__(token=SecretStr(token_value))
        self._responses = list(responses)
        self.calls: list[tuple[str, dict | None, RequestMethod]] = []

    async def _make_request(
        self,
        url: str,
        params: dict | None = None,
        method: RequestMethod = RequestMethod.GET,
    ) -> tuple[dict, dict]:
        self.calls.append((url, params, method))
        if not self._responses:
            raise AssertionError("Stub responses exhausted")
        response = self._responses.pop(0)
        if isinstance(response, Exception):
            raise response
        return response


class AsyncClientStub:
    async def __aenter__(self):
        return SimpleNamespace()

    async def __aexit__(self, exc_type, exc, tb):  # pragma: no cover - no logic to test
        return False


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


def _make_repo(
    repo_id: str = "repo-1",
    workspace: str = "workspace",
    slug: str = "repo",
    is_private: bool = False,
    updated_on: str = "2024-01-01T00:00:00Z",
    main_branch: str = "main",
) -> dict:
    return {
        "uuid": repo_id,
        "workspace": {"slug": workspace},
        "slug": slug,
        "is_private": is_private,
        "updated_on": updated_on,
        "mainbranch": {"name": main_branch},
    }


@pytest.mark.asyncio
async def test_bitbucket_extract_owner_and_repo_valid_invalid() -> None:
    service = BitBucketService(token=SecretStr("token"))
    assert service._extract_owner_and_repo("team/project") == ("team", "project")
    with pytest.raises(ValueError):
        service._extract_owner_and_repo("invalid")


@pytest.mark.asyncio
async def test_bitbucket_get_headers_supports_basic_and_bearer() -> None:
    basic_service = BitBucketService(token=SecretStr("user:pass"))
    headers = await basic_service._get_headers()
    assert headers["Authorization"].startswith("Basic ")
    encoded = headers["Authorization"].split(" ", 1)[1]
    assert encoded == base64.b64encode(b"user:pass").decode()

    bearer_service = BitBucketService(token=SecretStr("token"))
    bearer_headers = await bearer_service._get_headers()
    assert bearer_headers["Authorization"] == "Bearer token"


@pytest.mark.asyncio
async def test_bitbucket_fetch_paginated_data_accumulates_results() -> None:
    responses = [
        ({"values": [{"slug": "repo1"}], "next": "next-url"}, {}),
        ({"values": [{"slug": "repo2"}]}, {}),
    ]
    service = StubBitbucketService(responses)
    items = await service._fetch_paginated_data(
        "https://example.com", {"pagelen": 1}, max_items=5
    )
    assert items == [{"slug": "repo1"}, {"slug": "repo2"}]


@pytest.mark.asyncio
async def test_bitbucket_get_user_parses_response() -> None:
    responses = [
        (
            {
                "account_id": "abc",
                "username": "test-user",
                "links": {"avatar": {"href": "https://avatar"}},
                "display_name": "Test User",
            },
            {},
        ),
    ]
    service = StubBitbucketService(responses)
    user = await service.get_user()
    assert user.id == "abc"
    assert user.login == "test-user"
    assert user.avatar_url == "https://avatar"


@pytest.mark.asyncio
async def test_bitbucket_make_request_handles_refresh_and_headers(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    service = BitBucketService(token=SecretStr("initial"))
    service.refresh = True
    responses = [
        DummyHTTPResponse(status_code=401),
        DummyHTTPResponse(
            status_code=200,
            headers={
                "Link": "next",
                "X-Total": "5",
                "Content-Type": "application/json",
            },
            json_data={"data": 1},
        ),
    ]

    async def fake_execute_request(*args, **kwargs):
        return responses.pop(0)

    monkeypatch.setattr(
        "forge.integrations.bitbucket.service.base.httpx.AsyncClient",
        lambda: AsyncClientStub(),
    )
    service.execute_request = AsyncMock(side_effect=fake_execute_request)
    service.get_latest_token = AsyncMock(return_value=SecretStr("refreshed"))

    data, headers = await service._make_request("https://example.com", {"foo": "bar"})

    assert data == {"data": 1}
    assert headers["Link"] == "next"
    assert headers["X-Total"] == "5"
    assert service.execute_request.await_count == 2
    service.get_latest_token.assert_awaited_once()


@pytest.mark.asyncio
async def test_bitbucket_make_request_returns_headers_dict(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    service = BitBucketService(token=SecretStr("token"))
    response = DummyHTTPResponse(
        status_code=200,
        headers={"Content-Type": "application/json"},
        json_data={"ok": True},
    )
    service.execute_request = AsyncMock(return_value=response)
    monkeypatch.setattr(
        "forge.integrations.bitbucket.service.base.httpx.AsyncClient",
        lambda: AsyncClientStub(),
    )
    data, headers = await service._make_request("https://example.com")
    assert data == {"ok": True}
    assert headers == {"Content-Type": "application/json"}


@pytest.mark.asyncio
async def test_bitbucket_make_request_wraps_http_status_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    service = BitBucketService(token=SecretStr("token"))
    error_response = DummyHTTPResponse(status_code=404)
    service.execute_request = AsyncMock(return_value=error_response)
    monkeypatch.setattr(
        "forge.integrations.bitbucket.service.base.httpx.AsyncClient",
        lambda: AsyncClientStub(),
    )
    with pytest.raises(ResourceNotFoundError):
        await service._make_request("https://example.com")


@pytest.mark.asyncio
async def test_bitbucket_make_request_wraps_http_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    service = BitBucketService(token=SecretStr("token"))
    service.execute_request = AsyncMock(side_effect=httpx.HTTPError("boom"))
    monkeypatch.setattr(
        "forge.integrations.bitbucket.service.base.httpx.AsyncClient",
        lambda: AsyncClientStub(),
    )
    with pytest.raises(UnknownException):
        await service._make_request("https://example.com")


def test_bitbucket_parse_repository_builds_full_name() -> None:
    service = BitBucketService(token=SecretStr("token"))
    repo = service._parse_repository(_make_repo())
    assert repo.full_name == "workspace/repo"
    assert repo.is_public is True
    assert repo.git_provider == ProviderType.BITBUCKET


@pytest.mark.asyncio
async def test_bitbucket_get_repository_details_from_repo_name() -> None:
    responses = [
        (_make_repo(), {}),
    ]
    service = StubBitbucketService(responses)
    repo = await service.get_repository_details_from_repo_name("workspace/repo")
    assert repo.full_name == "workspace/repo"


@pytest.mark.asyncio
async def test_bitbucket_get_cursorrules_url_requires_main_branch(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    service = BitBucketService(token=SecretStr("token"))
    repo = Repository(
        id="1",
        full_name="workspace/repo",
        git_provider=ProviderType.BITBUCKET,
        is_public=True,
        main_branch="main",
    )
    monkeypatch.setattr(
        service, "get_repository_details_from_repo_name", AsyncMock(return_value=repo)
    )
    url = await service._get_cursorrules_url("workspace/repo")
    assert url.endswith("/src/main/.cursorrules")

    repo_without_branch = repo.model_copy(update={"main_branch": None})
    monkeypatch.setattr(
        service,
        "get_repository_details_from_repo_name",
        AsyncMock(return_value=repo_without_branch),
    )
    with pytest.raises(ResourceNotFoundError):
        await service._get_cursorrules_url("workspace/repo")


@pytest.mark.asyncio
async def test_bitbucket_get_microagents_directory_url(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    service = BitBucketService(token=SecretStr("token"))
    repo = Repository(
        id="1",
        full_name="workspace/repo",
        git_provider=ProviderType.BITBUCKET,
        is_public=True,
        main_branch="dev",
    )
    monkeypatch.setattr(
        service, "get_repository_details_from_repo_name", AsyncMock(return_value=repo)
    )
    url = await service._get_microagents_directory_url(
        "workspace/repo", ".Forge/microagents"
    )
    assert url.endswith("/src/dev/.Forge/microagents")


def test_bitbucket_microagent_helpers() -> None:
    service = BitBucketService(token=SecretStr("token"))
    item = {"type": "commit_file", "path": ".Forge/microagents/example.md"}
    assert service._is_valid_microagent_file(item) is True
    assert service._get_file_name_from_item(item) == "example.md"
    assert (
        service._get_file_path_from_item(item, ".Forge/microagents")
        == ".Forge/microagents/example.md"
    )


@pytest.mark.asyncio
async def test_bitbucket_get_branches_uses_fetch(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    service = BitBucketService(token=SecretStr("token"))
    branch_data = [
        {"name": "main", "target": {"hash": "abc", "date": "2024-01-01T00:00:00Z"}},
        {"name": "dev", "target": {"hash": "def"}},
    ]
    monkeypatch.setattr(
        service, "_fetch_paginated_data", AsyncMock(return_value=branch_data)
    )
    branches = await service.get_branches("workspace/repo")
    assert [branch.name for branch in branches] == ["main", "dev"]


@pytest.mark.asyncio
async def test_bitbucket_get_paginated_branches(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    responses = [
        (
            {
                "values": [
                    {"name": "main", "target": {"hash": "abc"}},
                    {"name": "dev", "target": {"hash": "def"}},
                ],
                "next": "next",
            },
            {},
        ),
    ]
    service = StubBitbucketService(responses)
    result = await service.get_paginated_branches("workspace/repo", page=2, per_page=5)
    assert isinstance(result, PaginatedBranchesResponse)
    assert result.has_next_page is True
    assert result.current_page == 2
    assert [branch.name for branch in result.branches] == ["main", "dev"]


@pytest.mark.asyncio
async def test_bitbucket_search_branches(monkeypatch: pytest.MonkeyPatch) -> None:
    responses = [
        ({"values": [{"name": "feature", "target": {"hash": "abc"}}]}, {}),
    ]
    service = StubBitbucketService(responses)
    branches = await service.search_branches("workspace/repo", "feat", per_page=10)
    assert branches[0].name == "feature"


@pytest.mark.asyncio
async def test_bitbucket_branches_invalid_repository() -> None:
    service = BitBucketService(token=SecretStr("token"))
    with pytest.raises(ValueError):
        await service.get_paginated_branches("invalid")
    with pytest.raises(ValueError):
        await service.search_branches("invalid", "query")


@pytest.mark.asyncio
async def test_bitbucket_create_pr_and_get_details() -> None:
    responses = [
        ({"links": {"html": {"href": "https://bitbucket/pr/1"}}}, {}),
        ({"state": "OPEN"}, {}),
    ]
    service = StubBitbucketService(responses)
    url = await service.create_pr("workspace/repo", "feature", "main", "Title")
    assert url.endswith("/1")
    details = await service.get_pr_details("workspace/repo", 1)
    assert details["state"] == "OPEN"
    assert await service.is_pr_open("workspace/repo", 1) is True


@pytest.mark.asyncio
async def test_bitbucket_is_pr_open_handles_missing_state_and_errors(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    service = BitBucketService(token=SecretStr("token"))
    monkeypatch.setattr(
        service, "get_pr_details", AsyncMock(return_value={"unexpected": True})
    )
    assert await service.is_pr_open("workspace/repo", 2) is True
    monkeypatch.setattr(
        service, "get_pr_details", AsyncMock(side_effect=RuntimeError("boom"))
    )
    assert await service.is_pr_open("workspace/repo", 3) is True


@pytest.mark.asyncio
async def test_bitbucket_is_pr_open_state_branch(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    service = BitBucketService(token=SecretStr("token"))
    monkeypatch.setattr(
        service, "get_pr_details", AsyncMock(return_value={"state": "OPEN"})
    )
    assert await service.is_pr_open("workspace/repo", 4) is True
    monkeypatch.setattr(
        service, "get_pr_details", AsyncMock(return_value={"state": "MERGED"})
    )
    assert await service.is_pr_open("workspace/repo", 4) is False


@pytest.mark.asyncio
async def test_bitbucket_get_microagent_content(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    service = BitBucketService(token=SecretStr("token"))
    repo = Repository(
        id="1",
        full_name="workspace/repo",
        git_provider=ProviderType.BITBUCKET,
        is_public=True,
        main_branch="main",
    )
    monkeypatch.setattr(
        service, "get_repository_details_from_repo_name", AsyncMock(return_value=repo)
    )
    monkeypatch.setattr(
        service, "_make_request", AsyncMock(return_value=({"content": "## Title"}, {}))
    )
    monkeypatch.setattr(
        service, "_parse_microagent_content", lambda response, path: "parsed"
    )
    result = await service.get_microagent_content(
        "workspace/repo", "microagents/file.md"
    )
    assert result == "parsed"

    repo_no_branch = repo.model_copy(update={"main_branch": None})
    monkeypatch.setattr(
        service,
        "get_repository_details_from_repo_name",
        AsyncMock(return_value=repo_no_branch),
    )
    with pytest.raises(ResourceNotFoundError):
        await service.get_microagent_content("workspace/repo", "microagents/file.md")


@pytest.mark.asyncio
async def test_bitbucket_get_installations(monkeypatch: pytest.MonkeyPatch) -> None:
    service = BitBucketService(token=SecretStr("token"))
    monkeypatch.setattr(
        service,
        "_fetch_paginated_data",
        AsyncMock(return_value=[{"slug": "alpha"}, {"slug": "beta"}]),
    )
    installations = await service.get_installations(query="alp")
    assert installations == ["alpha", "beta"]


@pytest.mark.asyncio
async def test_bitbucket_get_paginated_repos_with_installation() -> None:
    responses = [
        ({"values": [_make_repo(repo_id="1")], "next": "https://next?page=2"}, {}),
    ]
    service = StubBitbucketService(responses)
    repos = await service.get_paginated_repos(
        page=1, per_page=10, sort="pushed", installation_id="workspace"
    )
    assert len(repos) == 1
    assert repos[0].link_header.endswith('rel="next"')


@pytest.mark.asyncio
async def test_bitbucket_get_all_repositories_limits_results(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    service = BitBucketService(token=SecretStr("token"))
    workspaces = [{"slug": "workspace"}]
    monkeypatch.setattr(
        service,
        "_fetch_paginated_data",
        AsyncMock(side_effect=[[{"slug": "workspace"}], [_make_repo()]]),
    )
    repos = await service.get_all_repositories("pushed", AppMode.SAAS)
    assert len(repos) == 1
    assert repos[0].full_name == "workspace/repo"


@pytest.mark.asyncio
async def test_bitbucket_search_helpers(monkeypatch: pytest.MonkeyPatch) -> None:
    service = BitBucketService(token=SecretStr("token"))
    repo_obj = Repository(
        id="1",
        full_name="workspace/repo",
        git_provider=ProviderType.BITBUCKET,
        is_public=True,
    )
    monkeypatch.setattr(
        service,
        "get_repository_details_from_repo_name",
        AsyncMock(return_value=repo_obj),
    )
    public_results = await service._search_public_repository(
        "https://bitbucket.org/workspace/repo"
    )
    assert public_results == [repo_obj]

    monkeypatch.setattr(
        service, "get_paginated_repos", AsyncMock(return_value=[repo_obj])
    )
    workspace_results = await service._search_workspace_repository(
        "workspace/repo", 10, "pushed"
    )
    assert workspace_results == [repo_obj]

    monkeypatch.setattr(
        service, "get_paginated_repos", AsyncMock(side_effect=[[repo_obj], [repo_obj]])
    )
    matching = await service._search_matching_workspaces(
        "wor", 10, "pushed", ["workspace", "other"]
    )
    assert matching == [repo_obj]
    all_workspaces = await service._search_all_workspaces(
        "repo", 10, "pushed", ["workspace"]
    )
    assert all_workspaces == [repo_obj]


@pytest.mark.asyncio
async def test_bitbucket_search_repositories_routes(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    service = BitBucketService(token=SecretStr("token"))
    repo_obj = Repository(
        id="1",
        full_name="workspace/repo",
        git_provider=ProviderType.BITBUCKET,
        is_public=True,
    )
    monkeypatch.setattr(
        service, "_search_public_repository", AsyncMock(return_value=[repo_obj])
    )
    result = await service.search_repositories(
        query="https://bitbucket.org/workspace/repo",
        per_page=10,
        sort="pushed",
        order="desc",
        public=True,
    )
    assert result == [repo_obj]

    monkeypatch.setattr(
        service, "_search_public_repository", AsyncMock(return_value=[])
    )
    monkeypatch.setattr(
        service, "_search_workspace_repository", AsyncMock(return_value=[repo_obj])
    )
    result = await service.search_repositories(
        query="workspace/repo",
        per_page=10,
        sort="pushed",
        order="desc",
        public=False,
    )
    assert result == [repo_obj]

    monkeypatch.setattr(
        service, "_search_workspace_repository", AsyncMock(return_value=[])
    )
    monkeypatch.setattr(
        service, "get_installations", AsyncMock(return_value=["workspace"])
    )
    monkeypatch.setattr(
        service, "_search_matching_workspaces", AsyncMock(return_value=[repo_obj])
    )
    monkeypatch.setattr(
        service, "_search_all_workspaces", AsyncMock(return_value=[repo_obj])
    )
    result = await service.search_repositories(
        query="repo",
        per_page=10,
        sort="pushed",
        order="desc",
        public=False,
    )
    assert len(result) == 2


@pytest.mark.asyncio
async def test_bitbucket_get_user_workspaces(monkeypatch: pytest.MonkeyPatch) -> None:
    service = BitBucketService(token=SecretStr("token"))
    monkeypatch.setattr(
        service,
        "_make_request",
        AsyncMock(return_value=({"values": [{"slug": "workspace"}]}, {})),
    )
    workspaces = await service._get_user_workspaces()
    assert workspaces == [{"slug": "workspace"}]


@pytest.mark.asyncio
async def test_bitbucket_get_suggested_tasks_returns_empty() -> None:
    service = BitBucketService(token=SecretStr("token"))
    assert await service.get_suggested_tasks() == []


def test_bitbucket_base_domain_override() -> None:
    service = BitBucketService(token=SecretStr("token"), base_domain="example.com")
    assert service.BASE_URL == "https://api.example.com/2.0"
    assert service.base_domain == "example.com"


@pytest.mark.asyncio
async def test_bitbucket_get_latest_token(monkeypatch: pytest.MonkeyPatch) -> None:
    service = BitBucketService(token=SecretStr("token"))
    assert await service.get_latest_token() == service.token


@pytest.mark.asyncio
async def test_bitbucket_search_public_repository_handles_exceptions(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    service = BitBucketService(token=SecretStr("token"))
    monkeypatch.setattr(
        service,
        "get_repository_details_from_repo_name",
        AsyncMock(side_effect=ValueError("fail")),
    )
    result = await service._search_public_repository(
        "https://bitbucket.org/workspace/repo"
    )
    assert result == []


@pytest.mark.asyncio
async def test_bitbucket_workspace_search_skips_errors(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    service = BitBucketService(token=SecretStr("token"))
    repo_obj = service._parse_repository(_make_repo())
    monkeypatch.setattr(
        service,
        "get_paginated_repos",
        AsyncMock(side_effect=[RuntimeError("boom"), [repo_obj]]),
    )
    matching = await service._search_matching_workspaces(
        "work", 10, "pushed", ["workspace", "work-two", "other"]
    )
    assert matching == [repo_obj]
    monkeypatch.setattr(
        service,
        "get_paginated_repos",
        AsyncMock(side_effect=[RuntimeError("oops"), [repo_obj]]),
    )
    all_workspaces = await service._search_all_workspaces(
        "repo", 10, "pushed", ["alpha", "beta"]
    )
    assert all_workspaces == [repo_obj]


@pytest.mark.asyncio
async def test_bitbucket_get_paginated_repos_without_installation_returns_empty() -> (
    None
):
    service = BitBucketService(token=SecretStr("token"))
    result = await service.get_paginated_repos(
        page=1, per_page=10, sort="created", installation_id=None
    )
    assert result == []


@pytest.mark.asyncio
async def test_bitbucket_get_paginated_repos_sort_mappings(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    service = BitBucketService(token=SecretStr("token"))
    responses = [({"values": []}, {})] * 3
    mock_request = AsyncMock(side_effect=responses)
    monkeypatch.setattr(service, "_make_request", mock_request)

    await service.get_paginated_repos(
        page=2, per_page=5, sort="created", installation_id="workspace"
    )
    await service.get_paginated_repos(
        page=3, per_page=5, sort="full_name", installation_id="workspace"
    )
    await service.get_paginated_repos(
        page=4, per_page=5, sort="pushed", installation_id="workspace", query="repo"
    )

    created_params = mock_request.call_args_list[0][0][1]
    full_name_params = mock_request.call_args_list[1][0][1]
    default_params = mock_request.call_args_list[2][0][1]

    assert created_params["sort"] == "-created_on"
    assert "q" not in created_params
    assert full_name_params["sort"] == "name"
    assert default_params["sort"] == "-updated_on"
    assert default_params["q"] == 'name~"repo"'


@pytest.mark.asyncio
async def test_bitbucket_get_paginated_repos_formats_link_headers(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    service = BitBucketService(token=SecretStr("token"))
    response_with_page = (
        {"values": [_make_repo()], "next": "https://example.com?foo=1&page=7"},
        {},
    )
    response_without_page = (
        {"values": [_make_repo(repo_id="2")], "next": "https://example.com/next"},
        {},
    )
    monkeypatch.setattr(
        service,
        "_make_request",
        AsyncMock(side_effect=[response_with_page, response_without_page]),
    )

    repos = await service.get_paginated_repos(
        page=1, per_page=5, sort="pushed", installation_id="workspace"
    )
    assert repos[0].link_header.endswith('page=7>; rel="next"')

    repos_no_page = await service.get_paginated_repos(
        page=1, per_page=5, sort="pushed", installation_id="workspace"
    )
    assert repos_no_page[0].link_header.endswith('next>; rel="next"')


@pytest.mark.asyncio
async def test_bitbucket_get_all_repositories_skips_missing_slug_and_limits(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    service = BitBucketService(token=SecretStr("token"))
    workspaces = [{"slug": "workspace"}, {"name": "no-slug"}]
    large_repo_list = [_make_repo(repo_id=str(i)) for i in range(1001)]
    monkeypatch.setattr(
        service,
        "_fetch_paginated_data",
        AsyncMock(side_effect=[workspaces, large_repo_list]),
    )
    repos = await service.get_all_repositories("pushed", AppMode.SAAS)
    assert len(repos) == 1000
    assert repos[0].full_name == "workspace/repo"


@pytest.mark.asyncio
async def test_bitbucket_get_all_repositories_sort_variants(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    service = BitBucketService(token=SecretStr("token"))
    workspaces = [{"slug": "workspace"}]
    repo_payload: list[dict] = []
    mock_fetch = AsyncMock(side_effect=[workspaces, repo_payload])
    monkeypatch.setattr(service, "_fetch_paginated_data", mock_fetch)
    await service.get_all_repositories("created", AppMode.SAAS)
    params_created = mock_fetch.call_args_list[1][0][1]
    assert params_created["sort"] == "-created_on"

    mock_fetch = AsyncMock(side_effect=[workspaces, repo_payload])
    monkeypatch.setattr(service, "_fetch_paginated_data", mock_fetch)
    await service.get_all_repositories("full_name", AppMode.SAAS)
    params_full_name = mock_fetch.call_args_list[1][0][1]
    assert params_full_name["sort"] == "name"


@pytest.mark.asyncio
async def test_bitbucket_get_all_repositories_skips_empty_workspace(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    service = BitBucketService(token=SecretStr("token"))
    workspaces = [{"slug": None}, {"slug": "workspace"}]
    repos = [_make_repo()]
    monkeypatch.setattr(
        service, "_fetch_paginated_data", AsyncMock(side_effect=[workspaces, repos])
    )
    result = await service.get_all_repositories("pushed", AppMode.SAAS)
    assert len(result) == 1
    assert result[0].full_name == "workspace/repo"


@pytest.mark.asyncio
async def test_bitbucket_microagents_directory_helpers(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    service = BitBucketService(token=SecretStr("token"))
    repo = Repository(
        id="1",
        full_name="workspace/repo",
        git_provider=ProviderType.BITBUCKET,
        is_public=True,
        main_branch=None,
    )
    monkeypatch.setattr(
        service, "get_repository_details_from_repo_name", AsyncMock(return_value=repo)
    )
    with pytest.raises(ResourceNotFoundError):
        await service._get_microagents_directory_url(
            "workspace/repo", ".Forge/microagents"
        )
    assert service._get_microagents_directory_params("path") is None
