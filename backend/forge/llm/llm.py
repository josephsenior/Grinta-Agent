"""LLM integration and communication layer.

Classes:
    LLM

Functions:
    retry_decorator
"""

from __future__ import annotations

import copy
import os
import time
import warnings
from typing import TYPE_CHECKING, Any, Callable, Optional, cast, AsyncIterator, List, Dict

from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from forge.llm.metrics import Metrics
from forge.llm.model_features import get_features, ModelFeatures
from forge.llm.llm_utils import get_token_count, create_pretrained_tokenizer
from forge.utils.tenacity_stop import stop_if_should_exit
from forge.llm.direct_clients import get_direct_client, LLMResponse

from forge.core.exceptions import LLMNoResponseError
from forge.core.logger import forge_logger as logger
from forge.core.message import Message
from forge.llm.debug_mixin import DebugMixin
from forge.llm.retry_mixin import RetryMixin

if TYPE_CHECKING:
    from forge.core.config import LLMConfig


# Create a standalone retry decorator for class-level decorators
def retry_decorator(**kwargs: Any) -> Callable:
    """Create a retry decorator for LLM completion calls."""
    num_retries = kwargs.get("num_retries", 3)
    retry_exceptions = kwargs.get("retry_exceptions", (Exception,))
    retry_min_wait = kwargs.get("retry_min_wait", 1.0)
    retry_max_wait = kwargs.get("retry_max_wait", 60.0)
    retry_multiplier = kwargs.get("retry_multiplier", 2.0)

    return retry(
        stop=stop_after_attempt(num_retries) | stop_if_should_exit(),
        reraise=True,
        retry=retry_if_exception_type(retry_exceptions),
        wait=wait_exponential(
            multiplier=retry_multiplier, min=retry_min_wait, max=retry_max_wait
        ),
    )


from forge.llm.exceptions import (
    APIConnectionError,
    ContentPolicyViolationError,
    RateLimitError,
    ServiceUnavailableError,
)

__all__ = ["LLM"]

LLM_RETRY_EXCEPTIONS: tuple[type[Exception], ...] = (
    APIConnectionError,
    RateLimitError,
    ServiceUnavailableError,
    LLMNoResponseError,
)


