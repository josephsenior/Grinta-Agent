from __future__ import annotations

"SOP template discovery utilities.\n\nProvides functions to enumerate available SOP templates and offer fuzzy suggestions\nwhen a requested template name is not found.\n"
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Iterable

SOPS_DIR = Path(__file__).parent / "sops"


@dataclass
class SopTemplateInfo:
    name: str
    path: Path
    description: str | None = None
    __test__ = False


def _extract_description(path: Path) -> str | None:
    """Return the first non-empty comment line (starting with #) as description."""
    try:
        with path.open("r", encoding="utf-8") as fh:
            for line in fh:
                stripped_line = line.strip()
                if not stripped_line:
                    continue
                if stripped_line.startswith("#"):
                    desc = stripped_line.lstrip("# ").strip()
                    return desc or None
                if ":" in stripped_line:
                    break
    except Exception:
        return None
    return None


def list_sop_templates() -> list[SopTemplateInfo]:
    templates: list[SopTemplateInfo] = []
    if not SOPS_DIR.exists():
        return templates
    for f in sorted(SOPS_DIR.glob("*.yaml")):
        name = f.stem
        desc = _extract_description(f)
        templates.append(SopTemplateInfo(name=name, path=f, description=desc))
    return templates


def suggest_similar(name: str, candidates: Iterable[str], limit: int = 3) -> list[str]:
    """Return up to `limit` closest names using a simple normalized Levenshtein distance.

    We implement a tiny distance function locally to avoid new dependencies.
    """
    name = name.lower().strip()
    scored = []

    def lev(a: str, b: str) -> int:
        if a == b:
            return 0
        if not a:
            return len(b)
        if not b:
            return len(a)
        prev = list(range(len(b) + 1))
        for i, ca in enumerate(a, 1):
            cur = [i]
            for j, cb in enumerate(b, 1):
                cost = 0 if ca == cb else 1
                cur.append(min(prev[j] + 1, cur[j - 1] + 1, prev[j - 1] + cost))
            prev = cur
        return prev[-1]

    for cand in candidates:
        d = lev(name, cand.lower())
        norm = d / max(len(name), len(cand))
        scored.append((norm, cand))
    scored.sort(key=lambda x: x[0])
    filtered = [c for _n, c in scored if _n <= 0.45]
    return filtered[:limit] if filtered else []


class SOPNotFoundError(FileNotFoundError):
    """Raised when a requested SOP template isn't found, with optional suggestions."""

    def __init__(self, name: str, available: list[str], suggestions: list[str]) -> None:
        base = f"SOP template '{name}' not found."
        msg_parts = [base]
        if available:
            msg_parts.append(f"Available: {', '.join(sorted(available))}.")
        if suggestions:
            msg_parts.append(f"Did you mean: {', '.join(suggestions)}?")
        super().__init__(" ".join(msg_parts))
