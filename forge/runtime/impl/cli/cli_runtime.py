"""This runtime runs commands locally using subprocess and performs file operations using Python's standard library.

It does not implement browser functionality.
"""

from __future__ import annotations

import asyncio
import os
import select
import shutil
import signal
import subprocess
import sys
import tempfile
import time
import zipfile
from pathlib import Path
from typing import TYPE_CHECKING, Any, Callable

from binaryornot.check import is_binary
try:
    from forge_aci.editor.editor import OHEditor
    from forge_aci.editor.exceptions import ToolError
    from forge_aci.editor.results import ToolResult
    from forge_aci.utils.diff import get_diff
except ImportError:
    # Stubs for when forge_aci is not installed
    class ToolError(Exception):
        """Stub ToolError for testing."""

        def __init__(self, message: str = "") -> None:
            """Store an optional message for the simulated editor error."""
            super().__init__(message)
            self.message = message

    class ToolResult:
        """Stub ToolResult for testing."""

        def __init__(
            self,
            *,
            output: str | None = None,
            error: str | None = None,
            old_content: str | None = None,
            new_content: str | None = None,
        ) -> None:
            """Capture simulated output/error values for testing without forge_aci."""
            self.output = output or ""
            self.error = error
            self.old_content = old_content
            self.new_content = new_content

    class OHEditor:
        """Stub OHEditor for testing when forge_aci is unavailable."""

        def __init__(self, workspace_root: str | None = None, *args, **kwargs) -> None:
            """Remember the workspace root for basic file operations in tests."""
            self.workspace_root = workspace_root

        def __call__(
            self,
            *,
            command: str,
            path: str,
            file_text: str | None = None,
            view_range: list[int] | None = None,
            old_str: str | None = None,
            new_str: str | None = None,
            insert_line: int | None = None,
            enable_linting: bool = False,
            **_: Any,
        ) -> ToolResult:
            """Execute a minimal editing command against the local filesystem stub."""
            try:
                if command == "view":
                    if not os.path.exists(path) or os.path.isdir(path):
                        return ToolResult(output="", old_content=None, new_content=None)
                    with open(path, encoding="utf-8", errors="replace") as handle:
                        content = handle.read()
                    if view_range:
                        start, end = view_range
                        lines = content.splitlines(True)
                        selected = "".join(lines[max(start - 1, 0): end])
                    else:
                        selected = content
                    return ToolResult(output=selected, old_content=content, new_content=content)
                if command in {"edit", "apply_edit"}:
                    previous = ""
                    if os.path.exists(path):
                        with open(path, encoding="utf-8", errors="replace") as handle:
                            previous = handle.read()
                    updated = new_str if new_str is not None else file_text or previous
                    directory = os.path.dirname(path)
                    if directory:
                        os.makedirs(directory, exist_ok=True)
                    with open(path, "w", encoding="utf-8") as handle:
                        handle.write(updated)
                    return ToolResult(output="File updated", old_content=previous, new_content=updated)
                if command == "write":
                    content = file_text or new_str or ""
                    directory = os.path.dirname(path)
                    if directory:
                        os.makedirs(directory, exist_ok=True)
                    with open(path, "w", encoding="utf-8") as handle:
                        handle.write(content)
                    return ToolResult(output="File written", old_content=None, new_content=content)
            except Exception as exc:  # pragma: no cover - safeguard for stub
                return ToolResult(error=str(exc))
            return ToolResult(output="", old_content=None, new_content=None)

    def get_diff(
        old: str | None = None,
        new: str | None = None,
        *,
        old_contents: str = "",
        new_contents: str = "",
        **__: Any,
    ) -> str:
        """Stub diff function when forge_aci is unavailable."""
        previous = old if old is not None else old_contents
        updated = new if new is not None else new_contents
        return "\n".join(
            [
                "--- old",
                "+++ new",
                "@@ -1 +1 @@",
                f"-{previous}",
                f"+{updated}",
            ]
        )
from pydantic import SecretStr

from forge.core.config.mcp_config import MCPConfig, MCPStdioServerConfig
from forge.core.logger import forge_logger as logger
from forge.events.event import FileEditSource, FileReadSource
from forge.events.observation import (
    CmdOutputObservation,
    ErrorObservation,
    FileEditObservation,
    FileReadObservation,
    FileWriteObservation,
    Observation,
)
from forge.runtime.base import Runtime
from forge.runtime.runtime_status import RuntimeStatus
from forge.mcp import utils as mcp_utils

