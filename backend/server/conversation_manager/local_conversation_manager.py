"""Conversation manager implementation for single-node Forge deployments."""

from __future__ import annotations

import asyncio
import contextlib
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import TYPE_CHECKING, Any, Callable

from backend.core.exceptions import AgentRuntimeUnavailableError
from backend.core.logger import forge_logger as logger
from backend.core.schemas import AgentState, ObservationType
from backend.events.observation.commands import CmdOutputObservation
from backend.events.stream import EventStreamSubscriber, session_exists
from backend.runtime import get_runtime_cls
from backend.server.constants import ROOM_KEY
from backend.server.data_models.agent_loop_info import AgentLoopInfo
from backend.server.monitoring import MonitoringListener
from backend.server.session.constants import WAIT_TIME_BEFORE_CLOSE
from backend.server.session.conversation import ServerConversation
from backend.storage.conversation.conversation_store import ConversationStore
from backend.storage.data_models.conversation_status import ConversationStatus
from backend.utils.async_utils import (
    GENERAL_TIMEOUT,
    call_async_from_sync,
    run_in_loop,
    wait_all,
)
from backend.utils.conversation_summary import (
    auto_generate_title,
    get_default_conversation_title,
)
from backend.utils.import_utils import get_impl
from backend.utils.shutdown_listener import should_continue
from backend.utils.utils import create_registry_and_conversation_stats

from .conversation_manager import ConversationManager
from .metadata_tracker import ConversationMetadataTracker

if TYPE_CHECKING:
    from collections.abc import Iterable

    import socketio  # type: ignore[import-untyped]

    from backend.core.config.llm_config import LLMConfig
    from backend.core.config.forge_config import ForgeConfig
    from backend.events.action import MessageAction
    from backend.models.llm_registry import LLMRegistry
    from backend.server.config.server_config import ServerConfig
    from backend.server.session.agent_session import AgentSession
    from backend.server.session.session import Session
    from backend.storage.data_models.conversation_metadata import ConversationMetadata
    from backend.storage.data_models.settings import Settings
    from backend.storage.files import FileStore

_CLEANUP_INTERVAL = 15
UPDATED_AT_CALLBACK_ID = "updated_at_callback_id"


