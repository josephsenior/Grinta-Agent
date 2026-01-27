"""Routes for managing provider tokens and custom secrets via the API."""

from __future__ import annotations

from typing import TYPE_CHECKING, Annotated, Any, Mapping

from fastapi import APIRouter, Depends, status, FastAPI, Path
from fastapi.responses import JSONResponse
from typing import Annotated

from forge.core.logger import forge_logger as logger
from forge.integrations.provider import PROVIDER_TOKEN_TYPE, CustomSecret, ProviderToken
from forge.integrations.service_types import ProviderType
from forge.integrations.utils import validate_provider_token
from forge.server.dependencies import get_dependencies
from forge.server.settings import (
    CustomSecretModel,
    CustomSecretWithoutValueModel,
    GETCustomSecrets,
    POSTProviderModel,
)
from forge.server.user_auth import (
    get_provider_tokens,
    get_secrets_store,
    get_user_secrets,
)
from forge.storage.data_models.user_secrets import UserSecrets
from forge.storage.secrets.secrets_store import SecretsStore

if TYPE_CHECKING:
    from forge.storage.data_models.settings import Settings
    from forge.storage.settings.settings_store import SettingsStore

router = APIRouter(prefix="/api", dependencies=get_dependencies())


class _SecretsAppProxy:
    """Hybrid object that behaves like both an APIRouter and an ASGI app."""

    def __init__(self, base_router: APIRouter) -> None:
        self._router = base_router
        self._app: FastAPI | None = None

    def _ensure_app(self) -> FastAPI:
        if self._app is None:
            app = FastAPI()
            app.include_router(self._router)
            self._app = app
        return self._app

    def __getattr__(self, item):
        if hasattr(self._router, item):
            return getattr(self._router, item)
        app = self._ensure_app()
        return getattr(app, item)

    async def __call__(self, scope, receive, send) -> None:  # ASGI callable
        app = self._ensure_app()
        await app(scope, receive, send)


# Backwards compatibility: expose proxy as `app`
app = _SecretsAppProxy(router)


# 🚀 PERFORMANCE FIX: Cache migration status to avoid repeated writes
_migration_done_cache: dict[str, bool] = {}


async def invalidate_legacy_secrets_store(
    settings: Settings,
    settings_store: SettingsStore,
    secrets_store: SecretsStore,
) -> UserSecrets | None:
    """We are moving `secrets_store` (a field from `Settings` object) to its own dedicated store.

    This function moves the values from Settings to UserSecrets, and deletes the values in Settings.
    While this function in called multiple times, the migration only ever happens once.

    🚀 PERFORMANCE FIX: Added caching to prevent repeated database writes on every request.
    """
    # 🚀 FIX: Check cache first to avoid repeated migrations
    user_id = str(getattr(settings, "user_id", "default"))
    if _migration_done_cache.get(user_id, False):
        return None  # Migration already done for this user

    provider_tokens_map = getattr(
        getattr(settings, "secrets_store", None), "provider_tokens", None
    )
    if provider_tokens_map:
        user_secrets = UserSecrets(
            provider_tokens=provider_tokens_map,
        )

        await secrets_store.store(user_secrets)
        invalidated_secrets_settings = settings.model_copy(
            update={"secrets_store": UserSecrets()},
        )
        await settings_store.store(invalidated_secrets_settings)

        # 🚀 FIX: Mark migration as done for this user
        _migration_done_cache[user_id] = True

        return user_secrets

    # 🚀 FIX: Even if no tokens, mark as checked to avoid repeated calls
    _migration_done_cache[user_id] = True
    return None


def process_token_validation_result(
    confirmed_token_type: ProviderType | None,
    token_type: ProviderType,
) -> str:
    """Validate provider token type matches expected type.

    Args:
        confirmed_token_type: Validated token type from provider
        token_type: Expected token type

    Returns:
        Error message if validation fails, empty string otherwise

    """
    expected = (
        token_type.value if isinstance(token_type, ProviderType) else str(token_type)
    )
    if not confirmed_token_type or confirmed_token_type != token_type:
        return f"Invalid token. Please make sure it is a valid {expected} token."
    return ""


