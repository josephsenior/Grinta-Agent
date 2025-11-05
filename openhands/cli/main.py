"""Command-line interface for OpenHands.

Functions:
    run_alias_setup_flow
    run_cli_command
    stream_to_console
    on_event
"""

from __future__ import annotations

import asyncio
import logging
import os
import sys
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, Callable

from prompt_toolkit import print_formatted_text
from prompt_toolkit.formatted_text import HTML
from prompt_toolkit.shortcuts import clear

from openhands.cli.commands import check_folder_security_agreement, handle_commands
from openhands.cli.settings import modify_llm_settings_basic
from openhands.cli.shell_config import (
    ShellConfigManager,
    add_aliases_to_shell_config,
    alias_setup_declined,
    aliases_exist_in_shell_config,
    mark_alias_setup_declined,
)
from openhands.cli.tui import (
    UsageMetrics,
    cli_confirm,
    display_agent_running_message,
    display_banner,
    display_event,
    display_initial_user_prompt,
    display_initialization_animation,
    display_runtime_initialization_message,
    display_welcome_message,
    read_confirmation_input,
    read_prompt_input,
    start_pause_listener,
    stop_pause_listener,
    update_streaming_output,
)
from openhands.cli.utils import update_usage_metrics
from openhands.cli.vscode_extension import attempt_vscode_extension_install
from openhands.core.config import OpenHandsConfig, setup_config_from_args

if TYPE_CHECKING:
    from openhands.core.config.condenser_config import NoOpCondenserConfig
from openhands.core.config.mcp_config import OpenHandsMCPConfigImpl
from openhands.core.config.utils import finalize_config
from openhands.core.logger import openhands_logger as logger
from openhands.core.loop import run_agent_until_done
from openhands.core.schema import AgentState
from openhands.core.schema.exit_reason import ExitReason
from openhands.core.setup import (
    create_agent,
    create_controller,
    create_memory,
    create_runtime,
    generate_sid,
    initialize_repository_for_runtime,
)
from openhands.events import EventSource, EventStreamSubscriber
from openhands.events.action import (
    ActionSecurityRisk,
    ChangeAgentStateAction,
    MessageAction,
)
from openhands.events.observation import AgentStateChangedObservation
from openhands.io import read_task
from openhands.mcp_client import add_mcp_tools_to_agent
from openhands.mcp_client.error_collector import mcp_error_collector
from openhands.memory.condenser.impl.llm_summarizing_condenser import (
    LLMSummarizingCondenserConfig,
)
from openhands.runtime import get_runtime_cls
from openhands.storage.settings.file_settings_store import FileSettingsStore
from openhands.utils.utils import create_registry_and_conversation_stats

if TYPE_CHECKING:
    from openhands.controller import AgentController
    from openhands.controller.agent import Agent
    from openhands.events.event import Event
    from openhands.microagent.microagent import BaseMicroagent
    from openhands.runtime.base import Runtime
    from openhands.storage.data_models.settings import Settings


@dataclass
class SessionState:
    """Session state variables."""

    reload_microagents: bool
    new_session_requested: bool
    exit_reason: ExitReason
    is_loaded: asyncio.Event
    is_paused: asyncio.Event
    always_confirm_mode: bool
    auto_highrisk_confirm_mode: bool


@dataclass
class RuntimeComponents:
    """Runtime components."""

    agent: Any
    runtime: Any
    controller: Any
    initial_state: Any
    event_stream: Any
    usage_metrics: Any
    config: OpenHandsConfig
    memory: Any = None
    sid: str = ""


@dataclass
class EventHandlers:
    """Event handlers."""

    prompt_for_next_task: Callable[[str], None]
    on_event: Callable[[Event], None]
    on_event_async: Callable[[Event], None]


def _save_session_state(controller: AgentController, event_stream) -> None:
    """Save the current session state."""
    end_state = controller.get_state()
    end_state.save_to_session(event_stream.sid, event_stream.file_store, event_stream.user_id)


async def _cancel_pending_tasks(loop: asyncio.AbstractEventLoop) -> None:
    """Cancel all pending tasks except the current one."""
    current_task = asyncio.current_task(loop)
    pending = [task for task in asyncio.all_tasks(loop) if task is not current_task]
    if pending:
        _done, pending_set = await asyncio.wait(set(pending), timeout=2.0)
        pending = list(pending_set)
    for task in pending:
        task.cancel()


