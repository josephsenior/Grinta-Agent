"""Routes for creating, listing, and managing Forge conversations and sessions."""

from __future__ import annotations

import asyncio
import contextlib
import itertools
import os
import sys
import re
import uuid
from datetime import datetime, timezone, timedelta
from types import MappingProxyType
from typing import Optional, TYPE_CHECKING, Annotated, Any, cast

from fastapi import APIRouter, Body, Depends, HTTPException, Request, status
from fastapi.responses import JSONResponse
from jinja2 import Environment, FileSystemLoader
from pydantic import BaseModel, ConfigDict, Field

from forge.server.utils.responses import success, error

from forge.core.config.llm_config import LLMConfig
from forge.core.logger import forge_logger as logger
from forge.core.pydantic_compat import model_dump_json
from forge.events.action import ChangeAgentStateAction, NullAction
from forge.events.event_filter import EventFilter
from forge.events.event_store import EventStore
from forge.events.observation import AgentStateChangedObservation, NullObservation
from forge.metasop.router import run_metasop_for_conversation
from forge.runtime import get_runtime_cls
from forge.runtime.runtime_status import RuntimeStatus
from forge.server.data_models.conversation_info import ConversationInfo
from forge.server.data_models.conversation_info_result_set import (
    ConversationInfoResultSet,
)
from forge.server.dependencies import get_dependencies
from forge.server.services.conversation_service import (
    create_new_conversation,
    initialize_conversation,
    setup_init_conversation_settings,
)
from forge.server.shared import (
    ConversationManagerImpl,
    ConversationStoreImpl,
    config,
    conversation_manager,
    file_store,
    get_conversation_manager,
    get_conversation_manager_impl,
)
from forge.server.types import LLMAuthenticationError, MissingSettingsError
from forge.server.user_auth import (
    get_auth_type,
    get_provider_tokens,
    get_user_id,
    get_user_secrets,
    get_user_settings,
    get_user_settings_store,
)
from forge.server.user_auth.user_auth import AuthType
from forge.server.utils import get_conversation as get_conversation_metadata
from forge.server.utils import (
    get_conversation_store,
    resolve_conversation_store,
    validate_conversation_id,
)
from forge.storage.data_models.conversation_metadata import (
    ConversationMetadata,
    ConversationTrigger,
)
from forge.storage.data_models.conversation_status import ConversationStatus
from forge.storage.locations import get_experiment_config_filename
from forge.utils.async_utils import wait_all
from forge.utils.conversation_summary import get_default_conversation_title

# Import these at runtime for InitSessionRequest model_rebuild
from forge.core.config.mcp_config import MCPConfig
from forge.integrations.provider import (
    PROVIDER_TOKEN_TYPE,
    ProviderHandler,
    ProviderToken,
)
from forge.integrations.service_types import (
    CreateMicroagent,
    ProviderType,
    SuggestedTask,
)
from forge.storage.data_models.user_secrets import UserSecrets

if TYPE_CHECKING:
    from forge.experiments.experiment_manager import ExperimentConfig
    from forge.server.data_models.agent_loop_info import AgentLoopInfo
    from forge.storage.conversation.conversation_store import ConversationStore
    from forge.storage.data_models.settings import Settings
    from forge.storage.settings.settings_store import SettingsStore
    from forge.server.conversation_manager.conversation_manager import ConversationManager

app: APIRouter
if "pytest" in sys.modules:

    class NoOpAPIRouter(APIRouter):
        """Router stub used in tests to short-circuit FastAPI route registration."""

        def add_api_route(self, path: str, endpoint, **kwargs):  # type: ignore[override]
            """Return endpoint without registering it so tests can inspect handlers directly."""
            return endpoint

    app = cast(APIRouter, NoOpAPIRouter())
else:
    app = APIRouter(prefix="/api")


async def _resolve_conversation_store(
    conversation_store: Any | None, user_id: str | None = None
):
    if conversation_store is not None:
        return conversation_store
    if user_id is not None:
        return await ConversationStoreImpl.get_instance(config, user_id)
    return await resolve_conversation_store(None)


def _filter_conversations_by_age(
    conversations: list[ConversationMetadata], max_age_seconds: int
) -> list:
    """Filter conversations by age, removing those older than max_age_seconds.

    Args:
        conversations: List of conversations to filter
        max_age_seconds: Maximum age in seconds for conversations to be included

    Returns:
        List of conversations that meet the age criteria

    """
    now = datetime.now(timezone.utc)
    filtered_results = []
    for conversation in conversations:
        if not hasattr(conversation, "created_at"):
            continue
        age_seconds = (
            now - conversation.created_at.replace(tzinfo=timezone.utc)
        ).total_seconds()
        if age_seconds > max_age_seconds:
            continue
        filtered_results.append(conversation)
    return filtered_results


async def _build_conversation_result_set(
    filtered_conversations: list,
    next_page_id: str | None,
) -> ConversationInfoResultSet:
    """Build a ConversationInfoResultSet from filtered conversations.

    This function handles the common logic of getting conversation IDs, connections,
    agent loop info, and building the final result set.

    Args:
        filtered_conversations: List of filtered conversations
        next_page_id: Next page ID for pagination

    Returns:
        ConversationInfoResultSet with the processed conversations

    """
    manager = _require_conversation_manager()
    conversation_ids = {
        conversation.conversation_id for conversation in filtered_conversations
    }
    connection_ids_to_conversation_ids = await manager.get_connections(
        filter_to_sids=conversation_ids
    )
    agent_loop_info = await manager.get_agent_loop_info(
        filter_to_sids=conversation_ids
    )
    agent_loop_info_by_conversation_id = {
        info.conversation_id: info for info in agent_loop_info
    }
    return ConversationInfoResultSet(
        results=await wait_all(
            _get_conversation_info(
                conversation=conversation,
                num_connections=sum(
                    conversation_id == conversation.conversation_id
                    for conversation_id in connection_ids_to_conversation_ids.values()
                ),
                agent_loop_info=agent_loop_info_by_conversation_id.get(
                    conversation.conversation_id
                ),
            )
            for conversation in filtered_conversations
        ),
        next_page_id=next_page_id,
    )


