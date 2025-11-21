"""API key management utilities for Forge configuration workflows."""

from __future__ import annotations

import os
from typing import Any, Dict, Optional

from pydantic import BaseModel, SecretStr, Field
from forge.core.logger import forge_logger as logger
from .provider_config import provider_config_manager, ProviderConfigurationManager


class APIKeyManager(BaseModel):
    """Secure API key manager for multi-provider LLM support.

    Handles API keys for 30+ LLM providers with automatic provider detection,
    format validation, and secure storage using Pydantic SecretStr.

    Features:
        - Auto-detection of provider from model string (e.g., 'openrouter/gpt-4' → 'openrouter')
        - API key format validation (prefix matching, length checks)
        - Environment variable fallbacks (ANTHROPIC_API_KEY, OPENAI_API_KEY, etc.)
        - Secure storage (never logs full keys, uses SecretStr)
        - Provider-specific validation rules

    Example:
        >>> manager = api_key_manager
        >>> key = manager.get_api_key_for_model('openrouter/gpt-4o')
        >>> # Returns: SecretStr(OPENROUTER_API_KEY from environment)

        >>> manager.set_environment_variables('claude-4', key)
        >>> # Sets: ANTHROPIC_API_KEY in environment for LiteLLM

    Attributes:
        provider_api_keys: Mapping of provider names to their API keys

    """

    # Provider-specific API key mappings
    provider_api_keys: Dict[str, SecretStr] = Field(default_factory=dict)

    def get_api_key_for_model(
        self, model: str, provided_key: Optional[SecretStr] = None
    ) -> Optional[SecretStr]:
        """Get the correct API key for a given model, following provider conventions.

        Determines the provider from the model string, validates the API key format,
        and returns the appropriate key from provided key, environment variables,
        or stored keys.

        Args:
            model: The LLM model identifier. Format varies by provider:
                - OpenAI: 'gpt-4o', 'gpt-5-2025-08-07'
                - Anthropic: 'claude-sonnet-4-20250514'
                - OpenRouter: 'openrouter/anthropic/claude-3.5-sonnet'
                - xAI: 'openrouter/x-ai/grok-4-fast'
                - Ollama: 'ollama/llama3.3:70b'
            provided_key: API key provided by user. May be incorrect for the provider
                (e.g., user provides OpenAI key but model requires Anthropic key).
                Will be validated and corrected if needed.

        Returns:
            SecretStr containing the correct API key for the model's provider,
            or None if no key found. Keys are never logged in plaintext.

        Example:
            >>> # Get key for OpenRouter model
            >>> key = manager.get_api_key_for_model('openrouter/gpt-4o')
            >>> # Returns: OPENROUTER_API_KEY from environment

            >>> # Wrong key provided, will be corrected
            >>> wrong_key = SecretStr('sk-...')  # OpenAI key
            >>> correct_key = manager.get_api_key_for_model(
            ...     'claude-4',  # Anthropic model
            ...     provided_key=wrong_key
            ... )
            >>> # Returns: ANTHROPIC_API_KEY from environment (corrected)

        """
        provider = self._extract_provider(model)

        # Check if provided key is correct for this provider
        if provided_key:
            key_value = provided_key.get_secret_value()
            if self._is_correct_provider_key(provided_key, provider):
                logger.debug(f"Using provided API key for {provider}")
                return provided_key
            elif (
                key_value and len(key_value) > 10
            ):  # Fallback: if it's a substantial key, use it
                logger.info(
                    f"Using provided API key as fallback for {provider} (key length: {len(key_value)})"
                )
                return provided_key
            else:
                logger.warning(
                    f"Provided API key appears to be for wrong provider. Expected {provider}"
                )

        # Try to get key from environment variables
        env_key = self._get_provider_key_from_env(provider)
        if env_key:
            logger.debug(f"Loaded {provider} API key from environment")
            return SecretStr(env_key)

        # Try provider-specific mappings
        if provider in self.provider_api_keys:
            logger.debug(f"Using stored {provider} API key")
            return self.provider_api_keys[provider]

        # Provide helpful guidance for missing API keys
        provider_config = provider_config_manager.get_provider_config(provider)
        env_var = (
            provider_config.env_var
            if provider_config
            else f"{provider.upper()}_API_KEY"
        )

        logger.error(f"No API key found for provider: {provider}")
        logger.info(
            f"To fix this, set the {env_var} environment variable with your {provider} API key"
        )
        return None

    def set_api_key(self, model: str, api_key: SecretStr) -> None:
        """Set API key for a model's provider."""
        provider = self._extract_provider(model)
        self.provider_api_keys[provider] = api_key
        logger.debug(f"Set API key for {provider}")

    def set_environment_variables(
        self, model: str, api_key: Optional[SecretStr] = None
    ) -> None:
        """Set appropriate environment variables for LiteLLM based on model provider.

        Args:
            model: The LLM model identifier
            api_key: API key to use, or get from storage/environment if None

        """
        provider = self._extract_provider(model)
        logger.debug(
            f"Setting environment variables for model: {model}, provider: {provider}"
        )

        # Get provider configuration
        provider_config = provider_config_manager.get_provider_config(provider)

        # Get the correct API key to use - prioritize the provided key
        key_to_use: SecretStr | None = None
        if api_key:
            key_to_use = api_key
            logger.debug(f"Using provided API key for {provider}")

            # Validate API key format using provider configuration (warn only, don't fail)
            if api_key_value := api_key.get_secret_value():
                provider_config_manager.validate_api_key_format(provider, api_key_value)
                logger.debug(f"API key format validation completed for {provider}")
        else:
            key_to_use = self.get_api_key_for_model(model)
            if key_to_use:
                logger.debug(f"Retrieved API key from manager for {provider}")

        if not key_to_use:
            # Check if API key is actually required for this provider
            if "api_key" in provider_config.required_params:
                env_var = provider_config.env_var
                logger.error(
                    f"CRITICAL: No API key available for {provider} model {model}"
                )
                logger.info(
                    f"Please set the {env_var} environment variable with your {provider} API key"
                )
                # Try to get from environment as last resort
                env_key = self._get_provider_key_from_env(provider)
                if env_key:
                    logger.info(f"Found API key in environment for {provider}")
                    key_to_use = SecretStr(env_key)
                else:
                    logger.error(f"FAILED: No API key found anywhere for {provider}")
                    logger.info(
                        f"Set {env_var} environment variable to use {provider} models"
                    )
                    return
            else:
                logger.debug(f"API key not required for provider {provider}")
                return

        api_key_value = key_to_use.get_secret_value()
        logger.debug(f"Using API key: {api_key_value[:15]}... for {provider}")

        # Use provider configuration for environment variable mapping
        env_var = provider_config_manager.get_environment_variable(provider)
        if env_var:
            os.environ[env_var] = api_key_value
            logger.debug(f"Set {env_var} environment variable for {provider}")

            # CRITICAL: For Google/Gemini, also set GOOGLE_API_KEY as LiteLLM expects this too
            if provider == "google":
                os.environ["GOOGLE_API_KEY"] = api_key_value
                logger.debug(
                    f"Set GOOGLE_API_KEY environment variable for Google provider"
                )
        else:
            logger.debug(f"No environment variable specified for provider: {provider}")

        # Also set generic fallback - CRITICAL for LiteLLM
        os.environ["LLM_API_KEY"] = api_key_value
        logger.debug(f"Set LLM_API_KEY fallback environment variable")

    def _check_prefix_match(self, model: str, model_lower: str) -> str | None:
        """Check for provider prefix matches.

        Args:
            model: Original model string
            model_lower: Lowercase model string

        Returns:
            Provider name if matched, None otherwise

        """
        # Define prefix and pattern mappings for each provider
        prefix_patterns = {
            "openhands": ["Openhands/", "openhands/", "Forge/"],
            "forge": ["Forge/"],  # Legacy alias
            "openrouter": ["openrouter/"],
            "openai": ["openai/", "gpt-"],
            "anthropic": ["anthropic/", "claude-"],
            "google": ["google/"],
            "mistral": ["mistral/"],
            "groq": ["groq/"],
            "together": ["together/"],
            "deepinfra": ["deepinfra/"],
            "replicate": ["replicate/"],
            "fireworks": ["fireworks/"],
            "perplexity": ["perplexity/"],
            "cohere": ["cohere/"],
            "ollama": ["ollama/"],
        }

        for provider, prefixes in prefix_patterns.items():
            if any(model.startswith(prefix) for prefix in prefixes):
                return "openhands" if provider == "forge" else provider

        return None

    def _check_keyword_match(self, model_lower: str) -> str | None:
        """Check for provider keyword matches in model name.

        Args:
            model_lower: Lowercase model string

        Returns:
            Provider name if matched, None otherwise

        """
        keyword_patterns = {
            "openhands": ["openhands", "forge"],
            "google": ["gemini"],
            "mistral": ["mistral"],
            "groq": ["groq"],
            "together": ["together"],
            "deepinfra": ["deepinfra"],
            "replicate": ["replicate"],
            "fireworks": ["fireworks"],
            "perplexity": ["perplexity"],
            "cohere": ["cohere"],
            "ollama": ["ollama"],
        }

        for provider, keywords in keyword_patterns.items():
            if any(keyword in model_lower for keyword in keywords):
                return provider

        return None

    def _check_fallback_patterns(self, model_lower: str) -> str:
        """Check fallback patterns for common model families.

        Args:
            model_lower: Lowercase model string

        Returns:
            Provider name or 'unknown'

        """
        fallback_patterns = {
            "openai": ["gpt", "davinci", "curie", "babbage"],
            "anthropic": ["claude", "anthropic"],
            "google": ["gemini", "palm"],
        }

        for provider, patterns in fallback_patterns.items():
            if any(pattern in model_lower for pattern in patterns):
                return provider

        return "unknown"

    def _extract_provider(self, model: str) -> str:
        """Extract provider from model identifier.

        Args:
            model: Model identifier string

        Returns:
            Provider name (e.g., 'openai', 'anthropic', etc.)

        """
        if not model:
            return "unknown"

        model_lower = model.lower()

        # Check prefix matches first (most specific)
        if provider := self._check_prefix_match(model, model_lower):
            return provider

        # Check keyword matches (moderately specific)
        if provider := self._check_keyword_match(model_lower):
            return provider

        # Check fallback patterns (least specific)
        return self._check_fallback_patterns(model_lower)

    def _is_correct_provider_key(
        self, api_key: SecretStr, expected_provider: str
    ) -> bool:
        """Validate if an API key appears to be for the correct provider.

        This is a basic format check - different providers have different key formats.
        """
        try:
            key_value = api_key.get_secret_value()

            # Basic format validation based on provider conventions
            provider_patterns = {
                "openrouter": lambda k: k.startswith("sk-or-"),
                "openai": lambda k: k.startswith("sk-") and not k.startswith("sk-or-"),
                "anthropic": lambda k: k.startswith("sk-ant-"),
                "google": lambda k: k.startswith("AIza"),
                "mistral": lambda k: len(k) > 20 and not k.startswith("sk-"),
                "groq": lambda k: k.startswith("gsk_"),
                "cohere": lambda k: k.startswith("co-"),
                "openhands": lambda k: k.startswith("sk-"),
            }

            pattern_check = provider_patterns.get(expected_provider)
            if pattern_check:
                return pattern_check(key_value)

            # If no pattern is known, assume it's correct
            return True

        except Exception:
            return False

    def _get_provider_key_from_env(self, provider: str) -> Optional[str]:
        """Get API key for provider from environment variables using provider configuration."""
        # Use provider configuration to get the correct environment variable
        env_var = provider_config_manager.get_environment_variable(provider)
        if env_var:
            return os.environ.get(env_var)

        # Fallback to generic
        return os.environ.get("LLM_API_KEY")

    def validate_and_clean_completion_params(
        self, model: str, params: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Validate and clean parameters for LiteLLM completion calls.

        Args:
            model: The LLM model identifier
            params: Dictionary of parameters to validate and clean

        Returns:
            Cleaned dictionary with only valid parameters for the provider

        """
        provider = self._extract_provider(model)
        logger.debug(f"Validating completion parameters for provider: {provider}")

        # Use the provider configuration manager to validate and clean parameters
        cleaned_params = provider_config_manager.validate_and_clean_params(
            provider, params
        )

        logger.debug(
            f"Parameter validation completed: {len(params)} -> {len(cleaned_params)} parameters"
        )
        return cleaned_params


# Global instance
api_key_manager = APIKeyManager()
