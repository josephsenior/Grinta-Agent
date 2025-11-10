from __future__ import annotations

from types import SimpleNamespace
import sys
import types
from unittest.mock import AsyncMock

import asyncio
import pytest

from forge.controller.safety_validator import (
    ExecutionContext,
    SafetyValidator,
    ValidationResult,
)
from forge.events.action import ActionSecurityRisk, CmdRunAction
from forge.security.command_analyzer import RiskCategory
from forge.security.safety_config import SafetyConfig


class _StubAnalyzer:
    def __init__(self, assessment):
        self._assessment = assessment

    def analyze_action(self, action):
        return self._assessment


def _context(is_autonomous: bool = False) -> ExecutionContext:
    return ExecutionContext(
        session_id="session",
        iteration=5,
        agent_state="RUNNING",
        recent_errors=[],
        is_autonomous=is_autonomous,
    )


def _assessment(
    *,
    risk_level: ActionSecurityRisk,
    risk_category: RiskCategory,
    reason: str = "reason",
    matched_patterns: list[str] | None = None,
):
    return SimpleNamespace(
        risk_level=risk_level,
        risk_category=risk_category,
        reason=reason,
        matched_patterns=matched_patterns or ["pattern"],
    )


def _config(**overrides) -> SafetyConfig:
    base = dict(
        environment="development",
        enable_audit_logging=False,
        enable_risk_alerts=False,
        blocked_patterns=[],
        allowed_exceptions=[],
        block_in_production=True,
        risk_threshold="high",
        enable_mandatory_validation=True,
        require_review_for_high_risk=False,
    )
    base.update(overrides)
    return SafetyConfig(**base)


@pytest.mark.asyncio
async def test_validate_blocks_critical_risk():
    config = _config(environment="production")
    validator = SafetyValidator(config)
    validator.analyzer = _StubAnalyzer(
        _assessment(risk_level=ActionSecurityRisk.HIGH, risk_category=RiskCategory.CRITICAL),
    )

    result = await validator.validate(CmdRunAction(command="rm -rf /"), _context())
    assert not result.allowed
    assert result.blocked_reason and "CRITICAL" in result.blocked_reason


@pytest.mark.asyncio
async def test_validate_blocks_high_risk_in_production():
    config = _config(environment="production", enable_mandatory_validation=False)
    validator = SafetyValidator(config)
    validator.analyzer = _StubAnalyzer(
        _assessment(risk_level=ActionSecurityRisk.HIGH, risk_category=RiskCategory.HIGH),
    )

    result = await validator.validate(CmdRunAction(command="chmod 777 file"), _context())
    assert not result.allowed
    assert result.blocked_reason and "HIGH RISK" in result.blocked_reason


@pytest.mark.asyncio
async def test_validate_blocks_high_risk_autonomous_when_mandatory():
    config = _config(require_review_for_high_risk=True)
    validator = SafetyValidator(config)
    validator.analyzer = _StubAnalyzer(
        _assessment(risk_level=ActionSecurityRisk.HIGH, risk_category=RiskCategory.HIGH),
    )

    result = await validator.validate(CmdRunAction(command="danger"), _context(is_autonomous=True))
    assert not result.allowed
    assert result.requires_review  # review required for high risk


@pytest.mark.asyncio
async def test_validate_allows_medium_risk():
    config = _config()
    validator = SafetyValidator(config)
    validator.analyzer = _StubAnalyzer(
        _assessment(risk_level=ActionSecurityRisk.MEDIUM, risk_category=RiskCategory.MEDIUM, matched_patterns=[]),
    )

    result = await validator.validate(CmdRunAction(command="ls"), _context())
    assert result.allowed
    assert result.blocked_reason is None
    assert not result.requires_review