class InitSessionRequest(BaseModel):
    """Request payload for creating or resuming a conversation session."""

    repository: str | None = None
    git_provider: ProviderType | None = None
    selected_branch: str | None = None
    initial_user_msg: str | None = None
    image_urls: list[str] | None = None
    replay_json: str | None = None
    suggested_task: SuggestedTask | None = None
    create_microagent: CreateMicroagent | None = None
    conversation_instructions: str | None = None
    mcp_config: MCPConfig | None = None
    if os.getenv("ALLOW_SET_CONVERSATION_ID", "0") == "1":
        conversation_id: str = Field(default_factory=lambda: uuid.uuid4().hex)
    model_config = ConfigDict(extra="forbid")


# Rebuild the model to resolve forward references
InitSessionRequest.model_rebuild()


class ConversationResponse(BaseModel):
    """Standard response payload for conversation management endpoints."""

    status: str
    conversation_id: str
    message: str | None = None
    conversation_status: ConversationStatus | None = None


class ProvidersSetModel(BaseModel):
    """Wrapper for optional provider list supplied when starting a conversation."""

    providers_set: list[ProviderType] | None = None


def _extract_request_data(
    data: InitSessionRequest,
) -> tuple[
    str | None,
    str | None,
    str | None,
    list[str],
    str | None,
    SuggestedTask | None,
    CreateMicroagent | None,
    ProviderType | None,
    str | None,
]:
    r"""Extract and organize initialization parameters from request payload.

    Unpacks the InitSessionRequest into individual components for use in
    conversation initialization. This helper centralizes parameter extraction
    to reduce complexity in the main flow.

    Args:
        data: InitSessionRequest containing all conversation initialization parameters

    Returns:
        Tuple containing in order:
            - repository: Optional repository identifier
            - selected_branch: Optional branch name
            - initial_user_msg: Optional initial user message
            - image_urls: List of image URLs (empty list if none)
            - replay_json: Optional JSON string for replaying conversation
            - suggested_task: Optional suggested task object
            - create_microagent: Optional microagent creation parameters
            - git_provider: Optional git provider type
            - conversation_instructions: Optional custom instructions

    Example:
        repo, branch, msg, imgs, replay, task, agent, provider, instr = \\
            _extract_request_data(request)

    """
    return (
        data.repository,
        data.selected_branch,
        data.initial_user_msg,
        data.image_urls or [],
        data.replay_json,
        data.suggested_task,
        data.create_microagent,
        data.git_provider,
        data.conversation_instructions,
    )


def _determine_conversation_trigger(
    suggested_task: SuggestedTask | None,
    create_microagent: CreateMicroagent | None,
    auth_type: AuthType | None,
) -> tuple[ConversationTrigger, str | None, ProviderType | None]:
    r"""Determine conversation trigger type and override repository/provider if needed.

    Analyzes request context to identify what triggered the conversation (GUI,
    suggested task, microagent management, or remote API key). May override
    the repository and git provider based on the trigger type.

    Args:
        suggested_task: Optional suggested task triggering the conversation
        create_microagent: Optional microagent creation parameters
        auth_type: Authentication type (e.g., BEARER for remote API)

    Returns:
        Tuple containing:
            - conversation_trigger: ConversationTrigger enum value indicating trigger type
            - repository: Overridden repository if applicable, None otherwise
            - git_provider: Overridden git provider if applicable, None otherwise

    Example:
        trigger, repo_override, provider_override = \\
            _determine_conversation_trigger(task, agent, AuthType.BEARER)

    """
    conversation_trigger = ConversationTrigger.GUI
    repository = None
    git_provider = None

    if suggested_task:
        conversation_trigger = ConversationTrigger.SUGGESTED_TASK
    elif create_microagent:
        conversation_trigger = ConversationTrigger.MICROAGENT_MANAGEMENT
        if create_microagent.repo:
            repository = create_microagent.repo
        if create_microagent.git_provider:
            git_provider = create_microagent.git_provider

    if auth_type == AuthType.BEARER:
        conversation_trigger = ConversationTrigger.REMOTE_API_KEY

    return conversation_trigger, repository, git_provider


def _validate_remote_api_request(
    conversation_trigger: ConversationTrigger,
    initial_user_msg: str,
) -> JSONResponse | None:
    """Validate remote API requests have required parameters.

    Remote API requests (identified by REMOTE_API_KEY trigger) require an
    initial user message. This validator ensures the requirement is met
    before proceeding with conversation initialization.

    Args:
        conversation_trigger: The conversation trigger type
        initial_user_msg: The initial message from user

    Returns:
        JSONResponse with error details if validation fails, None if valid

    Example:
        error = _validate_remote_api_request(trigger, msg)
        if error:
            return error

    """
    if (
        conversation_trigger == ConversationTrigger.REMOTE_API_KEY
        and not initial_user_msg
    ):
        return error(
            message="Missing initial user message",
            status_code=status.HTTP_400_BAD_REQUEST,
            error_code="CONFIGURATION$MISSING_USER_MESSAGE",
        )
    return None