async def _cleanup_resources(agent: Agent, runtime: Runtime, controller: AgentController) -> None:
    """Clean up agent, runtime, and controller resources."""
    agent.reset()
    runtime.close()
    await controller.close()


async def cleanup_session(
    loop: asyncio.AbstractEventLoop,
    agent: Agent,
    runtime: Runtime,
    controller: AgentController,
) -> None:
    """Clean up all resources from the current session."""
    event_stream = runtime.event_stream
    _save_session_state(controller, event_stream)

    try:
        await _cancel_pending_tasks(loop)
        await _cleanup_resources(agent, runtime, controller)
    except Exception as e:
        logger.error("Error during session cleanup: %s", e)


def _setup_runtime_components(
    config: OpenHandsConfig,
    sid: str,
    loop: asyncio.AbstractEventLoop,
    is_loaded: asyncio.Event,
):
    """Set up runtime components including agent, runtime, and controller."""
    display_runtime_initialization_message(config.runtime)
    loop.run_in_executor(None, display_initialization_animation, "Initializing...", is_loaded)
    llm_registry, conversation_stats, config = create_registry_and_conversation_stats(config, sid, None)
    agent = create_agent(config, llm_registry)
    runtime = create_runtime(config, llm_registry, sid=sid, headless_mode=True, agent=agent)

    def stream_to_console(output: str) -> None:
        update_streaming_output(output)

    runtime.subscribe_to_shell_stream(stream_to_console)

    controller, initial_state = create_controller(agent, runtime, config, conversation_stats)
    event_stream = runtime.event_stream
    usage_metrics = UsageMetrics()
    return agent, runtime, controller, initial_state, event_stream, usage_metrics, config


async def _handle_awaiting_user_input(event, is_paused, reload_microagents, runtime, memory, prompt_for_next_task):
    """Handle AWAITING_USER_INPUT and FINISHED states."""
    if is_paused.is_set():
        return reload_microagents
    if reload_microagents:
        microagents: list[BaseMicroagent] = runtime.get_microagents_from_selected_repo(None)
        memory.load_user_workspace_microagents(microagents)
        reload_microagents = False
    await prompt_for_next_task(event.agent_state)
    return reload_microagents


async def _handle_awaiting_confirmation(
    event,
    is_paused,
    always_confirm_mode,
    auto_highrisk_confirm_mode,
    controller,
    event_stream,
    config,
):
    """Handle AWAITING_USER_CONFIRMATION state."""
    if is_paused.is_set():
        return always_confirm_mode, auto_highrisk_confirm_mode
    if always_confirm_mode:
        event_stream.add_event(ChangeAgentStateAction(AgentState.USER_CONFIRMED), EventSource.USER)
        return always_confirm_mode, auto_highrisk_confirm_mode

    pending_action = controller._pending_action
    security_risk = ActionSecurityRisk.LOW
    if pending_action and hasattr(pending_action, "security_risk"):
        security_risk = pending_action.security_risk

    if auto_highrisk_confirm_mode and security_risk != ActionSecurityRisk.HIGH:
        event_stream.add_event(ChangeAgentStateAction(AgentState.USER_CONFIRMED), EventSource.USER)
        return always_confirm_mode, auto_highrisk_confirm_mode

    confirmation_status = await read_confirmation_input(config, security_risk=security_risk)
    if confirmation_status in ("yes", "always", "auto_highrisk"):
        event_stream.add_event(ChangeAgentStateAction(AgentState.USER_CONFIRMED), EventSource.USER)
    else:
        event_stream.add_event(ChangeAgentStateAction(AgentState.USER_REJECTED), EventSource.USER)
        print_formatted_text(HTML("<skyblue>Okay, please tell me what I should do next/instead.</skyblue>"))

    if confirmation_status == "always":
        always_confirm_mode = True
    elif confirmation_status == "auto_highrisk":
        auto_highrisk_confirm_mode = True

    return always_confirm_mode, auto_highrisk_confirm_mode


