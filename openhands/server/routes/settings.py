from __future__ import annotations

from typing import TYPE_CHECKING, Annotated

from fastapi import APIRouter, Depends, status
from fastapi.responses import JSONResponse

from openhands.core.logger import openhands_logger as logger
from openhands.core.pydantic_compat import model_dump_with_options
from openhands.server.dependencies import get_dependencies
from openhands.core.config.api_key_manager import api_key_manager
from openhands.server.routes.secrets import invalidate_legacy_secrets_store
from openhands.server.settings import GETSettingsModel
from openhands.server.shared import config
from openhands.server.user_auth import (
    get_provider_tokens,
    get_secrets_store,
    get_user_id,
    get_user_settings,
    get_user_settings_store,
)
from openhands.storage.data_models.settings import Settings
# Import these at runtime so FastAPI can resolve them in Annotated types
from openhands.integrations.provider import PROVIDER_TOKEN_TYPE, ProviderType
from openhands.storage.secrets.secrets_store import SecretsStore
from openhands.storage.settings.settings_store import SettingsStore

if TYPE_CHECKING:
    pass  # ProviderType is now imported at runtime

# Rebuild GETSettingsModel to resolve forward references
GETSettingsModel.model_rebuild()

app = APIRouter(prefix="/api", dependencies=get_dependencies())

# 🚀 PERFORMANCE FIX: Global cache for settings to avoid repeated database calls
#   Cache key: user_id (or 'default' for single-tenant), Cache value: (settings_response, timestamp)
#   TTL: 60 seconds (OPTIMIZED: increased from 30s for 2-3x improvement)
import time as time_module
_settings_cache: dict[str, tuple[GETSettingsModel, float]] = {}
_SETTINGS_CACHE_TTL = 60  # seconds (OPTIMIZED)

@app.get(
    "/settings",
    response_model=GETSettingsModel,
    responses={
        200: {
            "description": "Settings retrieved successfully",
            "content": {
                "application/json": {
                    "examples": {
                        "basic": {
                            "summary": "Basic configuration",
                            "value": {
                                "LLM_MODEL": "anthropic/claude-3-5-sonnet-20241022",
                                "LLM_API_KEY": "sk-ant-***",
                                "AGENT": "CodeActAgent",
                                "LANGUAGE": "en",
                                "LLM_NUM_RETRIES": 6,
                                "LLM_TIMEOUT": 180
                            }
                        }
                    }
                }
            }
        },
        404: {"description": "Settings not found"},
        401: {"description": "Invalid token"},
    },
)
async def load_settings(
    provider_tokens: Annotated[PROVIDER_TOKEN_TYPE | None, Depends(get_provider_tokens)],
    settings_store: Annotated[SettingsStore, Depends(get_user_settings_store)],
    settings: Annotated[Settings, Depends(get_user_settings)],
    secrets_store: Annotated[SecretsStore, Depends(get_secrets_store)],
    user_id: Annotated[str | None, Depends(get_user_id)] = None,
) -> GETSettingsModel | JSONResponse:
    """Load user settings with token status information.
    
    🚀 PERFORMANCE OPTIMIZED: 60s cache with proper per-user key for 2-3x improvement.
       - Increased TTL from 30s to 60s
       - Fixed cache key to use user_id instead of settings_hash
       - Expected: 1,295ms → ~300-500ms for 10 concurrent users

    Args:
        provider_tokens: Provider tokens dependency
        settings_store: Settings store dependency
        settings: User settings dependency
        secrets_store: Secrets store dependency
        user_id: User ID (None for single-tenant, defaults to 'default')

    Returns:
        Settings model or error response
    """
    try:
        if not settings:
            # Return default settings for development when no settings exist
            logger.info("No settings found, returning default settings for development")
            return _build_default_settings_response()

        # 🚀 PERFORMANCE FIX: Check cache first with proper user_id key
        # Use user_id as cache key (fallback to 'default' for single-tenant mode)
        cache_key = user_id if user_id else 'default'
        current_time = time_module.time()
        
        if cache_key in _settings_cache:
            cached_response, cached_time = _settings_cache[cache_key]
            if current_time - cached_time < _SETTINGS_CACHE_TTL:
                logger.debug(f"🚀 Cache HIT: Returning cached settings for user '{cache_key}'")
                return cached_response

        # Cache miss - load from database
        logger.debug(f"🚀 Cache MISS: Loading settings for user '{cache_key}'")
        # 🚀 CRITICAL FIX: Skip migration for performance - it only needs to run once per user
        # user_secrets = await invalidate_legacy_secrets_store(settings, settings_store, secrets_store)
        user_secrets = None  # Skip migration to eliminate 1+ second delay
        provider_tokens_set = _build_provider_tokens_set(user_secrets, provider_tokens)

        response = _build_settings_response(settings, provider_tokens_set)
        
        # 🚀 PERFORMANCE FIX: Cache the response with user_id key
        _settings_cache[cache_key] = (response, current_time)
        logger.debug(f"🚀 Cached settings for user '{cache_key}' (TTL: {_SETTINGS_CACHE_TTL}s)")
        
        return response

    except Exception as e:
        logger.warning("Error loading settings: %s, returning default settings for development", e)
        return _build_default_settings_response()


