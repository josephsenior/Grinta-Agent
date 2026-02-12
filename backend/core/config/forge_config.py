"""Forge configuration schema, defaults, and loading helpers."""

from __future__ import annotations

import os
from typing import Any, ClassVar

from pydantic import BaseModel, ConfigDict, Field, SecretStr

from backend._canonical import CanonicalModelMetaclass
from backend.core import logger
from backend.core.config.config_utils import (
    model_defaults_to_dict,
)
from backend.core.constants import (
    DEFAULT_CACHE_DIR,
    DEFAULT_CONVERSATION_MAX_AGE_SECONDS,
    DEFAULT_ENABLE_BROWSER,
    DEFAULT_ENABLE_DEFAULT_CONDENSER,
    DEFAULT_FILE_STORE,
    DEFAULT_GIT_USER_EMAIL,
    DEFAULT_GIT_USER_NAME,
    DEFAULT_LOG_FORMAT,
    DEFAULT_LOG_LEVEL,
    DEFAULT_MAX_CONCURRENT_CONVERSATIONS,
    DEFAULT_MAX_FILE_UPLOAD_SIZE_MB,
    DEFAULT_RUNTIME,
    DEFAULT_WORKSPACE_BASE,
    FORGE_DEFAULT_AGENT,
    FORGE_MAX_ITERATIONS,
)
from backend.core.config.llm_config import LLMConfig
from backend.core.config.agent_config import AgentConfig
from backend.core.config.mcp_config import MCPConfig
from backend.core.config.sandbox_config import SandboxConfig
from backend.core.config.security_config import SecurityConfig
from backend.core.config.extended_config import ExtendedConfig


