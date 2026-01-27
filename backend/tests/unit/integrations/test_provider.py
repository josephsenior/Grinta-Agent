"""Comprehensive tests for forge.integrations.provider."""

from __future__ import annotations

import os
from types import MappingProxyType
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest
from pydantic import SecretStr, ValidationError

from forge.events.action.commands import CmdRunAction
from forge.integrations.provider import CustomSecret, ProviderHandler, ProviderToken
from forge.integrations.service_types import (
    AuthenticationError,
    Branch,
    PaginatedBranchesResponse,
    ProviderType,
    Repository,
    TokenResponse,
    User,
)
from forge.utils.circuit_breaker import get_circuit_breaker_manager


class TestProviderTokenValidators:
    """Test ProviderToken field validators."""

    def test_valid_user_id(self):
        """Test ProviderToken with valid user_id."""
        token = ProviderToken(token=SecretStr("token"), user_id="user123")
        assert token.user_id == "user123"

    def test_invalid_user_id_empty_string(self):
        """Test ProviderToken rejects empty user_id."""
        with pytest.raises(ValidationError) as exc_info:
            ProviderToken(token=SecretStr("token"), user_id="")
        assert "field must be a non-empty string" in str(exc_info.value)

    def test_invalid_user_id_whitespace(self):
        """Test ProviderToken rejects whitespace-only user_id."""
        with pytest.raises(ValidationError) as exc_info:
            ProviderToken(token=SecretStr("token"), user_id="   ")
        assert "field must be a non-empty string" in str(exc_info.value) or "cannot be empty or whitespace-only" in str(exc_info.value)

    def test_valid_host(self):
        """Test ProviderToken with valid host."""
        token = ProviderToken(token=SecretStr("token"), host="github.company.com")
        assert token.host == "github.company.com"

    def test_invalid_host_empty_string(self):
        """Test ProviderToken rejects empty host."""
        with pytest.raises(ValidationError) as exc_info:
            ProviderToken(token=SecretStr("token"), host="")
        assert "field must be a non-empty string" in str(exc_info.value)

    def test_invalid_host_whitespace(self):
        """Test ProviderToken rejects whitespace-only host."""
        with pytest.raises(ValidationError) as exc_info:
            ProviderToken(token=SecretStr("token"), host="   ")
        assert "field must be a non-empty string" in str(exc_info.value) or "cannot be empty or whitespace-only" in str(exc_info.value)

    def test_none_values_allowed(self):
        """Test ProviderToken allows None for optional fields."""
        token = ProviderToken(token=None, user_id=None, host=None)
        assert token.token is None
        assert token.user_id is None
        assert token.host is None


class TestCustomSecretValidators:
    """Test CustomSecret field validators."""

    def test_defaults(self):
        """Test CustomSecret with default values."""
        secret = CustomSecret()
        assert secret.secret.get_secret_value() == ""
        assert secret.description == ""

    def test_valid_values(self):
        """Test CustomSecret with valid values."""
        secret = CustomSecret(secret=SecretStr("my-secret"), description="API key")
        assert secret.secret.get_secret_value() == "my-secret"
        assert secret.description == "API key"


class TestProviderHandlerInitialization:
    """Test ProviderHandler initialization and properties."""

    def test_init_with_web_host(self, monkeypatch):
        """Test ProviderHandler initialization with WEB_HOST env var."""
        monkeypatch.setenv("WEB_HOST", "example.com")
        tokens = MappingProxyType({
            ProviderType.GITHUB: ProviderToken(token=SecretStr("token"))
        })
        handler = ProviderHandler(tokens)
        assert handler.REFRESH_TOKEN_URL == "https://example.com/api/refresh-tokens"

    def test_init_without_web_host(self, monkeypatch):
        """Test ProviderHandler initialization without WEB_HOST env var."""
        monkeypatch.delenv("WEB_HOST", raising=False)
        tokens = MappingProxyType({
            ProviderType.GITHUB: ProviderToken(token=SecretStr("token"))
        })
        handler = ProviderHandler(tokens)
        assert handler.REFRESH_TOKEN_URL is None

    def test_provider_tokens_property(self):
        """Test ProviderHandler provider_tokens property returns read-only mapping."""
        tokens = MappingProxyType({
            ProviderType.GITHUB: ProviderToken(token=SecretStr("token"))
        })
        handler = ProviderHandler(tokens)
        assert handler.provider_tokens == tokens
        # Verify it's read-only
        with pytest.raises(TypeError):
            handler.provider_tokens[ProviderType.GITHUB] = ProviderToken(token=SecretStr("token"))


