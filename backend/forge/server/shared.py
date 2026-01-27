import logging
import os
from typing import Type

from forge.server.config.server_config import load_server_config
from forge.server.conversation_manager.conversation_manager import ConversationManager
from forge.storage.conversation.conversation_store import ConversationStore
from forge.storage.files import FileStore
from forge.storage.secrets.secrets_store import SecretsStore
from forge.storage.settings.settings_store import SettingsStore
from forge.server.monitoring import MonitoringListener
from forge.utils.import_utils import get_impl
from forge.events.adapter import EventServiceAdapter
from forge.core.config import ForgeConfig
from forge.storage.local import LocalFileStore

logger = logging.getLogger(__name__)

# Load global server configuration
server_config = load_server_config()

# These will be initialized by the app factory or main entry point
import socketio  # type: ignore[import-untyped]
sio = socketio.AsyncServer(cors_allowed_origins='*', async_mode='asgi')
config = ForgeConfig()
# Use file store path for storage
workspace_base = os.path.expanduser(config.file_store_path)
file_store = LocalFileStore(workspace_base)
monitoring_listener = None

# Event service adapter (lazy initialization)
event_service_adapter = None

def get_event_service_adapter():
    """Get or create the event service adapter singleton."""
    global event_service_adapter
    if event_service_adapter is None:
        event_service_adapter = EventServiceAdapter(lambda user_id: file_store)
    return event_service_adapter

# Lazily resolve ConversationManager to avoid circular imports during module load
ConversationManagerImpl = None
conversation_manager = None

def get_conversation_manager_impl():
    global ConversationManagerImpl
    if ConversationManagerImpl is None:
        ConversationManagerImpl_local = get_impl(
            ConversationManager,
            server_config.conversation_manager_class,
        )
        ConversationManagerImpl = ConversationManagerImpl_local
    return ConversationManagerImpl

def get_conversation_manager():
    global conversation_manager
    # Attempt to resolve and initialize the conversation manager singleton.
    # Log the resolution attempt to aid debugging when lazy initialization fails.
    try:
        if conversation_manager is None:
            logger.debug("Resolving ConversationManager implementation: %s", server_config.conversation_manager_class)
            impl = get_conversation_manager_impl()
            # monitoring_listener and other singletons are already initialized above
            conversation_manager_local = impl.get_instance(
                sio, config, file_store, server_config, monitoring_listener
            )
            conversation_manager = conversation_manager_local
            logger.info("ConversationManager initialized: %s, file_store: %s", type(conversation_manager).__name__, conversation_manager.file_store)
    except Exception as exc:
        logger.exception("Failed to initialize ConversationManager: %s", exc)
        # Re-raise to allow callers to handle the failure
        raise
    return conversation_manager

SettingsStoreImpl = get_impl(SettingsStore, server_config.settings_store_class)

SecretsStoreImpl = get_impl(SecretsStore, server_config.secret_store_class)

ConversationStoreImpl = get_impl(
    ConversationStore,
    server_config.conversation_store_class,
)
