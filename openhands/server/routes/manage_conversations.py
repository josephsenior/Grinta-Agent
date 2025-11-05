from __future__ import annotations

import asyncio
import contextlib
import itertools
import os
import re
import uuid
from datetime import datetime, timezone
from typing import TYPE_CHECKING, Annotated

from fastapi import APIRouter, Body, Depends, HTTPException, Request, status
from fastapi.responses import JSONResponse
from jinja2 import Environment, FileSystemLoader
from pydantic import BaseModel, ConfigDict, Field

from openhands.core.config.llm_config import LLMConfig
from openhands.core.logger import openhands_logger as logger
from openhands.core.pydantic_compat import model_dump_json
from openhands.events.action import ChangeAgentStateAction, NullAction
from openhands.events.event_filter import EventFilter
from openhands.events.event_store import EventStore
from openhands.events.observation import AgentStateChangedObservation, NullObservation
from openhands.integrations.provider import PROVIDER_TOKEN_TYPE, ProviderHandler
from openhands.metasop.router import run_metasop_for_conversation
from openhands.runtime import get_runtime_cls
from openhands.runtime.runtime_status import RuntimeStatus
from openhands.server.data_models.conversation_info import ConversationInfo
from openhands.server.data_models.conversation_info_result_set import (
    ConversationInfoResultSet,
)
from openhands.server.dependencies import get_dependencies
from openhands.server.services.conversation_service import (
    create_new_conversation,
    initialize_conversation,
    setup_init_conversation_settings,
)
from openhands.server.shared import (
    ConversationManagerImpl,
    ConversationStoreImpl,
    config,
    conversation_manager,
    file_store,
)
from openhands.server.types import LLMAuthenticationError, MissingSettingsError
from openhands.server.user_auth import (
    get_auth_type,
    get_provider_tokens,
    get_user_id,
    get_user_secrets,
    get_user_settings,
    get_user_settings_store,
)
from openhands.server.user_auth.user_auth import AuthType
from openhands.server.utils import get_conversation as get_conversation_metadata
from openhands.server.utils import get_conversation_store, validate_conversation_id
from openhands.storage.data_models.conversation_metadata import (
    ConversationMetadata,
    ConversationTrigger,
)
from openhands.storage.data_models.conversation_status import ConversationStatus
from openhands.storage.locations import get_experiment_config_filename
from openhands.utils.async_utils import wait_all
from openhands.utils.conversation_summary import get_default_conversation_title

# Import these at runtime for InitSessionRequest model_rebuild
from openhands.core.config.mcp_config import MCPConfig
from openhands.integrations.provider import (
    PROVIDER_TOKEN_TYPE,
    ProviderHandler,
)
from openhands.integrations.service_types import (
    CreateMicroagent,
    ProviderType,
    SuggestedTask,
)
from openhands.storage.data_models.user_secrets import UserSecrets

if TYPE_CHECKING:
    from openhands.experiments.experiment_manager import ExperimentConfig
    from openhands.server.data_models.agent_loop_info import AgentLoopInfo
    from openhands.storage.conversation.conversation_store import ConversationStore
    from openhands.storage.data_models.settings import Settings
    from openhands.storage.settings.settings_store import SettingsStore

app = APIRouter(prefix="/api", dependencies=get_dependencies())


def _filter_conversations_by_age(conversations: list[ConversationMetadata], max_age_seconds: int) -> list:
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
        age_seconds = (now - conversation.created_at.replace(tzinfo=timezone.utc)).total_seconds()
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
    conversation_ids = {conversation.conversation_id for conversation in filtered_conversations}
    connection_ids_to_conversation_ids = await conversation_manager.get_connections(filter_to_sids=conversation_ids)
    agent_loop_info = await conversation_manager.get_agent_loop_info(filter_to_sids=conversation_ids)
    agent_loop_info_by_conversation_id = {info.conversation_id: info for info in agent_loop_info}
    return ConversationInfoResultSet(
        results=await wait_all(
            _get_conversation_info(
                conversation=conversation,
                num_connections=sum(
                    conversation_id == conversation.conversation_id
                    for conversation_id in connection_ids_to_conversation_ids.values()
                ),
                agent_loop_info=agent_loop_info_by_conversation_id.get(conversation.conversation_id),
            )
            for conversation in filtered_conversations
        ),
        next_page_id=next_page_id,
    )


