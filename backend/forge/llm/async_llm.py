# coverage: ignore file
"""Async LLM client integrating litellm completion with Forge configuration."""

import asyncio
import contextlib
from functools import partial
from importlib import import_module
from typing import Any, Callable

# Be resilient to litellm versions or environments without the package
try:
    from litellm import acompletion as litellm_acompletion  # type: ignore[attr-defined]
except Exception:
    try:
        import litellm  # type: ignore
    except Exception:
        async def litellm_acompletion(*args: Any, **kwargs: Any) -> Any:  # type: ignore[override]
            raise ImportError("litellm is not available")
    else:
        async def litellm_acompletion(*args: Any, **kwargs: Any) -> Any:  # type: ignore[override]
            """Fallback async wrapper for synchronous `litellm.completion`.

            Some litellm versions do not expose `acompletion` at the package root.
            This wrapper allows imports to succeed during test collection.
            """
            func = getattr(litellm, "acompletion", None)
            if callable(func):  # if available after monkeypatching
                return await func(*args, **kwargs)  # type: ignore[misc]

            sync_completion = getattr(litellm, "completion", None)
            if not callable(sync_completion):
                raise ImportError("litellm completion/acompletion not available")

            loop = None
            try:
                loop = asyncio.get_running_loop()
            except RuntimeError:
                pass
            if loop is None:
                loop = asyncio.new_event_loop()
                try:
                    return await loop.run_in_executor(None, lambda: sync_completion(*args, **kwargs))
                finally:
                    loop.close()
            return await loop.run_in_executor(None, lambda: sync_completion(*args, **kwargs))

from forge.core.exceptions import UserCancelledError
from forge.core.logger import forge_logger as logger
from forge.llm.llm import LLM, LLM_RETRY_EXCEPTIONS
from forge.llm.model_features import get_features
from forge.utils.shutdown_listener import should_continue

# Backwards compatibility for imports expecting ``forge.llm.async_llm.llm``.
llm = import_module("forge.llm.llm")


class AsyncLLM(LLM):
    """Asynchronous LLM class."""

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        """Configure the asynchronous completion pipeline and provider-specific parameters."""
        super().__init__(*args, **kwargs)
        # Build base completion parameters
        base_completion_kwargs = {
            "model": self.config.model,
            "api_key": self.config.api_key.get_secret_value()
            if self.config.api_key
            else None,
            "max_tokens": self.config.max_output_tokens,
            "timeout": self.config.timeout,
            "temperature": self.config.temperature,
            "top_p": self.config.top_p,
            "drop_params": self.config.drop_params,
            "seed": self.config.seed,
        }

        # Add optional parameters if they exist
        if self.config.base_url is not None:
            base_completion_kwargs["base_url"] = self.config.base_url
        if self.config.api_version is not None:
            base_completion_kwargs["api_version"] = self.config.api_version
        if self.config.custom_llm_provider is not None:
            base_completion_kwargs["custom_llm_provider"] = (
                self.config.custom_llm_provider
            )

        self._base_async_completion = partial(
            self._call_acompletion, **base_completion_kwargs
        )
        logger.debug(
            "Async LLM setup for %s with %d base parameters",
            self.config.model,
            len(base_completion_kwargs),
        )

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
            return await self._execute_completion_with_cancellation(
                self._base_async_completion, args, kwargs
            )

        self._async_completion = async_completion_wrapper

    def _process_completion_args(
        self, args: tuple[Any, ...], kwargs: dict[str, Any]
    ) -> list[dict[str, Any]]:
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
