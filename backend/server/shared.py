import logging
import os
import threading
from typing import Type

from backend.server.config.server_config import load_server_config
from backend.server.conversation_manager.conversation_manager import ConversationManager
from backend.storage.conversation.conversation_store import ConversationStore
from backend.storage.files import FileStore
from backend.storage.secrets.secrets_store import SecretsStore
from backend.storage.settings.settings_store import SettingsStore
from backend.server.monitoring import MonitoringListener
from backend.utils.import_utils import get_impl
from backend.events.adapter import EventServiceAdapter
from backend.core.config import ForgeConfig
from backend.storage.local import LocalFileStore

logger = logging.getLogger(__name__)

# Thread lock for singleton initialization
_init_lock = threading.Lock()

# Load global server configuration
server_config = load_server_config()

# These will be initialized by the app factory or main entry point
import socketio  # type: ignore[import-untyped]

# CORS: Default to localhost origins; override via FORGE_CORS_ORIGINS env var (comma-separated)
_default_cors_origins = "http://localhost:3000,http://localhost:3001,http://127.0.0.1:3000,http://127.0.0.1:3001"
_cors_origins_str = os.environ.get("FORGE_CORS_ORIGINS", _default_cors_origins)
_cors_allowed_origins = [o.strip() for o in _cors_origins_str.split(",") if o.strip()]
sio = socketio.AsyncServer(cors_allowed_origins=_cors_allowed_origins, async_mode='asgi')
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
    with _init_lock:
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
    with _init_lock:
        try:
            if conversation_manager is None:
                logger.debug("Resolving ConversationManager implementation: %s", server_config.conversation_manager_class)
                impl = get_conversation_manager_impl()
                conversation_manager_local = impl.get_instance(
                    sio, config, file_store, server_config, monitoring_listener
                )
                conversation_manager = conversation_manager_local
                logger.info("ConversationManager initialized: %s, file_store: %s", type(conversation_manager).__name__, conversation_manager.file_store)
        except Exception as exc:
            logger.exception("Failed to initialize ConversationManager: %s", exc)
            raise
    return conversation_manager

SettingsStoreImpl = get_impl(SettingsStore, server_config.settings_store_class)

SecretsStoreImpl = get_impl(SecretsStore, server_config.secret_store_class)

ConversationStoreImpl = get_impl(
    ConversationStore,
    server_config.conversation_store_class,
)

conversation_store = None

async def get_conversation_store_async(user_id: str | None = None):
    """Async-safe conversation store accessor.

    Must be called from within a running event loop.
    """
    global conversation_store
    if conversation_store is not None:
        return conversation_store
    try:
        store = await ConversationStoreImpl.get_instance(config, user_id or "oss_user")
        conversation_store = store
        return conversation_store
    except Exception as e:
        logger.error("Failed to initialize conversation store: %s", e)
        raise


def get_conversation_store():
    """Synchronous conversation store accessor (legacy).

    Prefers returning the cached instance. If not yet initialized, attempts
    sync bootstrapping only when no event loop is running.
    """
    global conversation_store
    if conversation_store is not None:
        return conversation_store

    import asyncio
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        loop = None

    if loop is not None and loop.is_running():
        # Cannot run_until_complete inside a running loop — caller must use
        # get_conversation_store_async() instead.
        logger.warning(
            "get_conversation_store() called from a running event loop; "
            "use get_conversation_store_async() instead"
        )
        return None

    # No running loop — safe to bootstrap synchronously
    try:
        loop = asyncio.new_event_loop()
        conversation_store = loop.run_until_complete(
            ConversationStoreImpl.get_instance(config, "oss_user")
        )
        loop.close()
        return conversation_store
    except Exception as e:
        logger.error("Failed to initialize global conversation_store: %s", e)
        return None
