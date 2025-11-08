"""Core functionality for the Forge agent framework.

Classes:
    FakeUserResponseFunc

Functions:
    auto_continue_response
    load_replay_log
    on_event
"""

from __future__ import annotations

import asyncio
import json
import os
from pathlib import Path
from typing import TYPE_CHECKING, Callable, Protocol

if TYPE_CHECKING:
    from forge.controller.agent import Agent
    from forge.controller.state.state import State
    from forge.events.action.action import Action
    from forge.events.event import Event
    from forge.llm.llm_registry import LLMRegistry
    from forge.memory.memory import Memory
    from forge.runtime.base import Runtime
    from forge.server.services.conversation_stats import ConversationStats

from forge.controller.replay import ReplayManager
from forge.core.config import (
    ForgeConfig,
    parse_arguments,
    setup_config_from_args,
)
from forge.core.config.mcp_config import ForgeMCPConfigImpl, forgeMCPConfigImpl
from forge.core.logger import forge_logger as logger
from forge.core.loop import run_agent_until_done
from forge.core.schema import AgentState
from forge.core.setup import (
    create_agent,
    create_controller,
    create_memory,
    create_runtime,
    generate_sid,
    get_provider_tokens,
    initialize_repository_for_runtime,
)
from forge.events import EventSource, EventStreamSubscriber
from forge.events.action import MessageAction, NullAction
from forge.events.observation import AgentStateChangedObservation
from forge.io import read_input, read_task
from forge.mcp_client import add_mcp_tools_to_agent
import contextlib

from forge.runtime.runtime_status import RuntimeStatus
from forge.utils.async_utils import call_async_from_sync
from forge.utils.utils import create_registry_and_conversation_stats


class FakeUserResponseFunc(Protocol):
    """Protocol for fake user response functions in testing/evaluation.
    
    Defines the interface for functions that simulate user responses
    during automated agent evaluation.
    """

    def __call__(
        self,
        state: State,
        encapsulate_solution: bool = False,
        try_parse: Callable[[Action | None], str] | None = None,
    ) -> str:
        """Simulate a user reply given the current state and parsing helpers."""


def _setup_runtime_and_repo(
    config_: ForgeConfig,
    session_id: str,
    llm_registry,
    agent,
    headless_mode: bool,
) -> tuple[Runtime, str | None]:
    """Setup runtime and repository directory."""
    repo_tokens = get_provider_tokens()
    runtime = create_runtime(
        config_,
        llm_registry,
        sid=session_id,
        headless_mode=headless_mode,
        agent=agent,
        git_provider_tokens=repo_tokens,
    )
    call_async_from_sync(runtime.connect)

    repo_directory = None
    if config_.sandbox.selected_repo:
        repo_directory = initialize_repository_for_runtime(
            runtime,
            immutable_provider_tokens=repo_tokens,
            selected_repository=config_.sandbox.selected_repo,
        )

    return runtime, repo_directory


async def _setup_memory_and_mcp(
    config_: ForgeConfig,
    runtime: Runtime,
    session_id: str,
    repo_directory: str | None,
    memory: Memory | None,
    conversation_instructions: str | None,
    agent,
) -> Memory:
    """Setup memory and MCP tools."""
    event_stream = runtime.event_stream

    if memory is None:
        memory = create_memory(
            runtime=runtime,
            event_stream=event_stream,
            sid=session_id,
            selected_repository=config_.sandbox.selected_repo,
            repo_directory=repo_directory,
            conversation_instructions=conversation_instructions,
            working_dir=config_.workspace_mount_path_in_sandbox,
        )

    if agent.config.enable_mcp:
        _, FORGE_mcp_stdio_servers = ForgeMCPConfigImpl.create_default_mcp_server_config(
            config_.mcp_host,
            config_,
            None,
        )
        runtime.config.mcp.stdio_servers.extend(FORGE_mcp_stdio_servers)
        await add_mcp_tools_to_agent(agent, runtime, memory)

    return memory


def _setup_replay_events(config_: ForgeConfig, initial_action: Action) -> tuple[list[Event] | None, Action]:
    """Setup replay events if trajectory replay is enabled."""
    if config_.replay_trajectory_path:
        logger.info("Trajectory replay is enabled")
        assert isinstance(initial_action, NullAction)
        return load_replay_log(config_.replay_trajectory_path)
    return None, initial_action


