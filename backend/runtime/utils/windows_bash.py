"""This module provides a Windows-specific implementation for running commands in PowerShell.

Uses subprocess calls to pwsh.exe (PowerShell 7) or powershell.exe (Windows PowerShell).
This is simpler and more reliable than using the .NET SDK via pythonnet.
"""

from __future__ import annotations

import sys

# CRITICAL: Platform check MUST be the very first thing after imports
if sys.platform != "win32":
    class WindowsOnlyModuleError(RuntimeError):
        """Raised when Windows-specific module functionality is accessed on unsupported platforms."""
        def __init__(self, module: str):
            super().__init__(
                f"FATAL ERROR: This module ({module}) requires Windows platform, "
                f"but is running on {sys.platform}. This should never happen and indicates a "
                f"serious configuration issue. Please use the appropriate platform-specific runtime."
            )
    raise WindowsOnlyModuleError("windows_bash.py")

import os
import subprocess
import time
from pathlib import Path
from threading import RLock
from typing import TYPE_CHECKING

from backend.core.logger import forge_logger as logger
from backend.events.observation import ErrorObservation
from backend.events.observation.commands import (
    CmdOutputMetadata,
    CmdOutputObservation,
)
from backend.runtime.utils.bash_constants import TIMEOUT_MESSAGE_TEMPLATE
from backend.utils.shutdown_listener import should_continue

if TYPE_CHECKING:
    from backend.events.action import CmdRunAction


def _find_powershell_executable() -> str:
    """Find the best available PowerShell executable.
    
    Returns:
        Path to pwsh.exe (PowerShell 7) or powershell.exe (Windows PowerShell)
        
    Raises:
        RuntimeError: If no PowerShell executable is found
    """
    # Try PowerShell 7 first (pwsh.exe)
    try:
        result = subprocess.run(
            ["pwsh", "-NoProfile", "-Command", "$PSVersionTable.PSVersion"],
            capture_output=True,
            text=True,
            timeout=5,
        )
        if result.returncode == 0:
            logger.info("Found PowerShell 7 (pwsh.exe)")
            return "pwsh"
    except (FileNotFoundError, subprocess.TimeoutExpired):
        pass
    
    # Fall back to Windows PowerShell
    try:
        result = subprocess.run(
            ["powershell", "-NoProfile", "-Command", "$PSVersionTable.PSVersion"],
            capture_output=True,
            text=True,
            timeout=5,
        )
        if result.returncode == 0:
            logger.info("Found Windows PowerShell (powershell.exe)")
            return "powershell"
    except (FileNotFoundError, subprocess.TimeoutExpired):
        pass
    
    raise RuntimeError(
        "PowerShell is required on Windows but could not be found. "
        "Please install PowerShell 7 (https://aka.ms/powershell) or ensure Windows PowerShell is available."
    )