async def _verify_repository_access(
    repository: str | None,
    git_provider: ProviderType | None,
    provider_tokens: PROVIDER_TOKEN_TYPE,
) -> None:
    """Verify user has access to the specified repository.

    Calls the provider handler to verify repository access using provided
    authentication tokens. This prevents invalid repository selections and
    improves error messaging early in the flow.

    Args:
        repository: Repository identifier (e.g., 'owner/repo')
        git_provider: Git provider type (GitHub, Bitbucket, etc.)
        provider_tokens: Authentication tokens for the provider

    Raises:
        AuthenticationError: If provider tokens are missing or invalid
        PermissionError: If user doesn't have access to repository
        RuntimeError: If provider verification fails

    Example:
        await _verify_repository_access('owner/repo', 'github', tokens)

    """
    if not repository:
        return
    provider_handler = ProviderHandler(
        cast(MappingProxyType[ProviderType, ProviderToken], provider_tokens)
    )
    await provider_handler.verify_repo_provider(repository, git_provider)


async def _handle_metasop_conversation(
    user_id: str,
    conversation_id: str,
    repository: str | None,
    selected_branch: str | None,
    conversation_trigger: ConversationTrigger,
    git_provider: ProviderType | None,
    initial_user_msg: str | None,
) -> ConversationResponse:
    """Initialize and start a MetaSOP-orchestrated conversation.

    Creates conversation metadata and schedules a background MetaSOP orchestration
    task. MetaSOP conversations allow complex multi-step agent workflows triggered
    from initial user messages. Returns immediately to client while MetaSOP runs.

    Args:
        user_id: Authenticated user identifier
        conversation_id: Unique conversation identifier
        repository: Repository to work with
        selected_branch: Git branch to use
        conversation_trigger: What triggered this conversation
        git_provider: Git provider type (GitHub, Bitbucket, etc.)
        initial_user_msg: Initial message to start MetaSOP with

    Returns:
        ConversationResponse with status "ok" and conversation ID

    Raises:
        RuntimeError: If conversation initialization fails

    Example:
        response = await _handle_metasop_conversation(
            user_id="user123",
            conversation_id="conv456",
            repository="owner/repo",
            selected_branch="main",
            conversation_trigger=ConversationTrigger.GUI,
            git_provider="github",
            initial_user_msg="Fix the bug in main.py"
        )

    """
    conversation_metadata = await initialize_conversation(
        user_id,
        conversation_id,
        repository,
        selected_branch,
        conversation_trigger,
        git_provider,
    )

    if not conversation_metadata:
        msg = "Failed to initialize conversation"
        raise RuntimeError(msg)

    manager = _get_conversation_manager_instance()
    if manager is not None:
        sio = getattr(manager, "sio", None)
        if sio is not None:
            with contextlib.suppress(Exception):
                await sio.emit(
                    "oh_event",
                    {
                        "status_update": True,
                        "type": "info",
                        "message": "Starting MetaSOP orchestration…",
                    },
                    to=f"room:{conversation_id}",
                )

    asyncio.create_task(
        run_metasop_for_conversation(
            conversation_id=conversation_id,
            user_id=user_id,
            raw_message=initial_user_msg or "",
            repo_root=None,
        ),
    )

    return ConversationResponse(
        status="ok",
        conversation_id=conversation_id,
        conversation_status=ConversationStatus.STARTING,
    )


async def _handle_regular_conversation(
    user_id: str,
    conversation_id: str,
    repository: str | None,
    selected_branch: str | None,
    initial_user_msg: str | None,
    image_urls: list[str],
    replay_json: str | None,
    conversation_trigger: ConversationTrigger,
    conversation_instructions: str | None,
    git_provider: ProviderType | None,
    provider_tokens: PROVIDER_TOKEN_TYPE,
    user_secrets: UserSecrets,
    mcp_config: MCPConfig | None,
) -> ConversationResponse:
    """Initialize a regular conversation with full startup configuration.

    Creates and starts a new conversation with the agent, applying all user
    settings, secrets, and optional configurations. This is the standard
    conversation startup path (vs MetaSOP orchestration).

    Args:
        user_id: Authenticated user identifier
        conversation_id: Unique conversation identifier
        repository: Target repository (optional)
        selected_branch: Git branch to use (optional)
        initial_user_msg: Initial message for the agent
        image_urls: List of image URLs to include in context
        replay_json: JSON string to replay conversation events (optional)
        conversation_trigger: What triggered this conversation
        conversation_instructions: Custom instructions for the agent
        git_provider: Git provider type
        provider_tokens: Authentication tokens for git operations
        user_secrets: User's stored secrets for services
        mcp_config: MCP server configuration

    Returns:
        ConversationResponse with conversation status and ID

    Raises:
        MissingSettingsError: If required user settings missing
        LLMAuthenticationError: If LLM authentication fails

    Example:
        response = await _handle_regular_conversation(
            user_id="user123",
            conversation_id="conv456",
            repository="owner/repo",
            selected_branch="main",
            initial_user_msg="Debug this issue",
            image_urls=[],
            replay_json=None,
            conversation_trigger=ConversationTrigger.GUI,
            conversation_instructions=None,
            git_provider="github",
            provider_tokens={...},
            user_secrets=UserSecrets(),
            mcp_config=None
        )

    """
    agent_loop_info = await create_new_conversation(
        user_id=user_id,
        git_provider_tokens=provider_tokens,
        custom_secrets=user_secrets.custom_secrets if user_secrets else None,
        selected_repository=repository,
        selected_branch=selected_branch,
        initial_user_msg=initial_user_msg,
        image_urls=image_urls or None,
        replay_json=replay_json,
        conversation_trigger=conversation_trigger,
        conversation_instructions=conversation_instructions,
        git_provider=git_provider,
        conversation_id=conversation_id,
        mcp_config=mcp_config,
    )

    return ConversationResponse(
        status="ok",
        conversation_id=conversation_id,
        conversation_status=agent_loop_info.status,
    )