async def _setup_memory_and_mcp(agent, runtime, event_stream, config, sid, repo_directory, conversation_instructions):
    """Set up memory and MCP tools."""
    memory = create_memory(
        runtime=runtime,
        event_stream=event_stream,
        sid=sid,
        selected_repository=config.sandbox.selected_repo,
        repo_directory=repo_directory,
        conversation_instructions=conversation_instructions,
        working_dir=os.getcwd(),
    )

    if agent.config.enable_mcp:
        mcp_error_collector.clear_errors()
        mcp_error_collector.enable_collection()
        _, openhands_mcp_stdio_servers = OpenHandsMCPConfigImpl.create_default_mcp_server_config(
            config.mcp_host,
            config,
            None,
        )
        runtime.config.mcp.stdio_servers.extend(openhands_mcp_stdio_servers)
        await add_mcp_tools_to_agent(agent, runtime, memory)
        mcp_error_collector.disable_collection()

    return memory


def _build_welcome_message(agent, config) -> str:
    """Build the welcome message including MCP server information."""
    welcome_message = ""
    if agent.config.enable_mcp:
        total_mcp_servers = len(config.mcp.stdio_servers) + len(config.mcp.sse_servers) + len(config.mcp.shttp_servers)
        if total_mcp_servers > 0:
            mcp_line = f"Using {
                len(
                    config.mcp.stdio_servers)} stdio MCP servers, {
                len(
                    config.mcp.sse_servers)} SSE MCP servers and {
                len(
                    config.mcp.shttp_servers)} SHTTP MCP servers."
            if agent.config.enable_mcp and mcp_error_collector.has_errors():
                mcp_line += " ✗ MCP errors detected (type /mcp → select View errors to view)"
            welcome_message += mcp_line + "\n\n"
    welcome_message += "What do you want to build?"
    return welcome_message


def _handle_session_resumption(initial_state, config, task_content, welcome_message) -> tuple[str, str]:
    """Handle session resumption logic and return initial message and welcome message."""
    initial_message = task_content or ""

    if initial_state is not None:
        logger.info("Resuming session")
        if initial_state.last_error:
            error_message = initial_state.last_error
            if "ERROR_LLM_AUTHENTICATION" in error_message:
                welcome_message = "Authentication error with the LLM provider. Please check your API key."
                llm_config = config.get_llm_config()
                if llm_config.model.startswith("openhands/"):
                    welcome_message += "\nIf you're using OpenHands models, get a new API key from https://app.all-hands.dev/settings/api-keys"
            else:
                initial_message = "NOTE: the last session ended with an error.Let's get back on track. Do NOT resume your task. Ask me about it."
        else:
            initial_message = ""
            welcome_message += "\nLoading previous conversation."

    return initial_message, welcome_message


async def run_session(
    loop: asyncio.AbstractEventLoop,
    config: OpenHandsConfig,
    settings_store: FileSettingsStore,
    current_dir: str,
    task_content: str | None = None,
    conversation_instructions: str | None = None,
    session_name: str | None = None,
    skip_banner: bool = False,
    conversation_id: str | None = None,
) -> bool:
    """Run an OpenHands session with the given configuration and parameters.

    Args:
        loop: The asyncio event loop to run the session on.
        config: The OpenHands configuration.
        settings_store: The file settings store for persistence.
        current_dir: The current working directory.
        task_content: Optional initial task content.
        conversation_instructions: Optional conversation instructions.
        session_name: Optional session name.
        skip_banner: Whether to skip displaying the banner.
        conversation_id: Optional conversation ID to resume.

    Returns:
        bool: True if a new session was requested, False otherwise.
    """
    # Initialize session state
    session_state = _initialize_session_state()
    sid = conversation_id or generate_sid(config, session_name)

    # Setup runtime components
    runtime_components = _setup_runtime_components(config, sid, loop, session_state.is_loaded)

    # Create event handlers
    event_handlers = _create_event_handlers(
        loop,
        session_state,
        runtime_components,
        config,
        current_dir,
        settings_store,
        sid,
    )

    # Setup session
    repo_directory = (
        initialize_repository_for_runtime(runtime_components.runtime, selected_repository=config.sandbox.selected_repo)
        if config.sandbox.selected_repo
        else None
    )
    await _setup_session(
        runtime_components,
        event_handlers,
        config,
        conversation_instructions,
        repo_directory,
    )

    # Initialize session display
    _initialize_session_display(session_state, sid, skip_banner, runtime_components)

    # Handle session startup
    await _handle_session_startup(
        runtime_components,
        session_state,
        task_content,
        event_handlers,
    )

    # Run the session
    await run_agent_until_done(
        runtime_components.controller,
        runtime_components.runtime,
        runtime_components.memory,
        [AgentState.STOPPED, AgentState.ERROR],
    )

    # Cleanup and return
    await cleanup_session(loop, runtime_components.agent, runtime_components.runtime, runtime_components.controller)
    return _display_session_result(session_state.exit_reason, session_state.new_session_requested)


