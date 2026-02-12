"""Sandbox execution configuration schemas and helpers."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field, ValidationError
from backend._canonical import CanonicalModelMetaclass
from backend.core.constants import (
    DEFAULT_SANDBOX_AUTO_LINT_ENABLED,
    DEFAULT_SANDBOX_CLOSE_DELAY,
    DEFAULT_SANDBOX_FORCE_REBUILD_RUNTIME,
    DEFAULT_SANDBOX_KEEP_RUNTIME_ALIVE,
    DEFAULT_SANDBOX_REMOTE_RUNTIME_RESOURCE_FACTOR,
    DEFAULT_SANDBOX_TIMEOUT,
    DEFAULT_SANDBOX_USE_HOST_NETWORK,
)


class SandboxConfig(BaseModel, metaclass=CanonicalModelMetaclass):
    """Configuration for the sandbox.

    Simplified for Forge Core (LocalRuntime only).
    """

    timeout: int = Field(
        default=DEFAULT_SANDBOX_TIMEOUT,
        ge=1,
        description="The timeout in seconds for the default sandbox action execution"
    )
    enable_auto_lint: bool = Field(
        default=DEFAULT_SANDBOX_AUTO_LINT_ENABLED,
        description="Whether to enable auto-lint"
    )
    runtime_startup_env_vars: dict[str, str] = Field(
        default_factory=dict,
        description="The environment variables to set at the launch of the runtime"
    )
    browsergym_eval_env: str | None = Field(
        default=None,
        description="The BrowserGym environment to use for browser evaluation"
    )
    selected_repo: str | None = Field(
        default=None,
        description="Selected repository for sandbox operations"
    )
    base_container_image: str | None = Field(default=None, description="Base container image for sandbox")
    runtime_container_image: str | None = Field(default=None, description="Runtime container image for sandbox")
    api_key: str | None = Field(default=None, description="API key for sandbox")
    close_delay: int = Field(default=DEFAULT_SANDBOX_CLOSE_DELAY, description="Delay in seconds before closing sandbox")
    remote_runtime_resource_factor: float = Field(default=DEFAULT_SANDBOX_REMOTE_RUNTIME_RESOURCE_FACTOR, description="Resource factor for remote runtime")
    keep_runtime_alive: bool = Field(default=DEFAULT_SANDBOX_KEEP_RUNTIME_ALIVE, description="Whether to keep runtime alive between requests")
    use_host_network: bool = Field(default=DEFAULT_SANDBOX_USE_HOST_NETWORK, description="Whether to use host network mode for Docker containers")
    force_rebuild_runtime: bool = Field(default=DEFAULT_SANDBOX_FORCE_REBUILD_RUNTIME, description="Whether to force rebuild of runtime container image")
    model_config = ConfigDict(extra="forbid")

    @classmethod
    def from_toml_section(cls, data: dict) -> dict[str, SandboxConfig]:
        """Create a mapping of SandboxConfig instances from a toml dictionary representing the [sandbox] section.

        Returns:
            dict[str, SandboxConfig]: A mapping where the key "sandbox" corresponds to the [sandbox] configuration
        """
        sandbox_mapping: dict[str, SandboxConfig] = {}
        try:
            sandbox_mapping["sandbox"] = cls.model_validate(data)
        except ValidationError as e:
            msg = f"Invalid sandbox configuration: {e}"
            raise ValueError(msg) from e
        return sandbox_mapping
