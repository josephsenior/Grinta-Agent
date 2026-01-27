from __future__ import annotations

from datetime import datetime
from types import MappingProxyType, SimpleNamespace
from unittest.mock import AsyncMock, patch

import pytest
from pydantic import SecretStr

from forge.events.action.commands import CmdRunAction
from forge.integrations.provider import ProviderHandler, ProviderToken
from forge.integrations.service_types import (
    AuthenticationError,
    Branch,
    MicroagentParseError,
    PaginatedBranchesResponse,
    ProviderType,
    Repository,
    ResourceNotFoundError,
)
from forge.microagent.types import MicroagentContentResponse, MicroagentResponse


def make_tokens(
    overrides: dict[ProviderType, ProviderToken] | None = None,
) -> MappingProxyType[ProviderType, ProviderToken]:
    base: dict[ProviderType, ProviderToken] = {
        ProviderType.GITHUB: ProviderToken(
            token=SecretStr("gh-token"), user_id="1", host=None
        ),
    }
    if overrides:
        base.update(overrides)
    return MappingProxyType(base)


def make_handler(
    overrides: dict[ProviderType, ProviderToken] | None = None, **kwargs
) -> ProviderHandler:
    return ProviderHandler(make_tokens(overrides), **kwargs)


def make_empty_handler(**kwargs) -> ProviderHandler:
    return ProviderHandler(MappingProxyType({}), **kwargs)


def make_repo(
    provider: ProviderType = ProviderType.GITHUB,
    full_name: str = "acme/repo",
    repo_id: str = "1",
) -> Repository:
    return Repository(
        id=repo_id,
        full_name=full_name,
        git_provider=provider,
        is_public=True,
    )


def make_branch(name: str = "main") -> Branch:
    return Branch(name=name, commit_sha="abc123", protected=False)


def make_paginated(
    branches: list[Branch],
    page: int = 1,
    per_page: int = 30,
    has_next: bool = False,
    total: int | None = None,
) -> PaginatedBranchesResponse:
    return PaginatedBranchesResponse(
        branches=branches,
        has_next_page=has_next,
        current_page=page,
        per_page=per_page,
        total_count=total,
    )


def make_microagent(name: str = "agent") -> MicroagentResponse:
    return MicroagentResponse(
        name=name, path=f"{name}.md", created_at=datetime.utcnow()
    )


def make_microagent_content(
    name: str = "agent", provider: str = "github"
) -> MicroagentContentResponse:
    return MicroagentContentResponse(
        content=f"{name}-content",
        path=f"{name}.md",
        triggers=["t"],
        git_provider=provider,
    )


def make_service(**methods: AsyncMock) -> SimpleNamespace:
    return SimpleNamespace(**methods)


@pytest.mark.asyncio
async def test_get_user_success() -> None:
    handler = make_handler()
    user = object()
    service = make_service(get_user=AsyncMock(return_value=user))
    with patch.object(handler, "_get_service", return_value=service):
        result = await handler.get_user()
    assert result is user
    service.get_user.assert_awaited_once()


@pytest.mark.asyncio
async def test_get_user_authentication_error() -> None:
    handler = make_handler()
    service = make_service(get_user=AsyncMock(side_effect=Exception("boom")))
    with patch.object(handler, "_get_service", return_value=service):
        with pytest.raises(AuthenticationError):
            await handler.get_user()
    service.get_user.assert_awaited_once()


@pytest.mark.asyncio
async def test_get_repositories_selected_provider_requires_pagination() -> None:
    handler = make_handler()
    with pytest.raises(ValueError):
        await handler.get_repositories(
            sort="updated",
            app_mode=object(),
            selected_provider=ProviderType.GITHUB,
            page=None,
            per_page=None,
            installation_id=None,
        )


