"""Collection of core agent implementations for Forge."""

# Import submodules using relative imports to avoid circular dependencies
from backend.controller.agent import Agent

from . import (
    auditor,  # noqa: F401
    echo,  # noqa: F401
    locator,  # noqa: F401
    navigator,  # noqa: F401
    orchestrator,  # noqa: F401
)

__all__ = [
    "Agent",
    "navigator",
    "orchestrator",
    "echo",
    "locator",
    "auditor",
]
