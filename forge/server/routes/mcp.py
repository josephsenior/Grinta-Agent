"""Model Context Protocol (MCP) routes and helpers for Forge server tooling."""

# Note: NOT using "from __future__ import annotations" to avoid Field resolution issues in fastmcp
# from __future__ import annotations

import os
import re
from typing import TYPE_CHECKING, Annotated

# Import Field early to ensure it's in the global namespace
from pydantic import Field

from fastmcp import FastMCP
from fastmcp.exceptions import ToolError
from fastmcp.server.dependencies import get_http_request

from forge.core.logger import forge_logger as logger
from forge.integrations.bitbucket.bitbucket_service import BitBucketServiceImpl
from forge.integrations.github.github_service import GithubServiceImpl
from forge.integrations.gitlab.gitlab_service import GitLabServiceImpl
from forge.integrations.provider import ProviderToken
from forge.integrations.service_types import GitService, ProviderType
from forge.server.dependencies import get_dependencies
from forge.server.types import AppMode
from forge.server.user_auth import (
    get_access_token,
    get_provider_tokens,
    get_user_id,
)

if TYPE_CHECKING:
    from forge.storage.data_models.conversation_metadata import ConversationMetadata

# Lazy import to avoid circular dependency issues during config loading
def get_conversation_store():
    """Return conversation store implementation lazily to avoid import cycles."""
    from forge.server.shared import ConversationStoreImpl
    return ConversationStoreImpl

def get_server_config():
    """Return server configuration module lazily to avoid circular import."""
    from forge.server.shared import server_config
    return server_config

def get_config():
    """Return Forge configuration without importing at module import time."""
    from forge.server.shared import config
    return config


server_config = get_server_config()

mcp_server = FastMCP("mcp", stateless_http=True, dependencies=None, mask_error_details=True)
HOST = f"https://{os.getenv('WEB_HOST', 'app.all-hands.dev').strip()}"
CONVERSATION_URL = HOST + "/conversations/{}"


async def get_conversation_link(
    service: GitService,
    conversation_id: str | None,
    body: str,
) -> str:
    """Append a Forge conversation link to PR/MR body in SaaS mode.

    Adds a followup link to the original Forge conversation URL in the PR/MR
    body, enabling reviewers to click through to continue refining the request.
    This only operates in SaaS app mode; other modes return the body unchanged.

    Args:
        service: The Git service instance (GitHub, GitLab, or Bitbucket)
            with authentication configured for retrieving user information.
        conversation_id: Unique identifier of the conversation that opened
            the pull/merge request.
        body: The current PR/MR body text to augment with the conversation link.

    Returns:
        str: The body text with appended conversation link (if in SaaS mode),
            or the original body unchanged (if in non-SaaS mode).

    Raises:
        ServiceError: Propagated from service.get_user() if user retrieval fails.

    """
    if server_config.app_mode != AppMode.SAAS or not conversation_id:
        return body
    user = await service.get_user()
    username = user.login
    conversation_url = CONVERSATION_URL.format(conversation_id)
    conversation_link = f"@{username} can click here to [continue refining the PR]({conversation_url})"
    body += f"\n\n{conversation_link}"
    return body


async def save_pr_metadata(user_id: str | None, conversation_id: str, tool_result: str) -> None:
    """Extract PR/MR number from tool output and update conversation metadata.

    Parses GitHub pull request or GitLab merge request numbers from tool
    result URLs using regex patterns, then persists the extracted PR number
    to the conversation's metadata store for tracking.

    Args:
        user_id: User identifier for accessing conversation store.
            Can be None for anonymous conversations.
        conversation_id: Unique conversation identifier to retrieve and update.
        tool_result: Tool output string expected to contain PR/MR URL
            (e.g., "https://github.com/owner/repo/pull/123").

    Returns:
        None

    Raises:
        Exception: Any exceptions from conversation_store operations are logged
            but not re-raised; warnings logged if PR number extraction fails.

    """
    conversation_store = await get_conversation_store().get_instance(get_config(), user_id)
    conversation: ConversationMetadata = await conversation_store.get_metadata(conversation_id)
    pull_pattern = "pull/(\\d+)"
    merge_request_pattern = "merge_requests/(\\d+)"
    pr_number = None
    match_pull = re.search(pull_pattern, tool_result)
    match_merge_request = re.search(merge_request_pattern, tool_result)
    if match_pull:
        pr_number = int(match_pull[1])
    elif match_merge_request:
        pr_number = int(match_merge_request[1])
    if pr_number:
        logger.info("Saving PR number: %s for conversation %s", pr_number, conversation_id)
        conversation.pr_number.append(pr_number)
    else:
        logger.warning("Failed to extract PR number for conversation %s", conversation_id)
    await conversation_store.save_metadata(conversation)


