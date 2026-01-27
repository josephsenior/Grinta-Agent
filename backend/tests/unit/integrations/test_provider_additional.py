"""Additional comprehensive tests for forge.integrations.provider."""

from __future__ import annotations

from types import MappingProxyType
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest
from pydantic import SecretStr

from forge.integrations.provider import CustomSecret, ProviderHandler, ProviderToken
from forge.integrations.service_types import (
    AuthenticationError,
    Branch,
    PaginatedBranchesResponse,
    ProviderType,
    Repository,
    SuggestedTask,
    TaskType,
    User,
)
from forge.utils.circuit_breaker import get_circuit_breaker_manager


# Note: ProviderToken.from_value and CustomSecret.from_value are already tested in test_provider_models.py
# Removing duplicates to avoid redundancy


class TestProviderHandlerGetService:
    """Test ProviderHandler._get_service method."""

    def test_instantiates_correct_service(self):
        """Test _get_service instantiates the correct service class."""
        tokens = MappingProxyType({
            ProviderType.GITHUB: ProviderToken(
                token=SecretStr("token"),
                user_id="user123",
                host="github.company.com"
            )
        })
        handler = ProviderHandler(
            tokens,
            external_auth_id="ext-id",
            external_auth_token=SecretStr("ext-token"),
            external_token_manager=True
        )

        # Just verify the method works - actual service instantiation is tested elsewhere
        # This test covers the _get_service method path
        service = handler._get_service(ProviderType.GITHUB)
        assert service is not None


class TestProviderHandlerGetUser:
    """Test ProviderHandler.get_user edge cases."""

    @pytest.mark.asyncio
    async def test_github_success(self):
        """Test get_user succeeds with GitHub."""
        tokens = MappingProxyType({
            ProviderType.GITHUB: ProviderToken(token=SecretStr("token")),
        })
        handler = ProviderHandler(tokens)

        github_user = User(id="1", login="github_user", avatar_url="https://example.com/avatar.png")

        github_service = MagicMock()
        github_service.get_user = AsyncMock(return_value=github_user)

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
                result = await handler.get_user()
                assert result == github_user


class TestProviderHandlerGetLatestToken:
    """Test ProviderHandler._get_latest_provider_token additional cases."""

    @pytest.mark.asyncio
    async def test_handles_timeout_exception(self, monkeypatch):
        """Test token refresh handles TimeoutException."""
        tokens = MappingProxyType({
            ProviderType.GITHUB: ProviderToken(token=SecretStr("old-token"))
        })
        handler = ProviderHandler(
            tokens,
            sid="session-123",
            session_api_key="api-key"
        )
        handler.REFRESH_TOKEN_URL = "https://example.com/api/refresh-tokens"

        mock_client = MagicMock()
        mock_client.get = AsyncMock(side_effect=httpx.TimeoutException("Timeout"))
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)

        monkeypatch.setattr("httpx.AsyncClient", lambda *args, **kwargs: mock_client)

        token = await handler._get_latest_provider_token(ProviderType.GITHUB)
        assert token is None

    @pytest.mark.asyncio
    async def test_handles_http_status_error(self, monkeypatch):
        """Test token refresh handles HTTP status errors."""
        tokens = MappingProxyType({
            ProviderType.GITHUB: ProviderToken(token=SecretStr("old-token"))
        })
        handler = ProviderHandler(
            tokens,
            sid="session-123",
            session_api_key="api-key"
        )
        handler.REFRESH_TOKEN_URL = "https://example.com/api/refresh-tokens"

        mock_response = MagicMock()
        mock_response.raise_for_status.side_effect = httpx.HTTPStatusError(
            "Bad Request", request=MagicMock(), response=MagicMock()
        )

        mock_client = MagicMock()
        mock_client.get = AsyncMock(return_value=mock_response)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)

        monkeypatch.setattr("httpx.AsyncClient", lambda *args, **kwargs: mock_client)

        token = await handler._get_latest_provider_token(ProviderType.GITHUB)
        assert token is None


class TestProviderHandlerGetRepositories:
    """Test ProviderHandler.get_repositories additional cases."""

    @pytest.mark.asyncio
    async def test_github_success(self):
        """Test get_repositories returns results from GitHub."""
        tokens = MappingProxyType({
            ProviderType.GITHUB: ProviderToken(token=SecretStr("token")),
        })
        handler = ProviderHandler(tokens)

        repo1 = Repository(
            id="1",
            full_name="owner/repo1",
            git_provider=ProviderType.GITHUB,
            is_public=True
        )

        github_service = MagicMock()
        github_service.get_all_repositories = AsyncMock(return_value=[repo1])

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
                result = await handler.get_repositories(
                    sort="updated",
                    app_mode=object(),
                    selected_provider=None,
                    page=None,
                    per_page=None,
                    installation_id=None,
                )
                assert len(result) == 1
                assert repo1 in result


