"""Session orchestration tying together agent runtime, websockets, and events."""

from __future__ import annotations

import asyncio
import contextlib
import time
from typing import TYPE_CHECKING

from forge.controller.agent import Agent

if TYPE_CHECKING:
    from forge.core.config.condenser_config import (
        BrowserOutputCondenserConfig,
        CondenserPipelineConfig,
        ConversationWindowCondenserConfig,
        LLMSummarizingCondenserConfig,
    )
from forge.core.config.mcp_config import ForgeMCPConfigImpl
from forge.core.exceptions import MicroagentValidationError
from forge.core.logger import forgeLoggerAdapter
from forge.core.schemas import AgentState
from forge.events.action import MessageAction, NullAction
from forge.events.event import Event, EventSource
from forge.events.observation import (
    AgentStateChangedObservation,
    CmdOutputObservation,
    NullObservation,
)
from forge.events.observation.agent import RecallObservation
from forge.events.observation.error import ErrorObservation
from forge.events.serialization import event_from_dict, event_to_dict
from forge.events.stream import EventStreamSubscriber
from forge.runtime.runtime_status import RuntimeStatus
from forge.integrations.provider import PROVIDER_TOKEN_TYPE, CUSTOM_SECRETS_TYPE
from forge.server.constants import ROOM_KEY
from forge.server.session.agent_session import AgentSession
from forge.server.session.conversation_init_data import ConversationInitData

if TYPE_CHECKING:
    from logging import LoggerAdapter

    import socketio  # type: ignore[import-untyped]

    from forge.core.config import ForgeConfig
    from forge.llm.llm_registry import LLMRegistry
    from forge.server.services.conversation_stats import ConversationStats
    from forge.storage.data_models.settings import Settings
    from forge.storage.files import FileStore