def _initialize_session_state() -> SessionState:
    """Initialize the session state variables.

    Returns:
        SessionState: The initialized session state.
    """
    return SessionState(
        reload_microagents=False,
        new_session_requested=False,
        exit_reason=ExitReason.INTENTIONAL,
        is_loaded=asyncio.Event(),
        is_paused=asyncio.Event(),
        always_confirm_mode=False,
        auto_highrisk_confirm_mode=False,
    )


def _create_event_handlers(
    loop: asyncio.AbstractEventLoop,
    session_state: SessionState,
    runtime_components: RuntimeComponents,
    config: OpenHandsConfig,
    current_dir: str,
    settings_store: FileSettingsStore,
    sid: str,
) -> EventHandlers:
    """Create event handlers for the session.

    Args:
        loop: The asyncio event loop.
        session_state: The session state.
        runtime_components: The runtime components.
        config: The OpenHands configuration.
        current_dir: The current working directory.
        settings_store: The file settings store.
        sid: The session ID.

    Returns:
        EventHandlers: The created event handlers.
    """

    async def prompt_for_next_task(agent_state: str) -> None:
        """Prompt for the next task from the user."""
        nonlocal session_state
        while True:
            next_message = await read_prompt_input(config, agent_state, multiline=config.cli_multiline_input)
            if not next_message.strip():
                continue
            (
                close_repl,
                session_state.reload_microagents,
                session_state.new_session_requested,
                session_state.exit_reason,
            ) = await handle_commands(
                next_message,
                runtime_components.event_stream,
                runtime_components.usage_metrics,
                sid,
                config,
                current_dir,
                settings_store,
                agent_state,
            )
            if close_repl:
                return

    async def on_event_async(event: Event) -> None:
        """Handle events asynchronously."""
        nonlocal session_state
        display_event(event, config)
        update_usage_metrics(event, runtime_components.usage_metrics)

        if isinstance(event, AgentStateChangedObservation):
            await _handle_agent_state_change(event, session_state, runtime_components, prompt_for_next_task)

    def on_event(event: Event) -> None:
        """Handle events synchronously."""
        loop.create_task(on_event_async(event))

    return EventHandlers(
        prompt_for_next_task=prompt_for_next_task,
        on_event=on_event,
        on_event_async=on_event_async,
    )


async def _handle_agent_state_change(
    event: AgentStateChangedObservation,
    session_state: SessionState,
    runtime_components: RuntimeComponents,
    prompt_for_next_task: Callable[[str], None],
) -> None:
    """Handle agent state changes.

    Args:
        event: The agent state change event.
        session_state: The session state.
        runtime_components: The runtime components.
        prompt_for_next_task: The prompt function.
    """
    if event.agent_state not in [AgentState.RUNNING, AgentState.PAUSED]:
        await stop_pause_listener()

    if event.agent_state in [AgentState.AWAITING_USER_INPUT, AgentState.FINISHED]:
        session_state.reload_microagents = await _handle_awaiting_user_input(
            event,
            session_state.is_paused,
            session_state.reload_microagents,
            runtime_components.runtime,
            runtime_components.memory,
            prompt_for_next_task,
        )
    elif event.agent_state == AgentState.AWAITING_USER_CONFIRMATION:
        session_state.always_confirm_mode, session_state.auto_highrisk_confirm_mode = (
            await _handle_awaiting_confirmation(
                event,
                session_state.is_paused,
                session_state.always_confirm_mode,
                session_state.auto_highrisk_confirm_mode,
                runtime_components.controller,
                runtime_components.event_stream,
                runtime_components.config,
            )
        )
    elif event.agent_state == AgentState.PAUSED:
        session_state.is_paused.clear()
        await prompt_for_next_task(event.agent_state)
    elif event.agent_state == AgentState.RUNNING:
        display_agent_running_message()
        start_pause_listener(asyncio.get_event_loop(), session_state.is_paused, runtime_components.event_stream)