class LLM(RetryMixin, DebugMixin):
    """Language Model abstraction layer with direct SDK client support.

    Provides a unified interface to LLM models from providers including OpenAI,
    Anthropic, Google (Gemini), and xAI (Grok). Handles retries, cost tracking,
    streaming, and provider-specific quirks while using official SDKs for
    better stability and performance.
    """

    def __init__(
        self,
        config: LLMConfig,
        service_id: str,
        metrics: Metrics | None = None,
        retry_listener: Callable[[int, int], None] | None = None,
    ) -> None:
        self.config: LLMConfig = copy.deepcopy(config)
        self.service_id = service_id
        self.metrics: Metrics = (
            metrics if metrics is not None else Metrics(model_name=config.model)
        )
        self.retry_listener = retry_listener
        self._function_calling_active: bool = False
        
        # Initialize client
        api_key_value = self._extract_api_key()
        if not api_key_value:
            logger.error(f"No API key available for model: {self.config.model}")
            
        self.client = get_direct_client(
            model=self.config.model,
            api_key=api_key_value or "",
            base_url=self.config.base_url
        )
        
        # Configure capabilities
        try:
            features = get_features(self.config.model)
            self._function_calling_active = self.config.native_tool_calling if self.config.native_tool_calling is not None else features.supports_function_calling
        except Exception:
            logger.debug(f"Could not get features for model: {self.config.model}")
            self._function_calling_active = self.config.native_tool_calling or False

        # Initialize model info (limits, etc)
        self.init_model_info()
        
        # Cache model features for easy access
        try:
            self._cached_features = get_features(self.config.model)
        except Exception:
            from forge.llm.model_features import ModelFeatures
            self._cached_features = ModelFeatures()  # Default features

        # Handle custom tokenizer
        if self.config.custom_tokenizer:
            self.config.custom_tokenizer = create_pretrained_tokenizer(self.config.custom_tokenizer)
    
    @property
    def features(self) -> ModelFeatures:
        """Get model features/capabilities."""
        return self._cached_features

    def init_model_info(self) -> None:
        """Initialize model limits and capabilities.
        
        Maintained for backwards compatibility. Uses native model_features.
        """
        try:
            features = get_features(self.config.model)
            if self.config.max_input_tokens is None:
                self.config.max_input_tokens = features.max_input_tokens
            if self.config.max_output_tokens is None:
                self.config.max_output_tokens = features.max_output_tokens
        except Exception as e:
            logger.debug(f"Could not initialize model info for {self.config.model}: {e}")

    def _extract_api_key(self) -> str | None:
        """Extract API key from config or environment."""
        from forge.core.config.api_key_manager import api_key_manager
        
        if (
            self.config.api_key
            and self.config.api_key.get_secret_value()
            and self.config.api_key.get_secret_value().strip()
        ):
            return self.config.api_key.get_secret_value()

        key_obj = api_key_manager.get_api_key_for_model(
            self.config.model, self.config.api_key
        )
        return key_obj.get_secret_value() if key_obj else None

    def _get_call_kwargs(self, **kwargs) -> dict:
        """Merge default config with call-specific kwargs and handle model-specific parameters."""
        is_stream = kwargs.pop("is_stream", False)
        
        # Filter out legacy parameters that are no longer needed for direct SDKs
        legacy_params = ["drop_params", "force_timeout", "metadata", "api_base", "caching"]
        for param in legacy_params:
            kwargs.pop(param, None)

        call_kwargs = {
            "model": self.config.model,
            "temperature": self.config.temperature,
            "max_tokens": self.config.max_output_tokens,
            **kwargs
        }
        if self.config.top_p is not None:
            call_kwargs["top_p"] = self.config.top_p
        if self.config.top_k is not None:
            call_kwargs["top_k"] = self.config.top_k
            
        # Handle model-specific tweaks and optimizations
        model_lower = self.config.model.lower()
        provider_lower = (self.config.custom_llm_provider or "").lower()
        is_gemini = "gemini" in model_lower or "gemini" in provider_lower
        
        if is_gemini:
            # Gemini specific reasoning mapping
            if self.config.reasoning_effort in [None, "low"]:
                # In streaming, we don't support thinking budget yet for Gemini
                if not is_stream:
                    call_kwargs["thinking"] = {"budget_tokens": 128}
                call_kwargs.pop("reasoning_effort", None)
                # Gemini often doesn't want temperature/top_p when thinking is enabled
                if not is_stream:
                    call_kwargs.pop("temperature", None)
                    call_kwargs.pop("top_p", None)
            elif self.config.reasoning_effort == "medium":
                call_kwargs["reasoning_effort"] = "medium"
                call_kwargs.pop("thinking", None)
            elif self.config.reasoning_effort == "high":
                call_kwargs["reasoning_effort"] = "high"
                call_kwargs.pop("thinking", None)
        elif "opus-4-1" in model_lower:
            # Anthropic Opus 4.1 specific tweaks
            call_kwargs["thinking"] = {"type": "disabled"}
            call_kwargs.pop("top_p", None)
        elif "claude" in model_lower:
            # Claude models don't support reasoning_effort param
            call_kwargs.pop("reasoning_effort", None)
            if "claude-3-7" in model_lower or "claude-3.7" in model_lower:
                # Claude 3.7 supports thinking
                if self.config.reasoning_effort == "low":
                    call_kwargs["thinking"] = {"type": "enabled", "budget_tokens": 1024}
                elif self.config.reasoning_effort in ["medium", "high"]:
                    call_kwargs["thinking"] = {"type": "enabled", "budget_tokens": 4096}
        else:
            if self.config.reasoning_effort is not None:
                call_kwargs["reasoning_effort"] = self.config.reasoning_effort
                
        if self.config.seed is not None:
            call_kwargs["seed"] = self.config.seed
            
        return call_kwargs

    def completion(self, *args, **kwargs) -> Any:
        """Synchronous completion call."""
        messages = self._extract_messages(args, kwargs)
        
        # Merge default kwargs
        call_kwargs = self._get_call_kwargs(is_stream=False, **kwargs)
        
        @self.retry_decorator(
            num_retries=self.config.num_retries,
            retry_exceptions=LLM_RETRY_EXCEPTIONS,
            retry_min_wait=self.config.retry_min_wait,
            retry_max_wait=self.config.retry_max_wait,
            retry_multiplier=self.config.retry_multiplier,
            retry_listener=self.retry_listener,
        )
        def _completion_with_retry(**kwargs):
            start_time = time.time()
            try:
                self.log_prompt(messages)
                response = self.client.completion(messages=messages, **kwargs)
                latency = time.time() - start_time
                
                # Update metrics
                self.metrics.add_response_latency(latency, response.id)
                if response.usage:
                    # Add cost to metrics
                    cost = self.client.get_completion_cost(
                        prompt_tokens=response.usage.get("prompt_tokens", 0),
                        completion_tokens=response.usage.get("completion_tokens", 0),
                        config=self.config
                    )
                    self.metrics.add_cost(cost)

                    # Extract cache tokens
                    cache_read = response.usage.get("cache_read_tokens", 0)
                    cache_write = response.usage.get("cache_write_tokens", 0)
                    
                    # Handle nested usage details (like from OpenAI/Anthropic mocks in tests)
                    if not cache_read and "prompt_tokens_details" in response.usage:
                        details: Any = response.usage["prompt_tokens_details"]
                        if hasattr(details, "cached_tokens"):
                            cache_read = details.cached_tokens
                        elif isinstance(details, dict):
                            cache_read = details.get("cached_tokens", 0)
                            
                    if not cache_write and "model_extra" in response.usage:
                        extra: Any = response.usage["model_extra"]
                        if isinstance(extra, dict):
                            cache_write = extra.get("cache_creation_input_tokens", 0)

                    self.metrics.add_token_usage(
                        prompt_tokens=response.usage.get("prompt_tokens", 0),
                        completion_tokens=response.usage.get("completion_tokens", 0),
                        cache_read_tokens=cache_read,
                        cache_write_tokens=cache_write,
                        context_window=0, # Not easily available from direct clients yet
                        response_id=response.id
                    )
                
                self.log_response(response.to_dict())
                return response
            except Exception as e:
                # Map SDK exceptions to our custom exceptions if needed
                # For now, we assume the client or the retry decorator handles it
                raise

        return _completion_with_retry(**call_kwargs)

    async def acompletion(self, *args, **kwargs) -> Any:
        """Asynchronous completion call with cancellation support."""
        messages = self._extract_messages(args, kwargs)
        
        # Merge default kwargs
        call_kwargs = self._get_call_kwargs(is_stream=False, **kwargs)
        
        @self.retry_decorator(
            num_retries=self.config.num_retries,
            retry_exceptions=LLM_RETRY_EXCEPTIONS,
            retry_min_wait=self.config.retry_min_wait,
            retry_max_wait=self.config.retry_max_wait,
            retry_multiplier=self.config.retry_multiplier,
            retry_listener=self.retry_listener,
        )
        async def _acompletion_with_retry(**kwargs):
            start_time = time.time()
            # Check for cancellation before start
            if await self._check_cancelled():
                raise LLMNoResponseError("Request cancelled before start")

            self.log_prompt(messages)
            response = await self.client.acompletion(messages=messages, **kwargs)
            latency = time.time() - start_time
            
            # Update metrics
            self.metrics.add_response_latency(latency, response.id)
            if response.usage:
                # Add cost to metrics
                cost = self.client.get_completion_cost(
                    prompt_tokens=response.usage.get("prompt_tokens", 0),
                    completion_tokens=response.usage.get("completion_tokens", 0),
                    config=self.config
                )
                self.metrics.add_cost(cost)

                # Extract cache tokens
                cache_read = response.usage.get("cache_read_tokens", 0)
                cache_write = response.usage.get("cache_write_tokens", 0)
                
                # Handle nested usage details
                if not cache_read and "prompt_tokens_details" in response.usage:
                    details: Any = response.usage["prompt_tokens_details"]
                    if hasattr(details, "cached_tokens"):
                        cache_read = details.cached_tokens
                    elif isinstance(details, dict):
                        cache_read = details.get("cached_tokens", 0)
                        
                if not cache_write and "model_extra" in response.usage:
                    extra: Any = response.usage["model_extra"]
                    if isinstance(extra, dict):
                        cache_write = extra.get("cache_creation_input_tokens", 0)

                self.metrics.add_token_usage(
                    prompt_tokens=response.usage.get("prompt_tokens", 0),
                    completion_tokens=response.usage.get("completion_tokens", 0),
                    cache_read_tokens=cache_read,
                    cache_write_tokens=cache_write,
                    context_window=0, # Not easily available from direct clients yet
                    response_id=response.id
                )
            
            self.log_response(response.to_dict())
            return response

        return await _acompletion_with_retry(**call_kwargs)

    async def astream(self, *args, **kwargs) -> AsyncIterator[Dict[str, Any]]:
        """Asynchronous streaming call with cancellation support."""
        messages = self._extract_messages(args, kwargs)
        
        # Merge default kwargs
        call_kwargs = self._get_call_kwargs(is_stream=True, **kwargs)
        
        # Log prompt
        self.log_prompt(messages)
        
        try:
            # Type: ignore needed because mypy doesn't understand async generator return types
            # astream returns an async iterator, not a coroutine
            stream_iter = self.client.astream(messages=messages, **call_kwargs)
            async for chunk in stream_iter:  # type: ignore[attr-defined]
                # Check for cancellation during stream
                if await self._check_cancelled():
                    logger.debug("LLM stream cancelled by user.")
                    break
                
                # Log chunk content if available
                if chunk.get("choices") and chunk["choices"][0].get("delta"):
                    content = chunk["choices"][0]["delta"].get("content", "")
                    if content:
                        self.log_response(content)
                        
                yield chunk
        except Exception as e:
            logger.error(f"LLM astream error: {e}")
            raise

    async def _check_cancelled(self) -> bool:
        """Check if the request has been cancelled."""
        if (
            hasattr(self.config, "on_cancel_requested_fn")
            and self.config.on_cancel_requested_fn is not None
        ):
            return await self.config.on_cancel_requested_fn()
        return False

    @property
    def async_completion(self) -> Callable:
        """Alias for acompletion for backwards compatibility."""
        return self.acompletion

    @property
    def async_streaming_completion(self) -> Callable:
        """Alias for astream for backwards compatibility."""
        return self.astream

    def _extract_messages(self, args: tuple[Any, ...], kwargs: dict[str, Any]) -> list[dict]:
        """Extract and normalize messages from args and kwargs."""
        if len(args) > 0:
            messages_kwarg = args[0]
        elif "messages" in kwargs:
            messages_kwarg = kwargs.pop("messages")
        else:
            messages_kwarg = []

        if isinstance(messages_kwarg, list):
            messages_list = messages_kwarg
        else:
            messages_list = [messages_kwarg]

        normalized_messages = []
        for m in messages_list:
            if isinstance(m, Message):
                from forge.core.pydantic_compat import model_dump_with_options
                normalized_messages.append(model_dump_with_options(m))
            else:
                normalized_messages.append(m)
        
        return normalized_messages

    def vision_is_active(self) -> bool:
        return not self.config.disable_vision

    def is_caching_prompt_active(self) -> bool:
        return self.config.caching_prompt

    def is_function_calling_active(self) -> bool:
        return self._function_calling_active

    def get_token_count(self, messages: list[dict] | list[Message]) -> int:
        """Estimate token count."""
        try:
            return get_token_count(
                messages,
                model=self.config.model,
                custom_tokenizer=self.config.custom_tokenizer,
            )
        except Exception as e:
            logger.error(
                f"Error getting token count for\n model {self.config.model}\n{e}"
            )
            return 0

    def format_messages_for_llm(self, messages: Message | list[Message]) -> list[dict]:
        if isinstance(messages, Message):
            messages = [messages]
        from forge.core.pydantic_compat import model_dump_with_options
        return [model_dump_with_options(m) for m in messages]

    def __str__(self) -> str:
        return f"LLM(model={self.config.model})"

    def __repr__(self) -> str:
        return str(self)