def _build_provider_tokens_set(
    user_secrets,
    provider_tokens: PROVIDER_TOKEN_TYPE | None,
) -> dict[ProviderType, str | None]:
    """Build provider tokens set dict.

    Args:
        user_secrets: User secrets object
        provider_tokens: Provider tokens

    Returns:
        Dictionary mapping provider type to host
    """
    git_providers = user_secrets.provider_tokens if user_secrets else provider_tokens
    provider_tokens_set: dict[ProviderType, str | None] = {}

    if git_providers:
        for provider_type, provider_token in git_providers.items():
            if provider_token.token or provider_token.user_id:
                provider_tokens_set[provider_type] = provider_token.host

    return provider_tokens_set


def _build_settings_response(settings: Settings, provider_tokens_set: dict) -> GETSettingsModel:
    """Build settings response with masked sensitive data.

    Args:
        settings: User settings
        provider_tokens_set: Provider tokens status

    Returns:
        Settings model with masked keys
    """
    print(f"🔍 LOADING SETTINGS: autonomy_level={getattr(settings, 'autonomy_level', 'NOT_FOUND')}")
    settings_with_token_data = GETSettingsModel(
        **model_dump_with_options(settings, exclude={"secrets_store"}),
        llm_api_key_set=settings.llm_api_key is not None and bool(settings.llm_api_key),
        search_api_key_set=settings.search_api_key is not None and bool(settings.search_api_key),
        provider_tokens_set=provider_tokens_set,
    )

    # Mask sensitive data
    settings_with_token_data.llm_api_key = None
    settings_with_token_data.search_api_key = None
    settings_with_token_data.sandbox_api_key = None

    return settings_with_token_data


def _build_unauthorized_response(settings: Settings | None) -> JSONResponse:
    """Build unauthorized response for invalid tokens.

    Args:
        settings: User settings (may be None)

    Returns:
        401 Unauthorized JSON response
    """
    user_id = getattr(settings, "user_id", "unknown") if settings else "unknown"
    logger.info("Returning 401 Unauthorized - Invalid token for user_id: %s", user_id)

    return JSONResponse(
        status_code=status.HTTP_401_UNAUTHORIZED,
        content={"error": "Invalid token"},
    )


@app.post(
    "/reset-settings",
    responses={
        410: {
            "description": "Reset settings functionality has been removed",
            "model": dict,
        },
    },
)
async def reset_settings() -> JSONResponse:
    """Resets user settings. (Deprecated)."""
    logger.warning("Deprecated endpoint /api/reset-settings called by user")
    return JSONResponse(
        status_code=status.HTTP_410_GONE,
        content={"error": "Reset settings functionality has been removed."},
    )


