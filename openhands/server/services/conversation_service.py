from __future__ import annotations

import uuid
from types import MappingProxyType
from typing import TYPE_CHECKING, Any

from openhands.core.config.api_key_manager import api_key_manager
from openhands.core.logger import openhands_logger as logger
from openhands.events.action.message import MessageAction
from openhands.experiments.experiment_manager import ExperimentManagerImpl
from openhands.integrations.provider import (
    CUSTOM_SECRETS_TYPE_WITH_JSON_SCHEMA,
    PROVIDER_TOKEN_TYPE,
    ProviderToken,
)
from openhands.server.session.conversation_init_data import ConversationInitData
from openhands.server.shared import (
    ConversationStoreImpl,
    SecretsStoreImpl,
    SettingsStoreImpl,
    config,
    conversation_manager,
    server_config,
)
from openhands.server.types import AppMode, LLMAuthenticationError, MissingSettingsError
from openhands.storage.data_models.conversation_metadata import (
    ConversationMetadata,
    ConversationTrigger,
)
from openhands.utils.conversation_summary import get_default_conversation_title

if TYPE_CHECKING:
    from openhands.core.config.mcp_config import MCPConfig
    from openhands.integrations.service_types import ProviderType
    from openhands.server.data_models.agent_loop_info import AgentLoopInfo
    from openhands.storage.data_models.user_secrets import UserSecrets


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
        extra={"signal": "create_conversation", "user_id": user_id, "trigger": conversation_metadata.trigger},
    )
    logger.info("Loading settings")
    settings_store = await SettingsStoreImpl.get_instance(config, user_id)
    settings = await settings_store.load()
    logger.info("Settings loaded")
    session_init_args: dict[str, Any] = {}
    if settings:
        session_init_args = {**settings.__dict__, **session_init_args}
        
        # Simple API key validation like the original OpenHands
        model_name = settings.llm_model or ''
        is_bedrock_model = model_name.startswith('bedrock/')
        is_lemonade_model = model_name.startswith('lemonade/')
        
        # DEBUG: Log the actual state of the API key
        logger.info(f'[AUTH CHECK] Model: {model_name}')
        logger.info(f'[AUTH CHECK] Bedrock model: {is_bedrock_model}, Lemonade model: {is_lemonade_model}')
        logger.info(f'[AUTH CHECK] API key exists: {settings.llm_api_key is not None}')
        if settings.llm_api_key:
            key_value = settings.llm_api_key.get_secret_value()
            logger.info(f'[AUTH CHECK] API key value exists: {key_value is not None}')
            logger.info(f'[AUTH CHECK] API key length: {len(key_value) if key_value else 0}')
            logger.info(f'[AUTH CHECK] API key is whitespace: {key_value.isspace() if key_value else "N/A"}')
            logger.info(f'[AUTH CHECK] API key prefix: {key_value[:10] if key_value else "EMPTY"}...')

        if (
            not is_bedrock_model
            and not is_lemonade_model
            and (
                not settings.llm_api_key
                or settings.llm_api_key.get_secret_value().isspace()
            )
        ):
            logger.warning(f'Missing api key for model {settings.llm_model}')
            raise LLMAuthenticationError(
                'Error authenticating with the LLM provider. Please check your API key'
            )
        elif is_bedrock_model:
            logger.info(f'Bedrock model detected ({model_name}), API key not required')
        
        logger.info(f'[AUTH CHECK] ✅ API key validation PASSED for model: {model_name}')
    else:
        logger.warning("Settings not present, not starting conversation")
        msg = "Settings not found"
        raise MissingSettingsError(msg)
    # Convert to mappingproxy if needed (ConversationInitData expects immutable mappings)
    from types import MappingProxyType
    from openhands.storage.data_models.user_secrets import UserSecrets
    
    # Handle git_provider_tokens
    if git_provider_tokens is not None and git_provider_tokens:
        # If it's from UserSecrets, extract provider_tokens; otherwise convert dict
        if isinstance(git_provider_tokens, dict):
            session_init_args["git_provider_tokens"] = MappingProxyType(git_provider_tokens)
        else:
            session_init_args["git_provider_tokens"] = git_provider_tokens
    else:
        session_init_args["git_provider_tokens"] = MappingProxyType({})
    
    session_init_args["selected_repository"] = conversation_metadata.selected_repository
    
    # Handle custom_secrets
    if custom_secrets is not None:
        # Extract the mappingproxy from UserSecrets if that's what we have
        if isinstance(custom_secrets, UserSecrets):
            session_init_args["custom_secrets"] = custom_secrets.custom_secrets
        elif isinstance(custom_secrets, dict):
            session_init_args["custom_secrets"] = MappingProxyType(custom_secrets)
        else:
            session_init_args["custom_secrets"] = custom_secrets
    else:
        session_init_args["custom_secrets"] = MappingProxyType({})
    session_init_args["selected_branch"] = conversation_metadata.selected_branch
    session_init_args["git_provider"] = conversation_metadata.git_provider
    session_init_args["conversation_instructions"] = conversation_instructions
    if mcp_config:
        session_init_args["mcp_config"] = mcp_config
    conversation_init_data = ConversationInitData(**session_init_args)
    conversation_init_data = ExperimentManagerImpl.run_conversation_variant_test(
        user_id,
        conversation_id,
        conversation_init_data,
    )
    logger.info(
        "Starting agent loop for conversation %s",
        conversation_id,
        extra={"user_id": user_id, "session_id": conversation_id},
    )
    initial_message_action = None
    if initial_user_msg or image_urls:
        initial_message_action = MessageAction(content=initial_user_msg or "", image_urls=image_urls or [])
    agent_loop_info = await conversation_manager.maybe_start_agent_loop(
        conversation_id,
        conversation_init_data,
        user_id,
        initial_user_msg=initial_message_action,
        replay_json=replay_json,
    )
    logger.info("Finished initializing conversation %s", agent_loop_info.conversation_id)
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


