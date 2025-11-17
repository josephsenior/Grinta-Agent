"""Interactive CLI command handlers and supporting utilities."""

from __future__ import annotations

import asyncio
import os
import sys
from pathlib import Path
import re
import shlex
from typing import TYPE_CHECKING, Any, Awaitable, Callable, Dict

import tomlkit
from prompt_toolkit import HTML, print_formatted_text
from prompt_toolkit.patch_stdout import patch_stdout
from prompt_toolkit.shortcuts import clear, print_container
from prompt_toolkit.widgets import Frame, TextArea
from pydantic import ValidationError

from forge.cli.settings import (
    display_settings,
    modify_llm_settings_advanced,
    modify_llm_settings_basic,
    modify_search_api_settings,
)
from forge.cli.tui import (
    COLOR_GREY,
    UsageMetrics,
    cli_confirm,
    create_prompt_session,
    display_help,
    display_mcp_errors,
    display_shutdown_message,
    display_status,
    read_prompt_input,
)
from forge.cli.utils import (
    add_local_config_trusted_dir,
    get_local_config_trusted_dirs,
    read_file,
    write_to_file,
)
from forge.core.config.mcp_config import (
    MCPSHTTPServerConfig,
    MCPSSEServerConfig,
    MCPStdioServerConfig,
)
from forge.core.schemas import AgentState
from forge.core.schema.exit_reason import ExitReason
from forge.events import EventSource
from forge.events.action import ChangeAgentStateAction, MessageAction
from forge.metasop.capability_audit import audit_capabilities
from forge.metasop.registry import SOPS_DIR, load_role_profiles
from forge.metasop.replay import ReplayError, replay_manifest

if TYPE_CHECKING:
    from forge.core.config import ForgeConfig
    from forge.events.stream import EventStream
    from forge.storage.settings.file_settings_store import FileSettingsStore


async def collect_input(config: ForgeConfig, prompt_text: str) -> str | None:
    """Collect user input with cancellation support.

    Args:
        config: Forge configuration
        prompt_text: Text to display to user

    Returns:
        str | None: User input string, or None if user cancelled

    """
    print_formatted_text(prompt_text, end=" ")
    user_input = await read_prompt_input(config, "", multiline=False)
    if user_input.strip().lower() in ["/exit", "/cancel", "cancel"]:
        return None
    return user_input.strip()


def restart_cli() -> None:
    """Restart the CLI by replacing the current process."""
    print_formatted_text("🔄 Restarting Forge CLI...")
    python_executable = sys.executable
    # Sanitize argv to avoid control characters being passed through
    script_args = [arg for arg in sys.argv if "\n" not in arg and "\r" not in arg][:128]
    try:
        os.execv(python_executable, [python_executable, *script_args])
    except Exception as e:
        print_formatted_text(f"❌ Failed to restart CLI: {e}")
        print_formatted_text(
            "Please restart Forge manually for changes to take effect."
        )


async def prompt_for_restart(config: ForgeConfig) -> bool:
    """Prompt user if they want to restart the CLI and return their choice."""
    print_formatted_text("📝 MCP server configuration updated successfully!")
    print_formatted_text("The changes will take effect after restarting forge.")
    prompt_session = create_prompt_session(config)
    while True:
        try:
            with patch_stdout():
                response = await prompt_session.prompt_async(
                    HTML("<gold>Would you like to restart Forge now? (y/n): </gold>"),
                )
                response = response.strip().lower() if response else ""
                if response in ["y", "yes"]:
                    return True
                if response in ["n", "no"]:
                    return False
                print_formatted_text('Please enter "y" for yes or "n" for no.')
        except (KeyboardInterrupt, EOFError):
            return False


def _parse_replay_command(command: str) -> tuple[str, bool] | None:
    """Parse replay command and return manifest path and assert mode."""
    parts = command.split()
    if len(parts) < 2:
        print_formatted_text("Usage: /replay <manifest_path> [--assert]")
        return None

    manifest_path = parts[1]
    assert_mode = "--assert" in parts[2:]
    return manifest_path, assert_mode


def _display_replay_header(result: dict, manifest_path: str) -> None:
    """Display replay header."""
    header = "Replay OK" if result["ok"] else "Replay DIFFS"
    print_formatted_text(f"\n[{header}] {manifest_path}")


def _display_replay_summary(result: dict) -> None:
    """Display replay summary."""
    print_formatted_text(
        f"Summary: steps={result['summary']['steps']} diff_count={result['summary']['diff_count']}",
    )


def _display_replay_diffs(result: dict) -> None:
    """Display replay diffs."""
    if result["diffs"]:
        for d in result["diffs"][:50]:
            print_formatted_text(f" - {d}")


def _display_replay_assertion(result: dict, assert_mode: bool) -> None:
    """Display replay assertion result."""
    if assert_mode and (not result["ok"]):
        print_formatted_text("Assertion failed: differences detected.")


