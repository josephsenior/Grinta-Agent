from __future__ import annotations

import json

from backend.telemetry.evidence.report import write_evidence_report
from backend.telemetry.evidence.schema import EvidenceKind, ExecutionEvidence


def test_synthetic_session_lifecycle_produces_coherent_evidence_report(tmp_path) -> None:
    session_log = tmp_path / 'session.jsonl'
    records = [
        ExecutionEvidence(
            EvidenceKind.USER_INPUT,
            {'content_fingerprint': 'sha256:user', 'content_length': 12},
        ),
        ExecutionEvidence(
            EvidenceKind.MODEL_TURN,
            {'prompt_tokens': 10, 'completion_tokens': 4, 'cost_usd': 0.01},
        ),
        ExecutionEvidence(
            EvidenceKind.TOOL_EXECUTION,
            {
                'tool': 'run',
                'outcome': 'success',
                'verification_kind': 'test',
                'exit_code': 0,
                'changed_paths': ['src/app.py'],
            },
        ),
        ExecutionEvidence(
            EvidenceKind.FINISH_DECLARED,
            {'recorded_task_status': 'clear'},
        ),
        ExecutionEvidence(
            EvidenceKind.COMPLETION_VALIDATION,
            {'validator': 'current_task_validator', 'mode': 'advisory', 'enabled': False},
        ),
    ]
    with session_log.open('w', encoding='utf-8') as handle:
        for record in records:
            handle.write(json.dumps({'event': 'EXECUTION_EVIDENCE', 'payload': record.to_dict()}) + '\n')

    summary = write_evidence_report(tmp_path)
    report = json.loads((tmp_path / 'session.evidence.json').read_text(encoding='utf-8'))

    assert report == summary
    assert report['run']['final_agent_state'] == 'FINISHED'
    assert report['run']['additional_user_inputs'] == 0
    assert report['model']['turns'] == 1
    assert report['tools']['total'] == 1
    assert report['verification_activity']['last_test_exit_code'] == 0
    assert report['completion']['completion_validator']['enabled'] is False
