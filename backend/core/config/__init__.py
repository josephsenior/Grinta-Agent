"""Configuration schemas and helpers for Forge deployments."""

from backend.core.config.agent_config import AgentConfig
from backend.core.config.arg_utils import (
    get_cli_parser,
    get_headless_parser,
)
from backend.core.config.config_utils import (
    FORGE_DEFAULT_AGENT,
    FORGE_MAX_ITERATIONS,
    get_field_info,
)
from backend.core.config.extended_config import ExtendedConfig
from backend.core.config.llm_config import LLMConfig
from backend.core.config.mcp_config import MCPConfig
from backend.core.config.forge_config import ForgeConfig
from backend.core.config.sandbox_config import SandboxConfig
from backend.core.config.security_config import SecurityConfig
from backend.core.config.utils import (
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


# Ensure attributes exist at class level for patching frameworks

__all__ = [
    "FORGE_DEFAULT_AGENT",
    "FORGE_MAX_ITERATIONS",
    "AppConfig",
    "AgentConfig",
    "ExtendedConfig",
    "LLMConfig",
    "MCPConfig",
    "ForgeConfig",
    "SandboxConfig",
    "SecurityConfig",
    "finalize_config",
    "get_agent_config_arg",
    "get_cli_parser",
    "get_field_info",
    "get_headless_parser",
    "get_llm_config_arg",
    "load_from_env",
    "load_from_toml",
    "load_FORGE_config",
    "parse_arguments",
    "setup_config_from_args",
]