class TestProviderHandlerGetSuggestedTasks:
    """Test ProviderHandler.get_suggested_tasks."""

    @pytest.mark.asyncio
    async def test_github_success(self):
        """Test get_suggested_tasks returns tasks from GitHub."""
        tokens = MappingProxyType({
            ProviderType.GITHUB: ProviderToken(token=SecretStr("token")),
        })
        handler = ProviderHandler(tokens)

        task1 = SuggestedTask(
            git_provider=ProviderType.GITHUB,
            task_type=TaskType.OPEN_ISSUE,
            repo="owner/repo1",
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

    @pytest.mark.asyncio
    async def test_handles_errors(self):
        """Test get_suggested_tasks handles errors from GitHub."""
        tokens = MappingProxyType({
            ProviderType.GITHUB: ProviderToken(token=SecretStr("token")),
        })
        handler = ProviderHandler(tokens)

        github_service = MagicMock()
        github_service.get_suggested_tasks = AsyncMock(side_effect=Exception("error"))

        services = {
            ProviderType.GITHUB: github_service,
        }

        with patch.object(handler, "_get_service", side_effect=lambda p: services[p]):
            result = await handler.get_suggested_tasks()
            assert len(result) == 0


class TestProviderHandlerGetBranches:
    """Test ProviderHandler.get_branches additional cases."""

    @pytest.mark.asyncio
    async def test_with_specified_provider_success(self):
        """Test get_branches with specified provider."""
        tokens = MappingProxyType({
            ProviderType.GITHUB: ProviderToken(token=SecretStr("token"))
        })
        handler = ProviderHandler(tokens)

        branch = Branch(name="main", commit_sha="abc123", protected=False)
        paginated = PaginatedBranchesResponse(
            branches=[branch],
            has_next_page=True,
            current_page=1,
            per_page=30,
            total_count=50
        )

        mock_service = MagicMock()
        mock_service.get_paginated_branches = AsyncMock(return_value=paginated)

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
                result = await handler.get_branches(
                    "acme/repo",
                    specified_provider=ProviderType.GITHUB,
                    page=1,
                    per_page=30
                )
                assert result == paginated

    @pytest.mark.asyncio
    async def test_github_error_returns_empty(self):
        """Test get_branches returns empty response when GitHub errors."""
        tokens = MappingProxyType({
            ProviderType.GITHUB: ProviderToken(token=SecretStr("token")),
        })
        handler = ProviderHandler(tokens)

        github_service = MagicMock()
        github_service.get_paginated_branches = AsyncMock(side_effect=Exception("error"))

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
                result = await handler.get_branches("acme/repo")
                assert result.branches == []


class TestProviderHandlerGetMicroagents:
    """Test ProviderHandler.get_microagents additional cases."""

    @pytest.mark.asyncio
    async def test_github_error_raises_authentication_error(self):
        """Test get_microagents raises AuthenticationError when GitHub errors."""
        tokens = MappingProxyType({
            ProviderType.GITHUB: ProviderToken(token=SecretStr("token")),
        })
        handler = ProviderHandler(tokens)

        github_service = MagicMock()
        github_service.get_microagents = AsyncMock(side_effect=Exception("github error"))

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
                with pytest.raises(AuthenticationError):
                    await handler.get_microagents("acme/repo")


class TestProviderHandlerGetMicroagentContent:
    """Test ProviderHandler.get_microagent_content additional cases."""

    @pytest.mark.asyncio
    async def test_github_error_raises_authentication_error(self):
        """Test get_microagent_content raises AuthenticationError when GitHub errors."""
        tokens = MappingProxyType({
            ProviderType.GITHUB: ProviderToken(token=SecretStr("token")),
        })
        handler = ProviderHandler(tokens)

        github_service = MagicMock()
        github_service.get_microagent_content = AsyncMock(side_effect=Exception("github error"))

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
                with pytest.raises(AuthenticationError):
                    await handler.get_microagent_content("acme/repo", "file.md")


class TestProviderHandlerGetAuthenticatedGitUrl:
    """Test ProviderHandler.get_authenticated_git_url additional cases."""

    @pytest.mark.asyncio
    async def test_github_with_token(self):
        """Test get_authenticated_git_url with GitHub token."""
        tokens = MappingProxyType({
            ProviderType.GITHUB: ProviderToken(
                token=SecretStr("gh-token"),
                user_id="user"
            )
        })
        handler = ProviderHandler(tokens)

        with patch.object(
            handler,
            "_verify_repository",
            AsyncMock(return_value=(ProviderType.GITHUB, "acme/repo"))
        ):
            url = await handler.get_authenticated_git_url("acme/repo")
            assert "gh-token@" in url
            assert url.endswith(".git")


class TestProviderHandlerIsPrOpen:
    """Test ProviderHandler.is_pr_open."""

    @pytest.mark.asyncio
    async def test_returns_service_value(self):
        """Test is_pr_open returns value from service."""
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
    async def test_returns_true_on_exception(self):
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


class TestProviderHandlerGetProviderList:
    """Test ProviderHandler._get_provider_list."""

    def test_with_providers(self):
        """Test _get_provider_list with specified providers."""
        tokens = MappingProxyType({
            ProviderType.GITHUB: ProviderToken(token=SecretStr("token"))
        })
        handler = ProviderHandler(tokens)
        providers = [ProviderType.GITHUB]
        result = handler._get_provider_list(providers)
        assert result == providers

    def test_without_providers(self):
        """Test _get_provider_list without specified providers."""
        tokens = MappingProxyType({
            ProviderType.GITHUB: ProviderToken(token=SecretStr("token"))
        })
        handler = ProviderHandler(tokens)
        result = handler._get_provider_list(None)
        assert ProviderType.GITHUB in result


class TestProviderHandlerCollectProviderTokens:
    """Test ProviderHandler._collect_provider_tokens."""

    @pytest.mark.asyncio
    async def test_filters_none_tokens(self):
        """Test _collect_provider_tokens filters out None tokens."""
        tokens = MappingProxyType({
            ProviderType.GITHUB: ProviderToken(token=SecretStr("token")),
            ProviderType.ENTERPRISE_SSO: ProviderToken(token=None)
        })
        handler = ProviderHandler(tokens)
        result = await handler._collect_provider_tokens(
            [ProviderType.GITHUB, ProviderType.ENTERPRISE_SSO],
            get_latest=False
        )
        assert ProviderType.GITHUB in result
        assert ProviderType.ENTERPRISE_SSO not in result

