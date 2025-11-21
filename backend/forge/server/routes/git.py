"""Routes for interacting with Git providers and repository metadata."""

from __future__ import annotations

from types import MappingProxyType
from typing import Annotated, Any, cast

from fastapi import APIRouter, Depends, Query, status, FastAPI, Request
from fastapi.responses import JSONResponse

from forge.core.logger import forge_logger as logger
from forge.integrations.provider import (
    PROVIDER_TOKEN_TYPE,
    ProviderHandler,
    ProviderToken,
)
from forge.integrations.service_types import (
    AuthenticationError,
    Branch,
    PaginatedBranchesResponse,
    ProviderType,
    Repository,
    SuggestedTask,
    UnknownException,
    User,
)
from forge.microagent.types import MicroagentContentResponse, MicroagentResponse
from forge.server.dependencies import get_dependencies
from forge.server.shared import server_config
from forge.server.user_auth import (
    get_access_token,
    get_provider_tokens,
    get_user_id,
)

from pydantic import SecretStr

app = APIRouter(prefix="/api/user", dependencies=get_dependencies())

# Backward compatibility: some modules import `router`
router = app


def _normalize_provider_tokens(
    tokens: PROVIDER_TOKEN_TYPE | None,
) -> MappingProxyType[ProviderType, ProviderToken]:
    if isinstance(tokens, MappingProxyType):
        return tokens
    return MappingProxyType(dict(tokens or {}))


@app.get("/installations", response_model=list[str])
async def get_user_installations(
    provider: ProviderType,
    provider_tokens: Annotated[
        PROVIDER_TOKEN_TYPE | None, Depends(get_provider_tokens)
    ],
    access_token: Annotated[SecretStr | None, Depends(get_access_token)],
    user_id: Annotated[str | None, Depends(get_user_id)],
):
    """Get user's installations/workspaces for the specified provider.

    Args:
        provider: Git provider type (GitHub, Bitbucket, etc.)
        provider_tokens: Provider authentication tokens
        access_token: External auth token
        user_id: User identifier

    Returns:
        List of installation/workspace names

    Raises:
        AuthenticationError: If provider tokens not available

    """
    if provider_tokens:
        client = ProviderHandler(
            provider_tokens=_normalize_provider_tokens(provider_tokens),
            external_auth_token=access_token,
            external_auth_id=user_id,
        )
        if provider == ProviderType.GITHUB:
            return await client.get_github_installations()
        if provider == ProviderType.BITBUCKET:
            return await client.get_bitbucket_workspaces()
        return JSONResponse(
            content=f"Provider {provider} doesn't support installations",
            status_code=status.HTTP_400_BAD_REQUEST,
        )
    msg = "Git provider token required. (such as GitHub)."
    raise AuthenticationError(msg)


@app.get("/repositories", response_model=list[Repository])
async def get_user_repositories(
    sort: str = "pushed",
    selected_provider: ProviderType | None = None,
    page: int | None = None,
    per_page: int | None = None,
    installation_id: str | None = None,
    provider_tokens: PROVIDER_TOKEN_TYPE | None = Depends(get_provider_tokens),
    access_token: SecretStr | None = Depends(get_access_token),
    user_id: str | None = Depends(get_user_id),
) -> list[Repository] | JSONResponse:
    """Get user's repositories from git provider.

    Args:
        sort: Sort order (pushed, created, updated, full_name)
        selected_provider: Specific provider to query
        page: Page number for pagination
        per_page: Items per page
        installation_id: Filter by installation ID
        provider_tokens: Provider authentication tokens
        access_token: External auth token
        user_id: User identifier

    Returns:
        List of Repository objects or error response

    Raises:
        AuthenticationError: If provider tokens not available

    """
    if provider_tokens:
        client = ProviderHandler(
            provider_tokens=_normalize_provider_tokens(provider_tokens),
            external_auth_token=access_token,
            external_auth_id=user_id,
        )
        try:
            return await client.get_repositories(
                sort,
                server_config.app_mode,
                selected_provider,
                page,
                per_page,
                installation_id,
            )
        except UnknownException as e:
            return JSONResponse(
                content=str(e),
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )
    # nosec B628 - Not logging credentials, just auth failure
    logger.info("Returning 401 Unauthorized - Git provider token required")
    msg = "Git provider token required. (such as GitHub)."
    raise AuthenticationError(msg)