def _display_replay_result(result: dict, manifest_path: str, assert_mode: bool) -> None:
    """Display replay result to user."""
    _display_replay_header(result, manifest_path)
    _display_replay_summary(result)
    _display_replay_diffs(result)
    _display_replay_assertion(result, assert_mode)


async def _handle_replay_command(command: str) -> None:
    """Handle /replay command execution."""
    parsed = _parse_replay_command(command)
    if parsed is None:
        return

    manifest_path, assert_mode = parsed

    try:
        result = replay_manifest(manifest_path, assert_mode=assert_mode)
        _display_replay_result(result, manifest_path, assert_mode)
    except ReplayError as e:
        print_formatted_text(f"Replay error: {e}")
    except Exception as e:
        print_formatted_text(f"Unexpected replay crash: {e}")


async def _handle_capaudit_command(command: str) -> None:
    """Handle /capaudit command execution."""
    as_json = "--json" in command.split()[1:]

    try:
        profiles = load_role_profiles()
        report = audit_capabilities(profiles, SOPS_DIR)

        if as_json:
            import json as _json

            print_formatted_text(_json.dumps(report, indent=2))
        else:
            _display_capaudit_summary(report)
    except Exception as e:
        print_formatted_text(f"Capability audit error: {e}")


def _display_capaudit_summary(report: dict) -> None:
    """Display capability audit summary in human-readable format."""
    print_formatted_text("\nCapability Audit Summary:")
    print_formatted_text(
        f" Profiles: {report['profiles_count']}  SOPs: {report['sops_scanned']}"
    )

    _display_unknown_capabilities(report["unknown_capabilities"])
    _display_unused_capabilities(report["unused_capabilities"])
    _display_missing_capabilities(report["steps_missing_capabilities"])
    _display_capability_usage(report.get("capability_usage", {}))

    print_formatted_text("\nUse '/capaudit --json' for full details.")


def _display_unknown_capabilities(unknown_caps: list) -> None:
    """Display unknown capabilities."""
    print_formatted_text(f" Unknown capabilities: {len(unknown_caps)}")
    if unknown_caps:
        print_formatted_text("  - " + ", ".join(unknown_caps[:20]))


def _display_unused_capabilities(unused_caps: list) -> None:
    """Display unused capabilities."""
    print_formatted_text(f" Unused capabilities: {len(unused_caps)}")
    if unused_caps:
        print_formatted_text("  - " + ", ".join(unused_caps[:20]))


def _display_missing_capabilities(missing_caps: list) -> None:
    """Display steps with missing capabilities."""
    print_formatted_text(f" Steps with missing capabilities: {len(missing_caps)}")
    for miss in missing_caps[:10]:
        print_formatted_text(
            f"  - {miss['sop']}::{miss['step_id']} role={miss['role']} missing={miss['missing']}",
        )


def _display_capability_usage(usage: dict) -> None:
    """Display top capability usage."""
    if not usage:
        return

    top = sorted(usage.items(), key=lambda x: x[1], reverse=True)[:10]
    print_formatted_text(" Top capability usage:")
    for cap, count in top:
        print_formatted_text(f"   * {cap}: {count}")


async def handle_commands(
    command: str,
    event_stream: EventStream,
    usage_metrics: UsageMetrics,
    sid: str,
    config: ForgeConfig,
    current_dir: str,
    settings_store: FileSettingsStore,
    agent_state: str,
) -> tuple[bool, bool, bool, ExitReason]:
    """Handle CLI commands and route to the correct command handler."""
    normalized_command = command.strip()

    if result := _dispatch_sync_command(
        normalized_command,
        usage_metrics,
        sid,
        config,
        event_stream,
    ):
        return result

    async_result = await _dispatch_async_command(
        normalized_command,
        config,
        event_stream,
        current_dir,
        settings_store,
        agent_state,
    )
    if async_result:
        return async_result

    prefix_result = await _dispatch_prefixed_command(normalized_command)
    if prefix_result:
        return prefix_result

    return _handle_user_message(command, event_stream)


def _handle_help_command() -> tuple[bool, bool, bool, str | None]:
    """Handle /help command."""
    handle_help_command()
    return (False, False, False, None)


def _handle_status_command(usage_metrics, sid) -> tuple[bool, bool, bool, str | None]:
    """Handle /status command."""
    handle_status_command(usage_metrics, sid)
    return (False, False, False, None)


def handle_exit_command(
    config: ForgeConfig,
    event_stream: EventStream,
    usage_metrics: UsageMetrics,
    sid: str,
) -> bool:
    """Handle /exit command with confirmation.

    Args:
        config: Forge configuration
        event_stream: Event stream to send stop event
        usage_metrics: Usage metrics for display
        sid: Session ID

    Returns:
        True if user confirmed exit

    """
    close_repl = False
    confirm_exit = (
        cli_confirm(config, "\nTerminate session?", ["Yes, proceed", "No, dismiss"])
        == 0
    )
    if confirm_exit:
        event_stream.add_event(
            ChangeAgentStateAction(AgentState.STOPPED), EventSource.ENVIRONMENT
        )
        display_shutdown_message(usage_metrics, sid)
        close_repl = True
    return close_repl


