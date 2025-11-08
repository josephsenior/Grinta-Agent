"""Provider integration helpers aggregating GitHub, GitLab, and Bitbucket services."""

from __future__ import annotations

import os
from types import MappingProxyType
from typing import TYPE_CHECKING, Annotated, Any, Literal, cast, overload

import httpx
from pydantic import BaseModel, ConfigDict, Field, SecretStr, WithJsonSchema

from forge.core.logger import forge_logger as logger
from forge.events.action.commands import CmdRunAction
from forge.integrations.bitbucket.bitbucket_service import BitBucketServiceImpl
from forge.integrations.github.github_service import GithubServiceImpl
from forge.integrations.gitlab.gitlab_service import GitLabServiceImpl
from forge.integrations.service_types import (
    AuthenticationError,
    Branch,
    GitService,
    InstallationsService,
    MicroagentParseError,
    PaginatedBranchesResponse,
    ProviderType,
    Repository,
    ResourceNotFoundError,
    SuggestedTask,
    TokenResponse,
    User,
)

if TYPE_CHECKING:
    from collections.abc import Coroutine

    from forge.events.action.action import Action
    from forge.events.stream import EventStream
    from forge.microagent.types import MicroagentContentResponse, MicroagentResponse
    from forge.server.types import AppMode


class ProviderToken(BaseModel):
    """Typed container for provider access tokens plus optional metadata."""
    token: SecretStr | None = Field(default=None)
    user_id: str | None = Field(default=None)
    host: str | None = Field(default=None)
    model_config = ConfigDict(frozen=True, validate_assignment=True)

    @classmethod
    def from_value(cls, token_value: ProviderToken | dict[str, str]) -> ProviderToken:
        """Factory method to create a ProviderToken from various input types."""
        if isinstance(token_value, cls):
            return token_value
        if isinstance(token_value, dict):
            token_str = token_value.get("token", "")
            if token_str is None:
                token_str = ""
            user_id = token_value.get("user_id")
            host = token_value.get("host")
            return cls(token=SecretStr(token_str), user_id=user_id, host=host)
        msg = "Unsupported Provider token type"
        raise ValueError(msg)


class CustomSecret(BaseModel):
    """Represents a user-defined secret (value plus description)."""
    secret: SecretStr = Field(default_factory=lambda: SecretStr(""))
    description: str = Field(default="")
    model_config = ConfigDict(frozen=True, validate_assignment=True)

    @classmethod
    def from_value(cls, secret_value: CustomSecret | dict[str, str]) -> CustomSecret:
        """Factory method to create a ProviderToken from various input types."""
        if isinstance(secret_value, CustomSecret):
            return secret_value
        if isinstance(secret_value, dict):
            secret = secret_value.get("secret", "")
            description = secret_value.get("description", "")
            return cls(secret=SecretStr(secret), description=description)
        msg = "Unsupport Provider token type"
        raise ValueError(msg)


PROVIDER_TOKEN_TYPE = MappingProxyType[ProviderType, ProviderToken]
CUSTOM_SECRETS_TYPE = MappingProxyType[str, CustomSecret]
PROVIDER_TOKEN_FIELD_TYPE = dict[ProviderType, ProviderToken]
CUSTOM_SECRETS_FIELD_TYPE = dict[str, CustomSecret]
PROVIDER_TOKEN_TYPE_WITH_JSON_SCHEMA = Annotated[
    PROVIDER_TOKEN_FIELD_TYPE,
    WithJsonSchema({"type": "object", "additionalProperties": {"type": "string"}}),
]
CUSTOM_SECRETS_TYPE_WITH_JSON_SCHEMA = Annotated[
    CUSTOM_SECRETS_FIELD_TYPE,
    WithJsonSchema({"type": "object", "additionalProperties": {"type": "string"}}),
]