@app.get("/info", response_model=User)
async def get_user(
    provider_tokens: Annotated[
        PROVIDER_TOKEN_TYPE | None, Depends(get_provider_tokens)
    ],
    access_token: Annotated[SecretStr | None, Depends(get_access_token)],
    user_id: Annotated[str | None, Depends(get_user_id)],
) -> User | JSONResponse:
    """Get authenticated user information from git provider.

    Args:
        provider_tokens: Provider authentication tokens
        access_token: External auth token
        user_id: User identifier

    Returns:
        User object or error response

    Raises:
        AuthenticationError: If provider tokens not available

    """
    if provider_tokens:
        client = ProviderHandler(
            provider_tokens=_normalize_provider_tokens(provider_tokens),
            external_auth_token=access_token,
        )
        try:
            user: User = await client.get_user()
            return user
        except UnknownException as e:
            return JSONResponse(
                content=str(e),
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )
    # nosec B628 - Not logging credentials, just auth failure
    logger.info("Returning 401 Unauthorized - Git provider token required")
    msg = "Git provider token required. (such as GitHub)."
    raise AuthenticationError(msg)


@app.get("/search/repositories", response_model=list[Repository])
async def search_repositories(
    query: str,
    per_page: int = 5,
    sort: str = "stars",
    order: str = "desc",
    selected_provider: ProviderType | None = None,
    provider_tokens: PROVIDER_TOKEN_TYPE | None = Depends(get_provider_tokens),
    access_token: SecretStr | None = Depends(get_access_token),
    user_id: str | None = Depends(get_user_id),
) -> list[Repository] | JSONResponse:
    """Search repositories across git providers.

    Args:
        query: Search query string
        per_page: Number of results per page
        sort: Sort order (stars, forks, updated)
        order: Order direction (asc, desc)
        selected_provider: Specific provider to search
        provider_tokens: Provider authentication tokens
        access_token: External auth token
        user_id: User identifier

    Returns:
        List of matching Repository objects or error response

    Raises:
        AuthenticationError: If provider tokens not available

    """
    if provider_tokens:
        client = ProviderHandler(
            provider_tokens=_normalize_provider_tokens(provider_tokens),
            external_auth_token=access_token,
            external_auth_id=user_id,
        )
        try:
            repos: list[Repository] = await client.search_repositories(
                selected_provider,
                query,
                per_page,
                sort,
                order,
            )
            return repos
        except UnknownException as e:
            return JSONResponse(
                content=str(e),
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )
    logger.info("Returning 401 Unauthorized - Git provider token required")
    msg = "Git provider token required."
    raise AuthenticationError(msg)


@app.get("/search/branches", response_model=list[Branch])
async def search_branches(
    repository: str,
    query: str,
    per_page: int = 30,
    selected_provider: ProviderType | None = None,
    provider_tokens: PROVIDER_TOKEN_TYPE | None = Depends(get_provider_tokens),
    access_token: SecretStr | None = Depends(get_access_token),
    user_id: str | None = Depends(get_user_id),
) -> list[Branch] | JSONResponse:
    """Search branches in a repository.

    Args:
        repository: Repository name
        query: Branch search query
        per_page: Number of results per page
        selected_provider: Specific provider to use
        provider_tokens: Provider authentication tokens
        access_token: External auth token
        user_id: User identifier

    Returns:
        List of matching Branch objects or error response

    Raises:
        AuthenticationError: If provider tokens not available

    """
    if provider_tokens:
        client = ProviderHandler(
            provider_tokens=_normalize_provider_tokens(provider_tokens),
            external_auth_token=access_token,
            external_auth_id=user_id,
        )
        try:
            branches: list[Branch] = await client.search_branches(
                selected_provider,
                repository,
                query,
                per_page,
            )
            return branches
        except AuthenticationError as e:
            return JSONResponse(
                content=str(e),
                status_code=status.HTTP_401_UNAUTHORIZED,
            )
        except UnknownException as e:
            return JSONResponse(
                content=str(e),
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )
    logger.info("Returning 401 Unauthorized - Git provider token required")
    return JSONResponse(
        content="Git provider token required.",
        status_code=status.HTTP_401_UNAUTHORIZED,
    )


