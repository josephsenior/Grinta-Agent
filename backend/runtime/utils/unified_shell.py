"""Unified shell session abstraction for cross-platform runtime.

Provides a consistent interface for shell operations across different platforms
and shell types (Bash, PowerShell, etc.).
"""

from __future__ import annotations

import sys
from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

from backend.core.logger import forge_logger as logger

if TYPE_CHECKING:
    from backend.events.action import CmdRunAction
    from backend.events.observation import Observation
    from backend.runtime.utils.tool_registry import ToolRegistry
    from backend.runtime.utils.process_registry import TaskCancellationService


class UnifiedShellSession(ABC):
    """Abstract base class for shell sessions.
    
    Provides a consistent interface regardless of the underlying shell
    implementation (Bash + tmux, PowerShell, simple subprocess, etc.).
    """
    
    @abstractmethod
    def initialize(self) -> None:
        """Initialize the shell session."""
        pass
    
    @abstractmethod
    def execute(self, action: CmdRunAction) -> Observation:
        """Execute a command in the shell.
        
        Args:
            action: Command action to execute
        
        Returns:
            Observation with command output
        """
        pass
    
    @abstractmethod
    def close(self) -> None:
        """Close the shell session and clean up resources."""
        pass
    
    @property
    @abstractmethod
    def cwd(self) -> str:
        """Get current working directory."""
        pass
    
    @abstractmethod
    def get_detected_server(self):
        """Get and clear the last detected server.
        
        Returns:
            DetectedServer if one was detected since last check, None otherwise
        """
        pass


def create_shell_session(
    work_dir: str,
    tools: ToolRegistry | None = None,
    username: str | None = None,
    no_change_timeout_seconds: int = 30,
    max_memory_mb: int | None = None,
    cancellation_service: "TaskCancellationService | None" = None,
) -> UnifiedShellSession:
    """Factory function to create the appropriate shell session.
    
    Args:
        work_dir: Working directory for the session
        tools: ToolRegistry with detected tools (optional)
        username: Optional username for the session
        no_change_timeout_seconds: Timeout for no output change
        max_memory_mb: Optional memory limit
    
    Returns:
        Appropriate shell session implementation
    """
    if tools is None:
        from backend.runtime.utils.tool_registry import ToolRegistry
        tools = ToolRegistry()

    if cancellation_service is None:
        from backend.runtime.utils.process_registry import TaskCancellationService

        cancellation_service = TaskCancellationService(label="runtime")
    
    logger.info(f"Creating shell session for platform: {sys.platform}")
    logger.info(f"Detected shell: {tools.shell_type}")
    logger.info(f"Has tmux: {tools.has_tmux}")
    
    # Windows: Use PowerShell session
    if sys.platform == "win32":
        from backend.runtime.utils.windows_bash import WindowsPowershellSession
        
        logger.info("Using WindowsPowershellSession")
        session = WindowsPowershellSession(
            work_dir=work_dir,
            username=username,
            no_change_timeout_seconds=no_change_timeout_seconds,
            max_memory_mb=max_memory_mb,
            cancellation_service=cancellation_service,
        )
        # Type cast for mypy - WindowsPowershellSession implements UnifiedShellSession interface
        return session  # type: ignore[return-value]
    
    # Unix with tmux: Use full BashSession
    elif tools.has_tmux and tools.has_bash:
        from backend.runtime.utils.bash import BashSession
        
        logger.info("Using BashSession with tmux")
        return BashSession(
            work_dir=work_dir,
            username=username,
            no_change_timeout_seconds=no_change_timeout_seconds,
            max_memory_mb=max_memory_mb,
            cancellation_service=cancellation_service,
        )
    
    # Unix without tmux: Use simple Bash session
    elif tools.has_bash:
        from backend.runtime.utils.simple_bash import SimpleBashSession
        
        logger.info("Using SimpleBashSession (no tmux)")
        return SimpleBashSession(
            work_dir=work_dir,
            username=username,
            no_change_timeout_seconds=no_change_timeout_seconds,
            max_memory_mb=max_memory_mb,
            cancellation_service=cancellation_service,
        )
    
    # Fallback: Should not happen if tools are detected correctly
    else:
        raise RuntimeError(
            f"No suitable shell found for platform {sys.platform}. "
            f"Detected shell: {tools.shell_type}"
        )
