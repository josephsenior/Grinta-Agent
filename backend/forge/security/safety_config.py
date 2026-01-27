from pydantic import BaseModel, Field

class SafetyConfig(BaseModel):
    blocked_patterns: list[str] = Field(default_factory=list)
    allowed_exceptions: list[str] = Field(default_factory=list)
    risk_threshold: str = "HIGH"
    enable_audit_logging: bool = False
    audit_log_path: str = "audit.log"
    environment: str = "production"
    enable_mandatory_validation: bool = True