def _dispatch_sync_command(
    normalized_command: str,
    usage_metrics: UsageMetrics,
    sid: str,
    config: ForgeConfig,
    event_stream: EventStream,
) -> tuple[bool, bool, bool, ExitReason] | None:
    handlers: Dict[str, Callable[[], tuple[bool, bool, bool, ExitReason]]] = {
        "/help": _result_for_help,
        "/status": lambda: _result_for_status(usage_metrics, sid),
        "/new": lambda: _result_for_new(config, event_stream, usage_metrics, sid),
        "/exit": lambda: _result_for_exit(config, event_stream, usage_metrics, sid),
    }
    handler = handlers.get(normalized_command)
    if handler:
        return handler()
    return None


async def _dispatch_async_command(
    normalized_command: str,
    config: ForgeConfig,
    event_stream: EventStream,
    current_dir: str,
    settings_store: FileSettingsStore,
    agent_state: str,
) -> tuple[bool, bool, bool, ExitReason] | None:
    async_handlers: Dict[
        str, Callable[[], Awaitable[tuple[bool, bool, bool, ExitReason]]]
    ] = {
        "/init": lambda: _result_for_init(config, event_stream, current_dir),
        "/settings": lambda: _result_for_settings(config, settings_store),
        "/mcp": lambda: _result_for_mcp(config),
        "/resume": lambda: _result_for_resume(event_stream, agent_state),
    }
    handler = async_handlers.get(normalized_command)
    if handler:
        return await handler()
    return None


async def _dispatch_prefixed_command(
    normalized_command: str,
) -> tuple[bool, bool, bool, ExitReason] | None:
    prefix_handlers: Dict[str, Callable[[str], Awaitable[None]]] = {
        "/replay": _handle_replay_command,
        "/capaudit": _handle_capaudit_command,
    }
    for prefix, handler in prefix_handlers.items():
        if normalized_command.startswith(prefix):
            await handler(normalized_command)
            return _command_result()
    return None


def _handle_user_message(
    command: str, event_stream: EventStream
) -> tuple[bool, bool, bool, ExitReason]:
    action = MessageAction(content=command)
    event_stream.add_event(action, EventSource.USER)
    return (True, False, False, ExitReason.INTENTIONAL)


def _result_for_help() -> tuple[bool, bool, bool, ExitReason]:
    handle_help_command()
    return _command_result()


def _result_for_status(
    usage_metrics: UsageMetrics, sid: str
) -> tuple[bool, bool, bool, ExitReason]:
    handle_status_command(usage_metrics, sid)
    return _command_result()


def _result_for_new(
    config: ForgeConfig,
    event_stream: EventStream,
    usage_metrics: UsageMetrics,
    sid: str,
) -> tuple[bool, bool, bool, ExitReason]:
    close_repl, new_session_requested = handle_new_command(
        config, event_stream, usage_metrics, sid
    )
    exit_reason = ExitReason.INTENTIONAL if close_repl else ExitReason.ERROR
    return _command_result(close_repl, False, new_session_requested, exit_reason)


def _result_for_exit(
    config: ForgeConfig,
    event_stream: EventStream,
    usage_metrics: UsageMetrics,
    sid: str,
) -> tuple[bool, bool, bool, ExitReason]:
    close_repl = handle_exit_command(config, event_stream, usage_metrics, sid)
    exit_reason = ExitReason.INTENTIONAL if close_repl else ExitReason.ERROR
    return _command_result(close_repl, False, False, exit_reason)


async def _result_for_init(
    config: ForgeConfig,
    event_stream: EventStream,
    current_dir: str,
) -> tuple[bool, bool, bool, ExitReason]:
    close_repl, reload_microagents = await handle_init_command(
        config, event_stream, current_dir
    )
    exit_reason = ExitReason.INTENTIONAL if close_repl else ExitReason.ERROR
    return _command_result(close_repl, reload_microagents, False, exit_reason)


async def _result_for_settings(
    config: ForgeConfig, settings_store: FileSettingsStore
) -> tuple[bool, bool, bool, ExitReason]:
    await handle_settings_command(config, settings_store)
    return _command_result()


async def _result_for_mcp(
    config: ForgeConfig,
) -> tuple[bool, bool, bool, ExitReason]:
    await handle_mcp_command(config)
    return _command_result()


async def _result_for_resume(
    event_stream: EventStream,
    agent_state: str,
) -> tuple[bool, bool, bool, ExitReason]:
    close_repl, new_session_requested = await handle_resume_command(
        event_stream, agent_state
    )
    exit_reason = ExitReason.INTENTIONAL if close_repl else ExitReason.ERROR
    return _command_result(close_repl, False, new_session_requested, exit_reason)


def _command_result(
    close_repl: bool = False,
    reload_microagents: bool = False,
    new_session_requested: bool = False,
    exit_reason: ExitReason = ExitReason.ERROR,
) -> tuple[bool, bool, bool, ExitReason]:
    return close_repl, reload_microagents, new_session_requested, exit_reason


