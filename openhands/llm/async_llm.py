import asyncio
import contextlib
from functools import partial
from typing import Any, Callable

from litellm import acompletion as litellm_acompletion

from openhands.core.exceptions import UserCancelledError
from openhands.core.logger import openhands_logger as logger
from openhands.llm.llm import LLM, LLM_RETRY_EXCEPTIONS
from openhands.llm.model_features import get_features
from openhands.utils.shutdown_listener import should_continue


class AsyncLLM(LLM):
    """Asynchronous LLM class."""

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        # Import the API key manager for provider detection
        from openhands.core.config.api_key_manager import api_key_manager
        
        # Build base completion parameters
        base_completion_kwargs = {
            'model': self.config.model,
            'api_key': self.config.api_key.get_secret_value() if self.config.api_key else None,
            'max_tokens': self.config.max_output_tokens,
            'timeout': self.config.timeout,
            'temperature': self.config.temperature,
            'top_p': self.config.top_p,
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
        
        # CRITICAL: Use provider configuration to validate and clean parameters
        cleaned_completion_kwargs = api_key_manager.validate_and_clean_completion_params(
            self.config.model, base_completion_kwargs
        )
        
        self._async_completion = partial(self._call_acompletion, **cleaned_completion_kwargs)
        logger.debug(f"Async LLM setup for {self.config.model} with {len(cleaned_completion_kwargs)} validated parameters")
        async_completion_unwrapped = self._async_completion

        @self.retry_decorator(
            num_retries=self.config.num_retries,
            retry_exceptions=LLM_RETRY_EXCEPTIONS,
            retry_min_wait=self.config.retry_min_wait,
            retry_max_wait=self.config.retry_max_wait,
            retry_multiplier=self.config.retry_multiplier,
        )
        async def async_completion_wrapper(*args: Any, **kwargs: Any) -> Any:
            """Wrapper for the litellm acompletion function that adds logging and cost tracking."""
            # Process and validate messages
            messages = self._process_completion_args(args, kwargs)
            self._validate_messages(messages)

            # Configure completion parameters
            self._configure_completion_params(kwargs)

            # Log the prompt
            self.log_prompt(messages)

            # Execute completion with cancellation support
            return await self._execute_completion_with_cancellation(async_completion_unwrapped, args, kwargs)

    def _process_completion_args(self, args: tuple[Any, ...], kwargs: dict[str, Any]) -> list[dict[str, Any]]:
        """Process and extract messages from completion arguments.

        Args:
            args: Positional arguments passed to completion function.
            kwargs: Keyword arguments passed to completion function.

        Returns:
            list[dict[str, Any]]: Processed messages list.
        """
        messages: list[dict[str, Any]] | dict[str, Any] = []

        if len(args) > 1:
            messages = args[1] if len(args) > 1 else args[0]
            kwargs["messages"] = messages
            args = args[2:]
        elif "messages" in kwargs:
            messages = kwargs["messages"]

        return messages if isinstance(messages, list) else [messages]

    def _validate_messages(self, messages: list[dict[str, Any]]) -> None:
        """Validate that messages list is not empty.

        Args:
            messages: List of messages to validate.

        Raises:
            ValueError: If messages list is empty.
        """
        if not messages:
            msg = "The messages list is empty. At least one message is required."
            raise ValueError(msg)

    def _configure_completion_params(self, kwargs: dict[str, Any]) -> None:
        """Configure completion parameters based on model features.

        Args:
            kwargs: Keyword arguments to configure.
        """
        if get_features(self.config.model).supports_reasoning_effort:
            kwargs["reasoning_effort"] = self.config.reasoning_effort

    async def _execute_completion_with_cancellation(
        self,
        async_completion_unwrapped: Callable,
        args: tuple[Any, ...],
        kwargs: dict[str, Any],
    ) -> Any:
        """Execute completion with cancellation support.

        Args:
            async_completion_unwrapped: The unwrapped completion function.
            args: Positional arguments for completion.
            kwargs: Keyword arguments for completion.

        Returns:
            Any: The completion response.
        """
        stop_check_task = asyncio.create_task(self._create_stop_check_task())

        try:
            resp = await async_completion_unwrapped(*args, **kwargs)
            self._handle_completion_response(resp)
            return resp
        except UserCancelledError:
            logger.debug("LLM request cancelled by user.")
            raise
        except Exception as e:
            logger.error("Completion Error occurred:\n%s", e)
            raise
        finally:
            await self._cleanup_stop_check_task(stop_check_task)

    async def _create_stop_check_task(self) -> None:
        """Create and run the stop check task.

        This task continuously checks if the completion should be stopped.
        """
        while should_continue():
            if (
                hasattr(self.config, "on_cancel_requested_fn")
                and self.config.on_cancel_requested_fn is not None
                and await self.config.on_cancel_requested_fn()
            ):
                return
            await asyncio.sleep(0.1)

    def _handle_completion_response(self, resp: Any) -> None:
        """Handle the completion response by logging and post-processing.

        Args:
            resp: The completion response to handle.
        """
        message_back = resp["choices"][0]["message"]["content"]
        self.log_response(message_back)
        self._post_completion(resp)

    async def _cleanup_stop_check_task(self, stop_check_task: asyncio.Task) -> None:
        """Clean up the stop check task.

        Args:
            stop_check_task: The task to clean up.
        """
        await asyncio.sleep(0.1)
        stop_check_task.cancel()
        with contextlib.suppress(asyncio.CancelledError):
            await stop_check_task

        # Note: _async_completion is set during initialization, no need to reassign

    async def _call_acompletion(self, *args: Any, **kwargs: Any) -> Any:
        """Wrapper for the litellm acompletion function."""
        return await litellm_acompletion(*args, **kwargs)

    @property
    def async_completion(self) -> Callable:
        """Decorator for the async litellm acompletion function."""
        return self._async_completion
