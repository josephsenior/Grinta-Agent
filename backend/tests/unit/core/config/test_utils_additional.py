from __future__ import annotations

import argparse
import logging
import os
import sys
import textwrap
import types
from pathlib import Path
from types import SimpleNamespace
from typing import Any

from pydantic import BaseModel

if "tokenizers" not in sys.modules:
    sys.modules["tokenizers"] = types.ModuleType("tokenizers")

import pytest
from pydantic import BaseModel, SecretStr

from forge.core.config import utils as utils_module
from forge.core.config.agent_config import AgentConfig
from forge.core.config.forge_config import ForgeConfig
from forge.core.config.llm_config import LLMConfig
from forge.core.config.sandbox_config import SandboxConfig
from forge.core.config.mcp_config import MCPConfig
from forge.core.config.security_config import SecurityConfig
from forge.core.logger import FORGE_logger


@pytest.fixture(autouse=True)
def setup_home(tmp_path, monkeypatch):
    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.setenv("USERPROFILE", str(tmp_path))


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
    monkeypatch.setattr(
        "forge.core.config.api_key_manager.api_key_manager", dummy_manager
    )
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
    monkeypatch.setattr(
        "forge.core.config.api_key_manager.api_key_manager", dummy_manager
    )
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
    monkeypatch.setattr(
        "forge.core.config.api_key_manager.api_key_manager", dummy_manager
    )
    config = ForgeConfig()
    config.set_llm_config(LLMConfig(model="gpt-4o", api_key=SecretStr("sk-export")))
    utils_module._export_llm_api_keys(config)
    assert dummy_manager.calls


def test_process_core_agent_and_llm_sections(monkeypatch: pytest.MonkeyPatch):
    config = ForgeConfig()
    utils_module._process_core_section(
        {"default_agent": "CustomAgent", "unknown": 1}, config
    )
    assert config.default_agent == "CustomAgent"
    utils_module._process_agent_section(
        {"agent": {"CustomAgent": {"enable_prompt_extensions": False}}}, config
    )
    assert not config.get_agent_config("CustomAgent").enable_prompt_extensions
    utils_module._process_llm_section(
        {"llm": {"model": "gpt-4o", "api_key": "from-toml"}}, config
    )
    assert config.get_llm_config().model == "gpt-4o"


def test_process_mcp_and_sandbox_sections():
    config = ForgeConfig()
    utils_module._process_mcp_section(
        {"mcp": {"sse_servers": [{"url": "https://example.com"}]}}, config
    )
    utils_module._process_sandbox_section(
        {"sandbox": {"timeout": 30}}, config
    )
    assert config.mcp.sse_servers[0].url == "https://example.com"
    assert config.sandbox.timeout == 30


def test_process_condenser_section_assigns_default():
    config = ForgeConfig()
    utils_module._process_condenser_section({}, config)
    assert config.get_agent_config().condenser_config is not None


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


def test_resolve_llm_config_from_cli_and_try_user(
    tmp_path, monkeypatch: pytest.MonkeyPatch
):
    config = ForgeConfig()
    custom = LLMConfig(model="mock", api_key=SecretStr("sk-1"))
    config.set_llm_config(custom, "custom")
    assert (
        utils_module._resolve_llm_config_from_cli("custom", config, "config.toml")
        is custom
    )

    user_config_dir = tmp_path / ".Forge"
    user_config_dir.mkdir()
    user_toml = user_config_dir / "config.toml"
    user_toml.write_text(
        '[llm.custom]\nmodel = "from-user"\napi_key = "user-key"\n',
        encoding="utf-8",
    )
    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.setenv("USERPROFILE", str(tmp_path))
    result = utils_module._try_user_config_llm("custom", "other.toml")
    assert result.model == "from-user"


def test_process_security_section_value_error(monkeypatch: pytest.MonkeyPatch):
    config = ForgeConfig()

    def raise_value_error(cls, section):
        raise ValueError("boom")

    monkeypatch.setattr(
        utils_module.SecurityConfig,
        "from_toml_section",
        classmethod(raise_value_error),
    )

    with pytest.raises(ValueError) as exc:
        utils_module._process_security_section({"security": {}}, config)

    assert "Error in [security] section" in str(exc.value)


