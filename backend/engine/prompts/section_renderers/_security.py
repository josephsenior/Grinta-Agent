"""Renderer for the security risk policy block."""

from __future__ import annotations


def _render_security(
    cli_mode: bool = True,
    *,
    enable_web: bool = True,
    enable_docs: bool = True,
    enable_lsp: bool = False,
    enable_terminal: bool = True,
    enable_editor: bool = True,
    autonomy_level: object = 'balanced',
) -> str:
    from backend.core.autonomy import security_risk_required_for_autonomy

    read_only_tools = '`read_file`, `grep`, `glob`, `find_symbols`, `analyze_project_structure`'
    if enable_lsp:
        read_only_tools += ', `lsp`'
    if enable_web:
        read_only_tools += ', `web_search`, `web_fetch`'
    if enable_docs:
        read_only_tools += ', `docs_resolve`, `docs_query`'
    risk_block = (
        '- **LOW**: Safe, read-only actions.\n'
        '  - Viewing/summarizing content, reading project files, simple in-memory calculations.\n'
        '- **MEDIUM**: Project-scoped edits or execution.\n'
        '  - Modify user project files, run project scripts/tests, install project-local packages.\n'
        '- **HIGH**: System-level or untrusted operations.\n'
        '  - Changing system settings, global installs, elevated (`sudo`) commands, deleting critical files, '
        'downloading & executing untrusted code, or sending local secrets/data out.'
    )
    mutation_tools: list[str] = []
    if enable_terminal:
        mutation_tools.append('`terminal`')
    if enable_editor:
        mutation_tools.extend(['`create_file`', '`replace_string`', '`multiedit`'])
    mutation_label = ', '.join(mutation_tools) or 'enabled mutation tools'

    if security_risk_required_for_autonomy(autonomy_level):
        requirement = (
            f'`security_risk` is **required** on every call to {mutation_label}. '
            f'Read-only observation tools ({read_only_tools}) do **not** require it. '
            'Pick one of `LOW` / `MEDIUM` / `HIGH` based on the action you are about to take. '
            'The server may escalate your risk label; it never lowers it. Missing or invalid values '
            'fail the call.'
        )
    else:
        requirement = (
            f'`security_risk` is **optional** in full autonomy on {mutation_label}. '
            f'Read-only observation tools ({read_only_tools}) never need it. '
            'When omitted, the runtime classifies risk server-side. If you provide '
            '`LOW` / `MEDIUM` / `HIGH`, invalid values still fail the call.'
        )
    process_rule = (
        '\n- For servers and log tails, start with `terminal(action=start)` or '
        '`terminal(action=run, is_background=true)`, then use `wait`, `read`, and `kill`; '
        'do not start duplicate sessions.'
        if enable_terminal
        else ''
    )
    return (
        '# 🔐 Security Risk Policy\n'
        f'{requirement}\n\n'
        f'{risk_block}\n\n'
        '**Global Rules**\n'
        '- Always escalate to **HIGH** if sensitive data leaves the environment.'
        f'{process_rule}'
    )