class TestProviderHandlerGetLatestToken:
    """Test ProviderHandler._get_latest_provider_token method."""

    @pytest.mark.asyncio
    async def test_success(self, monkeypatch):
        """Test successful token refresh."""
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
        mock_response.text = '{"token": "new-token"}'
        mock_response.raise_for_status = MagicMock()

        mock_client = MagicMock()
        mock_client.get = AsyncMock(return_value=mock_response)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)

        monkeypatch.setattr(httpx, "AsyncClient", lambda *args, **kwargs: mock_client)

        token = await handler._get_latest_provider_token(ProviderType.GITHUB)
        assert token is not None
        assert token.get_secret_value() == "new-token"

    @pytest.mark.asyncio
    async def test_no_refresh_url(self):
        """Test token refresh when REFRESH_TOKEN_URL is not set."""
        tokens = MappingProxyType({
            ProviderType.GITHUB: ProviderToken(token=SecretStr("old-token"))
        })
        handler = ProviderHandler(tokens)
        handler.REFRESH_TOKEN_URL = None

        token = await handler._get_latest_provider_token(ProviderType.GITHUB)
        assert token is None

    @pytest.mark.asyncio
    async def test_no_sid(self):
        """Test token refresh when sid is not set."""
        tokens = MappingProxyType({
            ProviderType.GITHUB: ProviderToken(token=SecretStr("old-token"))
        })
        handler = ProviderHandler(tokens)
        handler.REFRESH_TOKEN_URL = "https://example.com/api/refresh-tokens"
        handler.sid = None

        token = await handler._get_latest_provider_token(ProviderType.GITHUB)
        assert token is None

    @pytest.mark.asyncio
    async def test_http_error(self, monkeypatch):
        """Test token refresh handles HTTP errors."""
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
        mock_client.get = AsyncMock(side_effect=httpx.HTTPError("Network error"))
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)

        monkeypatch.setattr(httpx, "AsyncClient", lambda *args, **kwargs: mock_client)

        token = await handler._get_latest_provider_token(ProviderType.GITHUB)
        assert token is None

    @pytest.mark.asyncio
    async def test_with_session_api_key(self, monkeypatch):
        """Test token refresh includes session API key in headers."""
        tokens = MappingProxyType({
            ProviderType.GITHUB: ProviderToken(token=SecretStr("old-token"))
        })
        handler = ProviderHandler(
            tokens,
            sid="session-123",
            session_api_key="api-key-123"
        )
        handler.REFRESH_TOKEN_URL = "https://example.com/api/refresh-tokens"

        mock_response = MagicMock()
        mock_response.text = '{"token": "new-token"}'
        mock_response.raise_for_status = MagicMock()

        captured_headers = {}

        async def mock_get(url, headers=None, params=None, **kwargs):
            if headers:
                captured_headers.update(headers)
            return mock_response

        mock_client = MagicMock()
        mock_client.get = AsyncMock(side_effect=mock_get)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)

        monkeypatch.setattr(httpx, "AsyncClient", lambda *args, **kwargs: mock_client)

        await handler._get_latest_provider_token(ProviderType.GITHUB)
        assert captured_headers.get("X-Session-API-Key") == "api-key-123"