def _coerce_provider_type(token_type_key: str | ProviderType) -> ProviderType:
    return (
        token_type_key
        if isinstance(token_type_key, ProviderType)
        else ProviderType(token_type_key)
    )


def _provider_key(provider_type: ProviderType) -> str:
    return provider_type.value


async def _validate_incoming_token(
    token_value: ProviderToken, provider_type: ProviderType
) -> str:
    if not token_value.token:
        return ""
    confirmed_token_type = await validate_provider_token(
        token_value.token,
        token_value.host,
    )
    return process_token_validation_result(confirmed_token_type, provider_type)


async def _validate_existing_host_conflict(
    existing_token: ProviderToken | None,
    incoming_token: ProviderToken,
    provider_type: ProviderType,
) -> str:
    if (
        existing_token is None
        or existing_token.host == incoming_token.host
        or not existing_token.token
    ):
        return ""
    confirmed_token_type = await validate_provider_token(
        existing_token.token,
        incoming_token.host,
    )
    return process_token_validation_result(confirmed_token_type, provider_type)


def _incoming_token_provided(token_value: ProviderToken) -> bool:
    if not token_value.token:
        return False
    getter = getattr(token_value.token, "get_secret_value", None)
    secret_value = (
        getter() if callable(getter) else token_value.token  # type: ignore[arg-type]
    )
    return bool(secret_value and str(secret_value).strip())


def _resolved_provider_token(
    incoming_token: ProviderToken,
    existing_token: ProviderToken | None,
) -> ProviderToken:
    if existing_token and not _incoming_token_provided(incoming_token):
        return existing_token
    new_host = incoming_token.host or (existing_token.host if existing_token else None)
    return incoming_token.model_copy(update={"host": new_host})


def _merge_provider_tokens(
    incoming_tokens: dict[str, ProviderToken] | None,
    existing_tokens: Mapping[ProviderType, ProviderToken] | None,
) -> dict[ProviderType, ProviderToken]:
    if not incoming_tokens:
        return {}
    existing = dict(existing_tokens or {})
    merged: dict[ProviderType, ProviderToken] = {}
    for provider_key, token_value in incoming_tokens.items():
        provider_type = _coerce_provider_type(provider_key)
        merged[provider_type] = _resolved_provider_token(
            token_value,
            existing.get(provider_type),
        )
    return merged


async def check_provider_tokens(
    incoming_provider_tokens: POSTProviderModel,
    existing_provider_tokens: PROVIDER_TOKEN_TYPE | None,
) -> tuple[str, dict[str, ProviderToken]]:
    """Check and validate incoming provider tokens.

    Validates tokens against provider APIs and checks host compatibility.

    Args:
        incoming_provider_tokens: New provider tokens to validate
        existing_provider_tokens: Currently stored provider tokens

    Returns:
        Error message if validation fails, empty string if all valid

    """
    normalized_tokens: dict[str, ProviderToken] = {}
    incoming_tokens = incoming_provider_tokens.provider_tokens or {}
    existing_tokens = existing_provider_tokens or {}

    for token_type_key, token_value in incoming_tokens.items():
        provider_type = _coerce_provider_type(token_type_key)
        normalized_tokens[_provider_key(provider_type)] = token_value

        msg = await _validate_incoming_token(token_value, provider_type)
        if msg:
            return msg, normalized_tokens

        existing_token = existing_tokens.get(provider_type)
        msg = await _validate_existing_host_conflict(
            existing_token,
            token_value,
            provider_type,
        )
        if msg:
            return msg, normalized_tokens

    return "", normalized_tokens


