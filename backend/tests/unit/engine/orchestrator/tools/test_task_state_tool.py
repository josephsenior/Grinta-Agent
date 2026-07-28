from __future__ import annotations

import pytest

from backend.engine.tools.task_state import create_task_state_tool


def _parameters() -> dict:
    return create_task_state_tool()['function']['parameters']


def _branch(parameters: dict, action: str) -> dict:
    return next(
        branch
        for branch in parameters['oneOf']
        if branch['properties']['action']['const'] == action
    )


@pytest.mark.parametrize(
    ('action', 'fields', 'required'),
    [
        (
            'set',
            {
                'action',
                'expected_revision',
                'objective',
                'requirements',
                'constraints',
                'success_conditions',
                'tasks',
            },
            {'action'},
        ),
        (
            'update_task',
            {'action', 'expected_revision', 'task_id', 'status', 'result'},
            {'action', 'task_id', 'status'},
        ),
        (
            'review',
            {'action', 'expected_revision'},
            {'action'},
        ),
        (
            'audit',
            {'action', 'expected_revision', 'evidence'},
            {'action', 'evidence'},
        ),
    ],
)
def test_task_state_schema_discriminates_action_fields(
    action: str,
    fields: set[str],
    required: set[str],
) -> None:
    branch = _branch(_parameters(), action)

    assert set(branch['properties']) == fields
    assert set(branch['required']) == required
    assert branch['additionalProperties'] is False


def test_set_schema_rejects_fields_owned_by_other_actions() -> None:
    set_branch = _branch(_parameters(), 'set')

    assert {'evidence', 'result', 'status', 'task_id'}.isdisjoint(
        set_branch['properties']
    )