class Session:
    """Active conversation session encapsulating runtime, controller, and event stream."""

    sid: str
    sio: socketio.AsyncServer | None
    last_active_ts: int = 0
    is_alive: bool = True
    agent_session: AgentSession
    loop: asyncio.AbstractEventLoop
    config: ForgeConfig
    llm_registry: LLMRegistry
    file_store: FileStore
    user_id: str | None
    logger: LoggerAdapter

    def __init__(
        self,
        sid: str,
        config: ForgeConfig,
        llm_registry: LLMRegistry,
        conversation_stats: ConversationStats,
        file_store: FileStore,
        sio: socketio.AsyncServer | None,
        user_id: str | None = None,
    ) -> None:
        """Wire up agent session state, queue workers, and analytics tracking."""
        self.sid = sid
        self.sio = sio
        self.last_active_ts = int(time.time())
        self.file_store = file_store
        self.logger = forgeLoggerAdapter(extra={"session_id": sid})
        self.llm_registry = llm_registry
        self.conversation_stats = conversation_stats
        self.agent_session = AgentSession(
            sid,
            file_store,
            llm_registry=self.llm_registry,
            conversation_stats=conversation_stats,
            status_callback=self.queue_status_message,
            user_id=user_id,
        )
        self.agent_session.event_stream.subscribe(
            EventStreamSubscriber.SERVER, self.on_event, self.sid
        )
        self.config = config
        from forge.experiments.experiment_manager import ExperimentManagerImpl

        self.config = ExperimentManagerImpl.run_config_variant_test(
            user_id, sid, self.config
        )
        self.loop = asyncio.get_event_loop()
        self.user_id = user_id
        self._publish_queue: asyncio.Queue = asyncio.Queue()
        self._monitor_publish_queue_task: asyncio.Task = self.loop.create_task(
            self._monitor_publish_queue()
        )
        self._wait_websocket_initial_complete: bool = True

    async def close(self) -> None:
        """Close session and notify clients of stopped state."""
        if self.sio:
            await self.sio.emit(
                "oh_event",
                event_to_dict(
                    AgentStateChangedObservation("", AgentState.STOPPED.value)
                ),
                to=ROOM_KEY.format(sid=self.sid),
            )
        self.is_alive = False
        await self.agent_session.close()
        self._monitor_publish_queue_task.cancel()

    def _configure_security_settings(self, settings: Settings) -> None:
        """Configure security settings from the provided settings."""
        self.config.security.confirmation_mode = (
            self.config.security.confirmation_mode
            if settings.confirmation_mode is None
            else settings.confirmation_mode
        )
        self.config.security.security_analyzer = (
            self.config.security.security_analyzer
            if settings.security_analyzer is None
            else settings.security_analyzer
        )

    def _configure_sandbox_settings(self, settings: Settings) -> None:
        """Configure sandbox settings from the provided settings."""
        self.config.sandbox.base_container_image = (
            settings.sandbox_base_container_image
            or self.config.sandbox.base_container_image
        )
        self.config.sandbox.runtime_container_image = (
            settings.sandbox_runtime_container_image
            if settings.sandbox_base_container_image
            or settings.sandbox_runtime_container_image
            else self.config.sandbox.runtime_container_image
        )

        if settings.sandbox_api_key:
            self.config.sandbox.api_key = settings.sandbox_api_key.get_secret_value()

    def _configure_git_settings(self, settings: Settings) -> None:
        """Configure git settings from the provided settings."""
        git_user_name = getattr(settings, "git_user_name", None)
        if git_user_name is not None:
            self.config.git_user_name = git_user_name

        git_user_email = getattr(settings, "git_user_email", None)
        if git_user_email is not None:
            self.config.git_user_email = git_user_email

    def _configure_mcp_settings(self, settings: Settings) -> None:
        """Configure MCP settings from the provided settings."""
        self.logger.debug(
            f"MCP configuration before setup - self.config.mcp_config: {self.config.mcp}"
        )

        mcp_config = getattr(settings, "mcp_config", None)
        if mcp_config is not None:
            self.config.mcp = self.config.mcp.merge(mcp_config)
            self.logger.debug(f"Merged custom MCP Config: {mcp_config}")

        FORGE_mcp_server, FORGE_mcp_stdio_servers = (
            ForgeMCPConfigImpl.create_default_mcp_server_config(
                self.config.mcp_host,
                self.config,
                self.user_id,
            )
        )
        if FORGE_mcp_server:
            self.config.mcp.shttp_servers.append(FORGE_mcp_server)
            self.logger.debug("Added default MCP HTTP server to config")
            self.config.mcp.stdio_servers.extend(FORGE_mcp_stdio_servers)

        self.logger.debug(
            f"MCP configuration after setup - self.config.mcp: {self.config.mcp}"
        )

    def _configure_agent_condenser(
        self, settings: Settings, agent_config, llm_config
    ) -> None:
        """Configure agent condenser if enabled."""
        if settings.enable_default_condenser:
            max_events_for_condenser = settings.condenser_max_size or 120
            from forge.core.config.condenser_config import (
                CondenserPipelineConfig,
                ConversationWindowCondenserConfig,
                BrowserOutputCondenserConfig,
                LLMSummarizingCondenserConfig,
            )

            default_condenser_config = CondenserPipelineConfig(
                condensers=[
                    ConversationWindowCondenserConfig(),
                    BrowserOutputCondenserConfig(attention_window=2),
                    LLMSummarizingCondenserConfig(
                        llm_config=llm_config,
                        keep_first=4,
                        max_size=max_events_for_condenser,
                    ),
                ],
            )
            self.logger.info(
                f'Enabling pipeline condenser with: browser_output_masking(attention_window=2), llm(model="{
                    llm_config.model
                }", base_url="{llm_config.base_url}", keep_first=4, max_size={
                    max_events_for_condenser
                })',
            )
            agent_config.condenser = default_condenser_config

    def _extract_conversation_data(
        self,
        settings: Settings,
    ) -> tuple[
        PROVIDER_TOKEN_TYPE | None,
        str | None,
        str | None,
        CUSTOM_SECRETS_TYPE | None,
        str | None,
    ]:
        """Extract conversation-specific data from settings."""
        git_provider_tokens: PROVIDER_TOKEN_TYPE | None = None
        selected_repository = None
        selected_branch = None
        custom_secrets: CUSTOM_SECRETS_TYPE | None = None
        conversation_instructions = None

        if isinstance(settings, ConversationInitData):
            git_provider_tokens = settings.git_provider_tokens
            selected_repository = settings.selected_repository
            selected_branch = settings.selected_branch
            custom_secrets = settings.custom_secrets
            conversation_instructions = settings.conversation_instructions

        return (
            git_provider_tokens,
            selected_repository,
            selected_branch,
            custom_secrets,
            conversation_instructions,
        )

    async def _start_agent_session(
        self,
        agent,
        max_iterations: int,
        max_budget_per_task: float | None,
        git_provider_tokens: PROVIDER_TOKEN_TYPE | None,
        custom_secrets: CUSTOM_SECRETS_TYPE | None,
        selected_repository: str | None,
        selected_branch: str | None,
        initial_message: MessageAction | None,
        conversation_instructions: str | None,
        replay_json: str | None,
    ) -> None:
        """Start the agent session with error handling."""
        try:
            await self.agent_session.start(
                runtime_name=self.config.runtime,
                config=self.config,
                agent=agent,
                max_iterations=max_iterations,
                max_budget_per_task=max_budget_per_task,
                agent_to_llm_config=self.config.get_agent_to_llm_config_map(),
                agent_configs=self.config.get_agent_configs(),
                git_provider_tokens=git_provider_tokens,
                custom_secrets=custom_secrets,
                selected_repository=selected_repository,
                selected_branch=selected_branch,
                initial_message=initial_message,
                conversation_instructions=conversation_instructions,
                replay_json=replay_json,
            )
        except MicroagentValidationError as e:
            self.logger.exception(f"Error creating agent_session: {e}")
            await self.send_error(f"Failed to create agent session: {e!s}")
            return
        except ValueError as e:
            self.logger.exception(f"Error creating agent_session: {e}")
            error_message = str(e)
            if "microagent" in error_message.lower():
                await self.send_error(
                    f"Failed to create agent session: {error_message}"
                )
            else:
                await self.send_error("Failed to create agent session: ValueError")
            return
        except Exception as e:
            self.logger.exception(f"Error creating agent_session: {e}")
            await self.send_error(
                f"Failed to create agent session: {e.__class__.__name__}"
            )
            return

    async def initialize_agent(
        self,
        settings: Settings,
        initial_message: MessageAction | None,
        replay_json: str | None,
    ) -> None:
        """Initialize the agent with the provided settings."""
        # Set loading state
        self.agent_session.event_stream.add_event(
            AgentStateChangedObservation("", AgentState.LOADING),
            EventSource.ENVIRONMENT,
        )

        # Get agent class
        agent_cls = settings.agent or self.config.default_agent

        # Configure various settings
        self._configure_security_settings(settings)
        self._configure_sandbox_settings(settings)
        self._configure_git_settings(settings)
        self._configure_mcp_settings(settings)

        # Set additional configuration
        max_iterations = settings.max_iterations or self.config.max_iterations
        max_budget_per_task = (
            settings.max_budget_per_task
            if settings.max_budget_per_task is not None
            else self.config.max_budget_per_task
        )

        # Get agent configuration
        agent_config = self.config.get_agent_config(agent_cls)
        agent_name = agent_cls if agent_cls is not None else "agent"
        llm_config = self.config.get_llm_config_from_agent(agent_name)

        # Configure condenser if enabled
        self._configure_agent_condenser(settings, agent_config, llm_config)

        # Create agent
        agent = Agent.get_cls(agent_cls)(agent_config, self.llm_registry)
        self.llm_registry.retry_listner = self._notify_on_llm_retry

        # Extract conversation data
        (
            git_provider_tokens,
            selected_repository,
            selected_branch,
            custom_secrets,
            conversation_instructions,
        ) = self._extract_conversation_data(settings)

        # Start agent session
        await self._start_agent_session(
            agent,
            max_iterations,
            max_budget_per_task,
            git_provider_tokens,
            custom_secrets,
            selected_repository,
            selected_branch,
            initial_message,
            conversation_instructions,
            replay_json,
        )

    def _notify_on_llm_retry(self, retries: int, max: int) -> None:
        self.queue_status_message(
            "info", RuntimeStatus.LLM_RETRY, f"Retrying LLM request, {retries} / {max}"
        )

    def on_event(self, event: Event) -> None:
        """Synchronous event callback that delegates to async handler.

        Args:
            event: Event to process

        """
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            loop = None

        if loop:
            loop.create_task(self._on_event(event))
            return

        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = None

        if loop is None:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
        loop.run_until_complete(self._on_event(event))

    async def _on_event(self, event: Event) -> None:
        """Callback function for events that mainly come from the agent.

        Event is the base class for any agent action and observation.

        Args:
            event: The agent event (Observation or Action).

        """
        if isinstance(event, NullAction):
            return
        if isinstance(event, NullObservation):
            return
        if event.source in (EventSource.AGENT, EventSource.USER):
            await self.send(event_to_dict(event))
        elif event.source == EventSource.ENVIRONMENT and isinstance(
            event,
            (CmdOutputObservation, AgentStateChangedObservation, RecallObservation),
        ):
            event_dict = event_to_dict(event)
            event_dict["source"] = EventSource.AGENT
            # Debug logging for agent state changes
            if isinstance(event, AgentStateChangedObservation):
                self.logger.info(
                    f"DEBUG: AgentStateChangedObservation received - state: {event.agent_state}, reason: {event.reason}, sending to WebSocket",
                    extra={"session_id": self.sid},
                )
            await self.send(event_dict)
            if (
                isinstance(event, AgentStateChangedObservation)
                and event.agent_state == AgentState.ERROR
            ):
                self.logger.error(
                    f"Agent status error: {event.reason}",
                    extra={"signal": "agent_status_error"},
                )
        elif isinstance(event, ErrorObservation):
            event_dict = event_to_dict(event)
            event_dict["source"] = EventSource.AGENT
            await self.send(event_dict)

    async def dispatch(self, data: dict) -> None:
        """Dispatch incoming event data to appropriate handlers."""
        # Log dispatch start
        self._log_dispatch_start(data)

        # Parse event from data
        event = event_from_dict(data.copy())
        self._log_parsed_event(event)

        # Handle MetaSOP orchestration if applicable
        if await self._handle_metasop_dispatch(event):
            return

        # Handle image validation for message actions
        if await self._handle_image_validation(event):
            return

        # Add event to stream
        self.agent_session.event_stream.add_event(event, EventSource.USER)

    def _log_dispatch_start(self, data: dict) -> None:
        """Log the start of dispatch operation."""
        with contextlib.suppress(Exception):
            self.logger.info(
                f"Dispatch called with data: {data}",
                extra={"signal": "dispatch_called"},
            )

    def _log_parsed_event(self, event) -> None:
        """Log the parsed event information."""
        with contextlib.suppress(Exception):
            self.logger.info(
                f"Parsed event: {type(event).__name__} content={getattr(event, 'content', None)!r}",
                extra={"signal": "dispatch_parsed_event"},
            )

    async def _handle_metasop_dispatch(self, event) -> bool:
        """Handle MetaSOP orchestration dispatch. Returns True if handled."""
        try:
            if not isinstance(event, MessageAction):
                return False

            content = (event.content or "").strip()
            if not content.lower().startswith("sop:"):
                return False

            await self._send_status_message(
                "info", RuntimeStatus.READY, "Starting MetaSOP orchestration…"
            )

            # Create and start MetaSOP runner task
            asyncio.create_task(self._run_metasop_orchestration(content))
            return True

        except Exception as e:
            await self._handle_metasop_error(e)
            return False

    async def _run_metasop_orchestration(self, content: str) -> None:
        """Run MetaSOP orchestration asynchronously."""
        from forge.metasop.router import run_metasop_for_conversation

        try:
            self.logger.info(
                f"Starting clean MetaSOP runner for conversation={self.sid}",
                extra={"signal": "metasop_start"},
            )

            await run_metasop_for_conversation(
                conversation_id=self.sid,
                user_id=self.user_id,
                raw_message=content,
                repo_root=None,
                llm_registry=self.llm_registry,
            )

            self.logger.info(
                f"MetaSOP runner completed for conversation={self.sid}",
                extra={"signal": "metasop_completed"},
            )

        except Exception as e:
            self._handle_metasop_runner_error(e)

    def _handle_metasop_runner_error(self, error: Exception) -> None:
        """Handle errors in MetaSOP runner."""
        with contextlib.suppress(Exception):
            self.logger.exception(
                f"Unhandled exception in MetaSOP runner for sid={self.sid}: {error}"
            )

    async def _handle_metasop_error(self, error: Exception) -> None:
        """Handle errors in MetaSOP dispatch."""
        with contextlib.suppress(Exception):
            self.logger.exception(f"Error while handling MetaSOP dispatch: {error}")

        with contextlib.suppress(Exception):
            await self._send_status_message(
                "debug", RuntimeStatus.ERROR, f"MetaSOP dispatch error: {error}"
            )

    async def _handle_image_validation(self, event) -> bool:
        """Handle image validation for message actions. Returns True if validation failed."""
        if not isinstance(event, MessageAction) or not event.image_urls:
            return False

        controller = self.agent_session.controller
        if not controller:
            return False

        # Check if vision is disabled
        if controller.agent.llm.config.disable_vision:
            await self.send_error(
                "Support for images is disabled for this model, try without an image."
            )
            return True

        # Check if model supports vision
        if not controller.agent.llm.vision_is_active():
            await self.send_error(
                "Model does not support image upload, change to a different model or try without an image.",
            )
            return True

        return False

    async def send(self, data: dict[str, object]) -> None:
        """Queue data for publishing to WebSocket clients.

        Args:
            data: Data dictionary to send

        """
        self._publish_queue.put_nowait(data)

    async def _monitor_publish_queue(self) -> None:
        try:
            while True:
                data: dict = await self._publish_queue.get()
                await self._send(data)
        except asyncio.CancelledError:
            return

    async def _send(self, data: dict[str, object]) -> bool:
        """Send data to websocket with retry logic.

        Args:
            data: Data dictionary to send

        Returns:
            True if sent successfully, False otherwise

        """
        try:
            if not self.is_alive:
                return False

            if self.sio:
                await self._wait_for_client_connection()

                if self._should_drop_event(data):
                    return True

                await self._emit_to_client(data)

            # Removed artificial delay for instant streaming
            # await asyncio.sleep(0.001)
            self.last_active_ts = int(time.time())
            return True

        except RuntimeError as e:
            self.logger.exception(f"Error sending data to websocket: {e!s}")
            self.is_alive = False
            return False

    async def _wait_for_client_connection(self) -> None:
        """Wait for client to connect to room.

        Waits up to 2 seconds for a client to join the room.
        """
        _start_time = time.time()
        _waiting_times = 1

        sio = self.sio
        if sio is None:
            return
        manager = getattr(sio, "manager", None)
        if manager is None:
            return

        while (
            self._wait_websocket_initial_complete
            and time.time() - _start_time < 2
            and not bool(manager.rooms.get("/", {}).get(ROOM_KEY.format(sid=self.sid)))  # type: ignore[arg-type]
        ):
            self.logger.warning(
                f"There is no listening client in the current room, waiting for the {
                    _waiting_times
                }th attempt: {self.sid}",
            )
            _waiting_times += 1
            await asyncio.sleep(0.1)

    def _should_drop_event(self, data: dict) -> bool:
        """Check if event should be dropped due to null values.

        Args:
            data: Event data

        Returns:
            True if event should be dropped

        """
        if isinstance(data, dict) and (
            data.get("observation") == "null" or data.get("action") == "null"
        ):
            with contextlib.suppress(Exception):
                self.logger.warning(
                    'Dropping event with literal "null" in observation/action',
                    extra={"payload_sample": data},
                )
            return True
        return False

    async def _emit_to_client(self, data: dict) -> None:
        """Emit event to client via websocket.

        Args:
            data: Event data to emit

        """
        self._wait_websocket_initial_complete = False

        # Performance logging for streaming events
        event_type = data.get("action") or data.get("observation") or "unknown"
        event_id = data.get("id", "N/A")
        self.logger.debug(f"📡 Emitting to WebSocket: {event_type} (id={event_id})")

        # Special logging for state changes
        if data.get("observation") == "agent_state_changed":
            self.logger.info(
                f"🔄 Agent state changed to: {data.get('extras', {}).get('agent_state', 'unknown')}"
            )

        if self.sio is None:
            self.logger.warning("Socket.IO server not available; dropping event.")
            return
        await self.sio.emit("oh_event", data, to=ROOM_KEY.format(sid=self.sid))

    async def send_error(self, message: str) -> None:
        """Sends an error message to the client."""
        await self.send({"error": True, "message": message})

    async def _send_status_message(
        self, msg_type: str, runtime_status: RuntimeStatus, message: str
    ) -> None:
        """Sends a status message to the client."""
        if msg_type == "error":
            agent_session = self.agent_session
            controller = self.agent_session.controller
            if controller is not None and (not agent_session.is_closed()):
                await controller.set_agent_state_to(AgentState.ERROR)
            self.logger.error(
                f"Agent status error: {message}", extra={"signal": "agent_status_error"}
            )
        await self.send(
            {
                "status_update": True,
                "type": msg_type,
                "id": runtime_status.value,
                "message": message,
            }
        )

    def queue_status_message(
        self, msg_type: str, runtime_status: RuntimeStatus, message: str
    ) -> None:
        """Queues a status message to be sent asynchronously."""
        asyncio.run_coroutine_threadsafe(
            self._send_status_message(msg_type, runtime_status, message), self.loop
        )
