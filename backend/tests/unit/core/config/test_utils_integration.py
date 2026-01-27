from __future__ import annotations

import os
import sys
import textwrap
import types
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest
from pydantic import BaseModel, SecretStr

from forge.core.config import utils as utils_module
from forge.core.config.agent_config import AgentConfig
from forge.core.config.extended_config import ExtendedConfig
from forge.core.config.forge_config import ForgeConfig
from forge.core.config.llm_config import LLMConfig
from forge.core.config.mcp_config import MCPConfig
from forge.core.config.sandbox_config import SandboxConfig
from forge.core.config.security_config import SecurityConfig


# Minimal stubs so importing forge modules does not require native deps during tests
if "tokenizers" not in sys.modules:
    sys.modules["tokenizers"] = types.ModuleType("tokenizers")


class RecordingAPIKeyManager:
    def __init__(self) -> None:
        self.calls: list[tuple[str, str, SecretStr]] = []

    def set_api_key(self, model: str, key: SecretStr) -> None:
        self.calls.append(("set", model, key))

    def set_environment_variables(self, model: str, key: SecretStr) -> None:
        self.calls.append(("env", model, key))


def _patch_model_rebuilds(monkeypatch: pytest.MonkeyPatch) -> None:
    """Speed up load_FORGE_config by disabling expensive model rebuilds."""

    def _noop(cls, *_args, **_kwargs) -> None:
        return None

    from forge.core.config.kubernetes_config import KubernetesConfig

    rebuild_targets = [
        LLMConfig,
        SandboxConfig,
        SecurityConfig,
        ExtendedConfig,
        KubernetesConfig,
    ]
    # Additional configs imported inside utils
    from forge.core.config.cli_config import CLIConfig
    from forge.core.config.permissions_config import PermissionsConfig
    from forge.security.safety_config import SafetyConfig
    from forge.core.config.condenser_config import (
        AmortizedForgettingCondenserConfig,
        BrowserOutputCondenserConfig,
        CondenserPipelineConfig,
        ConversationWindowCondenserConfig,
        LLMAttentionCondenserConfig,
        LLMSummarizingCondenserConfig,
        NoOpCondenserConfig,
        ObservationMaskingCondenserConfig,
        RecentEventsCondenserConfig,
        SmartCondenserConfig,
        StructuredSummaryCondenserConfig,
    )

    rebuild_targets.extend(
        [
            CLIConfig,
            MCPConfig,
            PermissionsConfig,
            SafetyConfig,
            AmortizedForgettingCondenserConfig,
            BrowserOutputCondenserConfig,
            CondenserPipelineConfig,
            ConversationWindowCondenserConfig,
            LLMAttentionCondenserConfig,
            LLMSummarizingCondenserConfig,
            NoOpCondenserConfig,
            ObservationMaskingCondenserConfig,
            RecentEventsCondenserConfig,
            SmartCondenserConfig,
            StructuredSummaryCondenserConfig,
            AgentConfig,
            ForgeConfig,
        ],
    )

    for cls in rebuild_targets:
        if hasattr(cls, "model_rebuild"):
            monkeypatch.setattr(cls, "model_rebuild", classmethod(_noop))


