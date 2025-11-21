from __future__ import annotations

import sys
import types
from typing import Any

from pydantic import BaseModel

if "litellm" not in sys.modules:
    _litellm_module = types.ModuleType("litellm")

    class _LiteLLMModelResponse(BaseModel):
        model: str | None = None
        choices: list[Any] = []

    class _LiteLLMModelInfo(BaseModel):
        model: str | None = None

    class _LiteLLMPromptTokensDetails(BaseModel):
        prompt_name: str | None = None

    class _LiteLLMChatCompletionToolParam(BaseModel):
        function: dict[str, Any] = {}

    class _LiteLLMCostPerToken(BaseModel):
        cost: float = 0.0

    class _LiteLLMUsage(BaseModel):
        total_tokens: int = 0

    _litellm_module.ModelResponse = _LiteLLMModelResponse
    _litellm_module.ModelInfo = _LiteLLMModelInfo
    _litellm_module.PromptTokensDetails = _LiteLLMPromptTokensDetails
    _litellm_module.ChatCompletionToolParam = _LiteLLMChatCompletionToolParam
    _litellm_module.CostPerToken = _LiteLLMCostPerToken
    _litellm_module.Usage = _LiteLLMUsage
    _litellm_module.APIConnectionError = RuntimeError
    _litellm_module.APIError = RuntimeError
    _litellm_module.AuthenticationError = RuntimeError
    _litellm_module.BadRequestError = RuntimeError
    _litellm_module.ContentPolicyViolationError = RuntimeError
    _litellm_module.ContextWindowExceededError = RuntimeError
    _litellm_module.InternalServerError = RuntimeError
    _litellm_module.NotFoundError = RuntimeError
    _litellm_module.OpenAIError = RuntimeError
    _litellm_module.RateLimitError = RuntimeError
    _litellm_module.ServiceUnavailableError = RuntimeError
    _litellm_module.Timeout = RuntimeError
    _litellm_module.acompletion = lambda *args, **kwargs: None
    _litellm_module.completion = lambda *args, **kwargs: None
    _litellm_module.completion_cost = lambda *args, **kwargs: 0
    _litellm_module.suppress_debug_info = True
    _litellm_module.set_verbose = False
    _litellm_utils = types.ModuleType("litellm.utils")
    _litellm_utils.create_pretrained_tokenizer = lambda *args, **kwargs: None
    _litellm_utils.get_model_info = lambda *args, **kwargs: {}
    _litellm_exceptions = types.ModuleType("litellm.exceptions")
    for _name, _exc in {
        "APIConnectionError": RuntimeError,
        "APIError": RuntimeError,
        "AuthenticationError": RuntimeError,
        "BadRequestError": RuntimeError,
        "ContentPolicyViolationError": RuntimeError,
        "ContextWindowExceededError": RuntimeError,
        "InternalServerError": RuntimeError,
        "NotFoundError": RuntimeError,
        "OpenAIError": RuntimeError,
        "RateLimitError": RuntimeError,
        "ServiceUnavailableError": RuntimeError,
        "Timeout": RuntimeError,
    }.items():
        setattr(_litellm_exceptions, _name, _exc)
    _litellm_types_utils = types.ModuleType("litellm.types.utils")
    _litellm_types_utils.CostPerToken = _litellm_module.CostPerToken
    _litellm_types_utils.ModelResponse = _litellm_module.ModelResponse
    _litellm_types_utils.Usage = _litellm_module.Usage
    _litellm_module.utils = _litellm_utils
    _litellm_module.exceptions = _litellm_exceptions
    _litellm_module.create_pretrained_tokenizer = (
        _litellm_utils.create_pretrained_tokenizer
    )
    _litellm_module.get_model_info = _litellm_utils.get_model_info
    sys.modules["litellm"] = _litellm_module
    sys.modules["litellm.utils"] = _litellm_utils
    sys.modules["litellm.exceptions"] = _litellm_exceptions
    sys.modules["litellm.types.utils"] = _litellm_types_utils