class ForgeConfig(BaseModel, metaclass=CanonicalModelMetaclass):
    """Configuration for the app.

    Attributes:
        llms: Dictionary mapping LLM names to their configurations.
            The default configuration is stored under the 'llm' key.
        agents: Dictionary mapping agent names to their configurations.
            The default configuration is stored under the 'agent' key.
        default_agent: Name of the default agent to use.
        sandbox: Sandbox configuration settings.
        runtime: Runtime environment identifier.
        file_store: Type of file store to use.
        file_store_path: Path to the file store.
        enable_browser: Whether to enable the browser environment
        max_iterations: Maximum number of iterations allowed.
        mcp: MCP configuration settings.
        git_user_name: Git user name for commits made by the agent.
        git_user_email: Git user email for commits made by the agent.
    """

    llms: dict[str, LLMConfig] = Field(default_factory=dict)
    agents: dict[str, AgentConfig] = Field(default_factory=dict)
    default_agent: str = Field(default=FORGE_DEFAULT_AGENT)
    sandbox: SandboxConfig = Field(default_factory=lambda: SandboxConfig())
    security: SecurityConfig = Field(default_factory=lambda: SecurityConfig())
    runtime: str = Field(default=DEFAULT_RUNTIME)
    file_store: str = Field(default=DEFAULT_FILE_STORE)
    file_store_path: str = Field(default=DEFAULT_WORKSPACE_BASE)
    enable_browser: bool = Field(default=DEFAULT_ENABLE_BROWSER)
    cache_dir: str = Field(default=DEFAULT_CACHE_DIR)
    max_iterations: int = Field(default=FORGE_MAX_ITERATIONS)
    max_budget_per_task: float | None = Field(
        default=5.0,
        description=(
            "Maximum LLM cost (USD) allowed per task. "
            "Set to 0 or None for no limit (not recommended)."
        ),
    )
    debug: bool = Field(default=False)
    disable_color: bool = Field(default=False)
    conversation_max_age_seconds: int = Field(default=DEFAULT_CONVERSATION_MAX_AGE_SECONDS)
    enable_default_condenser: bool = Field(default=DEFAULT_ENABLE_DEFAULT_CONDENSER)
    max_concurrent_conversations: int = Field(default=DEFAULT_MAX_CONCURRENT_CONVERSATIONS)
    mcp: MCPConfig = Field(default_factory=lambda: MCPConfig())
    git_user_name: str = Field(
        default=DEFAULT_GIT_USER_NAME, description="Git user name for commits made by the agent"
    )
    git_user_email: str = Field(
        default=DEFAULT_GIT_USER_EMAIL,
        description="Git user email for commits made by the agent",
    )
    jwt_secret: SecretStr | None = Field(
        default=None,
        description="JWT secret for the app",
    )
    # Logging configuration
    log_format: str = Field(
        default=DEFAULT_LOG_FORMAT,
        description="Log format: 'json' or 'text'",
    )
    log_level: str = Field(
        default=DEFAULT_LOG_LEVEL,
        description="Log level: DEBUG, INFO, WARNING, ERROR, CRITICAL",
    )
    # Extended configuration for additional features
    extended: ExtendedConfig | None = Field(
        default=None,
        description="Extended configuration for additional features"
    )
    # Optional attributes accessed via extended config or direct access
    workspace_base: str | None = Field(default=None, description="Base workspace directory")
    workspace_mount_path_in_sandbox: str | None = Field(default=None, description="Workspace mount path in sandbox")
    file_store_web_hook_url: str | None = Field(default=None, description="File store webhook URL")
    file_store_web_hook_headers: dict[str, str] | None = Field(default=None, description="File store webhook headers")
    file_store_web_hook_batch: bool = Field(default=False, description="Enable file store webhook batching")
    # Trajectory replay/save configuration
    replay_trajectory_path: str | None = Field(default=None, description="Path to trajectory file for replay")
    save_trajectory_path: str | None = Field(default=None, description="Path to save trajectory file")
    save_screenshots_in_trajectory: bool = Field(default=False, description="Save screenshots in trajectory")
    # CLI configuration
    cli_multiline_input: bool = Field(default=False, description="Enable multiline input in CLI")
    # MCP configuration
    mcp_host: str | None = Field(default=None, description="MCP host address")
    # Runtime configuration
    init_git_in_empty_workspace: bool = Field(default=False, description="Initialize git in empty workspace")
    run_as_Forge: bool = Field(default=False, description="Run commands as Forge user")
    # File upload configuration
    file_uploads_max_file_size_mb: int = Field(default=DEFAULT_MAX_FILE_UPLOAD_SIZE_MB, description="Maximum file upload size in MB")
    file_uploads_restrict_file_types: bool = Field(default=False, description="Whether to restrict file types")
    file_uploads_allowed_extensions: set[str] = Field(default_factory=set, description="Allowed file extensions")
    defaults_dict: ClassVar[dict] = {}
    model_config = ConfigDict(extra="forbid", arbitrary_types_allowed=True)

    def get_llm_config(self, name: str = "llm") -> LLMConfig:
        """'llm' is the name for default config (for backward compatibility prior to 0.8)."""
        if name in self.llms:
            return self.llms[name]
        if name is not None and name != "llm":
            logger.FORGE_logger.warning(
                f"llm config group {name} not found, using default config"
            )
        if "llm" not in self.llms:
            self.llms["llm"] = LLMConfig()
        return self.llms["llm"]

    def set_llm_config(self, value: LLMConfig, name: str = "llm") -> None:
        """Set LLM configuration by name.

        Args:
            value: LLM configuration to set
            name: Configuration name (default "llm")

        """
        self.llms[name] = value

    def get_agent_config(self, name: str = "agent") -> AgentConfig:
        """'agent' is the name for default config (for backward compatibility prior to 0.8)."""
        if name in self.agents:
            return self.agents[name]
        if "agent" not in self.agents:
            self.agents["agent"] = AgentConfig()
        return self.agents["agent"]

    def set_agent_config(self, value: AgentConfig, name: str = "agent") -> None:
        """Set agent configuration by name.

        Args:
            value: Agent configuration to set
            name: Configuration name (default "agent")

        """
        self.agents[name] = value

    def get_agent_to_llm_config_map(self) -> dict[str, LLMConfig]:
        """Get a map of agent names to llm configs."""
        return {name: self.get_llm_config_from_agent(name) for name in self.agents}

    def get_llm_config_from_agent_config(self, agent_config: AgentConfig):
        """Get LLM configuration from agent configuration.

        Args:
            agent_config: Agent configuration

        Returns:
            LLM configuration for the agent

        """
        llm_spec = agent_config.llm_config
        if isinstance(llm_spec, LLMConfig):
            return llm_spec
        llm_config_name = llm_spec if llm_spec is not None else "llm"
        return self.get_llm_config(llm_config_name)

    def get_llm_config_from_agent(self, name: str = "agent") -> LLMConfig:
        """Get LLM configuration for named agent.

        Args:
            name: Agent name

        Returns:
            LLM configuration for the agent

        """
        agent_config: AgentConfig = self.get_agent_config(name)
        return self.get_llm_config_from_agent_config(agent_config)

    def get_agent_configs(self) -> dict[str, AgentConfig]:
        """Get all agent configurations.

        Returns:
            Dictionary mapping agent names to configurations

        """
        return self.agents

    def model_post_init(self, __context: Any) -> None:
        """Post-initialization hook, called when the instance is created with only default values."""
        super().model_post_init(__context)
        if not ForgeConfig.defaults_dict:
            ForgeConfig.defaults_dict = model_defaults_to_dict(self)


# Rebuild the model after all dependencies are loaded to resolve forward references
ForgeConfig.model_rebuild()