if TYPE_CHECKING:
    from forge.core.config import ForgeConfig
    from forge.events import EventStream
    from forge.events.action import (
        BrowseInteractiveAction,
        BrowseURLAction,
        CmdRunAction,
        FileEditAction,
        FileReadAction,
        FileWriteAction,
        IPythonRunCellAction,
    )
    from forge.events.action.mcp import MCPAction
    from forge.integrations.provider import PROVIDER_TOKEN_TYPE
    from forge.llm.llm_registry import LLMRegistry
    from forge.runtime.plugins import PluginRequirement

# Windows PowerShell session - only available on Windows
# Note: Import is deferred to avoid executing windows_bash.py on non-Windows platforms
WindowsPowershellSession = None

# Import Windows-specific exception for proper error handling
if sys.platform == "win32":
    try:
        from forge.runtime.utils.windows_exceptions import DotNetMissingError
    except ImportError:
        # Fallback if windows_exceptions module is not available
        class DotNetMissingError(Exception):
            """Raised when required .NET runtime dependencies for PowerShell are missing."""

            def __init__(self, message: str, details: str | None = None):
                """Capture message and optional details for missing .NET runtime issues."""
                self.message = message
                self.details = details
                super().__init__(message)
else:
    # Stub for non-Windows platforms
    class DotNetMissingError(Exception):
        """Stub error used on non-Windows platforms when .NET dependency checks occur."""

        def __init__(self, message: str, details: str | None = None):
            """Store provided message and optional extra details."""
            self.message = message
            self.details = details
            super().__init__(message)