def handle_help_command() -> None:
    """Handle /help command by displaying help message."""
    display_help()


async def handle_init_command(
    config: ForgeConfig,
    event_stream: EventStream,
    current_dir: str,
) -> tuple[bool, bool]:
    """Handle /init command to initialize repository context.

    Args:
        config: Forge configuration
        event_stream: Event stream to send init message
        current_dir: Current working directory

    Returns:
        Tuple of (close_repl, reload_microagents) flags

    """
    close_repl = False
    reload_microagents = False
    if config.runtime in ("local", "cli"):
        init_repo = await init_repository(config, current_dir)
        if init_repo:
            REPO_MD_CREATE_PROMPT = "\n        Please explore this repository. Create the file .Forge/microagents/repo.md with:\n            - A description of the project\n            - An overview of the file structure\n            - Any information on how to run tests or other relevant commands\n            - Any other information that would be helpful to a brand new developer\n        Keep it short--just a few paragraphs will do.\n    "
            event_stream.add_event(
                MessageAction(content=REPO_MD_CREATE_PROMPT), EventSource.USER
            )
            reload_microagents = True
            close_repl = True
    else:
        print_formatted_text(
            "\nRepository initialization through the CLI is only supported for CLI and local runtimes.\n",
        )
    return (close_repl, reload_microagents)


def handle_status_command(usage_metrics: UsageMetrics, sid: str) -> None:
    """Handle /status command to display session status and metrics.

    Args:
        usage_metrics: Usage metrics to display
        sid: Session ID

    """
    display_status(usage_metrics, sid)


def handle_new_command(
    config: ForgeConfig,
    event_stream: EventStream,
    usage_metrics: UsageMetrics,
    sid: str,
) -> tuple[bool, bool]:
    """Handle /new command to start new conversation.

    Args:
        config: Forge configuration
        event_stream: Event stream to send stop event
        usage_metrics: Usage metrics for display
        sid: Session ID

    Returns:
        Tuple of (close_repl, new_session_requested) flags

    """
    close_repl = False
    new_session_requested = False
    new_session_requested = (
        cli_confirm(
            config,
            "\nCurrent session will be terminated and you will lose the conversation history.\n\nContinue?",
            ["Yes, proceed", "No, dismiss"],
        )
        == 0
    )
    if new_session_requested:
        close_repl = True
        new_session_requested = True
        event_stream.add_event(
            ChangeAgentStateAction(AgentState.STOPPED), EventSource.ENVIRONMENT
        )
        display_shutdown_message(usage_metrics, sid)
    return (close_repl, new_session_requested)


async def handle_settings_command(
    config: ForgeConfig, settings_store: FileSettingsStore
) -> None:
    """Handle /settings command to modify configuration.

    Args:
        config: Forge configuration to modify
        settings_store: Settings storage backend

    """
    display_settings(config)
    modify_settings = cli_confirm(
        config,
        "\nWhich settings would you like to modify?",
        ["LLM (Basic)", "LLM (Advanced)", "Search API (Optional)", "Go back"],
    )
    if modify_settings == 0:
        await modify_llm_settings_basic(config, settings_store)
    elif modify_settings == 1:
        await modify_llm_settings_advanced(config, settings_store)
    elif modify_settings == 2:
        await modify_search_api_settings(config, settings_store)


async def handle_resume_command(
    event_stream: EventStream, agent_state: str
) -> tuple[bool, bool]:
    """Handle /resume command to resume paused agent.

    Args:
        event_stream: Event stream to send continue message
        agent_state: Current agent state

    Returns:
        Tuple of (close_repl, new_session_requested) flags

    """
    close_repl = True
    new_session_requested = False
    if agent_state != AgentState.PAUSED:
        close_repl = False
        print_formatted_text(
            HTML(
                "<ansired>Error: Agent is not paused. /resume command is only available when agent is paused.</ansired>",
            ),
        )
        return (close_repl, new_session_requested)
    event_stream.add_event(MessageAction(content="continue"), EventSource.USER)
    return (close_repl, new_session_requested)


async def init_repository(config: ForgeConfig, current_dir: str) -> bool:
    """Initialize repository with Forge microagent context.

    Prompts user to create repo.md with project documentation.

    Args:
        config: Forge configuration
        current_dir: Current working directory

    Returns:
        True if user confirmed initialization

    """
    repo_file_path = Path(current_dir) / ".Forge" / "microagents" / "repo.md"
    init_repo = False
    if repo_file_path.exists():
        try:
            content = await asyncio.get_event_loop().run_in_executor(
                None, read_file, repo_file_path
            )
            print_formatted_text(
                "Repository instructions file (repo.md) already exists.\n"
            )
            container = Frame(
                TextArea(
                    text=content, read_only=True, style=COLOR_GREY, wrap_lines=True
                ),
                title="Repository Instructions (repo.md)",
                style=f"fg:{COLOR_GREY}",
            )
            print_container(container)
            print_formatted_text("")
            init_repo = (
                cli_confirm(
                    config,
                    "Do you want to re-initialize?",
                    ["Yes, re-initialize", "No, dismiss"],
                )
                == 0
            )
            if init_repo:
                write_to_file(repo_file_path, "")
        except Exception:
            print_formatted_text("Error reading repository instructions file (repo.md)")
            init_repo = False
    else:
        print_formatted_text(
            "\nRepository instructions file will be created by exploring the repository.\n"
        )
        init_repo = (
            cli_confirm(
                config, "Do you want to proceed?", ["Yes, create", "No, dismiss"]
            )
            == 0
        )
    return init_repo


