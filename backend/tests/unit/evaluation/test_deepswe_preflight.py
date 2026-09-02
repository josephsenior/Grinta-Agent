from __future__ import annotations

import json
import subprocess
from pathlib import Path

from evaluation.deepswe import preflight


def test_protocol_check_requires_subscription_transport(tmp_path: Path) -> None:
    path = tmp_path / 'protocol.json'
    path.write_text(
        json.dumps(
            {
                'reported_run': {
                    'model': 'codex/gpt-5.6-sol',
                    'authentication': 'chatgpt_subscription',
                    'usage_billed_api': False,
                }
            }
        ),
        encoding='utf-8',
    )

    assert preflight._protocol_check(path).ok is True

    data = json.loads(path.read_text(encoding='utf-8'))
    data['reported_run']['model'] = 'openai/gpt-5.6-sol'
    path.write_text(json.dumps(data), encoding='utf-8')
    assert preflight._protocol_check(path).ok is False


def test_codex_auth_check_does_not_echo_command_output(monkeypatch) -> None:
    monkeypatch.setattr(preflight.shutil, 'which', lambda _: 'codex')
    monkeypatch.setattr(
        preflight,
        '_command',
        lambda _: subprocess.CompletedProcess(
            args=['codex'],
            returncode=0,
            stdout='Logged in via ChatGPT SECRET',
            stderr='',
        ),
    )

    check = preflight._codex_auth_check()

    assert check.ok is True
    assert 'SECRET' not in check.detail


def test_codex_auth_check_rejects_not_logged_in(monkeypatch) -> None:
    monkeypatch.setattr(preflight.shutil, 'which', lambda _: 'codex')
    monkeypatch.setattr(
        preflight,
        '_command',
        lambda _: subprocess.CompletedProcess(
            args=['codex'], returncode=1, stdout='', stderr='Not logged in'
        ),
    )

    assert preflight._codex_auth_check().ok is False


def test_frozen_subset_and_config_are_subscription_safe() -> None:
    root = Path(__file__).resolve().parents[4]
    subset = json.loads(
        (root / 'evaluation/deepswe/subset_seed0_n20.json').read_text(encoding='utf-8')
    )
    config = json.loads(
        (root / 'evaluation/deepswe/config.json').read_text(encoding='utf-8')
    )
    protocol = json.loads(
        (root / 'evaluation/deepswe/protocol.json').read_text(encoding='utf-8')
    )

    assert len(subset['task_ids']) == 20
    assert len(set(subset['task_ids'])) == 20
    assert subset['selection'] == {
        'method': 'Pier DatasetConfig sampling',
        'sample_seed': 0,
        'n_tasks': 20,
        'source_task_count': 113,
    }
    assert config['llm_provider'] == 'codex'
    assert config['llm_model'] == 'codex/gpt-5.6-sol'
    assert config['llm_reasoning_effort'] == 'xhigh'
    assert config['max_budget_per_task'] is None
    assert protocol['reported_run']['agent_harness'] == 'grinta'
    assert protocol['reported_run']['model_transport'] == (
        'grinta_codex_app_server_client'
    )
