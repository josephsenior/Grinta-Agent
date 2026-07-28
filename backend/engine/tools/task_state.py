"""Single model-facing tool for durable contract and plan state."""

from typing import Any

from backend.core.tools.tool_names import TASK_STATE_TOOL_NAME
from backend.engine.contracts import ChatCompletionToolParam
from backend.engine.tools.param_defs import create_tool_definition, get_command_param


def create_task_state_tool() -> ChatCompletionToolParam:
    contract_item: dict[str, Any] = {
        'type': 'object',
        'properties': {
            'id': {'type': 'string'},
            'text': {'type': 'string'},
            'source': {
                'type': 'string',
                'enum': ['user', 'repository', 'system', 'agent'],
            },
            'status': {
                'type': 'string',
                'enum': ['unknown', 'satisfied', 'gap', 'not_applicable'],
            },
        },
        'required': ['text'],
        'additionalProperties': False,
    }
    task: dict[str, Any] = {
        'type': 'object',
        'properties': {
            'id': {'type': 'string'},
            'description': {'type': 'string'},
            'status': {
                'type': 'string',
                'enum': ['todo', 'in_progress', 'done', 'skipped', 'blocked'],
            },
            'result': {'type': 'string'},
        },
        'required': ['id', 'description'],
        'additionalProperties': False,
    }
    evidence: dict[str, Any] = {
        'type': 'object',
        'properties': {
            'item_id': {'type': 'string'},
            'status': {
                'type': 'string',
                'enum': ['unknown', 'satisfied', 'gap', 'not_applicable'],
            },
            'evidence': {'type': 'string'},
            'kind': {'type': 'string'},
        },
        'required': ['item_id', 'status', 'evidence'],
        'additionalProperties': False,
    }
    action = get_command_param(
        'set updates supplied top-level contract/plan fields; update_task '
        'changes one task; review is read-only; audit records contract evidence.',
        ['set', 'update_task', 'review', 'audit'],
    )
    expected_revision = {'type': 'integer'}
    objective = {'type': 'string'}
    requirements = {'type': 'array', 'items': contract_item}
    constraints = {'type': 'array', 'items': contract_item}
    success_conditions = {'type': 'array', 'items': contract_item}
    tasks = {'type': 'array', 'items': task}
    task_id = {'type': 'string'}
    status = {
        'type': 'string',
        'enum': ['todo', 'in_progress', 'done', 'skipped', 'blocked'],
    }
    result = {'type': 'string'}
    evidence_rows = {'type': 'array', 'items': evidence}

    # Keep the root property union as a compatibility fallback for providers that
    # strip schema combinators. Providers that support JSON Schema oneOf get the
    # action-specific field constraints below.
    tool = create_tool_definition(
        name=TASK_STATE_TOOL_NAME,
        description=(
            'Create and maintain durable state for substantial multi-step work. '
            'The contract records the overall user objective and what must remain '
            'true; tasks record the current strategy. For set, pass objective, '
            'requirements, constraints, success_conditions, and tasks directly as '
            'top-level structured arguments. Do not use contract/plan wrappers and '
            'do not JSON-encode fields. Use review to refresh the full state and audit '
            'to attach evidence. This tool reports state; it does not decide whether '
            'you should finish.'
        ),
        properties={
            'action': action,
            'expected_revision': expected_revision,
            'objective': objective,
            'requirements': requirements,
            'constraints': constraints,
            'success_conditions': success_conditions,
            'tasks': tasks,
            'task_id': task_id,
            'status': status,
            'result': result,
            'evidence': evidence_rows,
        },
        required=['action'],
    )
    tool['function']['parameters']['oneOf'] = [
        _action_schema(
            'set',
            {
                'expected_revision': expected_revision,
                'objective': objective,
                'requirements': requirements,
                'constraints': constraints,
                'success_conditions': success_conditions,
                'tasks': tasks,
            },
        ),
        _action_schema(
            'update_task',
            {
                'expected_revision': expected_revision,
                'task_id': task_id,
                'status': status,
                'result': result,
            },
            required=['task_id', 'status'],
        ),
        _action_schema(
            'review',
            {'expected_revision': expected_revision},
        ),
        _action_schema(
            'audit',
            {
                'expected_revision': expected_revision,
                'evidence': evidence_rows,
            },
            required=['evidence'],
        ),
    ]
    return tool


def _action_schema(
    action: str,
    properties: dict[str, Any],
    *,
    required: list[str] | None = None,
) -> dict[str, Any]:
    """Build one action branch for the discriminated task-state schema."""
    return {
        'type': 'object',
        'properties': {
            'action': {'type': 'string', 'const': action},
            **properties,
        },
        'required': ['action', *(required or [])],
        'additionalProperties': False,
    }


__all__ = ['create_task_state_tool']