def check_folder_security_agreement(config: ForgeConfig, current_dir: str) -> bool:
    """Check if current directory is trusted, prompt user if not.

    Args:
        config: Forge configuration with trusted directories
        current_dir: Directory to check

    Returns:
        True if directory is trusted or user approves

    """
    app_config_trusted_dirs = config.sandbox.trusted_dirs
    local_config_trusted_dirs = get_local_config_trusted_dirs()
    trusted_dirs = local_config_trusted_dirs
    if not local_config_trusted_dirs:
        trusted_dirs = app_config_trusted_dirs
    is_trusted = current_dir in trusted_dirs
    if not is_trusted:
        security_frame = Frame(
            TextArea(
                text=f" Do you trust the files in this folder?\n\n   {current_dir}\n\n Forge may read and execute files in this folder with your permission.",
                style=COLOR_GREY,
                read_only=True,
                wrap_lines=True,
            ),
            style=f"fg:{COLOR_GREY}",
        )
        clear()
        print_container(security_frame)
        print_formatted_text("")
        confirm = (
            cli_confirm(
                config, "Do you wish to continue?", ["Yes, proceed", "No, exit"]
            )
            == 0
        )
        if confirm:
            add_local_config_trusted_dir(current_dir)
        return confirm
    return True


async def handle_mcp_command(config: ForgeConfig) -> None:
    """Handle MCP command with interactive menu."""
    action = cli_confirm(
        config,
        "MCP Server Configuration",
        [
            "List configured servers",
            "Add new server",
            "Remove server",
            "View errors",
            "Go back",
        ],
    )
    if action == 0:
        display_mcp_servers(config)
    elif action == 1:
        await add_mcp_server(config)
    elif action == 2:
        await remove_mcp_server(config)
    elif action == 3:
        handle_mcp_errors_command()


def display_mcp_servers(config: ForgeConfig) -> None:
    """Display MCP server configuration information."""
    mcp_config = config.mcp
    sse_count = len(mcp_config.sse_servers)
    stdio_count = len(mcp_config.stdio_servers)
    shttp_count = len(mcp_config.shttp_servers)
    total_count = sse_count + stdio_count + shttp_count
    if total_count == 0:
        print_formatted_text(
            "No custom MCP servers configured. See the documentation to learn more:\n  https://docs.all-hands.dev/usage/how-to/cli-mode#using-mcp-servers",
        )
    else:
        print_formatted_text(
            f"Configured MCP servers:\n  • SSE servers: {sse_count}\n  • Stdio servers: {stdio_count}\n  • SHTTP servers: {shttp_count}\n  • Total: {total_count}",
        )
        if sse_count > 0:
            print_formatted_text("SSE Servers:")
            for idx, sse_server in enumerate(mcp_config.sse_servers, 1):
                print_formatted_text(f"  {idx}. {sse_server.url}")
            print_formatted_text("")
        if stdio_count > 0:
            print_formatted_text("Stdio Servers:")
            for idx, stdio_server in enumerate(mcp_config.stdio_servers, 1):
                print_formatted_text(
                    f"  {idx}. {stdio_server.name} ({stdio_server.command})"
                )
            print_formatted_text("")
        if shttp_count > 0:
            print_formatted_text("SHTTP Servers:")
            for idx, shttp_server in enumerate(mcp_config.shttp_servers, 1):
                print_formatted_text(f"  {idx}. {shttp_server.url}")
            print_formatted_text("")


def handle_mcp_errors_command() -> None:
    """Display MCP connection errors."""
    display_mcp_errors()


def get_config_file_path() -> Path:
    """Get the path to the config file. By default, we use config.toml in the current working directory. If not found, we use ~/.Forge/config.toml."""
    current_dir = Path.cwd() / "config.toml"
    if current_dir.exists():
        return current_dir
    return Path.home() / ".Forge" / "config.toml"


def load_config_file(file_path: Path) -> dict:
    """Load the config file, creating it if it doesn't exist."""
    if file_path.exists():
        try:
            with open(file_path, encoding="utf-8") as f:
                return dict(tomlkit.load(f))
        except Exception:
            pass
    file_path.parent.mkdir(parents=True, exist_ok=True)
    return {}