def _handle_conversation_errors(e: Exception) -> JSONResponse:
    """Convert conversation initialization errors to appropriate HTTP responses.

    Maps specific exception types to HTTP status codes and user-friendly error
    messages. For known errors, returns structured JSON responses; for unknown
    errors, re-raises the exception.

    Args:
        e: Exception raised during conversation initialization

    Returns:
        JSONResponse with appropriate HTTP status and error details:
            - 400 Bad Request for MissingSettingsError or LLMAuthenticationError
            - Other errors are re-raised

    Raises:
        Exception: If error type is not specifically handled

    Example:
        try:
            await initialize_conversation(...)
        except Exception as e:
            return _handle_conversation_errors(e)

    """
    if isinstance(e, MissingSettingsError):
        return error(
            message=str(e),
            status_code=status.HTTP_400_BAD_REQUEST,
            error_code="CONFIGURATION$SETTINGS_NOT_FOUND",
        )
    if isinstance(e, LLMAuthenticationError):
        return error(
            message=str(e),
            status_code=status.HTTP_400_BAD_REQUEST,
            error_code=RuntimeStatus.ERROR_LLM_AUTHENTICATION.value,
        )
    raise e


def _apply_conversation_overrides(
    repository: str | None,
    git_provider: ProviderType | None,
    override_repo: str | None,
    override_git_provider: ProviderType | None,
    suggested_task: SuggestedTask | None,
    initial_user_msg: str | None,
) -> tuple[str | None, ProviderType | None, str | None]:
    """Apply conversation overrides from triggers.

    Args:
        repository: Original repository
        git_provider: Original git provider
        override_repo: Override repository
        override_git_provider: Override git provider
        suggested_task: Suggested task object
        initial_user_msg: Initial user message

    Returns:
        Tuple of (repository, git_provider, initial_user_msg)

    """
    if override_repo and not repository:
        repository = override_repo
    if override_git_provider and not git_provider:
        git_provider = override_git_provider
    if suggested_task:
        initial_user_msg = suggested_task.get_prompt_for_task()

    return repository, git_provider, initial_user_msg


def _normalize_provider_tokens(
    provider_tokens: PROVIDER_TOKEN_TYPE | None,
) -> PROVIDER_TOKEN_TYPE:
    """Normalize provider tokens into a MappingProxyType keyed by ProviderType."""
    if provider_tokens is None:
        return cast(PROVIDER_TOKEN_TYPE, MappingProxyType({}))
    if isinstance(provider_tokens, MappingProxyType):
        return provider_tokens
    return cast(
        PROVIDER_TOKEN_TYPE,
        MappingProxyType(dict(provider_tokens)),
    )


def _get_conversation_manager_instance() -> "ConversationManager | None":
    """Best-effort fetch of the global conversation manager."""
    manager: Any = conversation_manager
    if manager is not None:
        return manager
    try:
        return get_conversation_manager()
    except Exception:
        return None


def _require_conversation_manager() -> "ConversationManager":
    """Fetch the global conversation manager or raise an HTTP error."""
    manager = _get_conversation_manager_instance()
    if manager is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Conversation manager is not initialized",
        )
    return manager


def _prepare_conversation_params(
    user_id: str | None,
    provider_tokens: PROVIDER_TOKEN_TYPE | None,
    user_secrets: UserSecrets | None,
) -> tuple[str, PROVIDER_TOKEN_TYPE, UserSecrets]:
    """Prepare conversation parameters with defaults.

    Args:
        user_id: User ID
        provider_tokens: Provider tokens
        user_secrets: User secrets

    Returns:
        Tuple of (user_id, provider_tokens, user_secrets)

    """
    normalized_tokens = _normalize_provider_tokens(provider_tokens)

    return (
        user_id or "dev-user",
        normalized_tokens,
        user_secrets or UserSecrets(),
    )


@app.post("/conversations", response_model=ConversationResponse)
async def new_conversation(
    data: InitSessionRequest,
    user_id: Annotated[str | None, Depends(get_user_id)] = None,
    provider_tokens: Annotated[
        PROVIDER_TOKEN_TYPE | None, Depends(get_provider_tokens)
    ] = None,
    user_secrets: Annotated[UserSecrets | None, Depends(get_user_secrets)] = None,
    auth_type: Annotated[AuthType | None, Depends(get_auth_type)] = None,
) -> ConversationResponse | JSONResponse:
    """Initialize a new session or join an existing one.

    After successful initialization, the client should connect to the WebSocket
    using the returned conversation ID.
    """
    logger.info("initializing_new_conversation:%s", data)

    (
        repository,
        selected_branch,
        initial_user_msg,
        image_urls,
        replay_json,
        suggested_task,
        create_microagent,
        git_provider,
        conversation_instructions,
    ) = _extract_request_data(data)

    conversation_trigger, override_repo, override_git_provider = (
        _determine_conversation_trigger(
            suggested_task,
            create_microagent,
            auth_type,
        )
    )

    repository, git_provider, initial_user_msg = _apply_conversation_overrides(
        repository,
        git_provider,
        override_repo,
        override_git_provider,
        suggested_task,
        initial_user_msg,
    )

    if error_response := _validate_remote_api_request(
        conversation_trigger, initial_user_msg or ""
    ):
        return error_response

    user_id, provider_tokens, user_secrets = _prepare_conversation_params(
        user_id, provider_tokens, user_secrets
    )

    try:
        if repository:
            await _verify_repository_access(repository, git_provider, provider_tokens)

        conversation_id = getattr(data, "conversation_id", None) or uuid.uuid4().hex

        return await _handle_regular_conversation(
            user_id=user_id,
            conversation_id=conversation_id,
            repository=repository,
            selected_branch=selected_branch,
            initial_user_msg=initial_user_msg,
            image_urls=image_urls,
            replay_json=replay_json,
            conversation_trigger=conversation_trigger,
            conversation_instructions=conversation_instructions,
            git_provider=git_provider,
            provider_tokens=provider_tokens,
            user_secrets=user_secrets,
            mcp_config=data.mcp_config,
        )
    except Exception as e:  # noqa: BLE001 - bubble up known errors via helper
        logger.exception("Failed to initialize conversation: %s", e)
        return _handle_conversation_errors(e)