@pytest.mark.asyncio
async def test_get_repositories_selected_provider_success() -> None:
    handler = make_handler()
    repo = make_repo()
    service = make_service(get_paginated_repos=AsyncMock(return_value=[repo]))
    with patch.object(handler, "_get_service", return_value=service):
        result = await handler.get_repositories(
            sort="updated",
            app_mode=object(),
            selected_provider=ProviderType.GITHUB,
            page=1,
            per_page=5,
            installation_id="123",
        )
    assert result == [repo]
    service.get_paginated_repos.assert_awaited_once_with(1, 5, "updated", "123")


@pytest.mark.asyncio
async def test_get_repositories_success() -> None:
    handler = make_handler()
    repo = make_repo(ProviderType.GITHUB, "acme/repo1", "1")
    services = {
        ProviderType.GITHUB: make_service(
            get_all_repositories=AsyncMock(return_value=[repo])
        ),
    }
    with patch.object(
        handler, "_get_service", side_effect=lambda provider: services[provider]
    ):
        result = await handler.get_repositories(
            sort="updated",
            app_mode=object(),
            selected_provider=None,
            page=None,
            per_page=None,
            installation_id=None,
        )
    assert result == [repo]
    services[ProviderType.GITHUB].get_all_repositories.assert_awaited_once()


@pytest.mark.asyncio
async def test_get_repositories_error_returns_empty() -> None:
    handler = make_handler()
    services = {
        ProviderType.GITHUB: make_service(
            get_all_repositories=AsyncMock(side_effect=Exception("boom"))
        ),
    }
    with patch.object(
        handler, "_get_service", side_effect=lambda provider: services[provider]
    ):
        result = await handler.get_repositories(
            sort="updated",
            app_mode=object(),
            selected_provider=None,
            page=None,
            per_page=None,
            installation_id=None,
        )
    assert result == []
    services[ProviderType.GITHUB].get_all_repositories.assert_awaited_once()


@pytest.mark.asyncio
async def test_search_branches_selected_provider_success() -> None:
    handler = make_handler()
    branch = make_branch()
    service = make_service(search_branches=AsyncMock(return_value=[branch]))
    with patch.object(handler, "_get_service", return_value=service):
        result = await handler.search_branches(
            selected_provider=ProviderType.GITHUB,
            repository="acme/repo",
            query="feature",
            per_page=20,
        )
    assert result == [branch]
    service.search_branches.assert_awaited_once_with("acme/repo", "feature", 20)


@pytest.mark.asyncio
async def test_search_branches_selected_provider_failure_returns_empty() -> None:
    handler = make_handler()
    service = make_service(search_branches=AsyncMock(side_effect=Exception("boom")))
    with patch.object(handler, "_get_service", return_value=service):
        result = await handler.search_branches(
            selected_provider=ProviderType.GITHUB,
            repository="acme/repo",
            query="feature",
        )
    assert result == []
    service.search_branches.assert_awaited_once()


@pytest.mark.asyncio
async def test_search_branches_resolves_provider_when_not_specified() -> None:
    handler = make_handler()
    branch = make_branch()
    repo = make_repo(ProviderType.GITHUB)
    service = make_service(search_branches=AsyncMock(return_value=[branch]))
    with (
        patch.object(
            handler, "verify_repo_provider", AsyncMock(return_value=repo)
        ) as verify_mock,
        patch.object(
            handler,
            "_get_service",
            return_value=service,
        ),
    ):
        result = await handler.search_branches(
            selected_provider=None,
            repository="acme/repo",
            query="feature",
        )
    assert result == [branch]
    verify_mock.assert_awaited_once()
    service.search_branches.assert_awaited_once()


@pytest.mark.asyncio
async def test_search_branches_returns_empty_when_verification_fails() -> None:
    handler = make_handler()
    with patch.object(
        handler, "verify_repo_provider", AsyncMock(side_effect=Exception("boom"))
    ):
        result = await handler.search_branches(
            selected_provider=None,
            repository="acme/repo",
            query="feature",
        )
    assert result == []


