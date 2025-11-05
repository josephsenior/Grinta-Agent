from __future__ import annotations

import asyncio
import json
import time
from types import MappingProxyType
from typing import TYPE_CHECKING, Callable, cast

from openhands.controller import AgentController
from openhands.controller.replay import ReplayManager
from openhands.controller.state.state import State
from openhands.core.exceptions import AgentRuntimeUnavailableError
from openhands.core.logger import OpenHandsLoggerAdapter
from openhands.core.schema.agent import AgentState
from openhands.events.action import ChangeAgentStateAction, MessageAction
from openhands.events.event import Event, EventSource
from openhands.events.stream import EventStream
from openhands.integrations.provider import (
    CUSTOM_SECRETS_TYPE,
    PROVIDER_TOKEN_TYPE,
    ProviderHandler,
)
from openhands.mcp_client import add_mcp_tools_to_agent
from openhands.memory.memory import Memory
from openhands.runtime import get_runtime_cls
from openhands.runtime.impl.remote.remote_runtime import RemoteRuntime
from openhands.runtime.runtime_status import RuntimeStatus
from openhands.storage.data_models.user_secrets import UserSecrets
from openhands.utils.async_utils import EXECUTOR, call_sync_from_async
from openhands.utils.shutdown_listener import should_continue

if TYPE_CHECKING:
    from logging import LoggerAdapter

    from openhands.controller.agent import Agent
    from openhands.core.config import AgentConfig, LLMConfig, OpenHandsConfig
    from openhands.llm.llm_registry import LLMRegistry
    from openhands.microagent.microagent import BaseMicroagent
    from openhands.runtime.base import Runtime
    from openhands.server.services.conversation_stats import ConversationStats
    from openhands.storage.files import FileStore