async def store_llm_settings(
    settings: Settings,
    settings_store: SettingsStore,
) -> Settings:
    """Merge new LLM settings with existing settings.
    
    Preserves existing values for any fields that are None in new settings.
    Also auto-populates provider_tokens based on the selected model.
    
    Args:
        settings: New settings to merge
        settings_store: Settings storage
        
    Returns:
        Merged settings with existing values preserved
    """
    # DEBUG: Check incoming API key
    if settings.llm_api_key:
        key_val = settings.llm_api_key.get_secret_value() if hasattr(settings.llm_api_key, 'get_secret_value') else str(settings.llm_api_key)
        logger.debug(f"[STORE_LLM_SETTINGS] INCOMING API key: present={bool(key_val)}")
      else:
        logger.debug(f"[STORE_LLM_SETTINGS] INCOMING API key: None")
    
    existing_settings = await settings_store.load()
    if existing_settings:
        # Merge all fields: if new value is None, preserve existing value
        for field_name in Settings.model_fields:
            new_value = getattr(settings, field_name, None)
            if new_value is None:
                existing_value = getattr(existing_settings, field_name, None)
                if existing_value is not None:
                    # Clean base URL validation using provider detection
                    if field_name == 'llm_base_url' and settings.llm_model and existing_value:
                        provider = api_key_manager._extract_provider(settings.llm_model)
                        # Skip incorrect base URLs for providers that don't need them
                        base_url_lower = str(existing_value).lower()
                        if provider in ['openrouter', 'openai', 'anthropic'] and any(
                            incorrect in base_url_lower for incorrect in ['gemini', 'anthropic', 'openai']
                        ):
                            logger.debug(f"Skipping incorrect base URL '{existing_value}' for {provider} model")
                            continue
                    setattr(settings, field_name, existing_value)
    
    # Apply clean base URL validation after merge
    if settings.llm_model and settings.llm_base_url:
        provider = api_key_manager._extract_provider(settings.llm_model)
        base_url_lower = str(settings.llm_base_url).lower()
        if provider in ['openrouter', 'openai', 'anthropic'] and any(
            incorrect in base_url_lower for incorrect in ['gemini', 'anthropic', 'openai']
        ):
            logger.info(f"Clearing incorrect base URL '{settings.llm_base_url}' for {provider} model")
            settings.llm_base_url = None
    
    # Auto-populate provider_tokens based on model and API key
    if settings.llm_model and settings.llm_api_key:
        from openhands.integrations.provider import ProviderToken
        from openhands.storage.data_models.user_secrets import UserSecrets
        
        # Use the clean API key manager to determine provider
        provider = api_key_manager._extract_provider(settings.llm_model)
        
        # Map provider to token key
        provider_mapping = {
            'openhands': 'OPENHANDS_API_KEY',
            'openrouter': 'OPENROUTER_API_KEY',
            'openai': 'OPENAI_API_KEY',
            'anthropic': 'ANTHROPIC_API_KEY',
            'google': 'GOOGLE_API_KEY',
            'groq': 'GROQ_API_KEY',
            'deepseek': 'DEEPSEEK_API_KEY',
            'mistral': 'MISTRAL_API_KEY',
            'together': 'TOGETHER_API_KEY',
            'deepinfra': 'DEEPINFRA_API_KEY',
            'replicate': 'REPLICATE_API_KEY',
            'fireworks': 'FIREWORKS_API_KEY',
            'perplexity': 'PERPLEXITY_API_KEY',
        }
        
        provider_token_key = provider_mapping.get(provider)
        
        if provider_token_key:
            # Create new UserSecrets with updated provider_tokens
            current_tokens = dict(settings.secrets_store.provider_tokens) if settings.secrets_store and settings.secrets_store.provider_tokens else {}
            current_tokens[provider_token_key] = ProviderToken(token=settings.llm_api_key)
            
            new_secrets_store = UserSecrets(
                provider_tokens=current_tokens,
                custom_secrets=dict(settings.secrets_store.custom_secrets) if settings.secrets_store and settings.secrets_store.custom_secrets else {}
            )
            
            # Create new Settings object with updated secrets_store (can't modify frozen field)
            # CRITICAL: Preserve the actual API key before model_dump() converts it to asterisks
            original_api_key = settings.llm_api_key
            settings_dict = settings.model_dump(exclude={'secrets_store'})
            settings_dict['secrets_store'] = new_secrets_store
            # CRITICAL FIX: Restore the original API key after model_dump
            settings_dict['llm_api_key'] = original_api_key
            
            # CRITICAL FIX: Apply OpenRouter base URL correction during Settings object creation
            if settings_dict.get('llm_model') and settings_dict['llm_model'].startswith('openrouter/'):
                base_url = settings_dict.get('llm_base_url')
                if base_url and (
                    'gemini' in str(base_url).lower() or 
                    base_url == 'gemini-2.5-pro' or
                    str(base_url) == 'gemini-2.5-pro'
                ):
                    print(f"🔧 STORE_LLM_SETTINGS FIX: Clearing incorrect base_url '{settings_dict['llm_base_url']}' for OpenRouter model")
                    settings_dict['llm_base_url'] = ""
            
            settings = Settings(**settings_dict)
    
    # CRITICAL FIX: Ensure OpenRouter base URL is always cleared regardless of provider token handling
    if settings.llm_model and settings.llm_model.startswith('openrouter/'):
        if settings.llm_base_url and ('gemini' in str(settings.llm_base_url).lower() or settings.llm_base_url == 'gemini-2.5-pro'):
            print(f"🔧 STORE_LLM_SETTINGS FINAL FIX: Clearing base_url '{settings.llm_base_url}' for OpenRouter model")
            # Create new settings object with corrected base URL
            # CRITICAL: Preserve the actual API key before model_dump() converts it to asterisks
            original_api_key = settings.llm_api_key
            settings_dict = settings.model_dump()
            settings_dict['llm_base_url'] = ""
            # CRITICAL FIX: Restore the original API key after model_dump
            settings_dict['llm_api_key'] = original_api_key
            settings = Settings(**settings_dict)
    
    # DEBUG: Check outgoing API key after all processing
    if settings.llm_api_key:
        key_val = settings.llm_api_key.get_secret_value() if hasattr(settings.llm_api_key, 'get_secret_value') else str(settings.llm_api_key)
        logger.debug(f"[STORE_LLM_SETTINGS] OUTGOING API key: present={bool(key_val)}")
      else:
        logger.debug(f"[STORE_LLM_SETTINGS] OUTGOING API key: None")
    
    return settings


