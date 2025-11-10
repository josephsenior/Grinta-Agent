from __future__ import annotations

import argparse
import os
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest
from pydantic import BaseModel, SecretStr

from forge.core.config import utils as utils_module
from forge.core.config.agent_config import AgentConfig
from forge.core.config.forge_config import ForgeConfig
from forge.core.config.llm_config import LLMConfig
from forge.core.config.sandbox_config import SandboxConfig


class DummySubConfig(BaseModel):
    count: int = 0


class DummyConfig(BaseModel):
    nested: DummySubConfig = DummySubConfig()
    enabled: bool = False
    api_key: SecretStr | None = None
    model: str = "gpt-4o"
    count: int = 0


class RecordingAPIKeyManager:
    def __init__(self):
        self.calls: list[tuple[str, SecretStr]] = []

    def set_api_key(self, model: str, key: SecretStr):
        self.calls.append(("set", model, key))

    def set_environment_variables(self, model: str, key: SecretStr):
        self.calls.append(("env", model, key))


class DummyFileStore:
    def __init__(self):
        self.storage: dict[str, str] = {}
        self.read_called = False
        self.write_called = False

    def read(self, key: str) -> str:
        self.read_called = True
        if key not in self.storage:
            raise FileNotFoundError
        return self.storage[key]

    def write(self, key: str, value: str) -> None:
        self.write_called = True
        self.storage[key] = value


def test_to_posix_workspace_path_converts_windows_path():
    assert utils_module._to_posix_workspace_path("C:\\code\\project") == "/code/project"
    assert utils_module._to_posix_workspace_path("/already/posix/") == "/already/posix"


def test_get_optional_type_and_list_processing():
    optional_type = int | None
    assert utils_module._get_optional_type(optional_type) is int
    assert utils_module._is_dict_or_list_type(dict[str, int])

    class Item(BaseModel):
        value: int

    result = utils_module._process_list_items([{"value": 1}], list[Item])
    assert isinstance(result[0], Item)


def test_cast_value_to_type_handles_bool_list_and_secret():
    assert utils_module._cast_value_to_type("true", bool) is True
    assert utils_module._cast_value_to_type("[1, 2]", list[int]) == [1, 2]
    casted = utils_module._cast_value_to_type("secret", SecretStr)
    assert isinstance(casted, SecretStr)
    assert casted.get_secret_value() == "secret"


def test_process_field_value_sets_api_key(monkeypatch: pytest.MonkeyPatch):
    dummy_manager = RecordingAPIKeyManager()
    monkeypatch.setattr("forge.core.config.api_key_manager.api_key_manager", dummy_manager)
    config = DummyConfig()
    env = {"API_KEY": "sk-test-value"}
    field_type = DummyConfig.model_fields["api_key"].annotation
    utils_module._process_field_value(config, "api_key", field_type, "API_KEY", env)
    assert config.api_key.get_secret_value() == "sk-test-value"
    assert dummy_manager.calls and dummy_manager.calls[0][0] == "set"


def test_process_field_value_handles_invalid(monkeypatch: pytest.MonkeyPatch):
    config = DummyConfig()
    env = {"COUNT": "not-an-int"}
    field_type = DummyConfig.model_fields["count"].annotation
    utils_module._process_field_value(config, "count", field_type, "COUNT", env)
    assert config.count == 0


def test_set_attr_from_env_with_nested_model(monkeypatch: pytest.MonkeyPatch):
    dummy_manager = RecordingAPIKeyManager()
    monkeypatch.setattr("forge.core.config.api_key_manager.api_key_manager", dummy_manager)
    config = DummyConfig()
    env = {"ENABLED": "true", "NESTED_COUNT": "5", "API_KEY": "sk-inner"}
    utils_module._set_attr_from_env(config, env)
    assert config.enabled is True
    assert config.nested.count == 5
    assert config.api_key.get_secret_value() == "sk-inner"


def test_restore_environment_removes_added_variables(monkeypatch: pytest.MonkeyPatch):
    original = {"KEEP": "1"}
    monkeypatch.setenv("KEEP", "1")
    monkeypatch.setenv("DROP", "x")
    utils_module._restore_environment(original)
    assert "DROP" not in os.environ
    assert os.environ["KEEP"] == "1"


def test_export_llm_api_keys(monkeypatch: pytest.MonkeyPatch):
    dummy_manager = RecordingAPIKeyManager()
    monkeypatch.setattr("forge.core.config.api_key_manager.api_key_manager", dummy_manager)
    config = ForgeConfig()
    config.set_llm_config(LLMConfig(model="gpt-4o", api_key=SecretStr("sk-export")))
    utils_module._export_llm_api_keys(config)
    assert dummy_manager.calls


