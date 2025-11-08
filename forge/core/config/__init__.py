"""Configuration schemas and helpers for Forge deployments."""

from forge.core.config.agent_config import AgentConfig
from forge.core.config.arg_utils import (
    get_cli_parser,
    get_evaluation_parser,
    get_headless_parser,
)
from forge.core.config.cli_config import CLIConfig
from forge.core.config.config_utils import (
    OH_DEFAULT_AGENT,
    OH_MAX_ITERATIONS,
    get_field_info,
)
from forge.core.config.extended_config import ExtendedConfig
from forge.core.config.llm_config import LLMConfig
from forge.core.config.mcp_config import MCPConfig
from forge.core.config.forge_config import ForgeConfig
from forge.core.config.sandbox_config import SandboxConfig
from forge.core.config.security_config import SecurityConfig
from forge.core.config.utils import (
    finalize_config,
    get_agent_config_arg,
    get_llm_config_arg,
    load_from_env,
    load_from_toml,
    load_FORGE_config,
    parse_arguments,
    setup_config_from_args,
)



class AppConfig(ForgeConfig):
    """Backward-compatible alias for ForgeConfig exposing mutable class attributes."""

    # Explicitly expose commonly patched fields so test suites using monkeypatch work.
    workspace_base: str | None = ForgeConfig.model_fields["workspace_base"].default
    workspace_mount_path: str | None = ForgeConfig.model_fields["workspace_mount_path"].default


# Ensure attributes exist at class level for patching frameworks
setattr(AppConfig, "workspace_base", ForgeConfig.model_fields["workspace_base"].default)
setattr(AppConfig, "workspace_mount_path", ForgeConfig.model_fields["workspace_mount_path"].default)

__all__ = [
    "OH_DEFAULT_AGENT",
    "OH_MAX_ITERATIONS",
    "AppConfig",
    "AgentConfig",
    "CLIConfig",
    "ExtendedConfig",
    "LLMConfig",
    "MCPConfig",
    "ForgeConfig",
    "SandboxConfig",
    "SecurityConfig",
    "finalize_config",
    "get_agent_config_arg",
    "get_cli_parser",
    "get_evaluation_parser",
    "get_field_info",
    "get_headless_parser",
    "get_llm_config_arg",
    "load_from_env",
    "load_from_toml",
    "load_FORGE_config",
    "parse_arguments",
    "setup_config_from_args",
]
