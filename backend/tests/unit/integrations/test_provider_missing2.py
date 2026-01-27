"""Additional tests for missing coverage in provider.py."""

from __future__ import annotations

from types import MappingProxyType
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from pydantic import SecretStr

from forge.integrations.provider import ProviderHandler, ProviderToken
from forge.integrations.service_types import (
    AuthenticationError,
    Branch,
    MicroagentContentResponse,
    MicroagentParseError,
    MicroagentResponse,
    PaginatedBranchesResponse,
    ProviderType,
    Repository,
    ResourceNotFoundError,
    SuggestedTask,
    TaskType,
)
from forge.utils.circuit_breaker import get_circuit_breaker_manager


class TestProviderHandlerGetService:
    """Test ProviderHandler._get_service missing coverage."""

    def test_get_service_unsupported_provider(self):
        """Test _get_service with unsupported provider raises KeyError."""
        handler = ProviderHandler(MappingProxyType({}))
        # ENTERPRISE_SSO is not in service_class_map, so it will raise KeyError
        with pytest.raises(KeyError):
            handler._get_service(ProviderType.ENTERPRISE_SSO)


class TestProviderHandlerGetRepositories:
    """Test ProviderHandler.get_repositories missing coverage."""

    @pytest.mark.asyncio
    async def test_get_repositories_with_pagination_error(self):
        """Test get_repositories with pagination params but missing page."""
        tokens = MappingProxyType({
            ProviderType.GITHUB: ProviderToken(token=SecretStr("token"))
        })
        handler = ProviderHandler(tokens)

        with pytest.raises(ValueError, match="Failed to provider params"):
            await handler.get_repositories(
                sort="updated",
                app_mode=object(),
                selected_provider=ProviderType.GITHUB,
                page=None,
                per_page=10,
                installation_id=None,
            )

    @pytest.mark.asyncio
    async def test_get_repositories_no_tokens_returns_empty(self):
        """Test get_repositories with no tokens returns empty list."""
        handler = ProviderHandler(MappingProxyType({}))
        result = await handler.get_repositories(
            sort="updated",
            app_mode=object(),
            selected_provider=None,
            page=None,
            per_page=10,
            installation_id=None,
        )
        assert result == []


class TestProviderHandlerGetSuggestedTasks:
    """Test ProviderHandler.get_suggested_tasks missing coverage."""

    @pytest.mark.asyncio
    async def test_get_suggested_tasks(self):
        """Test get_suggested_tasks collects tasks from GitHub."""
        tokens = MappingProxyType({
            ProviderType.GITHUB: ProviderToken(token=SecretStr("token")),
        })
        handler = ProviderHandler(tokens)

        task1 = SuggestedTask(
            git_provider=ProviderType.GITHUB,
            task_type=TaskType.OPEN_ISSUE,
            repo="acme/repo",
            issue_number=1,
            title="Task 1"
        )

        github_service = MagicMock()
        github_service.get_suggested_tasks = AsyncMock(return_value=[task1])

        services = {
            ProviderType.GITHUB: github_service,
        }

        with patch.object(handler, "_get_service", side_effect=lambda p: services[p]):
            result = await handler.get_suggested_tasks()
            assert len(result) == 1
            assert task1 in result


