from __future__ import annotations

import os
import re
import time
import traceback
import uuid
from enum import Enum
from typing import TYPE_CHECKING, Any

import bashlex
import libtmux

from openhands.core.logger import openhands_logger as logger
from openhands.events.observation import ErrorObservation
from openhands.events.observation.commands import (
    CMD_OUTPUT_PS1_END,
    CmdOutputMetadata,
    CmdOutputObservation,
)
from openhands.runtime.utils.bash_constants import TIMEOUT_MESSAGE_TEMPLATE
from openhands.runtime.utils.prompt_detector import detect_interactive_prompt
from openhands.utils.shutdown_listener import should_continue

if TYPE_CHECKING:
    from openhands.events.action import CmdRunAction


def split_bash_commands(commands: str) -> list[str]:
    """Split bash commands string into individual commands.

    Args:
        commands: String containing multiple bash commands.

    Returns:
        list[str]: List of individual bash commands.
    """
    if not commands.strip():
        return [""]
    try:
        parsed = bashlex.parse(commands)
    except (bashlex.errors.ParsingError, NotImplementedError, TypeError, AttributeError):
        logger.debug(
            "Failed to parse bash commands\n[input]: %s\n[warning]: %s\nThe original command will be returned as is.",
            commands,
            traceback.format_exc(),
        )
        return [commands]
    result: list[str] = []
    last_end = 0
    for node in parsed:
        start, end = node.pos
        if start > last_end:
            between = commands[last_end:start]
            logger.debug("BASH PARSING between: %s", between)
            if result:
                result[-1] += between.rstrip()
            elif between.strip():
                result.append(between.rstrip())
        command = commands[start:end].rstrip()
        logger.debug("BASH PARSING command: %s", command)
        result.append(command)
        last_end = end
    remaining = commands[last_end:].rstrip()
    logger.debug("BASH PARSING remaining: %s", remaining)
    if last_end < len(commands):
        if result:
            result[-1] += remaining
            logger.debug("BASH PARSING result[-1] += remaining: %s", result[-1])
        elif remaining:
            result.append(remaining)
            logger.debug("BASH PARSING result.append(remaining): %s", result[-1])
    return result


def escape_bash_special_chars(command: str) -> str:
    r"""Escapes characters that have different interpretations in bash vs python.

    Specifically handles escape sequences like \\;, \\|, \\&, etc.
    """
    if not command.strip():
        return ""
    try:
        parts = []
        last_pos = 0

        def visit_node(node: Any) -> None:
            nonlocal last_pos
            if node.kind == "redirect" and hasattr(node, "heredoc") and (node.heredoc is not None):
                between = command[last_pos: node.pos[0]]
                parts.append(between)
                parts.append(command[node.pos[0]: node.heredoc.pos[0]])
                parts.append(command[node.heredoc.pos[0]: node.heredoc.pos[1]])
                last_pos = node.pos[1]
                return
            if node.kind == "word":
                between = command[last_pos: node.pos[0]]
                word_text = command[node.pos[0]: node.pos[1]]
                between = re.sub("\\\\([;&|><])", "\\\\\\\\\\1", between)
                parts.append(between)
                if (
                    (word_text.startswith('"') and word_text.endswith('"'))
                    or (word_text.startswith("'") and word_text.endswith("'"))
                    or (word_text.startswith("$(") and word_text.endswith(")"))
                    or (word_text.startswith("`") and word_text.endswith("`"))
                ):
                    parts.append(word_text)
                else:
                    word_text = re.sub("\\\\([;&|><])", "\\\\\\\\\\1", word_text)
                    parts.append(word_text)
                last_pos = node.pos[1]
                return
            if hasattr(node, "parts"):
                for part in node.parts:
                    visit_node(part)

        nodes = list(bashlex.parse(command))
        for node in nodes:
            between = command[last_pos: node.pos[0]]
            between = re.sub("\\\\([;&|><])", "\\\\\\\\\\1", between)
            parts.append(between)
            last_pos = node.pos[0]
            visit_node(node)
        remaining = command[last_pos:]
        parts.append(remaining)
        return "".join(parts)
    except (bashlex.errors.ParsingError, NotImplementedError, TypeError):
        logger.debug(
            "Failed to parse bash commands for special characters escape\n[input]: %s\n[warning]: %s\nThe original command will be returned as is.",
            command,
            traceback.format_exc(),
        )
        return command


