"""Additional tests for forge.controller.safety_validator."""

from __future__ import annotations

from types import SimpleNamespace

import pytest

from forge.controller.safety_validator import (
    ExecutionContext,
    SafetyValidator,
    ValidationResult,
)
from forge.events.action import ActionSecurityRisk, CmdRunAction
from forge.security.command_analyzer import RiskCategory
from forge.security.safety_config import SafetyConfig


class DummyAnalysis(SimpleNamespace):
    """Helper namespace representing analyzer output."""


@pytest.fixture
def patched_validator(monkeypatch, tmp_path):
    """Create a SafetyValidator with patched dependencies."""

    assessments = DummyAnalysis(
        risk_level=ActionSecurityRisk.LOW,
        risk_category=RiskCategory.LOW,
        reason="Looks safe",
        matched_patterns=[],
    )

    class DummyAnalyzer:
        def __init__(self, *_args, **_kwargs):
            self.assessment = assessments

        def analyze_action(self, action):
            return self.assessment

    class DummyAuditLogger:
        async def log_action(self, **kwargs):
            return "audit-id"

    monkeypatch.setattr("forge.controller.safety_validator.CommandAnalyzer", DummyAnalyzer)

    config = SafetyConfig(
        enable_audit_logging=False,
        audit_log_path=str(tmp_path),
        enable_risk_alerts=True,
        environment="production",
        block_in_production=True,
        require_review_for_high_risk=True,
    )

    validator = SafetyValidator(config)
    return validator, assessments, DummyAuditLogger


def make_context(is_autonomous: bool = True) -> ExecutionContext:
    """Create a reusable execution context."""

    return ExecutionContext(
        session_id="session-1",
        iteration=3,
        agent_state="running",
        recent_errors=[],
        is_autonomous=is_autonomous,
    )


@pytest.mark.asyncio
async def test_validate_allows_safe_action(patched_validator):
    """validate should permit actions when assessment is low risk."""

    validator, assessments, AuditLoggerStub = patched_validator
    validator.audit_logger = AuditLoggerStub()
    assessments.risk_level = ActionSecurityRisk.LOW
    result = await validator.validate(CmdRunAction(command="ls"), make_context())

    assert isinstance(result, ValidationResult)
    assert result.allowed is True
    assert result.audit_id == "audit-id"
    assert result.requires_review is False


@pytest.mark.asyncio
async def test_validate_blocks_critical_risk(patched_validator):
    """Critical risk assessments should trigger blocks with detailed reasons."""

    validator, assessments, _ = patched_validator
    assessments.risk_category = RiskCategory.CRITICAL
    assessments.risk_level = ActionSecurityRisk.HIGH
    assessments.reason = "rm -rf detected"
    assessments.matched_patterns = ["rm -rf /"]

    action = CmdRunAction(command="rm -rf /")
    context = make_context()
    result = await validator.validate(action, context)

    assert result.allowed is False
    assert "CRITICAL RISK" in result.blocked_reason
    assert result.requires_review is True


@pytest.mark.asyncio
async def test_validate_blocks_high_risk_in_production(patched_validator):
    """High risk actions in production should be blocked when configured."""

    validator, assessments, _ = patched_validator
    assessments.risk_level = ActionSecurityRisk.HIGH
    assessments.risk_category = RiskCategory.HIGH
    assessments.reason = "Dangerous command"

    result = await validator.validate(CmdRunAction(command="danger"), make_context())
    assert result.allowed is False
    assert "HIGH RISK" in result.blocked_reason


def test_format_alert_message_includes_details(patched_validator):
    """Alert message should include key context fields."""

    validator, assessments, _ = patched_validator
    assessments.risk_level = ActionSecurityRisk.HIGH
    assessments.reason = "Dangerous command"
    context = make_context()
    result = ValidationResult(
        allowed=False,
        risk_level=ActionSecurityRisk.HIGH,
        risk_category=RiskCategory.HIGH,
        reason="Dangerous command",
        matched_patterns=[],
        blocked_reason="Dangerous command",
    )
    message = validator._format_alert_message(CmdRunAction(command="danger"), context, result)
    assert "Session: session-1" in message
    assert "Risk Level: HIGH" in message


@pytest.mark.asyncio
async def test_send_alert_uses_asyncio_create_task(patched_validator, monkeypatch):
    """_send_alert should dispatch webhook tasks when enabled."""

    validator, assessments, _ = patched_validator
    assessments.risk_level = ActionSecurityRisk.HIGH
    assessments.reason = "danger"

    scheduled = {}
    monkeypatch.setattr("forge.controller.safety_validator.asyncio.create_task", lambda coro: scheduled.setdefault("task", coro))

    context = make_context()
    validator.config.alert_webhook_url = "https://hook.example.com"
    result = ValidationResult(
        allowed=False,
        risk_level=ActionSecurityRisk.HIGH,
        risk_category=RiskCategory.HIGH,
        reason="danger",
        matched_patterns=[],
        blocked_reason="danger",
    )
    await validator._send_alert(CmdRunAction(command="danger"), context, result)
    assert "task" in scheduled


@pytest.mark.asyncio
async def test_log_to_audit_handles_exceptions(patched_validator, monkeypatch):
    """_log_to_audit should absorb errors from the audit logger."""

    validator, _, _ = patched_validator

    class FailingAuditLogger:
        async def log_action(self, **kwargs):
            raise RuntimeError("failure")

    validator.audit_logger = FailingAuditLogger()

    result = ValidationResult(
        allowed=True,
        risk_level=ActionSecurityRisk.LOW,
        risk_category=RiskCategory.LOW,
        reason="ok",
        matched_patterns=[],
    )
    audit_id = await validator._log_to_audit(CmdRunAction(command="ok"), make_context(), result)
    assert audit_id == "audit_error"

