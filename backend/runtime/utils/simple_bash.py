"""Simple Bash session using subprocess (no tmux required).

Provides Bash command execution without tmux dependency.
Useful for systems that have Bash but not tmux installed.
"""

from __future__ import annotations

import os
import subprocess
from typing import TYPE_CHECKING

from backend.core.logger import forge_logger as logger
from backend.events.observation import ErrorObservation
from backend.events.observation.commands import (
    CmdOutputMetadata,
    CmdOutputObservation,
)
from backend.runtime.utils.process_registry import TaskCancellationService

if TYPE_CHECKING:
    from backend.events.action import CmdRunAction


class SimpleBashSession:
    """Bash session using simple subprocess calls (no tmux).
    
    This is a fallback for systems that have Bash but not tmux.
    It's simpler but lacks some features like background job management.
    """
    
    def __init__(
        self,
        work_dir: str,
        username: str | None = None,
        no_change_timeout_seconds: int = 30,
        max_memory_mb: int | None = None,
        cancellation_service: TaskCancellationService | None = None,
    ) -> None:
        """Initialize simple Bash session.
        
        Args:
            work_dir: Working directory for the session
            username: Optional username (currently ignored)
            no_change_timeout_seconds: Timeout for no output change
            max_memory_mb: Optional memory limit (currently ignored)
        """
        self._closed = False
        self._initialized = False
        self.work_dir = os.path.abspath(work_dir)
        self.username = username
        self._cwd: str = self.work_dir
        self.NO_CHANGE_TIMEOUT_SECONDS = no_change_timeout_seconds
        self.max_memory_mb = max_memory_mb
        self._cancellation = cancellation_service or TaskCancellationService(label="runtime")
        
        logger.info(
            "Initializing SimpleBashSession (no tmux). Work dir: %s",
            self.work_dir,
        )
    
    def initialize(self) -> None:
        """Initialize the session."""
        # Verify bash is available
        try:
            result = subprocess.run(
                ["bash", "--version"],
                capture_output=True,
                text=True,
                timeout=5,
                check=False,
            )
            if result.returncode != 0:
                raise RuntimeError("Bash is not available")
            
            logger.info("Bash version: %s", result.stdout.split("\n")[0])
        except (FileNotFoundError, subprocess.TimeoutExpired) as e:
            raise RuntimeError(f"Failed to initialize Bash session: {e}") from e
        
        # Verify working directory exists
        if not os.path.isdir(self._cwd):
            os.makedirs(self._cwd, exist_ok=True)
            logger.info("Created working directory: %s", self._cwd)
        
        self._initialized = True
        logger.info("SimpleBashSession initialized successfully")
    
    @property
    def cwd(self) -> str:
        """Get current working directory."""
        return self._cwd
    
    def execute(self, action: CmdRunAction) -> CmdOutputObservation | ErrorObservation:
        """Execute a command in Bash.
        
        Args:
            action: Command action to execute
        
        Returns:
            Observation with command output
        """
        if not self._initialized or self._closed:
            return ErrorObservation(
                content="Bash session is not initialized or has been closed."
            )
        
        command = action.command.strip()
        timeout_seconds = self._normalize_timeout(action.timeout)
        is_input = action.is_input
        
        if is_input:
            return ErrorObservation(
                content="Interactive input not supported in SimpleBashSession. "
                "Use tmux-based BashSession for interactive commands."
            )
        
        # Handle background commands (ending with &)
        command, run_in_background = self._prepare_command(command)
        
        logger.info(
            "Executing command: '%s', Timeout: %ss, background: %s",
            command,
            timeout_seconds,
            run_in_background,
        )
        
        if run_in_background:
            # For background commands, use nohup
            bg_command = f"nohup {command} > /dev/null 2>&1 & echo $!"
            stdout, stderr, exit_code = self._run_command(bg_command, timeout=10)
            
            if exit_code == 0 and stdout.strip().isdigit():
                pid = stdout.strip()
                logger.info("Background process started with PID: %s", pid)
                try:
                    self._cancellation.register_pid(int(pid))
                except Exception:
                    logger.debug("Failed to register background pid=%s", pid, exc_info=True)
                metadata = CmdOutputMetadata(
                    exit_code=0,
                    working_dir=self._cwd,
                )
                # Output format: [1] for compatibility with tmux tests
                return CmdOutputObservation(
                    content=f"[{pid}]",
                    command=command,
                    metadata=metadata,
                )
            else:
                logger.warning("Failed to start background process, running normally")
                run_in_background = False
        
        if not run_in_background:
            # Regular foreground command
            stdout, stderr, exit_code = self._run_command(
                command,
                timeout=timeout_seconds,
            )
            
            content_parts = []
            if stdout:
                content_parts.append(stdout)
            if stderr:
                content_parts.append("[ERROR STREAM]\n" + stderr)
            
            final_content = "\n".join(content_parts).strip()
            metadata = CmdOutputMetadata(
                exit_code=exit_code,
                working_dir=self._cwd,
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
    
    def _run_command(
        self,
        command: str,
        timeout: int | None = None,
    ) -> tuple[str, str, int]:
        """Run a Bash command via subprocess.
        
        Args:
            command: The Bash command to execute
            timeout: Timeout in seconds (None for no timeout)
        
        Returns:
            Tuple of (stdout, stderr, exit_code)
        """
        if self._closed:
            raise RuntimeError("Bash session is closed")
        
        process: subprocess.Popen | None = None
        try:
            process = subprocess.Popen(
                ["bash", "-c", command],
                cwd=self._cwd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
            )
            self._cancellation.register_process(process)

            stdout, stderr = process.communicate(timeout=timeout)
            return_code = process.returncode

            if "cd " in command:
                cwd_result = subprocess.run(
                    ["bash", "-c", "pwd"],
                    cwd=self._cwd,
                    capture_output=True,
                    text=True,
                    timeout=5,
                    check=False,
                )
                if cwd_result.returncode == 0:
                    new_cwd = cwd_result.stdout.strip()
                    if os.path.isdir(new_cwd):
                        self._cwd = new_cwd

            return (stdout, stderr, return_code)

        except subprocess.TimeoutExpired:
            logger.warning("Command timed out after %s seconds: %s", timeout, command)
            if process is not None:
                try:
                    process.kill()
                except Exception:
                    pass
            return ("", f"Command timed out after {timeout} seconds", 124)

        except Exception as e:
            logger.error("Error running Bash command: %s", e)
            return ("", str(e), 1)

        finally:
            if process is not None and getattr(process, "pid", None):
                self._cancellation.unregister_process(process.pid)
    
    def _normalize_timeout(self, timeout: int | float | None) -> int:
        """Normalize timeout value."""
        if timeout is None:
            return 60
        try:
            return int(timeout)
        except (TypeError, ValueError):
            return 60
    
    def _prepare_command(self, command: str) -> tuple[str, bool]:
        """Prepare command and detect background execution."""
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
            None (SimpleBashSession doesn't support server detection)
        """
        return None
    
    def close(self) -> None:
        """Close the Bash session."""
        if self._closed:
            return
        logger.info("Closing SimpleBashSession")
        self._closed = True
