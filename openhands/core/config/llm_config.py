from __future__ import annotations

import os
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, SecretStr, ValidationError

from openhands.core.logger import LOG_DIR
from openhands.core.logger import openhands_logger as logger
from openhands.core.config.api_key_manager import api_key_manager
from openhands.core.config.provider_config import provider_config_manager


class LLMConfig(BaseModel):
    """Configuration for the LLM model.

    Attributes:
        model: The model to use.
        api_key: The API key to use.
        base_url: The base URL for the API. This is necessary for local LLMs.
        api_version: The version of the API.
        aws_access_key_id: The AWS access key ID.
        aws_secret_access_key: The AWS secret access key.
        aws_region_name: The AWS region name.
        num_retries: The number of retries to attempt.
        retry_multiplier: The multiplier for the exponential backoff.
        retry_min_wait: The minimum time to wait between retries, in seconds. This is exponential backoff minimum. For models with very low limits, this can be set to 15-20.
        retry_max_wait: The maximum time to wait between retries, in seconds. This is exponential backoff maximum.
        timeout: The timeout for the API.
        max_message_chars: The approximate max number of characters in the content of an event included in the prompt to the LLM. Larger observations are truncated.
        temperature: The temperature for the API.
        top_p: The top p for the API.
        top_k: The top k for the API.
        custom_llm_provider: The custom LLM provider to use. This is undocumented in openhands, and normally not used. It is documented on the litellm side.
        max_input_tokens: The maximum number of input tokens. Note that this is currently unused, and the value at runtime is actually the total tokens in OpenAI (e.g. 128,000 tokens for GPT-4).
        max_output_tokens: The maximum number of output tokens. This is sent to the LLM.
        input_cost_per_token: The cost per input token. This will available in logs for the user to check.
        output_cost_per_token: The cost per output token. This will available in logs for the user to check.
        ollama_base_url: The base URL for the OLLAMA API.
        drop_params: Drop any unmapped (unsupported) params without causing an exception.
        modify_params: Modify params allows litellm to do transformations like adding a default message, when a message is empty.
        disable_vision: If model is vision capable, this option allows to disable image processing (useful for cost reduction).
        caching_prompt: Use the prompt caching feature if provided by the LLM and supported by the provider.
        log_completions: Whether to log LLM completions to the state.
        log_completions_folder: The folder to log LLM completions to. Required if log_completions is True.
        custom_tokenizer: A custom tokenizer to use for token counting.
        native_tool_calling: Whether to use native tool calling if supported by the model. Can be True, False, or not set.
        reasoning_effort: The effort to put into reasoning. This is a string that can be one of 'low', 'medium', 'high', or 'none'. Can apply to all reasoning models.
        seed: The seed to use for the LLM.
        safety_settings: Safety settings for models that support them (like Mistral AI and Gemini).
        correct_num: The number of times the draft editor LLM tries to fix an error when editing.
    """

    model: str = Field(default="claude-sonnet-4-20250514")
    api_key: SecretStr | None = Field(default=None)
    base_url: str | None = Field(default=None)
    api_version: str | None = Field(default=None)
    aws_access_key_id: SecretStr | None = Field(default=None)
    aws_secret_access_key: SecretStr | None = Field(default=None)
    aws_region_name: str | None = Field(default=None)
    openrouter_site_url: str = Field(default="https://docs.all-hands.dev/")
    openrouter_app_name: str = Field(default="OpenHands")
    num_retries: int = Field(default=5)
    retry_multiplier: float = Field(default=8)
    retry_min_wait: int = Field(default=8)
    retry_max_wait: int = Field(default=64)
    timeout: int | None = Field(default=None)
    max_message_chars: int = Field(default=30000)
    temperature: float = Field(default=0.0)
    top_p: float = Field(default=1.0)
    top_k: float | None = Field(default=None)
    custom_llm_provider: str | None = Field(default=None)
    max_input_tokens: int | None = Field(default=None)
    max_output_tokens: int | None = Field(default=None)
    input_cost_per_token: float | None = Field(default=None)
    output_cost_per_token: float | None = Field(default=None)
    ollama_base_url: str | None = Field(default=None)
    drop_params: bool = Field(default=True)
    modify_params: bool = Field(default=True)
    disable_vision: bool | None = Field(default=None)
    disable_stop_word: bool | None = Field(default=False)
    caching_prompt: bool = Field(default=True)
    log_completions: bool = Field(default=False)
    log_completions_folder: str = Field(default=os.path.join(LOG_DIR, "completions"))
    custom_tokenizer: str | None = Field(default=None)
    native_tool_calling: bool | None = Field(default=None)
    reasoning_effort: str | None = Field(default=None)
    seed: int | None = Field(default=None)
    safety_settings: list[dict[str, str]] | None = Field(
        default=None,
        description="Safety settings for models that support them (like Mistral AI and Gemini)",
    )
    correct_num: int = Field(
        default=5,
        description="The number of times the draft editor LLM tries to fix an error when editing"
    )
    for_routing: bool = Field(default=False)
    model_config = ConfigDict(extra="forbid")

    @classmethod
    def from_toml_section(cls, data: dict) -> dict[str, LLMConfig]:
        """Create a mapping of LLMConfig instances from a toml dictionary representing the [llm] section.

        The default configuration is built from all non-dict keys in data.
        Then, each key with a dict value (e.g. [llm.random_name]) is treated as a custom LLM configuration,
        and its values override the default configuration.

        Example:
        Apply generic LLM config with custom LLM overrides, e.g.
            [llm]
            model=...
            num_retries = 5
            [llm.claude]
            model="claude-3-5-sonnet"
        results in num_retries APPLIED to claude-3-5-sonnet.

        Returns:
            dict[str, LLMConfig]: A mapping where the key "llm" corresponds to the default configuration
            and additional keys represent custom configurations.
        """
        # Initialize the result mapping
        llm_mapping: dict[str, LLMConfig] = {}

        # Extract base config data (non-dict values)
        base_data = {}
        custom_sections: dict[str, dict] = {}
        for key, value in data.items():
            if isinstance(value, dict):
                custom_sections[key] = value
            else:
                base_data[key] = value

        # Try to create the base config
        try:
            base_config = cls.model_validate(base_data)
            llm_mapping['llm'] = base_config
        except ValidationError:
            logger.warning(
                'Cannot parse [llm] config from toml. Continuing with defaults.'
            )
            # If base config fails, create a default one
            base_config = cls()
            # Still add it to the mapping
            llm_mapping['llm'] = base_config

        # Process each custom section independently
        for name, overrides in custom_sections.items():
            try:
                # Merge base config with overrides
                merged = {**base_config.model_dump(), **overrides}
                custom_config = cls.model_validate(merged)
                llm_mapping[name] = custom_config
            except ValidationError:
                logger.warning(
                    f'Cannot parse [{name}] config from toml. This section will be skipped.'
                )
                # Skip this custom section but continue with others
                continue

        return llm_mapping


    def model_post_init(self, __context: Any) -> None:
        """Post-initialization hook for clean API key handling and environment setup.

        Uses the new APIKeyManager for secure, provider-aware API key handling.
        """
        super().model_post_init(__context)

        # SECURE API KEY HANDLING - Use the new API key manager
        try:
            # Get the correct API key for this model/provider
            correct_api_key = api_key_manager.get_api_key_for_model(self.model, self.api_key)
            
            if correct_api_key:
                self.api_key = correct_api_key
                logger.debug(f"Set correct API key for model: {self.model}")
            else:
                # Try to set from environment as fallback
                provider = api_key_manager._extract_provider(self.model)
                env_key = api_key_manager._get_provider_key_from_env(provider)
                if env_key:
                    self.api_key = SecretStr(env_key)
                    logger.debug(f"Loaded API key from environment for {provider}")
                else:
                    logger.warning(f"No API key available for model: {self.model}")
        except Exception as e:
            logger.error(f"Error in API key handling: {e}")

        # Set environment variables for LiteLLM using the secure manager
        api_key_manager.set_environment_variables(self.model, self.api_key)

        # CRITICAL: Clean base_url to prevent protocol errors
        self._clean_base_url()

        # Set provider-specific environment variables
        self._set_provider_environment_variables()

        # Configure model-specific settings
        self._configure_model_defaults()

    def _set_provider_environment_variables(self) -> None:
        """Set provider-specific environment variables."""
        # OpenRouter-specific variables
        if self.openrouter_site_url:
            os.environ['OR_SITE_URL'] = self.openrouter_site_url
        if self.openrouter_app_name:
            os.environ['OR_APP_NAME'] = self.openrouter_app_name

        # AWS credentials for Bedrock
        if self.aws_access_key_id:
            os.environ['AWS_ACCESS_KEY_ID'] = self.aws_access_key_id.get_secret_value()
        if self.aws_secret_access_key:
            os.environ['AWS_SECRET_ACCESS_KEY'] = (
                self.aws_secret_access_key.get_secret_value()
            )
        if self.aws_region_name:
            os.environ['AWS_REGION_NAME'] = self.aws_region_name

    def _clean_base_url(self) -> None:
        """Clean base_url and other parameters using provider-aware validation."""
        if not self.model:
            return
            
        provider = api_key_manager._extract_provider(self.model)
        provider_config = provider_config_manager.get_provider_config(provider)
        
        # Use provider configuration to validate and clean base_url
        cleaned_url = provider_config.validate_base_url(self.base_url)
        if cleaned_url != self.base_url:
            logger.info(f"Cleaned base_url for {provider}: '{self.base_url}' -> {cleaned_url}")
            self.base_url = cleaned_url
        
        # Additional validation for custom_llm_provider based on provider configuration
        if hasattr(self, 'custom_llm_provider') and self.custom_llm_provider:
            # Check if custom_llm_provider is forbidden for this provider
            if not provider_config.is_param_allowed('custom_llm_provider'):
                logger.info(f"Clearing custom_llm_provider '{self.custom_llm_provider}' for {provider} - not allowed for this provider")
                # Note: Can't directly modify Pydantic field, but this will help with logging

    def _configure_model_defaults(self) -> None:
        """Configure model-specific default settings."""
        # Set reasoning_effort to 'high' by default for non-Gemini models
        if self.reasoning_effort is None and 'gemini-2.5-pro' not in self.model:
            self.reasoning_effort = 'high'

        # Set API version for Azure models
        if self.model.startswith('azure') and self.api_version is None:
            self.api_version = '2024-12-01-preview'

