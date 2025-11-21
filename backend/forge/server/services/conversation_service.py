"""Service helpers for initializing conversations and orchestrating agent sessions."""

from __future__ import annotations

import uuid
from types import MappingProxyType
from typing import TYPE_CHECKING, Any, Sequence

from forge.core.config.api_key_manager import api_key_manager
from forge.core.logger import forge_logger as logger
from forge.events.action.message import MessageAction
from forge.experiments.experiment_manager import ExperimentManagerImpl
from forge.integrations.provider import (
    CUSTOM_SECRETS_TYPE_WITH_JSON_SCHEMA,
    PROVIDER_TOKEN_TYPE,
    ProviderToken,
)
from forge.integrations.service_types import ProviderType
from forge.server.session.conversation_init_data import ConversationInitData
from forge.server.shared import (
    ConversationStoreImpl,
    SecretsStoreImpl,
    SettingsStoreImpl,
    config,
    conversation_manager,
    get_conversation_manager,
    server_config,
)
from forge.server.types import AppMode, LLMAuthenticationError, MissingSettingsError
from forge.storage.data_models.conversation_metadata import (
    ConversationMetadata,
    ConversationTrigger,
)
from forge.utils.conversation_summary import get_default_conversation_title

if TYPE_CHECKING:
    from forge.core.config.mcp_config import MCPConfig
    from forge.server.data_models.agent_loop_info import AgentLoopInfo
    from forge.storage.data_models.user_secrets import UserSecrets


async def initialize_conversation(
    user_id: str | None,
    conversation_id: str | None,
    selected_repository: str | None,
    selected_branch: str | None,
    conversation_trigger: ConversationTrigger = ConversationTrigger.GUI,
    git_provider: ProviderType | None = None,
) -> ConversationMetadata | None:
    """Initialize a new conversation or retrieve existing one.

    Creates metadata for new conversations with generated IDs and titles.

    Args:
        user_id: User identifier
        conversation_id: Conversation ID (generates new if None)
        selected_repository: Repository for conversation
        selected_branch: Branch for conversation
        conversation_trigger: How conversation was triggered
        git_provider: Git provider type

    Returns:
        Conversation metadata or None if retrieval fails

    """
    if conversation_id is None:
        conversation_id = uuid.uuid4().hex
    conversation_store = await ConversationStoreImpl.get_instance(config, user_id)
    if not await conversation_store.exists(conversation_id):
        logger.info(
            "New conversation ID: %s",
            conversation_id,
            extra={"user_id": user_id, "session_id": conversation_id},
        )
        conversation_title = get_default_conversation_title(conversation_id)
        logger.info("Saving metadata for conversation %s", conversation_id)
        conversation_metadata = ConversationMetadata(
            trigger=conversation_trigger,
            conversation_id=conversation_id,
            title=conversation_title,
            user_id=user_id,
            selected_repository=selected_repository,
            selected_branch=selected_branch,
            git_provider=git_provider,
        )
        await conversation_store.save_metadata(conversation_metadata)
        return conversation_metadata
    try:
        return await conversation_store.get_metadata(conversation_id)
    except Exception:
        pass
    return None


def _validate_api_key_for_model(settings: Any, model_name: str) -> None:
    """Validate API key requirements for the given model.

    Args:
        settings: User settings containing API key
        model_name: Name of the LLM model

    Raises:
        LLMAuthenticationError: If API key validation fails

    """
    is_bedrock_model = model_name.startswith("bedrock/")
    is_lemonade_model = model_name.startswith("lemonade/")

    # DEBUG: Log the actual state of the API key
    logger.info(f"[AUTH CHECK] Model: {model_name}")
    logger.info(
        f"[AUTH CHECK] Bedrock model: {is_bedrock_model}, Lemonade model: {is_lemonade_model}"
    )
    logger.info(f"[AUTH CHECK] API key exists: {settings.llm_api_key is not None}")

    if settings.llm_api_key:
        key_value = settings.llm_api_key.get_secret_value()
        logger.info(f"[AUTH CHECK] API key value exists: {key_value is not None}")
        logger.info(
            f"[AUTH CHECK] API key length: {len(key_value) if key_value else 0}"
        )
        logger.info(
            f"[AUTH CHECK] API key is whitespace: {key_value.isspace() if key_value else 'N/A'}"
        )
        logger.info(
            f"[AUTH CHECK] API key prefix: {key_value[:10] if key_value else 'EMPTY'}..."
        )

    # Models that don't require API keys
    if is_bedrock_model or is_lemonade_model:
        logger.info(f"Model {model_name} does not require API key")
        return

    # Validate API key presence and non-emptiness
    if not settings.llm_api_key or settings.llm_api_key.get_secret_value().isspace():
        logger.warning(f"Missing api key for model {model_name}")
        raise LLMAuthenticationError(
            "Error authenticating with the LLM provider. Please check your API key"
        )

    logger.info(f"[AUTH CHECK] ✅ API key validation PASSED for model: {model_name}")


