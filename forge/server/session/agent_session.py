"""Runtime session orchestration for agents, including startup and lifecycle."""

from __future__ import annotations

import asyncio
import json
import time
from types import MappingProxyType, SimpleNamespace
from typing import TYPE_CHECKING, Callable, Mapping, cast

from forge.controller import AgentController
from forge.controller.services.delegate_runtime_provider import (
    DelegateRuntimeProvider,
)
from forge.controller.replay import ReplayManager
from forge.controller.state.state import State
from forge.core.exceptions import AgentRuntimeUnavailableError
from forge.core.logger import forgeLoggerAdapter
from forge.core.schemas import AgentState
from forge.events.action import ChangeAgentStateAction, MessageAction
from forge.events.event import Event, EventSource
from forge.integrations.provider import (
    CUSTOM_SECRETS_TYPE,
    PROVIDER_TOKEN_TYPE,
    ProviderHandler,
    CustomSecret,
    ProviderToken,
    ProviderType,
)
from forge.server.shared import get_event_service_adapter
from forge.mcp_client import add_mcp_tools_to_agent
from forge.memory.memory import Memory
from forge.runtime import RuntimeAcquireResult, get_runtime_cls, runtime_orchestrator
from forge.runtime.impl.remote.remote_runtime import RemoteRuntime
from forge.runtime.runtime_status import RuntimeStatus
from forge.storage.data_models.user_secrets import UserSecrets
from forge.utils.async_utils import EXECUTOR, call_sync_from_async
from forge.utils.shutdown_listener import should_continue
from .constants import (
    WAIT_TIME_BEFORE_CLOSE,
    WAIT_TIME_BEFORE_CLOSE_INTERVAL,
)

if TYPE_CHECKING:
    from logging import LoggerAdapter

    from forge.controller.agent import Agent
    from forge.events.stream import EventStream
    from forge.llm.llm_registry import LLMRegistry
    from forge.microagent.microagent import BaseMicroagent
    from forge.runtime.base import Runtime
    from forge.server.services.conversation_stats import ConversationStats
    from forge.storage.files import FileStore

from forge.core.config import AgentConfig, LLMConfig, ForgeConfig
from forge.core.main import _setup_runtime_and_repo
from forge.core.setup import initialize_repository_for_runtime


# Backward compatibility: expose EventStream at runtime (tests monkeypatch this symbol).
try:
    from forge.events.stream import EventStream as EventStream  # type: ignore
except Exception:  # pragma: no cover - defensive fallback
    EventStream = object  # type: ignore