def _create_early_status_callback(controller) -> Callable[[str, RuntimeStatus, str], None]:
    """Create the early status callback function."""

    def _early_status_callback(msg_type: str, runtime_status: RuntimeStatus, msg: str) -> None:
        if msg_type == "error":
            logger.error(msg)
            logger.info('MAIN._early_status_callback ENTER (runtime_status=%s, msg="%s")', runtime_status, msg)
            try:
                controller.state.last_error = msg
                if runtime_status == RuntimeStatus.ERROR_MEMORY:
                    logger.info("MAIN._early_status_callback: resetting iteration_flag.current_value to 0")
                    controller.state.iteration_flag.current_value = 0
                    setattr(controller.state, "_force_iteration_reset", True)
                    setattr(controller, "_force_iteration_reset", True)
            except Exception:
                pass
            with contextlib.suppress(Exception):
                asyncio.create_task(controller.set_agent_state_to(AgentState.ERROR))
        else:
            logger.info(msg)

    return _early_status_callback


def _validate_initial_action(initial_action: Action) -> None:
    """Validate that the initial action is properly formatted."""
    if not hasattr(initial_action, "message") and (not hasattr(initial_action, "content")):
        msg = f"initial user actions must be an Action-like object, got {type(initial_action)}"
        raise AssertionError(msg)


def _setup_initial_events(event_stream, initial_action: Action, initial_state: State | None) -> None:
    """Setup initial events based on state and action."""
    loop = None
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        loop = None

    if initial_state is not None and initial_state.last_error:
        error_message = MessageAction(
            content="Let's get back on track. If you experienced errors before, do NOT resume your task. Ask me about it.", )
        if loop is not None:
            loop.call_soon(event_stream.add_event, error_message, EventSource.USER)
        else:
            event_stream.add_event(error_message, EventSource.USER)
    elif loop is not None:
        loop.call_soon(event_stream.add_event, initial_action, EventSource.USER)
    else:
        event_stream.add_event(initial_action, EventSource.USER)


def _create_event_handler(
    config_: ForgeConfig,
    exit_on_message: bool,
    fake_user_response_fn: FakeUserResponseFunc | None,
    controller,
    event_stream,
) -> Callable[[Event], None]:
    """Create the event handler for user input."""

    def on_event(event: Event) -> None:
        """Handle events and trigger completion on user input or agent finish.
        
        Args:
            event: Event to process

        """
        if isinstance(event, AgentStateChangedObservation) and event.agent_state == AgentState.AWAITING_USER_INPUT:
            if exit_on_message:
                message = "/exit"
            elif fake_user_response_fn is None:
                message = read_input(config_.cli_multiline_input)
            else:
                message = fake_user_response_fn(controller.get_state())
            action = MessageAction(content=message)
            event_stream.add_event(action, EventSource.USER)

    return on_event


def _save_trajectory(config_: ForgeConfig, session_id: str, controller) -> None:
    """Save trajectory to file if configured."""
    if config_.save_trajectory_path is not None:
        if os.path.isdir(config_.save_trajectory_path):
            file_path = os.path.join(config_.save_trajectory_path, f"{session_id}.json")
        else:
            file_path = config_.save_trajectory_path
        os.makedirs(os.path.dirname(file_path), exist_ok=True)
        histories = controller.get_trajectory(config_.save_screenshots_in_trajectory)
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(histories, f, indent=4)


def _initialize_session_components(
    config_: ForgeConfig,
    session_id: str | None,
) -> tuple[str, LLMRegistry, ConversationStats, ForgeConfig, Agent]:
    """Initialize session and components."""
    session_id = session_id or generate_sid(config_)
    llm_registry, conversation_stats, config_ = create_registry_and_conversation_stats(config_, session_id, None)
    agent = create_agent(config_, llm_registry)
    return session_id, llm_registry, conversation_stats, config_, agent


