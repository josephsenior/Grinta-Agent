"""Sandbox execution configuration schemas and helpers."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field, ValidationError
from forge._canonical import CanonicalModelMetaclass


class SandboxConfig(BaseModel, metaclass=CanonicalModelMetaclass):
    """Configuration for the sandbox.

    Simplified for Forge Core (LocalRuntime only).
    """

    timeout: int = Field(
        default=120,
        ge=1,
        description="The timeout in seconds for the default sandbox action execution"
    )
    enable_auto_lint: bool = Field(
        default=True,
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