if "tokenizers" not in sys.modules:
    sys.modules["tokenizers"] = types.ModuleType("tokenizers")

import pytest

from forge.core.config.agent_config import (
    AgentConfig,
    CURRENT_AGENT_CONFIG_SCHEMA_VERSION,
)
from forge.core.config.config_telemetry import config_telemetry


def test_agent_config_condenser_alias():
    config = AgentConfig()
    new_condenser = type(config.condenser_config)()
    config.condenser = new_condenser
    assert config.condenser is new_condenser


def test_agent_config_get_llm_config_override():
    config = AgentConfig()
    assert config.get_llm_config() is None

    from forge.core.config.llm_config import LLMConfig

    llm_config = LLMConfig(model="mock")
    config.llm_config = llm_config
    assert config.get_llm_config() is llm_config


def test_agent_config_resolved_system_prompt_filename_handles_invalid():
    config = AgentConfig()
    config.system_prompt_filename = 123  # type: ignore[assignment]
    assert config.resolved_system_prompt_filename == "system_prompt.j2"


def test_agent_config_resolved_system_prompt_filename_returns_value():
    config = AgentConfig(system_prompt_filename="custom_prompt.j2")
    assert config.resolved_system_prompt_filename == "custom_prompt.j2"


def test_agent_config_separate_base_and_custom_sections_handles_llm():
    data = {
        "name": "BaseAgent",
        "llm_config": {"model": "gpt-4o"},
        "agent.Custom": {"enable_browsing": False},
    }
    base, custom = AgentConfig._separate_base_and_custom_sections(data)
    assert "llm_config" in base
    assert "agent.Custom" in custom


def test_agent_config_create_custom_config_rejects_invalid_fields():
    base = AgentConfig()
    with pytest.raises(ValueError, match="Unknown field"):
        AgentConfig._create_custom_config("Invalid", base, {"unknown": True})


def test_agent_config_create_custom_config_merges_overrides():
    base = AgentConfig(enable_browsing=False, enable_prompt_extensions=True)
    overrides = {"enable_browsing": True, "enable_prompt_extensions": False}
    custom = AgentConfig._create_custom_config("CustomAgent", base, overrides)
    assert custom is not None
    assert custom.name == "CustomAgent"
    assert custom.enable_browsing is True
    assert custom.enable_prompt_extensions is False


def test_agent_config_from_toml_section_alias_and_invalid_handling():
    data = {
        "memory_max_threads": "invalid",
        "CustomAgent": {"memory_max_threads": "bad", "enable_browsing": False},
    }

    with pytest.raises(ValueError):
        AgentConfig.from_toml_section(data)


def test_agent_config_schema_version_missing_records():
    config_telemetry.reset()
    AgentConfig.from_dict({})
    snapshot = config_telemetry.snapshot()
    assert snapshot["schema_missing"] == 1


def test_agent_config_schema_version_mismatch_records():
    config_telemetry.reset()
    AgentConfig.from_dict({"schema_version": "1900-01-01"})
    snapshot = config_telemetry.snapshot()
    assert snapshot["schema_mismatch"] == {"1900-01-01": 1}


def test_agent_config_schema_version_match_no_warning():
    config_telemetry.reset()
    AgentConfig.from_dict({"schema_version": CURRENT_AGENT_CONFIG_SCHEMA_VERSION})
    snapshot = config_telemetry.snapshot()
    assert snapshot["schema_missing"] == 0
    assert snapshot["schema_mismatch"] == {}


def test_agent_config_invalid_custom_records_telemetry():
    config_telemetry.reset()
    data = {
        "schema_version": CURRENT_AGENT_CONFIG_SCHEMA_VERSION,
        "agent.Bad": {"unknown_field": True},
    }
    with pytest.raises(ValueError):
        AgentConfig.from_dict(data)
    snapshot = config_telemetry.snapshot()
    assert snapshot["invalid_agents"] == {"agent.Bad": 1}
