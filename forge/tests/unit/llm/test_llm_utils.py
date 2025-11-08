"""Tests for `forge.llm.llm_utils`."""

from __future__ import annotations

from copy import deepcopy

from forge.core.config.llm_config import LLMConfig, suppress_llm_env_export
from forge.llm import llm_utils


def test_check_tools_passthrough_for_non_gemini() -> None:
    with suppress_llm_env_export():
        config = LLMConfig(model="gpt-4o")
    tools = [{"function": {"parameters": {"properties": {"value": {"type": "string"}}}}}]
    assert llm_utils.check_tools(tools, config) is tools


def test_check_tools_strips_defaults_and_unsupported_formats() -> None:
    with suppress_llm_env_export():
        config = LLMConfig(model="gemini-2.5-pro")

    original_tools = [
        {
            "function": {
                "parameters": {
                    "properties": {
                        "enum_value": {"type": "string", "format": "enum", "default": "keep"},
                        "dt_value": {"type": "string", "format": "date-time", "default": "2024-01-01"},
                        "custom": {"type": "string", "format": "uuid", "default": "remove-me"},
                    }
                }
            }
        }
    ]

    cleaned = llm_utils.check_tools(original_tools, config)
    assert cleaned is not original_tools  # deep copy

    properties = cleaned[0]["function"]["parameters"]["properties"]
    assert "default" not in properties["enum_value"]
    assert "default" not in properties["dt_value"]
    assert "default" not in properties["custom"]
    assert "format" not in properties["custom"]  # unsupported format removed
    assert "format" in properties["dt_value"]  # allowed format preserved

    # The original list should remain unchanged
    assert "default" in original_tools[0]["function"]["parameters"]["properties"]["enum_value"]