def _setup_runtime_for_controller(
    config_: ForgeConfig,
    llm_registry: LLMRegistry,
    session_id: str,
    headless_mode: bool,
    agent: Agent,
    runtime: Runtime | None,
) -> tuple[Runtime, str | None]:
    """Setup runtime for controller."""
    if runtime is not None:
        return runtime, None
    repo_tokens = get_provider_tokens()
    runtime = create_runtime(
        config_,
        llm_registry,
        sid=session_id,
        headless_mode=headless_mode,
        agent=agent,
        git_provider_tokens=repo_tokens,
    )
    call_async_from_sync(runtime.connect)
    repo_directory = (
        initialize_repository_for_runtime(
            runtime,
            immutable_provider_tokens=repo_tokens,
            selected_repository=config_.sandbox.selected_repo,
        )
        if config_.sandbox.selected_repo
        else None
    )
    return runtime, repo_directory


async def run_controller(
    config_: ForgeConfig | None = None,
    initial_action: Action | None = None,
    *,
    session_id: str | None = None,
    runtime: Runtime | None = None,
    exit_on_message: bool = False,
    fake_user_response_fn: FakeUserResponseFunc | None = None,
    headless_mode: bool = True,
    memory: Memory | None = None,
    conversation_instructions: str | None = None,
    **legacy_kwargs,
) -> State | None:
    """Main coroutine to run the agent controller with task input flexibility.

    It's only used when you launch Forge backend directly via cmdline.

    Args:
        config_: The app config.
        initial_action: An Action object containing initial user input
        session_id: (optional) The session id. IMPORTANT: please don't set this unless you know what you're doing.
            Set it to incompatible value will cause unexpected behavior on RemoteRuntime.
        runtime: (optional) A runtime for the agent to run on.
        exit_on_message: quit if agent asks for a message from user (optional)
        fake_user_response_fn: An optional function that receives the current state
            (could be None) and returns a fake user response.
        headless_mode: Whether the agent is run in headless mode.
        memory: Optional memory instance for the agent.
        conversation_instructions: Optional conversation instructions.
        **legacy_kwargs: Additional keyword arguments kept for backward compatibility.

    Returns:
        The final state of the agent, or None if an error occurred.

    Raises:
        AssertionError: If initial_action is not an Action instance.
        Exception: Various exceptions may be raised during execution and will be logged.

    Notes:
        - State persistence: If config_.file_store is set, the agent's state will be
          saved between sessions.
        - Trajectories: If config_.trajectories_path is set, execution history will be
          saved as JSON for analysis.
        - Budget control: Execution is limited by config_.max_iterations and
          config_.max_budget_per_task.

    Example:
        >>> config = load_FORGE_config()
        >>> action = MessageAction(content="Write a hello world program")
        >>> state = await run_controller(config_=config, initial_action=action)

    """
    # Support legacy keyword arguments used throughout tests and external tools.
    if config_ is None and "config" in legacy_kwargs:
        config_ = legacy_kwargs.pop("config")
    if initial_action is None and "initial_user_action" in legacy_kwargs:
        initial_action = legacy_kwargs.pop("initial_user_action")
    if session_id is None and "sid" in legacy_kwargs:
        session_id = legacy_kwargs.pop("sid")
    if "headless" in legacy_kwargs:
        headless_mode = legacy_kwargs.pop("headless")
    if legacy_kwargs:
        unexpected = ", ".join(sorted(legacy_kwargs.keys()))
        raise TypeError(f"run_controller() got unexpected keyword argument(s): {unexpected}")

    if config_ is None:
        raise TypeError("run_controller() missing required argument 'config_' (or legacy 'config')")
    if initial_action is None:
        raise TypeError("run_controller() missing required argument 'initial_action' (or legacy 'initial_user_action')")

    # Initialize session and components
    session_id, llm_registry, conversation_stats, config_, agent = _initialize_session_components(config_, session_id)

    # Setup runtime and repository
    runtime, repo_directory = _setup_runtime_for_controller(
        config_,
        llm_registry,
        session_id,
        headless_mode,
        agent,
        runtime,
    )

    # Setup memory and MCP
    event_stream = runtime.event_stream
    memory = await _setup_memory_and_mcp(
        config_,
        runtime,
        session_id,
        repo_directory,
        memory,
        conversation_instructions,
        agent,
    )

    # Setup replay events
    replay_events, initial_action = _setup_replay_events(config_, initial_action)

    # Create controller
    controller, initial_state = create_controller(
        agent,
        runtime,
        config_,
        conversation_stats,
        replay_events=replay_events,
    )

    # Setup status callback
    _early_status_callback = _create_early_status_callback(controller)
    with contextlib.suppress(Exception):
        memory.status_callback = _early_status_callback

    # Validate and setup initial events
    _validate_initial_action(initial_action)
    logger.debug(
        "Agent Controller Initialized: Running agent %s, model %s, with actions: %s",
        agent.name,
        agent.llm.config.model,
        initial_action,
    )

    _setup_initial_events(event_stream, initial_action, initial_state)

    # Setup event handler and run agent
    on_event = _create_event_handler(exit_on_message, fake_user_response_fn, config_, controller, event_stream)
    event_stream.subscribe(EventStreamSubscriber.MAIN, on_event, event_stream.sid)
    end_states = [AgentState.FINISHED, AgentState.REJECTED, AgentState.ERROR, AgentState.PAUSED, AgentState.STOPPED]

    try:
        await run_agent_until_done(controller, runtime, memory, end_states)
    except Exception as e:
        logger.error("Exception in main loop: %s", e)

    # Save state and trajectory
    if config_.file_store is not None and config_.file_store != "memory":
        end_state = controller.get_state()
        end_state.save_to_session(event_stream.sid, event_stream.file_store, event_stream.user_id)

    await controller.close(set_stop_state=False)
    state = controller.get_state()
    force_iteration_reset = getattr(controller, "_force_iteration_reset", False) or getattr(
        state,
        "_force_iteration_reset",
        False,
    )
    if force_iteration_reset:
        logger.debug(
            "run_controller: honoring forced iteration reset (current=%s)",
            state.iteration_flag.current_value,
        )
        state.iteration_flag.current_value = 0

    _save_trajectory(config_, session_id, controller)

    return state


