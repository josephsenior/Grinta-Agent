from __future__ import annotations

from copy import deepcopy
from typing import TYPE_CHECKING

from openhands.llm.llm_registry import LLMRegistry
from openhands.server.services.conversation_stats import ConversationStats
from openhands.storage import get_file_store

if TYPE_CHECKING:
    from openhands.core.config.openhands_config import OpenHandsConfig
    from openhands.storage.data_models.settings import Settings


def setup_llm_config(config: OpenHandsConfig, settings: Settings) -> OpenHandsConfig:
    """Setup LLM configuration from user settings.

    Args:
        config: The base OpenHands configuration.
        settings: User settings containing LLM preferences.

    Returns:
        OpenHandsConfig: Updated configuration with user LLM settings.
    """
    config = deepcopy(config)
    llm_config = config.get_llm_config()
    llm_config.model = settings.llm_model or ""
    llm_config.api_key = settings.llm_api_key
    llm_config.base_url = settings.llm_base_url
    config.set_llm_config(llm_config)
    return config


def create_registry_and_conversation_stats(
    config: OpenHandsConfig,
    sid: str,
    user_id: str | None,
    user_settings: Settings | None = None,
) -> tuple[LLMRegistry, ConversationStats, OpenHandsConfig]:
    """Create LLM registry and conversation stats for a session.

    Args:
        config: The base OpenHands configuration.
        sid: Session/conversation ID.
        user_id: User ID for the session.
        user_settings: Optional user-specific settings.

    Returns:
        tuple[LLMRegistry, ConversationStats, OpenHandsConfig]: Registry, stats, and updated config.
    """
    user_config = config
    if user_settings:
        user_config = setup_llm_config(config, user_settings)
    agent_cls = user_settings.agent if user_settings else None
    llm_registry = LLMRegistry(user_config, agent_cls)
    file_store = get_file_store(
        file_store_type=config.file_store,
        file_store_path=config.file_store_path,
        file_store_web_hook_url=config.file_store_web_hook_url,
        file_store_web_hook_headers=config.file_store_web_hook_headers,
        file_store_web_hook_batch=config.file_store_web_hook_batch,
    )
    conversation_stats = ConversationStats(file_store, sid, user_id)
    llm_registry.subscribe(conversation_stats.register_llm)
    return (llm_registry, conversation_stats, user_config)
