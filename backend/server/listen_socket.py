"""Socket.IO event handlers for real-time conversation streaming."""

from __future__ import annotations

import asyncio
import os
import secrets
from typing import Any
from urllib.parse import parse_qs

from socketio.exceptions import ConnectionRefusedError as SocketIOConnectionRefusedError  # type: ignore[import-untyped]

from backend.core.logger import forge_logger as logger
from backend.events.action import NullAction
from backend.events.action.agent import RecallAction
from backend.events.async_event_store_wrapper import AsyncEventStoreWrapper
from backend.events.event_store import EventStore
from backend.events.observation import NullObservation
from backend.events.observation.agent import AgentStateChangedObservation
from backend.events.serialization import event_to_dict
from backend.integrations.service_types import ProviderType
from backend.server.services.conversation_service import (
    setup_init_conversation_settings,
)
from backend.server.shared import (
    conversation_manager,
    get_conversation_manager,
    server_config,
    sio,
)
from backend.server.middleware.socketio_connection_manager import get_connection_manager
from backend.storage.conversation.conversation_validator import (
    create_conversation_validator,
)

# Debug function to show all registered events


def debug_show_events() -> None:
    """Debug function to display all registered Socket.IO events."""
    for event_name in [
        "connect",
        "disconnect",
        "forge_user_action",
        "forge_action",
        "test_event",
    ]:
        if (
            hasattr(sio, "handlers")
            and "/" in sio.handlers
            and event_name in sio.handlers["/"]
        ):
            pass
        else:
            pass


def _parse_latest_event_id(query_params: dict) -> int:
    """Parse latest_event_id from query parameters (utility function, not a socket event)."""
    latest_event_id_str = query_params.get("latest_event_id", [-1])[0]
    # Handle "undefined" string from frontend
    if latest_event_id_str == "undefined":
        return -1
    try:
        return int(latest_event_id_str)
    except ValueError:
        logger.debug(
            "Invalid latest_event_id value: %s, defaulting to -1", latest_event_id_str
        )
        return -1


def _parse_providers_set(query_params: dict) -> list[ProviderType]:
    """Parse providers_set from query parameters."""
    raw_list = query_params.get("providers_set", [])
    providers_list = []
    for item in raw_list:
        providers_list.extend(item.split(",") if isinstance(item, str) else [])
    providers_list = [p for p in providers_list if p]
    return [ProviderType(p) for p in providers_list]


def _validate_connection_params(
    conversation_id: str | None, query_params: dict, auth: dict | None = None
) -> None:
    """Validate connection parameters."""
    if not conversation_id:
        logger.error("No conversation_id in query params")
        msg = "No conversation_id in query params"
        raise SocketIOConnectionRefusedError(msg)
    if _invalid_session_api_key(query_params, auth):
        msg = "invalid_session_api_key"
        raise SocketIOConnectionRefusedError(msg)


async def _replay_events(
    async_store: AsyncEventStoreWrapper, connection_id: str
) -> AgentStateChangedObservation | None:
    """Replay events from store and return agent state if found.

    Args:
        async_store: Event store wrapper
        connection_id: Connection ID to emit to

    Returns:
        AgentStateChangedObservation if found, None otherwise

    """
    agent_state_changed = None
    event_count = 0

    async for event in async_store:
        event_count += 1
        logger.debug("forge_event: %s", event.__class__.__name__)

        if isinstance(event, (NullAction, NullObservation, RecallAction)):
            continue

        if isinstance(event, AgentStateChangedObservation):
            logger.info("DEBUG: Found AgentStateChangedObservation: %s", event.agent_state)
            agent_state_changed = event
        else:
            await sio.emit("forge_event", event_to_dict(event), to=connection_id)

    logger.info("DEBUG: Replayed %s events", event_count)
    return agent_state_changed


def _get_conversation_manager_instance():
    """Get conversation manager instance, initializing if needed."""
    manager = conversation_manager
    if manager is None:  # type: ignore[unreachable]
        try:
            return get_conversation_manager()
        except Exception:
            return None
    return manager


async def _send_agent_state(
    agent_state_changed: AgentStateChangedObservation | None,
    conversation_id: str,
    connection_id: str,
) -> bool:
    """Send agent state to connection.

    Args:
        agent_state_changed: Agent state observation if found
        conversation_id: Conversation ID
        connection_id: Connection ID

    Returns:
        True if state was sent

    """
    if agent_state_changed:
        logger.info(
            "DEBUG: Found agent state in event stream: %s",
            agent_state_changed.agent_state,
        )
        # Update connection activity
        conn_manager = get_connection_manager()
        conn_manager.update_activity(connection_id)
        await sio.emit("forge_event", event_to_dict(agent_state_changed), to=connection_id)
        return True

    manager = _get_conversation_manager_instance()
    if manager is None:
        logger.error("Conversation manager is not initialized")
        return False

    try:
        agent_loop_info_list = await manager.get_agent_loop_info(
            filter_to_sids={conversation_id}
        )
        if agent_loop_info_list and len(agent_loop_info_list) > 0:
            agent_loop_info = agent_loop_info_list[0]
            if agent_loop_info.agent_state:
                current_state_event = AgentStateChangedObservation(
                    "", agent_loop_info.agent_state, "Connection established"
                )
                logger.info(
                    "DEBUG: Sending current agent state %s to new connection %s",
                    agent_loop_info.agent_state,
                    connection_id,
                )
                # Update connection activity
                conn_manager = get_connection_manager()
                conn_manager.update_activity(connection_id)
                await sio.emit(
                    "forge_event", event_to_dict(current_state_event), to=connection_id
                )
                return True
            else:
                logger.warning(
                    "DEBUG: No agent state found in agent_loop_info for conversation %s",
                    conversation_id,
                )
    except Exception as e:
        logger.error("Error getting agent state from conversation manager: %s", e)

    return False


