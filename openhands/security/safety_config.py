"""Configuration for safety validation system."""

from __future__ import annotations

from pydantic import BaseModel, Field


class SafetyConfig(BaseModel):
    """Configuration for the safety validation system."""

    enable_enhanced_risk_detection: bool = Field(default=True)
    """Enable enhanced command risk detection with encoding detection."""

    enable_mandatory_validation: bool = Field(default=True)
    """Enable mandatory validation even in full autonomy mode."""

    risk_threshold: str = Field(default="high")
    """Risk threshold for blocking: 'critical', 'high', 'medium', 'low'."""

    environment: str = Field(default="development")
    """Environment: 'development', 'staging', 'production'."""

    blocked_patterns: list[str] = Field(default_factory=list)
    """Custom regex patterns to block."""

    allowed_exceptions: list[str] = Field(default_factory=list)
    """Commands to whitelist (exact matches)."""

    enable_audit_logging: bool = Field(default=True)
    """Enable audit logging of all actions."""

    audit_log_path: str = Field(default="~/.openhands/audit")
    """Path to store audit logs."""

    enable_risk_alerts: bool = Field(default=True)
    """Enable real-time risk alerts."""

    alert_webhook_url: str | None = Field(default=None)
    """Optional webhook URL for risk alerts (Slack/Discord)."""

    block_in_production: bool = Field(default=True)
    """Block high-risk commands in production environment."""

    require_review_for_high_risk: bool = Field(default=False)
    """Require human review for high-risk actions (creates review queue)."""
