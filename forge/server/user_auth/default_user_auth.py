"""Default user authentication strategy providing single-tenant behavior."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, cast

from forge.server import shared
from forge.server.user_auth.user_auth import UserAuth
from forge.storage.secrets.secrets_store import SecretsStore

if TYPE_CHECKING:
    from fastapi import Request
    from pydantic import SecretStr

    from forge.integrations.provider import PROVIDER_TOKEN_TYPE
    from forge.server.settings import Settings
    from forge.storage.data_models.user_secrets import UserSecrets
    from forge.storage.settings.settings_store import SettingsStore


@dataclass
class DefaultUserAuth(UserAuth):
    """Default user authentication mechanism."""

    _settings: Settings | None = None
    _settings_store: SettingsStore | None = None
    _secrets_store: SecretsStore | None = None
    _user_secrets: UserSecrets | None = None

    async def get_user_id(self) -> str | None:
        """The default implementation does not support multi tenancy, so user_id is always None."""
        return None

    async def get_user_email(self) -> str | None:
        """The default implementation does not support multi tenancy, so email is always None."""
        return None

    async def get_access_token(self) -> SecretStr | None:
        """The default implementation does not support multi tenancy, so access_token is always None."""
        return None

    async def get_user_settings_store(self) -> SettingsStore:
        """Return shared SettingsStore instance (cached after first lookup)."""
        settings_store = self._settings_store
        if settings_store:
            return settings_store
        user_id = await self.get_user_id()
        settings_store = await shared.SettingsStoreImpl.get_instance(
            shared.config, user_id
        )
        if settings_store is None:
            msg = "Failed to get settings store instance"
            raise ValueError(msg)
        self._settings_store = settings_store
        return settings_store

    async def get_user_settings(self) -> Settings | None:
        """Load and cache user settings."""
        if self._settings is not None:
            return self._settings

        settings_store = await self.get_user_settings_store()
        settings = await settings_store.load()
        if settings:
            settings = settings.merge_with_config_settings()
        self._settings = settings
        return settings

    async def get_secrets_store(self) -> SecretsStore:
        """Return SecretsStore singleton for current user (cached)."""
        if secrets_store := self._secrets_store:
            return secrets_store
        user_id = await self.get_user_id()
        secret_store = await shared.SecretsStoreImpl.get_instance(
            shared.config, user_id
        )
        if secret_store is None:
            msg = "Failed to get secrets store instance"
            raise ValueError(msg)
        self._secrets_store = secret_store
        return secret_store

    async def get_user_secrets(self) -> UserSecrets | None:
        """Load user secrets (provider tokens, custom secrets) if available."""
        user_secrets = self._user_secrets
        if user_secrets:
            return user_secrets
        secrets_store = await self.get_secrets_store()
        user_secrets = await secrets_store.load()
        self._user_secrets = user_secrets
        return user_secrets

    async def get_provider_tokens(self) -> PROVIDER_TOKEN_TYPE | None:
        """Return provider tokens extracted from stored user secrets."""
        user_secrets = await self.get_user_secrets()
        return (
            None
            if user_secrets is None
            else cast("PROVIDER_TOKEN_TYPE", user_secrets.provider_tokens)
        )

    @classmethod
    async def get_instance(cls, request: Request) -> UserAuth:
        """Factory entrypoint to satisfy UserAuth interface."""
        return DefaultUserAuth()
