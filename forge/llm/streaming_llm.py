# coverage: ignore file
"""Async streaming LLM client that surfaces token-by-token responses."""

import asyncio
import inspect
from functools import partial
from typing import Any, Callable

from forge.core.exceptions import UserCancelledError
from forge.core.logger import forge_logger as logger
from forge.llm.async_llm import LLM_RETRY_EXCEPTIONS, AsyncLLM
from forge.llm.model_features import get_features


class StreamingLLM(AsyncLLM):
    """Streaming LLM class."""

    def _create_streaming_completion_partial(self) -> Callable:
        """Create the partial streaming completion function with provider-agnostic validation.

        Returns:
            Callable: The partial streaming completion function.

        """
        # Build base completion parameters
        base_completion_kwargs = {
            'model': self.config.model,
            'api_key': self.config.api_key.get_secret_value() if self.config.api_key else None,
            'max_tokens': self.config.max_output_tokens,
            'timeout': self.config.timeout,
            'temperature': self.config.temperature,
            'top_p': self.config.top_p,
            'drop_params': self.config.drop_params,
            'stream': True,
        }
        
        # Add optional parameters if they exist
        if self.config.base_url is not None:
            base_completion_kwargs['base_url'] = self.config.base_url
        if self.config.api_version is not None:
            base_completion_kwargs['api_version'] = self.config.api_version
        if self.config.custom_llm_provider is not None:
            base_completion_kwargs['custom_llm_provider'] = self.config.custom_llm_provider
        logger.debug(
            "Streaming LLM setup for %s with %d base parameters",
            self.config.model,
            len(base_completion_kwargs),
        )
        return partial(self._call_acompletion, **base_completion_kwargs)

    def _process_streaming_messages(
        self,
        args: tuple,
        kwargs: dict,
        *,
        allow_empty: bool = False,
    ) -> list[dict[str, Any]]:
        """Process and validate messages for streaming completion.

        Args:
            args: Positional arguments.
            kwargs: Keyword arguments.

        Returns:
            list[dict[str, Any]]: Processed messages list.

        Raises:
            ValueError: If messages list is empty.

        """
        messages: list[dict[str, Any]] | dict[str, Any] = []

        if len(args) > 1:
            messages = args[1] if len(args) > 1 else args[0]
            kwargs["messages"] = messages
            args = args[2:]
        elif "messages" in kwargs:
            messages = kwargs["messages"]

        message_list = messages if isinstance(messages, list) else [messages] if messages else []
        if not message_list:
            if allow_empty:
                kwargs.setdefault("messages", [])
                return []
            msg = "The messages list is empty. At least one message is required."
            raise ValueError(msg)

        return message_list

    async def _process_streaming_chunks(self, resp, kwargs: dict) -> Any:
        """Process streaming chunks from the LLM response.

        Args:
            resp: The streaming response object.
            kwargs: Keyword arguments containing configuration.

        Yields:
            Any: Chunks from the streaming response.

        Raises:
            UserCancelledError: If cancellation is requested.

        """
        async for chunk in resp:
            if (
                hasattr(self.config, "on_cancel_requested_fn")
                and self.config.on_cancel_requested_fn is not None
                and await self.config.on_cancel_requested_fn()
            ):
                msg = "LLM request cancelled due to CANCELLED state"
                raise UserCancelledError(msg)

            if message_back := chunk["choices"][0]["delta"].get("content", ""):
                self.log_response(message_back)

            self._post_completion(chunk)
            yield chunk

    async def _async_streaming_completion_wrapper(self, *args: Any, **kwargs: Any) -> Any:
        """Wrapper for async streaming completion with retry logic.

        Args:
            *args: Positional arguments for completion.
            **kwargs: Keyword arguments for completion.

        Yields:
            Any: Chunks from the streaming response.

        """
        messages = self._process_streaming_messages(args, kwargs, allow_empty=True)

        if get_features(self.config.model).supports_reasoning_effort:
            kwargs["reasoning_effort"] = self.config.reasoning_effort

        self.log_prompt(messages)

        try:
            resp = self._base_async_streaming_completion(*args, **kwargs)
            if inspect.isawaitable(resp):
                resp = await resp
            async for chunk in self._process_streaming_chunks(resp, kwargs):
                yield chunk
        except UserCancelledError:
            logger.debug("LLM request cancelled by user.")
            raise
        except Exception as e:
            logger.error("Completion Error occurred:\n%s", e)
            raise
        finally:
            if kwargs.get("stream", False):
                await asyncio.sleep(0.1)

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        """Initialize the StreamingLLM with retry-decorated streaming completion.

        Args:
            *args: Arguments passed to parent class.
            **kwargs: Keyword arguments passed to parent class.

        """
        super().__init__(*args, **kwargs)

        # Create the base streaming completion function
        self._base_async_streaming_completion = self._create_streaming_completion_partial()

        # Apply retry decorator to the streaming completion wrapper
        self._async_streaming_completion = self.retry_decorator(
            num_retries=self.config.num_retries,
            retry_exceptions=LLM_RETRY_EXCEPTIONS,
            retry_min_wait=self.config.retry_min_wait,
            retry_max_wait=self.config.retry_max_wait,
            retry_multiplier=self.config.retry_multiplier,
        )(self._async_streaming_completion_wrapper)

    @property
    def async_streaming_completion(self) -> Callable:
        """Decorator for the async litellm acompletion function with streaming."""
        return self._async_streaming_completion