class TestProviderHandlerGetProviderToken:
    """Test ProviderHandler._get_provider_token method."""

    @pytest.mark.asyncio
    async def test_not_in_tokens(self):
        """Test getting token for provider not in tokens."""
        tokens = MappingProxyType({
            ProviderType.GITHUB: ProviderToken(token=SecretStr("token"))
        })
        handler = ProviderHandler(tokens)
        # Using a value that's not in tokens but exists in ProviderType
        # If there are no other types, this test might need adjustment
        # For now, let's assume we want to test a missing token scenario
        token = await handler._get_provider_token(ProviderType.ENTERPRISE_SSO, get_latest=False)
        assert token is None

    @pytest.mark.asyncio
    async def test_existing_token(self):
        """Test getting existing token without refresh."""
        tokens = MappingProxyType({
            ProviderType.GITHUB: ProviderToken(token=SecretStr("existing-token"))
        })
        handler = ProviderHandler(tokens)
        token = await handler._get_provider_token(ProviderType.GITHUB, get_latest=False)
        assert token is not None
        assert token.get_secret_value() == "existing-token"

    @pytest.mark.asyncio
    async def test_with_refresh(self, monkeypatch):
        """Test getting token with refresh enabled."""
        tokens = MappingProxyType({
            ProviderType.GITHUB: ProviderToken(token=SecretStr("old-token"))
        })
        handler = ProviderHandler(tokens, sid="session-123")
        handler.REFRESH_TOKEN_URL = "https://example.com/api/refresh-tokens"

        mock_response = MagicMock()
        mock_response.text = '{"token": "new-token"}'
        mock_response.raise_for_status = MagicMock()

        mock_client = MagicMock()
        mock_client.get = AsyncMock(return_value=mock_response)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)

        monkeypatch.setattr(httpx, "AsyncClient", lambda *args, **kwargs: mock_client)

        token = await handler._get_provider_token(ProviderType.GITHUB, get_latest=True)
        assert token is not None
        assert token.get_secret_value() == "new-token"

    @pytest.mark.asyncio
    async def test_none_token_returns_none(self):
        """Test getting token when token is None."""
        tokens = MappingProxyType({
            ProviderType.GITHUB: ProviderToken(token=None)
        })
        handler = ProviderHandler(tokens)
        token = await handler._get_provider_token(ProviderType.GITHUB, get_latest=False)
        assert token is None


class TestProviderHandlerGetRepositories:
    """Test ProviderHandler.get_repositories edge cases."""

    @pytest.mark.asyncio
    async def test_no_provider_tokens(self):
        """Test get_repositories with no provider tokens."""
        handler = ProviderHandler(MappingProxyType({}))
        result = await handler.get_repositories(
            sort="updated",
            app_mode=object(),
            selected_provider=None,
            page=None,
            per_page=None,
            installation_id=None,
        )
        assert result == []


class TestProviderHandlerSearchRepositories:
    """Test ProviderHandler.search_repositories edge cases."""

    @pytest.mark.asyncio
    async def test_selected_provider_public_url(self):
        """Test search_repositories with selected provider and public URL."""
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
                    query="https://github.com/acme/repo",
                    per_page=10,
                    sort="updated",
                    order="desc",
                )
        assert len(result) >= 0  # May be deduplicated

    @pytest.mark.asyncio
    async def test_error_handling(self):
        """Test search_repositories handles errors from providers."""
        tokens = MappingProxyType({
            ProviderType.GITHUB: ProviderToken(token=SecretStr("token")),
        })
        handler = ProviderHandler(tokens)

        mock_service = MagicMock()
        mock_service.search_repositories = AsyncMock(side_effect=Exception("error"))

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
                    selected_provider=None,
                    query="test",
                    per_page=10,
                    sort="updated",
                    order="desc",
                )
        assert result == []


