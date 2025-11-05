from __future__ import annotations

from typing import TYPE_CHECKING, Annotated

from fastapi import APIRouter, Depends, status
from fastapi.responses import JSONResponse

from openhands.core.logger import openhands_logger as logger
from openhands.integrations.provider import PROVIDER_TOKEN_TYPE, CustomSecret
from openhands.integrations.utils import validate_provider_token
from openhands.server.dependencies import get_dependencies
from openhands.server.settings import (
    CustomSecretModel,
    CustomSecretWithoutValueModel,
    GETCustomSecrets,
    POSTProviderModel,
)
from openhands.server.user_auth import (
    get_provider_tokens,
    get_secrets_store,
    get_user_secrets,
)
from openhands.storage.data_models.user_secrets import UserSecrets
from openhands.storage.secrets.secrets_store import SecretsStore

if TYPE_CHECKING:
    from openhands.integrations.service_types import ProviderType
    from openhands.storage.data_models.settings import Settings
    from openhands.storage.settings.settings_store import SettingsStore

app = APIRouter(prefix="/api", dependencies=get_dependencies())


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
    user_id = str(getattr(settings, 'user_id', 'default'))
    if _migration_done_cache.get(user_id, False):
        return None  # Migration already done for this user
    
    if len(settings.secrets_store.provider_tokens.items()) > 0:
        user_secrets = UserSecrets(
            provider_tokens=settings.secrets_store.provider_tokens,
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
    if not confirmed_token_type or confirmed_token_type != token_type:
        return f"Invalid token. Please make sure it is a valid {token_type.value} token."
    return ""


async def check_provider_tokens(
    incoming_provider_tokens: POSTProviderModel,
    existing_provider_tokens: PROVIDER_TOKEN_TYPE | None,
) -> str:
    """Check and validate incoming provider tokens.
    
    Validates tokens against provider APIs and checks host compatibility.
    
    Args:
        incoming_provider_tokens: New provider tokens to validate
        existing_provider_tokens: Currently stored provider tokens
        
    Returns:
        Error message if validation fails, empty string if all valid
    """
    msg = ""
    if incoming_provider_tokens.provider_tokens:
        for token_type, token_value in incoming_provider_tokens.provider_tokens.items():
            if token_value.token:
                confirmed_token_type = await validate_provider_token(
                    token_value.token,
                    token_value.host,
                )
                msg = process_token_validation_result(confirmed_token_type, token_type)
            existing_token = existing_provider_tokens.get(token_type, None) if existing_provider_tokens else None
            if existing_token and existing_token.host != token_value.host and existing_token.token:
                confirmed_token_type = await validate_provider_token(
                    existing_token.token,
                    token_value.host,
                )
                if not confirmed_token_type or confirmed_token_type != token_type:
                    msg = process_token_validation_result(
                        confirmed_token_type,
                        token_type,
                    )
    return msg


@app.post("/add-git-providers")
async def store_provider_tokens(
    provider_info: POSTProviderModel,
    secrets_store: Annotated[SecretsStore, Depends(get_secrets_store)],
    provider_tokens: Annotated[PROVIDER_TOKEN_TYPE | None, Depends(get_provider_tokens)],
) -> JSONResponse:
    """Store or update git provider authentication tokens.
    
    Validates and stores provider tokens (GitHub, GitLab, Bitbucket, etc.).
    
    Args:
        provider_info: Provider information and tokens to store
        secrets_store: Secrets storage dependency
        provider_tokens: Existing provider tokens
        
    Returns:
        JSON response with success/error message
    """
    provider_err_msg = await check_provider_tokens(provider_info, provider_tokens)
    if provider_err_msg:
        # nosec B628 - Not logging credentials, just error message
        logger.info(
            "Returning 401 Unauthorized - Provider token error: %s",
            provider_err_msg,
        )
        return JSONResponse(
            status_code=status.HTTP_401_UNAUTHORIZED,
            content={"error": provider_err_msg},
        )
    try:
        user_secrets = await secrets_store.load() or UserSecrets()
        if provider_info.provider_tokens:
            existing_providers = list(user_secrets.provider_tokens)
            for provider, token_value in list(provider_info.provider_tokens.items()):
                if provider in existing_providers and (not token_value.token):
                    existing_token = user_secrets.provider_tokens.get(provider)
                    if existing_token and existing_token.token:
                        provider_info.provider_tokens[provider] = existing_token
                provider_info.provider_tokens[provider] = provider_info.provider_tokens[provider].model_copy(
                    update={"host": token_value.host},
                )
        updated_secrets = user_secrets.model_copy(
            update={"provider_tokens": provider_info.provider_tokens},
        )
        await secrets_store.store(updated_secrets)
        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content={"message": "Git providers stored"},
        )
    except Exception as e:
        logger.warning(
            "Something went wrong storing git providers: %s",
            e,
        )  # nosec B608 - Generic error
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"error": "Something went wrong storing git providers"},
        )


@app.post("/unset-provider-tokens", response_model=dict[str, str])
async def unset_provider_tokens(
    secrets_store: Annotated[SecretsStore, Depends(get_secrets_store)],
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
    except Exception as e:
        logger.warning(
            "Something went wrong unsetting tokens: %s",
            e,
        )  # nosec B608 - Generic error, no credentials
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"error": "Something went wrong unsetting tokens"},
        )


@app.get("/secrets", response_model=GETCustomSecrets)
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
    except Exception as e:
        logger.warning(
            "Failed to load secret names: %s",
            e,
        )  # nosec B608 - Generic error, no credentials
        logger.info(
            "Returning 401 Unauthorized - Failed to get secret names",
        )  # nosec B608 - Generic message
        return JSONResponse(
            status_code=status.HTTP_401_UNAUTHORIZED,
            content={"error": "Failed to get secret names"},
        )


@app.post("/secrets", response_model=dict[str, str])
async def create_custom_secret(
    incoming_secret: CustomSecretModel,
    secrets_store: Annotated[SecretsStore, Depends(get_secrets_store)],
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
        custom_secrets = dict(existing_secrets.custom_secrets) if existing_secrets else {}
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
            provider_tokens=(existing_secrets.provider_tokens if existing_secrets else {}),
        )
        await secrets_store.store(updated_user_secrets)
        return JSONResponse(
            status_code=status.HTTP_201_CREATED,
            content={"message": "Secret created successfully"},
        )
    except Exception as e:
        logger.warning(
            "Something went wrong creating secret: %s",
            e,
        )  # nosec B608 - Generic error
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"error": "Something went wrong creating secret"},
        )


@app.put("/secrets/{secret_id}", response_model=dict[str, str])
async def update_custom_secret(
    secret_id: str,
    incoming_secret: CustomSecretWithoutValueModel,
    secrets_store: Annotated[SecretsStore, Depends(get_secrets_store)],
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
    except Exception as e:
        logger.warning(
            "Something went wrong updating secret: %s",
            e,
        )  # nosec B608 - Generic error
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"error": "Something went wrong updating secret"},
        )


@app.delete("/secrets/{secret_id}")
async def delete_custom_secret(
    secret_id: str,
    secrets_store: Annotated[SecretsStore, Depends(get_secrets_store)],
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
    except Exception as e:
        logger.warning(
            "Something went wrong deleting secret: %s",
            e,
        )  # nosec B608 - Generic error
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"error": "Something went wrong deleting secret"},
        )