@app.get("/conversations/test")
async def test_conversations_endpoint() -> JSONResponse:
    """Test endpoint to verify routing is working."""
    return JSONResponse(
        content={
            "status": "test_working",
            "message": "conversations endpoint is accessible",
        }
    )


@app.get("/conversations/simple")
async def simple_conversations_endpoint() -> dict:
    """Simple endpoint without dependencies to test routing."""
    return {"status": "simple_working", "count": 1}


async def _search_conversations_impl(
    *,
    page_id: str | None = None,
    limit: int = 20,
    conversation_store: ConversationStore | None = None,
    user_id: str | None = None,
    selected_repository: str | None = None,
    conversation_trigger: ConversationTrigger | None = None,
) -> ConversationInfoResultSet:
    """Search and filter conversations with pagination.

    Filters by age, repository, and trigger type when available.

    Args:
        page_id: Page cursor for pagination
        limit: Maximum results per page
        conversation_store: Optional conversation store override
        user_id: Identifier used to scope results to the requesting user
        selected_repository: Optional repository to filter results by
        conversation_trigger: Optional ConversationTrigger to filter results by

    Returns:
        Pagination-aware result set of conversations

    Raises:
        HTTPException: On any datastore issues

    """
    logger.info(
        "search_conversations called with: page_id=%s, limit=%s, user_id=%s, selected_repository=%s, conversation_trigger=%s",
        page_id,
        limit,
        user_id,
        selected_repository,
        conversation_trigger,
    )
    store = await _resolve_conversation_store(conversation_store, user_id)

    # Return empty list for development
    # return ConversationInfoResultSet(results=[], next_page_id=None)

    conversation_metadata_result_set = await store.search(page_id, limit)
    logger.info(
        "conversation_store.search returned %d conversations",
        len(conversation_metadata_result_set.results),
    )
    filtered_results = _filter_conversations_by_age(
        conversation_metadata_result_set.results,
        config.conversation_max_age_seconds,
    )
    final_filtered_results = []
    for conversation in filtered_results:
        if (
            selected_repository is not None
            and conversation.selected_repository != selected_repository
        ):
            continue
        if (
            conversation_trigger is not None
            and conversation.trigger != conversation_trigger
        ):
            continue
        final_filtered_results.append(conversation)
    return await _build_conversation_result_set(
        final_filtered_results, conversation_metadata_result_set.next_page_id
    )


@app.get("/conversations", response_model=None)
async def search_conversations_route(
    request: Request,
    page_id: str | None = None,
    limit: int = 20,
    selected_repository: str | None = None,
    conversation_trigger: ConversationTrigger | None = None,
):
    """HTTP endpoint to paginate conversation metadata with optional repository/trigger filters."""
    user_id = await get_user_id(request)
    conversation_store = await get_conversation_store(request)
    return await _search_conversations_impl(
        page_id=page_id,
        limit=limit,
        selected_repository=selected_repository,
        conversation_trigger=conversation_trigger,
        user_id=user_id,
        conversation_store=conversation_store,
    )


# Alias for tests expecting the function directly
search_conversations = _search_conversations_impl


async def get_conversation_details(
    conversation_id: str,
    conversation_store: Any | None = None,
    user_id: str | None = None,
) -> ConversationInfo | None:
    """Retrieve detailed conversation information without FastAPI dependencies."""
    store = await _resolve_conversation_store(conversation_store, user_id)
    if store is None:
        return None
    try:
        conversation = await store.get_metadata(conversation_id)
    except FileNotFoundError:
        return None

    manager = _require_conversation_manager()
    agent_loop_info_list = await manager.get_agent_loop_info(
        filter_to_sids={conversation_id}
    )
    agent_loop_info = agent_loop_info_list[0] if agent_loop_info_list else None
    connections = await manager.get_connections(conversation_id)
    num_connections = len(connections) if connections else 0

    return await _get_conversation_info(conversation, num_connections, agent_loop_info)


@app.get("/conversations/{conversation_id}", response_model=None)
async def _get_conversation_route(
    request: Request,
    conversation_id: str = Depends(validate_conversation_id),
) -> Any:
    user_id = await get_user_id(request)
    conversation_store = await get_conversation_store(request)
    return await get_conversation_details(conversation_id, conversation_store, user_id)


