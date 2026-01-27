"""Tests for SafetyConfig model with field validators and descriptions."""

import pytest
from pydantic import ValidationError

from forge.security.safety_config import SafetyConfig


class TestSafetyConfig:
    """Test SafetyConfig model validation and defaults."""

    def test_default_values(self):
        """Test SafetyConfig with all default values."""
        config = SafetyConfig()
        assert config.enable_enhanced_risk_detection is True
        assert config.enable_mandatory_validation is True
        assert config.risk_threshold == "high"
        assert config.environment == "development"
        assert config.blocked_patterns == []
        assert config.allowed_exceptions == []
        assert config.enable_audit_logging is True
        assert config.audit_log_path == "~/.Forge/audit"
        assert config.enable_risk_alerts is True
        assert config.alert_webhook_url is None
        assert config.block_in_production is True
        assert config.require_review_for_high_risk is False

    def test_custom_values(self):
        """Test SafetyConfig with custom values."""
        config = SafetyConfig(
            enable_enhanced_risk_detection=False,
            enable_mandatory_validation=False,
            risk_threshold="medium",
            environment="production",
            blocked_patterns=[r"rm -rf", r"sudo"],
            allowed_exceptions=["ls", "pwd"],
            enable_audit_logging=False,
            audit_log_path="/var/log/forge/audit",
            enable_risk_alerts=False,
            alert_webhook_url="https://hooks.slack.com/test",
            block_in_production=False,
            require_review_for_high_risk=True,
        )
        assert config.enable_enhanced_risk_detection is False
        assert config.enable_mandatory_validation is False
        assert config.risk_threshold == "medium"
        assert config.environment == "production"
        assert config.blocked_patterns == [r"rm -rf", r"sudo"]
        assert config.allowed_exceptions == ["ls", "pwd"]
        assert config.enable_audit_logging is False
        assert config.audit_log_path == "/var/log/forge/audit"
        assert config.enable_risk_alerts is False
        assert config.alert_webhook_url == "https://hooks.slack.com/test"
        assert config.block_in_production is False
        assert config.require_review_for_high_risk is True

    @pytest.mark.parametrize(
        "risk_threshold",
        ["critical", "high", "medium", "low"],
    )
    def test_valid_risk_threshold(self, risk_threshold: str):
        """Test valid risk threshold values."""
        config = SafetyConfig(risk_threshold=risk_threshold)
        assert config.risk_threshold == risk_threshold

    @pytest.mark.parametrize(
        "risk_threshold,expected_error",
        [
            ("", "String should have at least 1 character"),  # Pydantic min_length catches empty
            ("invalid", "risk_threshold must be one of: critical, high, medium, low"),
            ("HIGH", "risk_threshold must be one of: critical, high, medium, low"),  # Case sensitive
            ("critical ", "risk_threshold must be one of: critical, high, medium, low"),  # Trailing space
        ],
    )
    def test_invalid_risk_threshold(self, risk_threshold: str, expected_error: str):
        """Test invalid risk threshold values."""
        with pytest.raises(ValidationError) as exc_info:
            SafetyConfig(risk_threshold=risk_threshold)
        assert expected_error in str(exc_info.value)

    @pytest.mark.parametrize(
        "environment",
        ["development", "staging", "production"],
    )
    def test_valid_environment(self, environment: str):
        """Test valid environment values."""
        config = SafetyConfig(environment=environment)
        assert config.environment == environment

    @pytest.mark.parametrize(
        "environment,expected_error",
        [
            ("", "String should have at least 1 character"),  # Pydantic min_length catches empty
            ("invalid", "environment must be one of: development, staging, production"),
            ("PRODUCTION", "environment must be one of: development, staging, production"),  # Case sensitive
            ("development ", "environment must be one of: development, staging, production"),  # Trailing space
        ],
    )
    def test_invalid_environment(self, environment: str, expected_error: str):
        """Test invalid environment values."""
        with pytest.raises(ValidationError) as exc_info:
            SafetyConfig(environment=environment)
        assert expected_error in str(exc_info.value)

    @pytest.mark.parametrize(
        "audit_log_path",
        [
            "~/.Forge/audit",
            "/var/log/forge/audit",
            "./audit",
            "C:\\Users\\Forge\\audit",
            "/tmp/audit",
        ],
    )
    def test_valid_audit_log_path(self, audit_log_path: str):
        """Test valid audit log paths."""
        config = SafetyConfig(audit_log_path=audit_log_path)
        assert config.audit_log_path == audit_log_path

    def test_empty_audit_log_path(self):
        """Test empty audit log path raises error."""
        with pytest.raises(ValidationError) as exc_info:
            SafetyConfig(audit_log_path="")
        assert "String should have at least 1 character" in str(exc_info.value)  # Pydantic min_length catches empty

    @pytest.mark.parametrize(
        "webhook_url",
        [
            "https://hooks.slack.com/services/xxx",
            "http://localhost:8080/webhook",
            "https://discord.com/api/webhooks/xxx",
        ],
    )
    def test_valid_webhook_url(self, webhook_url: str):
        """Test valid webhook URLs."""
        config = SafetyConfig(alert_webhook_url=webhook_url)
        assert config.alert_webhook_url == webhook_url

    def test_none_webhook_url(self):
        """Test None webhook URL is allowed."""
        config = SafetyConfig(alert_webhook_url=None)
        assert config.alert_webhook_url is None

    @pytest.mark.parametrize(
        "webhook_url,expected_error",
        [
            ("", "must be a non-empty string"),
            ("invalid-url", "alert_webhook_url must start with http:// or https://"),
            ("ftp://example.com/webhook", "alert_webhook_url must start with http:// or https://"),
            ("example.com/webhook", "alert_webhook_url must start with http:// or https://"),
        ],
    )
    def test_invalid_webhook_url(self, webhook_url: str, expected_error: str):
        """Test invalid webhook URLs."""
        with pytest.raises(ValidationError) as exc_info:
            SafetyConfig(alert_webhook_url=webhook_url)
        assert expected_error in str(exc_info.value)

    def test_blocked_patterns_list(self):
        """Test blocked patterns as a list."""
        patterns = [r"rm -rf", r"sudo.*", r"chmod 777"]
        config = SafetyConfig(blocked_patterns=patterns)
        assert config.blocked_patterns == patterns
        assert len(config.blocked_patterns) == 3

    def test_allowed_exceptions_list(self):
        """Test allowed exceptions as a list."""
        exceptions = ["ls", "pwd", "cat"]
        config = SafetyConfig(allowed_exceptions=exceptions)
        assert config.allowed_exceptions == exceptions
        assert len(config.allowed_exceptions) == 3

    def test_empty_blocked_patterns(self):
        """Test empty blocked patterns list."""
        config = SafetyConfig(blocked_patterns=[])
        assert config.blocked_patterns == []

    def test_empty_allowed_exceptions(self):
        """Test empty allowed exceptions list."""
        config = SafetyConfig(allowed_exceptions=[])
        assert config.allowed_exceptions == []

    def test_production_config(self):
        """Test production environment configuration."""
        config = SafetyConfig(
            environment="production",
            risk_threshold="critical",
            block_in_production=True,
            require_review_for_high_risk=True,
            enable_audit_logging=True,
            audit_log_path="/var/log/forge/audit",
        )
        assert config.environment == "production"
        assert config.risk_threshold == "critical"
        assert config.block_in_production is True
        assert config.require_review_for_high_risk is True

    def test_development_config(self):
        """Test development environment configuration."""
        config = SafetyConfig(
            environment="development",
            risk_threshold="low",
            block_in_production=False,
            require_review_for_high_risk=False,
        )
        assert config.environment == "development"
        assert config.risk_threshold == "low"
        assert config.block_in_production is False

    def test_model_serialization(self):
        """Test model can be serialized to dict."""
        config = SafetyConfig(
            risk_threshold="medium",
            environment="staging",
            alert_webhook_url="https://example.com/webhook",
        )
        data = config.model_dump()
        assert isinstance(data, dict)
        assert data["risk_threshold"] == "medium"
        assert data["environment"] == "staging"
        assert data["alert_webhook_url"] == "https://example.com/webhook"

    def test_model_from_dict(self):
        """Test model can be created from dict."""
        data = {
            "risk_threshold": "high",
            "environment": "production",
            "enable_audit_logging": False,
            "blocked_patterns": [r"rm -rf"],
        }
        config = SafetyConfig(**data)
        assert config.risk_threshold == "high"
        assert config.environment == "production"
        assert config.enable_audit_logging is False
        assert config.blocked_patterns == [r"rm -rf"]