class AgentSession:
    """Represents a session with an Agent.

    Attributes:
        controller: The AgentController instance for controlling the agent.

    """

    sid: str
    user_id: str | None
    event_stream: EventStream
    llm_registry: LLMRegistry
    file_store: FileStore
    controller: AgentController | None = None
    runtime: Runtime | None = None
    memory: Memory | None = None
    _starting: bool = False
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
        self._delegate_env_vars: dict[str, str] | None = None
        self._delegate_git_tokens: PROVIDER_TOKEN_TYPE | None = None
        self._delegate_runtime_provider: DelegateRuntimeProvider | None = None
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
        try:
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

        finally:
            self._finalize_session_startup(startup_state, runtime_connected)

    def _validate_session_state(self) -> bool:
        """Validate that the session can be started."""
        if self.controller or self.runtime:
            msg = "Session already started. You need to close this session and start a new one."
            raise RuntimeError(msg)
        if self._closed:
            self.logger.warning("Session closed before starting")
            return False
        return True

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
        # Create runtime
        runtime_connected = await self._create_runtime(
            runtime_name=runtime_name,
            config=config,
            agent=agent,
            git_provider_tokens=git_provider_tokens,
            custom_secrets=custom_secrets,
            selected_repository=selected_repository,
            selected_branch=selected_branch,
        )

        # Setup provider handlers
        await self._setup_provider_handlers(git_provider_tokens, custom_secrets)

        return runtime_connected

    async def _setup_provider_handlers(
        self, git_provider_tokens, custom_secrets
    ) -> None:
        """Setup provider handlers for git and custom secrets."""
        if git_provider_tokens:
            provider_handler = ProviderHandler(provider_tokens=git_provider_tokens)
            await provider_handler.set_event_stream_secrets(self.event_stream)

        if custom_secrets:
            custom_secrets_handler = UserSecrets(custom_secrets=custom_secrets)
            custom_secrets_handler.set_event_stream_secrets(self.event_stream)

    async def _setup_memory_and_mcp_tools(
        self,
        selected_repository,
        selected_branch,
        conversation_instructions,
        custom_secrets,
        config,
        agent,
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
        self.memory = await self._create_memory(
            selected_repository=selected_repository,
            repo_directory=repo_directory,
            selected_branch=selected_branch,
            conversation_instructions=conversation_instructions,
            custom_secrets_descriptions=custom_secrets_handler.get_custom_secrets_descriptions(),
            working_dir=config.workspace_mount_path_in_sandbox,
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
                self.event_stream.add_event(initial_message, EventSource.USER)
                self.logger.debug(
                    "Enqueuing ChangeAgentStateAction(RUNNING)",
                    extra={"signal": "agent_start"},
                )
                self.event_stream.add_event(
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
                self.event_stream.add_event(
                    ChangeAgentStateAction(AgentState.AWAITING_USER_INPUT),
                    EventSource.ENVIRONMENT,
                )

    def _finalize_session_startup(self, startup_state, runtime_connected) -> None:
        """Finalize session startup and log results."""
        self._starting = False
        success = startup_state["finished"] and runtime_connected
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

    async def close(self) -> None:
        """Closes the Agent session."""
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
        if self.event_stream is not None:
            self.event_stream.close()
        if self.controller is not None:
            self.controller.save_state()
            await self.controller.close()
        if self._runtime_acquire_result is not None:
            runtime_orchestrator.release(self._runtime_acquire_result)
            self._runtime_acquire_result = None
            self.runtime = None
        elif self.runtime is not None:
            EXECUTOR.submit(self.runtime.close)

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

    async def _create_runtime(
        self,
        runtime_name: str,
        config: ForgeConfig,
        agent: Agent,
        git_provider_tokens: PROVIDER_TOKEN_TYPE | None = None,
        custom_secrets: CUSTOM_SECRETS_TYPE | None = None,
        selected_repository: str | None = None,
        selected_branch: str | None = None,
    ) -> bool:
        """Creates a runtime instance.

        Parameters:
        - runtime_name: The name of the runtime associated with the session
        - config:
        - agent:

        Return True on successfully connected, False if could not connect.
        Raises if already created, possibly in other situations.
        """
        self._ensure_runtime_absent()

        env_vars = await self._prepare_runtime_env(custom_secrets, git_provider_tokens)
        runtime_cls = get_runtime_cls(runtime_name)
        repo_tokens = self._resolve_repo_tokens(
            runtime_cls, git_provider_tokens, custom_secrets
        )

        self.logger.debug(f"Initializing runtime `{runtime_name}` now...")
        self._delegate_env_vars = dict(env_vars)
        self._delegate_git_tokens = repo_tokens

        if not self._can_use_shared_runtime_helper(config):
            return await self._create_runtime_direct(
                runtime_cls,
                config,
                agent,
                repo_tokens,
                env_vars,
                selected_repository,
                selected_branch,
            )

        repo_initializer = self._build_repo_initializer(
            repo_tokens, selected_repository, selected_branch
        )
        return self._setup_runtime_with_helper(
            config,
            agent,
            repo_tokens,
            env_vars,
            repo_initializer,
        )

    async def _create_runtime_direct(
        self,
        runtime_cls,
        config: ForgeConfig | SimpleNamespace,
        agent: Agent,
        git_provider_tokens: PROVIDER_TOKEN_TYPE | None,
        env_vars: dict[str, str],
        selected_repository: str | None,
        selected_branch: str | None,
    ) -> bool:
        self.runtime = runtime_cls(
            config=config,
            event_stream=self.event_stream,
            llm_registry=self.llm_registry,
            sid=self.sid,
            plugins=agent.sandbox_plugins,
            status_callback=self._status_callback,
            headless_mode=False,
            attach_to_existing=False,
            env_vars=env_vars,
            git_provider_tokens=git_provider_tokens,
        )
        try:
            await self.runtime.connect()
        except AgentRuntimeUnavailableError as e:
            self.logger.exception(f"Runtime initialization failed: {e}")
            if self._status_callback:
                self._status_callback(
                    "error", RuntimeStatus.ERROR_RUNTIME_DISCONNECTED, str(e)
                )
            return False
        repo_dir = await self.runtime.clone_or_init_repo(
            git_provider_tokens, selected_repository, selected_branch
        )
        await call_sync_from_async(self.runtime.maybe_run_setup_script)
        await call_sync_from_async(self.runtime.maybe_setup_git_hooks)
        self._repo_directory = repo_dir or (
            selected_repository.split("/")[-1] if selected_repository else None
        )
        self.logger.debug(
            f"Runtime initialized with plugins: {[plugin.name for plugin in self.runtime.plugins]}"
        )
        return True

    def _ensure_runtime_absent(self) -> None:
        if self.runtime is not None:
            msg = "Runtime already created"
            raise RuntimeError(msg)

    async def _prepare_runtime_env(
        self,
        custom_secrets: CUSTOM_SECRETS_TYPE | None,
        git_provider_tokens: PROVIDER_TOKEN_TYPE | None,
    ) -> dict[str, str]:
        custom_secret_dict = dict(custom_secrets or {})
        custom_secrets_handler = UserSecrets(custom_secrets=custom_secret_dict)
        env_vars = custom_secrets_handler.get_env_vars()

        provider_tokens = (
            git_provider_tokens
            if isinstance(git_provider_tokens, MappingProxyType)
            else MappingProxyType(dict(git_provider_tokens or {}))
        )
        provider_handler = ProviderHandler(provider_tokens=provider_tokens)
        provider_env_raw = await provider_handler.get_env_vars(expose_secrets=True)
        provider_env = cast(Mapping[str, str], provider_env_raw)
        env_vars.update(provider_env)
        return env_vars

    def _resolve_repo_tokens(
        self,
        runtime_cls,
        git_provider_tokens: PROVIDER_TOKEN_TYPE | None,
        custom_secrets: CUSTOM_SECRETS_TYPE | None,
    ) -> MappingProxyType[ProviderType, ProviderToken] | None:
        if runtime_cls != RemoteRuntime:
            if isinstance(git_provider_tokens, MappingProxyType):
                return git_provider_tokens
            return MappingProxyType(dict(git_provider_tokens or {}))
        return self.override_provider_tokens_with_custom_secret(
            git_provider_tokens, custom_secrets
        )

    def _can_use_shared_runtime_helper(self, config: ForgeConfig) -> bool:
        return all(hasattr(config, attr) for attr in ("runtime", "sandbox", "file_store"))

    def _build_repo_initializer(
        self,
        repo_tokens: PROVIDER_TOKEN_TYPE | None,
        selected_repository: str | None,
        selected_branch: str | None,
    ) -> Callable[[Runtime], str | None] | None:
        if not selected_repository:
            return None

        def _repo_initializer(runtime: Runtime) -> str | None:
            return initialize_repository_for_runtime(
                runtime,
                immutable_provider_tokens=repo_tokens,
                selected_repository=selected_repository,
                selected_branch=selected_branch,
            )

        return _repo_initializer

    def _setup_runtime_with_helper(
        self,
        config: ForgeConfig,
        agent: Agent,
        repo_tokens: PROVIDER_TOKEN_TYPE | None,
        env_vars: dict[str, str],
        repo_initializer: Callable[[Runtime], str | None] | None,
    ) -> bool:
        try:
            acquire_result = _setup_runtime_and_repo(
                config,
                self.sid,
                self.llm_registry,
                agent,
                headless_mode=False,
                git_provider_tokens=repo_tokens,
                repo_initializer=repo_initializer,
                event_stream=self.event_stream,
                env_vars=env_vars,
                user_id=self.user_id,
            )
        except AgentRuntimeUnavailableError as e:
            self._handle_runtime_initialization_error(e)
            return False

        self._apply_runtime_acquire_result(acquire_result)
        return True

    def _apply_runtime_acquire_result(
        self, acquire_result: RuntimeAcquireResult
    ) -> None:
        self.runtime = acquire_result.runtime
        self._runtime_acquire_result = acquire_result
        self._repo_directory = acquire_result.repo_directory
        self.logger.debug(
            f"Runtime initialized with plugins: {[plugin.name for plugin in self.runtime.plugins]}"
        )

    def _handle_runtime_initialization_error(self, exc: Exception) -> None:
        self.logger.exception(f"Runtime initialization failed: {exc}")
        if self._status_callback:
            self._status_callback(
                "error", RuntimeStatus.ERROR_RUNTIME_DISCONNECTED, str(exc)
            )

    def _get_delegate_runtime_provider(self) -> DelegateRuntimeProvider | None:
        if self._delegate_env_vars is None or self._delegate_git_tokens is None:
            return None
        if self._delegate_runtime_provider is None:
            self._delegate_runtime_provider = DelegateRuntimeProvider(
                config=self.config,
                llm_registry=self.llm_registry,
                file_store=self.file_store,
                parent_event_stream=self.event_stream,
                git_provider_tokens=self._delegate_git_tokens,
                env_vars=self._delegate_env_vars,
                user_id=self.user_id,
                selected_repository=self._selected_repository,
                selected_branch=self._selected_branch,
                base_session_id=self.sid,
            )
        return self._delegate_runtime_provider

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
        setattr(
            controller,
            "delegate_runtime_provider",
            self._get_delegate_runtime_provider(),
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
    ) -> Memory:
        memory = Memory(
            event_stream=self.event_stream,
            sid=self.sid,
            status_callback=self._status_callback,
        )
        if self.runtime:
            memory.set_runtime_info(
                self.runtime, custom_secrets_descriptions, working_dir
            )
            memory.set_conversation_instructions(conversation_instructions)
            microagents: list[BaseMicroagent] = await call_sync_from_async(
                self.runtime.get_microagents_from_selected_repo,
                selected_repository or None,
            )
            memory.load_user_workspace_microagents(microagents)
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
            if self.event_stream.get_latest_event_id() > 0:
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
