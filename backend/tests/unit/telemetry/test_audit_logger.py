"""Unit tests for backend.telemetry.audit_logger — AuditLogger."""

from __future__ import annotations

import json
from datetime import datetime
from typing import Any, cast
from unittest.mock import MagicMock, patch

import pytest

from backend.ledger.action import ActionSecurityRisk
from backend.telemetry.audit_logger import AuditLogger, _redact_credentials

# ── helpers ──────────────────────────────────────────────────────────


def _make_validation_result(
    *,
    allowed: bool = True,
    risk_level: ActionSecurityRisk = ActionSecurityRisk.LOW,
    requires_review: bool = False,
    blocked_reason: str | None = None,
    matched_patterns: list[str] | None = None,
) -> MagicMock:
    vr = MagicMock()
    vr.allowed = allowed
    vr.risk_level = risk_level
    vr.requires_review = requires_review
    vr.blocked_reason = blocked_reason
    vr.matched_patterns = matched_patterns or []
    return vr


def _make_cmd_action(command: str = 'echo hello') -> MagicMock:
    from backend.ledger.action import CmdRunAction

    action = MagicMock(spec=CmdRunAction)
    action.command = command
    type(action).__name__ = 'CmdRunAction'
    return action


def _make_file_edit_action(path: str = 'file.py') -> MagicMock:
    from backend.ledger.action import FileEditAction

    action = MagicMock(spec=FileEditAction)
    action.path = path
    type(action).__name__ = 'FileEditAction'
    return action


# ── AuditLogger init ────────────────────────────────────────────────


class TestAuditLoggerInit:
    def test_creates_directory(self, tmp_path):
        audit_dir = str(tmp_path / 'audit' / 'logs')
        logger = AuditLogger(audit_dir)
        assert logger.audit_base_path.exists()

    def test_existing_directory(self, tmp_path):
        audit_dir = str(tmp_path / 'existing')
        (tmp_path / 'existing').mkdir()
        logger = AuditLogger(audit_dir)
        assert logger.audit_base_path.exists()


class TestCredentialRedaction:
    def test_redact_credentials_patterns(self):
        assert _redact_credentials("") == ""
        assert "<credential_redacted>" in _redact_credentials("sk-12345678901234567890")
        assert "<credential_redacted>" in _redact_credentials("ghp_12345678901234567890")
        assert "<credential_redacted>" in _redact_credentials("Bearer 12345678901234567890")
        assert _redact_credentials("normal_text_123") == "normal_text_123"


# ── _extract_action_content ──────────────────────────────────────────


class TestExtractActionContent:
    def test_cmd_action(self, tmp_path):
        al = AuditLogger(str(tmp_path))
        action = _make_cmd_action('ls -la')
        content = al._extract_action_content(action)
        assert content == 'ls -la'

    def test_file_edit_action(self, tmp_path):
        al = AuditLogger(str(tmp_path))
        action = _make_file_edit_action('src/main.py')
        content = al._extract_action_content(action)
        assert 'src/main.py' in content

    def test_truncation(self, tmp_path):
        al = AuditLogger(str(tmp_path))
        action = _make_cmd_action('x' * 2000)
        content = al._extract_action_content(action)
        assert len(content) < 2000
        assert 'truncated' in content

    def test_fallback_str(self, tmp_path):
        al = AuditLogger(str(tmp_path))
        action = MagicMock()
        cast(Any, action).__str__ = MagicMock(return_value='some-action')
        type(action).__name__ = 'OtherAction'
        content = al._extract_action_content(action)
        assert isinstance(content, str)


class TestAuditLoggerSnapshotAndUpdate:
    @pytest.mark.asyncio
    async def test_update_entry_snapshot_non_existent(self, tmp_path):
        al = AuditLogger(str(tmp_path))
        # Log file doesn't exist yet -> returns False
        res = await al.update_entry_snapshot("missing_session", "audit_id", "snap_id")
        assert res is False

    @pytest.mark.asyncio
    async def test_update_entry_snapshot_with_corrupt_and_valid_lines(self, tmp_path):
        al = AuditLogger(str(tmp_path))
        log_file = al._get_session_log_file("s1")
        log_file.write_text("invalid_json_line\n{\"id\": \"target_id\", \"filesystem_snapshot_id\": null}\n", encoding="utf-8")

        updated = await al.update_entry_snapshot("s1", "target_id", "snap_123")
        assert updated is True
        content = log_file.read_text(encoding="utf-8")
        assert "snap_123" in content

    def test_read_session_audit_handles_corrupt_json(self, tmp_path):
        al = AuditLogger(str(tmp_path))
        log_file = al._get_session_log_file("s2")
        log_file.write_text("invalid json\n", encoding="utf-8")
        entries = al.read_session_audit("s2")
        assert entries == []

    def test_export_audit_trail_exception(self, tmp_path):
        al = AuditLogger(str(tmp_path))
        with patch.object(al, "read_session_audit", side_effect=PermissionError("Read error")):
            # Should catch exception without crashing
            al.export_audit_trail("s3", str(tmp_path / "out.json"))