async def _setup_session(
    runtime_components: RuntimeComponents,
    event_handlers: EventHandlers,
    config: OpenHandsConfig,
    conversation_instructions: str | None,
    repo_directory: str | None,
) -> None:
    """Setup the session components.

    Args:
        runtime_components: The runtime components.
        event_handlers: The event handlers.
        config: The OpenHands configuration.
        conversation_instructions: Optional conversation instructions.
        repo_directory: Optional repository directory.
    """
    runtime_components.event_stream.subscribe(
        EventStreamSubscriber.MAIN, event_handlers.on_event, runtime_components.sid,
    )
    await runtime_components.runtime.connect()

    runtime_components.memory = await _setup_memory_and_mcp(
        runtime_components.agent,
        runtime_components.runtime,
        runtime_components.event_stream,
        config,
        runtime_components.sid,
        repo_directory,
        conversation_instructions,
    )
    runtime_components.is_loaded.set()


def _initialize_session_display(
    session_state: SessionState,
    sid: str,
    skip_banner: bool,
    runtime_components: RuntimeComponents,
) -> None:
    """Initialize the session display.

    Args:
        session_state: The session state.
        sid: The session ID.
        skip_banner: Whether to skip the banner.
        runtime_components: The runtime components.
    """
    session_state.is_loaded.set()
    clear()
    if not skip_banner:
        display_banner(session_id=sid)


async def _handle_session_startup(
    runtime_components: RuntimeComponents,
    session_state: SessionState,
    task_content: str | None,
    event_handlers: EventHandlers,
) -> None:
    """Handle session startup.

    Args:
        runtime_components: The runtime components.
        session_state: The session state.
        task_content: Optional task content.
        event_handlers: The event handlers.
    """
    welcome_message = _build_welcome_message(runtime_components.agent, runtime_components.runtime.config)
    initial_message, welcome_message = _handle_session_resumption(
        runtime_components.initial_state,
        runtime_components.config,
        task_content,
        welcome_message,
    )
    display_welcome_message(welcome_message)

    if initial_message:
        display_initial_user_prompt(initial_message)
        runtime_components.event_stream.add_event(MessageAction(content=initial_message), EventSource.USER)
    else:
        asyncio.create_task(event_handlers.prompt_for_next_task(""))


def _display_session_result(exit_reason: ExitReason, new_session_requested: bool) -> bool:
    """Display the session result and return whether a new session was requested.

    Args:
        exit_reason: The reason for session exit.
        new_session_requested: Whether a new session was requested.

    Returns:
        bool: Whether a new session was requested.
    """
    if exit_reason == ExitReason.INTENTIONAL:
        print_formatted_text("✅ Session terminated successfully.\n")
    else:
        print_formatted_text(f"⚠️ Session was interrupted: {exit_reason.value}\n")
    return new_session_requested


async def run_setup_flow(config: OpenHandsConfig, settings_store: FileSettingsStore) -> None:
    """Run the setup flow to configure initial settings.

    Returns:
        bool: True if settings were successfully configured, False otherwise.
    """
    display_banner(session_id="setup")
    print_formatted_text(HTML("<grey>No settings found. Starting initial setup...</grey>\n"))
    await modify_llm_settings_basic(config, settings_store)
    print_formatted_text("")
    setup_search = cli_confirm(config, "Would you like to configure Search API settings (optional)?", ["Yes", "No"])
    if setup_search == 0:
        from openhands.cli.settings import modify_search_api_settings

        await modify_search_api_settings(config, settings_store)


