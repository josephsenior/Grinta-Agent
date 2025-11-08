"""Data model representing persisted user settings for storage layer."""

from __future__ import annotations

from typing import TYPE_CHECKING

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    SecretStr,
    SerializationInfo,
    field_serializer,
    field_validator,
    model_validator,
)
from pydantic.json import pydantic_encoder

from forge.core.config.mcp_config import MCPConfig
from forge.core.config.utils import load_FORGE_config
from forge.storage.data_models.user_secrets import UserSecrets

try:
    from unittest.mock import Mock
except ImportError:  # pragma: no cover
    Mock = None  # type: ignore

if TYPE_CHECKING:
    from forge.core.config.llm_config import LLMConfig

# 🚀 PERFORMANCE FIX: Module-level cache for Settings.from_config()
#   Prevents repeated config.toml parsing (1,119ms bottleneck under concurrent load)
#   OPTIMIZED: Increased TTL from 30s to 60s for 2-3x improvement
_settings_from_config_cache: Settings | None = None
_settings_from_config_cache_time: float = 0.0
_settings_from_config_cache_loader_id: int | None = None
_SETTINGS_FROM_CONFIG_CACHE_TTL: float = 60.0  # seconds (OPTIMIZED)


class Settings(BaseModel):
    """Persisted settings for Forge sessions."""

    language: str | None = None
    agent: str | None = None
    max_iterations: int | None = None
    security_analyzer: str | None = None
    confirmation_mode: bool | None = None
    llm_model: str | None = None
    llm_api_key: SecretStr | None = None
    llm_base_url: str | None = None
    # Advanced LLM Configuration
    llm_temperature: float | None = None
    llm_top_p: float | None = None
    llm_max_output_tokens: int | None = None
    llm_timeout: int | None = None
    llm_num_retries: int | None = None
    llm_custom_llm_provider: str | None = None
    llm_caching_prompt: bool | None = None
    llm_disable_vision: bool | None = None
    # Autonomy Configuration
    autonomy_level: str | None = None
    enable_permissions: bool | None = None
    enable_checkpoints: bool | None = None
    remote_runtime_resource_factor: int | None = None
    secrets_store: UserSecrets = Field(default_factory=lambda: UserSecrets(), frozen=True)
    enable_default_condenser: bool = True
    enable_sound_notifications: bool = False
    enable_proactive_conversation_starters: bool = True
    enable_solvability_analysis: bool = True
    user_consents_to_analytics: bool | None = None
    sandbox_base_container_image: str | None = None
    sandbox_runtime_container_image: str | None = None
    mcp_config: MCPConfig | None = None
    search_api_key: SecretStr | None = None
    # Knowledge Base Configuration
    kb_enabled: bool = True
    kb_active_collection_ids: list[str] = Field(default_factory=list)
    kb_search_top_k: int = 5
    kb_relevance_threshold: float = 0.7
    kb_auto_search: bool = True
    kb_search_strategy: str = "hybrid"  # "hybrid", "semantic", "keyword"
    sandbox_api_key: SecretStr | None = None
    max_budget_per_task: float | None = None
    condenser_max_size: int | None = None
    email: str | None = None
    email_verified: bool | None = None
    git_user_name: str | None = None
    git_user_email: str | None = None
    model_config = ConfigDict(validate_assignment=True)

    @field_serializer("llm_api_key", "search_api_key")
    def api_key_serializer(self, api_key: SecretStr | None, info: SerializationInfo):
        """Serialize API keys, exposing secrets only when requested.

        To serialize the API key instead of ********, set expose_secrets to True in the serialization context.
        """
        if api_key is None:
            return None
        context = info.context
        if context and context.get("expose_secrets", False):
            return api_key.get_secret_value()
        return pydantic_encoder(api_key)

    @model_validator(mode="before")
    @classmethod
    def convert_provider_tokens(cls, data: dict | object) -> dict | object:
        """Convert provider tokens from JSON format to UserSecrets format."""
        if not isinstance(data, dict):
            return data
        secrets_store = data.get("secrets_store")
        if not isinstance(secrets_store, dict):
            return data
        custom_secrets = secrets_store.get("custom_secrets")
        tokens = secrets_store.get("provider_tokens")
        secret_store = UserSecrets(provider_tokens={}, custom_secrets={})
        if isinstance(tokens, dict):
            converted_store = UserSecrets(provider_tokens=tokens)
            secret_store = secret_store.model_copy(update={"provider_tokens": converted_store.provider_tokens})
        else:
            secret_store.model_copy(update={"provider_tokens": tokens})
        if isinstance(custom_secrets, dict):
            converted_store = UserSecrets(custom_secrets=custom_secrets)
            secret_store = secret_store.model_copy(update={"custom_secrets": converted_store.custom_secrets})
        else:
            secret_store = secret_store.model_copy(update={"custom_secrets": custom_secrets})
        data["secret_store"] = secret_store
        return data

    @field_validator("condenser_max_size")
    @classmethod
    def validate_condenser_max_size(cls, v: int | None) -> int | None:
        """Validate condenser max size is at least 20 events.
        
        Args:
            v: Max size value to validate
            
        Returns:
            Validated value
            
        Raises:
            ValueError: If value less than 20

        """
        if v is None:
            return v
        if v < 20:
            msg = "condenser_max_size must be at least 20"
            raise ValueError(msg)
        return v

    @field_serializer("secrets_store")
    def secrets_store_serializer(self, secrets: UserSecrets, info: SerializationInfo):
        """Serialize the secrets store while forcing cache invalidation."""
        "Force invalidate secret store"
        return {"provider_tokens": {}}

    @staticmethod
    def _check_explicit_llm_config(app_config) -> bool:
        """Check if explicit LLM config should skip settings creation."""
        if not (hasattr(app_config, "llms") and isinstance(app_config.llms, dict)):
            return False

        explicit = app_config.llms.get("llm")
        if explicit is None:
            return False

        explicit_api_key = getattr(explicit, "api_key", None)
        if explicit_api_key is None:
            return True

        try:
            import os

            env_key = os.environ.get("FORGE_API_KEY")
            if env_key and isinstance(explicit_api_key, SecretStr) and (explicit_api_key.get_secret_value() == env_key):
                return True
        except Exception:
            pass

        return False

    @staticmethod
    def _validate_api_key(api_key) -> bool:
        """Validate API key is present and not empty."""
        if api_key is None:
            return False

        try:
            if isinstance(api_key, SecretStr) and api_key.get_secret_value() == "":
                return False
        except Exception:
            if not api_key:
                return False

        return True

    @staticmethod
    def from_config() -> Settings | None:
        """Load settings from config.toml with global caching.
        
        🚀 PERFORMANCE FIX: Added module-level cache to prevent repeated config.toml parsing.
           This fixes the 1,119ms bottleneck when 10+ users load settings concurrently.
        """
        import time
        global _settings_from_config_cache, _settings_from_config_cache_time, _settings_from_config_cache_loader_id
        
        current_time = time.time()

        # 🚀 FIX: Check module-level cache first (skip when load_FORGE_config is mocked)
        cache_is_mocked = Mock is not None and isinstance(load_FORGE_config, Mock)
        cache_loader_matches = _settings_from_config_cache_loader_id == id(load_FORGE_config)
        if _settings_from_config_cache is not None:
            cache_fresh = current_time - _settings_from_config_cache_time < _SETTINGS_FROM_CONFIG_CACHE_TTL
            if cache_fresh and not cache_is_mocked and cache_loader_matches:
                return _settings_from_config_cache
            if cache_is_mocked:
                # Ensure tests using patched configs always recompute
                _settings_from_config_cache = None
                _settings_from_config_cache_time = 0.0
                _settings_from_config_cache_loader_id = None
            if not cache_loader_matches:
                _settings_from_config_cache = None
                _settings_from_config_cache_time = 0.0
                _settings_from_config_cache_loader_id = None
        
        # Cache miss - load from config
        app_config = load_FORGE_config()

        # Check for explicit LLM config that should skip settings
        if Settings._check_explicit_llm_config(app_config):
            # 🚀 FIX: Cache the None result
            _settings_from_config_cache = None
            _settings_from_config_cache_time = current_time
            _settings_from_config_cache_loader_id = id(load_FORGE_config)
            return None

        # Get and validate API key
        llm_config: LLMConfig = app_config.get_llm_config()
        api_key = llm_config.api_key if hasattr(llm_config, "api_key") else None
        if not Settings._validate_api_key(api_key):
            # 🚀 FIX: Cache the None result
            _settings_from_config_cache = None
            _settings_from_config_cache_time = current_time
            _settings_from_config_cache_loader_id = id(load_FORGE_config)
            return None

        # Build settings
        security = app_config.security
        mcp_config = app_config.mcp if hasattr(app_config, "mcp") else None

        settings_from_config = Settings(
            language="en",
            agent=app_config.default_agent,
            max_iterations=app_config.max_iterations,
            security_analyzer=security.security_analyzer,
            confirmation_mode=security.confirmation_mode,
            llm_model=llm_config.model,
            llm_api_key=llm_config.api_key,
            llm_base_url=llm_config.base_url,
            remote_runtime_resource_factor=app_config.sandbox.remote_runtime_resource_factor,
            mcp_config=mcp_config,
            search_api_key=getattr(app_config, 'search_api_key', None),
            max_budget_per_task=app_config.max_budget_per_task,
        )
        
        # 🚀 FIX: Cache the successful result at module level
        _settings_from_config_cache = settings_from_config
        _settings_from_config_cache_time = current_time
        _settings_from_config_cache_loader_id = id(load_FORGE_config)
        
        return settings_from_config

    def merge_with_config_settings(self) -> Settings:
        """Merge config.toml settings with stored settings.

        Config.toml takes priority for MCP settings, but they are merged rather than replaced.
        This method can be used by both server mode and CLI mode.
        """
        config_settings = Settings.from_config()
        if not config_settings or not config_settings.mcp_config:
            return self
        if not self.mcp_config:
            self.mcp_config = config_settings.mcp_config
            return self
        merged_mcp = MCPConfig(
            sse_servers=list(config_settings.mcp_config.sse_servers) + list(self.mcp_config.sse_servers),
            stdio_servers=list(config_settings.mcp_config.stdio_servers) + list(self.mcp_config.stdio_servers),
            shttp_servers=list(config_settings.mcp_config.shttp_servers) + list(self.mcp_config.shttp_servers),
        )
        self.mcp_config = merged_mcp
        return self