def auto_continue_response(
    state: State,
    encapsulate_solution: bool = False,
    try_parse: Callable[[Action | None], str] | None = None,
) -> str:
    """Default function to generate user responses.

    Tell the agent to proceed without asking for more input, or finish the interaction.
    """
    return "Please continue on whatever approach you think is suitable.\nIf you think you have solved the task, please finish the interaction.\nIMPORTANT: YOU SHOULD NEVER ASK FOR HUMAN RESPONSE.\n"


def load_replay_log(trajectory_path: str) -> tuple[list[Event] | None, Action]:
    """Load trajectory from given path, serialize it to a list of events, and return.

    two things:
    1) A list of events except the first action
    2) First action (user message, a.k.a. initial task).
    """
    try:
        path = Path(trajectory_path).resolve()
        if not path.exists():
            msg = f"Trajectory file not found: {path}"
            raise ValueError(msg)
        if not path.is_file():
            msg = f"Trajectory path is a directory, not a file: {path}"
            raise ValueError(msg)
        with open(path, encoding="utf-8") as file:
            events = ReplayManager.get_replay_events(json.load(file))
            assert isinstance(events[0], MessageAction)
            return (events[1:], events[0])
    except json.JSONDecodeError as e:
        msg = f"Invalid JSON format in {trajectory_path}: {e}"
        raise ValueError(msg) from e


if __name__ == "__main__":
    args = parse_arguments()
    config_main: ForgeConfig = setup_config_from_args(args)
    task_str = read_task(args, config_main.cli_multiline_input)
    initial_action_main: Action = NullAction()
    if config_main.replay_trajectory_path:
        if task_str:
            msg = "User-specified task is not supported under trajectory replay mode"
            raise ValueError(msg)
    elif task_str:
        initial_action_main = MessageAction(content=task_str)
    else:
        msg = "No task provided. Please specify a task through -t, -f."
        raise ValueError(msg)
    session_name = args.name
    sid_main = generate_sid(config_main, session_name)
    asyncio.run(
        run_controller(
            config_=config_main,
            initial_action=initial_action_main,
            session_id=sid_main,
            fake_user_response_fn=None if args.no_auto_continue else auto_continue_response,
        ),
    )
