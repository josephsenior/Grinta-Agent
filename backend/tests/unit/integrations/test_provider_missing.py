"""Tests for missing coverage in provider.py."""

from __future__ import annotations

from types import MappingProxyType
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
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
)
from forge.utils.circuit_breaker import get_circuit_breaker_manager


class TestProviderTokenFromValue:
    """Test ProviderToken.from_value missing coverage."""

    def test_from_value_with_dict_token_none(self):
        """Test from_value with dict where token is None."""
        token = ProviderToken.from_value({"token": None, "user_id": "user"})
        assert token.token is None or token.token.get_secret_value() == ""

    def test_from_value_with_dict_token_non_string(self):
        """Test from_value with dict where token is not a string."""
        token = ProviderToken.from_value({"token": 123, "user_id": "user"})
        assert token.token.get_secret_value() == ""

    def test_from_value_unsupported_type(self):
        """Test from_value with unsupported type raises ValueError."""
        with pytest.raises(ValueError, match="Unsupported Provider token type"):
            ProviderToken.from_value(123)


class TestCustomSecretFromValue:
    """Test CustomSecret.from_value missing coverage."""

    def test_from_value_with_dict_secret_none(self):
        """Test from_value with dict where secret is None."""
        from forge.integrations.provider import CustomSecret
        secret = CustomSecret.from_value({"secret": None, "description": "desc"})
        assert secret.secret.get_secret_value() == ""

    def test_from_value_with_dict_secret_non_string(self):
        """Test from_value with dict where secret is not a string."""
        from forge.integrations.provider import CustomSecret
        secret = CustomSecret.from_value({"secret": 123, "description": "desc"})
        assert secret.secret.get_secret_value() == ""

    def test_from_value_unsupported_type(self):
        """Test from_value with unsupported type raises ValueError."""
        from forge.integrations.provider import CustomSecret
        with pytest.raises(ValueError, match="Unsupport Provider token type"):
            CustomSecret.from_value(123)


class TestProviderHandlerGetUser:
    """Test ProviderHandler.get_user missing coverage."""

    @pytest.mark.asyncio
    async def test_get_user_all_providers_fail(self):
        """Test get_user when all providers fail."""
        tokens = MappingProxyType({
            ProviderType.GITHUB: ProviderToken(token=SecretStr("token"))
        })
        handler = ProviderHandler(tokens)
        
        mock_service = MagicMock()
        mock_service.get_user = AsyncMock(side_effect=Exception("error"))
        
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
                with pytest.raises(AuthenticationError, match="Need valid provider token"):
                    await handler.get_user()


class TestProviderHandlerGetGithubInstallations:
    """Test ProviderHandler.get_github_installations missing coverage."""

    @pytest.mark.asyncio
    async def test_get_github_installations_exception_returns_empty(self):
        """Test get_github_installations handles exceptions."""
        tokens = MappingProxyType({
            ProviderType.GITHUB: ProviderToken(token=SecretStr("token"))
        })
        handler = ProviderHandler(tokens)
        
        mock_service = MagicMock()
        mock_service.get_installations = AsyncMock(side_effect=Exception("error"))
        
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
                result = await handler.get_github_installations()
                assert result == []


class TestProviderHandlerGetRepositories:
    """Test ProviderHandler.get_repositories missing coverage."""

    @pytest.mark.asyncio
    async def test_get_repositories_pagination_error(self):
        """Test get_repositories with pagination params but error."""
        tokens = MappingProxyType({
            ProviderType.GITHUB: ProviderToken(token=SecretStr("token"))
        })
        handler = ProviderHandler(tokens)
        
        with pytest.raises(ValueError, match="Failed to provider params"):
            await handler.get_repositories(
                sort="updated",
                app_mode=object(),
                selected_provider=ProviderType.GITHUB,
                page=None,  # Missing page
                per_page=10,
                installation_id=None,
            )