def test_is_repository_url_handles_custom_host() -> None:
    overrides = {
        ProviderType.GITHUB: ProviderToken(
            token=SecretStr("gh-token"), user_id="1", host="git.example.com"
        ),
    }
    handler = make_handler(overrides)
    assert handler._is_repository_url(
        "https://git.example.com/acme/repo", ProviderType.GITHUB
    )
    assert handler._is_repository_url(
        "https://github.com/acme/repo", ProviderType.GITHUB
    )


def test_is_repository_url_requires_http_prefix() -> None:
    handler = make_handler()
    assert not handler._is_repository_url("github.com/acme/repo", ProviderType.GITHUB)
    assert not handler._is_repository_url("acme/repo", ProviderType.GITHUB)


def test_deduplicate_repositories_removes_duplicate_full_names() -> None:
    handler = make_handler()
    repo1 = make_repo(full_name="acme/repo", repo_id="1")
    repo2 = make_repo(full_name="acme/repo", repo_id="2")
    unique = handler._deduplicate_repositories([repo1, repo2])
    assert unique == [repo1]


def test_expose_env_vars_returns_plain_strings() -> None:
    handler = make_handler()
    exposed = handler.expose_env_vars({ProviderType.GITHUB: SecretStr("token")})
    assert exposed == {"github_token": "token"}


@pytest.mark.asyncio
async def test_get_env_vars_returns_secret_values() -> None:
    handler = make_handler()
    env = await handler.get_env_vars()
    assert ProviderType.GITHUB in env
    assert env[ProviderType.GITHUB].get_secret_value() == "gh-token"


@pytest.mark.asyncio
async def test_get_env_vars_can_expose_strings() -> None:
    handler = make_handler()
    env = await handler.get_env_vars(expose_secrets=True)
    assert env == {"github_token": "gh-token"}


@pytest.mark.asyncio
async def test_get_env_vars_filters_requested_providers() -> None:
    handler = make_handler()
    env = await handler.get_env_vars(providers=[ProviderType.GITHUB])
    assert list(env.keys()) == [ProviderType.GITHUB]


@pytest.mark.asyncio
async def test_get_env_vars_fetches_latest_when_requested() -> None:
    handler = make_handler()
    handler.REFRESH_TOKEN_URL = "https://example.com/api"
    handler.sid = "session-id"
    with patch.object(
        handler,
        "_get_latest_provider_token",
        AsyncMock(return_value=SecretStr("fresh")),
    ) as latest_mock:
        env = await handler.get_env_vars(get_latest=True)
    latest_mock.assert_awaited_once_with(ProviderType.GITHUB)
    assert env[ProviderType.GITHUB].get_secret_value() == "fresh"


@pytest.mark.asyncio
async def test_get_env_vars_returns_empty_when_no_tokens() -> None:
    handler = make_empty_handler()
    env = await handler.get_env_vars()
    assert env == {}


class EventStreamStub:
    def __init__(self) -> None:
        self.secrets: dict[str, str] | None = None

    def set_secrets(self, secrets: dict[str, str]) -> None:
        self.secrets = secrets


@pytest.mark.asyncio
async def test_set_event_stream_secrets_with_explicit_env_vars() -> None:
    handler = make_handler()
    event_stream = EventStreamStub()
    await handler.set_event_stream_secrets(
        event_stream, {ProviderType.GITHUB: SecretStr("value")}
    )
    assert event_stream.secrets == {"github_token": "value"}


@pytest.mark.asyncio
async def test_set_event_stream_secrets_fetches_when_env_vars_not_provided() -> None:
    handler = make_handler()
    event_stream = EventStreamStub()
    with patch.object(
        handler, "get_env_vars", AsyncMock(return_value={"github_token": "value"})
    ) as get_env_mock:
        await handler.set_event_stream_secrets(event_stream, None)
    get_env_mock.assert_awaited_once_with(expose_secrets=True)
    assert event_stream.secrets == {"github_token": "value"}


