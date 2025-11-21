"""Shared server singletons for configuration, storage, and Socket.IO."""

import os

import socketio  # type: ignore[import-untyped]
from dotenv import load_dotenv

from forge.core.config import load_FORGE_config
from forge.core.config.forge_config import ForgeConfig
from forge.events.stream import EventStream
from forge.server.config.server_config import ServerConfig, load_server_config
from forge.server.conversation_manager.conversation_manager import (
    ConversationManager,
)
from forge.server.monitoring import MonitoringListener
from forge.server.types import ServerConfigInterface
from forge.services.adapters import EventServiceAdapter, RuntimeServiceAdapter
from forge.storage import get_file_store
from forge.storage.conversation.conversation_store import ConversationStore
from forge.storage.files import FileStore
from forge.storage.secrets.secrets_store import SecretsStore
from forge.storage.settings.settings_store import SettingsStore
from forge.utils.import_utils import get_impl

load_dotenv()


def _set_env_default(key: str, value) -> None:
    if value is None or key in os.environ:
        return
    if hasattr(value, "get_secret_value"):
        try:
            value = value.get_secret_value()
        except Exception:
            value = None
    if value is None:
        return
    if isinstance(value, bool):
        os.environ[key] = "true" if value else "false"
    else:
        os.environ[key] = str(value)


def _apply_runtime_env(cfg: ForgeConfig) -> None:
    """Mirror ForgeConfig observability settings into environment variables."""
    _set_env_default("REDIS_URL", cfg.redis_url)
    _set_env_default("REDIS_POOL_SIZE", cfg.redis_connection_pool_size)
    _set_env_default("REDIS_TIMEOUT", cfg.redis_connection_timeout)
    _set_env_default("REDIS_QUOTA_FALLBACK", cfg.redis_quota_fallback_enabled)

    # Logging & log shipping
    if cfg.log_format:
        _set_env_default("LOG_JSON", cfg.log_format.lower() == "json")
    _set_env_default("LOG_LEVEL", cfg.log_level.upper())
    _set_env_default("LOG_SHIPPING_ENABLED", cfg.log_shipping_enabled)
    _set_env_default("LOG_SHIPPING_ENDPOINT", cfg.log_shipping_endpoint)
    _set_env_default("LOG_SHIPPING_API_KEY", cfg.log_shipping_api_key)

    # Distributed tracing
    _set_env_default("TRACING_ENABLED", cfg.tracing_enabled)
    _set_env_default("TRACING_EXPORTER", cfg.tracing_exporter)
    _set_env_default("TRACING_ENDPOINT", cfg.tracing_endpoint)
    _set_env_default("TRACING_SAMPLE_RATE", cfg.tracing_sample_rate)
    _set_env_default("TRACING_SERVICE_NAME", cfg.tracing_service_name)
    _set_env_default("TRACING_SERVICE_VERSION", cfg.tracing_service_version)

    # Alerting / SLOs
    _set_env_default("ALERTING_ENABLED", cfg.alerting_enabled)
    _set_env_default("ALERTING_ENDPOINT", cfg.alerting_endpoint)
    _set_env_default("ALERTING_API_KEY", cfg.alerting_api_key)
    _set_env_default("SLO_AVAILABILITY_TARGET", cfg.slo_availability_target)
    _set_env_default("SLO_LATENCY_P95_TARGET_MS", cfg.slo_latency_p95_target_ms)
    _set_env_default("SLO_ERROR_RATE_TARGET", cfg.slo_error_rate_target)

    # Retry queue settings (used later by retry subsystem)
    _set_env_default("RETRY_QUEUE_ENABLED", cfg.retry_queue_enabled)
    _set_env_default("RETRY_QUEUE_BACKEND", cfg.retry_queue_backend)
    _set_env_default("RETRY_QUEUE_MAX_SIZE", cfg.retry_queue_max_size)
    _set_env_default("RETRY_QUEUE_MAX_RETRIES", cfg.retry_queue_max_retries)
    _set_env_default("RETRY_QUEUE_RETRY_DELAY_SECONDS", cfg.retry_queue_retry_delay_seconds)
    _set_env_default("RETRY_QUEUE_MAX_DELAY_SECONDS", cfg.retry_queue_max_delay_seconds)
    _set_env_default("GRACEFUL_DEGRADATION_ENABLED", cfg.graceful_degradation_enabled)