def _process_git_provider_tokens(
    git_provider_tokens: PROVIDER_TOKEN_TYPE | None,
) -> PROVIDER_TOKEN_TYPE:
    """Process and normalize git provider tokens.

    Args:
        git_provider_tokens: Raw provider tokens (dict, MappingProxy, or None)

    Returns:
        Normalized provider tokens as MappingProxyType

    """
    from forge.storage.data_models.user_secrets import UserSecrets

    if not git_provider_tokens:
        return MappingProxyType({})

    if isinstance(git_provider_tokens, dict):
        return MappingProxyType(git_provider_tokens)

    return git_provider_tokens


def _process_custom_secrets(
    custom_secrets: CUSTOM_SECRETS_TYPE_WITH_JSON_SCHEMA | Any | None,
) -> MappingProxyType:
    """Process and normalize custom secrets.

    Args:
        custom_secrets: Raw custom secrets (UserSecrets, dict, or None)

    Returns:
        Normalized custom secrets as MappingProxyType

    """
    from forge.storage.data_models.user_secrets import UserSecrets

    if not custom_secrets:
        return MappingProxyType({})

    if isinstance(custom_secrets, UserSecrets):
        # UserSecrets.custom_secrets is already a MappingProxyType
        secrets_dict = custom_secrets.custom_secrets
        return MappingProxyType(dict(secrets_dict))

    if isinstance(custom_secrets, dict):
        return MappingProxyType(custom_secrets)

    # If it's already a MappingProxyType, return it
    if isinstance(custom_secrets, MappingProxyType):
        return custom_secrets

    # Fallback: wrap in MappingProxyType
    return MappingProxyType({})


def _normalize_provider_list(providers_set: Sequence[ProviderType | str] | None) -> list[ProviderType]:
    """Normalize provider list to ProviderType enum."""
    normalized_providers: list[ProviderType] = []
    for provider in providers_set or []:
        if isinstance(provider, ProviderType):
            normalized_providers.append(provider)
        else:
            try:
                normalized_providers.append(ProviderType(provider))
            except Exception:
                continue
    return normalized_providers


def _get_normalized_provider_tokens(
    provider_tokens: PROVIDER_TOKEN_TYPE | None,
    default_tokens: PROVIDER_TOKEN_TYPE | None
) -> PROVIDER_TOKEN_TYPE | None:
    """Get normalized provider tokens, falling back to defaults if needed."""
    normalized = _process_git_provider_tokens(provider_tokens)
    return normalized if normalized else default_tokens


def _ensure_provider_tokens_for_providers(
    normalized_tokens: PROVIDER_TOKEN_TYPE | None,
    providers_set: Sequence[ProviderType | str] | None,
    user_id: str | None
) -> PROVIDER_TOKEN_TYPE:
    """Ensure tokens exist for all requested providers."""
    normalized_providers = _normalize_provider_list(providers_set)
    if not normalized_providers:
        return normalized_tokens or MappingProxyType({})
    
    token_dict = dict(normalized_tokens) if normalized_tokens is not None else {}
    for provider in normalized_providers:
        token_dict.setdefault(provider, ProviderToken(token=None, user_id=user_id))
    return MappingProxyType(token_dict)