def test_check_cmd_action_for_provider_token_ref_detects_tokens() -> None:
    action = CmdRunAction(command="echo $GITHUB_TOKEN")
    providers = ProviderHandler.check_cmd_action_for_provider_token_ref(action)
    assert ProviderType.GITHUB in providers


def test_check_cmd_action_for_provider_token_ref_ignores_other_actions() -> None:
    class DummyAction:
        pass

    providers = ProviderHandler.check_cmd_action_for_provider_token_ref(DummyAction())
    assert providers == []


def test_get_provider_env_key_formats_value() -> None:
    assert (
        ProviderHandler.get_provider_env_key(ProviderType.GITHUB)
        == "github_token"
    )


@pytest.mark.asyncio
async def test_verify_repo_provider_success() -> None:
    handler = make_handler()
    repo = make_repo()
    service = make_service(
        get_repository_details_from_repo_name=AsyncMock(return_value=repo)
    )
    with patch.object(handler, "_get_service", return_value=service):
        result = await handler.verify_repo_provider("acme/repo")
    assert result == repo
    service.get_repository_details_from_repo_name.assert_awaited_once_with("acme/repo")


@pytest.mark.asyncio
async def test_verify_repo_provider_uses_specified_provider() -> None:
    handler = make_handler()
    repo = make_repo()
    service = make_service(
        get_repository_details_from_repo_name=AsyncMock(return_value=repo)
    )
    with patch.object(handler, "_get_service", return_value=service):
        result = await handler.verify_repo_provider("acme/repo", ProviderType.GITHUB)
    assert result == repo
    service.get_repository_details_from_repo_name.assert_awaited_once()


@pytest.mark.asyncio
async def test_verify_repo_provider_fails() -> None:
    handler = make_handler()
    service = make_service(
        get_repository_details_from_repo_name=AsyncMock(
            side_effect=Exception("boom")
        )
    )
    with patch.object(
        handler, "_get_service", return_value=service
    ):
        with pytest.raises(AuthenticationError):
            await handler.verify_repo_provider("acme/repo")


@pytest.mark.asyncio
async def test_verify_repo_provider_raises_authentication_error() -> None:
    handler = make_handler()
    service = make_service(
        get_repository_details_from_repo_name=AsyncMock(side_effect=Exception("boom"))
    )
    with patch.object(handler, "_get_service", return_value=service):
        with pytest.raises(AuthenticationError):
            await handler.verify_repo_provider("acme/repo")


@pytest.mark.asyncio
async def test_get_branches_with_specified_provider() -> None:
    handler = make_handler()
    paginated = make_paginated(
        [make_branch()], page=2, per_page=10, has_next=True, total=40
    )
    service = make_service(get_paginated_branches=AsyncMock(return_value=paginated))
    with patch.object(handler, "_get_service", return_value=service):
        result = await handler.get_branches(
            "acme/repo", ProviderType.GITHUB, page=2, per_page=10
        )
    assert result == paginated
    service.get_paginated_branches.assert_awaited_once_with("acme/repo", 2, 10)


@pytest.mark.asyncio
async def test_get_branches_returns_default_when_all_fail() -> None:
    handler = make_handler()
    service = make_service(
        get_paginated_branches=AsyncMock(side_effect=Exception("boom"))
    )
    with patch.object(handler, "_get_service", return_value=service):
        result = await handler.get_branches(
            "acme/repo", ProviderType.GITHUB, page=3, per_page=5
        )
    assert result.branches == []
    assert result.has_next_page is False
    assert result.current_page == 3
    assert result.per_page == 5


@pytest.mark.asyncio
async def test_get_branches_error_returns_empty() -> None:
    handler = make_handler()
    service = make_service(
        get_paginated_branches=AsyncMock(side_effect=Exception("boom"))
    )
    with patch.object(
        handler, "_get_service", return_value=service
    ):
        result = await handler.get_branches("acme/repo")
    assert result.branches == []


