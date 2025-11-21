"""FastAPI dependency helpers for retrieving user authentication artifacts."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from fastapi import Request

from forge.server.user_auth.user_auth import AuthType, get_user_auth
from forge.storage.secrets.secrets_store import SecretsStore

if TYPE_CHECKING:
    from pydantic import SecretStr

    from forge.integrations.provider import PROVIDER_TOKEN_TYPE
    from forge.server.settings import Settings
    from forge.storage.data_models.user_secrets import UserSecrets
    from forge.storage.settings.settings_store import SettingsStore


async def get_provider_tokens(request: Request) -> PROVIDER_TOKEN_TYPE | None:
    """Get provider authentication tokens from request.

    Args:
        request: HTTP request

    Returns:
        Provider tokens or None

    """
    user_auth = await get_user_auth(request)
    return await user_auth.get_provider_tokens()


async def get_access_token(request: Request) -> SecretStr | None:
    """Get external access token from request.

    Args:
        request: HTTP request

    Returns:
        Access token or None

    """
    user_auth = await get_user_auth(request)
    return await user_auth.get_access_token()


async def get_user_id(request: Request) -> str | None:
    """Get user ID from request.

    Args:
        request: HTTP request

    Returns:
        User ID or None

    """
    user_auth = await get_user_auth(request)
    return await user_auth.get_user_id()


async def get_user_settings(request: Request) -> Settings | None:
    """Get user settings from request.

    Args:
        request: HTTP request

    Returns:
        User settings or None

    """
    user_auth = await get_user_auth(request)
    return await user_auth.get_user_settings()


async def get_secrets_store(request: Request) -> SecretsStore:
    """Get secrets store from request.

    Args:
        request: HTTP request

    Returns:
        Secrets store instance

    """
    user_auth = await get_user_auth(request)
    return await user_auth.get_secrets_store()


async def get_user_secrets(request: Request) -> UserSecrets | None:
    """Get user secrets from request.

    Args:
        request: HTTP request

    Returns:
        User secrets or None

    """
    user_auth = await get_user_auth(request)
    return await user_auth.get_user_secrets()


async def get_user_settings_store(request: Request) -> SettingsStore | None:
    """Get user settings store from request.

    Args:
        request: HTTP request

    Returns:
        Settings store or None

    """
    user_auth = await get_user_auth(request)
    return await user_auth.get_user_settings_store()


async def get_auth_type(request: Request) -> AuthType | None:
    """Get authentication type from request.

    Args:
        request: HTTP request

    Returns:
        Authentication type or None

    """
    user_auth = await get_user_auth(request)
    return user_auth.get_auth_type()