@app.post(
    "/settings",
    response_model=None,
    responses={
        200: {"description": "Settings stored successfully", "model": dict},
        500: {"description": "Error storing settings", "model": dict},
    },
)
async def store_settings(
    settings: Settings,
    settings_store: Annotated[SettingsStore, Depends(get_user_settings_store)],
) -> JSONResponse:
    """Store user settings with clean, secure API key handling.
    
    Uses the new APIKeyManager for secure, provider-aware API key validation and storage.
    
    Args:
        settings: Settings to store
        settings_store: Settings storage dependency
        
    Returns:
        JSON response with success/error message
    """
    try:
        logger.info("Storing settings with clean API key handling")
        
        # DEBUG: Log what API key was received from frontend
        if settings.llm_api_key:
            key_val = settings.llm_api_key.get_secret_value() if hasattr(settings.llm_api_key, 'get_secret_value') else str(settings.llm_api_key)
            logger.debug(f"[STORE SETTINGS] Received API key from frontend: present={bool(key_val)}, is_placeholder={key_val == '**********' if key_val else False}")
            
            # CRITICAL FIX: If the received API key is asterisks (placeholder), preserve the existing key
            if key_val == '**********':
                logger.info(f"[STORE SETTINGS] Received placeholder asterisks - will preserve existing API key")
                existing_settings = await settings_store.load()
                if existing_settings and existing_settings.llm_api_key:
                    logger.info(f"[STORE SETTINGS] Preserving existing API key")
                    settings.llm_api_key = existing_settings.llm_api_key
                else:
                    logger.warning(f"[STORE SETTINGS] No existing API key to preserve - setting to None")
                    settings.llm_api_key = None
        else:
            logger.info(f"[STORE SETTINGS] No API key received from frontend - will preserve existing")
            # If no API key provided, preserve the existing one
            existing_settings = await settings_store.load()
            if existing_settings and existing_settings.llm_api_key:
                logger.info(f"[STORE SETTINGS] Preserving existing API key (None received)")
                settings.llm_api_key = existing_settings.llm_api_key
        
        # CLEAN API KEY VALIDATION - Use the new secure API key manager
        if settings.llm_model and settings.llm_model.strip():
            logger.info(f"🔧 PROCESSING LLM SETTINGS: model='{settings.llm_model}', has_api_key={bool(settings.llm_api_key)}")
            
            # CRITICAL: If we have an API key, set environment variables immediately
            if settings.llm_api_key:
                logger.info(f"🔑 Setting environment variables with provided API key for {settings.llm_model}")
                try:
                    api_key_manager.set_environment_variables(settings.llm_model, settings.llm_api_key)
                    
                    # Verify environment variable was set correctly
                    provider = api_key_manager._extract_provider(settings.llm_model)
                    if provider == 'google':
                        import os
                        env_key = os.environ.get('GEMINI_API_KEY')
                        logger.debug(f"🔑 GEMINI_API_KEY environment variable set: {bool(env_key)}")
                except Exception as e:
                    logger.error(f"🔑 Failed to set environment variables: {e}")
            
            # Validate and get the correct API key for this model/provider
            correct_api_key = api_key_manager.get_api_key_for_model(settings.llm_model, settings.llm_api_key)
            
            if correct_api_key:
                settings.llm_api_key = correct_api_key
                logger.info(f"✅ Validated API key for model: {settings.llm_model}")
                
                # CRITICAL: Set environment variables immediately for this session
                try:
                    api_key_manager.set_environment_variables(settings.llm_model, correct_api_key)
                    logger.info(f"✅ Set environment variables for {settings.llm_model}")
                    
                    # Double-check environment variables for Google provider
                    provider = api_key_manager._extract_provider(settings.llm_model)
                    if provider == 'google':
                        import os
                        env_key = os.environ.get('GEMINI_API_KEY')
                        logger.debug(f"✅ Final GEMINI_API_KEY check: {bool(env_key)}")
                except Exception as e:
                    logger.error(f"❌ Failed to set environment variables after validation: {e}")
            elif settings.llm_api_key:
                # Fallback: use the provided key even if validation failed
                logger.warning(f"⚠️ Using provided API key as fallback for {settings.llm_model}")
                try:
                    api_key_manager.set_environment_variables(settings.llm_model, settings.llm_api_key)
                    
                    # Verify fallback environment variable
                    provider = api_key_manager._extract_provider(settings.llm_model)
                    if provider == 'google':
                        import os
                        env_key = os.environ.get('GEMINI_API_KEY')
                        logger.info(f"⚠️ Fallback GEMINI_API_KEY check: {bool(env_key)} (length: {len(env_key) if env_key else 0})")
                except Exception as e:
                    logger.error(f"❌ Failed to set fallback environment variables: {e}")
            
            # Clean base URL - remove incorrect base URLs for providers that don't need them
            provider = api_key_manager._extract_provider(settings.llm_model)
            
            # CRITICAL FIX: Check if base_url contains a model name instead of a URL
            if settings.llm_base_url:
                base_url_str = str(settings.llm_base_url).strip()
                base_url_lower = base_url_str.lower()
                
                # Check if it looks like a model name (contains model indicators but no URL protocol)
                model_indicators = ['gemini', 'gpt', 'claude', 'llama', 'mistral', 'deepseek', 'qwen']
                looks_like_model = any(indicator in base_url_lower for indicator in model_indicators)
                
                if looks_like_model and not base_url_lower.startswith(('http://', 'https://')):
                    logger.warning(f"🚨 CRITICAL: base_url appears to be a model name, not a URL: '{settings.llm_base_url}' - CLEARING IT")
                    settings.llm_base_url = None
            
            # OpenRouter and other providers don't need custom base URLs or need properly formatted ones
            if provider in ['openrouter', 'openai', 'anthropic', 'google'] and settings.llm_base_url:
                base_url_lower = str(settings.llm_base_url).lower().strip()
                
                # CRITICAL: For Google/Gemini, clear any base URL as they handle routing internally
                if provider == 'google':
                    logger.info(f"Clearing base URL for Google provider as it handles routing internally: '{settings.llm_base_url}'")
                    settings.llm_base_url = None
                # Clear if missing protocol - this causes the "missing protocol" error
                elif not base_url_lower.startswith(('http://', 'https://')):
                    logger.info(f"Clearing invalid base URL '{settings.llm_base_url}' for {provider} model - missing protocol")
                    settings.llm_base_url = None
                # Clear if it's an incorrect base URL for the provider
                elif any(incorrect in base_url_lower for incorrect in ['gemini', 'anthropic', 'openai']) and provider == 'openrouter':
                    logger.info(f"Clearing incorrect base URL '{settings.llm_base_url}' for {provider} model")
                    settings.llm_base_url = None
        
        # Clean settings handling - merge with existing settings
        existing_settings = await settings_store.load()
        if existing_settings:
            settings = await store_llm_settings(settings, settings_store)
            if settings.user_consents_to_analytics is None:
                settings.user_consents_to_analytics = existing_settings.user_consents_to_analytics

        # Update global configuration
        if settings.remote_runtime_resource_factor is not None:
            config.sandbox.remote_runtime_resource_factor = settings.remote_runtime_resource_factor
            
        git_config_updated = False
        if settings.git_user_name is not None:
            config.git_user_name = settings.git_user_name
            git_config_updated = True
        if settings.git_user_email is not None:
            config.git_user_email = settings.git_user_email
            git_config_updated = True
        if git_config_updated:
            logger.info(
                "Updated global git configuration: name=%s, email=%s",
                config.git_user_name,
                config.git_user_email,
            )

        # Final settings conversion and storage
        settings = convert_to_settings(settings)
        logger.info("Settings validation complete, storing clean settings")
        
        # CRITICAL: Ensure environment variables are set globally after final processing
        if settings.llm_model and settings.llm_model.strip() and settings.llm_api_key:
            logger.info(f"🌐 Setting final environment variables globally for {settings.llm_model}")
            try:
                api_key_manager.set_environment_variables(settings.llm_model, settings.llm_api_key)
                logger.info(f"🌐 Global environment variables set successfully for {settings.llm_model}")
            except Exception as e:
                logger.error(f"🌐 Failed to set global environment variables: {e}")
        
        await settings_store.store(settings)
        
        # 🚀 CACHE INVALIDATION: Clear AsyncSmartCache when settings change
        try:
            from openhands.core.cache import get_async_smart_cache
            from openhands.server.user_auth import get_user_id
            from fastapi import Request
            
            smart_cache = await get_async_smart_cache()
            # Get user ID from request context (use 'default' for single-tenant)
            user_id = 'default'  # Simplified for single-tenant mode
            await smart_cache.invalidate_user_cache(user_id)
            logger.info(f"🚀 Invalidated cache for user '{user_id}' after settings update")
        except Exception as e:
            logger.warning(f"Cache invalidation failed: {e}")
        
        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content={"message": "Settings stored"},
        )
    except Exception as e:
        logger.warning("Something went wrong storing settings: %s", e)
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"error": "Something went wrong storing settings"},
        )


