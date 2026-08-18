"""Shared post-compaction artifact finalization."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from backend.core.logging.logger import app_logger as logger

if TYPE_CHECKING:
    from backend.orchestration.state.state import State


def finalize_compaction_artifacts(*, state: State) -> dict[str, Any] | None:
    """Commit staged compaction artifacts and sync session-scoped memory."""
    try:
        from backend.context.compactor.pre_condensation_snapshot import (
            commit_snapshot,
            load_snapshot,
        )
        from backend.context.memory.working_set import sync_snapshot_to_working_memory

        commit_snapshot(state=state)
        snapshot = load_snapshot(state=state)
        sync_snapshot_to_working_memory(snapshot, state=state)
        if isinstance(snapshot, dict):
            try:
                from backend.telemetry.evidence import (
                    EvidenceKind,
                    emit_execution_evidence,
                )
                from backend.telemetry.evidence.fingerprint import fingerprint_text

                objective = str(snapshot.get('objective', '') or '')
                criteria = snapshot.get('acceptance_criteria', {})
                emit_execution_evidence(
                    EvidenceKind.CONTEXT_COMPACTION,
                    {
                        'events_condensed': snapshot.get('events_condensed'),
                        'files_preserved': len(snapshot.get('files_touched', {}) or {}),
                        'errors_preserved': len(
                            snapshot.get('recent_errors', []) or []
                        ),
                        'decisions_preserved': len(snapshot.get('decisions', []) or []),
                        'task_items_preserved': len(
                            snapshot.get('task_plan', {}) or {}
                        ),
                        'criteria_preserved': len(criteria or {}),
                        'objective_fingerprint': fingerprint_text(objective),
                        'contract_fingerprint': fingerprint_text(str(criteria)),
                        'tokens_before': None,
                        'tokens_after': None,
                    },
                )
            except Exception:
                logger.debug('Compaction evidence emission failed', exc_info=True)
        return snapshot if isinstance(snapshot, dict) else None
    except Exception:
        logger.debug('Post-compaction artifact finalization failed', exc_info=True)
        return None


__all__ = ['finalize_compaction_artifacts']
