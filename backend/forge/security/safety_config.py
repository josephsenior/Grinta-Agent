from pydantic import BaseModel, Field

class SafetyConfig(BaseModel):
    blocked_patterns: list[str] = Field(default_factory=list)
    allowed_exceptions: list[str] = Field(default_factory=list)
    risk_threshold: str = "HIGH"
    enable_audit_logging: bool = False
    audit_log_path: str = "audit.log"
    environment: str = "production"
    enable_mandatory_validation: bool = True
    block_in_production: bool = Field(default=True, description="Block high-risk actions in production")
    require_review_for_high_risk: bool = Field(default=False, description="Require review for high-risk actions")
    enable_risk_alerts: bool = Field(default=False, description="Enable risk alert notifications")
    alert_webhook_url: str | None = Field(default=None, description="Webhook URL for risk alerts")