@pytest.mark.asyncio
async def test_get_microagents_returns_first_successful_result() -> None:
    handler = make_handler()
    microagents = [make_microagent()]
    service = make_service(get_microagents=AsyncMock(return_value=microagents))
    with patch.object(handler, "_get_service", return_value=service):
        result = await handler.get_microagents("acme/repo")
    assert result == microagents
    service.get_microagents.assert_awaited_once_with("acme/repo")


@pytest.mark.asyncio
async def test_get_microagents_aggregates_errors() -> None:
    handler = make_handler()
    services = {
        ProviderType.GITHUB: make_service(
            get_microagents=AsyncMock(side_effect=Exception("boom"))
        ),
    }
    with patch.object(
        handler, "_get_service", side_effect=lambda provider: services[provider]
    ):
        with pytest.raises(AuthenticationError):
            await handler.get_microagents("acme/repo")


@pytest.mark.asyncio
async def test_get_microagent_content_returns_result() -> None:
    handler = make_handler()
    content = make_microagent_content()
    service = make_service(get_microagent_content=AsyncMock(return_value=content))
    with patch.object(handler, "_get_service", return_value=service):
        result = await handler.get_microagent_content(
            "acme/repo", "microagents/file.md"
        )
    assert result == content
    service.get_microagent_content.assert_awaited_once_with(
        "acme/repo", "microagents/file.md"
    )


@pytest.mark.asyncio
async def test_get_microagent_content_not_found_raises_resource_not_found() -> None:
    handler = make_handler()
    service = make_service(
        get_microagent_content=AsyncMock(
            side_effect=ResourceNotFoundError("missing")
        )
    )
    with patch.object(
        handler, "_get_service", return_value=service
    ):
        with pytest.raises(ResourceNotFoundError):
            await handler.get_microagent_content(
                "acme/repo", "microagents/file.md"
            )


@pytest.mark.asyncio
async def test_get_microagent_content_raises_authentication_error() -> None:
    handler = make_handler()
    service = make_service(
        get_microagent_content=AsyncMock(
            side_effect=MicroagentParseError("bad content")
        )
    )
    with patch.object(handler, "_get_service", return_value=service):
        with pytest.raises(AuthenticationError):
            await handler.get_microagent_content("acme/repo", "microagents/file.md")


@pytest.mark.asyncio
async def test_get_authenticated_git_url_includes_token() -> None:
    overrides = {
        ProviderType.GITHUB: ProviderToken(
            token=SecretStr("gh-token"), user_id="1", host="github.example.com"
        ),
    }
    handler = make_handler(overrides)
    with patch.object(
        handler,
        "_verify_repository",
        AsyncMock(return_value=(ProviderType.GITHUB, "acme/repo")),
    ):
        url = await handler.get_authenticated_git_url("acme/repo")
    assert url == "https://gh-token@github.example.com/acme/repo.git"


@pytest.mark.asyncio
async def test_get_authenticated_git_url_without_token_returns_basic_url() -> None:
    handler = make_handler()
    with patch.object(
        handler,
        "_verify_repository",
        AsyncMock(return_value=(ProviderType.GITHUB, "acme/repo")),
    ):
        url = await handler.get_authenticated_git_url("acme/repo")
    assert url == "https://github.com/acme/repo.git"


def test_get_authenticated_domain_prefers_custom_host() -> None:
    overrides = {
        ProviderType.GITHUB: ProviderToken(
            token=SecretStr("gh-token"), user_id="1", host="github.example.com"
        ),
    }
    handler = make_handler(overrides)
    assert (
        handler._get_authenticated_domain(ProviderType.GITHUB) == "github.example.com"
    )


