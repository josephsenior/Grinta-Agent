"""Canonical error types for boundary normalization.

These are intentionally small and generic. Layers (server/runtime/storage) can
wrap arbitrary exceptions into one of these for consistent handling.
"""

from __future__ import annotations


class ForgeError(RuntimeError):
    """Base class for normalized Forge errors."""


class RetryableError(ForgeError):
    """Operation may succeed if retried."""


class UserActionRequiredError(ForgeError):
    """User must change config/inputs before retrying."""


class InvariantBrokenError(ForgeError):
    """A system invariant was violated; continuing may be unsafe."""


def classify_error(exc: Exception) -> type[ForgeError]:
    """Best-effort classification helper."""
    if isinstance(exc, (ValueError,)):  # narrow by default
        return UserActionRequiredError
    return ForgeError


# ============================================================================
# Agent Runtime Errors (Phase 2: Bulletproof Execution)
# ============================================================================


class AgentRuntimeError(ForgeError):
    """Base class for all agent runtime errors with context."""

    def __init__(self, message: str, context: dict = None):
        super().__init__(message)
        self.context = context or {}


class ToolExecutionError(AgentRuntimeError):
    """Raised when a tool fails to execute (e.g., file not found, syntax error)."""

    pass


class ContextLimitError(AgentRuntimeError):
    """Raised when the LLM context window is exceeded."""

    pass


class PlanningError(AgentRuntimeError):
    """Raised when the planner fails to produce a valid next step."""

    pass


class ModelProviderError(AgentRuntimeError):
    """Raised when the LLM provider API fails (timeouts, rate limits)."""

    pass


class ConfigurationError(AgentRuntimeError):
    """Raised when the agent is misconfigured."""

    pass


# ============================================================================
# Session / Lifecycle Errors
# ============================================================================


class SessionError(ForgeError):
    """Base class for session lifecycle errors."""


class SessionStartupError(SessionError):
    """Raised when agent-session startup fails (runtime, controller, etc.)."""


class SessionAlreadyActiveError(SessionError):
    """Raised when trying to start a session that is already running."""


class RuntimeConnectError(SessionError, RetryableError):
    """Raised when the runtime fails to connect during session startup."""


class SocketAuthError(ForgeError):
    """Raised when Socket.IO auth validation fails."""


class EventStreamError(ForgeError):
    """Raised when event-stream operations fail."""
