import pytest

from backend.task_state.service import TaskStateService
from backend.task_state.store import TaskStateStore


def test_set_preserves_unsupplied_contract_fields(tmp_path):
    service = TaskStateService(TaskStateStore(tmp_path))
    state, _ = service.apply(
        'set',
        {
            'objective': 'Ship it',
            'requirements': [{'id': 'req-1', 'text': 'Keep API', 'source': 'user'}],
        },
    )
    state, _ = service.apply(
        'set',
        {
            'tasks': [{'id': 'task-1', 'description': 'Inspect'}],
            'expected_revision': state.revision,
        },
    )
    assert state.contract is not None
    assert state.contract.requirements[0].text == 'Keep API'
    assert state.plan is not None


def test_audit_records_structured_evidence(tmp_path):
    service = TaskStateService(TaskStateStore(tmp_path))
    service.apply('set', {'requirements': [{'id': 'req-1', 'text': 'Tests pass'}]})
    state, _ = service.apply(
        'audit',
        {
            'evidence': [
                {
                    'item_id': 'req-1',
                    'status': 'satisfied',
                    'kind': 'test',
                    'evidence': '12 passed',
                }
            ]
        },
    )
    item = state.contract.requirements[0]
    assert item.status == 'satisfied'
    assert item.evidence[0].kind == 'test'


def test_active_plan_never_renders_clear(tmp_path):
    service = TaskStateService(TaskStateStore(tmp_path))
    _, review = service.apply(
        'set',
        {
            'tasks': [
                {'id': 'done', 'description': 'Finish milestone', 'status': 'done'},
                {
                    'id': 'next',
                    'description': 'Continue overall objective',
                    'status': 'todo',
                },
            ]
        },
    )

    assert 'RECORDED STATUS\nACTIVE' in review
    assert 'open plan: next' in review
    assert 'RECORDED STATUS\nCLEAR' not in review


def test_blocked_plan_is_reported_without_claiming_clear(tmp_path):
    service = TaskStateService(TaskStateStore(tmp_path))
    _, review = service.apply(
        'set',
        {
            'tasks': [
                {
                    'id': 'external',
                    'description': 'Wait for unavailable credential',
                    'status': 'blocked',
                }
            ]
        },
    )

    assert 'RECORDED STATUS\nBLOCKED — external' in review
    assert 'RECORDED STATUS\nCLEAR' not in review


def test_satisfied_contract_and_completed_plan_render_clear(tmp_path):
    service = TaskStateService(TaskStateStore(tmp_path))
    _, review = service.apply(
        'set',
        {
            'requirements': [
                {
                    'id': 'req',
                    'text': 'Requested behavior works',
                    'status': 'satisfied',
                }
            ],
            'tasks': [
                {'id': 'task', 'description': 'Implement behavior', 'status': 'done'}
            ],
        },
    )

    assert 'RECORDED STATUS\nCLEAR' in review
    assert 'no unresolved contract conditions or open tasks recorded' in review


def test_set_rejects_silently_ignored_contract_wrapper(tmp_path):
    service = TaskStateService(TaskStateStore(tmp_path))

    with pytest.raises(ValueError, match='wrapper field.*contract'):
        service.apply(
            'set',
            {'contract': '{"objective": "Do the whole task"}', 'tasks': []},
        )


def test_set_rejects_invalid_contract_status(tmp_path):
    service = TaskStateService(TaskStateStore(tmp_path))

    with pytest.raises(ValueError, match="Invalid contract status 'todo'"):
        service.apply(
            'set',
            {'requirements': [{'id': 'req', 'text': 'Finish', 'status': 'todo'}]},
        )


def test_expected_revision_mismatch(tmp_path):
    service = TaskStateService(TaskStateStore(tmp_path))
    with pytest.raises(ValueError, match="Task state changed since your last review"):
        service.apply('review', {'expected_revision': 99})


def test_unsupported_action(tmp_path):
    service = TaskStateService(TaskStateStore(tmp_path))
    with pytest.raises(ValueError, match="Unsupported task_state action"):
        service.apply('invalid_action', {})


def test_update_task_without_plan(tmp_path):
    service = TaskStateService(TaskStateStore(tmp_path))
    with pytest.raises(ValueError, match="No plan exists"):
        service.apply('update_task', {'task_id': 't1', 'status': 'done'})


def test_update_task_invalid_status_or_id(tmp_path):
    service = TaskStateService(TaskStateStore(tmp_path))
    service.apply('set', {'tasks': [{'id': 't1', 'description': 'desc', 'status': 'todo'}]})

    with pytest.raises(ValueError, match="Invalid task status 'bad_status'"):
        service.apply('update_task', {'task_id': 't1', 'status': 'bad_status'})

    with pytest.raises(ValueError, match="Task 'missing' not found"):
        service.apply('update_task', {'task_id': 'missing', 'status': 'done'})


def test_audit_without_contract(tmp_path):
    service = TaskStateService(TaskStateStore(tmp_path))
    with pytest.raises(ValueError, match="No contract exists"):
        service.apply('audit', {'evidence': []})


def test_contract_item_validation_errors(tmp_path):
    service = TaskStateService(TaskStateStore(tmp_path))
    with pytest.raises(ValueError, match="Contract item fields must be lists"):
        service.apply('set', {'requirements': 'not_a_list'})

    with pytest.raises(ValueError, match="Invalid requirement source 'bad_source'"):
        service.apply('set', {'requirements': [{'text': 'x', 'source': 'bad_source'}]})