@pytest.mark.asyncio
async def test_log_to_audit_handles_disabled_and_errors():
    config = _config()
    validator = SafetyValidator(config)
    action = CmdRunAction(command="echo hi")
    context = _context()
    dummy_result = ValidationResult(
        allowed=True,
        risk_level=ActionSecurityRisk.LOW,
        risk_category=RiskCategory.LOW,
        reason="ok",
        matched_patterns=[],
    )

    audit_id = await validator._log_to_audit(action, context, dummy_result)
    assert audit_id == "audit_disabled"

    validator.audit_logger = SimpleNamespace(
        log_action=AsyncMock(side_effect=RuntimeError("fail")),
    )
    audit_id = await validator._log_to_audit(action, context, dummy_result)
    assert audit_id == "audit_error"
    validator.audit_logger = SimpleNamespace(
        log_action=AsyncMock(return_value="audit-success"),
    )
    assert await validator._log_to_audit(action, context, dummy_result) == "audit-success"


def test_validator_initializes_audit_logger(monkeypatch, tmp_path):
    class DummyAuditLogger:
        def __init__(self, path):
            self.path = path

        async def log_action(self, **kwargs):
            return "dummy"

    monkeypatch.setitem(sys.modules, "forge.audit.audit_logger", types.SimpleNamespace(AuditLogger=DummyAuditLogger))
    config = _config(enable_audit_logging=True, audit_log_path=str(tmp_path))
    validator = SafetyValidator(config)
    assert isinstance(validator.audit_logger, DummyAuditLogger)


@pytest.mark.asyncio
async def test_send_alert_triggers_webhook(monkeypatch):
    config = _config(enable_risk_alerts=True, alert_webhook_url="https://example.com")
    validator = SafetyValidator(config)
    validator._send_webhook_alert = AsyncMock(return_value=None)

    recorded = []

    class _DummyTask:
        def __init__(self, coro):
            self._coro = coro

        def __await__(self):
            return self._coro.__await__()

    def _fake_create_task(coro):
        recorded.append(coro)
        return _DummyTask(asyncio.sleep(0))

    monkeypatch.setattr(asyncio, "create_task", _fake_create_task)

    result = ValidationResult(
        allowed=False,
        risk_level=ActionSecurityRisk.HIGH,
        risk_category=RiskCategory.HIGH,
        reason="blocked",
        matched_patterns=["pattern"],
        blocked_reason="blocked reason",
    )

    await validator._send_alert(CmdRunAction(command="rm -rf /"), _context(), result)
    assert recorded  # webhook coroutine scheduled


@pytest.mark.asyncio
async def test_send_alert_high_risk_without_block(monkeypatch):
    config = _config(enable_risk_alerts=True, alert_webhook_url=None)
    validator = SafetyValidator(config)
    validator._send_webhook_alert = AsyncMock()

    result = ValidationResult(
        allowed=True,
        risk_level=ActionSecurityRisk.HIGH,
        risk_category=RiskCategory.HIGH,
        reason="risky",
        matched_patterns=["pattern"],
    )

    await validator._send_alert(CmdRunAction(command="cmd"), _context(), result)


@pytest.mark.asyncio
async def test_send_webhook_alert_success(monkeypatch):
    class DummyResponse:
        status = 200

        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, tb):
            return None

    class DummySession:
        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, tb):
            return None

        async def post(self, *args, **kwargs):
            return DummyResponse()

    class DummyTimeout:
        def __init__(self, total):
            self.total = total

    aiohttp_stub = types.SimpleNamespace(ClientSession=lambda: DummySession(), ClientTimeout=DummyTimeout)
    monkeypatch.setitem(sys.modules, "aiohttp", aiohttp_stub)

    validator = SafetyValidator(_config(alert_webhook_url="https://example.com"))
    await validator._send_webhook_alert("alert")


@pytest.mark.asyncio
async def test_send_webhook_alert_handles_error_status(monkeypatch):
    class DummyResponse:
        status = 500

        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, tb):
            return None

    class DummySession:
        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, tb):
            return None

        async def post(self, *args, **kwargs):
            return DummyResponse()

    class DummyTimeout:
        def __init__(self, total):
            self.total = total

    aiohttp_stub = types.SimpleNamespace(ClientSession=lambda: DummySession(), ClientTimeout=DummyTimeout)
    monkeypatch.setitem(sys.modules, "aiohttp", aiohttp_stub)

    validator = SafetyValidator(_config(alert_webhook_url="https://example.com"))
    await validator._send_webhook_alert("alert")