def test_process_sandbox_section_value_error(monkeypatch: pytest.MonkeyPatch):
    config = ForgeConfig()

    def raise_value_error(cls, section):
        raise ValueError("boom")

    monkeypatch.setattr(
        utils_module.SandboxConfig,
        "from_toml_section",
        classmethod(raise_value_error),
    )

    with pytest.raises(ValueError):
        utils_module._process_sandbox_section({"sandbox": {}}, config)


def test_process_mcp_section_value_error(monkeypatch: pytest.MonkeyPatch):
    config = ForgeConfig()

    def raise_value_error(cls, section):
        raise ValueError("boom")

    monkeypatch.setattr(
        utils_module.MCPConfig,
        "from_toml_section",
        classmethod(raise_value_error),
    )

    with pytest.raises(ValueError):
        utils_module._process_mcp_section({"mcp": {}}, config)


def test_process_condenser_section_error(monkeypatch: pytest.MonkeyPatch):
    config = ForgeConfig()

    def raise_type_error(*_args, **_kwargs):
        raise TypeError("bad condenser")

    monkeypatch.setattr(
        "forge.core.config.condenser_config.condenser_config_from_toml_section",
        raise_type_error,
    )

    utils_module._process_condenser_section({"condenser": {"default": {}}}, config)


def test_process_extended_section_handles_error(monkeypatch: pytest.MonkeyPatch):
    config = ForgeConfig()

    def raise_type_error(_value):
        raise TypeError("bad extended")

    monkeypatch.setattr(utils_module, "ExtendedConfig", raise_type_error)

    utils_module._process_extended_section({"extended": {"meta": 1}}, config)


def test_check_unknown_sections_warns():
    utils_module._check_unknown_sections({"core": {}, "custom": {}}, "config.toml")


def test_load_from_toml_missing_file(tmp_path):
    config = ForgeConfig()
    missing_path = tmp_path / "missing.toml"
    utils_module.load_from_toml(config, str(missing_path))
    # No exception and defaults remain intact
    assert config.max_iterations == ForgeConfig().max_iterations


def test_load_from_toml_decode_error(tmp_path):
    bad_toml = tmp_path / "bad.toml"
    bad_toml.write_text("[core\ninvalid", encoding="utf-8")
    config = ForgeConfig()
    utils_module.load_from_toml(config, str(bad_toml))
    assert config.max_iterations == ForgeConfig().max_iterations


def test_validate_condenser_section_missing():
    result = utils_module._validate_condenser_section({}, "default", "cfg.toml")
    assert result is None


def test_process_llm_condenser_success(monkeypatch: pytest.MonkeyPatch):
    llm = LLMConfig(model="mock")
    monkeypatch.setattr(utils_module, "get_llm_config_arg", lambda name, toml_file: llm)

    data = {"llm_config": "llm.mock"}
    processed = utils_module._process_llm_condenser(data, "custom", "config.toml")
    assert processed["llm_config"] is llm