def save_config_file(config_data: dict, file_path: Path) -> None:
    """Save the config file with proper MCP formatting."""
    doc = tomlkit.document()
    for key, value in config_data.items():
        if key == "mcp":
            mcp_section = tomlkit.table()
            for mcp_key, mcp_value in value.items():
                server_array = tomlkit.array()
                for server_config in mcp_value:
                    if isinstance(server_config, dict):
                        inline_table = tomlkit.inline_table()
                        for server_key, server_val in server_config.items():
                            inline_table[server_key] = server_val
                        server_array.append(inline_table)
                    else:
                        server_array.append(server_config)
                mcp_section[mcp_key] = server_array
            doc[key] = mcp_section
        else:
            doc[key] = value
    with open(file_path, "w", encoding="utf-8") as f:
        f.write(tomlkit.dumps(doc))


def _ensure_mcp_config_structure(config_data: dict) -> None:
    """Ensure MCP configuration structure exists in config data."""
    if "mcp" not in config_data:
        config_data["mcp"] = {}


def _add_server_to_config(server_type: str, server_config: dict) -> Path:
    """Add a server configuration to the config file."""
    config_file_path = get_config_file_path()
    config_data = load_config_file(config_file_path)
    _ensure_mcp_config_structure(config_data)
    if server_type not in config_data["mcp"]:
        config_data["mcp"][server_type] = []
    config_data["mcp"][server_type].append(server_config)
    save_config_file(config_data, config_file_path)
    return config_file_path


async def add_mcp_server(config: ForgeConfig) -> None:
    """Add a new MCP server configuration."""
    transport_type = cli_confirm(
        config,
        "Select MCP server transport type:",
        [
            "SSE (Server-Sent Events)",
            "Stdio (Standard Input/Output)",
            "SHTTP (Streamable HTTP)",
            "Cancel",
        ],
    )
    if transport_type == 3:
        return
    try:
        if transport_type == 0:
            await add_sse_server(config)
        elif transport_type == 1:
            await add_stdio_server(config)
        elif transport_type == 2:
            await add_shttp_server(config)
    except Exception as e:
        print_formatted_text(f"Error adding MCP server: {e}")


async def _collect_sse_server_inputs(
    config: ForgeConfig,
) -> tuple[str | None, str | None]:
    """Collect user inputs for SSE server configuration."""
    url = await collect_input(config, "\nEnter server URL:")
    if url is None:
        return None, None

    api_key = await collect_input(
        config, "\nEnter API key (optional, press Enter to skip):"
    )
    return (None, None) if api_key is None else (url, api_key or None)


async def _validate_and_create_sse_server(
    config: ForgeConfig,
    url: str,
    api_key: str | None,
) -> MCPSSEServerConfig | None:
    """Validate inputs and create SSE server config."""
    try:
        return MCPSSEServerConfig(url=url, api_key=api_key)
    except ValidationError as e:
        print_formatted_text("❌ Please fix the following errors:")
        for error in e.errors():
            field = error["loc"][0] if error["loc"] else "unknown"
            print_formatted_text(f"  • {field}: {error['msg']}")
        return None


def _build_sse_server_config(server) -> dict:
    """Build SSE server configuration dictionary."""
    server_config = {"url": server.url}
    if server.api_key:
        server_config["api_key"] = server.api_key
    return server_config


async def add_sse_server(config: ForgeConfig) -> None:
    """Add an SSE MCP server."""
    print_formatted_text("Adding SSE MCP Server")

    while True:
        url, api_key = await _collect_sse_server_inputs(config)
        if url is None:
            print_formatted_text("Operation cancelled.")
            return

        server = await _validate_and_create_sse_server(config, url, api_key)
        if server is not None:
            break

        if cli_confirm(config, "\nTry again?") != 0:
            print_formatted_text("Operation cancelled.")
            return

    server_config = _build_sse_server_config(server)
    config_file_path = _add_server_to_config("sse_servers", server_config)
    print_formatted_text(f"✓ SSE MCP server added to {config_file_path}: {server.url}")

    if await prompt_for_restart(config):
        restart_cli()


async def _collect_stdio_server_inputs(
    config: ForgeConfig,
) -> tuple[str | None, str | None, str | None, str | None]:
    """Collect user inputs for Stdio server configuration."""
    name = await collect_input(config, "\nEnter server name:")
    if name is None:
        return None, None, None, None

    command = await collect_input(config, "\nEnter command (e.g., 'uvx', 'npx'):")
    if command is None:
        return None, None, None, None

    args_input = await collect_input(
        config, '\nEnter arguments (optional, e.g., "-y server-package arg1"):'
    )
    if args_input is None:
        return None, None, None, None

    env_input = await collect_input(
        config,
        "\nEnter environment variables (KEY=VALUE format, comma-separated, optional):",
    )
    if env_input is None:
        return None, None, None, None

    return name, command, args_input, env_input


def _parse_stdio_args_input(args_input: str) -> list[str]:
    """Parse the arguments user input into a list suitable for MCPStdioServerConfig."""
    if not args_input.strip():
        return []
    try:
        return shlex.split(args_input.strip())
    except ValueError as exc:
        msg = (
            "Invalid argument format. Use shell-style quoting, e.g. "
            "'--flag value' or \"--config 'path with spaces'\"."
        )
        raise ValueError(msg) from exc


