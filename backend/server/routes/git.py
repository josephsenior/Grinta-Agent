"""Routes for interacting with Git providers and repository metadata."""

from __future__ import annotations

from types import MappingProxyType
from typing import Annotated, Any, cast

from fastapi import APIRouter, Depends, Query, status, FastAPI, Request, Path
from fastapi.responses import JSONResponse
from typing import Annotated

from backend.core.logger import forge_logger as logger
from backend.integrations.provider import (
    PROVIDER_TOKEN_TYPE,
    ProviderToken,
)
from backend.integrations.service_types import (
    AuthenticationError,
    Branch,
    PaginatedBranchesResponse,
    ProviderType,
    Repository,
    SuggestedTask,
    UnknownException,
    User,
)
from backend.instruction.types import PlaybookContentResponse, PlaybookResponse
from backend.server.dependencies import get_dependencies
from backend.server.shared import server_config
from backend.server.user_auth import (
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
        provider: Git provider type (GitHub)
        provider_tokens: Provider authentication tokens
        access_token: External auth token
        user_id: User identifier

    Returns:
        List of installation/workspace names

    Raises:
        AuthenticationError: If provider tokens not available

    """
    if provider_tokens:
        from backend.integrations.provider import ProviderHandler

        client = ProviderHandler(
            provider_tokens=_normalize_provider_tokens(provider_tokens),
            external_auth_token=access_token,
            external_auth_id=user_id,
        )
        if provider == ProviderType.GITHUB:
            return await client.get_github_installations()
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
        from backend.integrations.provider import ProviderHandler

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
        from backend.integrations.provider import ProviderHandler

        client = ProviderHandler(
            provider_tokens=_normalize_provider_tokens(provider_tokens),
            external_auth_token=access_token,
            external_auth_id=user_id,
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
    query: str = Query(..., min_length=1, description="Search query"),
    per_page: int = 5,
    sort: str = "stars",
    order: str = "desc",
    selected_provider: ProviderType | None = None,
    provider_tokens: PROVIDER_TOKEN_TYPE | None = Depends(get_provider_tokens),
    access_token: SecretStr | None = Depends(get_access_token),
    user_id: str | None = Depends(get_user_id),
) -> list[Repository] | JSONResponse:
    """Search repositories from GitHub.

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
        from backend.integrations.provider import ProviderHandler

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
    repository: str = Query(..., min_length=1, description="Repository name (owner/repo)"),
    query: str = Query(..., min_length=1, description="Branch search query"),
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
        from backend.integrations.provider import ProviderHandler

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
    """Get suggested tasks for the authenticated user from their GitHub repositories.

    Returns:
    - PRs owned by the user
    - Issues assigned to the user.

    """
    if provider_tokens:
        from backend.integrations.provider import ProviderHandler

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
    repository: str = Query(..., min_length=1, description="Repository name (owner/repo)"),
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
        from backend.integrations.provider import ProviderHandler

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
    "/repository/{repository_name:path}/playbooks",
    response_model=list[PlaybookResponse],
)
async def get_repository_playbooks(
    repository_name: Annotated[str, Path(..., min_length=1, description="Repository name (owner/repo)")],
    provider_tokens: Annotated[
        PROVIDER_TOKEN_TYPE | None, Depends(get_provider_tokens)
    ] = None,
    access_token: Annotated[SecretStr | None, Depends(get_access_token)] = None,
    user_id: Annotated[str | None, Depends(get_user_id)] = None,
) -> list[PlaybookResponse] | JSONResponse:
    """Scan the playbooks directory of a repository and return the list of playbooks.

    The playbooks directory location depends on the actual repository name:
    - If actual repository name is ".Forge": scans "playbooks" folder
    - Otherwise: scans ".Forge/playbooks" folder

    Note: This API returns playbook metadata without content for performance.
    Use the separate content API to fetch individual playbook content.

    Args:
        repository_name: Repository name in the format 'owner/repo' or 'domain/owner/repo'
        provider_tokens: Provider tokens for authentication
        access_token: Access token for external authentication
        user_id: User ID for authentication

    Returns:
        List of playbooks found in the repository's playbooks directory (without content)

    """
    try:
        from backend.integrations.provider import ProviderHandler

        provider_handler = ProviderHandler(
            provider_tokens=_normalize_provider_tokens(provider_tokens),
            external_auth_token=access_token,
            external_auth_id=user_id,
        )
        playbooks = await provider_handler.get_playbooks(repository_name)
        logger.info("Found %s playbooks in %s", len(playbooks), repository_name)
        return playbooks
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
    "/repository/{repository_name:path}/playbooks/content",
    response_model=PlaybookContentResponse,
)
async def get_repository_playbook_content(
    repository_name: Annotated[str, Path(..., min_length=1, description="Repository name (owner/repo)")],
    file_path: Annotated[
        str, Query(..., min_length=1, description="Path to the playbook file within the repository")
    ],
    provider_tokens: Annotated[
        PROVIDER_TOKEN_TYPE | None, Depends(get_provider_tokens)
    ] = None,
    access_token: Annotated[SecretStr | None, Depends(get_access_token)] = None,
    user_id: Annotated[str | None, Depends(get_user_id)] = None,
) -> PlaybookContentResponse | JSONResponse:
    """Fetch the content of a specific playbook file from a repository.

    Args:
        repository_name: Repository name in the format 'owner/repo' or 'domain/owner/repo'
        file_path: Query parameter - Path to the playbook file within the repository
        provider_tokens: Provider tokens for authentication
        access_token: Access token for external authentication
        user_id: User ID for authentication

    Returns:
        Playbook file content and metadata

    Example:
        GET /api/user/repository/owner/repo/playbooks/content?file_path=.Forge/playbooks/my-agent.md

    """
    try:
        from backend.integrations.provider import ProviderHandler

        provider_handler = ProviderHandler(
            provider_tokens=_normalize_provider_tokens(provider_tokens),
            external_auth_token=access_token,
            external_auth_id=user_id,
        )
        response = await provider_handler.get_playbook_content(
            repository_name,
            file_path,
        )
        logger.info(
            "Retrieved content for playbook %s from %s",
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
            "Error fetching playbook content from %s/%s: %s",
            repository_name,
            file_path,
            str(e),
            exc_info=True,
        )
        return JSONResponse(
            content=f"Error fetching playbook content: {e!s}",
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
