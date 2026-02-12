"""Runtime session orchestration for agents, including startup and lifecycle."""

from __future__ import annotations

import asyncio
import json
import time
from types import MappingProxyType
from typing import TYPE_CHECKING, Callable, Mapping, cast

from backend.controller import AgentController
from backend.controller.replay import ReplayManager
from backend.controller.state.state import State
from backend.core.exceptions import AgentRuntimeUnavailableError
from backend.core.logger import forgeLoggerAdapter
from backend.core.schemas import AgentState
from backend.events.action import ChangeAgentStateAction, MessageAction
from backend.events.observation import ErrorObservation
from backend.events.event import Event, EventSource
from backend.integrations.provider import (
    CUSTOM_SECRETS_TYPE,
    PROVIDER_TOKEN_TYPE,
    CustomSecret,
    ProviderToken,
    ProviderType,
)
from backend.server.shared import get_event_service_adapter
from backend.mcp import add_mcp_tools_to_agent
from backend.memory.memory import Memory
from backend.runtime import RuntimeAcquireResult, runtime_orchestrator
from backend.runtime.runtime_status import RuntimeStatus
from backend.server.types import LLMAuthenticationError
from backend.server.utils.error_formatter import format_error_for_user
from backend.storage.data_models.user_secrets import UserSecrets
from backend.utils.async_utils import EXECUTOR, call_sync_from_async
from backend.utils.shutdown_listener import should_continue
from .constants import (
    WAIT_TIME_BEFORE_CLOSE,
    WAIT_TIME_BEFORE_CLOSE_INTERVAL,
)

if TYPE_CHECKING:
    from logging import LoggerAdapter

    from backend.controller.agent import Agent
    from backend.events.stream import EventStream
    from backend.models.llm_registry import LLMRegistry
    from backend.integrations.provider import ProviderHandler
    from backend.instruction.playbook import BasePlaybook
    from backend.runtime.base import Runtime
    from backend.server.services.conversation_stats import ConversationStats
    from backend.storage.files import FileStore
    from backend.storage.data_models.settings import Settings
else:
    # Runtime imports - these are only used at runtime, not for type checking
    EventStream = object  # type: ignore[assignment,misc]
    LLMRegistry = object  # type: ignore[assignment,misc]
    FileStore = object  # type: ignore[assignment,misc]

from backend.core.config import AgentConfig, LLMConfig, ForgeConfig


# Backward compatibility: expose EventStream at runtime (tests monkeypatch this symbol).
try:
    from backend.events.stream import EventStream as _EventStream  # type: ignore
except Exception:  # pragma: no cover - defensive fallback
    pass  # Already set to object in else block above


