"""Runtime pool policy configuration models."""

from __future__ import annotations

from pydantic import BaseModel, Field


class RuntimePoolPolicy(BaseModel):
    """Warm runtime pool policy for a specific runtime kind."""

    max_size: int = Field(
        default=2,
        ge=0,
        le=32,
        description="Maximum number of warm runtimes to retain per key",
    )
    ttl_seconds: float = Field(
        default=600.0,
        ge=10.0,
        le=86400.0,
        description="How long to keep an idle warm runtime before reaping it",
    )


class RuntimePoolConfig(BaseModel):
    """Top-level configuration for runtime pooling."""

    enabled: bool = Field(
        default=True,
        description="Enable warm pooling; when false runtimes are single-use",
    )
    default: RuntimePoolPolicy = Field(
        default_factory=RuntimePoolPolicy,
        description="Default pool policy applied to all runtimes",
    )
    overrides: dict[str, RuntimePoolPolicy] = Field(
        default_factory=dict,
        description="Per-runtime overrides keyed by runtime name",
    )


