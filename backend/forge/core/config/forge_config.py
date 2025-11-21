"""Forge configuration schema, defaults, and loading helpers."""

from __future__ import annotations

import os
from typing import Any, ClassVar

from pydantic import BaseModel, ConfigDict, Field, SecretStr

from forge.core import logger
from forge.core.config.cli_config import CLIConfig
from forge.core.config.config_utils import (
    DEFAULT_WORKSPACE_MOUNT_PATH_IN_SANDBOX,
    OH_DEFAULT_AGENT,
    OH_MAX_ITERATIONS,
    model_defaults_to_dict,
)
from forge.core.config.extended_config import ExtendedConfig
from forge.core.config.kubernetes_config import KubernetesConfig
from forge.core.config.llm_config import LLMConfig
from forge.core.config.agent_config import AgentConfig
from forge.core.config.mcp_config import MCPConfig
from forge.core.config.sandbox_config import SandboxConfig
from forge.core.config.security_config import SecurityConfig
from forge.core.config.condenser_config import CondenserConfig
from forge.core.config.runtime_pool_config import RuntimePoolConfig


class ForgeConfig(BaseModel):
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
        file_store_web_hook_url: Optional url for file store web hook
        file_store_web_hook_headers: Optional headers for file_store web hook
        enable_browser: Whether to enable the browser environment
        save_trajectory_path: Either a folder path to store trajectories with auto-generated filenames, or a designated trajectory file path.
        save_screenshots_in_trajectory: Whether to save screenshots in trajectory (in encoded image format).
        replay_trajectory_path: Path to load trajectory and replay. If provided, trajectory would be replayed first before user's instruction.
        workspace_base (deprecated): Base path for the workspace. Defaults to `./workspace` as absolute path.
        workspace_mount_path (deprecated): Path to mount the workspace. Defaults to `workspace_base`.
        workspace_mount_path_in_sandbox (deprecated): Path to mount the workspace in sandbox. Defaults to `/workspace`.
        workspace_mount_rewrite (deprecated): Path to rewrite the workspace mount path.
        cache_dir: Path to cache directory. Defaults to `/tmp/cache`.
        run_as_Forge: Whether to run as forge.
        max_iterations: Maximum number of iterations allowed.
        max_budget_per_task: Maximum budget per task, agent stops if exceeded.
        disable_color: Whether to disable terminal colors. For terminals that don't support color.
        debug: Whether to enable debugging mode.
        file_uploads_max_file_size_mb: Maximum file upload size in MB. `0` means unlimited.
        file_uploads_restrict_file_types: Whether to restrict upload file types.
        file_uploads_allowed_extensions: Allowed file extensions. `['.*']` allows all.
        cli_multiline_input: Whether to enable multiline input in CLI. When disabled,
            input is read line by line. When enabled, input continues until /exit command.
        mcp_host: Host for Forge' default MCP server
        mcp: MCP configuration settings.
        git_user_name: Git user name for commits made by the agent.
        git_user_email: Git user email for commits made by the agent.

    """

    llms: dict[str, LLMConfig] = Field(default_factory=dict)
    agents: dict[str, AgentConfig] = Field(default_factory=dict)
    default_agent: str = Field(default=OH_DEFAULT_AGENT)
    agent_mode: str = Field(default="simple")
    "Agent execution mode: 'simple' (fast autonomous) or 'enterprise' (MetaSOP multi-role)"
    sandbox: SandboxConfig = Field(default_factory=lambda: SandboxConfig())
    security: SecurityConfig = Field(default_factory=lambda: SecurityConfig())
    extended: ExtendedConfig = Field(default_factory=lambda: ExtendedConfig({}))
    runtime: str = Field(default="docker")
    file_store: str = Field(default="local")
    file_store_path: str = Field(default="~/.Forge")
    file_store_web_hook_url: str | None = Field(default=None)
    file_store_web_hook_headers: dict | None = Field(default=None)
    file_store_web_hook_batch: bool = Field(default=False)
    enable_browser: bool = Field(default=True)
    save_trajectory_path: str | None = Field(default=None)
    save_screenshots_in_trajectory: bool = Field(default=False)
    replay_trajectory_path: str | None = Field(default=None)
    search_api_key: SecretStr | None = Field(
        default=None, description="API key for legacy search integrations"
    )
    workspace_base: str | None = Field(default=None)
    workspace_mount_path_in_sandbox: str = Field(
        default=DEFAULT_WORKSPACE_MOUNT_PATH_IN_SANDBOX
    )
    workspace_mount_path: str | None = Field(default=None, deprecated=True)
    workspace_mount_rewrite: str | None = Field(default=None, deprecated=True)
    cache_dir: str = Field(default="/tmp/cache")  # nosec B108 - Safe: configurable cache directory
    run_as_Forge: bool = Field(default=True)
    max_iterations: int = Field(default=OH_MAX_ITERATIONS)
    max_budget_per_task: float | None = Field(default=None)
    init_git_in_empty_workspace: bool = Field(default=False)
    disable_color: bool = Field(default=False)
    jwt_secret: SecretStr | None = Field(default=None)
    debug: bool = Field(default=False)
    file_uploads_max_file_size_mb: int = Field(default=0)
    file_uploads_restrict_file_types: bool = Field(default=False)
    file_uploads_allowed_extensions: list[str] = Field(default_factory=lambda: [".*"])
    cli_multiline_input: bool = Field(default=False)
    conversation_max_age_seconds: int = Field(default=864000)
    enable_default_condenser: bool = Field(default=True)
    max_concurrent_conversations: int = Field(default=3)
    mcp_host: str = Field(default=f"localhost:{os.getenv('port', 3000)}")
    mcp: MCPConfig = Field(default_factory=lambda: MCPConfig())
    kubernetes: KubernetesConfig = Field(default_factory=lambda: KubernetesConfig())
    cli: CLIConfig = Field(default_factory=lambda: CLIConfig())
    git_user_name: str = Field(
        default="forge", description="Git user name for commits made by the agent"
    )
    git_user_email: str = Field(
        default="Forge@all-hands.dev",
        description="Git user email for commits made by the agent",
    )
    # Redis configuration for distributed quota tracking
    redis_url: str | None = Field(
        default=None,
        description="Redis connection URL for distributed quota tracking (defaults to REDIS_URL env var)",
    )
    redis_connection_pool_size: int = Field(
        default=10,
        ge=1,
        le=100,
        description="Redis connection pool size",
    )
    redis_connection_timeout: float = Field(
        default=5.0,
        ge=1.0,
        le=60.0,
        description="Redis connection timeout in seconds",
    )
    redis_quota_fallback_enabled: bool = Field(
        default=True,
        description="Fall back to in-memory quota if Redis unavailable",
    )
    # Structured logging configuration
    log_format: str = Field(
        default="json",
        description="Log format: 'json' or 'text'",
    )
    log_level: str = Field(
        default="INFO",
        description="Log level: DEBUG, INFO, WARNING, ERROR, CRITICAL",
    )
    log_shipping_enabled: bool = Field(
        default=False,
        description="Enable log shipping to external services",
    )
    log_shipping_endpoint: str | None = Field(
        default=None,
        description="Log shipping endpoint (e.g., Datadog, ELK)",
    )
    log_shipping_api_key: SecretStr | None = Field(
        default=None,
        description="API key for log shipping service",
    )
    # Distributed tracing configuration
    tracing_enabled: bool = Field(
        default=True,
        description="Enable distributed tracing",
    )
    tracing_exporter: str = Field(
        default="console",
        description="Tracing exporter: 'jaeger', 'zipkin', 'otlp', 'console'",
    )
    tracing_endpoint: str | None = Field(
        default=None,
        description="Tracing endpoint URL",
    )
    tracing_sample_rate: float = Field(
        default=0.1,
        ge=0.0,
        le=1.0,
        description="Trace sampling rate (0.0 to 1.0)",
    )
    tracing_service_name: str = Field(
        default="forge",
        description="Service name for tracing",
    )
    tracing_service_version: str = Field(
        default="1.0.0",
        description="Service version for tracing",
    )
    runtime_pool: RuntimePoolConfig = Field(
        default_factory=RuntimePoolConfig,
        description="Warm runtime pool policy configuration",
    )
    # Alert policies and SLO tracking
    alerting_enabled: bool = Field(
        default=False,
        description="Enable alerting policies",
    )
    alerting_endpoint: str | None = Field(
        default=None,
        description="Alerting endpoint (e.g., PagerDuty, Slack)",
    )
    alerting_api_key: SecretStr | None = Field(
        default=None,
        description="API key for alerting service",
    )
    require_observability_dependencies: bool = Field(
        default=False,
        description=(
            "When true, fail fast during startup if monitoring dependencies such as "
            "Prometheus or Redis are unavailable. Can also be enabled via "
            "FORGE_STRICT_OBSERVABILITY=1."
        ),
    )
    slo_availability_target: float = Field(
        default=0.99,
        ge=0.0,
        le=1.0,
        description="Availability SLO target (0.0 to 1.0)",
    )
    slo_latency_p95_target_ms: float = Field(
        default=1000.0,
        ge=100.0,
        description="P95 latency SLO target in milliseconds",
    )
    slo_error_rate_target: float = Field(
        default=0.01,
        ge=0.0,
        le=1.0,
        description="Error rate SLO target (0.0 to 1.0)",
    )
    # Retry queue configuration
    retry_queue_enabled: bool = Field(
        default=True,
        description="Enable retry queue for failed operations",
    )
    retry_queue_backend: str = Field(
        default="redis",
        description="Retry queue backend: 'redis', 'memory', 'database'",
    )
    retry_queue_max_size: int = Field(
        default=10000,
        ge=100,
        description="Maximum retry queue size",
    )
    retry_queue_max_retries: int = Field(
        default=3,
        ge=1,
        le=10,
        description="Maximum retries per operation",
    )
    retry_queue_retry_delay_seconds: float = Field(
        default=60.0,
        ge=1.0,
        description="Initial retry delay in seconds",
    )
    retry_queue_max_delay_seconds: float = Field(
        default=3600.0,
        ge=60.0,
        description="Maximum retry delay in seconds",
    )
    graceful_degradation_enabled: bool = Field(
        default=True,
        description="Enable graceful degradation on failures",
    )
    # Slack integration settings
    SLACK_CLIENT_ID: str | None = Field(
        default=None, description="Slack OAuth client ID"
    )
    SLACK_CLIENT_SECRET: SecretStr | None = Field(
        default=None, description="Slack OAuth client secret"
    )
    SLACK_SIGNING_SECRET: SecretStr | None = Field(
        default=None,
        description="Slack signing secret for webhook verification",
    )
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
