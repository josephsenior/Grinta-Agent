from __future__ import annotations

import argparse
import subprocess
from pathlib import Path
from types import SimpleNamespace

from evaluation.deepswe.run_grinta import (
    _capture_patch,
    _extract_metrics,
    _load_instruction,
    _parser,
    _validate_subscription_model,
)


def _git(repo: Path, *args: str) -> None:
    subprocess.run(['git', *args], cwd=repo, check=True, capture_output=True)


def test_capture_patch_includes_tracked_untracked_and_committed_changes(
    tmp_path: Path,
) -> None:
    repo = tmp_path / 'repo'
    repo.mkdir()
    _git(repo, 'init')
    _git(repo, 'config', 'user.email', 'benchmark@example.invalid')
    _git(repo, 'config', 'user.name', 'Benchmark Test')
    tracked = repo / 'tracked.txt'
    tracked.write_text('before\n', encoding='utf-8')
    _git(repo, 'add', 'tracked.txt')
    _git(repo, 'commit', '-m', 'baseline')
    baseline = subprocess.run(
        ['git', 'rev-parse', 'HEAD'],
        cwd=repo,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()

    tracked.write_text('after\n', encoding='utf-8')
    _git(repo, 'add', 'tracked.txt')
    _git(repo, 'commit', '-m', 'agent commit')
    (repo / 'untracked.txt').write_text('new\n', encoding='utf-8')
    patch = _capture_patch(repo, baseline)

    assert 'tracked.txt' in patch
    assert 'untracked.txt' in patch
    assert '+after' in patch
    assert '+new' in patch
    assert subprocess.run(
        ['git', 'status', '--short'],
        cwd=repo,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.splitlines() == ['?? untracked.txt']


def test_extract_metrics_does_not_infer_a_verdict() -> None:
    combined = SimpleNamespace(accumulated_cost=1.25)
    state = SimpleNamespace(
        agent_state='finished',
        iteration_flag=SimpleNamespace(current_value=12),
        conversation_stats=SimpleNamespace(
            get_combined_metrics=lambda: combined,
        ),
    )

    assert _extract_metrics(state) == {
        'agent_state': 'finished',
        'turn_count': 12,
        'cost_usd': 1.25,
    }


def test_load_instruction_rejects_blank_text() -> None:
    args = argparse.Namespace(instruction_file=None, instruction='  ')

    try:
        _load_instruction(args)
    except ValueError as exc:
        assert str(exc) == 'task instruction must not be empty'
    else:
        raise AssertionError('blank instruction was accepted')


def test_protocol_defaults_freeze_sol_xhigh() -> None:
    parser = _parser()
    args = parser.parse_args(
        [
            '--workspace',
            'repo',
            '--instruction',
            'fix it',
            '--task-id',
            'task',
            '--grinta-commit',
            'a' * 40,
            '--output-dir',
            'out',
        ]
    )

    assert args.model == 'codex/gpt-5.6-sol'
    assert args.reasoning_effort == 'xhigh'


def test_subscription_protocol_rejects_usage_billed_provider() -> None:
    _validate_subscription_model('codex/gpt-5.6-sol')

    try:
        _validate_subscription_model('openai/gpt-5.6-sol')
    except ValueError as exc:
        assert 'subscription-only' in str(exc)
    else:
        raise AssertionError('usage-billed OpenAI API transport was accepted')
