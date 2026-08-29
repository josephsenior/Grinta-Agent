"""Narrow compatibility helpers for Pier-hosted DeepSWE trials."""

from __future__ import annotations

import shlex
from pathlib import Path


def normalize_shell_script_lf(path: Path) -> bool:
    """Rewrite CRLF shell-script bytes as LF, returning whether it changed."""
    original = path.read_bytes()
    normalized = original.replace(b'\r\n', b'\n')
    if normalized == original:
        return False
    path.write_bytes(normalized)
    return True


def codex_npm_install_args(version: str) -> str:
    """Return deterministic wrapper + Linux binary npm specs for Codex."""
    wrapper = f'@openai/codex@{version}'
    # The platform binary is an optional alias dependency. npm can omit it
    # after a slow registry fetch, leaving the wrapper unusable at runtime.
    linux_x64 = (
        f'@openai/codex-linux-x64@npm:@openai/codex@{version}-linux-x64'
    )
    return f'{shlex.quote(wrapper)} {shlex.quote(linux_x64)}'
