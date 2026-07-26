"""Renderer for the autonomy partial (system_partial_01_autonomy.md).

The ``_build_*`` helpers produce the inner blocks that are interpolated into
the autonomy template; keeping them in this module makes the full
autonomy-section assembly readable in one place.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from backend.engine.prompts.section_renderers._common import _semantic_recall_runtime
from backend.engine.prompts.section_renderers._env_hints import (
    _explore_hint,
    _lsp_available,
    _path_uncertainty_hint,
)


def _build_context_discipline_section(
    *,
    working_memory_on: bool,
    tracker_on: bool,
    criteria_on: bool = True,
    checkpoints_on: bool,
    condensation_on: bool,
    semantic_recall_on: bool = False,
) -> str:
    _ = (working_memory_on, criteria_on)
    parts = ['<CONTEXT_DISCIPLINE>']
    parts.append(
        'Use the visible conversation, current files, and fresh tool observations as context. '
        'After condensation, follow `<SELF_REGULATION>`.'
    )
    if semantic_recall_on:
        parts.extend(
            [
                '',
                '**search_history** — see `<MEMORY_AND_CONTEXT>` to search past turns.',
            ]
        )
    if checkpoints_on:
        parts.append(
            '**checkpoint** — see System Capabilities and `<EDITOR_AND_FILE_OPERATIONS>`.'
        )

    if tracker_on:
        parts.extend(
            [
                '',
                '**task_state** — durable overall objective, contract conditions, and plan; see `<TASK_STATE_POLICY>`.',
            ]
        )
        if condensation_on:
            parts.append(
                'Post-condensation: the live recorded objective, status, contract '
                'conditions, and task ids are in `<EXECUTION_CONTRACT>`; call '
                '`task_state(review)` only when you need the full state.'
            )

    parts.append('</CONTEXT_DISCIPLINE>')
    return '\n'.join(parts)


def _build_risk_preview(
    *,
    enabled: bool,
) -> str:
    if not enabled:
        return ''
    return (
        '<RISK_PREVIEW>\n'
        'Use risk preview only for risky work: multi-file refactors, core runtime changes, concurrency/async changes, lifecycle/tool-schema changes, destructive operations, public API changes, or large generated edits.\n\n'
        'When triggered, state two concrete failure modes in the same assistant turn as the next tool call. After the next major milestone, note whether either occurred and pivot if needed. Intermediate prose may accompany tool calls and does not end the run.\n\n'
        'For small/local edits, skip formal risk preview.\n'
        '</RISK_PREVIEW>'
    )


def _build_autonomy_block(_mode: str) -> str:
    return (
        '<AUTONOMY>\n'
        'For implementation work, drive the request through tools and verification; '
        'for discussion or planning work, keep the response aligned with the active protocol. '
        'Intermediate prose may accompany tool calls for approaches, risk previews, and progress updates. '
        'Plain prose without tool calls ends the run; see the active mode protocol. '
        'If the user changes or contradicts the task mid-run, treat the latest user directive as authoritative. '
        'Preserve completed work that still applies, drop work that no longer applies, and continue from the new instruction. '
        'The runtime may interrupt a tool call to surface a user decision; treat that decision as '
        'authoritative and continue from where you stopped. On failure, follow `<ERROR_RECOVERY_POLICY>`.'
        '\n</AUTONOMY>'
    )


def _render_autonomy(
    render_partial: Callable[..., str],
    config: Any,
    *,
    is_windows: bool,
    windows_with_bash: bool,
    shell_is_powershell: bool,
    semantic_recall_active: bool | None = None,
) -> str:
    from backend.core.interaction_modes import (
        is_chat_mode,
        is_plan_mode,
        normalize_interaction_mode,
    )

    mode = normalize_interaction_mode(getattr(config, 'mode', 'agent'))
    checkpoints_on = bool(getattr(config, 'enable_checkpoints', True))
    working_memory_on = bool(getattr(config, 'enable_working_memory', True))
    condensation_on = bool(getattr(config, 'enable_condensation_request', False))
    tracker_on = bool(getattr(config, 'enable_task_tracker_tool', True))
    criteria_on = bool(getattr(config, 'enable_acceptance_criteria_tool', True))
    semantic_recall_on = _semantic_recall_runtime(
        config, semantic_recall_active=semantic_recall_active
    )

    autonomy_block = _build_autonomy_block(mode)
    context_discipline = _build_context_discipline_section(
        working_memory_on=working_memory_on,
        tracker_on=tracker_on,
        criteria_on=criteria_on,
        checkpoints_on=checkpoints_on,
        condensation_on=condensation_on,
        semantic_recall_on=semantic_recall_on,
    )
    risk_preview = _build_risk_preview(
        enabled=not (is_chat_mode(mode) or is_plan_mode(mode))
    )

    explore = _explore_hint(config)
    path_hint = _path_uncertainty_hint(
        explore,
        is_windows=is_windows,
        windows_with_bash=windows_with_bash,
        shell_is_powershell=shell_is_powershell,
    )
    if not bool(getattr(config, 'enable_terminal', True)):
        path_hint = (
            f'When paths are uncertain, use {explore} and follow `<DISCOVERY_ROUTING>`; '
            'no terminal tool is available.'
        )
    if tracker_on:
        task_state_policy = (
            '<TASK_STATE_POLICY>\n'
            'Use `task_state` for durable multi-step cognition. The contract records '
            'WHAT must remain true: the overall objective, explicit requirements, '
            'constraints, and verifiable success conditions. Tasks record HOW you '
            'currently intend to work and may be replaced when evidence changes.\n'
            'Commands: `set`, `update_task`, `review`, `audit`. For `set`, pass '
            '`objective`, `requirements`, `constraints`, `success_conditions`, and '
            '`tasks` directly as structured top-level arguments—never JSON strings or '
            '`contract`/`plan` wrappers. Lightweight work need not create task state. '
            'Never record an implementation hypothesis as a user requirement; never '
            'silently weaken a user requirement. `task_state` reports evidence for '
            'your judgment; it does not decide whether to finish.\n\n'
            'Create it for substantial multi-step work. Update it when evidence changes '
            'a task or contract condition. After verification, record verification evidence with '
            '`audit`, review the overall objective, and reconcile remaining tasks before '
            'applying `<COMPLETION_CONTRACT>`. Lightweight work does not require task state.\n'
            '</TASK_STATE_POLICY>'
        )
    else:
        task_state_policy = ''

    verification_policy = (
        '<VERIFICATION_POLICY>\n'
        'Before final, run the narrowest relevant proof: the reproducer, affected tests, '
        'lint, typecheck, build, or a focused smoke test.\n'
        '**Done criteria by task type:**\n'
        '- **Bugfix:** capture or reproduce the failure, fix it, then re-run the same narrow proof when possible.\n'
        '- **Implementation:** exercise the changed path and run project-standard lint/typecheck when relevant.\n'
        '- **Refactor:** run affected tests or a narrow smoke check on touched modules.\n'
        '- **Tests and public contracts:** read the implementation being tested in this session and align mocks, fixtures, calls, signatures, and return shapes with the real API.\n'
        '- **Failed tests:** treat tests as executable evidence, not absolute truth. Diagnose implementation defects, stale expectations, fixture/mock mismatch, environment issues, and flakes; never alter tests merely to manufacture a pass.\n'
        '- **Blocked verification:** continue other safe checks. If no meaningful runnable check remains, state the concrete blocker: no harness, missing dependency or credential, an environment that cannot install/build/run, an unsafe or destructive check, or no meaningful runnable check for the task. Never use a vague excuse such as "not applicable."\n'
        '</VERIFICATION_POLICY>'
    )

    completion_contract = (
        '<COMPLETION_CONTRACT>\n'
        '- Reconcile status against the latest explicit user objective. A debugging subproblem or implementation milestone is not a new request boundary.\n'
        '- Complete every required in-scope action; adjacent work is allowed only when required for correctness.\n'
        '- Do not treat a completed task-state item, fix, or implementation milestone as completion of a broader objective.\n'
        '- Verify according to `<VERIFICATION_POLICY>`. If one required check is blocked, continue other safe in-scope work; identify the concrete blocker only after exhausting that work.\n'
        '- Stop at the objective boundary for unrelated style changes, refactors, or investigations; mention them without acting.\n'
        '- Before final, confirm that the objective is answered, no required actionable work remains, verification status is explicit, and durable task state matches reality.\n'
        '- Do not turn unfinished requested work into optional next steps or follow-up suggestions.\n'
        '- Finish with the summary required by the active mode protocol.\n'
        '</COMPLETION_CONTRACT>'
    )

    problem_solving_workflow_body = (
        'Default loop: scope → reproduce → isolate → fix → verify.\n'
        'For debug/fix tasks, re-run the same reproducer when possible.'
    )
    if tracker_on:
        problem_solving_workflow_body += (
            '\n\nFor substantial multi-step work, sync `task_state` after verification '
            'when a milestone or contract condition changed.'
        )

    lsp_avail = _lsp_available(config)
    error_recovery_pivot_lines = (
        '- `grep` / `glob` → `lsp` (check locally with the language server; no shell grep)\n'
        '- `lsp` → `grep` (wider text search)'
        if lsp_avail
        else ''
    )
    editor_error_recovery_lines = ''
    if bool(getattr(config, 'enable_editor', True)):
        editor_error_recovery_lines = (
            '- **Ambiguous edit target:** for ambiguous `replace_string`, re-read nearby '
            'context and make `old_string` unique; use `replace_all=true` only when every '
            'exact occurrence must change.\n'
            '- **Multi-file edit failure:** split the refactor only when atomicity is '
            'unnecessary; otherwise correct the failing `multiedit` operation and retry '
            'the atomic batch.'
        )

    return render_partial(
        'system_partial_01_autonomy.md',
        autonomy_block=autonomy_block,
        context_discipline=context_discipline,
        risk_preview=risk_preview,
        task_state_policy=task_state_policy,
        verification_policy=verification_policy,
        completion_contract=completion_contract,
        path_discovery_hint=path_hint,
        problem_solving_workflow_body=problem_solving_workflow_body,
        error_recovery_pivot_lines=error_recovery_pivot_lines,
        editor_error_recovery_lines=editor_error_recovery_lines,
    )