class TestProviderHandlerSearchRepositoriesSelectedProvider:
    """Test ProviderHandler.search_repositories with selected_provider."""

    @pytest.mark.asyncio
    async def test_search_repositories_with_selected_provider(self):
        """Test search_repositories with selected_provider."""
        tokens = MappingProxyType({
            ProviderType.GITHUB: ProviderToken(token=SecretStr("token"))
        })
        handler = ProviderHandler(tokens)

        repo = Repository(
            id="1",
            full_name="acme/repo",
            git_provider=ProviderType.GITHUB,
            is_public=True
        )

        mock_service = MagicMock()
        mock_service.search_repositories = AsyncMock(return_value=[repo])

        async def mock_async_call(op_key, func):
            if callable(func):
                result = func()
                if hasattr(result, '__await__'):
                    return await result
                return result
            return func

        with patch.object(handler, "_get_service", return_value=mock_service):
            with patch.object(
                get_circuit_breaker_manager(),
                "async_call",
                new_callable=AsyncMock,
                side_effect=mock_async_call
            ):
                result = await handler.search_repositories(
                    selected_provider=ProviderType.GITHUB,
                    query="acme",
                    per_page=10,
                    sort="updated",
                    order="desc",
                )
                assert len(result) == 1
                assert result[0] == repo

    @pytest.mark.asyncio
    async def test_search_repositories_error_handling(self):
        """Test search_repositories error handling."""
        tokens = MappingProxyType({
            ProviderType.GITHUB: ProviderToken(token=SecretStr("token")),
        })
        handler = ProviderHandler(tokens)

        github_service = MagicMock()
        github_service.search_repositories = AsyncMock(side_effect=Exception("error"))

        services = {
            ProviderType.GITHUB: github_service,
        }

        async def mock_async_call(op_key, func):
            if callable(func):
                result = func()
                if hasattr(result, '__await__'):
                    return await result
                return result
            return func

        with patch.object(handler, "_get_service", side_effect=lambda p: services[p]):
            with patch.object(
                get_circuit_breaker_manager(),
                "async_call",
                new_callable=AsyncMock,
                side_effect=mock_async_call
            ):
                result = await handler.search_repositories(
                    selected_provider=None,
                    query="acme",
                    per_page=10,
                    sort="updated",
                    order="desc",
                )
                # Should return empty list on error
                assert len(result) == 0


class TestProviderHandlerGetProviderList:
    """Test ProviderHandler._get_provider_list missing coverage."""

    def test_get_provider_list_with_providers(self):
        """Test _get_provider_list with provided list."""
        handler = ProviderHandler(MappingProxyType({}))
        providers = [ProviderType.GITHUB]
        result = handler._get_provider_list(providers)
        assert result == providers

    def test_get_provider_list_without_providers(self):
        """Test _get_provider_list without provided list uses all tokens."""
        tokens = MappingProxyType({
            ProviderType.GITHUB: ProviderToken(token=SecretStr("token")),
        })
        handler = ProviderHandler(tokens)
        result = handler._get_provider_list(None)
        assert ProviderType.GITHUB in result
        assert len(result) == 1


class TestProviderHandlerGetProviderToken:
    """Test ProviderHandler._get_provider_token missing coverage."""

    @pytest.mark.asyncio
    async def test_get_provider_token_with_get_latest(self):
        """Test _get_provider_token with get_latest=True."""
        tokens = MappingProxyType({
            ProviderType.GITHUB: ProviderToken(token=SecretStr("token"))
        })
        handler = ProviderHandler(tokens)
        handler.REFRESH_TOKEN_URL = "http://example.com/refresh"
        handler.sid = "session123"

        new_token = SecretStr("new-token")

        with patch.object(
            handler,
            "_get_latest_provider_token",
            AsyncMock(return_value=new_token)
        ):
            result = await handler._get_provider_token(ProviderType.GITHUB, get_latest=True)
            assert result == new_token

    @pytest.mark.asyncio
    async def test_get_provider_token_without_get_latest(self):
        """Test _get_provider_token with get_latest=False."""
        existing_token = ProviderToken(token=SecretStr("existing-token"))
        tokens = MappingProxyType({
            ProviderType.GITHUB: existing_token
        })
        handler = ProviderHandler(tokens)

        result = await handler._get_provider_token(ProviderType.GITHUB, get_latest=False)
        assert result == SecretStr("existing-token")


class TestProviderHandlerVerifyRepoProvider:
    """Test ProviderHandler.verify_repo_provider missing coverage."""

    @pytest.mark.asyncio
    async def test_verify_repo_provider_specified_provider_error(self):
        """Test verify_repo_provider with specified provider that errors."""
        tokens = MappingProxyType({
            ProviderType.GITHUB: ProviderToken(token=SecretStr("token"))
        })
        handler = ProviderHandler(tokens)

        mock_service = MagicMock()
        mock_service.get_repository_details_from_repo_name = AsyncMock(
            side_effect=Exception("error")
        )

        async def mock_async_call(op_key, func):
            if callable(func):
                result = func()
                if hasattr(result, '__await__'):
                    return await result
                return result
            return func

        with patch.object(handler, "_get_service", return_value=mock_service):
            with patch.object(
                get_circuit_breaker_manager(),
                "async_call",
                new_callable=AsyncMock,
                side_effect=mock_async_call
            ):
                with pytest.raises(AuthenticationError):
                    await handler.verify_repo_provider(
                        "acme/repo",
                        specified_provider=ProviderType.GITHUB
                    )