def _build_session_init_args(
    settings: Any,
    conversation_metadata: ConversationMetadata,
    git_provider_tokens: PROVIDER_TOKEN_TYPE | None,
    custom_secrets: CUSTOM_SECRETS_TYPE_WITH_JSON_SCHEMA | None,
    conversation_instructions: str | None,
    mcp_config: MCPConfig | None,
) -> dict[str, Any]:
    """Build session initialization arguments from various sources.

    Args:
        settings: User settings
        conversation_metadata: Conversation metadata
        git_provider_tokens: Provider tokens
        custom_secrets: Custom secrets
        conversation_instructions: Custom instructions
        mcp_config: MCP configuration

    Returns:
        Dictionary of session initialization arguments

    """
    session_init_args: dict[str, Any] = {**settings.__dict__}

    # Add provider tokens and secrets
    session_init_args["git_provider_tokens"] = _process_git_provider_tokens(
        git_provider_tokens
    )
    session_init_args["custom_secrets"] = _process_custom_secrets(custom_secrets)

    # Add conversation metadata
    session_init_args["selected_repository"] = conversation_metadata.selected_repository
    session_init_args["selected_branch"] = conversation_metadata.selected_branch
    session_init_args["git_provider"] = conversation_metadata.git_provider
    session_init_args["conversation_instructions"] = conversation_instructions

    # Add optional MCP config
    if mcp_config:
        session_init_args["mcp_config"] = mcp_config

    return session_init_args


def _create_initial_message_action(
    initial_user_msg: str | None,
    image_urls: list[str] | None,
) -> MessageAction | None:
    """Create initial message action if user message or images provided.

    Args:
        initial_user_msg: Initial user message
        image_urls: Initial image URLs

    Returns:
        MessageAction or None if no message or images

    """
    if not initial_user_msg and not image_urls:
        return None

    return MessageAction(content=initial_user_msg or "", image_urls=image_urls or [])


async def start_conversation(
    user_id: str | None,
    git_provider_tokens: PROVIDER_TOKEN_TYPE | None,
    custom_secrets: CUSTOM_SECRETS_TYPE_WITH_JSON_SCHEMA | None,
    initial_user_msg: str | None,
    image_urls: list[str] | None,
    replay_json: str | None,
    conversation_id: str,
    conversation_metadata: ConversationMetadata,
    conversation_instructions: str | None,
    mcp_config: MCPConfig | None = None,
) -> AgentLoopInfo:
    """Start an agent loop for a conversation with user settings and init data.

    Loads user settings, validates API keys, initializes conversation data,
    and starts the agent loop.

    Args:
        user_id: User identifier
        git_provider_tokens: Git provider authentication tokens
        custom_secrets: Custom user secrets
        initial_user_msg: Initial message from user
        image_urls: Initial image URLs
        replay_json: JSON for replaying conversation
        conversation_id: Conversation identifier
        conversation_metadata: Conversation metadata
        conversation_instructions: Custom instructions for conversation
        mcp_config: MCP configuration

    Returns:
        Agent loop information

    Raises:
        LLMAuthenticationError: If LLM API key invalid
        MissingSettingsError: If user settings not found

    """
    logger.info(
        "Creating conversation",
        extra={
            "signal": "create_conversation",
            "user_id": user_id,
            "trigger": conversation_metadata.trigger,
        },
    )

    # Load and validate settings
    logger.info("Loading settings")
    settings_store = await SettingsStoreImpl.get_instance(config, user_id)
    settings = await settings_store.load()
    logger.info("Settings loaded")

    if not settings:
        logger.warning("Settings not present, not starting conversation")
        raise MissingSettingsError("Settings not found")

    # Validate API key for the selected model
    model_name = settings.llm_model or ""
    _validate_api_key_for_model(settings, model_name)

    # Build session initialization arguments
    session_init_args = _build_session_init_args(
        settings,
        conversation_metadata,
        git_provider_tokens,
        custom_secrets,
        conversation_instructions,
        mcp_config,
    )

    # Create conversation init data and run experiments
    conversation_init_data = ConversationInitData(**session_init_args)
    conversation_init_data = ExperimentManagerImpl.run_conversation_variant_test(
        user_id,
        conversation_id,
        conversation_init_data,
    )

    # Start agent loop
    logger.info(
        "Starting agent loop for conversation %s",
        conversation_id,
        extra={"user_id": user_id, "session_id": conversation_id},
    )

    initial_message_action = _create_initial_message_action(
        initial_user_msg, image_urls
    )

    manager = conversation_manager or get_conversation_manager()
    if manager is None:
        raise RuntimeError("Conversation manager is not initialized")
    agent_loop_info = await manager.maybe_start_agent_loop(
        conversation_id,
        conversation_init_data,
        user_id,
        initial_user_msg=initial_message_action,
        replay_json=replay_json,
    )

    logger.info(
        "Finished initializing conversation %s", agent_loop_info.conversation_id
    )
    return agent_loop_info


