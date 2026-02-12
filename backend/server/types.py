"""Type abstractions and enums shared across the server stack."""

from __future__ import annotations

from abc import ABC, abstractmethod
from enum import Enum
from typing import Any, ClassVar, Protocol

from backend.core.schemas import AppMode


class SessionMiddlewareInterface(Protocol):
    """Protocol for session middleware classes."""


class ServerConfigInterface(ABC):
    """Abstract interface describing server configuration requirements."""

    CONFIG_PATH: ClassVar[str | None]
    APP_MODE: ClassVar[AppMode]
    POSTHOG_CLIENT_KEY: ClassVar[str]
    GITHUB_CLIENT_ID: ClassVar[str]
    ATTACH_SESSION_MIDDLEWARE_PATH: ClassVar[str]

    @abstractmethod
    def verify_config(self) -> None:
        """Verify configuration settings."""
        raise NotImplementedError

    @abstractmethod
    def get_config(self) -> dict[str, Any]:
        """Configure attributes for frontend."""
        raise NotImplementedError


class MissingSettingsError(ValueError):
    """Raised when settings are missing or not found."""


class LLMAuthenticationError(ValueError):
    """Raised when there is an issue with LLM authentication."""