async def _replay_event_stream(
    event_store: EventStore,
    latest_event_id: int,
    connection_id: str,
    conversation_id: str,
) -> None:
    """Replay event stream to new connection."""
    logger.info(
        "🚨 *** REPLAY START: Replaying event stream for conversation %s with connection_id %s...",
        conversation_id,
        connection_id,
    )
    logger.info(
        "DEBUG: Event store current ID: %s, latest_event_id: %s",
        event_store.cur_id,
        latest_event_id,
    )

    async_store = AsyncEventStoreWrapper(event_store, latest_event_id + 1)
    agent_state_changed = await _replay_events(async_store, connection_id)

    agent_state_sent = await _send_agent_state(
        agent_state_changed, conversation_id, connection_id
    )

    # Fallback: If we still haven't sent an agent state, send a default one
    if not agent_state_sent:
        logger.info(
            "DEBUG: No agent state found, sending default AWAITING_USER_INPUT state to connection %s",
            connection_id,
        )
        try:
            # Use the already imported AgentStateChangedObservation from the top of the file
            default_state_event = AgentStateChangedObservation(
                "", "awaiting_user_input", "Default state on connection"
            )
            # Update connection activity
            conn_manager = get_connection_manager()
            conn_manager.update_activity(connection_id)
            await sio.emit(
                "forge_event", event_to_dict(default_state_event), to=connection_id
            )
            logger.info("DEBUG: Sent default agent state to connection %s", connection_id)
        except Exception as e:
            logger.error(
                "Failed to send default agent state to connection %s: %s",
                connection_id,
                e,
            )

    logger.info("Finished replaying event stream for conversation %s", conversation_id)


@sio.event
async def connect(connection_id: str, environ: dict, *args) -> None:
    """Handle Socket.IO client connection.

    Authenticates user, validates conversation access, replays events, and joins conversation.

    Args:
        connection_id: Unique connection identifier
        environ: WSGI environment dictionary with request data
        *args: Additional arguments provided by Socket.IO for compatibility

    Raises:
        SocketIOConnectionRefusedError: If authentication or validation fails

    """
    try:
        logger.info(
            "*** DEBUG: connect handler called with connection_id: %s", connection_id
        )
        logger.info("sio:connect: %s", connection_id)
        query_params = parse_qs(environ.get("QUERY_STRING", ""))
        auth = args[0] if args else {}

        # Parse parameters
        latest_event_id = _parse_latest_event_id(query_params)
        conversation_id = query_params.get("conversation_id", [None])[0]
        providers_set = _parse_providers_set(query_params)

        logger.info(
            "Socket request for conversation %s with connection_id %s",
            conversation_id,
            connection_id,
        )

        # Validate connection
        _validate_connection_params(conversation_id, query_params, auth)

        # Authenticate user
        cookies_str = environ.get("HTTP_COOKIE", "")
        authorization_header = environ.get("HTTP_AUTHORIZATION")
        conversation_validator = create_conversation_validator()
        user_id = await conversation_validator.validate(
            conversation_id, cookies_str, authorization_header
        )
        logger.info(
            "User %s is allowed to connect to conversation %s", user_id, conversation_id
        )

        # Register connection with connection manager
        conn_manager = get_connection_manager()
        try:
            conn_manager.register_connection(
                sid=connection_id,
                user_id=user_id,
                conversation_id=conversation_id,
            )
            logger.info("Connection registered: %s", connection_id)
        except ValueError as e:
            logger.warning("Connection limit exceeded: %s", e)
            raise SocketIOConnectionRefusedError(str(e)) from e

        # Deliver any queued messages
        try:
            delivered = await conn_manager.deliver_queued_messages(connection_id, sio)
            if delivered > 0:
                logger.info("Delivered %s queued messages to %s", delivered, connection_id)
        except Exception as e:
            logger.error("Error delivering queued messages: %s", e)

        # Create event store
        manager = _get_conversation_manager_instance()
        if manager is None:
            msg = "Conversation manager is not initialized"
            raise SocketIOConnectionRefusedError(msg)
        try:
            event_store = EventStore(
                conversation_id, manager.file_store, user_id
            )
        except FileNotFoundError as e:
            logger.error(
                "Failed to create EventStore for conversation %s: %s",
                conversation_id,
                e,
            )
            msg = f"Failed to access conversation events: {e}"
            raise SocketIOConnectionRefusedError(msg) from e

        # Replay events
        await _replay_event_stream(
            event_store, latest_event_id, connection_id, conversation_id
        )

        # Join conversation
        try:
            conversation_init_data = await setup_init_conversation_settings(
                user_id, conversation_id, providers_set
            )
        except Exception as e:
            logger.error(
                "Failed to setup conversation settings for conversation %s (user_id: %s): %s",
                conversation_id,
                user_id,
                e,
                exc_info=True,
            )
            raise SocketIOConnectionRefusedError(
                f"Failed to setup conversation settings: {e}"
            ) from e
        
        agent_loop_info = await manager.join_conversation(
            conversation_id,
            connection_id,
            conversation_init_data,
            user_id,
        )
        if agent_loop_info is None:
            msg = "Failed to join conversation"
            raise SocketIOConnectionRefusedError(msg)

        logger.info(
            "Successfully joined conversation %s with connection_id %s",
            conversation_id,
            connection_id,
        )
    except SocketIOConnectionRefusedError:
        asyncio.create_task(sio.disconnect(connection_id))
        raise
    except Exception:
        import traceback

        traceback.print_exc()
        raise