def create_provider_tokens_object(providers_set: list[ProviderType]) -> PROVIDER_TOKEN_TYPE:
    """Create provider tokens object for the given providers."""
    provider_information: dict[ProviderType, ProviderToken] = {
        provider: ProviderToken(token=None, user_id=None) for provider in providers_set
    }
    return MappingProxyType(provider_information)


async def setup_init_conversation_settings(
    user_id: str | None,
    conversation_id: str,
    providers_set: list[ProviderType],
    provider_tokens: PROVIDER_TOKEN_TYPE | None = None,
) -> ConversationInitData:
    """Set up conversation initialization data with provider tokens.

    Args:
        user_id: The user ID
        conversation_id: The conversation ID
        providers_set: List of provider types to set up tokens for

    Returns:
        ConversationInitData with provider tokens configured
    """
    settings_store = await SettingsStoreImpl.get_instance(config, user_id)
    settings = await settings_store.load()
    secrets_store = await SecretsStoreImpl.get_instance(config, user_id)
    user_secrets: UserSecrets | None = await secrets_store.load()
    if not settings:
        from socketio.exceptions import ConnectionRefusedError

        msg = "Settings not found"
        raise ConnectionRefusedError(msg, {"msg_id": "CONFIGURATION$SETTINGS_NOT_FOUND"})
    session_init_args: dict = {}
    session_init_args = {**settings.__dict__, **session_init_args}

    # Use provided tokens if available (for SAAS resume), otherwise create scaffold
    if provider_tokens:
        logger.info(
            f'Using provided provider_tokens: {list(provider_tokens.keys())}',
            extra={'session_id': conversation_id},
        )
        git_provider_tokens = provider_tokens
    else:
        logger.info(
            f'No provider_tokens provided, creating scaffold for: {providers_set}',
            extra={'session_id': conversation_id},
        )
        git_provider_tokens = create_provider_tokens_object(providers_set)
        logger.info(
            f'Git provider scaffold: {git_provider_tokens}',
            extra={'session_id': conversation_id},
        )
        if server_config.app_mode != AppMode.SAAS and user_secrets:
            git_provider_tokens = user_secrets.provider_tokens
    session_init_args["git_provider_tokens"] = git_provider_tokens
    if user_secrets:
        session_init_args["custom_secrets"] = user_secrets.custom_secrets
    conversation_init_data = ConversationInitData(**session_init_args)
    return ExperimentManagerImpl.run_conversation_variant_test(user_id, conversation_id, conversation_init_data)
