"""Model Context Protocol (MCP) routes and helpers for Forge server tooling."""

# Note: NOT using "from __future__ import annotations" to avoid Field resolution issues in fastmcp
# from __future__ import annotations

import os
import re
import random
import contextlib
from dataclasses import dataclass
from collections.abc import Awaitable, Callable
from typing import TYPE_CHECKING, Annotated, Any, TypeVar

# Import Field early to ensure it's in the global namespace
from pydantic import Field, SecretStr

from fastmcp import FastMCP
from fastmcp.exceptions import ToolError
from fastmcp.server.dependencies import get_http_request

from forge.core.logger import forge_logger as logger, get_trace_context
from forge.integrations.github.github_service import GithubServiceImpl
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

mcp_server = FastMCP(
    "mcp", stateless_http=True, dependencies=None, mask_error_details=True
)

# Optional OpenTelemetry setup for MCP instrumentation
_OTEL_MCP_ENABLED = os.getenv(
    "OTEL_INSTRUMENT_MCP", os.getenv("OTEL_ENABLED", "false")
).lower() in (
    "true",
    "1",
    "yes",
)
_mcp_tracer: Any | None = None
_SPAN_KIND: Any | None = None
try:
    if _OTEL_MCP_ENABLED:
        from opentelemetry import trace as _otel_trace  # type: ignore
        from opentelemetry.trace import SpanKind  # type: ignore

        _mcp_tracer = _otel_trace.get_tracer("forge.mcp")
        _SPAN_KIND = SpanKind
except Exception:  # pragma: no cover - optional dependency
    _mcp_tracer = None
    _SPAN_KIND = None
HOST = f"https://{os.getenv('WEB_HOST', 'app.forge.dev').strip()}"
CONVERSATION_URL = HOST + "/conversations/{}"

ServiceT = TypeVar("ServiceT", bound=GitService)
ReturnT = TypeVar("ReturnT")


@dataclass
class _McpRequestContext:
    conversation_id: str | None
    provider_tokens: dict[ProviderType, ProviderToken] | None
    access_token: SecretStr | None
    user_id: str | None


async def _request_context() -> _McpRequestContext:
    request = get_http_request()
    headers = request.headers
    conversation_id = headers.get("X-Forge-ServerConversation-ID", None)
    provider_tokens_raw = await get_provider_tokens(request)
    provider_tokens = (
        dict(provider_tokens_raw) if provider_tokens_raw is not None else None
    )
    access_token = await get_access_token(request)
    user_id = await get_user_id(request)
    return _McpRequestContext(
        conversation_id=conversation_id,
        provider_tokens=provider_tokens,
        access_token=access_token,
        user_id=user_id,
    )


def _provider_token(
    context: _McpRequestContext, provider: ProviderType
) -> ProviderToken:
    if not context.provider_tokens:
        return ProviderToken()
    return context.provider_tokens.get(provider, ProviderToken())


def _build_service(
    service_cls: type[ServiceT],
    token: ProviderToken,
    external_auth_id: str | None,
    external_auth_token: SecretStr | None,
) -> ServiceT:
    return service_cls(
        user_id=token.user_id,
        external_auth_id=external_auth_id,
        external_auth_token=external_auth_token,
        token=token.token,
        base_domain=token.host,
    )


async def _append_conversation_link(
    service: GitService,
    conversation_id: str | None,
    body: str | None,
) -> str:
    body = body or ""
    try:
        return await get_conversation_link(service, conversation_id, body)
    except Exception as exc:
        logger.warning("Failed to append conversation link: %s", exc)
        return body


def _otel_sample_rate() -> float:
    try:
        return float(
            os.getenv("OTEL_SAMPLE_MCP", os.getenv("OTEL_SAMPLE_DEFAULT", "1.0"))
        )
    except Exception:
        return 1.0


def _span_context_manager():
    if _mcp_tracer is None:
        return contextlib.nullcontext()
    sample_rate = max(0.0, min(1.0, _otel_sample_rate()))
    if random.random() >= sample_rate:
        return contextlib.nullcontext()
    span_kind = _SPAN_KIND
    if span_kind is None:
        return contextlib.nullcontext()
    return _mcp_tracer.start_as_current_span("mcp.request", kind=span_kind.CLIENT)


def _set_span_attributes(
    span,
    tool_name: str,
    resource: str,
    conversation_id: str | None,
) -> None:
    try:
        span.set_attribute("tool.name", tool_name)
        span.set_attribute("tool.kind", "mcp")
        span.set_attribute("mcp.server.name", "mcp")
        span.set_attribute("mcp.method", tool_name)
        span.set_attribute("mcp.resource", resource)
        if conversation_id:
            span.set_attribute("conversation.id", conversation_id)
        ctx = get_trace_context()
        trace_id = ctx.get("trace_id")
        if trace_id:
            span.set_attribute("forge.trace_id", str(trace_id))
    except Exception:
        pass