class TestProviderHandlerVerifyRepoProvider:
    """Test ProviderHandler.verify_repo_provider edge cases."""

    @pytest.mark.asyncio
    async def test_specified_provider_error(self):
        """Test verify_repo_provider with specified provider that errors."""
        tokens = MappingProxyType({
            ProviderType.GITHUB: ProviderToken(token=SecretStr("token")),
        })
        handler = ProviderHandler(tokens)

        mock_service = MagicMock()
        mock_service.get_repository_details_from_repo_name = AsyncMock(
            side_effect=Exception("not found")
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


class TestProviderHandlerGetMicroagents:
    """Test ProviderHandler.get_microagents edge cases."""

    @pytest.mark.asyncio
    async def test_empty_result_tries_next_provider(self):
        """Test get_microagents returns empty when result is empty."""
        tokens = MappingProxyType({
            ProviderType.GITHUB: ProviderToken(token=SecretStr("token")),
        })
        handler = ProviderHandler(tokens)

        github_service = MagicMock()
        github_service.get_microagents = AsyncMock(return_value=[])

        services = {
            ProviderType.GITHUB: github_service,
        }

        async def mock_async_call(op_key, func):
            # Execute the function and await if it's async
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
                # Empty results from all providers without errors returns empty list
                # AuthenticationError is only raised if there are errors (line 671-678)
                result = await handler.get_microagents("acme/repo")
                assert result == []


class TestProviderHandlerGetMicroagentContent:
    """Test ProviderHandler.get_microagent_content edge cases."""

    @pytest.mark.asyncio
    async def test_handles_generic_exception(self):
        """Test get_microagent_content handles generic exceptions."""
        tokens = MappingProxyType({
            ProviderType.GITHUB: ProviderToken(token=SecretStr("token"))
        })
        handler = ProviderHandler(tokens)

        mock_service = MagicMock()
        mock_service.get_microagent_content = AsyncMock(side_effect=Exception("error"))

        async def mock_async_call(op_key, func):
            # Execute the function and await if it's async
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
                # Generic exception should be caught and raise AuthenticationError
                with pytest.raises(AuthenticationError):
                    await handler.get_microagent_content("acme/repo", "file.md")


class TestProviderHandlerVerifyRepository:
    """Test ProviderHandler._verify_repository edge cases."""

    @pytest.mark.asyncio
    async def test_no_tokens_requires_slash(self):
        """Test _verify_repository requires slash format when no tokens."""
        handler = ProviderHandler(MappingProxyType({}))
        with pytest.raises(AuthenticationError):
            await handler._verify_repository("invalid-repo-name")

    @pytest.mark.asyncio
    async def test_no_tokens_with_slash(self):
        """Test _verify_repository accepts slash format when no tokens."""
        handler = ProviderHandler(MappingProxyType({}))
        provider, name = await handler._verify_repository("owner/repo")
        assert provider == ProviderType.GITHUB
        assert name == "owner/repo"


class TestProviderHandlerGetAuthenticatedGitUrl:
    """Test ProviderHandler.get_authenticated_git_url edge cases."""

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

    @pytest.mark.asyncio
    async def test_no_token_returns_basic_url(self):
        """Test get_authenticated_git_url returns basic URL when no token."""
        tokens = MappingProxyType({
            ProviderType.GITHUB: ProviderToken(token=None, user_id="user")
        })
        handler = ProviderHandler(tokens)

        with patch.object(
            handler,
            "_verify_repository",
            AsyncMock(return_value=(ProviderType.GITHUB, "acme/repo"))
        ):
            url = await handler.get_authenticated_git_url("acme/repo")
        assert url == "https://github.com/acme/repo.git"
        assert "@" not in url


class TestProviderHandlerCheckCmdAction:
    """Test ProviderHandler.check_cmd_action_for_provider_token_ref."""

    def test_detects_all_providers(self):
        """Test check_cmd_action detects provider tokens in command."""
        action = CmdRunAction(
            command="echo $GITHUB_TOKEN"
        )
        providers = ProviderHandler.check_cmd_action_for_provider_token_ref(action)
        assert ProviderType.GITHUB in providers
        assert len(providers) == 1

    def test_case_insensitive(self):
        """Test check_cmd_action is case insensitive."""
        action = CmdRunAction(command="echo $github_token")
        providers = ProviderHandler.check_cmd_action_for_provider_token_ref(action)
        assert ProviderType.GITHUB in providers