class WindowsPowershellSession:
    """Manages PowerShell command execution using subprocess calls.

    Executes commands via pwsh.exe or powershell.exe, maintaining working directory
    state between calls. Simpler and more reliable than .NET SDK approach.
    """

    def __init__(
        self,
        work_dir: str,
        username: str | None = None,
        no_change_timeout_seconds: int = 30,
        max_memory_mb: int | None = None,
    ) -> None:
        """Initializes the PowerShell session.

        Args:
            work_dir: The starting working directory for the session.
            username: (Currently ignored) Username for execution.
            no_change_timeout_seconds: Timeout in seconds if no output change is detected.
            max_memory_mb: (Currently ignored) Maximum memory limit for the process.
        """
        self._closed = False
        self._initialized = False
        self.work_dir = os.path.abspath(work_dir)
        self.username = username
        self._cwd: str = self.work_dir
        self.NO_CHANGE_TIMEOUT_SECONDS = no_change_timeout_seconds
        self.max_memory_mb = max_memory_mb
        self._job_lock = RLock()
        
        try:
            self.powershell_exe = _find_powershell_executable()
            # Verify the working directory exists
            if not os.path.isdir(self._cwd):
                os.makedirs(self._cwd, exist_ok=True)
                logger.info("Created working directory: %s", self._cwd)
            self._initialized = True
            logger.info(
                "PowerShell session initialized. Using: %s, Initial CWD: %s",
                self.powershell_exe,
                self._cwd,
            )
        except Exception as e:
            logger.error("Failed to initialize PowerShell session: %s", e)
            self.close()
            raise RuntimeError(f"Failed to initialize PowerShell session: {e}") from e

    def initialize(self) -> None:
        """Initialize the session (already done in __init__).
        
        This method is provided for compatibility with the base ShellSession interface.
        """
        if not self._initialized:
            raise RuntimeError("PowerShell session failed to initialize in __init__")

    @property
    def cwd(self) -> str:
        """Gets the current working directory of the session."""
        return self._cwd

    def _run_command(
        self,
        command: str,
        timeout: int | None = None,
        cwd: str | None = None,
        input_text: str | None = None,
    ) -> tuple[str, str, int]:
        """Run a PowerShell command via subprocess.

        Args:
            command: The PowerShell command to execute.
            timeout: Timeout in seconds (None for no timeout).
            cwd: Working directory (None to use session CWD).
            input_text: Input to send to the command.

        Returns:
            Tuple of (stdout, stderr, exit_code)
        """
        if self._closed:
            raise RuntimeError("PowerShell session is closed")
        
        work_dir = cwd or self._cwd
        if not os.path.isdir(work_dir):
            work_dir = self.work_dir
        
        # Build PowerShell command
        # Use -NoProfile for faster startup, -Command to execute
        ps_command = [
            self.powershell_exe,
            "-NoProfile",
            "-NonInteractive",
            "-Command",
            command,
        ]
        
        try:
            result = subprocess.run(
                ps_command,
                cwd=work_dir,
                capture_output=True,
                text=True,
                timeout=timeout,
                input=input_text,
            )
            
            # Update CWD if command changed directory
            if "Set-Location" in command or "cd " in command:
                # Try to get the new CWD
                cwd_result = subprocess.run(
                    [self.powershell_exe, "-NoProfile", "-NonInteractive", "-Command", "Get-Location"],
                    cwd=work_dir,
                    capture_output=True,
                    text=True,
                    timeout=5,
                )
                if cwd_result.returncode == 0:
                    new_cwd = cwd_result.stdout.strip()
                    if os.path.isdir(new_cwd):
                        self._cwd = new_cwd
            
            return (result.stdout, result.stderr, result.returncode)
        except subprocess.TimeoutExpired:
            logger.warning("Command timed out after %s seconds: %s", timeout, command)
            return ("", f"Command timed out after {timeout} seconds", 124)
        except Exception as e:
            logger.error("Error running PowerShell command: %s", e)
            return ("", str(e), 1)

    def execute(self, action: "CmdRunAction") -> CmdOutputObservation | ErrorObservation:
        """Executes a command.

        Args:
            action: The command execution action.

        Returns:
            CmdOutputObservation or ErrorObservation.
        """
        if not self._session_ready():
            return self._session_not_ready_observation()
        
        command = action.command.strip()
        timeout_seconds_int = self._normalize_timeout(action.timeout)
        is_input = action.is_input
        
        # Handle background commands (ending with &)
        command, run_in_background = self._prepare_command(command)
        
        logger.info(
            "Executing command: '%s', Timeout: %ss, is_input: %s, background: %s",
            command,
            timeout_seconds_int,
            is_input,
            run_in_background,
        )
        
        if run_in_background:
            # For background commands, start a job
            # PowerShell jobs require a persistent session, so we'll use Start-Process
            # or Start-Job in a way that works with subprocess
            job_command = f'Start-Job -ScriptBlock {{ Set-Location "{self._cwd}"; {command} }} | ForEach-Object {{ Write-Output $_.Id }}'
            stdout, stderr, exit_code = self._run_command(job_command, timeout=10)
            if exit_code == 0 and stdout.strip().isdigit():
                job_id = stdout.strip()
                logger.info("Background job started with ID: %s", job_id)
                metadata = CmdOutputMetadata(
                    exit_code=0,
                    working_dir=self._cwd.replace("\\", "\\\\"),
                )
                # Output format: [1] for compatibility with bash/tmux tests
                return CmdOutputObservation(
                    content=f"[{job_id}]",
                    command=command,
                    metadata=metadata,
                )
            else:
                # Fallback: just run it normally
                logger.warning("Failed to start background job, running normally")
                run_in_background = False
        
        if not run_in_background:
            # Regular foreground command
            stdout, stderr, exit_code = self._run_command(
                command,
                timeout=timeout_seconds_int,
                input_text=action.stdin if is_input else None,
            )
            
            content_parts = []
            if stdout:
                content_parts.append(stdout)
            if stderr:
                content_parts.append("[ERROR STREAM]\n" + stderr)
            
            final_content = "\n".join(content_parts).strip()
            python_safe_cwd = self._cwd.replace("\\", "\\\\")
            metadata = CmdOutputMetadata(
                exit_code=exit_code,
                working_dir=python_safe_cwd,
            )
            metadata.prefix = "[Below is the output of the previous command.]\n"
            metadata.suffix = f"\n[The command completed with exit code {exit_code}.]"
            
            return CmdOutputObservation(
                content=final_content,
                command=command,
                metadata=metadata,
            )

        return ErrorObservation(
            content="Internal error: Command execution fell through all paths."
        )

    def _session_ready(self) -> bool:
        return self._initialized and not self._closed

    def _session_not_ready_observation(self) -> ErrorObservation:
        return ErrorObservation(
            content="PowerShell session is not initialized or has been closed."
        )

    def _normalize_timeout(self, timeout: int | float | None) -> int:
        if timeout is None:
            return 60
        try:
            return int(timeout)
        except (TypeError, ValueError):
            return 60

    def _prepare_command(self, command: str) -> tuple[str, bool]:
        command = command.strip()
        run_in_background = False
        if command.endswith("&"):
            run_in_background = True
            command = command[:-1].strip()
            logger.info("Detected background command: '%s'", command)
        return command, run_in_background

    def get_detected_server(self):
        """Get and clear the last detected server.
        
        Returns:
            None (Windows PowerShell doesn't support server detection)
        """
        return None

    def close(self) -> None:
        """Closes the PowerShell session."""
        if self._closed:
            return
        logger.info("Closing PowerShell session.")
        self._closed = True
