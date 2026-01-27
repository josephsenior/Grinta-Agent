"""Debug mixin offering prompt/response logging for Forge LLM classes."""

from __future__ import annotations

from logging import DEBUG
from typing import TYPE_CHECKING, Any

from forge.core.logger import llm_prompt_logger, llm_response_logger
from forge.core.logger import forge_logger as logger

if TYPE_CHECKING:
    pass

MESSAGE_SEPARATOR = "\n\n----------\n\n"


class DebugMixin:
    """Provide lightweight logging helpers to inspect prompts/responses in tests."""

    def __init__(self, *args, debug: bool = False, **kwargs) -> None:
        """Store the debug flag so subclasses can toggle verbose logging."""
        self.debug = debug

    def log_prompt(self, messages: list[dict[str, Any]] | dict[str, Any]) -> None:
        """Log prompt messages for debugging.

        Args:
            messages: Message or list of messages to log

        """
        if not logger.isEnabledFor(DEBUG):
            return
        if not messages:
            logger.debug("No completion messages!")
            return
        messages = messages if isinstance(messages, list) else [messages]
        if debug_message := MESSAGE_SEPARATOR.join(
            self._format_message_content(msg)
            for msg in messages
            if msg.get("content") is not None
        ):
            llm_prompt_logger.debug(debug_message)
        else:
            logger.debug("No completion messages!")

    def log_response(self, resp: dict[str, Any] | str) -> None:
        """Log LLM response for debugging.

        Args:
            resp: Model response dict or content string to log

        """
        if not logger.isEnabledFor(DEBUG):
            return
            
        if isinstance(resp, str):
            if resp:
                llm_response_logger.debug(resp)
            return
            
        message_back: str = ""
        if resp.get("choices") and resp["choices"][0].get("message"):
            msg = resp["choices"][0]["message"]
            message_back = msg.get("content") or ""
            if tool_calls := msg.get("tool_calls", []):
                for tool_call in tool_calls:
                    # Support both object and dict styles
                    if hasattr(tool_call, "function"):
                        fn_name = tool_call.function.name
                        fn_args = tool_call.function.arguments
                    else:
                        fn_name = tool_call.get("function", {}).get("name")
                        fn_args = tool_call.get("function", {}).get("arguments")
                    message_back += f"\nFunction call: {fn_name}({fn_args})"
        
        if message_back:
            llm_response_logger.debug(message_back)

    def _format_message_content(self, message: dict[str, Any]) -> str:
        content = message["content"]
        if isinstance(content, list):
            return "\n".join(
                self._format_content_element(element) for element in content
            )
        return str(content)

    def _format_content_element(self, element: dict[str, Any] | Any) -> str:
        if isinstance(element, dict):
            if "text" in element:
                return str(element["text"])
            if (
                self.vision_is_active()
                and "image_url" in element
                and ("url" in element["image_url"])
            ):
                return str(element["image_url"]["url"])
        return str(element)

    def vision_is_active(self) -> bool:
        """Check if vision is active (must be implemented by subclass)."""
        raise NotImplementedError