@mcp_server.tool()
async def create_pr(
    repo_name: Annotated[str, Field(description="GitHub repository ({{owner}}/{{repo}})")],
    source_branch: Annotated[str, Field(description="Source branch on repo")],
    target_branch: Annotated[str, Field(description="Target branch on repo")],
    title: Annotated[str, Field(description="PR Title")],
    body: Annotated[str | None, Field(description="PR body")],
    draft: Annotated[bool, Field(description="Whether PR opened is a draft")] = True,
    labels: Annotated[list[str] | None, Field(description="Labels to apply to the PR")] = None,
) -> str:
    """Create a pull request in GitHub repository.

    Opens a new pull request on GitHub with support for draft status and labels.
    Automatically appends a Forge conversation link to the PR body (in SaaS mode)
    and saves PR metadata to the conversation record.

    Args:
        repo_name: GitHub repository in format "owner/repo" (e.g., "pytorch/pytorch").
        source_branch: Source branch name containing the changes.
        target_branch: Target branch name where changes should merge (e.g., "main").
        title: Pull request title.
        body: Pull request description body text.
        draft: Whether to open as a draft PR. Defaults to True.
            Draft PRs cannot be merged until marked ready for review.
        labels: List of label names to apply to the PR.

    Returns:
        str: The created pull request URL.

    Raises:
        ToolError: If GitHub API call fails or authentication is invalid.
            Includes GitHub API error message in the error detail.

    Examples:
        >>> await create_pr(
        ...     repo_name="pytorch/pytorch",
        ...     source_branch="feature/async-ops",
        ...     target_branch="main",
        ...     title="Add async operations support",
        ...     body="Implements async/await for tensor operations",
        ...     draft=False,
        ...     labels=["enhancement", "high-priority"]
        ... )

    """
    logger.info("Calling Forge MCP create_pr")
    request = get_http_request()
    headers = request.headers
    conversation_id = headers.get("X-Forge-ServerConversation-ID", None)
    provider_tokens = await get_provider_tokens(request)
    access_token = await get_access_token(request)
    user_id = await get_user_id(request)
    github_token = provider_tokens.get(ProviderType.GITHUB, ProviderToken()) if provider_tokens else ProviderToken()
    github_service = GithubServiceImpl(
        user_id=github_token.user_id,
        external_auth_id=user_id,
        external_auth_token=access_token,
        token=github_token.token,
        base_domain=github_token.host,
    )
    try:
        body = await get_conversation_link(github_service, conversation_id, body or "")
    except Exception as e:
        logger.warning("Failed to append conversation link: %s", e)
    try:
        response = await github_service.create_pr(
            repo_name=repo_name,
            source_branch=source_branch,
            target_branch=target_branch,
            title=title,
            body=body,
            draft=draft,
            labels=labels,
        )
        if conversation_id:
            await save_pr_metadata(user_id, conversation_id, response)
    except Exception as e:
        error = f"Error creating pull request: {e}"
        raise ToolError(str(error)) from e
    return response