def test_load_from_env_applies_nested_values(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    config = ForgeConfig()
    logs_dir = tmp_path / "logs"
    logs_dir.mkdir()
    config.set_llm_config(LLMConfig(model="base", log_completions_folder=str(logs_dir)))
    api_manager = RecordingAPIKeyManager()
    monkeypatch.setattr(
        "forge.core.config.api_key_manager.api_key_manager", api_manager
    )

    cache_dir = tmp_path / "cache"
    cache_dir.mkdir()

    env = {
        "DEBUG": "true",
        "CACHE_DIR": str(cache_dir),
        "LLM_MODEL": "env-model",
        "LLM_API_KEY": "sk-env",
        "AGENT_ENABLE_BROWSING": "false",
    }

    utils_module.load_from_env(config, env)

    assert config.debug is True
    assert config.cache_dir == os.path.abspath(env["CACHE_DIR"])
    assert config.get_llm_config().model == "env-model"
    assert isinstance(config.get_llm_config().api_key, SecretStr)
    assert config.get_llm_config().api_key.get_secret_value() == "sk-env"
    assert config.get_agent_config().enable_browsing is False
    assert (
        "set",
        config.get_llm_config().model,
        config.get_llm_config().api_key,
    ) in api_manager.calls


def test_load_forge_config_full_flow(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    _patch_model_rebuilds(monkeypatch)

    workspace_dir = tmp_path / "workspace"
    workspace_dir.mkdir()
    cache_dir = tmp_path / "cache"
    cache_dir.mkdir()
    log_dir = tmp_path / "logs"
    log_dir.mkdir()

    workspace_path = workspace_dir.as_posix()
    cache_path = cache_dir.as_posix()
    log_path = log_dir.as_posix()

    config_dir = tmp_path / "config"
    config_dir.mkdir()
    config_toml = config_dir / "config.toml"
    config_toml.write_text(
        textwrap.dedent(
            f"""
            [core]
            default_agent = "CustomAgent"
            enable_default_condenser = true
            workspace_base = "{workspace_path}"
            runtime = "cli"
            cache_dir = "{cache_path}"

            [llm.llm]
            model = "gpt-config"
            api_key = "sk-toml-config-override"
            log_completions_folder = "{log_path}"

            [agent.CustomAgent]
            enable_browsing = true

            [security.security]
            enabled = true

            [sandbox.sandbox]
            volumes = "/tmp/host:/workspace:rw"
            use_host_network = true

            [mcp.mcp]
            servers = []

            [kubernetes.kubernetes]
            namespace = "integration"

            [condenser.default]
            type = "noop"

            [extended]
            feature_flag = "on"
            """
        ).strip(),
        encoding="utf-8",
    )

    # Environment overrides exercised by load_from_env
    monkeypatch.setenv("WORKSPACE_BASE", workspace_path)
    monkeypatch.setenv("SANDBOX_VOLUMES", "/tmp/host:/workspace:rw")
    monkeypatch.setenv("LLM_API_KEY", "sk-load-token-0000000000000")

    api_manager = RecordingAPIKeyManager()
    monkeypatch.setattr(
        "forge.core.config.api_key_manager.api_key_manager", api_manager
    )

    class InMemoryStore:
        def __init__(self) -> None:
            self.writes: dict[str, str] = {}

        def read(self, key: str) -> str:
            raise FileNotFoundError(key)

        def write(self, key: str, value: str) -> None:
            self.writes[key] = value

        def list(self, path: str) -> list[str]:
            return []

        def delete(self, path: str) -> None:
            return None

    store = InMemoryStore()
    monkeypatch.setattr(utils_module, "get_file_store", lambda *_args, **_kwargs: store)
    monkeypatch.setattr(utils_module.platform, "system", lambda: "Darwin")

    # Simplify TOML parsing for dependent configs
    monkeypatch.setattr(
        LLMConfig,
        "from_toml_section",
        classmethod(
            lambda cls, section: {
                name: cls(**values) for name, values in section.items()
            }
        ),
    )
    monkeypatch.setattr(
        SandboxConfig,
        "from_toml_section",
        classmethod(
            lambda cls, section: {"sandbox": cls(**section.get("sandbox", {}))}
        ),
    )
    monkeypatch.setattr(
        SecurityConfig,
        "from_toml_section",
        classmethod(lambda cls, section: {"security": cls()}),
    )
    monkeypatch.setattr(
        MCPConfig,
        "from_toml_section",
        classmethod(lambda cls, section: {"mcp": cls()}),
    )
    from forge.core.config.kubernetes_config import KubernetesConfig

    monkeypatch.setattr(
        KubernetesConfig,
        "from_toml_section",
        classmethod(
            lambda cls, section: {"kubernetes": cls(**section.get("kubernetes", {}))}
        ),
    )
    monkeypatch.setattr(
        "forge.core.config.condenser_config.condenser_config_from_toml_section",
        lambda *_args, **_kwargs: {"condenser": SimpleNamespace(type="noop")},
    )

    from forge.controller.agent import Agent

    registrations: list[tuple[str, type[Any]]] = []
    monkeypatch.setattr(
        utils_module, "get_impl", lambda base, path: type("DynamicAgent", (), {})
    )
    monkeypatch.setattr(
        Agent,
        "register",
        classmethod(lambda cls, name, impl: registrations.append((name, impl))),
    )

    config = utils_module.load_FORGE_config(config_file=str(config_toml))

    assert config.default_agent == "CustomAgent"
    assert config.get_llm_config().model == "gpt-config"
    assert (
        config.get_llm_config().api_key.get_secret_value() == "sk-toml-config-override"
    )
    assert (
        config.get_agent_config("CustomAgent").enable_browsing is False
    )  # disabled for cli runtime
    assert config.runtime == "cli"
    assert store.writes  # JWT secret persisted

    # Manually inject classpath to trigger registration helper
    original_agent = config.get_agent_config("CustomAgent")
    config.agents["CustomAgent"] = SimpleNamespace(
        **original_agent.model_dump(),
        classpath="package.module:Agent",
    )
    utils_module.register_custom_agents(config)
    assert registrations and registrations[0][0] == "CustomAgent"


def test_get_agent_and_llm_config_arg_roundtrip(tmp_path: Path) -> None:
    config_dir = tmp_path / "config-roundtrip"
    config_dir.mkdir()
    config_file = config_dir / "config.toml"
    config_file.write_text(
        textwrap.dedent(
            """
            [core]
            default_agent = "agent"

            [agent.Custom]
            enable_prompt_extensions = false

            [llm.custom]
            model = "gpt-4"
            """
        ).strip(),
        encoding="utf-8",
    )

    agent_config = utils_module.get_agent_config_arg("Custom", str(config_file))
    assert agent_config is not None
    assert agent_config.enable_prompt_extensions is False

    missing_agent = utils_module.get_agent_config_arg("Missing", str(config_file))
    assert missing_agent is None

    llm_config = utils_module.get_llm_config_arg("custom", str(config_file))
    assert llm_config is not None
    assert llm_config.model == "gpt-4"

    missing_llm = utils_module.get_llm_config_arg("missing", str(config_file))
    assert missing_llm is None


def test_setup_config_from_args_integration(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    _patch_model_rebuilds(monkeypatch)

    config_dir = tmp_path / "cli-config"
    config_dir.mkdir()
    config_file = config_dir / "config.toml"
    config_file.write_text(
        textwrap.dedent(
            """
            [core]
            default_agent = "agent"

            [llm.llm]
            model = "gpt-cli"
            """
        ).strip(),
        encoding="utf-8",
    )

    monkeypatch.setattr(
        LLMConfig,
        "from_toml_section",
        classmethod(
            lambda cls, section: {
                name: cls(**values) for name, values in section.items()
            }
        ),
    )

    args = SimpleNamespace(
        config_file=str(config_file),
        llm_config="llm",
        agent_cls="CLIChosenAgent",
        max_iterations=5,
        max_budget_per_task=12.5,
        selected_repo="example/repo",
    )

    config = utils_module.setup_config_from_args(args)

    assert config.default_agent == "CLIChosenAgent"
    assert config.max_iterations == 5
    assert config.max_budget_per_task == 12.5
    assert config.sandbox.selected_repo == "example/repo"
    assert config.get_llm_config().model == "gpt-cli"