@app.get("/suggested-tasks", response_model=list[SuggestedTask])
async def get_suggested_tasks(
    provider_tokens: Annotated[
        PROVIDER_TOKEN_TYPE | None, Depends(get_provider_tokens)
    ],
    access_token: Annotated[SecretStr | None, Depends(get_access_token)],
    user_id: Annotated[str | None, Depends(get_user_id)],
) -> list[SuggestedTask] | JSONResponse:
    """Get suggested tasks for the authenticated user across their most recently pushed repositories.

    Returns:
    - PRs owned by the user
    - Issues assigned to the user.

    """
    if provider_tokens:
        client = ProviderHandler(
            provider_tokens=_normalize_provider_tokens(provider_tokens),
            external_auth_token=access_token,
        )
        try:
            tasks: list[SuggestedTask] = await client.get_suggested_tasks()
            return tasks
        except UnknownException as e:
            return JSONResponse(
                content=str(e),
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )
    logger.info("Returning 401 Unauthorized - No providers set")
    msg = "No providers set."
    raise AuthenticationError(msg)


@app.get("/repository/branches", response_model=PaginatedBranchesResponse)
async def get_repository_branches(
    repository: str,
    page: int = 1,
    per_page: int = 30,
    provider_tokens: PROVIDER_TOKEN_TYPE | None = Depends(get_provider_tokens),
    access_token: SecretStr | None = Depends(get_access_token),
    user_id: str | None = Depends(get_user_id),
) -> PaginatedBranchesResponse | JSONResponse:
    """Get branches for a repository.

    Args:
        repository: The repository name in the format 'owner/repo'
        page: Page number for pagination (default: 1)
        per_page: Number of branches per page (default: 30)
        provider_tokens: Provider tokens for authentication
        access_token: Access token for external authentication
        user_id: User ID for authentication

    Returns:
        A paginated response with branches for the repository

    """
    if provider_tokens:
        client = ProviderHandler(
            provider_tokens=_normalize_provider_tokens(provider_tokens),
            external_auth_token=access_token,
        )
        try:
            branches_response: PaginatedBranchesResponse = await client.get_branches(
                repository,
                page=page,
                per_page=per_page,
            )
            return branches_response
        except UnknownException as e:
            return JSONResponse(
                content=str(e),
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )
    # nosec B628 - Not logging credentials, just auth failure
    logger.info("Returning 401 Unauthorized - Git provider token required")
    msg = "Git provider token required. (such as GitHub)."
    raise AuthenticationError(msg)


def _extract_repo_name(repository_name: str) -> str:
    """Extract the actual repository name from the full repository path.

    Args:
        repository_name: Repository name in format 'owner/repo' or 'domain/owner/repo'

    Returns:
        The actual repository name (last part after the last '/')

    """
    return repository_name.split("/")[-1]


