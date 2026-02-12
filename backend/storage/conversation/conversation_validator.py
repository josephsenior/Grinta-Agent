"""Conversation access validation interfaces and default helper factory."""

from __future__ import annotations

import os
from datetime import datetime, timezone

from backend.core.config.utils import load_FORGE_config
from backend.core.logger import forge_logger as logger
from backend.server.config.server_config import ServerConfig
from backend.storage.conversation.conversation_store import ConversationStore
from backend.storage.data_models.conversation_metadata import ConversationMetadata
from backend.utils.conversation_summary import get_default_conversation_title
from backend.utils.import_utils import get_impl


class ConversationValidator:
    """Abstract base class for validating conversation access.

    This is an extension point in Forge that allows applications to customize how
    conversation access is validated. Applications can substitute their own implementation by:
    1. Creating a class that inherits from ConversationValidator
    2. Implementing the validate method
    3. Setting FORGE_CONVERSATION_VALIDATOR_CLS environment variable to the fully qualified name of the class

    The class is instantiated via get_impl() in create_conversation_validator().

    The default implementation performs no validation and returns None, None.
    """

    async def validate(
        self,
        conversation_id: str,
        cookies_str: str,
        authorization_header: str | None = None,
    ) -> str | None:
        """Validate conversation access and return user ID.

        Default implementation performs no validation. Override for custom auth.

        Args:
            conversation_id: Conversation ID to validate
            cookies_str: Cookie string from request
            authorization_header: Optional authorization header

        Returns:
            User ID or None

        """
        user_id = None
        metadata = await self._ensure_metadata_exists(conversation_id, user_id)
        return metadata.user_id

    async def _ensure_metadata_exists(
        self, conversation_id: str, user_id: str | None
    ) -> ConversationMetadata:
        config = load_FORGE_config()
        server_config = ServerConfig()
        conversation_store_class: type[ConversationStore] = get_impl(
            ConversationStore,
            server_config.conversation_store_class,
        )
        conversation_store = await conversation_store_class.get_instance(
            config, user_id
        )
        try:
            metadata = await conversation_store.get_metadata(conversation_id)
        except FileNotFoundError:
            logger.info(
                "Creating new conversation metadata for %s",
                conversation_id,
                extra={"session_id": conversation_id},
            )
            await conversation_store.save_metadata(
                ConversationMetadata(
                    conversation_id=conversation_id,
                    user_id=user_id,
                    title=get_default_conversation_title(conversation_id),
                    last_updated_at=datetime.now(timezone.utc),
                    selected_repository=None,
                ),
            )
            metadata = await conversation_store.get_metadata(conversation_id)
        return metadata


def create_conversation_validator() -> ConversationValidator:
    """Create conversation validator from environment configuration.

    Returns:
        ConversationValidator instance (default or custom implementation)

    """
    conversation_validator_cls = os.environ.get(
        "FORGE_CONVERSATION_VALIDATOR_CLS",
        "forge.storage.conversation.conversation_validator.ConversationValidator",
    )
    ConversationValidatorImpl = get_impl(
        ConversationValidator, conversation_validator_cls
    )
    return ConversationValidatorImpl()