def test_process_core_agent_and_llm_sections(monkeypatch: pytest.MonkeyPatch):
    config = ForgeConfig()
    utils_module._process_core_section({"default_agent": "CustomAgent", "unknown": 1}, config)
    assert config.default_agent == "CustomAgent"
    utils_module._process_agent_section({"agent": {"CustomAgent": {"enable_prompt_extensions": False}}}, config)
    assert not config.get_agent_config("CustomAgent").enable_prompt_extensions
    utils_module._process_llm_section({"llm": {"model": "gpt-4o", "api_key": "from-toml"}}, config)
    assert config.get_llm_config().model == "gpt-4o"


def test_process_mcp_kubernetes_and_sandbox_sections():
    config = ForgeConfig()
    utils_module._process_mcp_section({"mcp": {"sse_servers": [{"url": "https://example.com"}]}}, config)
    utils_module._process_kubernetes_section({"kubernetes": {"namespace": "custom"}}, config)
    utils_module._process_sandbox_section({"sandbox": {"volumes": "/tmp/workspace:/workspace:rw"}}, config)
    assert config.kubernetes.namespace == "custom"
    assert config.sandbox.volumes == "/tmp/workspace:/workspace:rw"
    assert config.workspace_mount_path_in_sandbox == "/workspace"


def test_process_condenser_section_assigns_default():
    config = ForgeConfig()
    utils_module._process_condenser_section({}, config)
    assert config.get_agent_config().condenser_config is not None


def test_handle_sandbox_volumes_valid_and_invalid():
    config = ForgeConfig()
    config.sandbox = SandboxConfig(volumes="/host/work:/workspace:rw")
    utils_module._handle_sandbox_volumes(config)
    assert config.workspace_base.endswith("work")
    config.sandbox = SandboxConfig(volumes="/invalid")
    with pytest.raises(ValueError):
        utils_module._handle_sandbox_volumes(config)


def test_handle_deprecated_workspace_vars(caplog):
    config = ForgeConfig()
    config.workspace_base = "workspace"
    config.workspace_mount_rewrite = "/workspace:/sandbox"
    utils_module._handle_deprecated_workspace_vars(config)
    assert config.workspace_mount_path_in_sandbox == "/sandbox"


def test_configure_cli_runtime_agents():
    config = ForgeConfig()
    agent = AgentConfig(enable_jupyter=True, enable_browsing=True)
    config.agents["Custom"] = agent
    config.runtime = "cli"
    utils_module._configure_cli_runtime_agents(config)
    assert not config.agents["Custom"].enable_jupyter
    config.runtime = "docker"
    config.agents["Custom"].enable_jupyter = True
    config.agents["Custom"].model_fields_set.add("enable_jupyter")
    utils_module._configure_cli_runtime_agents(config)
    assert config.agents["Custom"].enable_jupyter


def test_get_or_create_jwt_secret(monkeypatch: pytest.MonkeyPatch):
    store = DummyFileStore()
    monkeypatch.setattr(utils_module, "get_file_store", lambda *_args, **_kwargs: store)
    secret = utils_module.get_or_create_jwt_secret(store)
    assert store.write_called
    store.storage[utils_module.JWT_SECRET] = "existing"
    assert utils_module.get_or_create_jwt_secret(store) == "existing"


def test_parse_arguments(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(
        utils_module.sys,
        "argv",
        ["forge", "--config-file", "custom.toml", "--max-iterations", "2"],
    )
    args = utils_module.parse_arguments()
    assert args.config_file == "custom.toml"
    assert args.max_iterations == 2


def test_register_custom_agents(monkeypatch: pytest.MonkeyPatch):
    def fake_get_impl(base, classpath):
        class FakeAgent:
            pass

        return FakeAgent

    config = ForgeConfig()
    config.agents["Custom"] = SimpleNamespace(classpath="package.module:Agent")

    monkeypatch.setattr(utils_module, "get_impl", fake_get_impl)
    from forge.controller.agent import Agent

    records: list[tuple[str, Any]] = []

    def fake_register(cls, name, impl):
        records.append((name, impl))

    monkeypatch.setattr(Agent, "register", classmethod(fake_register))
    utils_module.register_custom_agents(config)
    assert records and records[0][0] == "Custom"


def test_resolve_llm_config_from_cli_and_try_user(tmp_path, monkeypatch: pytest.MonkeyPatch):
    config = ForgeConfig()
    custom = LLMConfig(model="mock", api_key=SecretStr("sk-1"))
    config.set_llm_config(custom, "custom")
    assert utils_module._resolve_llm_config_from_cli("custom", config, "config.toml") is custom

    user_config_dir = tmp_path / ".Forge"
    user_config_dir.mkdir()
    user_toml = user_config_dir / "config.toml"
    user_toml.write_text(
        "[llm.custom]\nmodel = \"from-user\"\napi_key = \"user-key\"\n",
        encoding="utf-8",
    )
    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.setenv("USERPROFILE", str(tmp_path))
    result = utils_module._try_user_config_llm("custom", "other.toml")
    assert result.model == "from-user"

