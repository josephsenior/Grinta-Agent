"""Authenticated user authentication implementation.

Provides user authentication using JWT tokens and user store.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, cast

from forge.server.user_auth.user_auth import UserAuth
from forge.storage.user.file_user_store import get_user_store

if TYPE_CHECKING:
    from fastapi import Request
    from pydantic import SecretStr

    from forge.integrations.provider import PROVIDER_TOKEN_TYPE
    from forge.server.settings import Settings
    from forge.storage.data_models.user_secrets import UserSecrets
    from forge.storage.settings.settings_store import SettingsStore


@dataclass
class AuthenticatedUserAuth(UserAuth):
    """Authenticated user authentication implementation."""

    user_id: str | None = None
    _settings: "Settings" | None = None
    _settings_store: "SettingsStore" | None = None
    _secrets_store: "SecretsStore" | None = None
    _user_secrets: "UserSecrets" | None = None

    async def get_user_id(self) -> str | None:
        """Get the current user ID from request state."""
        return self.user_id

    async def get_user_email(self) -> str | None:
        """Get the current user email from request state."""
        if not self.user_id:
            return None

        from forge.storage.user.file_user_store import get_user_store

        user_store = get_user_store()
        user = await user_store.get_user_by_id(self.user_id)
        return user.email if user else None

    async def get_access_token(self) -> "SecretStr" | None:
        """Get the access token from request headers."""
        # Token is handled by middleware, not stored here
        return None

    async def get_user_settings_store(self) -> "SettingsStore":
        """Get settings store for the current user."""
        from forge.server import shared

        if self._settings_store:
            return self._settings_store

        user_id = await self.get_user_id()
        settings_store = await shared.SettingsStoreImpl.get_instance(
            shared.config, user_id
        )
        if settings_store is None:
            msg = "Failed to get settings store instance"
            raise ValueError(msg)
        self._settings_store = settings_store
        return settings_store

    async def get_user_settings(self) -> "Settings" | None:
        """Load and cache user settings."""
        if self._settings is not None:
            return self._settings

        settings_store = await self.get_user_settings_store()
        settings = await settings_store.load()
        if settings:
            settings = settings.merge_with_config_settings()
        self._settings = settings
        return settings

    async def get_secrets_store(self) -> "SecretsStore":
        """Get secrets store for the current user."""
        from forge.server import shared

        if self._secrets_store:
            return self._secrets_store

        user_id = await self.get_user_id()
        secrets_store = await shared.SecretsStoreImpl.get_instance(
            shared.config, user_id
        )
        if secrets_store is None:
            msg = "Failed to get secrets store instance"
            raise ValueError(msg)
        self._secrets_store = secrets_store
        return secrets_store

    async def get_user_secrets(self) -> "UserSecrets" | None:
        """Load user secrets."""
        if self._user_secrets:
            return self._user_secrets

        secrets_store = await self.get_secrets_store()
        user_secrets = await secrets_store.load()
        self._user_secrets = user_secrets
        return user_secrets

    async def get_provider_tokens(self) -> "PROVIDER_TOKEN_TYPE" | None:
        """Get provider tokens from user secrets."""
        user_secrets = await self.get_user_secrets()
        return (
            None
            if user_secrets is None
            else cast("PROVIDER_TOKEN_TYPE", user_secrets.provider_tokens)
        )

    @classmethod
    async def get_instance(cls, request: "Request") -> UserAuth:
        """Create instance from request with user ID from JWT."""
        instance = AuthenticatedUserAuth()
        # Get user_id from request state (set by AuthMiddleware)
        instance.user_id = getattr(request.state, "user_id", None)
        return instance

