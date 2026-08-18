"""Schema v1 for compact, forward-compatible execution evidence."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from enum import StrEnum
from typing import Any
from uuid import uuid4


class EvidenceKind(StrEnum):
    MODEL_TURN = 'model_turn'
    TOOL_EXECUTION = 'tool_execution'
    CONTROL_INTERVENTION = 'control_intervention'
    CONTEXT_COMPACTION = 'context_compaction'
    CHECKPOINT = 'checkpoint'
    USER_INPUT = 'user_input'
    FINISH_DECLARED = 'finish_declared'
    COMPLETION_VALIDATION = 'completion_validation'


@dataclass
class Correlation:
    ledger_event_id: int | None = None
    cause_event_id: int | None = None
    action_id: int | None = None
    observation_event_id: int | None = None
    response_id: str | None = None
    tool_call_id: str | None = None
    astep_id: str | None = None


@dataclass
class ExecutionEvidence:
    kind: EvidenceKind | str
    data: dict[str, Any] = field(default_factory=dict)
    correlation: Correlation = field(default_factory=Correlation)
    schema_version: int = 1
    evidence_id: str = field(default_factory=lambda: str(uuid4()))

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data['kind'] = str(self.kind)
        return data