class CLIRuntime(Runtime):
    """A runtime implementation that runs commands locally using subprocess and performs.

    file operations using Python's standard library. It does not implement browser functionality.

    Args:
        config (ForgeConfig): The application configuration.
        event_stream (EventStream): The event stream to subscribe to.
        sid (str, optional): The session ID. Defaults to 'default'.
        plugins (list[PluginRequirement] | None, optional): List of plugin requirements. Defaults to None.
        env_vars (dict[str, str] | None, optional): Environment variables to set. Defaults to None.
        status_callback (Callable | None, optional): Callback for status updates. Defaults to None.
        attach_to_existing (bool, optional): Whether to attach to an existing session. Defaults to False.
        headless_mode (bool, optional): Whether to run in headless mode. Defaults to False.
        user_id (str | None, optional): User ID for authentication. Defaults to None.
        git_provider_tokens (PROVIDER_TOKEN_TYPE | None, optional): Git provider tokens. Defaults to None.

    """

    def __init__(
        self,
        config: ForgeConfig,
        event_stream: EventStream,
        llm_registry: LLMRegistry,
        sid: str = "default",
        plugins: list[PluginRequirement] | None = None,
        env_vars: dict[str, str] | None = None,
        status_callback: Callable[[str, RuntimeStatus, str], None] | None = None,
        attach_to_existing: bool = False,
        headless_mode: bool = False,
        user_id: str | None = None,
        git_provider_tokens: PROVIDER_TOKEN_TYPE | None = None,
    ) -> None:
        """Initialize CLI runtime with local tooling, subscriptions, and env vars."""
        super().__init__(
            config,
            event_stream,
            llm_registry,
            sid,
            plugins,
            env_vars,
            status_callback,
            attach_to_existing,
            headless_mode,
            user_id,
            git_provider_tokens,
        )
        if self.config.workspace_base is not None:
            logger.warning(
                "Workspace base path is set to %s. It will be used as the path for the agent to run in. Be careful, the agent can EDIT files in this directory!",
                self.config.workspace_base,
            )
            self._workspace_path = self.config.workspace_base
        else:
            self._workspace_path = tempfile.mkdtemp(prefix=f"FORGE_workspace_{sid}_")
            logger.info("Created temporary workspace at %s", self._workspace_path)
        self.config.workspace_mount_path_in_sandbox = self._workspace_path
        self._runtime_initialized = False
        self.file_editor = OHEditor(workspace_root=self._workspace_path)
        self._shell_stream_callback: Callable[[str], None] | None = None
        self._is_windows = sys.platform == "win32"
        self._powershell_session = None
        logger.warning(
            "Initializing CLIRuntime. WARNING: NO SANDBOX IS USED. This runtime executes commands directly on the local system. Use with caution in untrusted environments.",
        )

    async def connect(self) -> None:
        """Initialize the runtime connection."""
        try:
            self.set_runtime_status(RuntimeStatus.STARTING_RUNTIME)
            logger.info("Starting CLI runtime initialization...")
            
            os.makedirs(self._workspace_path, exist_ok=True)
            os.chdir(self._workspace_path)
            
            if self._is_windows:
                try:
                    from forge.runtime.utils.windows_bash import WindowsPowershellSession
                    self._powershell_session = WindowsPowershellSession(
                        work_dir=self._workspace_path,
                        username=None,
                        no_change_timeout_seconds=30,
                        max_memory_mb=None,
                    )
                    logger.info("Windows PowerShell session support loaded successfully")
                except (ImportError, DotNetMissingError) as err:
                    friendly_message = "WARNING: PowerShell and .NET SDK are not properly configured. Some CLI features may not work.\nThe .NET SDK and PowerShell are required for full Forge CLI functionality on Windows.\nPlease install the .NET SDK following: https://docs.all-hands.dev/usage/windows-without-wsl"
                    logger.warning("Windows runtime initialization failed: %s: %s", type(err).__name__, str(err))
                    logger.warning(friendly_message)
                    if isinstance(err, DotNetMissingError) and hasattr(err, "details") and err.details:
                        logger.debug("Details: %s", err.details)
                    self._powershell_session = None
                except Exception as e:
                    logger.warning("Failed to initialize PowerShell session: %s", e)
                    self._powershell_session = None
            
            if not self.attach_to_existing:
                # Add timeout to prevent hanging on setup_initial_env
                try:
                    await asyncio.wait_for(
                        asyncio.to_thread(self.setup_initial_env),
                        timeout=60.0  # 60 second timeout for setup
                    )
                except asyncio.TimeoutError:
                    logger.error("CLI runtime setup_initial_env timed out after 60 seconds")
                    self.set_runtime_status(RuntimeStatus.ERROR)
                    raise RuntimeError("CLI runtime initialization timed out")
            
            self._runtime_initialized = True
            self.set_runtime_status(RuntimeStatus.RUNTIME_STARTED)
            logger.info("CLIRuntime initialized with workspace at %s", self._workspace_path)
            
        except Exception as e:
            logger.error("Failed to initialize CLI runtime: %s", e)
            # Set status to ERROR to prevent getting stuck in STARTING_RUNTIME
            self.set_runtime_status(RuntimeStatus.ERROR)
            # Re-raise the exception to let the caller handle it appropriately
            raise

    def add_env_vars(self, env_vars: dict[str, Any]) -> None:
        """Adds environment variables to the current runtime environment.

        For CLIRuntime, this means updating os.environ for the current process,
        so that subsequent commands inherit these variables.
        This overrides the BaseRuntime behavior which tries to run shell commands
        before it's initialized and modify .bashrc, which is not ideal for local CLI.
        """
        if not env_vars:
            return
        logger.info("[CLIRuntime] Setting environment variables for this session: %s", list(env_vars.keys()))
        for key, value in env_vars.items():
            if isinstance(value, SecretStr):
                os.environ[key] = value.get_secret_value()
                logger.warning('[CLIRuntime] Set os.environ["%s"] (from SecretStr)', key)
            else:
                os.environ[key] = value
                logger.debug('[CLIRuntime] Set os.environ["%s"]', key)

    def _safe_terminate_process(self, process_obj, signal_to_send=signal.SIGTERM) -> None:
        """Safely attempts to terminate/kill a process group or a single process.

        Args:
            process_obj: the subprocess.Popen object started with start_new_session=True
            signal_to_send: the signal to send to the process group or process

        """
        pid = getattr(process_obj, "pid", None)
        if pid is None:
            return

        try:
            self._try_kill_process_group(pid, signal_to_send)
        except ProcessLookupError as e:
            self._fallback_kill_process(process_obj, signal_to_send, pid, e)
        except (AttributeError, OSError) as e:
            self._fallback_kill_process(process_obj, signal_to_send, pid, e)
        except (KeyboardInterrupt, SystemExit):
            raise
        except Exception as e:
            logger.error("Error: %s", e)

    def _try_kill_process_group(self, pid: int, signal_to_send) -> None:
        """Try to kill process group.

        Args:
            pid: Process ID
            signal_to_send: Signal to send

        Raises:
            ProcessLookupError: If process not found
            OSError: On OS-level errors

        """
        group_desc = "kill process group" if signal_to_send == signal.SIGKILL else "terminate process group"

        logger.debug("[_safe_terminate_process] Original PID to act on: %s", pid)
        pgid_to_kill = os.getpgid(pid)
        logger.debug(
            "[_safe_terminate_process] Attempting to %s for PID %s (PGID: %s) with %s.",
            group_desc,
            pid,
            pgid_to_kill,
            signal_to_send,
        )
        os.killpg(pgid_to_kill, signal_to_send)
        logger.debug(
            "[_safe_terminate_process] Successfully sent signal %s to PGID %s (original PID: %s).",
            signal_to_send,
            pgid_to_kill,
            pid,
        )

    def _fallback_kill_process(self, process_obj, signal_to_send, pid: int, original_error: Exception) -> None:
        """Fallback to direct process termination.

        Args:
            process_obj: Process object
            signal_to_send: Signal to send
            pid: Process ID
            original_error: Original exception that triggered fallback

        """
        process_desc = "kill process" if signal_to_send == signal.SIGKILL else "terminate process"

        logger.warning(
            "[_safe_terminate_process] Error with PGID for PID %s: %s. Falling back to direct kill/terminate.",
            pid,
            original_error,
        )

        try:
            if signal_to_send == signal.SIGKILL:
                process_obj.kill()
            else:
                process_obj.terminate()
            logger.debug("[_safe_terminate_process] Fallback: Terminated %s (PID: %s).", process_desc, pid)
        except Exception as e_fallback:
            logger.error(
                "[_safe_terminate_process] Fallback: Error during %s (PID: %s): %s", process_desc, pid, e_fallback,
            )

    def _execute_powershell_command(self, command: str, timeout: float) -> CmdOutputObservation | ErrorObservation:
        """Execute a command using PowerShell session on Windows.

        Args:
            command: The command to execute
            timeout: Timeout in seconds for the command
        Returns:
            CmdOutputObservation containing the complete output and exit code

        """
        if self._powershell_session is None:
            return ErrorObservation(content="PowerShell session is not available.", error_id="POWERSHELL_SESSION_ERROR")
        try:
            from forge.events.action import CmdRunAction

            ps_action = CmdRunAction(command=command)
            ps_action.set_hard_timeout(timeout)
            return self._powershell_session.execute(ps_action)
        except Exception as e:
            logger.error('Error executing PowerShell command "%s": %s', command, e)
            return ErrorObservation(
                content=f'Error executing PowerShell command "{command}": {
                    e!s}',
                error_id="POWERSHELL_EXECUTION_ERROR",
            )

    def _execute_shell_command(self, command: str, timeout: float) -> CmdOutputObservation:
        """Execute a shell command and stream its output to a callback function.

        Args:
            command: The shell command to execute
            timeout: Timeout in seconds for the command
        Returns:
            CmdOutputObservation containing the complete output and exit code

        """
        # Initialize execution state
        execution_state = self._initialize_execution_state(command, timeout)

        # Start the process
        process = self._start_shell_process(command)

        try:
            # Execute the command with timeout handling
            self._execute_with_timeout_handling(process, execution_state, timeout)

            # Read remaining output
            self._read_remaining_output(process, execution_state)

            # Determine exit code
            execution_state["exit_code"] = -1 if execution_state["timed_out"] else process.returncode

        except Exception as e:
            return self._handle_execution_error(process, execution_state, e)

        # Create and return observation
        return self._create_output_observation(execution_state)

    def _initialize_execution_state(self, command: str, timeout: float) -> dict:
        """Initialize the execution state for command processing."""
        return {
            "command": command,
            "timeout": timeout,
            "output_lines": [],
            "timed_out": False,
            "start_time": time.monotonic(),
            "exit_code": None,
            "workspace_path": self._workspace_path,
        }

    def _start_shell_process(self, command: str) -> subprocess.Popen:
        """Start the shell process for command execution."""
        process = subprocess.Popen(
            ["bash", "-c", command],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1,
            universal_newlines=True,
            start_new_session=True,
        )
        logger.debug('[_execute_shell_command] PID of bash -c: %s for command: "%s"', process.pid, command)
        return process

    def _execute_with_timeout_handling(self, process: subprocess.Popen, execution_state: dict, timeout: float) -> None:
        """Execute the command with timeout handling."""
        if not process.stdout:
            return

        while process.poll() is None and not self._check_timeout(process, execution_state, timeout):
            self._read_available_output(process, execution_state)

    def _check_timeout(self, process: subprocess.Popen, execution_state: dict, timeout: float) -> bool:
        """Check if the command has timed out."""
        if timeout is not None and time.monotonic() - execution_state["start_time"] > timeout:
            logger.debug('Command "%s" timed out after %s seconds. Terminating.', execution_state["command"], timeout)
            self._safe_terminate_process(process, signal_to_send=signal.SIGTERM)
            execution_state["timed_out"] = True
            return True
        return False

    def _read_available_output(self, process: subprocess.Popen, execution_state: dict) -> None:
        """Read available output from the process."""
        ready_to_read, _, _ = select.select([process.stdout], [], [], 0.1)
        if ready_to_read and (line := process.stdout.readline()):
            execution_state["output_lines"].append(line)
            self._handle_stream_callback(line)

    def _handle_stream_callback(self, line: str) -> None:
        """Handle the stream callback if available."""
        if self._shell_stream_callback:
            self._shell_stream_callback(line)

    def _read_remaining_output(self, process: subprocess.Popen, execution_state: dict) -> None:
        """Read any remaining output from the process."""
        if process.stdout and not process.stdout.closed:
            try:
                while True:
                    line = process.stdout.readline()
                    if not line:
                        break
                    execution_state["output_lines"].append(line)
                    self._handle_stream_callback(line)
            except Exception as e:
                logger.warning(
                    'Error reading directly from stdout after loop for "%s": %s',
                    execution_state["command"],
                    e,
                )

    def _handle_execution_error(
        self,
        process: subprocess.Popen,
        execution_state: dict,
        e: Exception,
    ) -> CmdOutputObservation:
        """Handle execution errors."""
        logger.error('Outer exception in _execute_shell_command for "%s": %s', execution_state["command"], e)

        if process and process.poll() is None:
            self._safe_terminate_process(process, signal_to_send=signal.SIGKILL)

        error_content = "".join(execution_state["output_lines"]) + f"\nError during execution: {e}"
        return CmdOutputObservation(command=execution_state["command"], content=error_content, exit_code=-1)

    def _create_output_observation(self, execution_state: dict) -> CmdOutputObservation:
        """Create the final output observation."""
        complete_output = "".join(execution_state["output_lines"])
        logger.debug(
            '[_execute_shell_command] Complete output for "%s" (len: %s): %s',
            execution_state["command"],
            len(complete_output),
            complete_output,
        )

        obs_metadata = {"working_dir": execution_state["workspace_path"]}
        if execution_state["timed_out"]:
            obs_metadata["suffix"] = f'[The command timed out after {execution_state["timeout"]:.1f} seconds.]'

        return CmdOutputObservation(
            command=execution_state["command"],
            content=complete_output,
            exit_code=execution_state["exit_code"],
            metadata=obs_metadata,
        )

    def run(self, action: CmdRunAction) -> Observation:
        """Run a command using subprocess."""
        if not self._runtime_initialized:
            return ErrorObservation(f"Runtime not initialized for command: {action.command}")
        if action.is_input:
            logger.warning(
                "CLIRuntime received an action with `is_input=True` (command: '%s'). CLIRuntime currently does not support sending input or signals to active processes. This action will be ignored and an error observation will be returned.",
                action.command,
            )
            return ErrorObservation(
                content=f"CLIRuntime does not support interactive input from the agent (e.g., 'C-c'). The command '{
                    action.command}' was not sent to any process.",
                error_id="AGENT_ERROR$BAD_ACTION",
            )
        try:
            effective_timeout = action.timeout if action.timeout is not None else self.config.sandbox.timeout
            logger.debug(
                'Running command in CLIRuntime: "%s" with effective timeout: %ss',
                action.command,
                effective_timeout,
            )
            if self._is_windows and self._powershell_session is not None:
                return self._execute_powershell_command(action.command, timeout=effective_timeout)
            return self._execute_shell_command(action.command, timeout=effective_timeout)
        except Exception as e:
            logger.error('Error in CLIRuntime.run for command "%s": %s', action.command, str(e))
            return ErrorObservation(f'Error running command "{action.command}": {e!s}')

    def run_ipython(self, action: IPythonRunCellAction) -> Observation:
        """Run a Python code cell.

        This functionality is not implemented in CLIRuntime.
        Users should also disable the Jupyter plugin in AgentConfig.
        """
        logger.warning(
            "run_ipython is called on CLIRuntime, but it's not implemented. Please disable the Jupyter plugin in AgentConfig.", )
        return ErrorObservation("Executing IPython cells is not implemented in CLIRuntime. ")

    def _sanitize_filename(self, filename: str) -> str:
        if filename == "/workspace":
            actual_filename = self._workspace_path
        elif filename.startswith("/workspace/"):
            actual_filename = os.path.join(self._workspace_path, filename[len("/workspace/"):])
        elif filename.startswith("/"):
            if not filename.startswith(self._workspace_path):
                msg = f"Invalid path: {filename}. You can only work with files in {
                    self._workspace_path}."
                raise PermissionError(
                    msg,
                )
            actual_filename = filename
        else:
            actual_filename = os.path.join(self._workspace_path, filename.lstrip("/"))
        resolved_path = os.path.realpath(actual_filename)
        if not resolved_path.startswith(self._workspace_path):
            msg = f"Invalid path traversal: {filename}. Path resolves outside the workspace. Resolved: {resolved_path}, Workspace: {
                self._workspace_path}"
            raise PermissionError(
                msg,
            )
        return resolved_path

    def read(self, action: FileReadAction) -> Observation:
        """Read a file using Python's standard library or OHEditor."""
        if not self._runtime_initialized:
            return ErrorObservation("Runtime not initialized")
        file_path = self._sanitize_filename(action.path)
        if action.impl_source == FileReadSource.OH_ACI:
            result_str, _ = self._execute_file_editor(command="view", path=file_path, view_range=action.view_range)
            return FileReadObservation(content=result_str, path=action.path, impl_source=FileReadSource.OH_ACI)
        try:
            if not os.path.exists(file_path):
                return ErrorObservation(f"File not found: {action.path}")
            if os.path.isdir(file_path):
                return ErrorObservation(f"Cannot read directory: {action.path}")
            if is_binary(file_path):
                return ErrorObservation("ERROR_BINARY_FILE")
            with open(file_path, encoding="utf-8", errors="replace") as f:
                content = f.read()
            return FileReadObservation(content=content, path=action.path)
        except Exception as e:
            logger.error("Error reading file: %s", str(e))
            return ErrorObservation(f"Error reading file {action.path}: {e!s}")

    def write(self, action: FileWriteAction) -> Observation:
        """Write to a file using Python's standard library."""
        if not self._runtime_initialized:
            return ErrorObservation("Runtime not initialized")
        file_path = self._sanitize_filename(action.path)
        try:
            os.makedirs(os.path.dirname(file_path), exist_ok=True)
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(action.content)
            return FileWriteObservation(content="", path=action.path)
        except Exception as e:
            logger.error("Error writing to file: %s", str(e))
            return ErrorObservation(f"Error writing to file {action.path}: {e!s}")

    def browse(self, action: BrowseURLAction) -> Observation:
        """Not implemented for CLI runtime."""
        return ErrorObservation("Browser functionality is not implemented in CLIRuntime")

    def browse_interactive(self, action: BrowseInteractiveAction) -> Observation:
        """Not implemented for CLI runtime."""
        return ErrorObservation("Browser functionality is not implemented in CLIRuntime")

    def _execute_file_editor(
        self,
        command: str,
        path: str,
        file_text: str | None = None,
        view_range: list[int] | None = None,
        old_str: str | None = None,
        new_str: str | None = None,
        insert_line: int | None = None,
        enable_linting: bool = False,
    ) -> tuple[str, tuple[str | None, str | None]]:
        """Execute file editor command and handle exceptions.

        Args:
            command: Editor command to execute
            path: File path
            file_text: Optional file text content
            view_range: Optional view range tuple (start, end)
            old_str: Optional string to replace
            new_str: Optional replacement string
            insert_line: Optional line number for insertion
            enable_linting: Whether to enable linting

        Returns:
            tuple: A tuple containing the output string and a tuple of old and new file content

        """
        result: ToolResult | None = None
        try:
            result = self.file_editor(
                command=command,
                path=path,
                file_text=file_text,
                view_range=view_range,
                old_str=old_str,
                new_str=new_str,
                insert_line=insert_line,
                enable_linting=enable_linting,
            )
        except ToolError as e:
            result = ToolResult(error=e.message)
        if result.error:
            return (f"ERROR:\n{result.error}", (None, None))
        if not result.output:
            logger.warning("No output from file_editor for %s", path)
            return ("", (None, None))
        return (result.output, (result.old_content, result.new_content))

    def edit(self, action: FileEditAction) -> Observation:
        """Edit a file using the OHEditor."""
        if not self._runtime_initialized:
            return ErrorObservation("Runtime not initialized")
        file_path = self._sanitize_filename(action.path)
        if os.path.exists(file_path) and is_binary(file_path):
            return ErrorObservation("ERROR_BINARY_FILE")
        assert action.impl_source == FileEditSource.OH_ACI
        result_str, (old_content, new_content) = self._execute_file_editor(
            command=action.command,
            path=file_path,
            file_text=action.file_text,
            old_str=action.old_str,
            new_str=action.new_str,
            insert_line=action.insert_line,
            enable_linting=False,
        )
        return FileEditObservation(
            content=result_str,
            path=action.path,
            old_content=action.old_str,
            new_content=action.new_str,
            impl_source=FileEditSource.OH_ACI,
            diff=get_diff(old_contents=old_content or "", new_contents=new_content or "", filepath=action.path),
        )

    async def call_tool_mcp(self, action: MCPAction) -> Observation:
        """Execute an MCP tool action in CLI runtime.

        Args:
            action: The MCP action to execute

        Returns:
            Observation: The result of the MCP tool execution

        """
        if sys.platform == "win32":
            self.log("info", "MCP functionality is disabled on Windows")
            return ErrorObservation("MCP functionality is not available on Windows")
        try:
            mcp_config = self.get_mcp_config()
            if not mcp_config.sse_servers and (not mcp_config.shttp_servers) and (not mcp_config.stdio_servers):
                self.log("warning", "No MCP servers configured")
                return ErrorObservation("No MCP servers configured")
            self.log(
                "debug",
                f"Creating MCP clients for action {
                    action.name} with servers: SSE={
                    len(
                        mcp_config.sse_servers)}, SHTTP={
                    len(
                        mcp_config.shttp_servers)}, stdio={
                            len(
                                mcp_config.stdio_servers)}",
            )
            mcp_clients = await mcp_utils.create_mcp_clients(
                mcp_config.sse_servers,
                mcp_config.shttp_servers,
                self.sid,
                mcp_config.stdio_servers,
            )
            if not mcp_clients:
                self.log("warning", "No MCP clients could be created")
                return ErrorObservation("No MCP clients could be created - check server configurations")
            self.log("debug", f"Executing MCP tool: {action.name} with arguments: {action.arguments}")
            result = await mcp_utils.call_tool_mcp(mcp_clients, action)
            self.log("debug", f"MCP tool {action.name} executed successfully")
            return result
        except Exception as e:
            error_msg = f"Error executing MCP tool {action.name}: {e!s}"
            self.log("error", error_msg)
            return ErrorObservation(error_msg)

    @property
    def workspace_root(self) -> Path:
        """Return the workspace root path."""
        return Path(os.path.abspath(self._workspace_path))

    def copy_to(self, host_src: str, sandbox_dest: str, recursive: bool = False) -> None:
        """Copy a file or directory from the host to the sandbox."""
        # Validate runtime and source
        self._validate_copy_operation(host_src)

        # Sanitize destination
        dest = self._sanitize_filename(sandbox_dest)

        try:
            # Handle directory copy
            if os.path.isdir(host_src) and recursive:
                self._copy_directory(host_src, dest)
            # Handle file copy
            elif os.path.isfile(host_src):
                self._copy_file(host_src, dest, sandbox_dest)
            else:
                msg = f"Source path '{host_src}' is not a valid file or directory."
                raise FileNotFoundError(msg)

        except FileNotFoundError as e:
            logger.error("File not found during copy: %s", str(e))
            raise
        except shutil.SameFileError as e:
            logger.debug("Skipping copy as source and destination are the same: %s", str(e))
        except Exception as e:
            logger.error("Unexpected error copying file: %s", str(e))
            msg = f"Unexpected error copying file: {e!s}"
            raise RuntimeError(msg) from e

    def _validate_copy_operation(self, host_src: str) -> None:
        """Validate copy operation prerequisites."""
        if not self._runtime_initialized:
            msg = "Runtime not initialized"
            raise RuntimeError(msg)
        if not os.path.exists(host_src):
            msg = f"Source path '{host_src}' does not exist."
            raise FileNotFoundError(msg)

    def _copy_directory(self, host_src: str, dest: str) -> None:
        """Copy a directory recursively."""
        final_target_dir = os.path.join(dest, os.path.basename(host_src))

        if os.path.realpath(host_src) == os.path.realpath(final_target_dir):
            logger.debug("Skipping recursive copy: source and target are identical.")
        else:
            os.makedirs(dest, exist_ok=True)
            shutil.copytree(host_src, final_target_dir, dirs_exist_ok=True)

    def _copy_file(self, host_src: str, dest: str, sandbox_dest: str) -> None:
        """Copy a file to the destination."""
        final_target_file_path = self._determine_file_destination(host_src, dest, sandbox_dest)

        # Ensure destination directory exists
        os.makedirs(os.path.dirname(final_target_file_path), exist_ok=True)

        # Copy the file
        shutil.copy2(host_src, final_target_file_path)

    def _determine_file_destination(self, host_src: str, dest: str, sandbox_dest: str) -> str:
        """Determine the final destination path for a file."""
        # If destination is a directory or ends with separator
        if (
            os.path.isdir(dest)
            or sandbox_dest.endswith(("/", os.sep))
            or (not os.path.exists(dest) and "." not in os.path.basename(dest))
        ):
            target_dir = dest
            os.makedirs(target_dir, exist_ok=True)
            return os.path.join(target_dir, os.path.basename(host_src))

        # Default: use destination as file path
        return dest

    def list_files(self, path: str | None = None) -> list[str]:
        """List files in the sandbox."""
        if not self._runtime_initialized:
            msg = "Runtime not initialized"
            raise RuntimeError(msg)
        if path is None:
            dir_path = self._workspace_path
        else:
            dir_path = self._sanitize_filename(path)
        try:
            if not os.path.exists(dir_path):
                return []
            if not os.path.isdir(dir_path):
                return [dir_path]
            return [os.path.join(dir_path, f) for f in os.listdir(dir_path)]
        except Exception as e:
            logger.error("Error listing files: %s", str(e))
            return []

    def copy_from(self, path: str) -> Path:
        """Zip all files in the sandbox and return a path in the local filesystem."""
        if not self._runtime_initialized:
            msg = "Runtime not initialized"
            raise RuntimeError(msg)
        source_path = self._sanitize_filename(path)
        if not os.path.exists(source_path):
            msg = f"Path not found: {path}"
            raise FileNotFoundError(msg)
        temp_zip = tempfile.NamedTemporaryFile(suffix=".zip", delete=False)
        temp_zip.close()
        try:
            with zipfile.ZipFile(temp_zip.name, "w", zipfile.ZIP_DEFLATED) as zipf:
                if os.path.isdir(source_path):
                    for root, _, files in os.walk(source_path):
                        for file in files:
                            file_path = os.path.join(root, file)
                            arcname = os.path.relpath(file_path, source_path)
                            zipf.write(file_path, arcname)
                else:
                    zipf.write(source_path, os.path.basename(source_path))
            return Path(temp_zip.name)
        except Exception as e:
            logger.error("Error creating zip file: %s", str(e))
            msg = f"Error creating zip file: {e!s}"
            raise RuntimeError(msg) from e

    def close(self) -> None:
        """Close CLI runtime and clean up PowerShell session."""
        if self._powershell_session is not None:
            try:
                self._powershell_session.close()
                logger.debug("PowerShell session closed successfully.")
            except Exception as e:
                logger.warning("Error closing PowerShell session: %s", e)
            finally:
                self._powershell_session = None
        self._runtime_initialized = False
        super().close()

    @classmethod
    async def delete(cls, conversation_id: str) -> None:
        """Delete any resources associated with a conversation."""
        temp_dir = tempfile.gettempdir()
        prefix = f"FORGE_workspace_{conversation_id}_"
        for item in os.listdir(temp_dir):
            if item.startswith(prefix):
                try:
                    path = os.path.join(temp_dir, item)
                    if os.path.isdir(path):
                        shutil.rmtree(path)
                        logger.info("Deleted workspace directory: %s", path)
                except Exception as e:
                    logger.error("Error deleting workspace directory: %s", str(e))

    @property
    def additional_agent_instructions(self) -> str:
        """Get additional instructions for agent in CLI runtime.
        
        Returns:
            Instructions string with working directory constraints

        """
        return "\n\n".join(
            [
                f"Your working directory is {
                    self._workspace_path}. You can only read and write files in this directory.",
                "You are working directly on the user's machine. In most cases, the working environment is already set up.",
            ],
        )

    def get_mcp_config(self, extra_stdio_servers: list[MCPStdioServerConfig] | None = None) -> MCPConfig:
        """Get MCP configuration for CLI runtime.

        Args:
            extra_stdio_servers: Additional stdio servers to include in the config

        Returns:
            MCPConfig: The MCP configuration with stdio servers and any configured SSE/SHTTP servers

        """
        if sys.platform == "win32":
            self.log("debug", "MCP is disabled on Windows, returning empty config")
            return MCPConfig(sse_servers=[], stdio_servers=[], shttp_servers=[])
        mcp_config = self.config.mcp
        if extra_stdio_servers:
            current_stdio_servers = list(mcp_config.stdio_servers)
            for extra_server in extra_stdio_servers:
                if extra_server not in current_stdio_servers:
                    current_stdio_servers.append(extra_server)
                    self.log("info", f"Added extra stdio server: {extra_server.name}")
            mcp_config.stdio_servers = current_stdio_servers
        self.log(
            "debug",
            f"CLI MCP config: {
                len(
                    mcp_config.sse_servers)} SSE servers, {
                len(
                    mcp_config.stdio_servers)} stdio servers, {
                        len(
                            mcp_config.shttp_servers)} SHTTP servers",
        )
        return mcp_config

    def subscribe_to_shell_stream(self, callback: Callable[[str], None] | None = None) -> bool:
        """Subscribe to shell command output stream.

        Args:
            callback: A function that will be called with each line of output from shell commands.
                     If None, any existing subscription will be removed.

        """
        self._shell_stream_callback = callback
        return True