async def delete_conversation_entry(
    conversation_id: str,
    user_id: str | None = None,
    conversation_store: Any | None = None,
) -> bool:
    """Delete a conversation, mirroring the behaviour of the HTTP endpoint."""
    store = await _resolve_conversation_store(conversation_store, user_id)
    if store is None:
        return False
    try:
        await store.get_metadata(conversation_id)
    except FileNotFoundError:
        return False
    manager = _require_conversation_manager()
    if await manager.is_agent_loop_running(conversation_id):
        await manager.close_session(conversation_id)
    runtime_cls = get_runtime_cls(config.runtime)
    await runtime_cls.delete(conversation_id)
    await store.delete_metadata(conversation_id)
    return True


@app.delete("/conversations/{conversation_id}")
async def _delete_conversation_route(
    request: Request,
    conversation_id: str = Depends(validate_conversation_id),
) -> bool:
    user_id = await get_user_id(request)
    conversation_store = await get_conversation_store(request)
    return await delete_conversation_entry(conversation_id, user_id, conversation_store)


# Backwards-compatible aliases used directly in unit tests
get_conversation = get_conversation_details
delete_conversation = delete_conversation_entry


@app.get("/conversations/{conversation_id}/remember-prompt")
async def get_prompt(
    event_id: int,
    conversation_id: Annotated[str, Depends(validate_conversation_id)],
    user_settings: Annotated[Any, Depends(get_user_settings_store)],
    metadata: Annotated[ConversationMetadata, Depends(get_conversation_metadata)],
):
    """Generate a prompt for remembering conversation context at specific event.

    Args:
        event_id: Event ID to generate context from
        conversation_id: Conversation identifier
        user_settings: User settings store dependency
        metadata: Conversation metadata dependency

    Returns:
        JSON response with generated prompt

    Raises:
        ValueError: If settings not found

    """
    event_store = EventStore(
        sid=conversation_id, file_store=file_store, user_id=metadata.user_id
    )
    stringified_events = _get_contextual_events(event_store, event_id)
    settings = await user_settings.load()
    if settings is None:
        msg = "Settings not found"
        raise ValueError(msg)
    llm_config = LLMConfig(
        model=settings.llm_model or "",
        api_key=settings.llm_api_key,
        base_url=settings.llm_base_url,
    )
    prompt_template = generate_prompt_template(stringified_events)
    prompt = generate_prompt(llm_config, prompt_template, conversation_id)
    return JSONResponse({"status": "success", "prompt": prompt})


def generate_prompt_template(events: str) -> str:
    """Generate a prompt template from events using Jinja2.

    Args:
        events: The events string to include in the template.

    Returns:
        str: The rendered prompt template.

    """
    # nosec B701 - Template rendering for prompts (not HTML), autoescape enabled
    env = Environment(
        loader=FileSystemLoader("Forge/microagent/prompts"), autoescape=True
    )
    template = env.get_template("generate_remember_prompt.j2")
    return template.render(events=events)


def generate_prompt(
    llm_config: LLMConfig, prompt_template: str, conversation_id: str
) -> str:
    """Generate a prompt using LLM configuration and template.

    Args:
        llm_config: LLM configuration settings.
        prompt_template: The template to use for prompt generation.
        conversation_id: The conversation ID for context.

    Returns:
        str: The generated prompt.

    """
    messages = [
        {"role": "system", "content": prompt_template},
        {
            "role": "user",
            "content": "Please generate a prompt for the AI to update the special file based on the events provided.",
        },
    ]
    manager_impl = ConversationManagerImpl or get_conversation_manager_impl()
    if manager_impl is None:
        raise RuntimeError("Conversation manager implementation unavailable")
    raw_prompt = manager_impl.request_llm_completion(
        "remember_prompt",
        conversation_id,
        llm_config,
        messages,
    )
    if prompt := re.search(
        "<update_prompt>(.*?)</update_prompt>", raw_prompt, re.DOTALL
    ):
        return prompt[1].strip()
    msg = "No valid prompt found in the response."
    raise ValueError(msg)


async def _get_conversation_info(
    conversation: ConversationMetadata,
    num_connections: int,
    agent_loop_info: AgentLoopInfo | None,
) -> ConversationInfo | None:
    try:
        title = conversation.title or get_default_conversation_title(
            conversation.conversation_id
        )
        return ConversationInfo(
            trigger=conversation.trigger,
            conversation_id=conversation.conversation_id,
            title=title,
            last_updated_at=conversation.last_updated_at,
            created_at=conversation.created_at,
            selected_repository=conversation.selected_repository,
            selected_branch=conversation.selected_branch,
            git_provider=conversation.git_provider,
            status=getattr(agent_loop_info, "status", ConversationStatus.STOPPED),
            runtime_status=getattr(agent_loop_info, "runtime_status", None),
            agent_state=getattr(agent_loop_info, "agent_state", None),
            num_connections=num_connections,
            url=agent_loop_info.url if agent_loop_info else None,
            session_api_key=getattr(agent_loop_info, "session_api_key", None),
            pr_number=conversation.pr_number,
        )
    except Exception as e:
        logger.error(
            "Error loading conversation %s: %s",
            conversation.conversation_id,
            str(e),
            extra={"session_id": conversation.conversation_id},
        )
        return None