class ProviderHandler:
    """Facade around provider-specific services (GitHub, GitLab, Bitbucket)."""
    PROVIDER_DOMAINS: dict[ProviderType, str] = {
        ProviderType.GITHUB: "github.com",
        ProviderType.GITLAB: "gitlab.com",
        ProviderType.BITBUCKET: "bitbucket.org",
    }

    def __init__(
        self,
        provider_tokens: PROVIDER_TOKEN_TYPE,
        external_auth_id: str | None = None,
        external_auth_token: SecretStr | None = None,
        external_token_manager: bool = False,
        session_api_key: str | None = None,
        sid: str | None = None,
    ) -> None:
        """Initialize the handler with provider tokens and optional auth context."""
        if not isinstance(provider_tokens, MappingProxyType):
            msg = f"provider_tokens must be a MappingProxyType, got {type(provider_tokens).__name__}"
            raise TypeError(msg)
        self.service_class_map: dict[ProviderType, type[GitService]] = {
            ProviderType.GITHUB: GithubServiceImpl,
            ProviderType.GITLAB: GitLabServiceImpl,
            ProviderType.BITBUCKET: BitBucketServiceImpl,
        }
        self.external_auth_id = external_auth_id
        self.external_auth_token = external_auth_token
        self.external_token_manager = external_token_manager
        self.session_api_key = session_api_key
        self.sid = sid
        self._provider_tokens = provider_tokens
        WEB_HOST = os.getenv("WEB_HOST", "").strip()
        self.REFRESH_TOKEN_URL = f"https://{WEB_HOST}/api/refresh-tokens" if WEB_HOST else None

    @property
    def provider_tokens(self) -> PROVIDER_TOKEN_TYPE:
        """Read-only access to provider tokens."""
        return self._provider_tokens

    def _get_service(self, provider: ProviderType) -> GitService:
        """Helper method to instantiate a service for a given provider."""
        token = self.provider_tokens[provider]
        service_class = self.service_class_map[provider]
        return service_class(
            user_id=token.user_id,
            external_auth_id=self.external_auth_id,
            external_auth_token=self.external_auth_token,
            token=token.token,
            external_token_manager=self.external_token_manager,
            base_domain=token.host,
        )

    async def get_user(self) -> User:
        """Get user information from the first available provider."""
        for provider in self.provider_tokens:
            try:
                service = self._get_service(provider)
                return await service.get_user()
            except Exception:
                continue
        msg = "Need valid provider token"
        raise AuthenticationError(msg)

    async def _get_latest_provider_token(self, provider: ProviderType) -> SecretStr | None:
        """Get latest token from service."""
        try:
            async with httpx.AsyncClient() as client:
                resp = await client.get(
                    self.REFRESH_TOKEN_URL,
                    headers={"X-Session-API-Key": self.session_api_key},
                    params={"provider": provider.value, "sid": self.sid},
                )
            resp.raise_for_status()
            data = TokenResponse.model_validate_json(resp.text)
            return SecretStr(data.token)
        except Exception as e:
            logger.warning("Failed to fetch latest token for provider %s: %s", provider, e)
        return None

    async def get_github_installations(self) -> list[str]:
        """Get list of GitHub App installations accessible to user.
        
        Returns:
            List of installation IDs, empty list if error

        """
        service = cast("InstallationsService", self._get_service(ProviderType.GITHUB))
        try:
            return await service.get_installations()
        except Exception as e:
            logger.warning("Failed to get github installations %s", e)
        return []

    async def get_bitbucket_workspaces(self) -> list[str]:
        """Get list of Bitbucket workspaces accessible to user.
        
        Returns:
            List of workspace IDs, empty list if error

        """
        service = cast("InstallationsService", self._get_service(ProviderType.BITBUCKET))
        try:
            return await service.get_installations()
        except Exception as e:
            logger.warning("Failed to get bitbucket workspaces %s", e)
        return []

    async def get_repositories(
        self,
        sort: str,
        app_mode: AppMode,
        selected_provider: ProviderType | None,
        page: int | None,
        per_page: int | None,
        installation_id: str | None,
    ) -> list[Repository]:
        """Get repositories from providers."""
        "\n        Get repositories from providers\n        "
        if selected_provider:
            if not page or not per_page:
                msg = "Failed to provider params for paginating repos"
                raise ValueError(msg)
            service = self._get_service(selected_provider)
            return await service.get_paginated_repos(page, per_page, sort, installation_id)
        all_repos: list[Repository] = []
        for provider in self.provider_tokens:
            try:
                service = self._get_service(provider)
                service_repos = await service.get_all_repositories(sort, app_mode)
                all_repos.extend(service_repos)
            except Exception as e:
                logger.warning("Error fetching repos from %s: %s", provider, e)
        return all_repos

    async def get_suggested_tasks(self) -> list[SuggestedTask]:
        """Get suggested tasks from providers."""
        tasks: list[SuggestedTask] = []
        for provider in self.provider_tokens:
            try:
                service = self._get_service(provider)
                service_repos = await service.get_suggested_tasks()
                tasks.extend(service_repos)
            except Exception as e:
                logger.warning("Error fetching repos from %s: %s", provider, e)
        return tasks

    async def search_branches(
        self,
        selected_provider: ProviderType | None,
        repository: str,
        query: str,
        per_page: int = 30,
    ) -> list[Branch]:
        """Search for branches within a repository using the appropriate provider service."""
        if selected_provider:
            service = self._get_service(selected_provider)
            try:
                return await service.search_branches(repository, query, per_page)
            except Exception as e:
                logger.warning("Error searching branches from selected provider %s: %s", selected_provider, e)
                return []
        try:
            repo_details = await self.verify_repo_provider(repository)
            service = self._get_service(repo_details.git_provider)
            return await service.search_branches(repository, query, per_page)
        except Exception as e:
            logger.warning("Error searching branches for %s: %s", repository, e)
            return []

    async def search_repositories(
        self,
        selected_provider: ProviderType | None,
        query: str,
        per_page: int,
        sort: str,
        order: str,
    ) -> list[Repository]:
        """Search repositories across providers.
        
        Args:
            selected_provider: Specific provider to search, or None for all
            query: Search query string or repository URL
            per_page: Results per page
            sort: Sort field (stars, updated, etc.)
            order: Sort order (asc, desc)
            
        Returns:
            List of matching repositories

        """
        if selected_provider:
            service = self._get_service(selected_provider)
            public = self._is_repository_url(query, selected_provider)
            user_repos = await service.search_repositories(query, per_page, sort, order, public)
            return self._deduplicate_repositories(user_repos)
        all_repos: list[Repository] = []
        for provider in self.provider_tokens:
            try:
                service = self._get_service(provider)
                public = self._is_repository_url(query, provider)
                service_repos = await service.search_repositories(query, per_page, sort, order, public)
                all_repos.extend(service_repos)
            except Exception as e:
                logger.warning("Error searching repos from %s: %s", provider, e)
                continue
        return all_repos

    def _is_repository_url(self, query: str, provider: ProviderType) -> bool:
        """Check if the query is a repository URL."""
        custom_host = self.provider_tokens[provider].host
        custom_host_exists = custom_host and custom_host in query
        default_host_exists = self.PROVIDER_DOMAINS[provider] in query
        return query.startswith(("http://", "https://")) and (custom_host_exists or default_host_exists)

    def _deduplicate_repositories(self, repos: list[Repository]) -> list[Repository]:
        """Remove duplicate repositories based on full_name."""
        seen = set()
        unique_repos = []
        for repo in repos:
            if repo.full_name not in seen:
                seen.add(repo.full_name)
                unique_repos.append(repo)
        return unique_repos

    async def set_event_stream_secrets(
        self,
        event_stream: EventStream,
        env_vars: dict[ProviderType, SecretStr] | None = None,
    ) -> None:
        """This ensures that the latest provider tokens are masked from the event stream.

        It is called when the provider tokens are first initialized in the runtime or when tokens are re-exported with the latest working ones.

        Args:
            event_stream: Agent session's event stream
            env_vars: Dict of providers and their tokens that require updating

        """
        if env_vars:
            exposed_env_vars = self.expose_env_vars(env_vars)
        else:
            exposed_env_vars = await self.get_env_vars(expose_secrets=True)
        event_stream.set_secrets(exposed_env_vars)

    def expose_env_vars(self, env_secrets: dict[ProviderType, SecretStr]) -> dict[str, str]:
        """Return string values instead of typed values for environment secrets.

        Called just before exporting secrets to runtime, or setting secrets in the event stream.
        """
        exposed_envs = {}
        for provider, token in env_secrets.items():
            env_key = ProviderHandler.get_provider_env_key(provider)
            exposed_envs[env_key] = token.get_secret_value()
        return exposed_envs

    @overload
    def get_env_vars(
        self,
        expose_secrets: Literal[True],
        providers: list[ProviderType] | None = ...,
        get_latest: bool = False,
    ) -> Coroutine[Any, Any, dict[str, str]]:
        ...

    @overload
    def get_env_vars(
        self,
        expose_secrets: Literal[False],
        providers: list[ProviderType] | None = ...,
        get_latest: bool = False,
    ) -> Coroutine[Any, Any, dict[ProviderType, SecretStr]]:
        ...

    def _get_provider_list(self, providers: list[ProviderType] | None) -> list[ProviderType]:
        """Get the list of providers to process."""
        return providers if providers is not None else list(ProviderType)

    async def _get_provider_token(self, provider: ProviderType, get_latest: bool) -> SecretStr | None:
        """Get token for a specific provider."""
        if provider not in self.provider_tokens:
            return None

        token = self.provider_tokens[provider].token if self.provider_tokens else SecretStr("")

        if get_latest and self.REFRESH_TOKEN_URL and self.sid:
            token = await self._get_latest_provider_token(provider)

        return token or None

    async def _collect_provider_tokens(
        self,
        provider_list: list[ProviderType],
        get_latest: bool,
    ) -> dict[ProviderType, SecretStr]:
        """Collect tokens for all providers in the list."""
        env_vars: dict[ProviderType, SecretStr] = {}

        for provider in provider_list:
            token = await self._get_provider_token(provider, get_latest)
            if token:
                env_vars[provider] = token

        return env_vars

    async def get_env_vars(
        self,
        expose_secrets: bool = False,
        providers: list[ProviderType] | None = None,
        get_latest: bool = False,
    ) -> dict[ProviderType, SecretStr] | dict[str, str]:
        """Retrieves the provider tokens from ProviderHandler object.

        This is used when initializing/exporting new provider tokens in the runtime.

        Args:
            expose_secrets: Flag which returns strings instead of secrets
            providers: Return provider tokens for the list passed in, otherwise return all available providers
            get_latest: Get the latest working token for the providers if True, otherwise get the existing ones

        """
        if not self.provider_tokens:
            return {}

        provider_list = self._get_provider_list(providers)
        env_vars = await self._collect_provider_tokens(provider_list, get_latest)

        return self.expose_env_vars(env_vars) if expose_secrets else env_vars

    @classmethod
    def check_cmd_action_for_provider_token_ref(cls, event: Action) -> list[ProviderType]:
        """Detect if agent run action is using a provider token (e.g $GITHUB_TOKEN).

        Returns a list of providers which are called by the agent.
        """
        if not isinstance(event, CmdRunAction):
            return []
        return [
            provider
            for provider in ProviderType
            if ProviderHandler.get_provider_env_key(provider) in event.command.lower()
        ]

    @classmethod
    def get_provider_env_key(cls, provider: ProviderType) -> str:
        """Map ProviderType value to the environment variable name in the runtime."""
        return f"{provider.value}_token".lower()

    async def verify_repo_provider(self, repository: str, specified_provider: ProviderType | None = None) -> Repository:
        """Verify repository provider and get repository details.
        
        Args:
            repository: Repository name or URL
            specified_provider: Optional specific provider to check
            
        Returns:
            Repository details with verified provider
            
        Raises:
            ValueError: If repository not found in any provider

        """
        errors = []
        if specified_provider:
            try:
                service = self._get_service(specified_provider)
                return await service.get_repository_details_from_repo_name(repository)
            except Exception as e:
                errors.append(f"{specified_provider.value}: {e!s}")
        for provider in self.provider_tokens:
            try:
                service = self._get_service(provider)
                return await service.get_repository_details_from_repo_name(repository)
            except Exception as e:
                errors.append(f"{provider.value}: {e!s}")
        logger.error(
            "Failed to access repository %s with all available providers. Errors: %s",
            repository,
            "; ".join(errors),
        )
        msg = f"Unable to access repo {repository}"
        raise AuthenticationError(msg)

    async def get_branches(
        self,
        repository: str,
        specified_provider: ProviderType | None = None,
        page: int = 1,
        per_page: int = 30,
    ) -> PaginatedBranchesResponse:
        """Get branches for a repository.

        Args:
            repository: The repository name
            specified_provider: Optional provider type to use
            page: Page number for pagination (default: 1)
            per_page: Number of branches per page (default: 30)

        Returns:
            A paginated response with branches for the repository

        """
        if specified_provider:
            try:
                service = self._get_service(specified_provider)
                return await service.get_paginated_branches(repository, page, per_page)
            except Exception as e:
                logger.warning("Error fetching branches from %s: %s", specified_provider, e)
        for provider in self.provider_tokens:
            try:
                service = self._get_service(provider)
                return await service.get_paginated_branches(repository, page, per_page)
            except Exception as e:
                logger.warning("Error fetching branches from %s: %s", provider, e)
        return PaginatedBranchesResponse(
            branches=[],
            has_next_page=False,
            current_page=page,
            per_page=per_page,
            total_count=0,
        )

    async def get_microagents(self, repository: str) -> list[MicroagentResponse]:
        """Get microagents from a repository using the appropriate service.

        Args:
            repository: Repository name in the format 'owner/repo'

        Returns:
            List of microagents found in the repository

        Raises:
            AuthenticationError: If authentication fails

        """
        errors = []
        for provider in self.provider_tokens:
            try:
                service = self._get_service(provider)
                result = await service.get_microagents(repository)
                if result:
                    return result
                logger.debug("No microagents found on %s for %s, trying other providers", provider, repository)
            except Exception as e:
                errors.append(f"{provider.value}: {e!s}")
                logger.warning("Error fetching microagents from %s for %s: %s", provider, repository, e)
        if errors:
            logger.error(
                "Failed to fetch microagents for %s with all available providers. Errors: %s",
                repository,
                "; ".join(errors),
            )
            msg = f"Unable to fetch microagents for {repository}"
            raise AuthenticationError(msg)
        return []

    async def get_microagent_content(self, repository: str, file_path: str) -> MicroagentContentResponse:
        """Get content of a specific microagent file from a repository.

        Args:
            repository: Repository name in the format 'owner/repo'
            file_path: Path to the microagent file within the repository

        Returns:
            MicroagentContentResponse with parsed content and triggers

        Raises:
            AuthenticationError: If authentication fails

        """
        errors = []
        for provider in self.provider_tokens:
            try:
                service = self._get_service(provider)
                result = await service.get_microagent_content(repository, file_path)
                if result:
                    return result
                logger.debug(
                    "No content found on %s for %s/%s, trying other providers",
                    provider,
                    repository,
                    file_path,
                )
            except ResourceNotFoundError:
                logger.debug("File not found on %s for %s/%s, trying other providers", provider, repository, file_path)
                continue
            except MicroagentParseError as e:
                errors.append(f"{provider.value}: {e!s}")
                logger.warning("Error parsing microagent content from %s for %s: %s", provider, repository, e)
            except Exception as e:
                errors.append(f"{provider.value}: {e!s}")
                logger.warning("Error fetching microagent content from %s for %s: %s", provider, repository, e)
        if errors:
            logger.error(
                "Failed to fetch microagent content for %s with all available providers. Errors: %s",
                repository,
                "; ".join(errors),
            )
        msg = f"Microagent file {file_path} not found in {repository}"
        raise AuthenticationError(msg)

    async def _verify_repository(self, repo_name: str) -> tuple[ProviderType, str]:
        """Verify repository and return provider and full name."""
        try:
            repository = await self.verify_repo_provider(repo_name)
            return repository.git_provider, repository.full_name
        except AuthenticationError as e:
            msg = "Git provider authentication issue when getting remote URL"
            raise AuthenticationError(msg) from e

    def _get_authenticated_domain(self, provider: ProviderType) -> str:
        """Get the authenticated domain for the provider."""
        domain = self.PROVIDER_DOMAINS[provider]
        if self.provider_tokens and provider in self.provider_tokens:
            domain = self.provider_tokens[provider].host or domain
        return domain

    def _build_authenticated_url(self, provider: ProviderType, domain: str, repo_name: str, token_value: str) -> str:
        """Build authenticated URL based on provider type."""
        if provider == ProviderType.GITLAB:
            return f"https://oauth2:{token_value}@{domain}/{repo_name}.git"
        if (provider == ProviderType.BITBUCKET and ":" in token_value) or provider not in [
            ProviderType.GITLAB,
            ProviderType.BITBUCKET,
        ]:
            return f"https://{token_value}@{domain}/{repo_name}.git"
        return f"https://x-token-auth:{token_value}@{domain}/{repo_name}.git"

    def _get_remote_url(self, provider: ProviderType, domain: str, repo_name: str) -> str:
        """Get remote URL with or without authentication."""
        if not (self.provider_tokens and provider in self.provider_tokens):
            return f"https://{domain}/{repo_name}.git"

        git_token = self.provider_tokens[provider].token
        if not git_token:
            return f"https://{domain}/{repo_name}.git"

        token_value = git_token.get_secret_value()
        return self._build_authenticated_url(provider, domain, repo_name, token_value)

    async def get_authenticated_git_url(self, repo_name: str) -> str:
        """Get an authenticated git URL for a repository.

        Args:
            repo_name: Repository name (owner/repo)

        Returns:
            Authenticated git URL if credentials are available, otherwise regular HTTPS URL

        """
        provider, full_repo_name = await self._verify_repository(repo_name)
        domain = self._get_authenticated_domain(provider)
        return self._get_remote_url(provider, domain, full_repo_name)

    async def is_pr_open(self, repository: str, pr_number: int, git_provider: ProviderType) -> bool:
        """Check if a PR is still active (not closed/merged).

        This method checks the PR status using the provider's service method.

        Args:
            repository: Repository name in format 'owner/repo'
            pr_number: The PR number to check
            git_provider: The Git provider type for this repository

        Returns:
            True if PR is active (open), False if closed/merged, True if can't determine

        """
        try:
            service = self._get_service(git_provider)
            return await service.is_pr_open(repository, pr_number)
        except Exception as e:
            logger.warning(
                "Could not determine PR status for %s#%s: %s. Including conversation to be safe.",
                repository,
                pr_number,
                e,
            )
            return True