WAIT_TIME_BEFORE_CLOSE = 90
WAIT_TIME_BEFORE_CLOSE_INTERVAL = 5


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
        self.event_stream = EventStream(sid, file_store, user_id)
        self.file_store = file_store
        self._status_callback = status_callback
        self.user_id = user_id
        self.logger = OpenHandsLoggerAdapter(extra={"session_id": sid, "user_id": user_id})
        self.llm_registry = llm_registry
        self.conversation_stats = conversation_stats

    async def start(
        self,
        runtime_name: str,
        config: OpenHandsConfig,
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
        - config: The OpenHands configuration for this session.
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
        return {"started_at": started_at, "finished": False, "runtime_connected": False, "restored_state": False}

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

    async def _setup_provider_handlers(self, git_provider_tokens, custom_secrets) -> None:
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
        # Determine repo directory
        repo_directory = None
        if self.runtime and selected_repository:
            repo_directory = selected_repository.split("/")[-1]

        # Create memory
        custom_secrets_handler = UserSecrets(custom_secrets=custom_secrets or {})
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
                self.logger.info("Adding initial user message and switching agent state to RUNNING", extra={"signal": "agent_start"})
                self.event_stream.add_event(initial_message, EventSource.USER)
                self.logger.debug("Enqueuing ChangeAgentStateAction(RUNNING)", extra={"signal": "agent_start"})
                self.event_stream.add_event(ChangeAgentStateAction(AgentState.RUNNING), EventSource.ENVIRONMENT)
            else:
                self.logger.info("No initial message; queueing ChangeAgentStateAction(AWAITING_USER_INPUT)", extra={"signal": "agent_start"})
                self.logger.debug("Enqueuing ChangeAgentStateAction(AWAITING_USER_INPUT)", extra={"signal": "agent_start"})
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
            self.logger.info(f"Agent session start succeeded in {duration}s", extra=log_metadata)
        else:
            self.logger.error(f"Agent session start failed in {duration}s", extra=log_metadata)

    async def close(self) -> None:
        """Closes the Agent session."""
        if self._closed:
            return
        self._closed = True
        while self._starting and should_continue():
            self.logger.debug(f"Waiting for initialization to finish before closing session {self.sid}")
            await asyncio.sleep(WAIT_TIME_BEFORE_CLOSE_INTERVAL)
            if time.time() <= self._started_at + WAIT_TIME_BEFORE_CLOSE:
                self.logger.error(f"Waited too long for initialization to finish before closing session {self.sid}")
                break
        if self.event_stream is not None:
            self.event_stream.close()
        if self.controller is not None:
            self.controller.save_state()
            await self.controller.close()
        if self.runtime is not None:
            EXECUTOR.submit(self.runtime.close)

    def _run_replay(
        self,
        initial_message: MessageAction | None,
        replay_json: str,
        agent: Agent,
        config: OpenHandsConfig,
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
        if git_provider_tokens and custom_secrets:
            tokens = {
                provider: token
                for provider, token in git_provider_tokens.items()
                if not (
                    ProviderHandler.get_provider_env_key(provider) in custom_secrets
                    or ProviderHandler.get_provider_env_key(provider).upper() in custom_secrets
                )
            }
            return MappingProxyType(tokens)
        return git_provider_tokens

    async def _create_runtime(
        self,
        runtime_name: str,
        config: OpenHandsConfig,
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
        if self.runtime is not None:
            msg = "Runtime already created"
            raise RuntimeError(msg)
        custom_secrets_handler = UserSecrets(custom_secrets=custom_secrets or {})
        env_vars = custom_secrets_handler.get_env_vars()
        self.logger.debug(f"Initializing runtime `{runtime_name}` now...")
        runtime_cls = get_runtime_cls(runtime_name)
        if runtime_cls == RemoteRuntime:
            overrided_tokens = self.override_provider_tokens_with_custom_secret(git_provider_tokens, custom_secrets)
            self.runtime = runtime_cls(
                config=config,
                event_stream=self.event_stream,
                llm_registry=self.llm_registry,
                sid=self.sid,
                plugins=agent.sandbox_plugins,
                status_callback=self._status_callback,
                headless_mode=False,
                attach_to_existing=False,
                git_provider_tokens=overrided_tokens,
                env_vars=env_vars,
                user_id=self.user_id,
            )
        else:
            provider_handler = ProviderHandler(
                provider_tokens=git_provider_tokens or cast("PROVIDER_TOKEN_TYPE", MappingProxyType({})),
            )
            env_vars.update(await provider_handler.get_env_vars(expose_secrets=True))
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
                self._status_callback("error", RuntimeStatus.ERROR_RUNTIME_DISCONNECTED, str(e))
            return False
        await self.runtime.clone_or_init_repo(git_provider_tokens, selected_repository, selected_branch)
        await call_sync_from_async(self.runtime.maybe_run_setup_script)
        await call_sync_from_async(self.runtime.maybe_setup_git_hooks)
        self.logger.debug(f"Runtime initialized with plugins: {[plugin.name for plugin in self.runtime.plugins]}")
        return True

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
        msg = f"\n--------------------------------- OpenHands Configuration ---------------------------------\nLLM: {
            agent.llm.config.model}\nBase URL: {
            agent.llm.config.base_url}\nAgent: {
            agent.name}\nRuntime: {
                self.runtime.__class__.__name__}\nPlugins: {
                    (
                        [
                            p.name for p in agent.sandbox_plugins] if agent.sandbox_plugins else 'None')}\n-------------------------------------------------------------------------------------------"
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
    ) -> Memory:
        memory = Memory(event_stream=self.event_stream, sid=self.sid, status_callback=self._status_callback)
        if self.runtime:
            memory.set_runtime_info(self.runtime, custom_secrets_descriptions, working_dir)
            memory.set_conversation_instructions(conversation_instructions)
            microagents: list[BaseMicroagent] = await call_sync_from_async(
                self.runtime.get_microagents_from_selected_repo,
                selected_repository or None,
            )
            memory.load_user_workspace_microagents(microagents)
            if selected_repository and repo_directory:
                memory.set_repository_info(selected_repository, repo_directory, selected_branch)
        return memory

    def get_state(self) -> AgentState | None:
        if controller := self.controller:
            return controller.state.agent_state
        if time.time() > self._started_at + WAIT_TIME_BEFORE_CLOSE:
            return AgentState.ERROR
        return None

    def _maybe_restore_state(self) -> State | None:
        """Helper method to handle state restore logic."""
        restored_state = None
        try:
            restored_state = State.restore_from_session(self.sid, self.file_store, self.user_id)
            self.logger.debug(f"Restored state from session, sid: {self.sid}")
        except Exception as e:
            if self.event_stream.get_latest_event_id() > 0:
                self.logger.warning(f"State could not be restored: {e}")
            else:
                self.logger.debug("No events found, no state to restore")
        return restored_state

    def is_closed(self) -> bool:
        return self._closed