config: ForgeConfig = load_FORGE_config()
_apply_runtime_env(config)
server_config_interface: ServerConfigInterface = load_server_config()
assert isinstance(server_config_interface, ServerConfig), (
    "Loaded server config interface is not a ServerConfig, despite this being assumed"
)
server_config: ServerConfig = server_config_interface
file_store: FileStore = get_file_store(
    file_store_type=config.file_store,
    file_store_path=config.file_store_path,
    file_store_web_hook_url=config.file_store_web_hook_url,
    file_store_web_hook_headers=config.file_store_web_hook_headers,
    file_store_web_hook_batch=config.file_store_web_hook_batch,
)


def _event_file_store_factory(_: str | None) -> FileStore:
    return file_store


_metasop_cfg = getattr(config.extended, "metasop", {})
_default_sop = _metasop_cfg.get("default_sop", "feature_delivery_with_ui")


def _orchestrator_factory():
    from forge.metasop.orchestrator import MetaSOPOrchestrator

    return MetaSOPOrchestrator(_default_sop, config)


_event_grpc_endpoint = os.getenv("FORGE_EVENT_SERVICE_ENDPOINT")
_runtime_grpc_endpoint = os.getenv("FORGE_RUNTIME_SERVICE_ENDPOINT")
_use_event_service_grpc = os.getenv("FORGE_EVENT_SERVICE_GRPC", "false").lower() in {
    "1",
    "true",
    "yes",
}
_use_runtime_service_grpc = os.getenv(
    "FORGE_RUNTIME_SERVICE_GRPC", "false"
).lower() in {"1", "true", "yes"}

event_service_adapter = None
runtime_service_adapter = None

def get_event_service_adapter() -> EventServiceAdapter:
    global event_service_adapter
    if event_service_adapter is None:
        event_service_adapter = EventServiceAdapter(
            _event_file_store_factory,
            use_grpc=_use_event_service_grpc,
            grpc_endpoint=_event_grpc_endpoint,
        )
    return event_service_adapter

def get_runtime_service_adapter() -> RuntimeServiceAdapter:
    global runtime_service_adapter
    if runtime_service_adapter is None:
        runtime_service_adapter = RuntimeServiceAdapter(
            _orchestrator_factory,
            use_grpc=_use_runtime_service_grpc,
            grpc_endpoint=_runtime_grpc_endpoint,
            event_stream_provider=lambda sid: _ensure_event_stream(sid),
        )
    return runtime_service_adapter


def _ensure_event_stream(session_id: str) -> EventStream:
    try:
        return get_event_service_adapter().get_event_stream(session_id)
    except KeyError:
        info = get_event_service_adapter().start_session(session_id=session_id)
        return get_event_service_adapter().get_event_stream(info["session_id"])

client_manager = None
redis_host = os.environ.get("REDIS_HOST")
if redis_host:
    client_manager = socketio.AsyncRedisManager(
        f"redis://{redis_host}",
        redis_options={"password": os.environ.get("REDIS_PASSWORD")},
    )


sio = socketio.AsyncServer(
    async_mode="asgi",
    cors_allowed_origins="*",
    client_manager=client_manager,
    # Increase buffer size to 4MB (to handle 3MB files with base64 overhead)
    max_http_buffer_size=4 * 1024 * 1024,
)

MonitoringListenerImpl = get_impl(
    MonitoringListener,
    server_config.monitoring_listener_class,
)

monitoring_listener = MonitoringListenerImpl.get_instance(config)

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
    if conversation_manager is None:
        impl = get_conversation_manager_impl()
        # monitoring_listener and other singletons are already initialized above
        conversation_manager_local = impl.get_instance(
            sio, config, file_store, server_config, monitoring_listener
        )
        conversation_manager = conversation_manager_local
    return conversation_manager

SettingsStoreImpl = get_impl(SettingsStore, server_config.settings_store_class)

SecretsStoreImpl = get_impl(SecretsStore, server_config.secret_store_class)

ConversationStoreImpl = get_impl(
    ConversationStore,
    server_config.conversation_store_class,
)