class TestProviderHandlerGetBranches:
    """Test ProviderHandler.get_branches missing coverage."""

    @pytest.mark.asyncio
    async def test_get_branches_success(self):
        """Test get_branches success path."""
        tokens = MappingProxyType({
            ProviderType.GITHUB: ProviderToken(token=SecretStr("token"))
        })
        handler = ProviderHandler(tokens)

        branch = Branch(name="main", commit_sha="abc123", protected=False)
        response = PaginatedBranchesResponse(
            branches=[branch],
            has_next_page=False,
            current_page=1,
            per_page=30,
            total_count=1
        )

        mock_service = MagicMock()
        mock_service.get_paginated_branches = AsyncMock(return_value=response)

        async def mock_async_call(op_key, func):
            if callable(func):
                result = func()
                if hasattr(result, '__await__'):
                    return await result
                return result
            return func

        with patch.object(handler, "_get_service", return_value=mock_service):
            with patch.object(
                get_circuit_breaker_manager(),
                "async_call",
                new_callable=AsyncMock,
                side_effect=mock_async_call
            ):
                result = await handler.get_branches("acme/repo")
                assert isinstance(result, PaginatedBranchesResponse)
                assert len(result.branches) == 1


class TestProviderHandlerGetMicroagents:
    """Test ProviderHandler.get_microagents missing coverage."""

    @pytest.mark.asyncio
    async def test_get_microagents_success(self):
        """Test get_microagents success path."""
        tokens = MappingProxyType({
            ProviderType.GITHUB: ProviderToken(token=SecretStr("token"))
        })
        handler = ProviderHandler(tokens)

        from datetime import datetime
        microagent = MicroagentResponse(
            name="agent.md",
            path=".Forge/microagents/agent.md",
            git_provider="github",
            created_at=datetime.now()
        )

        mock_service = MagicMock()
        mock_service.get_microagents = AsyncMock(return_value=[microagent])

        async def mock_async_call(op_key, func):
            if callable(func):
                result = func()
                if hasattr(result, '__await__'):
                    return await result
                return result
            return func

        with patch.object(handler, "_get_service", return_value=mock_service):
            with patch.object(
                get_circuit_breaker_manager(),
                "async_call",
                new_callable=AsyncMock,
                side_effect=mock_async_call
            ):
                result = await handler.get_microagents("acme/repo")
                assert len(result) == 1
                assert result[0].name == microagent.name


class TestProviderHandlerVerifyRepository:
    """Test ProviderHandler._verify_repository missing coverage."""

    @pytest.mark.asyncio
    async def test_verify_repository_no_tokens_returns_github(self):
        """Test _verify_repository with no tokens returns GitHub."""
        handler = ProviderHandler(MappingProxyType({}))
        provider, repo_name = await handler._verify_repository("acme/repo")
        assert provider == ProviderType.GITHUB
        assert repo_name == "acme/repo"


class TestProviderHandlerBuildAuthenticatedUrl:
    """Test ProviderHandler._build_authenticated_url missing coverage."""

    def test_build_authenticated_url_github(self):
        """Test _build_authenticated_url for GitHub."""
        handler = ProviderHandler(MappingProxyType({}))
        url = handler._build_authenticated_url(
            ProviderType.GITHUB,
            "github.com",
            "acme/repo",
            "token123"
        )
        assert url == "https://token123@github.com/acme/repo.git"


