"""Unit tests for git routes covering success and error paths."""

from __future__ import annotations

import json
from types import SimpleNamespace

import pytest

from fastapi import status
from fastapi.responses import JSONResponse

from forge.integrations.service_types import (
    AuthenticationError,
    Branch,
    PaginatedBranchesResponse,
    ProviderType,
    Repository,
    SuggestedTask,
    TaskType,
    UnknownException,
    User,
)
from forge.server.routes import git as git_routes


def _dummy_handler(**methods):
    class DummyHandler:
        def __init__(self, *args, **kwargs):
            self.kwargs = kwargs

    for name, value in methods.items():
        setattr(DummyHandler, name, value)
    return DummyHandler


@pytest.mark.asyncio
async def test_get_user_installations_github(monkeypatch):
    async def get_installations(self):
        return ["repo1"]

    handler = _dummy_handler(get_github_installations=get_installations)
    monkeypatch.setattr(git_routes, "ProviderHandler", handler)

    result = await git_routes.get_user_installations(
        ProviderType.GITHUB,
        provider_tokens={"token": "x"},
        access_token=None,
        user_id="user",
    )
    assert result == ["repo1"]


@pytest.mark.asyncio
async def test_get_user_installations_bitbucket(monkeypatch):
    async def get_workspaces(self):
        return ["team"]

    handler = _dummy_handler(get_bitbucket_workspaces=get_workspaces)
    monkeypatch.setattr(git_routes, "ProviderHandler", handler)

    result = await git_routes.get_user_installations(
        ProviderType.BITBUCKET,
        provider_tokens={"token": "x"},
        access_token=None,
        user_id="user",
    )
    assert result == ["team"]


@pytest.mark.asyncio
async def test_get_user_installations_unsupported(monkeypatch):
    handler = _dummy_handler()
    monkeypatch.setattr(git_routes, "ProviderHandler", handler)

    response = await git_routes.get_user_installations(
        ProviderType.GITLAB,
        provider_tokens={"token": "x"},
        access_token=None,
        user_id="user",
    )
    assert isinstance(response, JSONResponse)
    assert response.status_code == status.HTTP_400_BAD_REQUEST


@pytest.mark.asyncio
async def test_get_user_installations_missing_tokens():
    with pytest.raises(AuthenticationError):
        await git_routes.get_user_installations(
            ProviderType.GITHUB,
            provider_tokens=None,
            access_token=None,
            user_id="user",
        )


@pytest.mark.asyncio
async def test_get_user_repositories_success(monkeypatch):
    async def get_repos(self, *args, **kwargs):
        return [
            Repository(
                id="1",
                full_name="user/repo",
                git_provider=ProviderType.GITHUB,
                is_public=True,
            )
        ]

    handler = _dummy_handler(get_repositories=get_repos)
    monkeypatch.setattr(git_routes, "ProviderHandler", handler)
    monkeypatch.setattr(git_routes.server_config, "app_mode", "cloud")

    result = await git_routes.get_user_repositories(provider_tokens={"token": "x"})
    assert len(result) == 1
    assert result[0].full_name == "user/repo"


@pytest.mark.asyncio
async def test_get_user_repositories_unknown_exception(monkeypatch):
    async def get_repos(self, *args, **kwargs):
        raise UnknownException("boom")

    handler = _dummy_handler(get_repositories=get_repos)
    monkeypatch.setattr(git_routes, "ProviderHandler", handler)

    response = await git_routes.get_user_repositories(provider_tokens={"token": "x"})
    assert isinstance(response, JSONResponse)
    assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR


@pytest.mark.asyncio
async def test_get_user_repositories_no_tokens():
    with pytest.raises(AuthenticationError):
        await git_routes.get_user_repositories(provider_tokens=None)


@pytest.mark.asyncio
async def test_get_user_success(monkeypatch):
    async def get_user(self):
        return User(login="tester", id="1", avatar_url="http://example.com/avatar.png")

    handler = _dummy_handler(get_user=get_user)
    monkeypatch.setattr(git_routes, "ProviderHandler", handler)

    user = await git_routes.get_user(provider_tokens={"token": "x"}, access_token=None, user_id="me")
    assert user.login == "tester"


@pytest.mark.asyncio
async def test_get_user_unknown(monkeypatch):
    async def get_user(self):
        raise UnknownException("fail")

    handler = _dummy_handler(get_user=get_user)
    monkeypatch.setattr(git_routes, "ProviderHandler", handler)

    response = await git_routes.get_user(provider_tokens={"token": "x"}, access_token=None, user_id="me")
    assert isinstance(response, JSONResponse)
    assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR


@pytest.mark.asyncio
async def test_get_user_no_tokens():
    with pytest.raises(AuthenticationError):
        await git_routes.get_user(provider_tokens=None, access_token=None, user_id="me")