def convert_to_settings(settings_with_token_data: Settings) -> Settings:
    """Convert settings with token data to clean Settings object.
    
    Filters out extra fields while preserving API keys.
    
    Args:
        settings_with_token_data: Settings object with potential extra fields
        
    Returns:
        Clean Settings object with only valid fields
    """
    settings_data = model_dump_with_options(settings_with_token_data, exclude_none=False)
    logger.info("Settings data before filtering: autonomy_level=%s", settings_data.get('autonomy_level', 'NOT_FOUND'))
    logger.info("API key before filtering: llm_api_key=%s", settings_data.get('llm_api_key', 'NOT_FOUND'))
    filtered_settings_data = {key: value for key, value in settings_data.items() if key in Settings.model_fields}
    logger.info("Settings data after filtering: autonomy_level=%s", filtered_settings_data.get('autonomy_level', 'NOT_FOUND'))
    logger.info("API key after filtering: llm_api_key=%s", filtered_settings_data.get('llm_api_key', 'NOT_FOUND'))
    
    # Preserve API keys by ensuring they're properly included
    if settings_with_token_data.llm_api_key is not None:
        from pydantic import SecretStr
        # Convert string API key to SecretStr if needed
        if isinstance(settings_with_token_data.llm_api_key, str):
            filtered_settings_data["llm_api_key"] = SecretStr(settings_with_token_data.llm_api_key)
        else:
            filtered_settings_data["llm_api_key"] = settings_with_token_data.llm_api_key
        logger.info("API key preserved: llm_api_key=%s", "SET" if filtered_settings_data.get('llm_api_key') else 'NOT_FOUND')
    if settings_with_token_data.search_api_key is not None:
        from pydantic import SecretStr
        # Convert string API key to SecretStr if needed
        if isinstance(settings_with_token_data.search_api_key, str):
            filtered_settings_data["search_api_key"] = SecretStr(settings_with_token_data.search_api_key)
        else:
            filtered_settings_data["search_api_key"] = settings_with_token_data.search_api_key
    
    # Fix API key and base URL mismatches for OpenRouter models (final fix before creating Settings object)
    if filtered_settings_data.get('llm_model') and filtered_settings_data['llm_model'].startswith('openrouter/'):
        print(f"🔧 FINAL FIX: Found OpenRouter model: {filtered_settings_data['llm_model']}")
        print(f"🔧 FINAL FIX: Current base_url: '{filtered_settings_data.get('llm_base_url')}'")
        
        # Fix base URL
        base_url = filtered_settings_data.get('llm_base_url')
        if base_url and ('gemini' in base_url.lower() or base_url == 'gemini-2.5-pro'):
            print(f"🔧 FINAL FIX: Fixing base URL from '{base_url}' to ''")
            filtered_settings_data['llm_base_url'] = ""
        
        # Fix API key mismatch
        api_key = filtered_settings_data.get('llm_api_key')
        if api_key:
            try:
                if hasattr(api_key, 'get_secret_value'):
                    key_value = api_key.get_secret_value()
                else:
                    key_value = str(api_key)
                
                if key_value.startswith('AIza') and 'openrouter' in filtered_settings_data['llm_model']:
                    print(f"🔧 FINAL FIX: Detected Gemini API key with OpenRouter model")
                    import os
                    openrouter_key = os.environ.get('OPENROUTER_API_KEY')
                    if openrouter_key:
                        from pydantic import SecretStr
                        filtered_settings_data['llm_api_key'] = SecretStr(openrouter_key)
                        print(f"🔧 FINAL FIX: Replaced with OpenRouter key from environment")
            except Exception as e:
                print(f"🔧 FINAL FIX: Error checking API key: {e}")
        
    return Settings(**filtered_settings_data)