@mcp_server.tool()
async def create_mr(
    id: Annotated[int | str, Field(description="GitLab repository (ID or URL-encoded path of the project)")],
    source_branch: Annotated[str, Field(description="Source branch on repo")],
    target_branch: Annotated[str, Field(description="Target branch on repo")],
    title: Annotated[str, Field(description="MR Title. Start title with `DRAFT:` or `WIP:` if applicable.")],
    description: Annotated[str | None, Field(description="MR description")],
    labels: Annotated[list[str] | None, Field(description="Labels to apply to the MR")] = None,
) -> str:
    """Create a merge request in GitLab repository.

    Opens a new merge request on GitLab. Automatically appends a Forge
    conversation link to the description and saves MR metadata to the
    conversation record.

    Args:
        id: GitLab project ID or URL-encoded project path.
            Can be numeric ID or path like "namespace/project".
        source_branch: Source branch name containing the changes.
        target_branch: Target branch name for merge (e.g., "main").
        title: Merge request title. Should include "DRAFT:" or "WIP:" prefix
            if the MR is not ready for review.
        description: Merge request description/body text.
        labels: List of label names to apply to the MR.

    Returns:
        str: The created merge request URL.

    Raises:
        ToolError: If GitLab API call fails or authentication is invalid.
            Includes GitLab API error message in the error detail.

    Examples:
        >>> await create_mr(
        ...     id="group/project-name",
        ...     source_branch="feature/caching",
        ...     target_branch="main",
        ...     title="DRAFT: Implement caching layer",
        ...     description="Adds Redis-based caching for performance",
        ...     labels=["performance"]
        ... )

    """
    logger.info("Calling Forge MCP create_mr")
    request = get_http_request()
    headers = request.headers
    conversation_id = headers.get("X-Forge-ServerConversation-ID", None)
    provider_tokens = await get_provider_tokens(request)
    access_token = await get_access_token(request)
    user_id = await get_user_id(request)
    github_token = provider_tokens.get(ProviderType.GITLAB, ProviderToken()) if provider_tokens else ProviderToken()
    gitlab_service = GitLabServiceImpl(
        user_id=github_token.user_id,
        external_auth_id=user_id,
        external_auth_token=access_token,
        token=github_token.token,
        base_domain=github_token.host,
    )
    try:
        description = await get_conversation_link(gitlab_service, conversation_id, description or "")
    except Exception as e:
        logger.warning("Failed to append conversation link: %s", e)
    try:
        response = await gitlab_service.create_mr(
            id=id,
            source_branch=source_branch,
            target_branch=target_branch,
            title=title,
            description=description,
            labels=labels,
        )
        if conversation_id:
            await save_pr_metadata(user_id, conversation_id, response)
    except Exception as e:
        error = f"Error creating merge request: {e}"
        raise ToolError(str(error)) from e
    return response


@mcp_server.tool()
async def create_bitbucket_pr(
    repo_name: Annotated[str, Field(description="Bitbucket repository (workspace/repo_slug)")],
    source_branch: Annotated[str, Field(description="Source branch on repo")],
    target_branch: Annotated[str, Field(description="Target branch on repo")],
    title: Annotated[str, Field(description="PR Title. Start title with `DRAFT:` or `WIP:` if applicable.")],
    description: Annotated[str | None, Field(description="PR description")],
) -> str:
    """Create a pull request in Bitbucket Cloud repository.

    Opens a new pull request on Bitbucket. Automatically appends a Forge
    conversation link to the description and saves PR metadata to the
    conversation record.

    Args:
        repo_name: Bitbucket repository in format "workspace/repo_slug"
            (e.g., "myworkspace/my-repo").
        source_branch: Source branch name containing the changes.
        target_branch: Target branch name for merge (e.g., "main").
        title: Pull request title. Should include "DRAFT:" or "WIP:" prefix
            if not ready for review.
        description: Pull request description/body text.

    Returns:
        str: The created pull request URL.

    Raises:
        ToolError: If Bitbucket API call fails or authentication is invalid.
            Includes Bitbucket API error message in the error detail.

    Examples:
        >>> await create_bitbucket_pr(
        ...     repo_name="myworkspace/my-repo",
        ...     source_branch="feature/auth",
        ...     target_branch="main",
        ...     title="Add OAuth2 support",
        ...     description="Implements OAuth2 authentication flow"
        ... )

    """
    logger.info("Calling Forge MCP create_bitbucket_pr")
    request = get_http_request()
    headers = request.headers
    conversation_id = headers.get("X-Forge-ServerConversation-ID", None)
    provider_tokens = await get_provider_tokens(request)
    access_token = await get_access_token(request)
    user_id = await get_user_id(request)
    bitbucket_token = (
        provider_tokens.get(ProviderType.BITBUCKET, ProviderToken()) if provider_tokens else ProviderToken()
    )
    bitbucket_service = BitBucketServiceImpl(
        user_id=bitbucket_token.user_id,
        external_auth_id=user_id,
        external_auth_token=access_token,
        token=bitbucket_token.token,
        base_domain=bitbucket_token.host,
    )
    try:
        description = await get_conversation_link(bitbucket_service, conversation_id, description or "")
    except Exception as e:
        logger.warning("Failed to append conversation link: %s", e)
    try:
        response = await bitbucket_service.create_pr(
            repo_name=repo_name,
            source_branch=source_branch,
            target_branch=target_branch,
            title=title,
            body=description,
        )
        if conversation_id:
            await save_pr_metadata(user_id, conversation_id, response)
    except Exception as e:
        error = f"Error creating pull request: {e}"
        logger.error(error)
        raise ToolError(str(error)) from e
    return response
