"""Utilities for adapting tool schemas to specific LLM provider constraints."""

import copy
from typing import TYPE_CHECKING

from forge.core.config import LLMConfig
from forge.core.logger import forge_logger as logger

if TYPE_CHECKING:
    from litellm import ChatCompletionToolParam


def check_tools(tools: list["ChatCompletionToolParam"], llm_config: LLMConfig) -> list["ChatCompletionToolParam"]:
    """Checks and modifies tools for compatibility with the current LLM.

    Args:
        tools: List of tool parameters
        llm_config: LLM configuration

    Returns:
        Modified tools compatible with the LLM

    """
    if "gemini" not in llm_config.model.lower():
        return tools

    logger.info(
        "Removing default fields and unsupported formats from tools for Gemini model %s "
        "since Gemini models have limited format support (only 'enum' and 'date-time' for STRING types).",
        llm_config.model,
    )

    return _clean_tools_for_gemini(tools)


def _clean_tools_for_gemini(tools: list["ChatCompletionToolParam"]) -> list["ChatCompletionToolParam"]:
    """Remove unsupported fields and formats for Gemini models.

    Args:
        tools: List of tool parameters

    Returns:
        Cleaned tools

    """
    checked_tools = copy.deepcopy(tools)

    for tool in checked_tools:
        if "function" in tool and "parameters" in tool["function"]:
            if "properties" in tool["function"]["parameters"]:
                _clean_tool_properties(tool["function"]["parameters"]["properties"])

    return checked_tools


def _clean_tool_properties(properties: dict) -> None:
    """Clean tool properties for Gemini compatibility.

    Args:
        properties: Tool properties dict (modified in place)

    """
    for prop_name, prop in properties.items():
        # Remove default values
        if "default" in prop:
            del prop["default"]

        # Remove unsupported string formats
        if prop.get("type") == "string" and "format" in prop:
            if prop["format"] not in ["enum", "date-time"]:
                logger.info(
                    'Removing unsupported format "%s" for STRING parameter "%s"',
                    prop["format"],
                    prop_name,
                )
                del prop["format"]