class TestProviderHandlerSearchBranches:
    """Test ProviderHandler.search_branches missing coverage."""

    @pytest.mark.asyncio
    async def test_search_branches_with_selected_provider(self):
        """Test search_branches with selected provider."""
        tokens = MappingProxyType({
            ProviderType.GITHUB: ProviderToken(token=SecretStr("token"))
        })
        handler = ProviderHandler(tokens)
        
        branch = Branch(name="main", commit_sha="abc123", protected=False)
        mock_service = MagicMock()
        mock_service.search_branches = AsyncMock(return_value=[branch])
        
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
                result = await handler.search_branches(
                    selected_provider=ProviderType.GITHUB,
                    repository="acme/repo",
                    query="main"
                )
                assert len(result) == 1
                assert result[0] == branch

    @pytest.mark.asyncio
    async def test_search_branches_verify_repo_provider(self):
        """Test search_branches with verify_repo_provider path."""
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
        branch = Branch(name="main", commit_sha="abc123", protected=False)
        
        mock_service = MagicMock()
        mock_service.get_repository_details_from_repo_name = AsyncMock(return_value=repo)
        mock_service.search_branches = AsyncMock(return_value=[branch])
        
        async def mock_async_call(op_key, func):
            if callable(func):
                result = func()
                if hasattr(result, '__await__'):
                    return await result
                return result
            return func
        
        with patch.object(handler, "_get_service", return_value=mock_service):
            with patch.object(handler, "verify_repo_provider", AsyncMock(return_value=repo)):
                with patch.object(
                    get_circuit_breaker_manager(),
                    "async_call",
                    new_callable=AsyncMock,
                    side_effect=mock_async_call
                ):
                    result = await handler.search_branches(
                        selected_provider=None,
                        repository="acme/repo",
                        query="main"
                    )
                    assert len(result) == 1

    @pytest.mark.asyncio
    async def test_search_branches_error_handling(self):
        """Test search_branches error handling."""
        tokens = MappingProxyType({
            ProviderType.GITHUB: ProviderToken(token=SecretStr("token"))
        })
        handler = ProviderHandler(tokens)
        
        mock_service = MagicMock()
        mock_service.search_branches = AsyncMock(side_effect=Exception("error"))
        
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
                result = await handler.search_branches(
                    selected_provider=ProviderType.GITHUB,
                    repository="acme/repo",
                    query="main"
                )
                assert result == []


class TestProviderHandlerSearchRepositories:
    """Test ProviderHandler.search_repositories missing coverage."""

    @pytest.mark.asyncio
    async def test_search_repositories_deduplicates(self):
        """Test search_repositories deduplicates results."""
        tokens = MappingProxyType({
            ProviderType.GITHUB: ProviderToken(token=SecretStr("token")),
        })
        handler = ProviderHandler(tokens)
        
        repo1 = Repository(
            id="1",
            full_name="acme/repo",
            git_provider=ProviderType.GITHUB,
            is_public=True
        )
        repo2 = Repository(
            id="2",
            full_name="acme/repo",  # Duplicate full_name
            git_provider=ProviderType.GITHUB,
            is_public=True
        )

        github_service = MagicMock()
        github_service.search_repositories = AsyncMock(return_value=[repo1, repo2])

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
                # Verify deduplication logic is called (coverage)
                assert len(result) == 1
                assert result[0].full_name == "acme/repo"


class TestProviderHandlerSetEventStreamSecrets:
    """Test ProviderHandler.set_event_stream_secrets missing coverage."""

    @pytest.mark.asyncio
    async def test_set_event_stream_secrets_with_env_vars(self):
        """Test set_event_stream_secrets with provided env_vars."""
        tokens = MappingProxyType({
            ProviderType.GITHUB: ProviderToken(token=SecretStr("token"))
        })
        handler = ProviderHandler(tokens)

        mock_event_stream = MagicMock()
        env_vars = {
            ProviderType.GITHUB: SecretStr("env-token")
        }

        await handler.set_event_stream_secrets(mock_event_stream, env_vars=env_vars)
        mock_event_stream.set_secrets.assert_called_once()
        call_args = mock_event_stream.set_secrets.call_args[0][0]
        assert "github_token" in call_args

    @pytest.mark.asyncio
    async def test_set_event_stream_secrets_without_env_vars(self):
        """Test set_event_stream_secrets without env_vars, calls get_env_vars."""
        tokens = MappingProxyType({
            ProviderType.GITHUB: ProviderToken(token=SecretStr("token"))
        })
        handler = ProviderHandler(tokens)

        mock_event_stream = MagicMock()

        async def mock_get_env_vars(expose_secrets=True):
            return {"github_token": "token-value"}

        with patch.object(handler, "get_env_vars", side_effect=mock_get_env_vars):
            await handler.set_event_stream_secrets(mock_event_stream)
            mock_event_stream.set_secrets.assert_called_once()


class TestProviderHandlerExposeEnvVars:
    """Test ProviderHandler.expose_env_vars missing coverage."""

    def test_expose_env_vars_converts_provider_tokens(self):
        """Test expose_env_vars converts provider tokens to env vars."""
        tokens = MappingProxyType({
            ProviderType.GITHUB: ProviderToken(token=SecretStr("gh-token")),
        })
        handler = ProviderHandler(tokens)

        env_secrets = {
            ProviderType.GITHUB: SecretStr("gh-secret"),
        }

        result = handler.expose_env_vars(env_secrets)
        assert result["github_token"] == "gh-secret"


class TestProviderHandlerGetEnvVars:
    """Test ProviderHandler.get_env_vars missing coverage."""

    @pytest.mark.asyncio
    async def test_get_env_vars_without_expose_secrets(self):
        """Test get_env_vars with expose_secrets=False."""
        tokens = MappingProxyType({
            ProviderType.GITHUB: ProviderToken(token=SecretStr("token"))
        })
        handler = ProviderHandler(tokens)
        
        async def mock_collect(provider_list, get_latest):
            return {ProviderType.GITHUB: ProviderToken(token=SecretStr("collected-token"))}

        with patch.object(handler, "_collect_provider_tokens", side_effect=mock_collect):
            result = await handler.get_env_vars(expose_secrets=False)
            assert isinstance(result, dict)
            assert ProviderType.GITHUB in result
            assert isinstance(result[ProviderType.GITHUB], ProviderToken)


