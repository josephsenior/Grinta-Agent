"""LLM integration and communication layer.

Classes:
    LLM

Functions:
    retry_decorator
    completion
    init_model_info
    vision_is_active
    is_caching_prompt_active
"""

from __future__ import annotations

import copy
import os
import time
import warnings
from functools import partial
from typing import TYPE_CHECKING, Any, Callable, cast

import httpx
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from openhands.llm.metrics import Metrics
from openhands.llm.model_features import get_features
from openhands.utils.tenacity_stop import stop_if_should_exit

with warnings.catch_warnings():
    warnings.simplefilter("ignore")
    import litellm
import contextlib

from litellm import ModelInfo, PromptTokensDetails
from litellm import completion as litellm_completion
from litellm import completion_cost as litellm_completion_cost
from litellm.exceptions import (
    APIConnectionError,
    RateLimitError,
    ServiceUnavailableError,
)
from litellm.types.utils import CostPerToken, ModelResponse, Usage
from litellm.utils import create_pretrained_tokenizer

from openhands.core.exceptions import LLMNoResponseError
from openhands.core.logger import openhands_logger as logger
from openhands.core.message import Message
from openhands.llm.debug_mixin import DebugMixin
from openhands.llm.fn_call_converter import (
    STOP_WORDS,
    convert_fncall_messages_to_non_fncall_messages,
    convert_non_fncall_messages_to_fncall_messages,
)
from openhands.llm.retry_mixin import RetryMixin

if TYPE_CHECKING:
    from openhands.core.config import LLMConfig


# Create a standalone retry decorator for class-level decorators
def retry_decorator(**kwargs: Any) -> Callable:
    """Create a retry decorator for LLM completion calls."""
    num_retries = kwargs.get("num_retries", 3)
    retry_exceptions = kwargs.get("retry_exceptions", ())
    retry_min_wait = kwargs.get("retry_min_wait", 1.0)
    retry_max_wait = kwargs.get("retry_max_wait", 60.0)
    retry_multiplier = kwargs.get("retry_multiplier", 2.0)

    return retry(
        stop=stop_after_attempt(num_retries) | stop_if_should_exit(),
        reraise=True,
        retry=retry_if_exception_type(retry_exceptions),
        wait=wait_exponential(multiplier=retry_multiplier, min=retry_min_wait, max=retry_max_wait),
    )


__all__ = ["LLM"]
LLM_RETRY_EXCEPTIONS: tuple[type[Exception], ...] = (
    APIConnectionError,
    RateLimitError,
    ServiceUnavailableError,
    litellm.Timeout,
    litellm.InternalServerError,
    LLMNoResponseError,
)


