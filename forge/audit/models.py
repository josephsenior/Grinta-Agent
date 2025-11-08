"""Data models for audit logging system."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime

from forge.events.action import ActionSecurityRisk


@dataclass
class AuditEntry:
    """Immutable audit log entry for an agent action."""

    id: str
    """Unique identifier for this audit entry."""

    timestamp: datetime
    """When the action occurred."""

    session_id: str
    """Session ID of the agent."""

    iteration: int
    """Iteration number when action occurred."""

    action_type: str
    """Type of action (CmdRunAction, FileEditAction, etc.)."""

    action_content: str
    """Content/details of the action."""

    risk_level: ActionSecurityRisk
    """Assessed risk level of the action."""

    validation_result: str
    """Result of validation: 'allowed', 'blocked', 'requires_review'."""

    execution_result: str | None = None
    """Result of action execution if it was allowed."""

    blocked_reason: str | None = None
    """Reason for blocking if action was blocked."""

    filesystem_snapshot_id: str | None = None
    """ID of filesystem snapshot if taken before high-risk action."""

    rollback_available: bool = False
    """Whether rollback is available for this action."""

    matched_risk_patterns: list[str] = field(default_factory=list)
    """Risk patterns that matched this action."""

    environment: str = "development"
    """Environment where action occurred."""

    agent_state: str = "unknown"
    """State of agent when action occurred."""

    def to_dict(self) -> dict:
        """Convert audit entry to dictionary for JSON serialization."""
        return {
            "id": self.id,
            "timestamp": self.timestamp.isoformat(),
            "session_id": self.session_id,
            "iteration": self.iteration,
            "action_type": self.action_type,
            "action_content": self.action_content,
            "risk_level": self.risk_level.name,
            "validation_result": self.validation_result,
            "execution_result": self.execution_result,
            "blocked_reason": self.blocked_reason,
            "filesystem_snapshot_id": self.filesystem_snapshot_id,
            "rollback_available": self.rollback_available,
            "matched_risk_patterns": self.matched_risk_patterns,
            "environment": self.environment,
            "agent_state": self.agent_state,
        }

    @classmethod
    def from_dict(cls, data: dict) -> AuditEntry:
        """Create audit entry from dictionary."""
        # Convert timestamp string back to datetime
        if isinstance(data.get("timestamp"), str):
            data["timestamp"] = datetime.fromisoformat(data["timestamp"])

        # Convert risk_level string back to enum
        if isinstance(data.get("risk_level"), str):
            data["risk_level"] = ActionSecurityRisk[data["risk_level"]]

        return cls(**data)