@router.post("/add-git-providers")
async def store_provider_tokens(
    provider_info: POSTProviderModel,
    secrets_store: Annotated[Any, Depends(get_secrets_store)],
    provider_tokens: Annotated[
        PROVIDER_TOKEN_TYPE | None, Depends(get_provider_tokens)
    ],
) -> JSONResponse:
    """Store or update git provider authentication tokens.

    Validates and stores provider tokens (GitHub).

    Args:
        provider_info: Provider information and tokens to store
        secrets_store: Secrets storage dependency
        provider_tokens: Existing provider tokens

    Returns:
        JSON response with success/error message

    """
    provider_err_msg, normalized_input_tokens = await check_provider_tokens(
        provider_info, provider_tokens
    )
    if provider_err_msg:
        # nosec B628 - Not logging credentials, just error message
        logger.info("Returning 401 Unauthorized - Provider token error")
        return JSONResponse(
            status_code=status.HTTP_401_UNAUTHORIZED,
            content={"error": provider_err_msg},
        )
    try:
        user_secrets = await secrets_store.load() or UserSecrets()
        merged_tokens = _merge_provider_tokens(
            normalized_input_tokens,
            user_secrets.provider_tokens,
        )
        updated_secrets = user_secrets.model_copy(
            update={"provider_tokens": merged_tokens}
        )
        await secrets_store.store(updated_secrets)
        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content={"message": "Git providers stored"},
        )
    except Exception:
        logger.warning("Something went wrong storing git providers")  # nosec B608
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"error": "Something went wrong storing git providers"},
        )


@router.post("/unset-provider-tokens", response_model=None)
async def unset_provider_tokens(
    secrets_store: Annotated[Any, Depends(get_secrets_store)],
) -> JSONResponse:
    """Remove all git provider authentication tokens.

    Args:
        secrets_store: Secrets storage dependency

    Returns:
        JSON response with success/error message

    """
    try:
        user_secrets = await secrets_store.load()
        if user_secrets:
            updated_secrets = user_secrets.model_copy(update={"provider_tokens": {}})
            await secrets_store.store(updated_secrets)
        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content={"message": "Unset Git provider tokens"},
        )
    except Exception:
        logger.warning("Something went wrong unsetting tokens")  # nosec B608
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"error": "Something went wrong unsetting tokens"},
        )


@router.get("/secrets", response_model=None)
async def load_custom_secrets_names(
    user_secrets: Annotated[UserSecrets | None, Depends(get_user_secrets)],
) -> GETCustomSecrets | JSONResponse:
    """Get list of custom secret names and descriptions (without values).

    Args:
        user_secrets: User secrets dependency

    Returns:
        List of custom secrets metadata or error response

    """
    try:
        if not user_secrets:
            return GETCustomSecrets(custom_secrets=[])
        custom_secrets: list[CustomSecretWithoutValueModel] = []
        if user_secrets.custom_secrets:
            for secret_name, secret_value in user_secrets.custom_secrets.items():
                custom_secret = CustomSecretWithoutValueModel(
                    name=secret_name,
                    description=secret_value.description,
                )
                custom_secrets.append(custom_secret)
        return GETCustomSecrets(custom_secrets=custom_secrets)
    except Exception:
        logger.warning("Failed to load secret names")  # nosec B608
        logger.info(
            "Returning 401 Unauthorized - Failed to get secret names",
        )  # nosec B608 - Generic message
        return JSONResponse(
            status_code=status.HTTP_401_UNAUTHORIZED,
            content={"error": "Failed to get secret names"},
        )


