from __future__ import annotations

import sys
import types
from typing import Any

from pydantic import BaseModel

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