class TestProviderHandlerGetRemoteUrl:
    """Test ProviderHandler._get_remote_url missing coverage."""

    def test_get_remote_url_with_token(self):
        """Test _get_remote_url with token."""
        tokens = MappingProxyType({
            ProviderType.GITHUB: ProviderToken(token=SecretStr("token123"))
        })
        handler = ProviderHandler(tokens)
        url = handler._get_remote_url(ProviderType.GITHUB, "github.com", "acme/repo")
        assert "token123" in url
        assert "@" in url

    def test_get_remote_url_with_none_token(self):
        """Test _get_remote_url with None token."""
        tokens = MappingProxyType({
            ProviderType.GITHUB: ProviderToken(token=None)
        })
        handler = ProviderHandler(tokens)
        url = handler._get_remote_url(ProviderType.GITHUB, "github.com", "acme/repo")
        assert url == "https://github.com/acme/repo.git"
        assert "@" not in url


class TestProviderHandlerGetAuthenticatedGitUrl:
    """Test ProviderHandler.get_authenticated_git_url missing coverage."""

    @pytest.mark.asyncio
    async def test_get_authenticated_git_url_success(self):
        """Test get_authenticated_git_url success path."""
        tokens = MappingProxyType({
            ProviderType.GITHUB: ProviderToken(token=SecretStr("token123"))
        })
        handler = ProviderHandler(tokens)

        repo = Repository(
            id="1",
            full_name="acme/repo",
            git_provider=ProviderType.GITHUB,
            is_public=True
        )

        with patch.object(handler, "_verify_repository", AsyncMock(return_value=(ProviderType.GITHUB, "acme/repo"))):
            url = await handler.get_authenticated_git_url("acme/repo")
            assert "acme/repo" in url
            assert ".git" in url


class TestProviderHandlerIsPrOpen:
    """Test ProviderHandler.is_pr_open missing coverage."""

    @pytest.mark.asyncio
    async def test_is_pr_open_true(self):
        """Test is_pr_open returns True when PR is open."""
        tokens = MappingProxyType({
            ProviderType.GITHUB: ProviderToken(token=SecretStr("token"))
        })
        handler = ProviderHandler(tokens)

        mock_service = MagicMock()
        mock_service.is_pr_open = AsyncMock(return_value=True)

        async def mock_async_call(op_key, func):
            if callable(func):
                result = func()
                if hasattr(result, '__await__'):
                    return await result
                return result
            return func

        with patch.object(handler, "_get_service", return_value=mock_service):
            with patch.object(
                get_circuit_breaker_manager(),
                "async_call",
                new_callable=AsyncMock,
                side_effect=mock_async_call
            ):
                result = await handler.is_pr_open("acme/repo", 1, ProviderType.GITHUB)
                assert result is True

    @pytest.mark.asyncio
    async def test_is_pr_open_false(self):
        """Test is_pr_open returns False when PR is closed."""
        tokens = MappingProxyType({
            ProviderType.GITHUB: ProviderToken(token=SecretStr("token"))
        })
        handler = ProviderHandler(tokens)

        mock_service = MagicMock()
        mock_service.is_pr_open = AsyncMock(return_value=False)

        async def mock_async_call(op_key, func):
            if callable(func):
                result = func()
                if hasattr(result, '__await__'):
                    return await result
                return result
            return func

        with patch.object(handler, "_get_service", return_value=mock_service):
            with patch.object(
                get_circuit_breaker_manager(),
                "async_call",
                new_callable=AsyncMock,
                side_effect=mock_async_call
            ):
                result = await handler.is_pr_open("acme/repo", 1, ProviderType.GITHUB)
                assert result is False

    @pytest.mark.asyncio
    async def test_is_pr_open_exception_returns_true(self):
        """Test is_pr_open returns True on exception."""
        tokens = MappingProxyType({
            ProviderType.GITHUB: ProviderToken(token=SecretStr("token"))
        })
        handler = ProviderHandler(tokens)

        mock_service = MagicMock()
        mock_service.is_pr_open = AsyncMock(side_effect=Exception("error"))

        async def mock_async_call(op_key, func):
            if callable(func):
                result = func()
                if hasattr(result, '__await__'):
                    return await result
                return result
            return func

        with patch.object(handler, "_get_service", return_value=mock_service):
            with patch.object(
                get_circuit_breaker_manager(),
                "async_call",
                new_callable=AsyncMock,
                side_effect=mock_async_call
            ):
                result = await handler.is_pr_open("acme/repo", 1, ProviderType.GITHUB)
                assert result is True