class LLM(RetryMixin, DebugMixin):
    """Language Model abstraction layer with multi-provider support via LiteLLM.
    
    Provides a unified interface to 200+ LLM models from 30+ providers including
    OpenAI, Anthropic, Google, OpenRouter, xAI, and more. Handles retries, cost
    tracking, streaming, function calling, and provider-specific quirks.
    
    Features:
        - Multi-provider support via LiteLLM (OpenAI, Claude, Gemini, Grok, etc.)
        - Automatic retry with exponential backoff
        - Real-time cost tracking per request
        - Streaming token generation
        - Function calling (when model supports it)
        - Prompt caching (Claude models)
        - Vision support (GPT-4V, Claude 3.5+, Gemini)
        - Metrics collection (tokens, latency, costs)
    
    Example:
        >>> config = LLMConfig(
        ...     model='claude-sonnet-4-20250514',
        ...     api_key='sk-ant-...',
        ...     temperature=0.0
        ... )
        >>> llm = LLM(config=config, service_id='main')
        >>> response = llm.completion(
        ...     messages=[{'role': 'user', 'content': 'Hello!'}]
        ... )
        >>> print(response.choices[0].message.content)
        >>> print(f'Cost: ${llm.metrics.accumulated_cost:.2f}')
    
    Attributes:
        config: LLMConfig object with model, API key, and parameters
        service_id: Identifier for this LLM instance (for logging/metrics)
        metrics: Metrics object tracking costs, tokens, and latency
        model_info: ModelInfo from LiteLLM with capability details
        cost_metric_supported: Whether cost calculation is available for this model
    """

    def _setup_basic_attributes(
        self,
        config: LLMConfig,
        service_id: str,
        metrics: Metrics | None,
        retry_listener: Callable[[int, int], None] | None,
    ) -> None:
        """Setup basic instance attributes."""
        self._tried_model_info = False
        self.cost_metric_supported: bool = True
        self.config: LLMConfig = copy.deepcopy(config)
        self.service_id = service_id
        self.metrics: Metrics = metrics if metrics is not None else Metrics(model_name=config.model)
        self.model_info: ModelInfo | None = None
        self._function_calling_active: bool = False
        self.retry_listener = retry_listener

    def _setup_logging(self) -> None:
        """Setup logging configuration."""
        if self.config.log_completions:
            if self.config.log_completions_folder is None:
                msg = "log_completions_folder is required when log_completions is enabled"
                raise RuntimeError(msg)
            os.makedirs(self.config.log_completions_folder, exist_ok=True)

    def _setup_model_info_and_capabilities(self) -> None:
        """Setup model info and log capabilities."""
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            self.init_model_info()

        if self.vision_is_active():
            logger.debug("LLM: model has vision enabled")
        if self.is_caching_prompt_active():
            logger.debug("LLM: caching prompt enabled")
        if self.is_function_calling_active():
            logger.debug("LLM: model supports function calling")

    def _setup_tokenizer(self) -> None:
        """Setup custom tokenizer if configured."""
        if self.config.custom_tokenizer is not None:
            self.tokenizer = create_pretrained_tokenizer(self.config.custom_tokenizer)
        else:
            self.tokenizer = None

    def _build_basic_kwargs(self) -> dict[str, Any]:
        """Build basic completion kwargs."""
        kwargs: dict[str, Any] = {
            "temperature": self.config.temperature,
            "max_completion_tokens": self.config.max_output_tokens,
        }

        if self.config.top_k is not None:
            kwargs["top_k"] = self.config.top_k
        
        # Claude models don't allow both temperature and top_p to be specified
        # Only include top_p if it's explicitly set and we're not using a Claude model
        is_claude_model = "claude" in self.config.model.lower()
        if self.config.top_p is not None and not is_claude_model:
            kwargs["top_p"] = self.config.top_p
        elif is_claude_model and self.config.top_p is not None:
            logger.debug("Skipping top_p for Claude model to avoid parameter conflict")

        return kwargs

    def _handle_openhands_model(self) -> None:
        """Handle OpenHands model configuration."""
        if self.config.model.startswith("openhands/"):
            model_name = self.config.model.removeprefix("openhands/")
            self.config.model = f"litellm_proxy/{model_name}"
            self.config.base_url = "https://llm-proxy.app.all-hands.dev/"
            logger.debug(
                "Rewrote openhands/%s to %s with base URL %s",
                model_name,
                self.config.model,
                self.config.base_url,
            )

    def _setup_model_info_and_capabilities(self) -> None:
        """Setup model info and check capabilities."""
        # Initialize model info if the method exists
        try:
            with warnings.catch_warnings():
                warnings.simplefilter('ignore')
                if hasattr(self, 'init_model_info'):
                    self.init_model_info()
        except Exception as e:
            logger.debug(f"Could not initialize model info: {e}")
        
        # Check capabilities if methods exist
        try:
            if hasattr(self, 'vision_is_active') and self.vision_is_active():
                logger.debug('LLM: model has vision enabled')
        except Exception:
            pass
            
        try:
            if hasattr(self, 'is_caching_prompt_active') and self.is_caching_prompt_active():
                logger.debug('LLM: caching prompt enabled')
        except Exception:
            pass
            
        try:
            if hasattr(self, 'is_function_calling_active') and self.is_function_calling_active():
                logger.debug('LLM: model supports function calling')
        except Exception:
            pass

    def _setup_tokenizer(self) -> None:
        """Setup tokenizer if needed."""
        # If using a custom tokenizer, make sure it's loaded and accessible in the format expected by litellm
        if self.config.custom_tokenizer is not None:
            self.tokenizer = create_pretrained_tokenizer(self.config.custom_tokenizer)
        else:
            self.tokenizer = None

    def _configure_reasoning_effort(self, kwargs: dict[str, Any]) -> None:
        """Configure reasoning effort for supported models."""
        features = get_features(self.config.model)
        if features.supports_reasoning_effort:
            if "gemini-2.5-pro" in self.config.model:
                logger.debug(
                    "Gemini model %s with reasoning_effort %s",
                    self.config.model,
                    self.config.reasoning_effort,
                )
                if self.config.reasoning_effort in {None, "low", "none"}:
                    kwargs["thinking"] = {"budget_tokens": 128}
                    kwargs["allowed_openai_params"] = ["thinking"]
                    kwargs.pop("reasoning_effort", None)
                else:
                    kwargs["reasoning_effort"] = self.config.reasoning_effort
                logger.debug(
                    "Gemini model %s with reasoning_effort %s mapped to thinking %s",
                    self.config.model,
                    self.config.reasoning_effort,
                    kwargs.get("thinking"),
                )
            else:
                kwargs["reasoning_effort"] = self.config.reasoning_effort
            kwargs.pop("temperature")
            kwargs.pop("top_p")

    def _configure_model_specific_settings(self, kwargs: dict[str, Any]) -> None:
        """Configure model-specific settings."""
        self._configure_azure_settings(kwargs)
        self._configure_safety_settings(kwargs)
        self._configure_aws_settings(kwargs)
        self._configure_claude_settings(kwargs)

    def _configure_azure_settings(self, kwargs: dict[str, Any]) -> None:
        """Configure Azure-specific settings.

        Args:
            kwargs: Completion kwargs to modify
        """
        if self.config.model.startswith("azure"):
            kwargs["max_tokens"] = self.config.max_output_tokens
            kwargs.pop("max_completion_tokens", None)

    def _configure_safety_settings(self, kwargs: dict[str, Any]) -> None:
        """Configure safety settings for supported models.

        Args:
            kwargs: Completion kwargs to modify
        """
        if not self.config.safety_settings:
            return

        model_lower = self.config.model.lower()
        if "mistral" in model_lower or "gemini" in model_lower:
            kwargs["safety_settings"] = self.config.safety_settings

    def _configure_aws_settings(self, kwargs: dict[str, Any]) -> None:
        """Configure AWS credentials.

        Args:
            kwargs: Completion kwargs to modify
        """
        kwargs["aws_region_name"] = self.config.aws_region_name

        if self.config.aws_access_key_id:
            kwargs["aws_access_key_id"] = self.config.aws_access_key_id.get_secret_value()

        if self.config.aws_secret_access_key:
            kwargs["aws_secret_access_key"] = self.config.aws_secret_access_key.get_secret_value()

    def _configure_claude_settings(self, kwargs: dict[str, Any]) -> None:
        """Configure Claude-specific settings.

        Args:
            kwargs: Completion kwargs to modify
        """
        model_lower = self.config.model.lower()

        if "claude-opus-4-1" in model_lower:
            kwargs["thinking"] = {"type": "disabled"}

            # Remove top_p when both temperature and top_p are set
            if "temperature" in kwargs and "top_p" in kwargs:
                kwargs.pop("top_p", None)

    def _handle_openhands_model(self) -> None:
        """Handle OpenHands provider - rewrite to litellm_proxy."""
        if self.config.model.startswith('openhands/'):
            model_name = self.config.model.removeprefix('openhands/')
            self.config.model = f'litellm_proxy/{model_name}'
            self.config.base_url = 'https://llm-proxy.app.all-hands.dev/'
            logger.debug(
                f'Rewrote openhands/{model_name} to {self.config.model} with base URL {self.config.base_url}'
            )

    def _setup_completion_function(self, kwargs: dict[str, Any]) -> None:
        """Setup the completion function with provider-agnostic parameter validation."""
        # CRITICAL: Ensure API key manager environment variables are set before completion setup
        from openhands.core.config.api_key_manager import api_key_manager
        
        # Force environment variable setup right before completion function
        if self.config.model:
            api_key_manager.set_environment_variables(self.config.model, self.config.api_key)
            logger.debug(f"Set environment variables for model: {self.config.model}")
        
        # Ensure API key is properly extracted with fallback
        api_key_value = None
        
        # First try to get API key from config - check if it's valid
        if (self.config.api_key and 
            self.config.api_key.get_secret_value() and 
            self.config.api_key.get_secret_value().strip()):
            api_key_value = self.config.api_key.get_secret_value()
            logger.debug(f"Using config API key for completion: {api_key_value[:10]}...")
        else:
            # CRITICAL: Try to get API key from environment variables as fallback
            provider = api_key_manager._extract_provider(self.config.model)
            env_key = api_key_manager._get_provider_key_from_env(provider)
            if env_key and env_key.strip():
                api_key_value = env_key
                logger.debug(f"Using environment API key for completion: {api_key_value[:10]}...")
            else:
                # Try to get API key using the manager as a final fallback
                correct_api_key = api_key_manager.get_api_key_for_model(self.config.model, self.config.api_key)
                if correct_api_key and correct_api_key.get_secret_value() and correct_api_key.get_secret_value().strip():
                    api_key_value = correct_api_key.get_secret_value()
                    logger.debug(f"Using API key manager result for completion: {api_key_value[:10]}...")
                else:
                    logger.error(f"CRITICAL: No API key available anywhere for model: {self.config.model}")
        
        # Build base completion parameters
        base_completion_kwargs = {
            'model': self.config.model,
            'api_key': api_key_value,
            'timeout': self.config.timeout,
            'drop_params': self.config.drop_params,
            'seed': self.config.seed,
        }
        
        # Add optional parameters if they exist
        if self.config.base_url is not None:
            base_completion_kwargs['base_url'] = self.config.base_url
        if self.config.api_version is not None:
            base_completion_kwargs['api_version'] = self.config.api_version
        if self.config.custom_llm_provider is not None:
            base_completion_kwargs['custom_llm_provider'] = self.config.custom_llm_provider
        
        # Merge additional kwargs from the function call
        all_params = {**base_completion_kwargs, **kwargs}
        
        # CRITICAL: Use provider configuration to validate and clean parameters
        cleaned_completion_kwargs = api_key_manager.validate_and_clean_completion_params(
            self.config.model, all_params
        )
        
        self._completion = partial(litellm_completion, **cleaned_completion_kwargs)
        self._completion_unwrapped = self._completion
        logger.debug(f"Completed function setup for model: {self.config.model} with {len(cleaned_completion_kwargs)} validated parameters")

    def __init__(
        self,
        config: LLMConfig,
        service_id: str,
        metrics: Metrics | None = None,
        retry_listener: Callable[[int, int], None] | None = None,
    ) -> None:
        """Initializes the LLM. If LLMConfig is passed, its values will be the fallback.

        Passing simple parameters always overrides config.

        Args:
            config: The LLM configuration.
            service_id: The service identifier.
            metrics: The metrics to use.
            retry_listener: Optional callback for retry events.
        """
        # Setup basic attributes
        self._setup_basic_attributes(config, service_id, metrics, retry_listener)

        # Setup logging
        self._setup_logging()

        # Setup model info and capabilities
        self._setup_model_info_and_capabilities()

        # Setup tokenizer
        self._setup_tokenizer()

        # Build completion kwargs
        kwargs = self._build_basic_kwargs()

        # Handle OpenHands model configuration
        self._handle_openhands_model()

        # Configure reasoning effort
        self._configure_reasoning_effort(kwargs)

        # Configure model-specific settings
        self._configure_model_specific_settings(kwargs)

        # Setup completion function
        self._setup_completion_function(kwargs)

    def _prepare_messages(
        self,
        args: tuple[Any, ...],
        kwargs: dict[str, Any],
    ) -> tuple[list[dict], bool, list[dict] | None, bool]:
        """Prepare messages for completion, handling conversion and tools."""
        mock_function_calling = not self.is_function_calling_active()

        # Extract and normalize messages
        messages = self._extract_messages(args, kwargs)
        kwargs["messages"] = messages

        # Handle function calling conversion if needed
        mock_fncall_tools = self._handle_function_calling_conversion(
            mock_function_calling,
            messages,
            kwargs,
        )

        return (messages, mock_function_calling, mock_fncall_tools, len(args) > 0)

    def _extract_messages(self, args: tuple[Any, ...], kwargs: dict[str, Any]) -> list[dict]:
        """Extract and normalize messages from args and kwargs."""
        # Extract messages from args or kwargs
        if len(args) > 1:
            messages_kwarg = args[1] if len(args) > 1 else args[0]
            kwargs["messages"] = messages_kwarg
            # Remove processed args (this would need to be handled by caller)
        elif "messages" in kwargs:
            messages_kwarg = kwargs["messages"]
        else:
            messages_kwarg = args[0] if args else []

        # Normalize to list
        messages_list = messages_kwarg if isinstance(messages_kwarg, list) else [messages_kwarg]

        # Convert Message objects to dicts if needed
        if messages_list and isinstance(messages_list[0], Message):
            from openhands.core.pydantic_compat import model_dump_with_options

            messages = [model_dump_with_options(m) for m in cast("list[Message]", messages_list)]
        else:
            messages = cast("list[dict[str, Any]]", messages_list)

        # Create deep copy to avoid mutation
        copy.deepcopy(messages)
        return messages

    def _handle_function_calling_conversion(
        self,
        mock_function_calling: bool,
        messages: list[dict],
        kwargs: dict[str, Any],
    ) -> list[dict] | None:
        """Handle function calling conversion when mocking is enabled."""
        if not mock_function_calling or "tools" not in kwargs:
            return None

        # Convert function calling messages to non-function calling format
        add_in_context_learning_example = (
            "openhands-lm" not in self.config.model and "devstral" not in self.config.model
        )

        converted_messages = convert_fncall_messages_to_non_fncall_messages(
            messages,
            kwargs["tools"],
            add_in_context_learning_example=add_in_context_learning_example,
        )
        kwargs["messages"] = converted_messages

        # Add stop words if supported
        if get_features(self.config.model).supports_stop_words and (not self.config.disable_stop_word):
            kwargs["stop"] = STOP_WORDS

        # Handle tool choice based on model
        mock_fncall_tools = kwargs.pop("tools")
        if "openhands-lm" in self.config.model:
            kwargs["tool_choice"] = "none"
        else:
            kwargs.pop("tool_choice", None)

        return mock_fncall_tools

    @retry_decorator(
        num_retries=3,
        retry_exceptions=LLM_RETRY_EXCEPTIONS,
        retry_min_wait=1.0,
        retry_max_wait=60.0,
        retry_multiplier=2.0,
    )
    def _log_completion_input(self, messages, mock_function_calling, mock_fncall_tools, kwargs) -> None:
        """Log completion input if logging is enabled."""
        if not self.config.log_completions:
            return

        from openhands.io import json

        input_data = {
            "model": self.config.model,
            "messages": messages,
            "kwargs": {k: v for k, v in kwargs.items() if k not in ["messages", "tools"]},
            "mock_function_calling": mock_function_calling,
        }
        if mock_fncall_tools:
            input_data["mock_fncall_tools"] = mock_fncall_tools

        with open(
            os.path.join(self.config.log_completions_folder, f"input_{int(time.time())}.json"), "w", encoding="utf-8",
        ) as f:
            f.write(json.dumps(input_data, indent=2))

    def _log_completion_error(self, messages, error: Exception, kwargs) -> None:
        """Log completion error if logging is enabled."""
        if not self.config.log_completions:
            return

        from openhands.io import json

        error_data = {
            "model": self.config.model,
            "messages": messages,
            "error": str(error),
            "kwargs": {k: v for k, v in kwargs.items() if k not in ["messages", "tools"]},
        }
        with open(
            os.path.join(self.config.log_completions_folder, f"error_{int(time.time())}.json"), "w", encoding="utf-8",
        ) as f:
            f.write(json.dumps(error_data, indent=2))

    def _log_completion_output(self, response, messages, kwargs) -> None:
        """Log completion output if logging is enabled."""
        if not self.config.log_completions:
            return

        from openhands.io import json

        output_data = {
            "model": self.config.model,
            "response": response.model_dump() if hasattr(response, "model_dump") else response,
            "messages": messages,
            "kwargs": {k: v for k, v in kwargs.items() if k not in ["messages", "tools"]},
        }
        with open(
            os.path.join(self.config.log_completions_folder, f"output_{int(time.time())}.json"), "w", encoding="utf-8",
        ) as f:
            f.write(json.dumps(output_data, indent=2))

    def _apply_mock_function_calling(self, response, mock_fncall_tools) -> None:
        """Apply mock function calling to response if needed."""
        response.choices[0].message.tool_calls = []
        response.choices[0].message.content = convert_non_fncall_messages_to_fncall_messages(
            [{"role": "assistant", "content": response.choices[0].message.content}],
            mock_fncall_tools,
        )[0]["content"]

    def _completion_wrapper(self, *args: Any, **kwargs: Any) -> Any:
        """Wrapper for the litellm completion function. Logs the input and output of the completion function."""
        messages, mock_function_calling, mock_fncall_tools, _has_extra_args = self._prepare_messages(args, kwargs)

        # Check if streaming is requested
        is_streaming = kwargs.get("stream", False)

        # Log input
        self._log_completion_input(messages, mock_function_calling, mock_fncall_tools, kwargs)

        # CRITICAL: Ensure environment variables are set right before completion call
        try:
            from openhands.core.config.api_key_manager import api_key_manager
            api_key_manager.set_environment_variables(self.config.model, self.config.api_key)
            logger.debug(f"Final environment variable check before completion for {self.config.model}")
            
            # FINAL SAFETY CHECK: Use provider configuration to clean any remaining problematic parameters
            provider = api_key_manager._extract_provider(self.config.model)
            provider_config = api_key_manager.validate_and_clean_completion_params(self.config.model, kwargs)
            
            # Update kwargs with cleaned parameters, removing forbidden ones
            for param_name in list(kwargs.keys()):
                if param_name not in provider_config:
                    logger.debug(f"FINAL SAFETY: Removing forbidden parameter '{param_name}' for {provider}")
                    del kwargs[param_name]
                        
        except Exception as e:
            logger.warning(f"Failed to set environment variables before completion: {e}")

        # Execute completion
        try:
            response = self._completion_unwrapped(*args, **kwargs)

            # If streaming, return the iterator directly (caller handles chunks)
            if is_streaming:
                return response

        except Exception as e:
            self._log_completion_error(messages, e, kwargs)
            raise

        # Log output (only for non-streaming)
        self._log_completion_output(response, messages, kwargs)

        # Apply mock function calling if needed
        if mock_function_calling and mock_fncall_tools:
            self._apply_mock_function_calling(response, mock_fncall_tools)

        return response

    @property
    def completion(self) -> Callable:
        """Decorator for the litellm completion function.

        Check the complete documentation at https://litellm.vercel.app/docs/completion
        """
        return self._completion_wrapper

    def _get_openrouter_model_info(self) -> None:
        """Get model info for OpenRouter models."""
        try:
            if self.config.model.startswith("openrouter"):
                self.model_info = litellm.get_model_info(self.config.model)
        except Exception as e:
            logger.debug("Error getting model info: %s", e)

    def _get_litellm_proxy_model_info(self) -> None:
        """Get model info from LiteLLM proxy."""
        base_url = self.config.base_url.strip() if self.config.base_url else ""
        if not base_url.startswith(("http://", "https://")):
            base_url = f"http://{base_url}"
        from openhands.core.utils.retry import RetryError, retry

        def _do_get():
            return httpx.get(
                f"{base_url}/v1/model/info",
                headers={
                    "Authorization": f"Bearer {
                        (
                            self.config.api_key.get_secret_value() if self.config.api_key else None)}",
                },
            )

        try:
            response = retry(
                _do_get,
                max_attempts=3,
                base_delay=0.5,
                max_delay=3.0,
                operation="litellm_proxy_model_info",
                logger=logger,
            )
        except RetryError as e:
            logger.info("Failed to fetch model info from LiteLLM proxy after retries: %s", e)
            response = None
        try:
            resp_json = response.json()
            if "data" not in resp_json:
                logger.info("No data field in model info response from LiteLLM proxy: %s", resp_json)
            all_model_info = resp_json.get("data", [])
        except Exception as e:
            logger.info("Error parsing JSON response from LiteLLM proxy: %s", e)
            all_model_info = []
        current_model_info = next(
            (info for info in all_model_info if info["model_name"] == self.config.model.removeprefix("litellm_proxy/")),
            None,
        )
        if current_model_info:
            self.model_info = current_model_info["model_info"]
            logger.debug("Got model info from litellm proxy: %s", self.model_info)

    def _try_get_model_info_from_litellm(self) -> None:
        """Try to get model info from litellm with different model name variations."""
        if not self.model_info:
            with contextlib.suppress(Exception):
                self.model_info = litellm.get_model_info(self.config.model.split(":")[0])

        if not self.model_info:
            with contextlib.suppress(Exception):
                self.model_info = litellm.get_model_info(self.config.model.split("/")[-1])

    def _log_model_info(self) -> None:
        """Log model information for debugging."""
        from openhands.io import json

        logger.debug(
            "Model info: %s",
            json.dumps({"model": self.config.model, "base_url": self.config.base_url}, indent=2),
        )

    def _configure_huggingface_model(self) -> None:
        """Configure Hugging Face model specific settings."""
        if self.config.model.startswith("huggingface"):
            logger.debug("Setting top_p to 0.9 for Hugging Face model: %s", self.config.model)
            self.config.top_p = 0.9 if self.config.top_p == 1 else self.config.top_p

    def _configure_input_tokens(self) -> None:
        """Configure max input tokens from model info."""
        if (
            self.config.max_input_tokens is None
            and self.model_info is not None
            and "max_input_tokens" in self.model_info
            and isinstance(self.model_info["max_input_tokens"], int)
        ):
            self.config.max_input_tokens = self.model_info["max_input_tokens"]

    def _configure_output_tokens(self) -> None:
        """Configure max output tokens from model info or defaults."""
        if self.config.max_output_tokens is None:
            if any(model in self.config.model for model in ["claude-3-7-sonnet", "claude-3.7-sonnet"]):
                self.config.max_output_tokens = 64000
            elif self.model_info is not None:
                if "max_output_tokens" in self.model_info and isinstance(self.model_info["max_output_tokens"], int):
                    self.config.max_output_tokens = self.model_info["max_output_tokens"]
                elif "max_tokens" in self.model_info and isinstance(self.model_info["max_tokens"], int):
                    self.config.max_output_tokens = self.model_info["max_tokens"]

    def _configure_function_calling(self) -> None:
        """Configure function calling capability."""
        features = get_features(self.config.model)
        if self.config.native_tool_calling is None:
            self._function_calling_active = features.supports_function_calling
        else:
            self._function_calling_active = self.config.native_tool_calling

    def init_model_info(self) -> None:
        """Initialize model information for the LLM."""
        if self._tried_model_info:
            return

        self._tried_model_info = True

        # Get model info from various sources
        self._get_openrouter_model_info()
        if self.config.model.startswith("litellm_proxy/"):
            self._get_litellm_proxy_model_info()

        # Try to get model info from litellm
        self._try_get_model_info_from_litellm()

        # Log model info
        self._log_model_info()

        # Configure model-specific settings
        self._configure_huggingface_model()
        self._configure_input_tokens()
        self._configure_output_tokens()
        self._configure_function_calling()

    def vision_is_active(self) -> bool:
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            return not self.config.disable_vision and self._supports_vision()

    def _supports_vision(self) -> bool:
        """Acquire from litellm if model is vision capable.

        Returns:
            bool: True if model is vision capable. Return False if model not supported by litellm.
        """
        if os.getenv("OPENHANDS_FORCE_VISION", "").lower() in ("1", "true", "yes", "on"):
            return True
        return (
            litellm.supports_vision(self.config.model)
            or litellm.supports_vision(self.config.model.split("/")[-1])
            or (self.model_info is not None and self.model_info.get("supports_vision", False))
        )

    def is_caching_prompt_active(self) -> bool:
        """Check if prompt caching is supported and enabled for current model.

        Returns:
            boolean: True if prompt caching is supported and enabled for the given model.
        """
        if not self.config.caching_prompt:
            return False
        return get_features(self.config.model).supports_prompt_cache

    def is_function_calling_active(self) -> bool:
        """Returns whether function calling is supported and enabled for this LLM instance.

        The result is cached during initialization for performance.
        """
        return self._function_calling_active

    def _build_cost_stats(self, cur_cost: float) -> str:
        """Build cost statistics string."""
        if not self.cost_metric_supported:
            return ""
        return f"Cost: {cur_cost:.2f} USD | Accumulated Cost: {self.metrics.accumulated_cost:.2f} USD\n"

    def _build_latency_stats(self) -> str:
        """Build latency statistics string."""
        if not self.metrics.response_latencies:
            return ""
        latest_latency = self.metrics.response_latencies[-1]
        return f"Response Latency: {latest_latency.latency:.3f} seconds\n"

    def _extract_cache_tokens(self, usage: Usage) -> tuple[int, int]:
        """Extract cache hit and write tokens from usage."""
        prompt_tokens_details: PromptTokensDetails = usage.get("prompt_tokens_details")
        cache_hit_tokens = (
            prompt_tokens_details.cached_tokens if prompt_tokens_details and prompt_tokens_details.cached_tokens else 0
        )
        model_extra = usage.get("model_extra", {})
        cache_write_tokens = model_extra.get("cache_creation_input_tokens", 0)
        return cache_hit_tokens, cache_write_tokens

    def _build_token_stats(self, usage: Usage) -> str:
        """Build token usage statistics string."""
        prompt_tokens = usage.get("prompt_tokens", 0)
        completion_tokens = usage.get("completion_tokens", 0)
        stats = ""

        if prompt_tokens:
            stats += f"Input tokens: {prompt_tokens!s}"
        if completion_tokens:
            stats += (" | " if prompt_tokens else "") + "Output tokens: " + str(completion_tokens) + "\n"

        cache_hit_tokens, cache_write_tokens = self._extract_cache_tokens(usage)
        if cache_hit_tokens:
            stats += f"Input tokens (cache hit): {cache_hit_tokens!s}" + "\n"
        if cache_write_tokens:
            stats += f"Input tokens (cache write): {cache_write_tokens!s}" + "\n"

        return stats

    def _update_metrics_from_usage(self, usage: Usage, response_id: str) -> None:
        """Update metrics from usage information."""
        prompt_tokens = usage.get("prompt_tokens", 0)
        completion_tokens = usage.get("completion_tokens", 0)
        cache_hit_tokens, cache_write_tokens = self._extract_cache_tokens(usage)

        context_window = 0
        if self.model_info and "max_input_tokens" in self.model_info:
            context_window = self.model_info["max_input_tokens"]
            logger.debug("Using context window: %s", context_window)

        self.metrics.add_token_usage(
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            cache_read_tokens=cache_hit_tokens,
            cache_write_tokens=cache_write_tokens,
            context_window=context_window,
            response_id=response_id,
        )

    def _post_completion(self, response: ModelResponse) -> float:
        """Post-process the completion response.

        Logs the cost and usage stats of the completion call.
        """
        try:
            cur_cost = self._completion_cost(response)
        except Exception:
            cur_cost = 0

        # Build statistics
        stats = self._build_cost_stats(cur_cost)
        stats += self._build_latency_stats()

        # Process usage information
        usage: Usage | None = response.get("usage")
        response_id = response.get("id", "unknown")
        if usage:
            stats += self._build_token_stats(usage)
            self._update_metrics_from_usage(usage, response_id)

        if stats:
            logger.debug(stats)

        return cur_cost

    def get_token_count(self, messages: list[dict] | list[Message]) -> int:
        """Get the number of tokens in a list of messages. Use dicts for better token counting.

        Args:
            messages (list): A list of messages, either as a list of dicts or as a list of Message objects.

        Returns:
            int: The number of tokens.
        """
        if isinstance(messages, list) and len(messages) > 0 and isinstance(messages[0], Message):
            logger.info("Message objects now include serialized tool calls in token counting")
            assert isinstance(messages, list) and all(
                isinstance(m, Message) for m in messages
            ), "Expected list of Message objects"
            messages_typed: list[Message] = messages
            messages = self.format_messages_for_llm(messages_typed)
        try:
            return int(
                litellm.token_counter(model=self.config.model, messages=messages, custom_tokenizer=self.tokenizer),
            )
        except Exception as e:
            logger.error(
                f"Error getting token count for\n model {self.config.model}\n{e}"
                + (
                    f"\ncustom_tokenizer: {self.config.custom_tokenizer}"
                    if self.config.custom_tokenizer is not None
                    else ""
                ),
            )
            return 0

    def _is_local(self) -> bool:
        """Determines if the system is using a locally running LLM.

        Returns:
            boolean: True if executing a local model.
        """
        if self.config.base_url is not None:
            for substring in ["localhost", "127.0.0.1", "0.0.0.0"]:  # nosec B104 - Safe: checking for local addresses
                if substring in self.config.base_url:
                    return True
        elif self.config.model is not None:
            if self.config.model.startswith("ollama"):
                return True
        return False

    def _completion_cost(self, response: Any) -> float:
        """Calculate completion cost and update metrics with running total.

        Calculate the cost of a completion response based on the model. Local models are treated as free.
        Add the current cost into total cost in metrics.

        Args:
            response: A response from a model invocation.

        Returns:
            number: The cost of the response.
        """
        if not self.cost_metric_supported:
            return 0.0
        extra_kwargs = {}
        if self.config.input_cost_per_token is not None and self.config.output_cost_per_token is not None:
            cost_per_token = CostPerToken(
                input_cost_per_token=self.config.input_cost_per_token,
                output_cost_per_token=self.config.output_cost_per_token,
            )
            logger.debug("Using custom cost per token: %s", cost_per_token)
            extra_kwargs["custom_cost_per_token"] = cost_per_token
        _hidden_params = getattr(response, "_hidden_params", {})
        cost = _hidden_params.get("additional_headers", {}).get("llm_provider-x-litellm-response-cost", None)
        if cost is not None:
            cost = float(cost)
            logger.debug("Got response_cost from response: %s", cost)
        try:
            if cost is None:
                try:
                    cost = litellm_completion_cost(completion_response=response, **extra_kwargs)
                except Exception as e:
                    logger.debug("Error getting cost from litellm: %s", e)
            if cost is None:
                _model_name = "/".join(self.config.model.split("/")[1:])
                cost = litellm_completion_cost(completion_response=response, model=_model_name, **extra_kwargs)
                logger.debug("Using fallback model name %s to get cost: %s", _model_name, cost)
            self.metrics.add_cost(float(cost))
            return float(cost)
        except Exception:
            self.cost_metric_supported = False
            logger.debug("Cost calculation not supported for this model.")
        return 0.0

    def __str__(self) -> str:
        if self.config.api_version:
            return f"LLM(model={
                self.config.model}, api_version={
                self.config.api_version}, base_url={
                self.config.base_url})"
        if self.config.base_url:
            return f"LLM(model={self.config.model}, base_url={self.config.base_url})"
        return f"LLM(model={self.config.model})"

    def __repr__(self) -> str:
        return str(self)

    def format_messages_for_llm(self, messages: Message | list[Message]) -> list[dict]:
        if isinstance(messages, Message):
            messages = [messages]
        for message in messages:
            message.cache_enabled = self.is_caching_prompt_active()
            message.vision_enabled = self.vision_is_active()
            message.function_calling_enabled = self.is_function_calling_active()
            if "deepseek" in self.config.model:
                message.force_string_serializer = True
            if "kimi-k2-instruct" in self.config.model and "groq" in self.config.model:
                message.force_string_serializer = True
            if "openrouter/anthropic/claude-sonnet-4" in self.config.model:
                message.force_string_serializer = True
        from openhands.core.pydantic_compat import model_dump_with_options

        return [model_dump_with_options(message) for message in messages]