class BashCommandStatus(Enum):
    CONTINUE = "continue"
    COMPLETED = "completed"
    NO_CHANGE_TIMEOUT = "no_change_timeout"
    HARD_TIMEOUT = "hard_timeout"
    __test__ = False


def _remove_command_prefix(command_output: str, command: str) -> str:
    """Remove command prefix from command output.

    Args:
        command_output: The output string from the command.
        command: The original command that was executed.

    Returns:
        str: The output with the command prefix removed.
    """
    return command_output.lstrip().removeprefix(command.lstrip()).lstrip()


class BashSession:
    POLL_INTERVAL = 0.5
    HISTORY_LIMIT = 10000
    PS1 = CmdOutputMetadata.to_ps1_prompt()

    def __init__(
        self,
        work_dir: str,
        username: str | None = None,
        no_change_timeout_seconds: int = 30,
        max_memory_mb: int | None = None,
    ) -> None:
        self.NO_CHANGE_TIMEOUT_SECONDS = no_change_timeout_seconds
        self.work_dir = work_dir
        self.username = username
        self._initialized = False
        self.max_memory_mb = max_memory_mb

    def initialize(self) -> None:
        self.server = libtmux.Server()
        _shell_command = "/bin/bash"
        if self.username in ["root", "openhands"]:
            _shell_command = f"su {self.username} -"
        window_command = _shell_command
        logger.debug("Initializing bash session with command: %s", window_command)
        session_name = f"openhands-{self.username}-{uuid.uuid4()}"
        self.session = self.server.new_session(
            session_name=session_name,
            start_directory=self.work_dir,
            kill_session=True,
            x=1000,
            y=1000,
        )
        self.session.set_option("history-limit", str(self.HISTORY_LIMIT), _global=True)
        self.session.history_limit = self.HISTORY_LIMIT
        _initial_window = self.session.active_window
        self.window = self.session.new_window(
            window_name="bash",
            window_shell=window_command,
            start_directory=self.work_dir,
        )
        self.pane = self.window.active_pane
        logger.debug("pane: %s; history_limit: %s", self.pane, self.session.history_limit)
        _initial_window.kill()
        self.pane.send_keys(f'''export PROMPT_COMMAND='export PS1="{self.PS1}"'; export PS2=""''')
        time.sleep(0.1)
        self._clear_screen()
        self.prev_status: BashCommandStatus | None = None
        self.prev_output: str = ""
        self._closed: bool = False
        logger.debug("Bash session initialized with work dir: %s", self.work_dir)
        self._cwd = os.path.abspath(self.work_dir)
        self._initialized = True

    def __del__(self) -> None:
        """Ensure the session is closed when the object is destroyed."""
        self.close()

    def _get_pane_content(self) -> str:
        """Capture the current pane content and update the buffer."""
        return "\n".join(line.rstrip() for line in self.pane.cmd("capture-pane", "-J", "-pS", "-").stdout)

    def close(self) -> None:
        """Clean up the session."""
        if self._closed:
            return
        self.session.kill()
        self._closed = True

    @property
    def cwd(self) -> str:
        return self._cwd

    def _is_special_key(self, command: str) -> bool:
        """Check if the command is a special key."""
        _command = command.strip()
        return _command.startswith("C-") and len(_command) == 3

    def _clear_screen(self) -> None:
        """Clear the tmux pane screen and history."""
        self.pane.send_keys("C-l", enter=False)
        time.sleep(0.1)
        self.pane.cmd("clear-history")

    def _get_command_output(
        self,
        command: str,
        raw_command_output: str,
        metadata: CmdOutputMetadata,
        continue_prefix: str = "",
    ) -> str:
        """Get the command output with the previous command output removed.

        Args:
            command: The command that was executed.
            raw_command_output: The raw output from the command.
            metadata: The metadata object to store prefix/suffix in.
            continue_prefix: The prefix to add to the command output if it's a continuation of the previous command.
        """
        if self.prev_output:
            command_output = raw_command_output.removeprefix(self.prev_output)
            metadata.prefix = continue_prefix
        else:
            command_output = raw_command_output
        self.prev_output = raw_command_output
        command_output = _remove_command_prefix(command_output, command)
        return command_output.rstrip()

    def _handle_completed_command(
        self,
        command: str,
        pane_content: str,
        ps1_matches: list[re.Match],
        hidden: bool,
        is_input: bool = False,
    ) -> CmdOutputObservation:
        is_special_key = self._is_special_key(command)
        assert (
            ps1_matches
        ), f"Expected at least one PS1 metadata block, but got {
            len(ps1_matches)}.\n---FULL OUTPUT---\n{
            pane_content!r}\n---END OF OUTPUT---"
        metadata = CmdOutputMetadata.from_ps1_match(ps1_matches[-1])
        get_content_before_last_match = len(ps1_matches) == 1
        if metadata.working_dir != self._cwd and metadata.working_dir:
            self._cwd = metadata.working_dir
        logger.debug("COMMAND OUTPUT: %s", pane_content)
        raw_command_output = self._combine_outputs_between_matches(
            pane_content,
            ps1_matches,
            get_content_before_last_match=get_content_before_last_match,
        )
        if get_content_before_last_match:
            num_lines = len(raw_command_output.splitlines())
            metadata.prefix = (
                f"[Previous command outputs are truncated. Showing the last {num_lines} lines of the output below.]\n"
            )
        metadata.suffix = (
            f"\n[The command completed with exit code {metadata.exit_code}. CTRL+{command[-1].upper()} was sent.]"
            if is_special_key
            else f"\n[The command completed with exit code {metadata.exit_code}.]"
        )
        if is_input and command != "":
            continue_prefix = ""
        else:
            continue_prefix = "[Below is the output of the previous command.]\n" if self.prev_output else ""
        command_output = self._get_command_output(
            command,
            raw_command_output,
            metadata,
            continue_prefix=continue_prefix,
        )
        self.prev_status = BashCommandStatus.COMPLETED
        self.prev_output = ""
        self._ready_for_next_command()
        return CmdOutputObservation(content=command_output, command=command, metadata=metadata, hidden=hidden)

    def _handle_nochange_timeout_command(
        self,
        command: str,
        pane_content: str,
        ps1_matches: list[re.Match],
    ) -> CmdOutputObservation:
        self.prev_status = BashCommandStatus.NO_CHANGE_TIMEOUT
        if len(ps1_matches) != 1:
            logger.warning(
                "Expected exactly one PS1 metadata block BEFORE the execution of a command, but got %s PS1 metadata blocks:\n---\n%s\n---",
                len(ps1_matches),
                pane_content,
            )
        raw_command_output = self._combine_outputs_between_matches(pane_content, ps1_matches)
        metadata = CmdOutputMetadata()
        metadata.suffix = f"\n[The command has no new output after {
            self.NO_CHANGE_TIMEOUT_SECONDS} seconds. {TIMEOUT_MESSAGE_TEMPLATE}]"
        command_output = self._get_command_output(
            command,
            raw_command_output,
            metadata,
            continue_prefix="[Below is the output of the previous command.]\n",
        )
        return CmdOutputObservation(content=command_output, command=command, metadata=metadata)

    def _handle_hard_timeout_command(
        self,
        command: str,
        pane_content: str,
        ps1_matches: list[re.Match],
        timeout: float,
    ) -> CmdOutputObservation:
        self.prev_status = BashCommandStatus.HARD_TIMEOUT
        if len(ps1_matches) != 1:
            logger.warning(
                "Expected exactly one PS1 metadata block BEFORE the execution of a command, but got %s PS1 metadata blocks:\n---\n%s\n---",
                len(ps1_matches),
                pane_content,
            )
        raw_command_output = self._combine_outputs_between_matches(pane_content, ps1_matches)
        metadata = CmdOutputMetadata()
        metadata.suffix = f"\n[The command timed out after {timeout} seconds. {TIMEOUT_MESSAGE_TEMPLATE}]"
        command_output = self._get_command_output(
            command,
            raw_command_output,
            metadata,
            continue_prefix="[Below is the output of the previous command.]\n",
        )
        return CmdOutputObservation(command=command, content=command_output, metadata=metadata)

    def _ready_for_next_command(self) -> None:
        """Reset the content buffer for a new command."""
        self._clear_screen()

    def _combine_outputs_between_matches(
        self,
        pane_content: str,
        ps1_matches: list[re.Match],
        get_content_before_last_match: bool = False,
    ) -> str:
        """Combine all outputs between PS1 matches.

        Args:
            pane_content: The full pane content containing PS1 prompts and command outputs
            ps1_matches: List of regex matches for PS1 prompts
            get_content_before_last_match: when there's only one PS1 match, whether to get
                the content before the last PS1 prompt (True) or after the last PS1 prompt (False)

        Returns:
            Combined string of all outputs between matches
        """
        if len(ps1_matches) == 1:
            if get_content_before_last_match:
                return pane_content[: ps1_matches[0].start()]
            return pane_content[ps1_matches[0].end() + 1:]
        if not ps1_matches:
            return pane_content
        combined_output = ""
        for i in range(len(ps1_matches) - 1):
            output_segment = pane_content[ps1_matches[i].end() + 1: ps1_matches[i + 1].start()]
            combined_output += output_segment + "\n"
        combined_output += pane_content[ps1_matches[-1].end() + 1:]
        logger.debug("COMBINED OUTPUT: %s", combined_output)
        return combined_output

    def _validate_session_and_command(self, action: CmdRunAction) -> None:
        """Validate session is initialized and command is valid."""
        if not self._initialized:
            msg = "Bash session is not initialized"
            raise RuntimeError(msg)

        logger.debug("RECEIVED ACTION: %s", action)

        command = action.command.strip()
        if self.prev_status not in {
            BashCommandStatus.CONTINUE,
            BashCommandStatus.NO_CHANGE_TIMEOUT,
            BashCommandStatus.HARD_TIMEOUT,
        }:
            if command == "":
                msg = "ERROR: No previous running command to retrieve logs from."
                raise ValueError(msg)
            is_input: bool = action.is_input

            if is_input:
                msg = "ERROR: No previous running command to interact with."
                raise ValueError(msg)

        splited_commands = split_bash_commands(command)
        if len(splited_commands) > 1:
            msg = f"ERROR: Cannot execute multiple commands at once.\nPlease run each command separately OR chain them into a single command via && or ;\nProvided commands:\n{'\n'.join((f'({i + 1}) {cmd}' for i, cmd in enumerate(
                splited_commands)))}"
            raise ValueError(
                msg,
            )

    def _handle_previous_command_timeout(
        self,
        command: str,
        last_pane_output: str,
        initial_ps1_matches: list,
        is_input: bool,
    ) -> CmdOutputObservation | None:
        """Handle case where previous command timed out."""
        if (
            self.prev_status in {BashCommandStatus.HARD_TIMEOUT, BashCommandStatus.NO_CHANGE_TIMEOUT}
            and not last_pane_output.rstrip().endswith(CMD_OUTPUT_PS1_END.rstrip())
            and not is_input
            and command != ""
        ):

            _ps1_matches = CmdOutputMetadata.matches_ps1_metadata(last_pane_output)
            current_matches_for_output = _ps1_matches or initial_ps1_matches
            raw_command_output = self._combine_outputs_between_matches(last_pane_output, current_matches_for_output)
            metadata = CmdOutputMetadata()
            metadata.suffix = f'\n[Your command "{command}" is NOT executed. The previous command is still running - You CANNOT send new commands until the previous command is completed. By setting `is_input` to `true`, you can interact with the current process: {TIMEOUT_MESSAGE_TEMPLATE}]'
            logger.debug("PREVIOUS COMMAND OUTPUT: %s", raw_command_output)
            command_output = self._get_command_output(
                command,
                raw_command_output,
                metadata,
                continue_prefix="[Below is the output of the previous command.]\n",
            )
            return CmdOutputObservation(
                command=command,
                content=command_output,
                metadata=metadata,
                hidden=False,
            )
        return None

    def _send_command_to_pane(self, command: str, is_input: bool) -> None:
        """Send command or input to the pane."""
        if is_input:
            is_special_key = self._is_special_key(command)
            logger.debug("SENDING INPUT TO RUNNING PROCESS: %s", command)
            self.pane.send_keys(command, enter=not is_special_key)
        elif command != "":
            is_special_key = self._is_special_key(command)
            command = escape_bash_special_chars(command)
            logger.debug("SENDING COMMAND: %s", command)
            self.pane.send_keys(command, enter=not is_special_key)

    def _check_command_completion(
        self,
        cur_pane_output: str,
        ps1_matches: list,
        initial_ps1_count: int,
        command: str,
        is_input: bool,
    ) -> CmdOutputObservation | None:
        """Check if command has completed and return observation if so."""
        current_ps1_count = len(ps1_matches)
        if current_ps1_count > initial_ps1_count or cur_pane_output.rstrip().endswith(CMD_OUTPUT_PS1_END.rstrip()):
            return self._handle_completed_command(
                command,
                pane_content=cur_pane_output,
                ps1_matches=ps1_matches,
                hidden=False,
                is_input=is_input,
            )
        return None

    def _check_timeouts(
        self,
        action: CmdRunAction,
        last_change_time: float,
        start_time: float,
        command: str,
        cur_pane_output: str,
        ps1_matches: list,
    ) -> CmdOutputObservation | None:
        """Check for various timeout conditions."""
        time_since_last_change = time.time() - last_change_time
        logger.debug(
            "CHECKING NO CHANGE TIMEOUT (%ss): elapsed %s. Action blocking: %s",
            self.NO_CHANGE_TIMEOUT_SECONDS,
            time_since_last_change,
            action.blocking,
        )

        if not action.blocking and time_since_last_change >= self.NO_CHANGE_TIMEOUT_SECONDS:
            return self._handle_nochange_timeout_command(command, pane_content=cur_pane_output, ps1_matches=ps1_matches)

        # Skip hard timeout check if timeout is None (long-running commands like servers)
        if action.timeout is None:
            logger.debug("No hard timeout set (long-running command), skipping timeout check")
            return None

        elapsed_time = time.time() - start_time
        logger.debug("CHECKING HARD TIMEOUT (%ss): elapsed %s", action.timeout, elapsed_time)

        if action.timeout and elapsed_time >= action.timeout:
            logger.debug("Hard timeout triggered.")
            return self._handle_hard_timeout_command(
                command,
                pane_content=cur_pane_output,
                ps1_matches=ps1_matches,
                timeout=action.timeout,
            )

        return None

    def _monitor_command_execution(
        self,
        command: str,
        initial_ps1_count: int,
        is_input: bool,
        action: CmdRunAction,
    ) -> CmdOutputObservation:
        """Monitor command execution until completion or timeout."""
        start_time = time.time()
        last_change_time = start_time
        last_pane_output = self._get_pane_content()

        while should_continue():
            _start_time = time.time()
            logger.debug("GETTING PANE CONTENT at %s", _start_time)
            cur_pane_output = self._get_pane_content()
            logger.debug("PANE CONTENT GOT after %s seconds", time.time() - _start_time)
            logger.debug("BEGIN OF PANE CONTENT: %s", cur_pane_output.split("\n")[:10])
            logger.debug("END OF PANE CONTENT: %s", cur_pane_output.split("\n")[-10:])

            ps1_matches = CmdOutputMetadata.matches_ps1_metadata(cur_pane_output)

            if cur_pane_output != last_pane_output:
                last_pane_output = cur_pane_output
                last_change_time = time.time()
                logger.debug("CONTENT UPDATED DETECTED at %s", last_change_time)

                # Check for interactive prompts and auto-respond
                is_prompt, response = detect_interactive_prompt(cur_pane_output)
                if is_prompt and response:
                    logger.info(f"🤖 Auto-responding to interactive prompt with: {response!r}")
                    self._send_command_to_pane(response, is_input=True)
                    # Reset last_change_time to avoid timeout during prompt handling
                    last_change_time = time.time()
                    # Give the system time to process the input
                    time.sleep(0.2)
                    continue

                # Check for server startup (hybrid detection: pattern + port + health check)
                from openhands.runtime.utils.server_detector import (
                    detect_server_from_output,
                )

                detected_server = detect_server_from_output(cur_pane_output, perform_health_check=True)
                if detected_server and not hasattr(self, "_last_detected_server_url"):
                    logger.info(f"🚀 Server detected: {detected_server.url} (health: {detected_server.health_status})")
                    # Store for runtime to emit ServerReadyObservation - only detect each server once
                    self._last_detected_server = detected_server
                    self._last_detected_server_url = detected_server.url

            if completion_result := self._check_command_completion(
                cur_pane_output,
                ps1_matches,
                initial_ps1_count,
                command,
                is_input,
            ):
                return completion_result

            if timeout_result := self._check_timeouts(
                action,
                last_change_time,
                start_time,
                command,
                cur_pane_output,
                ps1_matches,
            ):
                return timeout_result

            logger.debug("SLEEPING for %s seconds for next poll", self.POLL_INTERVAL)
            time.sleep(self.POLL_INTERVAL)

        msg = "Bash session was likely interrupted..."
        raise RuntimeError(msg)

    def execute(self, action: CmdRunAction) -> CmdOutputObservation | ErrorObservation:
        """Execute a command in the bash session."""
        try:
            # Validate session and command
            self._validate_session_and_command(action)
        except ValueError as e:
            if "No previous running command" in str(e):
                return CmdOutputObservation(content=str(e), command="", metadata=CmdOutputMetadata())
            return ErrorObservation(content=str(e))

        command = action.command.strip()
        is_input: bool = action.is_input

        # Get initial state
        initial_pane_output = self._get_pane_content()
        initial_ps1_matches = CmdOutputMetadata.matches_ps1_metadata(initial_pane_output)
        initial_ps1_count = len(initial_ps1_matches)
        logger.debug("Initial PS1 count: %s", initial_ps1_count)

        if timeout_result := self._handle_previous_command_timeout(
            command,
            initial_pane_output,
            initial_ps1_matches,
            is_input,
        ):
            return timeout_result

        # Send command to pane
        self._send_command_to_pane(command, is_input)

        # Monitor execution
        return self._monitor_command_execution(command, initial_ps1_count, is_input, action)

    def get_detected_server(self):
        """Get and clear the last detected server.

        Returns:
            DetectedServer if one was detected since last check, None otherwise
        """
        if hasattr(self, "_last_detected_server"):
            server = self._last_detected_server
            # Clear for next detection
            del self._last_detected_server
            del self._last_detected_server_url
            return server
        return None