class TestProviderHandlerCheckCmdAction:
    """Test ProviderHandler.check_cmd_action_for_provider_token_ref missing coverage."""

    def test_check_cmd_action_returns_empty_for_non_cmd_action(self):
        """Test check_cmd_action returns empty list for non-CmdRunAction."""
        from forge.events.action.action import Action
        mock_action = MagicMock(spec=Action)
        result = ProviderHandler.check_cmd_action_for_provider_token_ref(mock_action)
        assert result == []


class TestProviderHandlerVerifyRepoProvider:
    """Test ProviderHandler.verify_repo_provider missing coverage."""

    @pytest.mark.asyncio
    async def test_verify_repo_provider_success(self):
        """Test verify_repo_provider success path."""
        tokens = MappingProxyType({
            ProviderType.GITHUB: ProviderToken(token=SecretStr("token")),
        })
        handler = ProviderHandler(tokens)
        
        repo = Repository(
            id="1",
            full_name="acme/repo",
            git_provider=ProviderType.GITHUB,
            is_public=True
        )
        
        github_service = MagicMock()
        github_service.get_repository_details_from_repo_name = AsyncMock(return_value=repo)

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
                result = await handler.verify_repo_provider("acme/repo")
                assert result == repo


class TestProviderHandlerGetBranches:
    """Test ProviderHandler.get_branches missing coverage."""

    @pytest.mark.asyncio
    async def test_get_branches_error_returns_empty_response(self):
        """Test get_branches returns empty response when all providers error."""
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
                assert isinstance(result, PaginatedBranchesResponse)
                assert result.branches == []
                assert result.has_next_page is False


class TestProviderHandlerGetMicroagents:
    """Test ProviderHandler.get_microagents missing coverage."""

    @pytest.mark.asyncio
    async def test_get_microagents_with_errors_raises_authentication_error(self):
        """Test get_microagents raises AuthenticationError when all providers error."""
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
    """Test ProviderHandler.get_microagent_content missing coverage."""

    @pytest.mark.asyncio
    async def test_get_microagent_content_success(self):
        """Test get_microagent_content success path."""
        tokens = MappingProxyType({
            ProviderType.GITHUB: ProviderToken(token=SecretStr("token"))
        })
        handler = ProviderHandler(tokens)
        
        content_response = MicroagentContentResponse(
            content="content",
            path="file.md",
            triggers=[],
            git_provider="github"
        )
        
        mock_service = MagicMock()
        mock_service.get_microagent_content = AsyncMock(return_value=content_response)
        
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
                result = await handler.get_microagent_content("acme/repo", "file.md")
                assert result == content_response

    @pytest.mark.asyncio
    async def test_get_microagent_content_github_error(self):
        """Test get_microagent_content raises AuthenticationError when github errors."""
        tokens = MappingProxyType({
            ProviderType.GITHUB: ProviderToken(token=SecretStr("token")),
        })
        handler = ProviderHandler(tokens)
        
        github_service = MagicMock()
        github_service.get_microagent_content = AsyncMock(side_effect=Exception("error"))
        
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


class TestProviderHandlerVerifyRepository:
    """Test ProviderHandler._verify_repository missing coverage."""

    @pytest.mark.asyncio
    async def test_verify_repository_with_tokens_authentication_error(self):
        """Test _verify_repository raises AuthenticationError when verify_repo_provider fails."""
        tokens = MappingProxyType({
            ProviderType.GITHUB: ProviderToken(token=SecretStr("token"))
        })
        handler = ProviderHandler(tokens)

        with patch.object(
            handler,
            "verify_repo_provider",
            AsyncMock(side_effect=AuthenticationError("auth error"))
        ):
            with pytest.raises(AuthenticationError, match="Git provider authentication issue"):
                await handler._verify_repository("acme/repo")


class TestProviderHandlerGetAuthenticatedDomain:
    """Test ProviderHandler._get_authenticated_domain missing coverage."""

    def test_get_authenticated_domain_with_custom_host(self):
        """Test _get_authenticated_domain uses custom host from token."""
        tokens = MappingProxyType({
            ProviderType.GITHUB: ProviderToken(
                token=SecretStr("token"),
                host="github.company.com"
            )
        })
        handler = ProviderHandler(tokens)

        domain = handler._get_authenticated_domain(ProviderType.GITHUB)
        assert domain == "github.company.com"


class TestProviderHandlerGetRemoteUrl:
    """Test ProviderHandler._get_remote_url missing coverage."""

    def test_get_remote_url_no_token(self):
        """Test _get_remote_url returns basic URL when no token."""
        handler = ProviderHandler(MappingProxyType({}))
        url = handler._get_remote_url(ProviderType.GITHUB, "github.com", "acme/repo")
        assert url == "https://github.com/acme/repo.git"
        assert "@" not in url