@app.post("/conversations/{conversation_id}/start", response_model=ConversationResponse)
async def start_conversation(
    providers_set: ProvidersSetModel,
    conversation_id: str = Depends(validate_conversation_id),
    user_id: str = Depends(get_user_id),
    provider_tokens: Annotated[
        PROVIDER_TOKEN_TYPE | None, Depends(get_provider_tokens)
    ] = None,
    settings: Settings = Depends(get_user_settings),
    conversation_store: Annotated[
        Optional[Any], Depends(get_conversation_store)
    ] = None,
) -> ConversationResponse | JSONResponse:
    """Start an agent loop for a conversation.

    This endpoint calls the conversation_manager's maybe_start_agent_loop method
    to start a conversation. If the conversation is already running, it will
    return the existing agent loop info.

    The request body is optional and can contain:
    - providers_set: List of provider strings (e.g., ["github", "gitlab"])
    """
    logger.info("=== START CONVERSATION ENDPOINT CALLED ===")
    logger.info("conversation_id: %s", conversation_id)
    logger.info("user_id: %s", user_id)
    logger.info("settings loaded: %s", settings is not None)
    store = await _resolve_conversation_store(conversation_store, user_id)
    normalized_tokens = _normalize_provider_tokens(provider_tokens)
    logger.info("conversation_store loaded: %s", store is not None)
    logger.info("providers_set received: %s", providers_set.providers_set)

    # Extract providers_set from the model
    providers_list = providers_set.providers_set or []
    logger.info("Final providers_set: %s", providers_list)
    try:
        try:
            await store.get_metadata(conversation_id)
        except Exception:
            return error(
                message="Conversation not found",
                status_code=status.HTTP_404_NOT_FOUND,
                error_code="CONVERSATION_NOT_FOUND",
                conversation_id=conversation_id,
            )
        manager = _require_conversation_manager()
        conversation_init_data = await setup_init_conversation_settings(
            user_id,
            conversation_id,
            providers_list,
            normalized_tokens,
        )
        agent_loop_info = await manager.maybe_start_agent_loop(
            sid=conversation_id,
            settings=conversation_init_data,
            user_id=user_id,
        )
        return ConversationResponse(
            status="ok",
            conversation_id=conversation_id,
            conversation_status=agent_loop_info.status,
        )
    except Exception as e:
        logger.error(
            "Error starting conversation %s: %s",
            conversation_id,
            str(e),
            extra={"session_id": conversation_id},
        )
        return error(
            message=f"Failed to start conversation: {e!s}",
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            error_code="START_CONVERSATION_ERROR",
            conversation_id=conversation_id,
        )


@app.post("/conversations/{conversation_id}/stop", response_model=ConversationResponse)
async def stop_conversation(
    conversation_id: Annotated[str, Depends(validate_conversation_id)],
    user_id: Annotated[str, Depends(get_user_id)],
) -> ConversationResponse | JSONResponse:
    """Stop an agent loop for a conversation.

    This endpoint calls the conversation_manager's close_session method
    to stop a conversation.
    """
    logger.info("Stopping conversation: %s", conversation_id)
    try:
        manager = _require_conversation_manager()
        agent_loop_info = await manager.get_agent_loop_info(
            user_id=user_id,
            filter_to_sids={conversation_id},
        )
        conversation_status = (
            agent_loop_info[0].status if agent_loop_info else ConversationStatus.STOPPED
        )
        if conversation_status not in (
            ConversationStatus.STARTING,
            ConversationStatus.RUNNING,
        ):
            return ConversationResponse(
                status="ok",
                conversation_id=conversation_id,
                message="Conversation was not running",
                conversation_status=conversation_status,
            )
        await manager.close_session(conversation_id)
        return ConversationResponse(
            status="ok",
            conversation_id=conversation_id,
            message="Conversation stopped successfully",
            conversation_status=conversation_status,
        )
    except Exception as e:
        logger.error(
            "Error stopping conversation %s: %s",
            conversation_id,
            str(e),
            extra={"session_id": conversation_id},
        )
        return error(
            message=f"Failed to stop conversation: {e!s}",
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            error_code="STOP_CONVERSATION_ERROR",
            conversation_id=conversation_id,
        )


def _get_contextual_events(event_store: EventStore, event_id: int) -> str:
    """Get contextual events around a specific event ID.

    Args:
        event_store: The event store to search in.
        event_id: The event ID to get context around.

    Returns:
        str: Stringified contextual events.

    """
    context_size = 4
    agent_event_filter = EventFilter(
        exclude_hidden=True,
        exclude_types=(
            NullAction,
            NullObservation,
            ChangeAgentStateAction,
            AgentStateChangedObservation,
        ),
    )
    context_before = event_store.search_events(
        start_id=event_id,
        filter=agent_event_filter,
        reverse=True,
        limit=context_size,
    )
    context_after = event_store.search_events(
        start_id=event_id + 1, filter=agent_event_filter, limit=context_size + 1
    )
    ordered_context_before = list(context_before)
    ordered_context_before.reverse()
    all_events = itertools.chain(ordered_context_before, context_after)
    return "\n".join(str(event) for event in all_events)


class UpdateConversationRequest(BaseModel):
    """Request model for updating conversation metadata."""

    title: str = Field(
        ..., min_length=1, max_length=200, description="New conversation title"
    )
    model_config = ConfigDict(extra="forbid")