@pytest.mark.asyncio
async def test_search_repositories_success(monkeypatch):
    async def search(self, *args, **kwargs):
        return [
            Repository(
                id="1",
                full_name="user/repo",
                git_provider=ProviderType.GITHUB,
                is_public=True,
            )
        ]

    handler = _dummy_handler(search_repositories=search)
    monkeypatch.setattr(git_routes, "ProviderHandler", handler)

    repos = await git_routes.search_repositories("forge", provider_tokens={"token": "x"}, access_token=None, user_id="me")
    assert len(repos) == 1


@pytest.mark.asyncio
async def test_search_repositories_unknown(monkeypatch):
    async def search(self, *args, **kwargs):
        raise UnknownException("oops")

    handler = _dummy_handler(search_repositories=search)
    monkeypatch.setattr(git_routes, "ProviderHandler", handler)

    response = await git_routes.search_repositories("forge", provider_tokens={"token": "x"})
    assert isinstance(response, JSONResponse)
    assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR


@pytest.mark.asyncio
async def test_search_repositories_no_tokens():
    with pytest.raises(AuthenticationError):
        await git_routes.search_repositories("forge", provider_tokens=None)


@pytest.mark.asyncio
async def test_search_branches_success(monkeypatch):
    async def search(self, *args, **kwargs):
        return [Branch(name="main", commit_sha="abc", protected=False)]

    handler = _dummy_handler(search_branches=search)
    monkeypatch.setattr(git_routes, "ProviderHandler", handler)

    branches = await git_routes.search_branches(
        repository="repo",
        query="m",
        provider_tokens={"token": "x"},
    )
    assert branches[0].name == "main"


@pytest.mark.asyncio
async def test_search_branches_auth_error(monkeypatch):
    async def search(self, *args, **kwargs):
        raise AuthenticationError("nope")

    handler = _dummy_handler(search_branches=search)
    monkeypatch.setattr(git_routes, "ProviderHandler", handler)

    response = await git_routes.search_branches("repo", "m", provider_tokens={"token": "x"})
    assert isinstance(response, JSONResponse)
    assert response.status_code == status.HTTP_401_UNAUTHORIZED


@pytest.mark.asyncio
async def test_search_branches_unknown(monkeypatch):
    async def search(self, *args, **kwargs):
        raise UnknownException("uh oh")

    handler = _dummy_handler(search_branches=search)
    monkeypatch.setattr(git_routes, "ProviderHandler", handler)

    response = await git_routes.search_branches("repo", "m", provider_tokens={"token": "x"})
    assert isinstance(response, JSONResponse)
    assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR


@pytest.mark.asyncio
async def test_search_branches_missing_tokens():
    response = await git_routes.search_branches("repo", "m", provider_tokens=None)
    assert response.status_code == status.HTTP_401_UNAUTHORIZED


@pytest.mark.asyncio
async def test_get_suggested_tasks_success(monkeypatch):
    async def get_tasks(self, *args, **kwargs):
        return [
            SuggestedTask(
                git_provider=ProviderType.GITHUB,
                task_type=TaskType.OPEN_PR,
                repo="user/repo",
                issue_number=1,
                title="Review PR",
            )
        ]

    handler = _dummy_handler(get_suggested_tasks=get_tasks)
    monkeypatch.setattr(git_routes, "ProviderHandler", handler)

    tasks = await git_routes.get_suggested_tasks(provider_tokens={"token": "x"}, access_token=None, user_id="me")
    assert tasks[0].title == "Review PR"


@pytest.mark.asyncio
async def test_get_suggested_tasks_unknown(monkeypatch):
    async def get_tasks(self, *args, **kwargs):
        raise UnknownException("fail")

    handler = _dummy_handler(get_suggested_tasks=get_tasks)
    monkeypatch.setattr(git_routes, "ProviderHandler", handler)

    response = await git_routes.get_suggested_tasks(provider_tokens={"token": "x"}, access_token=None, user_id="me")
    assert isinstance(response, JSONResponse)
    assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR


@pytest.mark.asyncio
async def test_get_suggested_tasks_no_tokens():
    with pytest.raises(AuthenticationError):
        await git_routes.get_suggested_tasks(provider_tokens=None, access_token=None, user_id="me")


@pytest.mark.asyncio
async def test_get_repository_branches_success(monkeypatch):
    async def get_branches(self, *args, **kwargs):
        return PaginatedBranchesResponse(
            branches=[Branch(name="main", commit_sha="abc", protected=False)],
            has_next_page=False,
            current_page=1,
            per_page=30,
            total_count=1,
        )

    handler = _dummy_handler(get_branches=get_branches)
    monkeypatch.setattr(git_routes, "ProviderHandler", handler)

    result = await git_routes.get_repository_branches("owner/repo", provider_tokens={"token": "x"})
    assert result.total_count == 1
    assert result.branches[0].name == "main"