# Removed duplicate connect handler - using the one above that properly creates sessions


@sio.event
async def forge_user_action(connection_id: str, data: dict[str, Any]) -> None:
    """Handle user action from Socket.IO client.

    Args:
        connection_id: Client connection identifier
        data: Action data dictionary

    """
    # Debug logging
    logger.info("forge_user_action received: action=%s, data=%s", data.get("action"), data)

    manager = _get_conversation_manager_instance()
    if manager is not None:
        await manager.send_to_event_stream(connection_id, data)


@sio.event
async def forge_action(connection_id: str, data: dict[str, Any]) -> None:
    """Handle agent action from Socket.IO client.

    Args:
        connection_id: Client connection identifier
        data: Action data dictionary

    """
    manager = _get_conversation_manager_instance()
    if manager is not None:
        await manager.send_to_event_stream(connection_id, data)


@sio.event
async def disconnect(connection_id: str) -> None:
    """Handle Socket.IO client disconnection.

    Args:
        connection_id: Unique connection identifier

    """
    logger.info("sio:disconnect: %s", connection_id)
    
    # Unregister connection from connection manager
    conn_manager = get_connection_manager()
    conn_manager.unregister_connection(connection_id)
    logger.info("Connection unregistered: %s", connection_id)
    
    # Disconnect from session
    manager = _get_conversation_manager_instance()
    if manager is not None:
        await manager.disconnect_from_session(connection_id)


@sio.event
async def test_event(connection_id: str, data: dict[str, Any]) -> None:
    """Handle test event (no-op).

    Args:
        connection_id: Client connection identifier
        data: Event data

    """
    return None


def _invalid_session_api_key(query_params: dict, auth: dict | None = None) -> bool:
    """Validate the session API key against query params or socket auth payload.

    Args:
        query_params: Query parameters containing session_api_key.
        auth: Optional Socket.IO auth payload.

    Returns:
        bool: True if the API key is invalid, False otherwise.

    """
    expected_key = getattr(server_config, "session_api_key", "")
    if not expected_key:
        return False

    # Prefer auth payload (Socket.IO handshake auth) over query params.
    if auth and isinstance(auth, dict):
        provided_key = (
            auth.get("session_api_key")
            or auth.get("apiKey")
            or auth.get("token")
        )
        if provided_key is not None:
            return not secrets.compare_digest(str(provided_key), expected_key)

    # Query-param auth is leak-prone; keep it opt-in for local/dev compatibility.
    allow_query_token_auth = os.getenv("FORGE_ALLOW_QUERY_TOKEN_AUTH", "false").lower() in (
        "1",
        "true",
        "yes",
    )
    if allow_query_token_auth:
        query_api_keys = (
            query_params.get("session_api_key", [])
            or query_params.get("token", [])
            or query_params.get("apiKey", [])
        )
        if query_api_keys:
            return not secrets.compare_digest(str(query_api_keys[0]), expected_key)

    return True  # Invalid if key is missing and we have an expected key


# Call debug function after all event handlers are registered
def show_events() -> None:
    """Display all registered Socket.IO events for debugging purposes.

    This function prints information about all registered event handlers
    to help with debugging Socket.IO event registration issues.
    """
    logger.info("*** DEBUG: Socket.IO event handlers being registered")
    if hasattr(sio, "handlers") and "/" in sio.handlers:
        for event_name, _handlers in sio.handlers["/"].items():
            logger.info("*** DEBUG: Registered event handler: %s", event_name)
    else:
        logger.info("*** DEBUG: No Socket.IO handlers found")


show_events()

# Add a test to see if handlers are being overridden
if hasattr(sio, "handlers") and "/" in sio.handlers:
    for _event_name, _handler in sio.handlers["/"].items():
        pass
else:
    pass

# Check if this is the same instance being used in listen.py