class AgentSession:
    """Represents a session with an Agent.

    Attributes:
        controller: The AgentController instance for controlling the agent.

    """

    sid: str
    user_id: str | None
    event_stream: "EventStream"
    llm_registry: "LLMRegistry"
    file_store: "FileStore"
    controller: AgentController | None = None
    runtime: Runtime | None = None
    memory: Memory | None = None
    _starting: bool = False
    _startup_failed: bool = False
    _started_at: float = 0
    _closed: bool = False
    loop: asyncio.AbstractEventLoop | None = None
    logger: LoggerAdapter

    def __init__(
        self,
        sid: str,
        file_store: FileStore,
        llm_registry: LLMRegistry,
        conversation_stats: ConversationStats,
        status_callback: Callable | None = None,
        user_id: str | None = None,
    ) -> None:
        """Initializes a new instance of the Session class.

        Parameters:
        - sid: The session ID
        - file_store: Instance of the FileStore
        """
        self.sid = sid
        adapter = get_event_service_adapter()
        session_info = adapter.start_session(
            session_id=sid,
            user_id=user_id,
            labels={"source": "agent_session"},
        )
        self.event_stream = adapter.get_event_stream(session_info["session_id"])
        self.file_store = file_store
        self._status_callback = status_callback
        self.user_id = user_id
        self.logger = forgeLoggerAdapter(extra={"session_id": sid, "user_id": user_id})
        self.llm_registry = llm_registry
        self.conversation_stats = conversation_stats
        self._runtime_acquire_result: RuntimeAcquireResult | None = None
        self._repo_directory: str | None = None
        self._selected_repository: str | None = None
        self._selected_branch: str | None = None

    async def start(
        self,
        runtime_name: str,
        config: ForgeConfig,
        agent: Agent,
        max_iterations: int,
        git_provider_tokens: PROVIDER_TOKEN_TYPE | None = None,
        custom_secrets: CUSTOM_SECRETS_TYPE | None = None,
        max_budget_per_task: float | None = None,
        agent_to_llm_config: dict[str, LLMConfig] | None = None,
        agent_configs: dict[str, AgentConfig] | None = None,
        selected_repository: str | None = None,
        selected_branch: str | None = None,
        initial_message: MessageAction | None = None,
        conversation_instructions: str | None = None,
        replay_json: str | None = None,
        user_settings: Settings | None = None,
    ) -> None:
        """Starts the Agent session.

        Parameters:
        - runtime_name: The name of the runtime associated with the session.
        - config: The Forge configuration for this session.
        - agent: The Agent instance to start.
        - max_iterations: Maximum iterations for the agent.
        - max_budget_per_task: Per-task budget for the agent.
        - agent_to_llm_config: Mapping of agent to LLM configurations.
        - agent_configs: Additional agent configuration mapping.
        - user_settings: User settings for this session.
        """
        # Validate session state
        if not self._validate_session_state():
            return

        # Initialize session startup
        startup_state = self._initialize_session_startup()
        runtime_connected = False  # Initialize to False in case of exception

        self._selected_repository = selected_repository
        self._selected_branch = selected_branch

        self.config = config
        error_msg = None
        error_exception = None
        error_context = None
        try:
            # Validate API keys before starting anything slow
            if agent_to_llm_config:
                for agent_name, llm_config in agent_to_llm_config.items():
                    try:
                        self._validate_api_key_for_model(llm_config)
                    except LLMAuthenticationError as e:
                        # Add model/provider context to error
                        error_context = {
                            "model": llm_config.model or "unknown",
                            "agent": agent_name,
                            "session_id": self.sid,
                        }
                        # Try to extract provider from model name
                        model_name = llm_config.model or ""
                        if "/" in model_name:
                            provider_name = model_name.split("/")[0].title()
                            error_context["provider"] = provider_name
                        elif "claude" in model_name.lower():
                            error_context["provider"] = "Anthropic (Claude)"
                        elif "gpt" in model_name.lower() or "openai" in model_name.lower():
                            error_context["provider"] = "OpenAI"
                        elif "gemini" in model_name.lower():
                            error_context["provider"] = "Google (Gemini)"
                        raise

            # Setup runtime and providers
            runtime_connected = await self._setup_runtime_and_providers(
                runtime_name,
                config,
                agent,
                git_provider_tokens,
                custom_secrets,
                selected_repository,
                selected_branch,
            )

            # Setup memory and MCP tools
            await self._setup_memory_and_mcp_tools(
                selected_repository,
                selected_branch,
                conversation_instructions,
                custom_secrets,
                config,
                agent,
                user_settings=user_settings,
            )

            # Setup controller and handle replay
            initial_message = await self._setup_controller_and_handle_replay(
                replay_json,
                initial_message,
                agent,
                config,
                max_iterations,
                max_budget_per_task,
                agent_to_llm_config,
                agent_configs,
            )

            # Start agent execution
            self.logger.info(
                "Starting agent execution; has_initial_message=%s",
                bool(initial_message),
                extra={"signal": "agent_start"},
            )
            self._start_agent_execution(initial_message)

            startup_state["finished"] = True

        except Exception as e:
            error_msg = str(e)
            error_exception = e
            # Preserve error context if it was set
            if error_context and hasattr(e, '__dict__'):
                e.__dict__.update(error_context)
            raise
        finally:
            self._finalize_session_startup(startup_state, runtime_connected, error_msg, error_exception, error_context)

    def _validate_session_state(self) -> bool:
        """Validate that the session can be started."""
        if self.controller or self.runtime:
            msg = "Session already started. You need to close this session and start a new one."
            raise RuntimeError(msg)
        if self._closed:
            self.logger.warning("Session closed before starting")
            return False
        return True

    def _validate_api_key_for_model(self, llm_config: LLMConfig) -> None:
        """Validate API key requirements for the given model.

        Args:
            llm_config: LLM configuration containing API key and model name

        Raises:
            LLMAuthenticationError: If API key validation fails

        """
        # Validate API key presence and non-emptiness
        if not llm_config.api_key or llm_config.api_key.get_secret_value().isspace():
            model_name = llm_config.model or "the selected model"
            # Extract provider name from model if possible
            provider_name = "your AI provider"
            if "/" in model_name:
                provider_name = model_name.split("/")[0].title()
            elif "claude" in model_name.lower():
                provider_name = "Anthropic (Claude)"
            elif "gpt" in model_name.lower() or "openai" in model_name.lower():
                provider_name = "OpenAI"
            elif "gemini" in model_name.lower():
                provider_name = "Google (Gemini)"
            
            raise LLMAuthenticationError(
                f"Error authenticating with the LLM provider. Please check your API key"
            )

    def _initialize_session_startup(self):
        """Initialize session startup state."""
        self._starting = True
        started_at = time.time()
        self._started_at = started_at
        return {
            "started_at": started_at,
            "finished": False,
            "runtime_connected": False,
            "restored_state": False,
        }

    async def _setup_runtime_and_providers(
        self,
        runtime_name,
        config,
        agent,
        git_provider_tokens,
        custom_secrets,
        selected_repository,
        selected_branch,
    ):
        """Setup runtime and provider handlers."""
        from backend.server.session.runtime_factory import create_runtime

        result = await create_runtime(
            runtime_name=runtime_name,
            config=config,
            agent=agent,
            sid=self.sid,
            user_id=self.user_id,
            event_stream=self.event_stream,
            llm_registry=self.llm_registry,
            status_callback=self._status_callback,
            session_logger=self.logger,
            git_provider_tokens=git_provider_tokens,
            custom_secrets=custom_secrets,
            selected_repository=selected_repository,
            selected_branch=selected_branch,
        )
        if result.success:
            self.runtime = result.runtime
            self._runtime_acquire_result = result.acquire_result
            self._repo_directory = result.repo_directory

        # Setup provider handlers
        await self._setup_provider_handlers(git_provider_tokens, custom_secrets)

        return result.success

    async def _setup_provider_handlers(
        self, git_provider_tokens, custom_secrets
    ) -> None:
        """Setup provider handlers for git and custom secrets."""
        if git_provider_tokens:
            from backend.integrations.provider import ProviderHandler

            provider_handler = ProviderHandler(provider_tokens=git_provider_tokens)
            await provider_handler.set_event_stream_secrets(self.event_stream)  # type: ignore[arg-type]

        if custom_secrets:
            custom_secrets_handler = UserSecrets(custom_secrets=custom_secrets)
            custom_secrets_handler.set_event_stream_secrets(self.event_stream)  # type: ignore[arg-type]

    async def _setup_memory_and_mcp_tools(
        self,
        selected_repository,
        selected_branch,
        conversation_instructions,
        custom_secrets,
        config,
        agent,
        user_settings: Settings | None = None,
    ) -> None:
        """Setup memory and MCP tools."""
        # Create memory
        custom_secret_dict: dict[str, CustomSecret] = {}
        if custom_secrets:
            custom_secret_dict = {key: value for key, value in custom_secrets.items()}
        custom_secrets_handler = UserSecrets(custom_secrets=custom_secret_dict)
        repo_directory = self._repo_directory
        if repo_directory is None and selected_repository:
            repo_directory = selected_repository.split("/")[-1]
        
        # Determine working directory for memory
        working_dir = "."
        if self.runtime:
            working_dir = str(self.runtime.workspace_root)

        self.memory = await self._create_memory(
            selected_repository=selected_repository,
            repo_directory=repo_directory,
            selected_branch=selected_branch,
            conversation_instructions=conversation_instructions,
            custom_secrets_descriptions=custom_secrets_handler.get_custom_secrets_descriptions(),
            working_dir=working_dir,
            user_id=self.user_id,
            user_settings=user_settings,
        )

        # Add MCP tools if enabled
        if self.runtime and agent.config.enable_mcp:
            await add_mcp_tools_to_agent(agent, self.runtime, self.memory)

    async def _setup_controller_and_handle_replay(
        self,
        replay_json,
        initial_message,
        agent,
        config,
        max_iterations,
        max_budget_per_task,
        agent_to_llm_config,
        agent_configs,
    ):
        """Setup controller and handle replay if specified."""
        if replay_json:
            initial_message = self._run_replay(
                initial_message,
                replay_json,
                agent,
                config,
                max_iterations,
                max_budget_per_task,
                agent_to_llm_config,
                agent_configs,
            )
        else:
            self.controller, _restored_state = self._create_controller(
                agent,
                config.security.confirmation_mode,
                max_iterations,
                max_budget_per_task=max_budget_per_task,
                agent_to_llm_config=agent_to_llm_config,
                agent_configs=agent_configs,
            )
        return initial_message

    def _start_agent_execution(self, initial_message) -> None:
        """Start agent execution with appropriate initial state."""
        if not self._closed:
            if initial_message:
                self.logger.info(
                    "Adding initial user message and switching agent state to RUNNING",
                    extra={"signal": "agent_start"},
                )
                self.event_stream.add_event(initial_message, EventSource.USER)  # type: ignore[attr-defined]
                self.logger.debug(
                    "Enqueuing ChangeAgentStateAction(RUNNING)",
                    extra={"signal": "agent_start"},
                )
                self.event_stream.add_event(  # type: ignore[attr-defined]
                    ChangeAgentStateAction(AgentState.RUNNING), EventSource.ENVIRONMENT
                )
            else:
                self.logger.info(
                    "No initial message; queueing ChangeAgentStateAction(AWAITING_USER_INPUT)",
                    extra={"signal": "agent_start"},
                )
                self.logger.debug(
                    "Enqueuing ChangeAgentStateAction(AWAITING_USER_INPUT)",
                    extra={"signal": "agent_start"},
                )
                self.event_stream.add_event(  # type: ignore[attr-defined]
                    ChangeAgentStateAction(AgentState.AWAITING_USER_INPUT),
                    EventSource.ENVIRONMENT,
                )

    def _finalize_session_startup(
        self, startup_state, runtime_connected, error_msg=None, error_exception=None, error_context=None
    ) -> None:
        """Finalize session startup and log results."""
        self._starting = False
        success = startup_state["finished"] and runtime_connected
        self._startup_failed = not success
        duration = time.time() - startup_state["started_at"]

        log_metadata = {
            "signal": "agent_session_start",
            "success": success,
            "duration": duration,
            "restored_state": startup_state["restored_state"],
        }

        if success:
            self.logger.info(
                f"Agent session start succeeded in {duration}s", extra=log_metadata
            )
        else:
            self.logger.error(
                f"Agent session start failed in {duration}s", extra=log_metadata
            )
            # Format error for user-friendly display
            if error_exception:
                try:
                    # Merge error context with session context
                    context = {"session_id": self.sid}
                    if error_context:
                        context.update(error_context)
                    # Also try to extract model/provider from exception attributes
                    if hasattr(error_exception, '__dict__'):
                        for key in ["model", "provider", "agent"]:
                            if key in error_exception.__dict__:
                                context[key] = error_exception.__dict__[key]
                    
                    formatted_error = format_error_for_user(
                        error_exception,
                        context=context
                    )
                    # Include formatted error as JSON in content so frontend can parse it
                    error_content = json.dumps(formatted_error)
                except Exception as format_err:
                    self.logger.warning(f"Failed to format error: {format_err}")
                    error_content = error_msg or "Agent session failed to initialize"
            else:
                error_content = error_msg or "Agent session failed to initialize"
            
            # Add error observation to the event stream so the UI can show it
            if self.event_stream:
                self.event_stream.add_event(
                    ErrorObservation(
                        content=error_content,
                    ),
                    EventSource.ENVIRONMENT,
                )
                # Also send an agent state change to ERROR so the UI stops "Initializing..."
                from backend.events.observation import AgentStateChangedObservation

                # Use user-friendly message for state change
                user_message = error_msg or "Agent session failed to initialize"
                if error_exception:
                    try:
                        formatted = format_error_for_user(
                            error_exception,
                            context={"session_id": self.sid}
                        )
                        user_message = formatted.get("message", user_message)
                    except Exception:
                        pass

                self.event_stream.add_event(
                    AgentStateChangedObservation(
                        content=user_message,
                        agent_state=AgentState.ERROR,
                        reason=user_message,
                    ),
                    EventSource.ENVIRONMENT,
                )

    async def close(self) -> None:
        """Closes the Agent session, releasing all resources via try/finally."""
        if self._closed:
            return
        self._closed = True
        while self._starting and should_continue():
            self.logger.debug(
                f"Waiting for initialization to finish before closing session {self.sid}"
            )
            await asyncio.sleep(WAIT_TIME_BEFORE_CLOSE_INTERVAL)
            # Break only after exceeding the maximum wait window
            if time.time() >= self._started_at + WAIT_TIME_BEFORE_CLOSE:
                self.logger.error(
                    f"Waited too long for initialization to finish before closing session {self.sid}"
                )
                break
        try:
            if self.event_stream is not None:
                self.event_stream.close()  # type: ignore[attr-defined]
        except Exception as e:
            self.logger.warning("Error closing event stream: %s", e)
        try:
            if self.controller is not None:
                self.controller.save_state()
                await self.controller.close()
        except Exception as e:
            self.logger.warning("Error closing controller: %s", e)
        finally:
            # Always release runtime — even if controller.close() throws
            try:
                if self._runtime_acquire_result is not None:
                    runtime_orchestrator.release(self._runtime_acquire_result)
                    self._runtime_acquire_result = None
                    self.runtime = None
                elif self.runtime is not None:
                    EXECUTOR.submit(self.runtime.close)
                    self.runtime = None
            except Exception as e:
                self.logger.warning("Error releasing runtime: %s", e)

    def _run_replay(
        self,
        initial_message: MessageAction | None,
        replay_json: str,
        agent: Agent,
        config: ForgeConfig,
        max_iterations: int,
        max_budget_per_task: float | None,
        agent_to_llm_config: dict[str, LLMConfig] | None,
        agent_configs: dict[str, AgentConfig] | None,
    ) -> MessageAction:
        """Replays a trajectory from a JSON file.

        Note that once the replay session finishes, the controller will continue to run with
        further user instructions, so we still need to pass llm configs, budget, etc., even
        though the replay itself does not call LLM or cost money.
        """
        assert initial_message is None
        replay_events = ReplayManager.get_replay_events(json.loads(replay_json))
        self.controller, _ = self._create_controller(
            agent,
            config.security.confirmation_mode,
            max_iterations,
            max_budget_per_task=max_budget_per_task,
            agent_to_llm_config=agent_to_llm_config,
            agent_configs=agent_configs,
            replay_events=replay_events[1:],
        )
        assert isinstance(replay_events[0], MessageAction)
        return replay_events[0]

    def override_provider_tokens_with_custom_secret(
        self,
        git_provider_tokens: PROVIDER_TOKEN_TYPE | None,
        custom_secrets: CUSTOM_SECRETS_TYPE | None,
    ):
        """Filter out provider tokens that have been overridden by custom secrets.

        Args:
            git_provider_tokens: Provider tokens from configuration
            custom_secrets: Custom secrets that may override provider tokens

        Returns:
            Filtered provider tokens (immutable)

        """
        if git_provider_tokens and custom_secrets:
            from backend.integrations.provider import ProviderHandler

            tokens = {
                provider: token
                for provider, token in git_provider_tokens.items()
                if not (
                    ProviderHandler.get_provider_env_key(provider) in custom_secrets
                    or ProviderHandler.get_provider_env_key(provider).upper()
                    in custom_secrets
                )
            }
            return MappingProxyType(tokens)
        return git_provider_tokens

    def _create_controller(
        self,
        agent: Agent,
        confirmation_mode: bool,
        max_iterations: int,
        max_budget_per_task: float | None = None,
        agent_to_llm_config: dict[str, LLMConfig] | None = None,
        agent_configs: dict[str, AgentConfig] | None = None,
        replay_events: list[Event] | None = None,
    ) -> tuple[AgentController, bool]:
        """Creates an AgentController instance.

        Parameters:
        - agent:
        - confirmation_mode: Whether to use confirmation mode
        - max_iterations:
        - max_budget_per_task:
        - agent_to_llm_config:
        - agent_configs:

        Returns:
            Agent Controller and a bool indicating if state was restored from a previous conversation

        """
        if self.controller is not None:
            msg = "Controller already created"
            raise RuntimeError(msg)
        if self.runtime is None:
            msg = "Runtime must be initialized before the agent controller"
            raise RuntimeError(msg)
        msg = f"\n--------------------------------- Forge Configuration ---------------------------------\nLLM: {
            agent.llm.config.model
        }\nBase URL: {agent.llm.config.base_url}\nAgent: {agent.name}\nRuntime: {
            self.runtime.__class__.__name__
        }\nPlugins: {
            (
                [p.name for p in agent.sandbox_plugins]
                if agent.sandbox_plugins
                else 'None'
            )
        }\n-------------------------------------------------------------------------------------------"
        self.logger.debug(msg)
        initial_state = self._maybe_restore_state()
        controller = AgentController(
            sid=self.sid,
            user_id=self.user_id,
            file_store=self.file_store,
            event_stream=self.event_stream,
            conversation_stats=self.conversation_stats,
            agent=agent,
            iteration_delta=max_iterations,
            budget_per_task_delta=max_budget_per_task,
            agent_to_llm_config=agent_to_llm_config,
            agent_configs=agent_configs,
            confirmation_mode=confirmation_mode,
            headless_mode=False,
            status_callback=self._status_callback,
            initial_state=initial_state,
            replay_events=replay_events,
            security_analyzer=self.runtime.security_analyzer if self.runtime else None,
        )
        return (controller, initial_state is not None)

    async def _create_memory(
        self,
        selected_repository: str | None,
        repo_directory: str | None,
        selected_branch: str | None,
        conversation_instructions: str | None,
        custom_secrets_descriptions: dict[str, str],
        working_dir: str,
        user_id: str | None = None,
        user_settings: Settings | None = None,
    ) -> Memory:
        memory = Memory(
            event_stream=self.event_stream,
            sid=self.sid,
            status_callback=self._status_callback,
            user_id=user_id,
        )
        # Apply Knowledge Base settings if available
        if user_settings and user_settings.knowledge_base:
            kb_settings = user_settings.knowledge_base
            # If we need to pass more settings to Memory, we can do it here
            # For now, KnowledgeBaseManager in Memory uses default settings 
            # or we can add a method to Memory to update KB settings
            if hasattr(memory, "set_knowledge_base_settings"):
                memory.set_knowledge_base_settings(kb_settings)

        if self.runtime:
            memory.set_runtime_info(
                self.runtime, custom_secrets_descriptions, working_dir
            )
            memory.set_conversation_instructions(conversation_instructions)
            playbooks: list[BasePlaybook] = await call_sync_from_async(
                self.runtime.get_playbooks_from_selected_repo,
                selected_repository or None,
            )
            memory.load_user_workspace_playbooks(playbooks)
            if selected_repository and repo_directory:
                memory.set_repository_info(
                    selected_repository, repo_directory, selected_branch
                )
        return memory

    def get_state(self) -> AgentState | None:
        """Get current agent state.

        Returns:
            Current agent state, ERROR if timed out, None if still initializing

        """
        if controller := self.controller:
            return controller.state.agent_state
        if time.time() > self._started_at + WAIT_TIME_BEFORE_CLOSE:
            return AgentState.ERROR
        return None

    def _maybe_restore_state(self) -> State | None:
        """Helper method to handle state restore logic."""
        restored_state = None
        try:
            restored_state = State.restore_from_session(
                self.sid, self.file_store, self.user_id
            )
            self.logger.debug(f"Restored state from session, sid: {self.sid}")
        except Exception as e:
            if self.event_stream.get_latest_event_id() > 0:  # type: ignore[attr-defined]
                self.logger.warning(f"State could not be restored: {e}")
            else:
                self.logger.debug("No events found, no state to restore")
        return restored_state

    def is_closed(self) -> bool:
        """Check if session has been closed.

        Returns:
            True if session is closed

        """
        return self._closed