def _parse_stdio_env_input(env_input: str) -> dict[str, str]:
    """Parse environment variables input into dictionary form."""
    if not env_input.strip():
        return {}

    environment: dict[str, str] = {}
    for pair in env_input.split(","):
        pair = pair.strip()
        if not pair:
            continue
        if "=" not in pair:
            msg = f"Environment variable '{pair}' must be in KEY=VALUE format."
            raise ValueError(msg)
        key, value = pair.split("=", 1)
        key = key.strip()
        if not key:
            raise ValueError("Environment variable key cannot be empty.")
        if not re.match(r"^[a-zA-Z_][a-zA-Z0-9_]*$", key):
            msg = (
                f"Invalid environment variable name '{key}'. Must start with a letter "
                "or underscore and contain only alphanumeric characters and underscores."
            )
            raise ValueError(msg)
        environment[key] = value
    return environment


def _validate_stdio_server_config(
    name: str, command: str, args: list[str], env: dict[str, str]
) -> MCPStdioServerConfig:
    """Validate and create Stdio server configuration."""
    return MCPStdioServerConfig(
        name=name, command=command, args=args, env=env
    )


def _build_stdio_server_config_dict(server: MCPStdioServerConfig) -> dict[str, Any]:
    """Build configuration dictionary for Stdio server."""
    server_config: dict[str, Any] = {"name": server.name, "command": server.command}
    if server.args:
        server_config["args"] = server.args
    if server.env:
        server_config["env"] = server.env
    return server_config


async def _validate_stdio_server_name(config: ForgeConfig, name: str) -> bool:
    """Validate that server name is unique."""
    existing_names = [server.name for server in config.mcp.stdio_servers]
    if name in existing_names:
        print_formatted_text(f"❌ Server name '{name}' already exists.")
        return False
    return True


async def _validate_stdio_server_inputs(
    config: ForgeConfig,
    name: str,
    command: str,
    args_input: str,
    env_input: str,
) -> MCPStdioServerConfig | None:
    """Validate inputs and create stdio server config."""
    try:
        parsed_args = _parse_stdio_args_input(args_input)
        parsed_env = _parse_stdio_env_input(env_input)
        return _validate_stdio_server_config(name, command, parsed_args, parsed_env)
    except ValueError as parse_error:
        print_formatted_text(f"❌ {parse_error}")
        return None
    except ValidationError as e:
        print_formatted_text("❌ Please fix the following errors:")
        for error in e.errors():
            field = error["loc"][0] if error["loc"] else "unknown"
            print_formatted_text(f"  • {field}: {error['msg']}")
        return None


async def add_stdio_server(config: ForgeConfig) -> None:
    """Add a Stdio MCP server."""
    print_formatted_text("Adding Stdio MCP Server")
    while True:
        gathered = await _gather_stdio_inputs(config)
        if gathered is None:
            _announce_operation_cancelled()
            return
        name, command, args_input, env_input = gathered

        if not await _validate_stdio_server_name(config, name):
            if not _should_retry_after_failure(config):
                _announce_operation_cancelled()
                return
            continue

        server = await _validate_stdio_server_inputs(
            config, name, command, args_input, env_input
        )
        if server is not None:
            await _finalize_stdio_server_addition(config, server)
            return

        if not _should_retry_after_failure(config):
            _announce_operation_cancelled()
            return


async def _gather_stdio_inputs(
    config: ForgeConfig,
) -> tuple[str, str, str, str] | None:
    """Collect stdio inputs and handle cancellation."""
    name, command, args_input, env_input = await _collect_stdio_server_inputs(config)
    if None in (name, command, args_input, env_input):
        return None
    assert isinstance(name, str)
    assert isinstance(command, str)
    assert isinstance(args_input, str)
    assert isinstance(env_input, str)
    return name, command, args_input, env_input


def _announce_operation_cancelled() -> None:
    print_formatted_text("Operation cancelled.")


def _should_retry_after_failure(config: ForgeConfig) -> bool:
    return cli_confirm(config, "\nTry again?") == 0


async def _finalize_stdio_server_addition(
    config: ForgeConfig, server: MCPStdioServerConfig
) -> None:
    server_config = _build_stdio_server_config_dict(server)
    config_file_path = _add_server_to_config("stdio_servers", server_config)
    print_formatted_text(
        f"✓ Stdio MCP server added to {config_file_path}: {server.name}"
    )
    if await prompt_for_restart(config):
        restart_cli()


async def _collect_shttp_server_inputs(
    config: ForgeConfig,
) -> tuple[str | None, str | None]:
    """Collect user inputs for SHTTP server configuration."""
    url = await collect_input(config, "\nEnter server URL:")
    if url is None:
        return None, None

    api_key = await collect_input(
        config, "\nEnter API key (optional, press Enter to skip):"
    )
    return (None, None) if api_key is None else (url, api_key or None)