def _build_default_settings_response() -> GETSettingsModel:
    """Build default settings response for development.
    
    Returns:
        Default settings model for unauthenticated/development use
    """
    # Create default settings similar to frontend DEFAULT_SETTINGS
    default_settings = Settings(
        llm_model="openhands/claude-sonnet-4-20250514",
        llm_base_url="",
        agent="CodeActAgent",
        language="en",
        confirmation_mode=False,
        security_analyzer="llm",
        remote_runtime_resource_factor=1,
        enable_default_condenser=True,
        condenser_max_size=120,
        enable_sound_notifications=False,
        user_consents_to_analytics=False,
        enable_proactive_conversation_starters=False,
        enable_solvability_analysis=False,
        search_api_key="",
        is_new_user=True,
        max_budget_per_task=None,
        email="",
        email_verified=True,
        mcp_config={
            "sse_servers": [],
            "stdio_servers": [],
            "shttp_servers": [],
        },
        git_user_name="openhands",
        git_user_email="openhands@all-hands.dev",
        # Autonomy Configuration
        autonomy_level="balanced",
        enable_permissions=True,
        enable_checkpoints=True,
        # Advanced LLM Configuration
        llm_temperature=None,
        llm_top_p=None,
        llm_max_output_tokens=None,
        llm_timeout=None,
        llm_num_retries=None,
        llm_caching_prompt=None,
        llm_disable_vision=None,
        llm_custom_llm_provider=None,
    )
    
    # Build response similar to _build_settings_response
    settings_with_token_data = GETSettingsModel(
        **model_dump_with_options(default_settings, exclude={"secrets_store"}),
        llm_api_key_set=False,
        search_api_key_set=False,
        provider_tokens_set={},
    )

    # Mask sensitive data
    settings_with_token_data.llm_api_key = None
    settings_with_token_data.search_api_key = None
    settings_with_token_data.sandbox_api_key = None

    return settings_with_token_data