def test_get_remote_url_variants() -> None:
    handler = make_handler()
    github_url = handler._get_remote_url(ProviderType.GITHUB, "github.com", "acme/repo")
    assert github_url == "https://github.com/acme/repo.git"


@pytest.mark.asyncio
async def test_verify_repository_wraps_authentication_error() -> None:
    handler = make_handler()
    with patch.object(
        handler,
        "verify_repo_provider",
        AsyncMock(side_effect=AuthenticationError("bad token")),
    ):
        with pytest.raises(
            AuthenticationError, match="Git provider authentication issue"
        ):
            await handler._verify_repository("acme/repo")


@pytest.mark.asyncio
async def test_get_github_installations() -> None:
    handler = make_handler()
    service = make_service(get_installations=AsyncMock(return_value=["1", "2"]))
    with patch.object(handler, "_get_service", return_value=service):
        result = await handler.get_github_installations()
    assert result == ["1", "2"]


@pytest.mark.asyncio
async def test_get_github_installations_on_error_returns_empty() -> None:
    handler = make_handler()
    service = make_service(get_installations=AsyncMock(side_effect=Exception("boom")))
    with patch.object(handler, "_get_service", return_value=service):
        result = await handler.get_github_installations()
    assert result == []


@pytest.mark.asyncio
async def test_get_suggested_tasks_aggregates() -> None:
    overrides = {
        ProviderType.ENTERPRISE_SSO: ProviderToken(
            token=SecretStr("gl-token"), user_id="2", host=None
        ),
    }
    handler = make_handler(overrides)
    tasks1 = ["t1"]
    tasks2 = ["t2"]
    services = {
        ProviderType.GITHUB: make_service(
            get_suggested_tasks=AsyncMock(return_value=tasks1)
        ),
        ProviderType.ENTERPRISE_SSO: make_service(
            get_suggested_tasks=AsyncMock(return_value=tasks2)
        ),
    }
    with patch.object(
        handler, "_get_service", side_effect=lambda provider: services[provider]
    ):
        result = await handler.get_suggested_tasks()
    assert result == tasks1 + tasks2


@pytest.mark.asyncio
async def test_search_repositories_selected_provider_deduplicates() -> None:
    handler = make_handler()
    repo = make_repo()
    duplicate = make_repo(repo_id="2")
    service = make_service(
        search_repositories=AsyncMock(return_value=[repo, duplicate])
    )
    with patch.object(handler, "_get_service", return_value=service):
        result = await handler.search_repositories(
            selected_provider=ProviderType.GITHUB,
            query="https://github.com/acme/repo",
            per_page=10,
            sort="updated",
            order="desc",
        )
    assert result == [repo]


@pytest.mark.asyncio
async def test_search_repositories_across_providers() -> None:
    handler = make_handler()
    repo1 = make_repo()
    services = {
        ProviderType.GITHUB: make_service(
            search_repositories=AsyncMock(return_value=[repo1])
        ),
    }
    with patch.object(
        handler, "_get_service", side_effect=lambda provider: services[provider]
    ):
        result = await handler.search_repositories(
            selected_provider=None,
            query="acme",
            per_page=10,
            sort="updated",
            order="desc",
        )
    assert repo1 in result


@pytest.mark.asyncio
async def test_is_pr_open_returns_service_value() -> None:
    handler = make_handler()
    service = make_service(is_pr_open=AsyncMock(return_value=False))
    with patch.object(handler, "_get_service", return_value=service):
        result = await handler.is_pr_open("acme/repo", 1, ProviderType.GITHUB)
    assert result is False


@pytest.mark.asyncio
async def test_is_pr_open_returns_true_on_exception() -> None:
    handler = make_handler()
    service = make_service(is_pr_open=AsyncMock(side_effect=Exception("boom")))
    with patch.object(handler, "_get_service", return_value=service):
        result = await handler.is_pr_open("acme/repo", 1, ProviderType.GITHUB)
    assert result is True