def run_alias_setup_flow(config: OpenHandsConfig) -> None:
    """Run the alias setup flow to configure shell aliases.

    Prompts the user to set up aliases for 'openhands' and 'oh' commands.
    Handles existing aliases by offering to keep or remove them.

    Args:
        config: OpenHands configuration
    """
    print_formatted_text("")
    print_formatted_text(HTML("<gold>🚀 Welcome to OpenHands CLI!</gold>"))
    print_formatted_text("")
    print_formatted_text(HTML("<grey>Would you like to set up convenient shell aliases?</grey>"))
    print_formatted_text("")
    print_formatted_text(HTML("<grey>This will add the following aliases to your shell profile:</grey>"))
    print_formatted_text(HTML("<grey>  • <b>openhands</b> → uvx --python 3.12 --from openhands-ai openhands</grey>"))
    print_formatted_text(HTML("<grey>  • <b>oh</b> → uvx --python 3.12 --from openhands-ai openhands</grey>"))
    print_formatted_text("")
    print_formatted_text(HTML("<ansiyellow>⚠️  Note: This requires uv to be installed first.</ansiyellow>"))
    print_formatted_text(
        HTML("<ansiyellow>   Installation guide: https://docs.astral.sh/uv/getting-started/installation</ansiyellow>"),
    )
    print_formatted_text("")
    choice = cli_confirm(config, "Set up shell aliases?", ["Yes, set up aliases", "No, skip this step"])
    if choice == 0:
        if add_aliases_to_shell_config():
            print_formatted_text("")
            print_formatted_text(HTML("<ansigreen>✅ Aliases added successfully!</ansigreen>"))
            shell_manager = ShellConfigManager()
            reload_cmd = shell_manager.get_reload_command()
            print_formatted_text(
                HTML(f"<grey>Run <b>{reload_cmd}</b> (or restart your terminal) to use the new aliases.</grey>"),
            )
        else:
            print_formatted_text("")
            print_formatted_text(
                HTML("<ansired>❌ Failed to add aliases. You can set them up manually later.</ansired>"),
            )
    else:
        mark_alias_setup_declined()
        print_formatted_text("")
        print_formatted_text(HTML("<grey>Skipped alias setup. You can run this setup again anytime.</grey>"))
    print_formatted_text("")


def _setup_logging(args) -> None:
    """Setup logging configuration based on command line arguments."""
    if args.log_level and isinstance(args.log_level, str):
        log_level = getattr(logging, str(args.log_level).upper())
        logger.setLevel(log_level)
    else:
        env_log_level = os.getenv("LOG_LEVEL")
        if not env_log_level:
            logger.setLevel(logging.WARNING)


def _load_config_and_setup_vscode(args) -> OpenHandsConfig:
    """Load configuration and attempt VS Code extension installation."""
    if not os.path.exists(args.config_file):
        home_config_file = os.path.join(os.path.expanduser("~"), ".openhands", "config.toml")
        logger.info(
            "Config file %s does not exist, using default config file in home directory: %s.",
            args.config_file,
            home_config_file,
        )
        args.config_file = home_config_file
    config: OpenHandsConfig = setup_config_from_args(args)
    attempt_vscode_extension_install()
    return config


async def _initialize_settings(config: OpenHandsConfig) -> tuple[Settings | None, bool, FileSettingsStore]:
    """Initialize settings and determine if banner should be shown."""
    settings_store = await FileSettingsStore.get_instance(config=config, user_id=None)
    settings = await settings_store.load()
    banner_shown = False
    if not settings:
        clear()
        await run_setup_flow(config, settings_store)
        banner_shown = True
        settings = await settings_store.load()
    return (settings, banner_shown, settings_store)


def _apply_settings_to_config(config, settings) -> None:
    """Apply settings to configuration."""
    assert settings.agent is not None
    config.default_agent = settings.agent

    llm_config = config.get_llm_config()
    if settings.llm_model and settings.llm_api_key:
        logger.debug("Using LLM configuration from settings.json")
        llm_config.model = settings.llm_model
        llm_config.api_key = settings.llm_api_key
        llm_config.base_url = settings.llm_base_url
        config.set_llm_config(llm_config)

    config.security.confirmation_mode = settings.confirmation_mode or False

    if settings.search_api_key and (not config.search_api_key):
        config.search_api_key = settings.search_api_key
        logger.debug("Using search API key from settings.json")

    _configure_condenser(config, settings)


