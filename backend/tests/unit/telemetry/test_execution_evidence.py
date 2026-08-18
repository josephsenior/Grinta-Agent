from __future__ import annotations

import json

from backend.telemetry.evidence.emitter import emit_execution_evidence
from backend.telemetry.evidence.fingerprint import fingerprint_json
from backend.telemetry.evidence.projector import project
from backend.telemetry.evidence.report import write_evidence_report
from backend.telemetry.evidence.schema import EvidenceKind, ExecutionEvidence


def test_schema_serializes_and_fingerprint_is_canonical() -> None:
    record = ExecutionEvidence(EvidenceKind.MODEL_TURN, {'prompt_tokens': 3}).to_dict()
    assert record['schema_version'] == 1
    assert record['kind'] == 'model_turn'
    assert fingerprint_json({'a': 1, 'b': 2}) == fingerprint_json({'b': 2, 'a': 1})


def test_projector_ignores_duplicate_unknown_and_malformed_records(tmp_path) -> None:
    payload = ExecutionEvidence(
        EvidenceKind.TOOL_EXECUTION,
        {
            'tool': 'run',
            'outcome': 'success',
            'verification_kind': 'test',
            'exit_code': 0,
        },
    ).to_dict()
    lines = [
        json.dumps(
            {
                'ts': '2026-01-01T00:00:00+00:00',
                'event': 'EXECUTION_EVIDENCE',
                'payload': payload,
            }
        ),
        json.dumps({'event': 'EXECUTION_EVIDENCE', 'payload': payload}),
        json.dumps(
            {
                'event': 'EXECUTION_EVIDENCE',
                'payload': {
                    'schema_version': 1,
                    'evidence_id': 'future',
                    'kind': 'future',
                    'data': {},
                },
            }
        ),
        '{broken',
    ]
    path = tmp_path / 'session.jsonl'
    path.write_text('\n'.join(lines), encoding='utf-8')
    result = project(path)
    assert result['tools']['total'] == 1
    assert result['verification_activity'] == {'test_runs': 1, 'last_test_exit_code': 0}


def test_report_is_idempotent(tmp_path) -> None:
    (tmp_path / 'session.jsonl').write_text('', encoding='utf-8')
    first = write_evidence_report(tmp_path)
    second = write_evidence_report(tmp_path)
    assert first == second
    assert json.loads((tmp_path / 'session.evidence.json').read_text()) == first


def test_projector_counts_control_interventions() -> None:
    records = [
        {
            'event': 'EXECUTION_EVIDENCE',
            'payload': ExecutionEvidence(
                EvidenceKind.CONTROL_INTERVENTION,
                {'intervention': 'retry_scheduled'},
            ).to_dict(),
        },
        {
            'event': 'EXECUTION_EVIDENCE',
            'payload': ExecutionEvidence(
                EvidenceKind.CONTROL_INTERVENTION,
                {'intervention': 'stuck_detected'},
            ).to_dict(),
        },
    ]
    result = project(records)
    assert result['reliability']['control_interventions'] == 2
    assert result['reliability']['retries'] == 1
    assert result['reliability']['stuck_detections'] == 1


def test_emitter_fails_open_when_session_logger_fails(monkeypatch) -> None:
    def broken_logger(*args, **kwargs):
        raise RuntimeError('logger unavailable')

    monkeypatch.setattr(
        'backend.core.logging.session_event_logger.emit_session_event', broken_logger
    )
    emit_execution_evidence(EvidenceKind.TOOL_EXECUTION, {'tool': 'run'})