async def _validate_and_create_shttp_server(
    config: ForgeConfig,
    url: str,
    api_key: str | None,
) -> MCPSHTTPServerConfig | None:
    """Validate inputs and create SHTTP server config."""
    try:
        return MCPSHTTPServerConfig(url=url, api_key=api_key)
    except ValidationError as e:
        print_formatted_text("❌ Please fix the following errors:")
        for error in e.errors():
            field = error["loc"][0] if error["loc"] else "unknown"
            print_formatted_text(f"  • {field}: {error['msg']}")
        return None


def _build_shttp_server_config(server) -> dict:
    """Build SHTTP server configuration dictionary."""
    server_config = {"url": server.url}
    if server.api_key:
        server_config["api_key"] = server.api_key
    return server_config


async def add_shttp_server(config: ForgeConfig) -> None:
    """Add an SHTTP MCP server."""
    print_formatted_text("Adding SHTTP MCP Server")

    while True:
        url, api_key = await _collect_shttp_server_inputs(config)
        if url is None:
            print_formatted_text("Operation cancelled.")
            return

        server = await _validate_and_create_shttp_server(config, url, api_key)
        if server is not None:
            break

        if cli_confirm(config, "\nTry again?") != 0:
            print_formatted_text("Operation cancelled.")
            return

    server_config = _build_shttp_server_config(server)
    config_file_path = _add_server_to_config("shttp_servers", server_config)
    print_formatted_text(
        f"✓ SHTTP MCP server added to {config_file_path}: {server.url}"
    )

    if await prompt_for_restart(config):
        restart_cli()


def _collect_available_servers(mcp_config) -> list[tuple[str, str, object]]:
    """Collect all available MCP servers for removal."""
    servers: list[tuple[str, str, object]] = []
    servers.extend(
        ("SSE", sse_server.url, sse_server) for sse_server in mcp_config.sse_servers
    )
    servers.extend(
        ("Stdio", stdio_server.name, stdio_server)
        for stdio_server in mcp_config.stdio_servers
    )
    servers.extend(
        ("SHTTP", shttp_server.url, shttp_server)
        for shttp_server in mcp_config.shttp_servers
    )
    return servers


def _get_server_removal_choices(servers: list[tuple[str, str, object]]) -> list[str]:
    """Get list of server choices for user selection."""
    choices = [f"{server_type}: {identifier}" for server_type, identifier, _ in servers]
    choices.append("Cancel")
    return choices


def _confirm_server_removal(
    config: ForgeConfig, server_type: str, identifier: str
) -> bool:
    """Confirm server removal with user."""
    confirm = cli_confirm(
        config,
        f'Are you sure you want to remove {server_type} server "{identifier}"?',
        ["Yes, remove", "Cancel"],
    )
    return confirm == 0


def _remove_sse_server(config_data: dict, identifier: str) -> bool:
    """Remove SSE server from configuration."""
    if "sse_servers" not in config_data["mcp"]:
        return False
    config_data["mcp"]["sse_servers"] = [
        s for s in config_data["mcp"]["sse_servers"] if s.get("url") != identifier
    ]
    return True


def _remove_stdio_server(config_data: dict, identifier: str) -> bool:
    """Remove Stdio server from configuration."""
    if "stdio_servers" not in config_data["mcp"]:
        return False
    config_data["mcp"]["stdio_servers"] = [
        s for s in config_data["mcp"]["stdio_servers"] if s.get("name") != identifier
    ]
    return True


def _remove_shttp_server(config_data: dict, identifier: str) -> bool:
    """Remove SHTTP server from configuration."""
    if "shttp_servers" not in config_data["mcp"]:
        return False
    config_data["mcp"]["shttp_servers"] = [
        s for s in config_data["mcp"]["shttp_servers"] if s.get("url") != identifier
    ]
    return True


def _remove_server_from_config(
    config_data: dict, server_type: str, identifier: str
) -> bool:
    """Remove server from configuration data."""
    if server_type == "SSE":
        return _remove_sse_server(config_data, identifier)
    if server_type == "Stdio":
        return _remove_stdio_server(config_data, identifier)
    if server_type == "SHTTP":
        return _remove_shttp_server(config_data, identifier)
    return False


async def remove_mcp_server(config: ForgeConfig) -> None:
    """Remove an MCP server configuration."""
    servers = _collect_available_servers(config.mcp)

    if not servers:
        print_formatted_text("No MCP servers configured to remove.")
        return

    choices = _get_server_removal_choices(servers)
    choice = cli_confirm(config, "Select MCP server to remove:", choices)

    if choice == len(choices) - 1:
        return

    server_type, identifier, _ = servers[choice]

    if not _confirm_server_removal(config, server_type, identifier):
        return

    config_file_path = get_config_file_path()
    config_data = load_config_file(config_file_path)
    _ensure_mcp_config_structure(config_data)

    if _remove_server_from_config(config_data, server_type, identifier):
        save_config_file(config_data, config_file_path)
        print_formatted_text(
            f'✓ {server_type} MCP server "{identifier}" removed from {config_file_path}.'
        )
        if await prompt_for_restart(config):
            restart_cli()
    else:
        print_formatted_text(f'Failed to remove {server_type} server "{identifier}".')