@contextlib.contextmanager
def _mcp_span(tool_name: str, resource: str, conversation_id: str | None):
    span_ref = None
    with _span_context_manager() as span:
        span_ref = span
        if span_ref is not None:
            _set_span_attributes(span_ref, tool_name, resource, conversation_id)
        try:
            yield span_ref
        except Exception as exc:
            if span_ref is not None:
                try:
                    span_ref.record_exception(exc)
                    span_ref.set_attribute("error", True)
                except Exception:
                    pass
            raise


async def _maybe_save_metadata(
    user_id: str | None, conversation_id: str | None, response: str
) -> None:
    if conversation_id:
        await save_pr_metadata(user_id, conversation_id, response)


async def _execute_with_tracing(
    tool_name: str,
    resource: str,
    conversation_id: str | None,
    action: Callable[[], Awaitable[ReturnT]],
    error_prefix: str,
) -> ReturnT:
    try:
        with _mcp_span(tool_name, resource, conversation_id):
            return await action()
    except Exception as exc:
        error = f"{error_prefix}: {exc}"
        logger.error(error)
        raise ToolError(error) from exc


async def get_conversation_link(
    service: GitService,
    conversation_id: str | None,
    body: str,
) -> str:
    """Append a Forge conversation link to PR body in SaaS mode.

    Adds a followup link to the original Forge conversation URL in the PR
    body, enabling reviewers to click through to continue refining the request.
    This only operates in SaaS app mode; other modes return the body unchanged.

    Args:
        service: The Git service instance (GitHub)
            with authentication configured for retrieving user information.
        conversation_id: Unique identifier of the conversation that opened
            the pull request.
        body: The current PR body text to augment with the conversation link.

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
    conversation_link = (
        f"@{username} can click here to [continue refining the PR]({conversation_url})"
    )
    body += f"\n\n{conversation_link}"
    return body


async def save_pr_metadata(
    user_id: str | None, conversation_id: str, tool_result: str
) -> None:
    """Extract PR number from tool output and update conversation metadata.

    Parses GitHub pull request numbers from tool result URLs using regex patterns,
    then persists the extracted PR number to the conversation's metadata store
    for tracking.

    Args:
        user_id: User identifier for accessing conversation store.
            Can be None for anonymous conversations.
        conversation_id: Unique conversation identifier to retrieve and update.
        tool_result: Tool output string expected to contain PR URL
            (e.g., "https://github.com/owner/repo/pull/123").

    Returns:
        None

    Raises:
        Exception: Any exceptions from conversation_store operations are logged
            but not re-raised; warnings logged if PR number extraction fails.

    """
    conversation_store = await get_conversation_store().get_instance(
        get_config(), user_id
    )
    conversation: ConversationMetadata = await conversation_store.get_metadata(
        conversation_id
    )
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
        logger.info(
            "Saving PR number: %s for conversation %s", pr_number, conversation_id
        )
        conversation.pr_number.append(pr_number)
    else:
        logger.warning(
            "Failed to extract PR number for conversation %s", conversation_id
        )
    await conversation_store.save_metadata(conversation)


@mcp_server.tool()
async def create_pr(
    repo_name: Annotated[
        str, Field(description="GitHub repository ({{owner}}/{{repo}})")
    ],
    source_branch: Annotated[str, Field(description="Source branch on repo")],
    target_branch: Annotated[str, Field(description="Target branch on repo")],
    title: Annotated[str, Field(description="PR Title")],
    body: Annotated[str | None, Field(description="PR body")],
    draft: Annotated[bool, Field(description="Whether PR opened is a draft")] = True,
    labels: Annotated[
        list[str] | None, Field(description="Labels to apply to the PR")
    ] = None,
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
    context = await _request_context()
    github_token = _provider_token(context, ProviderType.GITHUB)
    github_service = _build_service(
        GithubServiceImpl, github_token, context.user_id, context.access_token
    )
    body = await _append_conversation_link(github_service, context.conversation_id, body)

    async def _perform_request() -> str:
        response = await github_service.create_pr(
            repo_name=repo_name,
            source_branch=source_branch,
            target_branch=target_branch,
            title=title,
            body=body,
            draft=draft,
            labels=labels,
        )
        await _maybe_save_metadata(context.user_id, context.conversation_id, response)
        return response

    return await _execute_with_tracing(
        tool_name="create_pr",
        resource="github/pr",
        conversation_id=context.conversation_id,
        action=_perform_request,
        error_prefix="Error creating pull request",
    )







