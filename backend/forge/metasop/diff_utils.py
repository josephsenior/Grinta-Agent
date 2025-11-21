r"""Diff and fingerprint utilities for micro-iteration foundation.

This module provides helpers to compute deterministic fingerprints of
text diffs so repeated no-op or semantically identical iterations can
be detected cheaply.

Design notes:
- Input diff is expected to be a unified diff string (\\n terminated lines).
- We normalise line endings to \\n, strip trailing whitespace, and remove
  hunk index metadata ranges that vary with context length.
- Lines starting with '+++' / '---' (file headers) are retained but
  path prefixes are normalised (strip absolute components) to keep
  fingerprints stable across different workspace roots.
- A short SHA256 hex digest (full 64 chars) is returned for collision resistance.
"""

from __future__ import annotations

import hashlib
import re

_HEADER_RE = re.compile("^(\\+\\+\\+|---)\\s+(?:a/|b/)?(.+)$")
_HUNK_RE = re.compile("^@@\\s+-(\\d+),(\\d+)\\s+\\+(\\d+),(\\d+)\\s+@@")


def _normalise_diff(diff_text: str) -> str:
    lines = diff_text.replace("\r\n", "\n").replace("\r", "\n").split("\n")
    out: list[str] = []
    for line in lines:
        if _HUNK_RE.match(line):
            out.append("@@ RANGE @@")
            continue
        if m := _HEADER_RE.match(line):
            kind, path = m.groups()
            path = path.strip().split("/")[-1]
            out.append(f"{kind} {path}")
            continue
        out.append(line.rstrip())
    while out and out[0] == "":
        out.pop(0)
    while out and out[-1] == "":
        out.pop()
    return "\n".join(out) + "\n"


def compute_diff_fingerprint(unified_diff: str) -> str:
    """Return a stable SHA256 hex digest of a unified diff.

    Empty diffs produce the hash of an empty normalised string.
    """
    norm = _normalise_diff(unified_diff or "")
    return hashlib.sha256(norm.encode("utf-8")).hexdigest()


__all__ = ["compute_diff_fingerprint"]
