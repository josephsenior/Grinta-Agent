"""Audit logger for tracking all autonomous agent actions."""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import TYPE_CHECKING
from uuid import uuid4

if TYPE_CHECKING:
    from datetime import datetime

    from backend.controller.safety_validator import ValidationResult
    from backend.events.action import Action

from backend.telemetry.models import AuditEntry
from backend.core.logger import forge_logger as logger
from backend.events.action import ActionSecurityRisk


class AuditLogger:
    """Immutable audit logger for autonomous agent actions.

    Logs all actions to an append-only JSON log file for compliance and debugging.
    Each entry includes:
    - Action details
    - Risk assessment
    - Validation result
    - Execution result
    - Optional filesystem snapshot ID for rollback
    """

    def __init__(self, audit_log_path: str) -> None:
        """Initialize the audit logger.

        Args:
            audit_log_path: Base path for audit logs

        """
        # Expand user home directory
        self.audit_base_path = Path(os.path.expanduser(audit_log_path))
        self.audit_base_path.mkdir(parents=True, exist_ok=True)

        # Create session-specific log file
        self.current_session_log = None

        logger.info(f"AuditLogger initialized at {self.audit_base_path}")

    async def log_action(
        self,
        session_id: str,
        iteration: int,
        action: Action,
        validation_result: ValidationResult,
        timestamp: datetime,
        execution_result: str | None = None,
    ) -> str:
        """Log an action to the audit trail.

        Args:
            session_id: Session ID
            iteration: Iteration number
            action: The action being logged
            validation_result: Result of safety validation
            timestamp: When the action occurred
            execution_result: Optional result of action execution

        Returns:
            Audit entry ID

        """
        # Generate unique audit ID
        audit_id = str(uuid4())

        # Get action details
        action_type = type(action).__name__
        action_content = self._extract_action_content(action)

        # Determine validation result string
        if not validation_result.allowed:
            validation_status = "blocked"
        elif validation_result.requires_review:
            validation_status = "requires_review"
        else:
            validation_status = "allowed"

        # Create audit entry
        entry = AuditEntry(
            id=audit_id,
            timestamp=timestamp,
            session_id=session_id,
            iteration=iteration,
            action_type=action_type,
            action_content=action_content,
            risk_level=validation_result.risk_level,
            validation_result=validation_status,
            execution_result=execution_result,
            blocked_reason=validation_result.blocked_reason,
            matched_risk_patterns=validation_result.matched_patterns,
            rollback_available=False,  # Will be updated if snapshot is taken
        )

        # Write to log file
        await self._write_entry(session_id, entry)

        return audit_id

    def _extract_action_content(self, action: Action) -> str:
        """Extract content from action for logging.

        Args:
            action: The action

        Returns:
            Action content string (truncated if too long)

        """
        from backend.events.action import (
            CmdRunAction,
            FileEditAction,
        )

        if isinstance(action, CmdRunAction):
            content = action.command
        elif isinstance(action, FileEditAction):
            content = f"Edit {action.path}"
        else:
            content = str(action)

        # Truncate if too long
        max_length = 1000
        if len(content) > max_length:
            content = content[:max_length] + "... (truncated)"

        return content

    async def _write_entry(self, session_id: str, entry: AuditEntry) -> None:
        """Write audit entry to log file.

        Args:
            session_id: Session ID
            entry: Audit entry to write

        """
        try:
            # Get or create session log file
            log_file = self._get_session_log_file(session_id)

            # Append entry to log file (JSONL format)
            with open(log_file, "a", encoding="utf-8") as f:
                json.dump(entry.to_dict(), f)
                f.write("\n")

        except Exception as e:
            logger.error(f"Failed to write audit entry: {e}")

    def _get_session_log_file(self, session_id: str) -> Path:
        """Get log file path for session.

        Args:
            session_id: Session ID

        Returns:
            Path to session log file

        """
        # Create session-specific log file
        safe_session_id = session_id.replace("/", "_").replace("\\", "_")
        log_file = self.audit_base_path / f"session_{safe_session_id}.jsonl"

        # Create file if it doesn't exist
        if not log_file.exists():
            log_file.touch()
            logger.info(f"Created audit log file: {log_file}")

        return log_file

    def read_session_audit(self, session_id: str) -> list[AuditEntry]:
        """Read audit trail for a session.

        Args:
            session_id: Session ID

        Returns:
            List of audit entries for the session

        """
        try:
            log_file = self._get_session_log_file(session_id)

            if not log_file.exists():
                return []

            entries = []
            with open(log_file, encoding="utf-8") as f:
                for line in f:
                    if line.strip():
                        try:
                            data = json.loads(line)
                            entry = AuditEntry.from_dict(data)
                            entries.append(entry)
                        except Exception as e:
                            logger.error(f"Failed to parse audit entry: {e}")
                            continue

            return entries

        except Exception as e:
            logger.error(f"Failed to read audit trail: {e}")
            return []

    def get_blocked_actions(self, session_id: str) -> list[AuditEntry]:
        """Get all blocked actions for a session.

        Args:
            session_id: Session ID

        Returns:
            List of blocked audit entries

        """
        all_entries = self.read_session_audit(session_id)
        return [entry for entry in all_entries if entry.validation_result == "blocked"]

    def get_high_risk_actions(self, session_id: str) -> list[AuditEntry]:
        """Get all high-risk actions for a session.

        Args:
            session_id: Session ID

        Returns:
            List of high-risk audit entries

        """
        all_entries = self.read_session_audit(session_id)
        return [
            entry
            for entry in all_entries
            if entry.risk_level == ActionSecurityRisk.HIGH
        ]

    def export_audit_trail(self, session_id: str, output_path: str) -> None:
        """Export audit trail to a file for compliance.

        Args:
            session_id: Session ID
            output_path: Output file path

        """
        try:
            entries = self.read_session_audit(session_id)

            with open(output_path, "w", encoding="utf-8") as f:
                json.dump(
                    [entry.to_dict() for entry in entries],
                    f,
                    indent=2,
                    default=str,
                )

            logger.info(f"Exported audit trail to {output_path}")

        except Exception as e:
            logger.error(f"Failed to export audit trail: {e}")
