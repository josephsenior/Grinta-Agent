"""Narrow compatibility helpers for Pier-hosted DeepSWE trials."""

from __future__ import annotations

from pathlib import Path


def normalize_shell_script_lf(path: Path) -> bool:
    """Rewrite CRLF shell-script bytes as LF, returning whether it changed."""
    original = path.read_bytes()
    normalized = original.replace(b'\r\n', b'\n')
    if normalized == original:
        return False
    path.write_bytes(normalized)
    return True
