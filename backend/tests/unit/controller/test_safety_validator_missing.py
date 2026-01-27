"""Tests for missing coverage in safety_validator.py."""

from __future__ import annotations

import sys
import types
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from forge.controller.safety_validator import (
    ExecutionContext,
    SafetyValidator,
    ValidationResult,
)
from forge.events.action import ActionSecurityRisk, CmdRunAction
from forge.security.command_analyzer import RiskCategory
from forge.security.safety_config import SafetyConfig


def _context() -> ExecutionContext:
    return ExecutionContext(
        session_id="session",
        iteration=5,
        agent_state="RUNNING",
        recent_errors=[],
        is_autonomous=False,
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


class _StubAnalyzer:
    def __init__(self, assessment):
        self._assessment = assessment

    def analyze_action(self, action):
        return self._assessment


# Note: ImportError path (lines 81-82) is difficult to test without breaking imports
# Coverage is already at 95.28% which exceeds the 95% target


@pytest.mark.asyncio
async def test_get_blocked_reason_returns_assessment_reason():
    """Test _get_blocked_reason returns assessment.reason for non-CRITICAL/HIGH risks."""
    config = SafetyConfig(environment="development")
    validator = SafetyValidator(config)
    assessment = _assessment(
        risk_level=ActionSecurityRisk.MEDIUM,
        risk_category=RiskCategory.MEDIUM,
        reason="Medium risk reason",
    )
    result = validator._get_blocked_reason(assessment)
    assert result == "Medium risk reason"


@pytest.mark.asyncio
async def test_send_webhook_alert_no_url():
    """Test _send_webhook_alert returns early when no URL is configured."""
    config = SafetyConfig(alert_webhook_url=None)
    validator = SafetyValidator(config)
    # Should not raise
    await validator._send_webhook_alert("test message")


@pytest.mark.asyncio
async def test_send_webhook_alert_error_status(monkeypatch):
    """Test _send_webhook_alert handles non-200 status codes."""
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

    aiohttp_stub = types.SimpleNamespace(
        ClientSession=lambda: DummySession(), ClientTimeout=DummyTimeout
    )
    monkeypatch.setitem(sys.modules, "aiohttp", aiohttp_stub)

    validator = SafetyValidator(SafetyConfig(alert_webhook_url="https://example.com"))
    # Should not raise, just log error (covers lines 323-324)
    await validator._send_webhook_alert("test message")


@pytest.mark.asyncio
async def test_send_webhook_alert_exception_handling(monkeypatch):
    """Test _send_webhook_alert handles exceptions."""
    class DummySession:
        async def __aenter__(self):
            raise RuntimeError("Connection failed")

        async def __aexit__(self, exc_type, exc, tb):
            return None

    class DummyTimeout:
        def __init__(self, total):
            self.total = total

    aiohttp_stub = types.SimpleNamespace(
        ClientSession=lambda: DummySession(), ClientTimeout=DummyTimeout
    )
    monkeypatch.setitem(sys.modules, "aiohttp", aiohttp_stub)

    validator = SafetyValidator(SafetyConfig(alert_webhook_url="https://example.com"))
    # Should not raise, just log error
    await validator._send_webhook_alert("test message")