async def create_new_conversation(
    user_id: str | None,
    git_provider_tokens: PROVIDER_TOKEN_TYPE | None,
    custom_secrets: CUSTOM_SECRETS_TYPE_WITH_JSON_SCHEMA | None,
    selected_repository: str | None,
    selected_branch: str | None,
    initial_user_msg: str | None,
    image_urls: list[str] | None,
    replay_json: str | None,
    conversation_instructions: str | None = None,
    conversation_trigger: ConversationTrigger = ConversationTrigger.GUI,
    git_provider: ProviderType | None = None,
    conversation_id: str | None = None,
    mcp_config: MCPConfig | None = None,
) -> AgentLoopInfo:
    """Create and start a new conversation end-to-end.

    Initializes conversation metadata and starts agent loop in one operation.

    Args:
        user_id: User identifier
        git_provider_tokens: Git provider tokens
        custom_secrets: Custom secrets
        selected_repository: Repository for conversation
        selected_branch: Branch for conversation
        initial_user_msg: Initial message
        image_urls: Initial images
        replay_json: Replay data
        conversation_instructions: Custom instructions
        conversation_trigger: How conversation was triggered
        git_provider: Git provider type
        conversation_id: Optional conversation ID
        mcp_config: MCP configuration

    Returns:
        Agent loop information

    Raises:
        ValueError: If conversation initialization fails

    """
    conversation_metadata = await initialize_conversation(
        user_id,
        conversation_id,
        selected_repository,
        selected_branch,
        conversation_trigger,
        git_provider,
    )
    if not conversation_metadata:
        msg = "Failed to initialize conversation"
        raise RuntimeError(msg)
    return await start_conversation(
        user_id,
        git_provider_tokens,
        custom_secrets,
        initial_user_msg,
        image_urls,
        replay_json,
        conversation_metadata.conversation_id,
        conversation_metadata,
        conversation_instructions,
        mcp_config,
    )


def create_provider_tokens_object(
    providers_set: list[ProviderType],
) -> PROVIDER_TOKEN_TYPE:
    """Create provider tokens object for the given providers."""
    provider_information: dict[ProviderType, ProviderToken] = {
        provider: ProviderToken(token=None, user_id=None) for provider in providers_set
    }
    return MappingProxyType(provider_information)


async def setup_init_conversation_settings(
    user_id: str | None,
    conversation_id: str,
    providers_set: Sequence[ProviderType | str] | None = None,
    provider_tokens: PROVIDER_TOKEN_TYPE | None = None,
) -> ConversationInitData:
    """Prepare conversation settings for joining an existing session.

    Args:
        user_id: Authenticated user identifier.
        conversation_id: The conversation identifier to join.
        providers_set: Optional list of providers requiring token placeholders.
        provider_tokens: Optional provider tokens supplied by caller.

    Returns:
        ConversationInitData containing session settings.

    Raises:
        MissingSettingsError: If user settings cannot be loaded.
        RuntimeError: If conversation metadata is unavailable.
    """
    conversation_store = await ConversationStoreImpl.get_instance(config, user_id)
    conversation_metadata = await conversation_store.get_metadata(conversation_id)
    if not conversation_metadata:
        raise RuntimeError(f"Conversation metadata not found for {conversation_id}")

    settings_store = await SettingsStoreImpl.get_instance(config, user_id)
    settings = await settings_store.load()
    if settings is None:
        raise MissingSettingsError("Settings not found")

    normalized_tokens = _get_normalized_provider_tokens(
        provider_tokens, settings.secrets_store.provider_tokens
    )
    normalized_tokens = _ensure_provider_tokens_for_providers(
        normalized_tokens, providers_set, user_id
    )

    session_init_args = _build_session_init_args(
        settings,
        conversation_metadata,
        normalized_tokens,
        settings.secrets_store.custom_secrets,
        conversation_instructions=None,
        mcp_config=settings.mcp_config,
    )
    return ConversationInitData(**session_init_args)