@app.patch("/conversations/{conversation_id}", response_model=bool)
async def update_conversation(
    data: UpdateConversationRequest,
    conversation_id: Annotated[str, Depends(validate_conversation_id)],
    user_id: Annotated[str | None, Depends(get_user_id)],
    conversation_store: Annotated[
        Optional[Any], Depends(get_conversation_store)
    ] = None,
) -> bool | JSONResponse:
    """Update conversation metadata.

    This endpoint allows updating conversation details like title.
    Only the conversation owner can update the conversation.

    Args:
        conversation_id: The ID of the conversation to update
        data: The conversation update data (title, etc.)
        user_id: The authenticated user ID
        conversation_store: The conversation store dependency

    Returns:
        bool: True if the conversation was updated successfully

    Raises:
        HTTPException: If conversation is not found or user lacks permission

    """
    logger.info(
        "Updating conversation %s with title: %s",
        conversation_id,
        data.title,
        extra={"session_id": conversation_id, "user_id": user_id},
    )
    store = await _resolve_conversation_store(conversation_store, user_id)
    try:
        metadata = await store.get_metadata(conversation_id)
        if user_id and metadata.user_id != user_id:
            logger.warning(
                "User %s attempted to update conversation %s owned by %s",
                user_id,
                conversation_id,
                metadata.user_id,
                extra={"session_id": conversation_id, "user_id": user_id},
            )
            return error(
                message="Permission denied: You can only update your own conversations",
                status_code=status.HTTP_403_FORBIDDEN,
                error_code="AUTHORIZATION$PERMISSION_DENIED",
            )
        original_title = metadata.title
        metadata.title = data.title.strip()
        new_timestamp = datetime.now(timezone.utc)
        if metadata.last_updated_at and new_timestamp <= metadata.last_updated_at:
            new_timestamp = metadata.last_updated_at + timedelta(microseconds=1)
        metadata.last_updated_at = new_timestamp
        await store.save_metadata(metadata)
        manager = _get_conversation_manager_instance()
        if manager is not None:
            sio = getattr(manager, "sio", None)
            if sio is not None:
                try:
                    status_update_dict = {
                        "status_update": True,
                        "type": "info",
                        "message": conversation_id,
                        "conversation_title": metadata.title,
                    }
                    await sio.emit("oh_event", status_update_dict, to=f"room:{conversation_id}")
                except Exception as e:
                    logger.error("Error emitting title update event: %s", e)
        logger.info(
            'Successfully updated conversation %s title from "%s" to "%s"',
            conversation_id,
            original_title,
            metadata.title,
            extra={"session_id": conversation_id, "user_id": user_id},
        )
        return True
    except FileNotFoundError:
        logger.warning(
            "Conversation %s not found for update",
            conversation_id,
            extra={"session_id": conversation_id, "user_id": user_id},
        )
        return error(
            message="Conversation not found",
            status_code=status.HTTP_404_NOT_FOUND,
            error_code="CONVERSATION$NOT_FOUND",
        )
    except Exception as e:
        logger.error(
            "Error updating conversation %s: %s",
            conversation_id,
            str(e),
            extra={"session_id": conversation_id, "user_id": user_id},
        )
        return error(
            message=f"Failed to update conversation: {e!s}",
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            error_code="CONVERSATION$UPDATE_ERROR",
        )


@app.post("/conversations/{conversation_id}/exp-config")
def add_experiment_config_for_conversation(
    exp_config: ExperimentConfig,
    conversation_id: Annotated[str, Depends(validate_conversation_id)],
) -> bool:
    """Add experiment configuration for a conversation.

    Args:
        exp_config: The experiment configuration to add.
        conversation_id: The conversation ID to add the config to.

    Returns:
        bool: True if the configuration was added successfully.

    """
    exp_config_filepath = get_experiment_config_filename(conversation_id)
    exists = False
    try:
        file_store.read(exp_config_filepath)
        exists = True
    except FileNotFoundError:
        pass
    if exists:
        return False
    try:
        file_store.write(exp_config_filepath, model_dump_json(exp_config))
    except Exception as e:
        logger.info("Failed to write experiment config for %s: %s", conversation_id, e)
        return True
    return False


@app.get("/microagent-management/conversations")
async def get_microagent_management_conversations(
    selected_repository: str,
    page_id: str | None = None,
    limit: int = 20,
    conversation_store: Annotated[
        Optional[Any], Depends(get_conversation_store)
    ] = None,
    provider_tokens: Annotated[
        PROVIDER_TOKEN_TYPE | None, Depends(get_provider_tokens)
    ] = None,
) -> ConversationInfoResultSet:
    """Get conversations for the microagent management page with pagination support.

    This endpoint returns conversations with conversation_trigger = 'microagent_management'
    and only includes conversations with active PRs. Pagination is supported.

    Args:
        page_id: Optional page ID for pagination
        limit: Maximum number of results per page (default: 20)
        selected_repository: Optional repository filter to limit results to a specific repository
        conversation_store: Conversation store dependency
        provider_tokens: Provider tokens for checking PR status

    """
    store = await _resolve_conversation_store(conversation_store)
    normalized_tokens = _normalize_provider_tokens(provider_tokens)
    provider_handler = ProviderHandler(
        cast(MappingProxyType[ProviderType, ProviderToken], normalized_tokens)
    )
    conversation_metadata_result_set = await store.search(page_id, limit)
    filtered_results = _filter_conversations_by_age(
        conversation_metadata_result_set.results,
        config.conversation_max_age_seconds,
    )
    final_filtered_results = []
    for conversation in filtered_results:
        if conversation.trigger != ConversationTrigger.MICROAGENT_MANAGEMENT:
            continue
        if conversation.selected_repository != selected_repository:
            continue
        if (
            conversation.pr_number
            and len(conversation.pr_number) > 0
            and conversation.selected_repository
            and conversation.git_provider
            and (
                not await provider_handler.is_pr_open(
                    conversation.selected_repository,
                    conversation.pr_number[-1],
                    conversation.git_provider,
                )
            )
        ):
            continue
        final_filtered_results.append(conversation)
    return await _build_conversation_result_set(
        final_filtered_results, conversation_metadata_result_set.next_page_id
    )