def _configure_condenser(config, settings) -> None:
    """Configure condenser based on settings."""
    if settings.enable_default_condenser:
        llm_config = config.get_llm_config()
        agent_config = config.get_agent_config(config.default_agent)
        agent_config.condenser = LLMSummarizingCondenserConfig(llm_config=llm_config, type="llm")
        config.set_agent_config(agent_config)
        config.enable_default_condenser = True
    else:
        agent_config = config.get_agent_config(config.default_agent)
        from openhands.core.config.condenser_config import NoOpCondenserConfig
        agent_config.condenser = NoOpCondenserConfig(type="noop")
        config.set_agent_config(agent_config)
        config.enable_default_condenser = False


def _should_override_cli_defaults(args) -> bool:
    """Determine if CLI defaults should be overridden."""
    val_override = args.override_cli_mode
    return (
        val_override is True
        or (isinstance(val_override, str) and val_override.lower() in ("true", "1"))
        or (isinstance(val_override, int) and val_override == 1)
    )


def _apply_cli_defaults(config) -> None:
    """Apply CLI-specific defaults to configuration."""
    config.runtime = "cli"
    if not config.workspace_base:
        config.workspace_base = os.getcwd()
    config.security.confirmation_mode = True
    config.security.security_analyzer = "llm"
    agent_config = config.get_agent_config(config.default_agent)
    agent_config.cli_mode = True
    config.set_agent_config(agent_config)
    finalize_config(config)


def _handle_alias_setup(config, banner_shown: bool) -> None:
    """Handle alias setup if needed."""
    if not aliases_exist_in_shell_config() and (not alias_setup_declined()) and sys.stdin.isatty():
        if not banner_shown:
            clear()
        run_alias_setup_flow(config)


def _prepare_task_string(args, config) -> str:
    """Prepare the task string based on arguments."""
    if not args.file:
        return read_task(args, config.cli_multiline_input)
    with open(args.file, encoding="utf-8") as file:
        file_content = file.read()
    return (
        f"The user has tagged a file '{args.file}'.\n"
        f"Please read and understand the following file content first:\n\n"
        f"```\n{file_content}\n```\n\n"
        f"After reviewing the file, please ask the user what they would like to do with it."
    )


async def _run_sessions(loop, config, settings_store, current_dir: str, task_str: str, args) -> None:
    """Run the main session and any additional sessions."""
    get_runtime_cls(config.runtime).setup(config)

    new_session_requested = await run_session(
        loop,
        config,
        settings_store,
        current_dir,
        task_str,
        session_name=args.name,
        skip_banner=args.banner_shown,
        conversation_id=args.conversation,
    )

    while new_session_requested:
        new_session_requested = await run_session(loop, config, settings_store, current_dir, None)

    get_runtime_cls(config.runtime).teardown(config)


async def main_with_loop(loop: asyncio.AbstractEventLoop, args) -> None:
    """Runs the agent in CLI mode."""
    _setup_logging(args)
    config = _load_config_and_setup_vscode(args)
    settings, banner_shown, settings_store = await _initialize_settings(config)

    # Apply settings if available
    if settings:
        _apply_settings_to_config(config, settings)

    # Apply CLI defaults if not overridden
    if not _should_override_cli_defaults(args):
        _apply_cli_defaults(config)

    # Handle alias setup
    _handle_alias_setup(config, banner_shown)

    # Validate workspace
    current_dir = config.workspace_base
    if not current_dir:
        # Use current working directory as default workspace
        current_dir = os.getcwd()
        config.workspace_base = current_dir
        logger.info("Using current directory as workspace: %s", current_dir)
    if not check_folder_security_agreement(config, current_dir):
        return

    # Prepare task and run sessions
    task_str = _prepare_task_string(args, config)
    await _run_sessions(loop, config, settings_store, current_dir, task_str, args)


def run_cli_command(args) -> None:
    """Run the CLI command with proper error handling and cleanup."""
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        loop.run_until_complete(main_with_loop(loop, args))
    except KeyboardInterrupt:
        print_formatted_text("⚠️ Session was interrupted: interrupted\n")
    except ConnectionRefusedError as e:
        print_formatted_text(f"Connection refused: {e}")
        sys.exit(1)
    finally:
        try:
            pending = asyncio.all_tasks(loop)
            for task in pending:
                task.cancel()
            loop.run_until_complete(asyncio.gather(*pending, return_exceptions=True))
            loop.close()
        except Exception as e:
            print_formatted_text(f"Error during cleanup: {e}")
            sys.exit(1)
