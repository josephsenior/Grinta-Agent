"""Resource limit enforcement for runtime operations.

Enforces memory, CPU, disk, and other resource limits to prevent resource exhaustion.
"""

from __future__ import annotations

import os
import psutil
from dataclasses import dataclass
from pathlib import Path

from backend.core.constants import (
    DEFAULT_RUNTIME_MAX_CPU_PERCENT,
    DEFAULT_RUNTIME_MAX_DISK_GB,
    DEFAULT_RUNTIME_MAX_FILE_COUNT,
    DEFAULT_RUNTIME_MAX_MEMORY_MB,
    DEFAULT_RUNTIME_MAX_NETWORK_REQUESTS_PER_MINUTE,
)
from backend.core.exceptions import ResourceLimitExceededError
from backend.core.logger import forge_logger as logger


@dataclass
class ResourceStats:
    """Current resource usage statistics."""
    memory_mb: float
    cpu_percent: float
    disk_gb: float
    file_count: int


@dataclass
class ResourceLimits:
    """Resource limit configuration."""

    max_memory_mb: int = DEFAULT_RUNTIME_MAX_MEMORY_MB
    max_cpu_percent: float = DEFAULT_RUNTIME_MAX_CPU_PERCENT
    max_disk_gb: int = DEFAULT_RUNTIME_MAX_DISK_GB
    max_file_count: int = DEFAULT_RUNTIME_MAX_FILE_COUNT
    max_network_requests_per_minute: int = DEFAULT_RUNTIME_MAX_NETWORK_REQUESTS_PER_MINUTE


class ResourceLimiter:
    """Enforce resource limits on runtime operations.
    
    This class checks current resource usage against configured limits and
    raises exceptions if limits are exceeded. This prevents resource exhaustion
    attacks and ensures fair resource allocation.
    """

    def __init__(
        self,
        limits: ResourceLimits | None = None,
        workspace_path: str | Path | None = None,
    ) -> None:
        """Initialize resource limiter.
        
        Args:
            limits: Resource limits configuration. If None, loads from environment.
            workspace_path: Path to workspace for disk/file counting
        """
        if limits is None:
            limits = ResourceLimits(
                max_memory_mb=int(
                    os.getenv("RUNTIME_MAX_MEMORY_MB", str(DEFAULT_RUNTIME_MAX_MEMORY_MB))
                ),
                max_cpu_percent=float(
                    os.getenv(
                        "RUNTIME_MAX_CPU_PERCENT", str(DEFAULT_RUNTIME_MAX_CPU_PERCENT)
                    )
                ),
                max_disk_gb=int(
                    os.getenv("RUNTIME_MAX_DISK_GB", str(DEFAULT_RUNTIME_MAX_DISK_GB))
                ),
                max_file_count=int(
                    os.getenv("RUNTIME_MAX_FILE_COUNT", str(DEFAULT_RUNTIME_MAX_FILE_COUNT))
                ),
            )
        
        self.limits = limits
        self.workspace_path = Path(workspace_path) if workspace_path else None

    def get_resource_stats(self) -> ResourceStats:
        """Get current resource usage statistics.
        
        Returns:
            ResourceStats with current usage
        """
        process = psutil.Process()
        
        # Memory usage (RSS - Resident Set Size)
        memory_info = process.memory_info()
        memory_mb = memory_info.rss / (1024 * 1024)
        
        # CPU usage (average over last second)
        cpu_percent = process.cpu_percent(interval=0.1)
        
        # Disk usage (if workspace path provided)
        disk_gb = 0.0
        file_count = 0
        if self.workspace_path and self.workspace_path.exists():
            try:
                # Get disk usage
                disk_usage = psutil.disk_usage(str(self.workspace_path))
                disk_gb = disk_usage.used / (1024 * 1024 * 1024)
                
                # Count files (with limit to avoid performance issues)
                file_count = sum(1 for _ in self.workspace_path.rglob("*") if _.is_file())
            except Exception as e:
                logger.warning(f"Error calculating disk/file stats: {e}")
        
        return ResourceStats(
            memory_mb=memory_mb,
            cpu_percent=cpu_percent,
            disk_gb=disk_gb,
            file_count=file_count,
        )

    def check_limits(self, raise_on_exceed: bool = True) -> bool:
        """Check if current resource usage is within limits.
        
        Args:
            raise_on_exceed: If True, raise exception on limit exceeded.
                           If False, return False.
        
        Returns:
            True if within limits, False if exceeded (only if raise_on_exceed=False)
        
        Raises:
            ResourceLimitExceededError: If limit exceeded and raise_on_exceed=True
        """
        stats = self.get_resource_stats()
        
        # Check memory limit
        if stats.memory_mb > self.limits.max_memory_mb:
            error_msg = (
                f"Memory limit exceeded: {stats.memory_mb:.1f}MB > {self.limits.max_memory_mb}MB"
            )
            if raise_on_exceed:
                raise ResourceLimitExceededError(error_msg)
            logger.warning(error_msg)
            return False
        
        # Check CPU limit (only warn, don't block - CPU is transient)
        if stats.cpu_percent > self.limits.max_cpu_percent:
            logger.warning(
                f"CPU usage high: {stats.cpu_percent:.1f}% > {self.limits.max_cpu_percent}%"
            )
            # Don't block on CPU - it's transient and can spike
        
        # Check disk limit
        if self.workspace_path and stats.disk_gb > self.limits.max_disk_gb:
            error_msg = (
                f"Disk limit exceeded: {stats.disk_gb:.1f}GB > {self.limits.max_disk_gb}GB"
            )
            if raise_on_exceed:
                raise ResourceLimitExceededError(error_msg)
            logger.warning(error_msg)
            return False
        
        # Check file count limit
        if self.workspace_path and stats.file_count > self.limits.max_file_count:
            error_msg = (
                f"File count limit exceeded: {stats.file_count} > {self.limits.max_file_count}"
            )
            if raise_on_exceed:
                raise ResourceLimitExceededError(error_msg)
            logger.warning(error_msg)
            return False
        
        return True