@dataclass
class LocalConversationManager(ConversationManager):
    """Default implementation of ConversationManager for single-server deployments.

    See ConversationManager for extensibility details.
    """

    sio: socketio.AsyncServer
    config: ForgeConfig
    file_store: FileStore
    server_config: ServerConfig
    monitoring_listener: MonitoringListener = MonitoringListener()
    _local_agent_loops_by_sid: dict[str, "Session"] = field(default_factory=dict)
    _local_connection_id_to_session_id: dict[str, str] = field(default_factory=dict)
    _active_conversations: dict[str, tuple[ServerConversation, int]] = field(
        default_factory=dict
    )
    _detached_conversations: dict[str, tuple[ServerConversation, float]] = field(
        default_factory=dict
    )
    _conversations_lock: asyncio.Lock = field(default_factory=asyncio.Lock)
    _sessions_lock: asyncio.Lock = field(default_factory=asyncio.Lock)
    _background_tasks: set[asyncio.Task] = field(default_factory=set)
    _cleanup_task: asyncio.Task | None = None
    _conversation_store_class: type[ConversationStore] | None = None
    _loop: asyncio.AbstractEventLoop | None = None

    async def __aenter__(self):
        """Start background cleanup and initialize the runtime runtime class."""
        self._loop = asyncio.get_event_loop()
        self._cleanup_task = asyncio.create_task(self._cleanup_stale())
        get_runtime_cls(self.config.runtime).setup(self.config)
        # Metadata tracking is now delegated to a focused helper class.
        self._metadata_tracker = ConversationMetadataTracker(
            sio=self.sio,
            file_store=self.file_store,
            conversation_store_factory=self._get_conversation_store,
            session_lookup=lambda sid: self._local_agent_loops_by_sid.get(sid),
            loop=self._loop,
        )
        return self

    async def __aexit__(self, exc_type, exc_value, traceback):
        """Cancel cleanup tasks and teardown the runtime runtime class."""
        if self._cleanup_task:
            self._cleanup_task.cancel()
            self._cleanup_task = None
        get_runtime_cls(self.config.runtime).teardown(self.config)

    async def attach_to_conversation(
        self, sid: str, user_id: str | None = None
    ) -> ServerConversation | None:
        """Attach to an existing conversation or establish a new connection.

        Args:
            sid: Conversation/session identifier.
            user_id: Optional user identifier for session ownership validation.

        Returns:
            The connected `ServerConversation`, or None if no session is found.

        """
        start_time = time.time()
        if not await session_exists(sid, self.file_store, user_id=user_id):
            return None

        # Fast path: check if conversation is already active/detached under lock
        async with self._conversations_lock:
            if sid in self._active_conversations:
                conversation, count = self._active_conversations[sid]
                self._active_conversations[sid] = (conversation, count + 1)
                logger.info(
                    "Reusing active conversation %s", sid, extra={"session_id": sid}
                )
                return conversation
            if sid in self._detached_conversations:
                conversation, _ = self._detached_conversations.pop(sid)
                self._active_conversations[sid] = (conversation, 1)
                logger.info(
                    "Reusing detached conversation %s", sid, extra={"session_id": sid}
                )
                return conversation

        # Slow path: gather session info OUTSIDE the lock to avoid starvation
        event_stream = None
        runtime = None
        async with self._sessions_lock:
            session = self._local_agent_loops_by_sid.get(sid)
        if session is not None:
            event_stream = session.agent_session.event_stream
            runtime = session.agent_session.runtime
            # Wait for runtime creation outside any lock
            if runtime is None and getattr(session.agent_session, "_starting", False):
                max_wait = 30
                wait_interval = 0.2
                waited = 0.0
                logger.debug(
                    "Agent session for %s is starting, waiting for runtime...",
                    sid,
                )
                while waited < max_wait and runtime is None:
                    await asyncio.sleep(wait_interval)
                    waited += wait_interval
                    runtime = session.agent_session.runtime
                    if getattr(session.agent_session, "_startup_failed", False):
                        logger.warning(
                            "Agent session for %s failed initialization", sid
                        )
                        break
                    if getattr(session.agent_session, "_closed", False):
                        logger.warning(
                            "Agent session for %s was closed during initialization", sid
                        )
                        break
                if runtime is None:
                    logger.warning(
                        "Runtime not created for session %s after %ss of waiting.",
                        sid,
                        max_wait,
                    )
            elif runtime is None:
                logger.debug(
                    "Session %s exists but runtime is None and not starting.",
                    sid,
                )
            # Create ServerConversation
            # If runtime is None, ServerConversation will create its own runtime for file access
            # This allows file access even before agent initialization completes
            c = ServerConversation(
                sid,
                file_store=self.file_store,
                config=self.config,
                user_id=user_id,
                event_stream=event_stream,  # type: ignore[arg-type]
                runtime=runtime,  # May be None - ServerConversation will create one
            )

            # CRITICAL: Ensure runtime exists (it should be created in __init__ if runtime=None)
            if not c.runtime:
                logger.error(
                    f"ServerConversation for {sid} was created without a runtime! "
                    "This should never happen - runtime should be created in __init__."
                )
                await c.disconnect()
                return None

            logger.debug(
                f"ServerConversation for {sid} created with runtime: {type(c.runtime).__name__}, "
                f"attach_to_existing={c._attach_to_existing}"
            )

            # Connect and initialize the runtime
            try:
                await c.connect()
                logger.debug(f"ServerConversation for {sid} connected successfully")
                # Verify runtime is actually ready after connection
                # For in-process local runtime, initialization happens in connect()
                if hasattr(c.runtime, "runtime_initialized"):
                    if not c.runtime.runtime_initialized:
                        logger.debug(
                            f"Runtime for conversation {sid} connected but not initialized yet, "
                            "waiting for initialization..."
                        )
                        # Wait for initialization to complete
                        import asyncio

                        max_wait = 5  # Reduced wait time since in-process runtime initializes quickly
                        wait_interval = 0.1
                        waited = 0.0
                        while waited < max_wait and not c.runtime.runtime_initialized:
                            await asyncio.sleep(wait_interval)
                            waited += wait_interval
                            # Also check if agent session runtime is now ready (prefer that one)
                            if session and session.agent_session.runtime:
                                logger.debug(
                                    f"Agent session runtime for {sid} is now ready, "
                                    "updating ServerConversation to use it"
                                )
                                # Update to use agent session's runtime if it's ready
                                # This avoids having two runtimes for the same conversation
                                c.runtime = session.agent_session.runtime
                                c._attach_to_existing = True
                                break
                        if not c.runtime.runtime_initialized:
                            logger.warning(
                                f"Runtime for conversation {sid} still not initialized after {max_wait}s. "
                                "File operations may fail."
                            )
                # Final check: ensure runtime is ready before returning
                if not c.runtime:
                    logger.error(
                        f"Runtime for conversation {sid} is None after connect()!"
                    )
                    await c.disconnect()
                    return None

                logger.debug(
                    f"ServerConversation for {sid} ready with runtime: "
                    f"{type(c.runtime).__name__}, initialized={getattr(c.runtime, 'runtime_initialized', 'N/A')}"
                )
            except AgentRuntimeUnavailableError as e:
                logger.error(
                    "Error connecting to conversation %s: %s",
                    c.sid,
                    e,
                    extra={"session_id": sid},
                    exc_info=True,  # Include full traceback
                )
                # Don't disconnect - keep the conversation and runtime for retry
                # The runtime might still work for file operations even if connect() failed
                logger.warning(
                    f"Conversation {sid} created but runtime connection failed: {e}. "
                    "File operations will not work until the runtime is ready. "
                    "Check logs above for details about why the local runtime failed to initialize."
                )
            except Exception as e:
                logger.error(
                    f"Unexpected error connecting runtime for conversation {sid}: {e}",
                    exc_info=True,
                    extra={"session_id": sid},
                )
                # Don't fail completely - allow the conversation to exist
                # The runtime might still work
        end_time = time.time()
        logger.info(
            "ServerConversation %s connected in %s seconds",
            c.sid,
            end_time - start_time,
            extra={"session_id": sid},
        )
        # Re-acquire lock only for the brief dict mutation
        async with self._conversations_lock:
            # Double-check: another coroutine may have raced us
            if sid in self._active_conversations:
                existing, count = self._active_conversations[sid]
                self._active_conversations[sid] = (existing, count + 1)
                # Discard our duplicate
                await c.disconnect()
                return existing
            self._active_conversations[sid] = (c, 1)
        return c

    async def join_conversation(
        self,
        sid: str,
        connection_id: str,
        settings: Settings,
        user_id: str | None,
    ) -> AgentLoopInfo:
        """Join a conversation and ensure the agent loop is active.

        Args:
            sid: Conversation identifier to join.
            connection_id: Socket connection identifier for the joining client.
            settings: Conversation settings used to initialize the agent loop.
            user_id: Optional user identifier.

        Returns:
            Aggregated info describing the running agent loop.

        """
        logger.info(
            "join_conversation:%s:%s",
            sid,
            connection_id,
            extra={"session_id": sid, "user_id": user_id},
        )
        await self.sio.enter_room(connection_id, ROOM_KEY.format(sid=sid))
        self._local_connection_id_to_session_id[connection_id] = sid
        return await self.maybe_start_agent_loop(sid, settings, user_id)

    async def detach_from_conversation(self, conversation: ServerConversation) -> None:
        """Decrease active reference count and mark conversation for cleanup."""
        sid = conversation.sid
        async with self._conversations_lock:
            if sid in self._active_conversations:
                conv, count = self._active_conversations[sid]
                if count > 1:
                    self._active_conversations[sid] = (conv, count - 1)
                    return
                self._active_conversations.pop(sid)
                self._detached_conversations[sid] = (conversation, time.time())

    async def _cleanup_detached_conversations(self) -> None:
        """Cleanup all detached conversations."""
        async with self._conversations_lock:
            items = list(self._detached_conversations.items())
            for sid, (conversation, _detach_time) in items:
                await conversation.disconnect()
                self._detached_conversations.pop(sid, None)

    def _find_stale_sessions(self, close_threshold: float) -> list[str]:
        """Find sessions that should be closed based on inactivity."""
        running_loops = list(self._local_agent_loops_by_sid.items())
        running_loops.sort(key=lambda item: item[1].last_active_ts)

        sid_to_close: list[str] = []
        for sid, session in running_loops:
            state = session.agent_session.get_state()
            if session.last_active_ts < close_threshold and state not in [
                AgentState.RUNNING,
                None,
            ]:
                sid_to_close.append(sid)

        return sid_to_close

    async def _cleanup_cancelled(self) -> None:
        """Handle cleanup when task is cancelled."""
        async with self._conversations_lock:
            for conversation, _ in self._detached_conversations.values():
                await conversation.disconnect()
            self._detached_conversations.clear()
        await wait_all(
            self._close_session(sid) for sid in self._local_agent_loops_by_sid
        )

    async def _cleanup_stale(self) -> None:
        while should_continue():
            try:
                # Cleanup detached conversations
                await self._cleanup_detached_conversations()

                # Check if close delay is configured
                if not self.config.sandbox.close_delay:
                    return

                # Find and close stale sessions
                close_threshold = time.time() - self.config.sandbox.close_delay
                sid_to_close = self._find_stale_sessions(close_threshold)

                # Filter out connected sessions
                connections = await self.get_connections(
                    filter_to_sids=set(sid_to_close)
                )
                connected_sids = {sid for _, sid in connections.items()}
                sid_to_close = [
                    sid for sid in sid_to_close if sid not in connected_sids
                ]

                # Close stale sessions
                await wait_all(
                    (self._close_session(sid) for sid in sid_to_close),
                    timeout=WAIT_TIME_BEFORE_CLOSE,
                )
                await asyncio.sleep(_CLEANUP_INTERVAL)

            except asyncio.CancelledError:
                await self._cleanup_cancelled()
                return
            except Exception:
                logger.error("error_cleaning_stale")
                await asyncio.sleep(_CLEANUP_INTERVAL)

    async def _get_conversation_store(self, user_id: str | None) -> ConversationStore:
        conversation_store_class = self._conversation_store_class
        if not conversation_store_class:
            self._conversation_store_class = conversation_store_class = get_impl(
                ConversationStore,
                self.server_config.conversation_store_class,
            )
        return await conversation_store_class.get_instance(self.config, user_id)

    async def get_running_agent_loops(
        self,
        user_id: str | None = None,
        filter_to_sids: set[str] | None = None,
    ) -> set[str]:
        """Get the running session ids in chronological order (oldest first).

        If a user is supplied, then the results are limited to session ids for that user.
        If a set of filter_to_sids is supplied, then results are limited to these ids of interest.

        Returns:
            A set of session IDs

        """
        items: Iterable[tuple[str, "Session"]] = self._local_agent_loops_by_sid.items()
        if filter_to_sids is not None:
            items = (item for item in items if item[0] in filter_to_sids)
        if user_id:
            items = (item for item in items if item[1].user_id == user_id)
        return {sid for sid, _ in items}

    async def get_connections(
        self,
        user_id: str | None = None,
        filter_to_sids: set[str] | None = None,
    ) -> dict[str, str]:
        """Return mapping from connection IDs to session IDs with optional filters."""
        connections = dict(**self._local_connection_id_to_session_id)
        if filter_to_sids is not None:
            connections = {
                connection_id: sid
                for connection_id, sid in connections.items()
                if sid in filter_to_sids
            }
        if user_id:
            for connection_id, sid in list(connections.items()):
                session = self._local_agent_loops_by_sid.get(sid)
                if not session or session.user_id != user_id:
                    connections.pop(connection_id)
        return connections

    async def maybe_start_agent_loop(
        self,
        sid: str,
        settings: Settings | None,
        user_id: str | None,
        initial_user_msg: MessageAction | None = None,
        replay_json: str | None = None,
    ) -> AgentLoopInfo:
        """Start an agent loop if needed and return its exposed information."""
        logger.info("maybe_start_agent_loop:%s", sid, extra={"session_id": sid})
        if settings is None:
            logger.warning(
                "maybe_start_agent_loop called with no settings; skipping start",
                extra={"session_id": sid},
            )
            raise RuntimeError("Conversation settings were not initialized")
        session = self._local_agent_loops_by_sid.get(
            sid
        ) or await self._start_agent_loop(
            sid,
            settings,
            user_id,
            initial_user_msg,
            replay_json,
        )
        return self._agent_loop_info_from_session(session)

    async def _start_agent_loop(
        self,
        sid: str,
        settings: Settings,
        user_id: str | None,
        initial_user_msg: MessageAction | None = None,
        replay_json: str | None = None,
    ) -> "Session":
        logger.info("starting_agent_loop:%s", sid, extra={"session_id": sid})
        # Local import to avoid circular dependency during module import time
        from backend.server.session.session import Session

        response_ids = await self.get_running_agent_loops(user_id)
        if len(response_ids) >= self.config.max_concurrent_conversations:
            logger.info(
                "too_many_sessions_for:%s",
                user_id or "",
                extra={"session_id": sid, "user_id": user_id},
            )
            conversation_store = await self._get_conversation_store(user_id)
            conversations = await conversation_store.get_all_metadata(response_ids)
            conversations.sort(key=_last_updated_at_key, reverse=True)
            while len(conversations) >= self.config.max_concurrent_conversations:
                oldest_conversation_id = conversations.pop().conversation_id
                logger.debug(
                    "closing_from_too_many_sessions:%s:%s",
                    user_id or "",
                    oldest_conversation_id,
                    extra={"session_id": oldest_conversation_id, "user_id": user_id},
                )
                status_update_dict = {
                    "status_update": True,
                    "type": "error",
                    "id": "AGENT_ERROR$TOO_MANY_CONVERSATIONS",
                    "message": "Too many conversations at once. If you are still using this one, try reactivating it by prompting the agent to continue",
                }
                if self._loop is not None:
                    await run_in_loop(
                        self.sio.emit(
                            "forge_event",
                            status_update_dict,
                            to=ROOM_KEY.format(sid=oldest_conversation_id),
                        ),
                        self._loop,
                    )
                else:
                    await self.sio.emit(
                        "forge_event",
                        status_update_dict,
                        to=ROOM_KEY.format(sid=oldest_conversation_id),
                    )
                await self.close_session(oldest_conversation_id)
        llm_registry, conversation_stats, config = (
            create_registry_and_conversation_stats(
                self.config,
                sid,
                user_id,
                settings,
            )
        )
        session = Session(
            sid=sid,
            file_store=self.file_store,
            config=config,
            llm_registry=llm_registry,
            conversation_stats=conversation_stats,
            sio=self.sio,
            user_id=user_id,
        )
        async with self._sessions_lock:
            self._local_agent_loops_by_sid[sid] = session

        task = asyncio.create_task(
            session.initialize_agent(settings, initial_user_msg, replay_json)
        )
        self._background_tasks.add(task)
        task.add_done_callback(self._background_tasks.discard)
        with contextlib.suppress(ValueError):
            session.agent_session.event_stream.subscribe(  # type: ignore[attr-defined]
                EventStreamSubscriber.SERVER,
                self._create_conversation_update_callback(
                    user_id, sid, settings, session.llm_registry
                ),
                UPDATED_AT_CALLBACK_ID,
            )
        return session

    async def send_to_event_stream(self, connection_id: str, data: dict) -> None:
        """Emit data to the event stream backing a socket connection."""
        if sid := self._local_connection_id_to_session_id.get(connection_id):
            await self.send_event_to_conversation(sid, data)
        else:
            msg = f"no_connected_session:{connection_id}"
            raise RuntimeError(msg)

    async def send_event_to_conversation(self, sid: str, data: dict) -> None:
        """Dispatch event payload to a specific conversation session."""
        if session := self._local_agent_loops_by_sid.get(sid):
            await session.dispatch(data)
        else:
            msg = f"no_conversation:{sid}"
            raise RuntimeError(msg)

    async def request_llm_completion(
        self,
        sid: str,
        service_id: str,
        llm_config: LLMConfig,
        messages: list[dict[str, str]],
    ):
        """Proxy completion requests through the session's LLM registry."""
        session = self._local_agent_loops_by_sid.get(sid)
        if not session:
            msg = f"no_conversation:{sid}"
            raise RuntimeError(msg)
        llm_registry = session.llm_registry
        return llm_registry.request_extraneous_completion(
            service_id, llm_config, messages
        )

    async def disconnect_from_session(self, connection_id: str) -> None:
        """Remove connection mapping and detach the conversation if no connections remain."""
        sid = self._local_connection_id_to_session_id.pop(connection_id, None)
        logger.info(
            "disconnect_from_session:%s:%s",
            connection_id,
            sid,
            extra={"session_id": sid},
        )
        if not sid:
            logger.warning(
                "disconnect_from_uninitialized_session:%s",
                connection_id,
                extra={"session_id": sid},
            )
            return
        # Detach conversation when no more connections reference it
        async with self._conversations_lock:
            if sid in self._active_conversations:
                conv, count = self._active_conversations[sid]
                if count > 1:
                    self._active_conversations[sid] = (conv, count - 1)
                else:
                    self._active_conversations.pop(sid)
                    self._detached_conversations[sid] = (conv, time.time())

    async def close_session(self, sid: str) -> None:
        """Public API hook to close a session from external callers."""
        if self._local_agent_loops_by_sid.get(sid):
            await self._close_session(sid)

    def get_agent_session(self, sid: str) -> AgentSession | None:
        """Get the agent session for a given session ID.

        Args:
            sid: The session ID.

        Returns:
            The agent session, or None if not found.

        """
        if session := self._local_agent_loops_by_sid.get(sid):
            return session.agent_session
        return None

    async def _close_session(self, sid: str) -> None:
        """Close a session and disconnect all associated WebSocket connections.

        Args:
            sid: Session ID to close

        """
        logger.info("_close_session:%s", sid, extra={"session_id": sid})
        connection_ids_to_remove = [
            connection_id
            for connection_id, conn_sid in self._local_connection_id_to_session_id.items()
            if sid == conn_sid
        ]
        logger.info(
            "removing connections: %s",
            connection_ids_to_remove,
            extra={"session_id": sid},
        )
        for connection_id in connection_ids_to_remove:
            await self.sio.disconnect(connection_id)
            self._local_connection_id_to_session_id.pop(connection_id, None)
        async with self._sessions_lock:
            session = self._local_agent_loops_by_sid.pop(sid, None)
        if not session:
            logger.warning("no_session_to_close:%s", sid, extra={"session_id": sid})
            return
        logger.info("closing_session:%s", session.sid, extra={"session_id": sid})
        await session.close()
        logger.info("closed_session:%s", session.sid, extra={"session_id": sid})

    @classmethod
    def get_instance(
        cls,
        sio: socketio.AsyncServer,
        config: ForgeConfig,
        file_store: FileStore,
        server_config: ServerConfig,
        monitoring_listener: MonitoringListener | None,
    ) -> ConversationManager:
        """Get or create LocalConversationManager instance.

        Args:
            sio: SocketIO server instance
            config: Forge configuration
            file_store: File storage backend
            server_config: Server configuration
            monitoring_listener: Optional monitoring listener

        Returns:
            ConversationManager instance

        """
        return LocalConversationManager(
            sio,
            config,
            file_store,
            server_config,
            monitoring_listener or MonitoringListener(),
        )

    def _create_conversation_update_callback(
        self,
        user_id: str | None,
        conversation_id: str,
        settings: Settings,
        llm_registry: LLMRegistry,
    ) -> Callable:
        """Delegate to :class:`ConversationMetadataTracker`."""
        return self._metadata_tracker.create_update_callback(
            user_id, conversation_id, settings, llm_registry
        )

    # --------------------------------------------------------------- #
    # Legacy delegation stubs (kept for backward-compat & grep-ability)
    # The real implementations now live in metadata_tracker.py.
    # --------------------------------------------------------------- #

    async def _update_conversation_for_event(
        self,
        user_id: str,
        conversation_id: str,
        settings: Settings,
        llm_registry: LLMRegistry,
        event=None,
    ) -> None:
        """Update conversation metadata based on event.

        Args:
            user_id: User identifier
            conversation_id: Conversation identifier
            settings: User settings
            llm_registry: LLM registry
            event: Optional event that triggered update

        """
        conversation_store = await self._get_conversation_store(user_id)
        conversation = await conversation_store.get_metadata(conversation_id)
        conversation.last_updated_at = datetime.now(timezone.utc)

        self._update_metrics_from_event(conversation, event)
        await self._handle_git_event(conversation_id, conversation, event)
        await self._update_conversation_title(
            conversation_id, conversation, user_id, settings, llm_registry
        )

        await conversation_store.save_metadata(conversation)

    def _update_metrics_from_event(self, conversation, event) -> None:
        """Update conversation metrics from event.

        Args:
            conversation: Conversation metadata
            event: Event with potential metrics

        """
        if not event or not hasattr(event, "llm_metrics") or not event.llm_metrics:
            return

        metrics = event.llm_metrics

        if hasattr(metrics, "accumulated_cost"):
            conversation.accumulated_cost = metrics.accumulated_cost

        if hasattr(metrics, "accumulated_token_usage"):
            token_usage = metrics.accumulated_token_usage
            conversation.prompt_tokens = token_usage.prompt_tokens
            conversation.completion_tokens = token_usage.completion_tokens
            conversation.total_tokens = (
                token_usage.prompt_tokens + token_usage.completion_tokens
            )

    async def _handle_git_event(
        self, conversation_id: str, conversation, event
    ) -> None:
        """Handle git-related events.

        Args:
            conversation_id: Conversation ID
            conversation: Conversation metadata
            event: Event to check

        """
        if event and self._is_git_related_event(event):
            logger.info(
                "Git-related event detected, updating conversation branch for %s",
                conversation_id,
                extra={
                    "session_id": conversation_id,
                    "command": getattr(event, "command", "unknown"),
                },
            )
            await self._update_conversation_branch(conversation)

    async def _update_conversation_title(
        self,
        conversation_id: str,
        conversation,
        user_id: str,
        settings: Settings,
        llm_registry: LLMRegistry,
    ) -> None:
        """Update conversation title if needed.

        Args:
            conversation_id: Conversation ID
            conversation: Conversation metadata
            user_id: User ID
            settings: User settings
            llm_registry: LLM registry

        """
        default_title = get_default_conversation_title(conversation_id)

        if conversation.title != default_title:
            return

        # Resolve auto_generate_title from this module at call-time so test patches apply
        import sys as _sys

        _mod = _sys.modules[__name__]
        _auto_gen = getattr(_mod, "auto_generate_title")
        title = await _auto_gen(
            conversation_id, user_id, self.file_store, settings, llm_registry
        )

        if title and not title.isspace():
            conversation.title = title
            await self._emit_title_update(conversation_id, title)
        else:
            conversation.title = default_title

    async def _emit_title_update(self, conversation_id: str, title: str) -> None:
        """Emit title update event to client.

        Args:
            conversation_id: Conversation ID
            title: New title

        """
        try:
            status_update_dict = {
                "status_update": True,
                "type": "info",
                "message": conversation_id,
                "conversation_title": title,
            }
            if self._loop is not None:
                await run_in_loop(
                    self.sio.emit(
                        "forge_event",
                        status_update_dict,
                        to=ROOM_KEY.format(sid=conversation_id),
                    ),
                    self._loop,
                )
            else:
                await self.sio.emit(
                    "forge_event",
                    status_update_dict,
                    to=ROOM_KEY.format(sid=conversation_id),
                )
        except Exception as e:
            logger.error("Error emitting title update event: %s", e)

    def _is_git_related_event(self, event) -> bool:
        """Determine if an event is related to git operations that could change the branch.

        Args:
            event: The event to check

        Returns:
            True if the event is git-related and could change the branch, False otherwise

        """
        if not event or not isinstance(event, CmdOutputObservation):
            return False
        if event.observation == ObservationType.RUN and event.metadata.exit_code == 0:
            command = event.command.lower()
            git_commands = [
                "git checkout",
                "git switch",
                "git merge",
                "git rebase",
                "git reset",
                "git branch",
            ]
            is_git_related = any(git_cmd in command for git_cmd in git_commands)
            if is_git_related:
                logger.debug(
                    "Detected git-related command: %s with exit code %s",
                    command,
                    event.metadata.exit_code,
                    extra={"command": command, "exit_code": event.metadata.exit_code},
                )
            return is_git_related
        return False

    async def _update_conversation_branch(
        self, conversation: ConversationMetadata
    ) -> None:
        """Update the conversation's current branch if it has changed.

        Args:
            conversation: The conversation metadata to update

        """
        try:
            session, runtime = self._get_session_and_runtime(
                conversation.conversation_id
            )
            if not session or not runtime:
                return
            current_branch = self._get_current_workspace_branch(
                runtime, conversation.selected_repository
            )
            if self._should_update_branch(conversation.selected_branch, current_branch):
                self._update_branch_in_conversation(conversation, current_branch)
        except Exception as e:
            logger.warning(
                "Failed to update conversation branch: %s",
                e,
                extra={"session_id": conversation.conversation_id},
            )

    def _get_session_and_runtime(
        self, conversation_id: str
    ) -> tuple["Session" | None, Any | None]:
        """Get the session and runtime for a conversation.

        Args:
            conversation_id: The conversation ID

        Returns:
            Tuple of (session, runtime) or (None, None) if not found

        """
        session = self._local_agent_loops_by_sid.get(conversation_id)
        if not session or not session.agent_session.runtime:
            return (None, None)
        return (session, session.agent_session.runtime)

    def _get_current_workspace_branch(
        self, runtime: Any, selected_repository: str | None
    ) -> str | None:
        """Get the current branch from the workspace.

        Args:
            runtime: The runtime instance
            selected_repository: The selected repository path or None

        Returns:
            The current branch name or None if not found

        """
        if not selected_repository:
            primary_repo_path = None
        else:
            primary_repo_path = selected_repository.split("/")[-1]
        return runtime.get_workspace_branch(primary_repo_path)

    def _should_update_branch(
        self, current_branch: str | None, new_branch: str | None
    ) -> bool:
        """Determine if the branch should be updated.

        Args:
            current_branch: The current branch in conversation metadata
            new_branch: The new branch from the workspace

        Returns:
            True if the branch should be updated, False otherwise

        """
        return new_branch is not None and new_branch != current_branch

    def _update_branch_in_conversation(
        self, conversation: ConversationMetadata, new_branch: str | None
    ) -> None:
        """Update the branch in the conversation metadata.

        Args:
            conversation: The conversation metadata to update
            new_branch: The new branch name

        """
        old_branch = conversation.selected_branch
        conversation.selected_branch = new_branch
        logger.info(
            "Branch changed from %s to %s",
            old_branch,
            new_branch,
            extra={"session_id": conversation.conversation_id},
        )

    async def get_agent_loop_info(
        self, user_id: str | None = None, filter_to_sids: set[str] | None = None
    ):
        """Collect agent loop info objects filtered by user or sessions."""
        results = []
        for session in self._local_agent_loops_by_sid.values():
            if user_id and session.user_id != user_id:
                continue
            if filter_to_sids and session.sid not in filter_to_sids:
                continue
            results.append(self._agent_loop_info_from_session(session))
        return results

    def _agent_loop_info_from_session(self, session: "Session"):
        # Get the current agent state from the controller if available
        agent_state = None
        if session.agent_session.controller:
            agent_state = session.agent_session.controller.get_agent_state()

        return AgentLoopInfo(
            conversation_id=session.sid,
            url=self._get_conversation_url(session.sid),
            session_api_key=None,
            event_store=session.agent_session.event_stream,  # type: ignore[arg-type]
            status=_get_status_from_session(session),
            runtime_status=getattr(
                session.agent_session.runtime, "runtime_status", None
            ),
            agent_state=agent_state,
        )

    def _get_conversation_url(self, conversation_id: str) -> str:
        return f"/api/conversations/{conversation_id}"


def _get_status_from_session(session: "Session") -> ConversationStatus:
    agent_session = session.agent_session
    if agent_session.runtime and agent_session.runtime.runtime_initialized:
        return ConversationStatus.RUNNING
    if getattr(agent_session, "_startup_failed", False):
        return (
            ConversationStatus.STOPPED
        )  # Use STOPPED instead of ERROR which doesn't exist
    return ConversationStatus.STARTING


def _last_updated_at_key(conversation: ConversationMetadata) -> float:
    last_updated_at = conversation.last_updated_at
    return 0.0 if last_updated_at is None else last_updated_at.timestamp()