class InitSessionRequest(BaseModel):
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
    status: str
    conversation_id: str
    message: str | None = None
    conversation_status: ConversationStatus | None = None


class ProvidersSetModel(BaseModel):
    providers_set: list[str] | None = None


def _extract_request_data(data: InitSessionRequest) -> tuple[str, str, str, list, str, str, str, str, str]:
    """Extract and return data from the request."""
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
    suggested_task,
    create_microagent,
    auth_type: AuthType | None,
) -> tuple[ConversationTrigger, str, str]:
    """Determine conversation trigger and update repository/git_provider if needed."""
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
    """Validate remote API request requirements."""
    if conversation_trigger == ConversationTrigger.REMOTE_API_KEY and not initial_user_msg:
        return JSONResponse(
            content={
                "status": "error",
                "message": "Missing initial user message",
                "msg_id": "CONFIGURATION$MISSING_USER_MESSAGE",
            },
            status_code=status.HTTP_400_BAD_REQUEST,
        )
    return None


async def _verify_repository_access(repository: str, git_provider: str, provider_tokens) -> None:
    """Verify repository access if repository is provided."""
    if repository:
        provider_handler = ProviderHandler(provider_tokens)
        await provider_handler.verify_repo_provider(repository, git_provider)


async def _handle_metasop_conversation(
    user_id: str,
    conversation_id: str,
    repository: str,
    selected_branch: str,
    conversation_trigger: ConversationTrigger,
    git_provider: str,
    initial_user_msg: str,
) -> ConversationResponse:
    """Handle MetaSOP conversation initialization."""
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

    with contextlib.suppress(Exception):
        await conversation_manager.sio.emit(
            "oh_event",
            {"status_update": True, "type": "info", "message": "Starting MetaSOP orchestration…"},
            to=f"room:{conversation_id}",
        )

    asyncio.create_task(
        run_metasop_for_conversation(
            conversation_id=conversation_id,
            user_id=user_id,
            raw_message=initial_user_msg,
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
    repository: str,
    selected_branch: str,
    initial_user_msg: str,
    image_urls: list,
    replay_json: str,
    conversation_trigger: ConversationTrigger,
    conversation_instructions: str,
    git_provider: str,
    provider_tokens,
    user_secrets: UserSecrets,
    mcp_config,
) -> ConversationResponse:
    """Handle regular conversation initialization."""
    agent_loop_info = await create_new_conversation(
        user_id=user_id,
        git_provider_tokens=provider_tokens,
        custom_secrets=user_secrets.custom_secrets if user_secrets else None,
        selected_repository=repository,
        selected_branch=selected_branch,
        initial_user_msg=initial_user_msg,
        image_urls=image_urls,
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
    """Handle conversation creation errors."""
    if isinstance(e, MissingSettingsError):
        return JSONResponse(
            content={"status": "error", "message": str(e), "msg_id": "CONFIGURATION$SETTINGS_NOT_FOUND"},
            status_code=status.HTTP_400_BAD_REQUEST,
        )
    if isinstance(e, LLMAuthenticationError):
        return JSONResponse(
            content={"status": "error", "message": str(e), "msg_id": RuntimeStatus.ERROR_LLM_AUTHENTICATION.value},
            status_code=status.HTTP_400_BAD_REQUEST,
        )
    raise e


@app.post("/conversations")
async def new_conversation(
    data: InitSessionRequest,
    user_id: Annotated[str | None, Depends(get_user_id)] = None,
    provider_tokens: Annotated[PROVIDER_TOKEN_TYPE | None, Depends(get_provider_tokens)] = None,
    user_secrets: Annotated[UserSecrets | None, Depends(get_user_secrets)] = None,
    auth_type: Annotated[AuthType | None, Depends(get_auth_type)] = None,
) -> ConversationResponse:
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

    conversation_trigger, override_repo, override_git_provider = _determine_conversation_trigger(
        suggested_task,
        create_microagent,
        auth_type,
    )

    if override_repo:
        repository = override_repo
    if override_git_provider:
        git_provider = override_git_provider

    if suggested_task:
        initial_user_msg = suggested_task.get_prompt_for_task()

    if error_response := _validate_remote_api_request(conversation_trigger, initial_user_msg or ""):
        return error_response

    provider_tokens = provider_tokens or {}
    user_secrets = user_secrets or UserSecrets()
    user_id = user_id or "dev-user"

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
    return JSONResponse(content={"status": "test_working", "message": "conversations endpoint is accessible"})

@app.get("/conversations/simple")
async def simple_conversations_endpoint() -> dict:
    """Simple endpoint without dependencies to test routing."""
    return {"status": "simple_working", "count": 1}

@app.get("/conversations")
async def search_conversations(
    request: Request,
    page_id: str | None = None,
    limit: int = 20,
    selected_repository: str | None = None,
    conversation_trigger: ConversationTrigger | None = None,
    user_id: Annotated[str | None, Depends(get_user_id)] = None,
    conversation_store: ConversationStore = Depends(get_conversation_store),
) -> ConversationInfoResultSet:
    """Search and filter conversations with pagination.
    
    Filters by age, repository, and trigger type.
    
    Args:
        page_id: Page cursor for pagination
        limit: Maximum results per page
        selected_repository: Filter by repository
        conversation_trigger: Filter by trigger type
        conversation_store: Conversation storage dependency
        
    Returns:
        Filtered conversation results with next page cursor
    """
    logger.info(f"search_conversations called with: page_id={page_id}, limit={limit}, user_id={user_id}")
    
    # Return empty list for development
    # return ConversationInfoResultSet(results=[], next_page_id=None)
    
    conversation_metadata_result_set = await conversation_store.search(page_id, limit)
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
        if selected_repository is not None and conversation.selected_repository != selected_repository:
            continue
        if conversation_trigger is not None and conversation.trigger != conversation_trigger:
            continue
        final_filtered_results.append(conversation)
    return await _build_conversation_result_set(final_filtered_results, conversation_metadata_result_set.next_page_id)


@app.get("/conversations/{conversation_id}")
async def get_conversation(
    conversation_id: Annotated[str, Depends(validate_conversation_id)],
    user_id: Annotated[str | None, Depends(get_user_id)],
) -> ConversationInfo | None:
    """Get detailed information about a specific conversation.
    
    Args:
        conversation_id: Conversation identifier
        user_id: User identifier from authentication
        
    Returns:
        Conversation info including metadata and agent state, or None if not found
    """
    # Load conversation metadata from storage
    conversation_store = await ConversationStoreImpl.get_instance(config, user_id)
    conversation = await conversation_store.get_metadata(conversation_id)
    if not conversation:
        return None
    
    agent_loop_info_list = await conversation_manager.get_agent_loop_info(filter_to_sids={conversation_id})
    logger.info(f"get_conversation: conversation_id={conversation_id}, agent_loop_info_list={agent_loop_info_list}")
    agent_loop_info = agent_loop_info_list[0] if agent_loop_info_list else None
    logger.info(f"get_conversation: agent_loop_info={agent_loop_info}")
    connections = await conversation_manager.get_connections(conversation_id)
    num_connections = len(connections) if connections else 0
    
    return await _get_conversation_info(conversation, num_connections, agent_loop_info)


@app.delete("/conversations/{conversation_id}")
async def delete_conversation(
    conversation_id: Annotated[str, Depends(validate_conversation_id)],
    user_id: Annotated[str | None, Depends(get_user_id)],
) -> bool:
    """Delete a conversation and its associated resources.
    
    Closes active sessions and deletes runtime and metadata.
    
    Args:
        conversation_id: Conversation identifier
        user_id: User identifier
        
    Returns:
        True if deleted successfully, False if not found
    """
    conversation_store = await ConversationStoreImpl.get_instance(config, user_id)
    try:
        await conversation_store.get_metadata(conversation_id)
    except FileNotFoundError:
        return False
    is_running = await conversation_manager.is_agent_loop_running(conversation_id)
    if is_running:
        await conversation_manager.close_session(conversation_id)
    runtime_cls = get_runtime_cls(config.runtime)
    await runtime_cls.delete(conversation_id)
    await conversation_store.delete_metadata(conversation_id)
    return True


@app.get("/conversations/{conversation_id}/remember-prompt")
async def get_prompt(
    event_id: int,
    conversation_id: Annotated[str, Depends(validate_conversation_id)],
    user_settings: Annotated[SettingsStore, Depends(get_user_settings_store)],
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
    event_store = EventStore(sid=conversation_id, file_store=file_store, user_id=metadata.user_id)
    stringified_events = _get_contextual_events(event_store, event_id)
    settings = await user_settings.load()
    if settings is None:
        msg = "Settings not found"
        raise ValueError(msg)
    llm_config = LLMConfig(model=settings.llm_model or "", api_key=settings.llm_api_key, base_url=settings.llm_base_url)
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
    env = Environment(loader=FileSystemLoader("openhands/microagent/prompts"), autoescape=True)
    template = env.get_template("generate_remember_prompt.j2")
    return template.render(events=events)


def generate_prompt(llm_config: LLMConfig, prompt_template: str, conversation_id: str) -> str:
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
    raw_prompt = ConversationManagerImpl.request_llm_completion(
        "remember_prompt",
        conversation_id,
        llm_config,
        messages,
    )
    if prompt := re.search("<update_prompt>(.*?)</update_prompt>", raw_prompt, re.DOTALL):
        return prompt[1].strip()
    msg = "No valid prompt found in the response."
    raise ValueError(msg)


async def _get_conversation_info(
    conversation: ConversationMetadata,
    num_connections: int,
    agent_loop_info: AgentLoopInfo | None,
) -> ConversationInfo | None:
    try:
        title = conversation.title or get_default_conversation_title(conversation.conversation_id)
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


class ProvidersSetModel(BaseModel):
    providers_set: list[str] | None = None

@app.post("/conversations/{conversation_id}/start")
async def start_conversation(
    providers_set: ProvidersSetModel,
    conversation_id: str = Depends(validate_conversation_id),
    user_id: str = Depends(get_user_id),
    provider_tokens: PROVIDER_TOKEN_TYPE = Depends(get_provider_tokens),
    settings: Settings = Depends(get_user_settings),
    conversation_store: ConversationStore = Depends(get_conversation_store),
) -> ConversationResponse:
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
    logger.info("conversation_store loaded: %s", conversation_store is not None)
    logger.info("providers_set received: %s", providers_set.providers_set)
    
    # Extract providers_set from the model
    providers_list = providers_set.providers_set or []
    logger.info("Final providers_set: %s", providers_list)
    try:
        try:
            await conversation_store.get_metadata(conversation_id)
        except Exception:
            return JSONResponse(
                content={"status": "error", "conversation_id": conversation_id},
                status_code=status.HTTP_404_NOT_FOUND,
            )
        conversation_init_data = await setup_init_conversation_settings(
            user_id,
            conversation_id,
            providers_list,
            provider_tokens,
        )
        agent_loop_info = await conversation_manager.maybe_start_agent_loop(
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
        return JSONResponse(
            content={
                "status": "error",
                "conversation_id": conversation_id,
                "message": f"Failed to start conversation: {
                    e!s}",
            },
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )


@app.post("/conversations/{conversation_id}/stop")
async def stop_conversation(
    conversation_id: Annotated[str, Depends(validate_conversation_id)],
    user_id: Annotated[str, Depends(get_user_id)],
) -> ConversationResponse:
    """Stop an agent loop for a conversation.

    This endpoint calls the conversation_manager's close_session method
    to stop a conversation.
    """
    logger.info("Stopping conversation: %s", conversation_id)
    try:
        agent_loop_info = await conversation_manager.get_agent_loop_info(
            user_id=user_id,
            filter_to_sids={conversation_id},
        )
        conversation_status = agent_loop_info[0].status if agent_loop_info else ConversationStatus.STOPPED
        if conversation_status not in (ConversationStatus.STARTING, ConversationStatus.RUNNING):
            return ConversationResponse(
                status="ok",
                conversation_id=conversation_id,
                message="Conversation was not running",
                conversation_status=conversation_status,
            )
        await conversation_manager.close_session(conversation_id)
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
        return JSONResponse(
            content={
                "status": "error",
                "conversation_id": conversation_id,
                "message": f"Failed to stop conversation: {
                    e!s}",
            },
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
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
        exclude_types=(NullAction, NullObservation, ChangeAgentStateAction, AgentStateChangedObservation),
    )
    context_before = event_store.search_events(
        start_id=event_id,
        filter=agent_event_filter,
        reverse=True,
        limit=context_size,
    )
    context_after = event_store.search_events(start_id=event_id + 1, filter=agent_event_filter, limit=context_size + 1)
    ordered_context_before = list(context_before)
    ordered_context_before.reverse()
    all_events = itertools.chain(ordered_context_before, context_after)
    return "\n".join(str(event) for event in all_events)


class UpdateConversationRequest(BaseModel):
    """Request model for updating conversation metadata."""

    title: str = Field(..., min_length=1, max_length=200, description="New conversation title")
    model_config = ConfigDict(extra="forbid")


@app.patch("/conversations/{conversation_id}")
async def update_conversation(
    data: UpdateConversationRequest,
    conversation_id: Annotated[str, Depends(validate_conversation_id)],
    user_id: Annotated[str | None, Depends(get_user_id)],
    conversation_store: Annotated[ConversationStore, Depends(get_conversation_store)],
) -> bool:
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
    try:
        metadata = await conversation_store.get_metadata(conversation_id)
        if user_id and metadata.user_id != user_id:
            logger.warning(
                "User %s attempted to update conversation %s owned by %s",
                user_id,
                conversation_id,
                metadata.user_id,
                extra={"session_id": conversation_id, "user_id": user_id},
            )
            return JSONResponse(
                content={
                    "status": "error",
                    "message": "Permission denied: You can only update your own conversations",
                    "msg_id": "AUTHORIZATION$PERMISSION_DENIED",
                },
                status_code=status.HTTP_403_FORBIDDEN,
            )
        original_title = metadata.title
        metadata.title = data.title.strip()
        metadata.last_updated_at = datetime.now(timezone.utc)
        await conversation_store.save_metadata(metadata)
        try:
            status_update_dict = {
                "status_update": True,
                "type": "info",
                "message": conversation_id,
                "conversation_title": metadata.title,
            }
            await conversation_manager.sio.emit("oh_event", status_update_dict, to=f"room:{conversation_id}")
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
        return JSONResponse(
            content={"status": "error", "message": "Conversation not found", "msg_id": "CONVERSATION$NOT_FOUND"},
            status_code=status.HTTP_404_NOT_FOUND,
        )
    except Exception as e:
        logger.error(
            "Error updating conversation %s: %s",
            conversation_id,
            str(e),
            extra={"session_id": conversation_id, "user_id": user_id},
        )
        return JSONResponse(
            content={
                "status": "error",
                "message": f"Failed to update conversation: {
                    e!s}",
                "msg_id": "CONVERSATION$UPDATE_ERROR",
            },
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
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
    conversation_store: ConversationStore = Depends(get_conversation_store),
    provider_tokens: PROVIDER_TOKEN_TYPE = Depends(get_provider_tokens),
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
    conversation_metadata_result_set = await conversation_store.search(page_id, limit)
    filtered_results = _filter_conversations_by_age(
        conversation_metadata_result_set.results,
        config.conversation_max_age_seconds,
    )
    provider_handler = ProviderHandler(provider_tokens)
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
    return await _build_conversation_result_set(final_filtered_results, conversation_metadata_result_set.next_page_id)