@router.post("/secrets", response_model=None)
async def create_custom_secret(
    incoming_secret: CustomSecretModel,
    secrets_store: Annotated[Any, Depends(get_secrets_store)],
) -> JSONResponse:
    """Create a new custom secret.

    Args:
        incoming_secret: Secret data (name, value, description)
        secrets_store: Secrets storage dependency

    Returns:
        JSON response with success/error message

    """
    try:
        existing_secrets = await secrets_store.load()
        custom_secrets = (
            dict(existing_secrets.custom_secrets) if existing_secrets else {}
        )
        secret_name = incoming_secret.name
        secret_value = incoming_secret.value
        secret_description = incoming_secret.description
        if secret_name in custom_secrets:
            return JSONResponse(
                status_code=status.HTTP_400_BAD_REQUEST,
                content={"message": f"Secret {secret_name} already exists"},
            )
        custom_secrets[secret_name] = CustomSecret(
            secret=secret_value,
            description=secret_description or "",
        )
        updated_user_secrets = UserSecrets(
            custom_secrets=custom_secrets,
            provider_tokens=(
                existing_secrets.provider_tokens if existing_secrets else {}
            ),
        )
        await secrets_store.store(updated_user_secrets)
        return JSONResponse(
            status_code=status.HTTP_201_CREATED,
            content={"message": "Secret created successfully"},
        )
    except Exception:
        logger.warning("Something went wrong creating secret")  # nosec B608
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"error": "Something went wrong creating secret"},
        )


@router.put("/secrets/{secret_id}", response_model=None)
async def update_custom_secret(
    secret_id: Annotated[str, Path(..., min_length=1, description="Secret ID")],
    incoming_secret: CustomSecretWithoutValueModel,
    secrets_store: Annotated[Any, Depends(get_secrets_store)],
) -> JSONResponse:
    """Update an existing custom secret's name and/or description.

    Secret value is preserved. Allows renaming if new name doesn't conflict.

    Args:
        secret_id: ID of secret to update
        incoming_secret: Updated name and description
        secrets_store: Secrets storage dependency

    Returns:
        JSON response with success/error message

    """
    try:
        existing_secrets = await secrets_store.load()
        if existing_secrets:
            if secret_id not in existing_secrets.custom_secrets:
                return JSONResponse(
                    status_code=status.HTTP_404_NOT_FOUND,
                    content={"error": f"Secret with ID {secret_id} not found"},
                )
            secret_name = incoming_secret.name
            secret_description = incoming_secret.description
            custom_secrets = dict(existing_secrets.custom_secrets)
            existing_secret = custom_secrets.pop(secret_id)
            if secret_name != secret_id and secret_name in custom_secrets:
                return JSONResponse(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    content={"message": f"Secret {secret_name} already exists"},
                )
            custom_secrets[secret_name] = CustomSecret(
                secret=existing_secret.secret,
                description=secret_description or "",
            )
            updated_secrets = UserSecrets(
                custom_secrets=custom_secrets,
                provider_tokens=existing_secrets.provider_tokens,
            )
            await secrets_store.store(updated_secrets)
        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content={"message": "Secret updated successfully"},
        )
    except Exception:
        logger.warning("Something went wrong updating secret")  # nosec B608
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"error": "Something went wrong updating secret"},
        )


@router.delete("/secrets/{secret_id}")
async def delete_custom_secret(
    secret_id: Annotated[str, Path(..., min_length=1, description="Secret ID")],
    secrets_store: Annotated[Any, Depends(get_secrets_store)],
) -> JSONResponse:
    """Delete a custom secret by ID.

    Args:
        secret_id: ID of secret to delete
        secrets_store: Secrets storage dependency

    Returns:
        JSON response with success/error message

    """
    try:
        existing_secrets = await secrets_store.load()
        if existing_secrets:
            custom_secrets = dict(existing_secrets.custom_secrets)
            if secret_id not in custom_secrets:
                return JSONResponse(
                    status_code=status.HTTP_404_NOT_FOUND,
                    content={"error": f"Secret with ID {secret_id} not found"},
                )
            custom_secrets.pop(secret_id)
            updated_secrets = UserSecrets(
                custom_secrets=custom_secrets,
                provider_tokens=existing_secrets.provider_tokens,
            )
            await secrets_store.store(updated_secrets)
        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content={"message": "Secret deleted successfully"},
        )
    except Exception:
        logger.warning("Something went wrong deleting secret")  # nosec B608
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"error": "Something went wrong deleting secret"},
        )


# Provide both router and test app exports for compatibility
secrets_test_app = FastAPI()
secrets_test_app.include_router(router)
