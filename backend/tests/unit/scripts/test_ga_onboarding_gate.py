"""Unit tests for ga_onboarding_gate script."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

from backend.scripts.verify.ga_onboarding_gate import (
    _collect_reports,
    _count_ci_smoke,
    _count_interactive,
    _format_status_table,
    _gate_ready,
    _parse_report,
    _print_summary,
    main,
)


def test_parse_report_reads_evidence_type(tmp_path: Path) -> None:
    report = tmp_path / '2026-07-08_source_windows_1.md'
    report.write_text(
        '# report\n\n| Evidence type | interactive-fresh-machine |\n',
        encoding='utf-8',
    )
    parsed = _parse_report(report)
    assert parsed is not None
    assert parsed.path == 'source'
    assert parsed.os == 'windows'
    assert parsed.evidence == 'interactive-fresh-machine'


def test_gate_not_ready_without_interactive_reports(tmp_path: Path) -> None:
    report = tmp_path / '2026-07-08_source_windows_2.md'
    report.write_text(
        '# report\n\n| Evidence type | ci-smoke-only |\n',
        encoding='utf-8',
    )
    reports = _collect_reports(tmp_path)
    interactive = _count_interactive(reports)
    ci_smoke = _count_ci_smoke(reports)
    assert interactive[('source', 'windows')] == 0
    assert ci_smoke[('source', 'windows')] == 1
    assert not _gate_ready(interactive)


def test_format_status_table_gate_ready_and_not_ready() -> None:
    interactive_ready = {
        ('pipx', 'linux'): 3,
        ('pipx', 'windows'): 3,
        ('source', 'linux'): 3,
        ('source', 'windows'): 3,
    }
    table_ready = _format_status_table(interactive_ready, {})
    assert 'Interactive evidence target met' in table_ready

    interactive_not_ready = {
        ('pipx', 'linux'): 1,
    }
    table_not_ready = _format_status_table(interactive_not_ready, {})
    assert 'Interactive evidence target not met' in table_not_ready


def test_print_summary(capsys) -> None:
    interactive = {('pipx', 'linux'): 3}
    ci_smoke = {('pipx', 'linux'): 1}
    _print_summary(interactive, ci_smoke)
    captured = capsys.readouterr().out
    assert 'Onboarding evidence summary' in captured
    assert 'pipx   linux' in captured


def test_main_cli_arg_handling(tmp_path: Path) -> None:
    with (
        patch(
            'backend.scripts.verify.ga_onboarding_gate._repo_root',
            return_value=tmp_path,
        ),
        patch(
            'backend.scripts.verify.ga_onboarding_gate._collect_reports',
            return_value=[],
        ),
    ):
        # Without --update-status, returns 1 if not ready
        exit_code = main([])
        assert exit_code == 1

        # With --update-status, writes GA_GATE_STATUS.md and returns 0
        reports_dir = tmp_path / 'docs' / 'onboarding_reports'
        reports_dir.mkdir(parents=True)
        exit_code_update = main(['--update-status'])
        assert exit_code_update == 0
        assert (reports_dir / 'GA_GATE_STATUS.md').exists()
