"""Process manager for tracking and cleaning up long-running processes.

Prevents orphaned processes (npm run dev, http.server, etc.) from running
forever after conversation stops.
"""

from __future__ import annotations

import asyncio
import signal
import time
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from openhands.core.logger import openhands_logger as logger
from openhands.utils.async_utils import call_sync_from_async

if TYPE_CHECKING:
    from openhands.runtime.utils.bash import BashSession


@dataclass
class ManagedProcess:
    """Represents a managed long-running process."""
    
    command: str
    process_name: str  # Simplified - extract main process name (npm, python, etc.)
    started_at: float
    command_id: str


class ProcessManager:
    """Manager for tracking and cleaning up long-running processes.
    
    Usage:
        manager = ProcessManager()
        
        # Register process when started
        manager.register_process(command, command_id)
        
        # Cleanup when conversation stops
        await manager.cleanup_all(runtime)
    """
    
    def __init__(self):
        self._processes: dict[str, ManagedProcess] = {}
        self._cleanup_lock = asyncio.Lock()
    
    def _extract_process_name(self, command: str) -> str:
        """Extract the main process name from command for pkill.
        
        Args:
            command: Full command string
            
        Returns:
            Process name (e.g., 'python', 'npm', 'node')
        """
        cmd_lower = command.lower().strip()
        
        # Common patterns
        if 'python' in cmd_lower:
            return 'python' if 'python3' not in cmd_lower else 'python3'
        if 'npm' in cmd_lower:
            return 'npm'
        if 'node' in cmd_lower:
            return 'node'
        if 'yarn' in cmd_lower:
            return 'yarn'
        if 'pnpm' in cmd_lower:
            return 'pnpm'
        
        # Default: first word of command
        return command.split()[0] if command.split() else 'unknown'
    
    def register_process(
        self,
        command: str,
        command_id: str,
    ) -> None:
        """Register a long-running process for tracking.
        
        Args:
            command: The command being executed
            command_id: Unique identifier for this command execution
        """
        process_name = self._extract_process_name(command)
        process = ManagedProcess(
            command=command,
            process_name=process_name,
            started_at=time.time(),
            command_id=command_id,
        )
        self._processes[command_id] = process
        logger.info(f"📝 Registered long-running process: {command[:80]} (process: {process_name}, ID: {command_id})")
    
    def unregister_process(self, command_id: str) -> None:
        """Unregister a process that has terminated naturally.
        
        Args:
            command_id: Unique identifier for the command
        """
        if command_id in self._processes:
            process = self._processes.pop(command_id)
            logger.info(f"✅ Process terminated naturally: {process.command[:80]}")
    
    async def cleanup_all(self, runtime=None, timeout_seconds: int = 5) -> dict[str, bool]:
        """Cleanup all tracked processes using pkill.
        
        Args:
            runtime: Runtime instance (if available) for executing cleanup commands
            timeout_seconds: Seconds to wait for SIGTERM before SIGKILL
            
        Returns:
            Dictionary mapping command_id to success status
        """
        async with self._cleanup_lock:
            if not self._processes:
                logger.info("No long-running processes to cleanup")
                return {}
            
            logger.info(f"🧹 Starting cleanup of {len(self._processes)} long-running processes")
            results = {}
            
            # 🛡️ CRITICAL FIX: Kill by FULL command, not just process name
            # Before: pkill -f 'python' killed ALL python processes (including runtime!)
            # After: Kill each specific command individually
            for cmd_id, process in list(self._processes.items()):
                try:
                    # Step 1: Send SIGTERM (graceful shutdown) using the FULL command
                    logger.info(f"Sending SIGTERM to process: {process.command[:80]}")
                    if runtime:
                        from openhands.events.action import CmdRunAction
                        # Escape single quotes in command for safety
                        safe_command = process.command.replace("'", "'\\''")
                        await call_sync_from_async(
                            runtime.run,
                            CmdRunAction(command=f"pkill -TERM -f '{safe_command}' || true")
                        )
                    
                    # Step 2: Wait briefly for graceful shutdown
                    await asyncio.sleep(1)  # Reduced from 5s to 1s for faster cleanup
                    
                    # Step 3: Send SIGKILL (force kill) to any remaining instances
                    logger.info(f"Sending SIGKILL if needed: {process.command[:80]}")
                    if runtime:
                        safe_command = process.command.replace("'", "'\\''")
                        await call_sync_from_async(
                            runtime.run,
                            CmdRunAction(command=f"pkill -9 -f '{safe_command}' || true")
                        )
                    
                    logger.info(f"✅ Terminated process: {process.command[:80]}")
                    results[cmd_id] = True
                
                except Exception as e:
                    logger.error(f"Error cleaning up process {cmd_id}: {e}")
                    results[cmd_id] = False
            
            # Clear all tracked processes
            self._processes.clear()
            
            logger.info(f"✅ Cleanup completed. Success: {sum(results.values())}/{len(results)}")
            return results
    
    def get_running_processes(self) -> list[ManagedProcess]:
        """Get list of currently tracked processes.
        
        Returns:
            List of managed processes
        """
        return list(self._processes.values())
    
    def count(self) -> int:
        """Get count of tracked processes.
        
        Returns:
            Number of tracked processes
        """
        return len(self._processes)