@app.get(
    "/repository/{repository_name:path}/microagents",
    response_model=list[MicroagentResponse],
)
async def get_repository_microagents(
    repository_name: str,
    provider_tokens: Annotated[
        PROVIDER_TOKEN_TYPE | None, Depends(get_provider_tokens)
    ] = None,
    access_token: Annotated[SecretStr | None, Depends(get_access_token)] = None,
    user_id: Annotated[str | None, Depends(get_user_id)] = None,
) -> list[MicroagentResponse] | JSONResponse:
    """Scan the microagents directory of a repository and return the list of microagents.

    The microagents directory location depends on the git provider and actual repository name:
    - If git provider is not GitLab and actual repository name is ".Forge": scans "microagents" folder
    - If git provider is GitLab and actual repository name is "Forge-config": scans "microagents" folder
    - Otherwise: scans ".Forge/microagents" folder

    Note: This API returns microagent metadata without content for performance.
    Use the separate content API to fetch individual microagent content.

    Args:
        repository_name: Repository name in the format 'owner/repo' or 'domain/owner/repo'
        provider_tokens: Provider tokens for authentication
        access_token: Access token for external authentication
        user_id: User ID for authentication

    Returns:
        List of microagents found in the repository's microagents directory (without content)

    """
    try:
        provider_handler = ProviderHandler(
            provider_tokens=_normalize_provider_tokens(provider_tokens),
            external_auth_token=access_token,
            external_auth_id=user_id,
        )
        microagents = await provider_handler.get_microagents(repository_name)
        logger.info("Found %s microagents in %s", len(microagents), repository_name)
        return microagents
    except AuthenticationError:
        raise
    except RuntimeError as e:
        return JSONResponse(
            content=str(e),
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )
    except Exception as e:
        logger.error(
            "Error scanning repository %s: %s",
            repository_name,
            str(e),
            exc_info=True,
        )
        return JSONResponse(
            content=f"Error scanning repository: {e!s}",
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )


@app.get(
    "/repository/{repository_name:path}/microagents/content",
    response_model=MicroagentContentResponse,
)
async def get_repository_microagent_content(
    repository_name: str,
    file_path: Annotated[
        str, Query(description="Path to the microagent file within the repository")
    ],
    provider_tokens: Annotated[
        PROVIDER_TOKEN_TYPE | None, Depends(get_provider_tokens)
    ] = None,
    access_token: Annotated[SecretStr | None, Depends(get_access_token)] = None,
    user_id: Annotated[str | None, Depends(get_user_id)] = None,
) -> MicroagentContentResponse | JSONResponse:
    """Fetch the content of a specific microagent file from a repository.

    Args:
        repository_name: Repository name in the format 'owner/repo' or 'domain/owner/repo'
        file_path: Query parameter - Path to the microagent file within the repository
        provider_tokens: Provider tokens for authentication
        access_token: Access token for external authentication
        user_id: User ID for authentication

    Returns:
        Microagent file content and metadata

    Example:
        GET /api/user/repository/owner/repo/microagents/content?file_path=.Forge/microagents/my-agent.md

    """
    try:
        provider_handler = ProviderHandler(
            provider_tokens=_normalize_provider_tokens(provider_tokens),
            external_auth_token=access_token,
            external_auth_id=user_id,
        )
        response = await provider_handler.get_microagent_content(
            repository_name,
            file_path,
        )
        logger.info(
            "Retrieved content for microagent %s from %s",
            file_path,
            repository_name,
        )
        return response
    except AuthenticationError:
        raise
    except RuntimeError as e:
        return JSONResponse(
            content=str(e),
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )
    except Exception as e:
        logger.error(
            "Error fetching microagent content from %s/%s: %s",
            repository_name,
            file_path,
            str(e),
            exc_info=True,
        )
        return JSONResponse(
            content=f"Error fetching microagent content: {e!s}",
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )


@app.post("/git/summarize_repository")
async def summarize_repository(
    request: Request,
    summarize_request: Any,
) -> Any:
    """Generate summary of repository contents invoked via API request."""
    user_id = await get_user_id(request)
    logger.info(
        "Repository summarization requested by user_id=%s but this feature is not implemented.",
        user_id,
    )
    return JSONResponse(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        content={
            "error": "Repository summarization is not implemented on this server."
        },
    )
