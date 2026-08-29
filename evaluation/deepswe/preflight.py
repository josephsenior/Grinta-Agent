"""Zero-token readiness checks for the subscription-backed DeepSWE protocol."""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
from dataclasses import asdict, dataclass
from importlib import metadata
from pathlib import Path
from typing import Sequence


@dataclass(frozen=True)
class Check:
    name: str
    ok: bool
    detail: str


def _command(command: Sequence[str], *, timeout: int = 15) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        list(command),
        check=False,
        capture_output=True,
        text=True,
        encoding='utf-8',
        errors='replace',
        timeout=timeout,
    )


def _codex_auth_check() -> Check:
    if shutil.which('codex') is None:
        return Check('codex_chatgpt_auth', False, 'Codex CLI is not installed')
    result = _command(('codex', 'login', 'status'))
    output = f'{result.stdout}\n{result.stderr}'.strip()
    normalized = output.casefold()
    ok = (
        result.returncode == 0
        and 'logged in' in normalized
        and 'not logged in' not in normalized
        and 'chatgpt' in normalized
    )
    if ok:
        # Never expose an auth cache, token, or its contents in benchmark output.
        return Check('codex_chatgpt_auth', True, 'Codex CLI reports an authenticated session')
    return Check(
        'codex_chatgpt_auth',
        False,
        'Codex CLI is not authenticated with ChatGPT; run `codex login` and choose ChatGPT sign-in',
    )


def _pier_check() -> Check:
    try:
        version = metadata.version('datacurve-pier')
    except metadata.PackageNotFoundError:
        version = None
    if version:
        return Check('datacurve_pier', True, f'datacurve-pier {version}')

    if shutil.which('pier') is not None:
        return Check('datacurve_pier', True, 'Pier executable is available')
    if shutil.which('uv') is not None:
        result = _command(('uv', 'tool', 'dir', '--bin'))
        if result.returncode == 0 and result.stdout.strip():
            bin_dir = Path(result.stdout.strip())
            if (bin_dir / 'pier').is_file() or (bin_dir / 'pier.exe').is_file():
                return Check('datacurve_pier', True, 'datacurve-pier uv tool is installed')
    return Check('datacurve_pier', False, 'datacurve-pier is not installed')


def _docker_check() -> Check:
    if shutil.which('docker') is None:
        return Check('docker', False, 'Docker CLI is not installed')
    result = _command(('docker', 'version', '--format', '{{.Server.Version}}'))
    version = result.stdout.strip()
    if result.returncode == 0 and version:
        return Check('docker', True, f'Docker engine {version}')
    return Check('docker', False, 'Docker engine is not running or not accessible')


def _protocol_check(protocol_path: Path) -> Check:
    try:
        data = json.loads(protocol_path.read_text(encoding='utf-8'))
        reported = data['reported_run']
    except (OSError, json.JSONDecodeError, KeyError, TypeError) as exc:
        return Check('subscription_protocol', False, f'Invalid protocol: {exc}')
    model = str(reported.get('model', ''))
    api_billing = reported.get('usage_billed_api')
    auth = reported.get('authentication')
    ok = model.startswith('codex/') and api_billing is False and auth == 'chatgpt_subscription'
    detail = (
        f'{model} via ChatGPT subscription; usage-billed API disabled'
        if ok
        else 'Protocol does not enforce codex/ + ChatGPT subscription + no API billing'
    )
    return Check('subscription_protocol', ok, detail)


def run_checks(protocol_path: Path) -> list[Check]:
    """Run checks without making a model request or consuming plan capacity."""
    return [
        _protocol_check(protocol_path),
        _codex_auth_check(),
        _pier_check(),
        _docker_check(),
    ]


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        '--protocol',
        default=str(Path(__file__).with_name('protocol.json')),
    )
    parser.add_argument('--json', action='store_true', dest='as_json')
    args = parser.parse_args(argv)
    checks = run_checks(Path(args.protocol).resolve())
    if args.as_json:
        print(json.dumps([asdict(check) for check in checks], indent=2))
    else:
        for check in checks:
            marker = 'PASS' if check.ok else 'FAIL'
            print(f'[{marker}] {check.name}: {check.detail}')
        print('\nNo model request was made; no ChatGPT plan capacity was consumed.')
    return 0 if all(check.ok for check in checks) else 1


if __name__ == '__main__':
    raise SystemExit(main())