def test_process_llm_condenser_missing(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(
        utils_module, "get_llm_config_arg", lambda *_args, **_kwargs: None
    )
    result = utils_module._process_llm_condenser(
        {"llm_config": "missing"}, "custom", "cfg.toml"
    )
    assert result is None


def test_create_condenser_config_error(monkeypatch: pytest.MonkeyPatch):
    def raise_value_error(_ctype, _data):
        raise ValueError("bad condenser")

    monkeypatch.setattr(
        "forge.core.config.condenser_config.create_condenser_config",
        raise_value_error,
    )

    result = utils_module._create_condenser_config("noop", {}, "custom", "cfg.toml")
    assert result is None


def test_get_condenser_config_arg_success(tmp_path, monkeypatch: pytest.MonkeyPatch):
    config_path = tmp_path / "config.toml"
    config_path.write_text(
        textwrap.dedent(
            """
            [condenser.default]
            type = "noop"
            """
        ),
        encoding="utf-8",
    )

    sentinel = object()
    monkeypatch.setattr(
        "forge.core.config.condenser_config.create_condenser_config",
        lambda *_args, **_kwargs: sentinel,
    )

    result = utils_module.get_condenser_config_arg(
        "[condenser.default]", str(config_path)
    )
    assert result is sentinel


def test_get_condenser_config_arg_missing_section(tmp_path):
    config_path = tmp_path / "config.toml"
    config_path.write_text('[condenser.other]\ntype = "noop"\n', encoding="utf-8")
    result = utils_module.get_condenser_config_arg(
        "[condenser.missing]", str(config_path)
    )
    assert result is None


def test_load_toml_config_handles_errors(tmp_path):
    missing = tmp_path / "missing.toml"
    assert utils_module._load_toml_config(str(missing)) is None

    bad = tmp_path / "bad.toml"
    bad.write_text("[invalid", encoding="utf-8")
    assert utils_module._load_toml_config(str(bad)) is None


def test_apply_llm_config_override(monkeypatch: pytest.MonkeyPatch):
    config = ForgeConfig()
    args = SimpleNamespace(llm_config="custom", config_file="cfg.toml")
    llm = LLMConfig(model="mock")

    monkeypatch.setattr(
        utils_module, "_resolve_llm_config_from_cli", lambda *_args: llm
    )

    utils_module._apply_llm_config_override(config, args)
    assert config.get_llm_config().model == "mock"


def test_apply_additional_overrides():
    config = ForgeConfig()
    args = SimpleNamespace(
        agent_cls="CustomAgent",
        max_iterations=7,
        max_budget_per_task=12.5,
    )

    utils_module._apply_additional_overrides(config, args)
    assert config.default_agent == "CustomAgent"
    assert config.max_iterations == 7
    assert config.max_budget_per_task == 12.5


def test_apply_additional_overrides_no_attrs():
    config = ForgeConfig()
    args = SimpleNamespace()
    utils_module._apply_additional_overrides(config, args)
    # Should not raise or change defaults
    assert config.default_agent == ForgeConfig().default_agent


def test_to_posix_workspace_path_edge_cases():
    assert utils_module._to_posix_workspace_path("") == ""
    assert utils_module._to_posix_workspace_path("//nested//path//") == "/nested/path"


def test_get_optional_type_handles_non_union():
    assert utils_module._get_optional_type(int) is int


def test_process_field_value_empty_string():
    config = DummyConfig()
    env = {"COUNT": ""}
    utils_module._process_field_value(config, "count", int, "COUNT", env)
    assert config.count == 0


def test_export_llm_api_keys_handles_exception(monkeypatch: pytest.MonkeyPatch):
    config = ForgeConfig()
    config.set_llm_config(LLMConfig(model="gpt-export", api_key=SecretStr("sk-export")))

    class RaisingManager:
        def set_api_key(self, *_args, **_kwargs):
            raise RuntimeError("boom")

        def set_environment_variables(self, *_args, **_kwargs):
            raise RuntimeError("boom")

    monkeypatch.setattr(
        "forge.core.config.api_key_manager.api_key_manager", RaisingManager()
    )
    utils_module._export_llm_api_keys(config)


def test_process_agent_section_error(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(
        AgentConfig,
        "from_dict",
        classmethod(lambda cls, data: (_ for _ in ()).throw(TypeError("bad"))),
    )
    config = ForgeConfig()
    utils_module._process_agent_section({"agent": {}}, config)
    assert config.agents == {}


def test_process_llm_section_error(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(
        LLMConfig,
        "from_toml_section",
        classmethod(lambda cls, data: (_ for _ in ()).throw(TypeError("bad"))),
    )
    config = ForgeConfig()
    utils_module._process_llm_section({"llm": {}}, config)
    assert config.llms == {}


def test_process_security_sandbox_mcp_errors(
    monkeypatch: pytest.MonkeyPatch,
):
    monkeypatch.setattr(
        SecurityConfig,
        "from_toml_section",
        classmethod(lambda cls, data: (_ for _ in ()).throw(TypeError("bad"))),
    )
    monkeypatch.setattr(
        SandboxConfig,
        "from_toml_section",
        classmethod(lambda cls, data: (_ for _ in ()).throw(TypeError("bad"))),
    )
    monkeypatch.setattr(
        MCPConfig,
        "from_toml_section",
        classmethod(lambda cls, data: (_ for _ in ()).throw(TypeError("bad"))),
    )

    config = ForgeConfig()
    utils_module._process_security_section({"security": {}}, config)
    utils_module._process_sandbox_section({"sandbox": {}}, config)
    utils_module._process_mcp_section({"mcp": {}}, config)
    assert config.security is not None
    assert config.sandbox is not None
    assert config.mcp is not None


def test_load_from_toml_missing_core_section(tmp_path: Path):
    config_file = tmp_path / "config.toml"
    config_file.write_text("[agent]\nname='example'\n", encoding="utf-8")
    config = ForgeConfig()
    utils_module.load_from_toml(config, str(config_file))
    assert config.default_agent == ForgeConfig().default_agent


def test_load_from_toml_emits_summary_for_invalid_sections(
    tmp_path: Path, caplog: pytest.LogCaptureFixture, monkeypatch: pytest.MonkeyPatch
):
    config_file = tmp_path / "config.toml"
    config_file.write_text(
        textwrap.dedent(
            """
            [agent]
            enable_prompt_extensions = true

            [sandbox]
            timeout = 60
            """
        ).strip(),
        encoding="utf-8",
    )
    config = ForgeConfig()

    def raise_sandbox_error(cls, _section):
        raise TypeError("sandbox config invalid")

    monkeypatch.setattr(
        utils_module.SandboxConfig,
        "from_toml_section",
        classmethod(raise_sandbox_error),
    )
    with caplog.at_level(logging.WARNING):
        FORGE_logger.addHandler(caplog.handler)
        try:
            utils_module.load_from_toml(config, str(config_file))
        finally:
            FORGE_logger.removeHandler(caplog.handler)
    assert "Configuration sections skipped or partially applied" in caplog.text
    assert "[core]" in caplog.text  # missing core section
    assert "[sandbox]" in caplog.text


def test_get_agent_config_arg_missing_file(tmp_path: Path):
    missing = tmp_path / "missing.toml"
    assert utils_module.get_agent_config_arg("agent", str(missing)) is None


def test_get_llm_config_arg_missing_file(tmp_path: Path):
    missing = tmp_path / "missing.toml"
    assert utils_module.get_llm_config_arg("llm", str(missing)) is None


def test_get_llm_config_arg_parse_error(tmp_path: Path):
    config_file = tmp_path / "bad.toml"
    config_file.write_text("[llm\ninvalid", encoding="utf-8")
    assert utils_module.get_llm_config_arg("llm", str(config_file)) is None


def test_get_condenser_config_arg_missing_type(tmp_path: Path):
    config_file = tmp_path / "cond.toml"
    config_file.write_text(
        textwrap.dedent(
            """
            [condenser.custom]
            llm_config = "llm.ref"
            """
        ).strip(),
        encoding="utf-8",
    )
    result = utils_module.get_condenser_config_arg(
        "[condenser.custom]", str(config_file)
    )
    assert result is None


def test_register_custom_agents_handles_failure(monkeypatch: pytest.MonkeyPatch):
    config = ForgeConfig()
    config.agents["Broken"] = SimpleNamespace(classpath="invalid:Agent")
    monkeypatch.setattr(
        utils_module,
        "get_impl",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(RuntimeError("boom")),
    )
    from forge.controller.agent import Agent

    utils_module.register_custom_agents(config)


def test_resolve_llm_config_from_cli_missing(monkeypatch: pytest.MonkeyPatch):
    config = ForgeConfig()
    monkeypatch.setattr(utils_module, "_try_user_config_llm", lambda *_args: None)
    with pytest.raises(ValueError):
        utils_module._resolve_llm_config_from_cli("missing", config, "config.toml")


def test_try_user_config_llm_no_user_file(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
):
    home_dir = tmp_path / "home"
    home_dir.mkdir()
    monkeypatch.setenv("HOME", str(home_dir))
    monkeypatch.setenv("USERPROFILE", str(home_dir))
    config_path = home_dir / ".Forge" / "config.toml"
    config_path.parent.mkdir()
    config_path.write_text("[llm.test]\nmodel='gpt'\n", encoding="utf-8")
    result = utils_module._try_user_config_llm("test", str(config_path))
    assert result is None


def test_apply_llm_config_override_no_arg():
    config = ForgeConfig()
    original_model = config.get_llm_config().model
    args = SimpleNamespace(llm_config=None, config_file="config.toml")
    utils_module._apply_llm_config_override(config, args)
    assert config.get_llm_config().model == original_model
