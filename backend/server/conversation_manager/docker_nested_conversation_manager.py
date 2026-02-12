"""Shim for Docker nested conversation manager.

Docker nested runtimes have been removed from this codebase. This module
exposes a lightweight shim that delegates to the `StandaloneConversationManager`.
Keeping this shim preserves import paths for any remaining references while
preventing the Docker runtime from being imported or used.
"""

from __future__ import annotations

from typing import Any

from backend.server.conversation_manager.standalone_conversation_manager import (
    StandaloneConversationManager,
)


def get_instance(*args: Any, **kwargs: Any):
    """Return the StandaloneConversationManager instance (local runtime).

    Preserves the original `get_instance` import path but ensures no Docker
    runtime code is imported or executed.
    """
    return StandaloneConversationManager.get_instance(*args, **kwargs)