@pytest.mark.asyncio
async def test_get_repository_branches_unknown(monkeypatch):
    async def get_branches(self, *args, **kwargs):
        raise UnknownException("boom")

    handler = _dummy_handler(get_branches=get_branches)
    monkeypatch.setattr(git_routes, "ProviderHandler", handler)

    response = await git_routes.get_repository_branches("owner/repo", provider_tokens={"token": "x"})
    assert isinstance(response, JSONResponse)
    assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR


@pytest.mark.asyncio
async def test_get_repository_branches_no_tokens():
    with pytest.raises(AuthenticationError):
        await git_routes.get_repository_branches("owner/repo", provider_tokens=None)


def test_extract_repo_name():
    assert git_routes._extract_repo_name("domain/owner/repo") == "repo"


@pytest.mark.asyncio
async def test_get_repository_microagents_success(monkeypatch):
    async def get_microagents(self, name):
        return [SimpleNamespace(name="agent")]

    handler = _dummy_handler(get_microagents=get_microagents)
    monkeypatch.setattr(git_routes, "ProviderHandler", handler)

    result = await git_routes.get_repository_microagents("owner/repo")
    assert result[0].name == "agent"


@pytest.mark.asyncio
async def test_get_repository_microagents_runtime_error(monkeypatch):
    async def get_microagents(self, name):
        raise RuntimeError("bad")

    handler = _dummy_handler(get_microagents=get_microagents)
    monkeypatch.setattr(git_routes, "ProviderHandler", handler)

    response = await git_routes.get_repository_microagents("owner/repo")
    assert isinstance(response, JSONResponse)
    assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR


@pytest.mark.asyncio
async def test_get_repository_microagents_generic_error(monkeypatch):
    async def get_microagents(self, name):
        raise ValueError("oops")

    handler = _dummy_handler(get_microagents=get_microagents)
    monkeypatch.setattr(git_routes, "ProviderHandler", handler)

    response = await git_routes.get_repository_microagents("owner/repo")
    assert isinstance(response, JSONResponse)
    assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
    assert b"Error scanning repository" in response.body


@pytest.mark.asyncio
async def test_get_repository_microagents_auth_error(monkeypatch):
    async def get_microagents(self, name):
        raise AuthenticationError("no auth")

    handler = _dummy_handler(get_microagents=get_microagents)
    monkeypatch.setattr(git_routes, "ProviderHandler", handler)

    with pytest.raises(AuthenticationError):
        await git_routes.get_repository_microagents("owner/repo")


@pytest.mark.asyncio
async def test_get_repository_microagent_content_success(monkeypatch):
    async def get_content(self, repo, path):
        return SimpleNamespace(content="data")

    handler = _dummy_handler(get_microagent_content=get_content)
    monkeypatch.setattr(git_routes, "ProviderHandler", handler)

    result = await git_routes.get_repository_microagent_content("owner/repo", file_path="microagents/a.md")
    assert result.content == "data"


@pytest.mark.asyncio
async def test_get_repository_microagent_content_runtime_error(monkeypatch):
    async def get_content(self, repo, path):
        raise RuntimeError("bad")

    handler = _dummy_handler(get_microagent_content=get_content)
    monkeypatch.setattr(git_routes, "ProviderHandler", handler)

    response = await git_routes.get_repository_microagent_content("owner/repo", file_path="microagents/a.md")
    assert isinstance(response, JSONResponse)
    assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR


@pytest.mark.asyncio
async def test_get_repository_microagent_content_generic_error(monkeypatch):
    async def get_content(self, repo, path):
        raise ValueError("oops")

    handler = _dummy_handler(get_microagent_content=get_content)
    monkeypatch.setattr(git_routes, "ProviderHandler", handler)

    response = await git_routes.get_repository_microagent_content("owner/repo", file_path="microagents/a.md")
    assert isinstance(response, JSONResponse)
    assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
    assert b"Error fetching microagent content" in response.body


@pytest.mark.asyncio
async def test_get_repository_microagent_content_auth_error(monkeypatch):
    async def get_content(self, repo, path):
        raise AuthenticationError("no auth")

    handler = _dummy_handler(get_microagent_content=get_content)
    monkeypatch.setattr(git_routes, "ProviderHandler", handler)

    with pytest.raises(AuthenticationError):
        await git_routes.get_repository_microagent_content("owner/repo", file_path="microagents/a.md")


@pytest.mark.asyncio
async def test_summarize_repository(monkeypatch):
    async def fake_get_user_id(request):
        return "user123"

    monkeypatch.setattr(git_routes, "get_user_id", fake_get_user_id)

    class DummyRequest:
        pass

    response = await git_routes.summarize_repository(DummyRequest(), summarize_request={})
    assert response.status_code == status.HTTP_501_NOT_IMPLEMENTED
    assert json.loads(response.body) == {
        "error": "Repository summarization is not implemented on this server."
    }
