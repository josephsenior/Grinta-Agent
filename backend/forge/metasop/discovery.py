"""SOP template discovery utilities and fuzzy name suggestions."""

from __future__ import annotations
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Iterable

SOPS_DIR = Path(__file__).parent / "sops"


@dataclass
class SopTemplateInfo:
    """Lightweight description of an SOP template on disk."""

    name: str
    path: Path
    description: str | None = None
    __test__ = False


def _extract_description(path: Path) -> str | None:
    """Extract first comment line from YAML file as description.

    Reads the YAML file and extracts the first non-empty line that starts with '#'
    as the SOP template description. Useful for generating helpful SOP listings.

    Args:
        path: Path to YAML SOP template file

    Returns:
        str | None: Description text from first comment, or None if:
            - File cannot be read
            - No comment lines exist before first YAML key
            - First comment is empty after stripping '#' symbols

    Example:
        >>> desc = _extract_description(Path("sops/code_generation.yaml"))
        >>> desc
        "Generate production code with comprehensive docstrings"

    Note:
        Only the first comment block is extracted. Stops reading at first
        non-comment, non-empty line containing ':' (YAML key-value).

    """
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
    """List all available SOP templates in the sops directory.

    Discovers all YAML files in the standard SOPS_DIR and creates SopTemplateInfo
    objects for each, including descriptions extracted from file comments.

    Returns:
        list[SopTemplateInfo]: Sorted list of available SOP templates. Empty list
            if SOPS_DIR doesn't exist.

    Side Effects:
        - Reads file system (SOPS_DIR)
        - Extracts descriptions from each YAML file

    Example:
        >>> templates = list_sop_templates()
        >>> len(templates) > 0
        True
        >>> templates[0].name
        "code_generation"

    Note:
        Returns templates sorted by filename in alphabetical order.
        File read errors are silently handled (templates still included without description).

    """
    templates: list[SopTemplateInfo] = []
    if not SOPS_DIR.exists():
        return templates
    for f in sorted(SOPS_DIR.glob("*.yaml")):
        name = f.stem
        desc = _extract_description(f)
        templates.append(SopTemplateInfo(name=name, path=f, description=desc))
    return templates


def suggest_similar(name: str, candidates: Iterable[str], limit: int = 3) -> list[str]:
    """Return up to `limit` closest names using normalized Levenshtein distance.

    Implements fuzzy matching for SOP template name suggestions. Useful for
    providing helpful recommendations when a user requests a non-existent SOP.

    Algorithm:
        - Computes normalized Levenshtein distance for each candidate
        - Normalization: distance / max(len(query), len(candidate))
        - Filters candidates with normalized distance ≤ 0.45
        - Returns up to `limit` closest matches, sorted by distance

    Args:
        name: Query SOP name to match against
        candidates: Iterable of candidate names to compare
        limit: Maximum number of suggestions to return (default: 3)

    Returns:
        list[str]: Up to `limit` closest matching names, sorted by similarity.
            Empty list if no candidates meet the threshold.

    Example:
        >>> suggest_similar("code_gen", ["code_generation", "testing", "planning"])
        ["code_generation"]

    Note:
        - Comparison is case-insensitive
        - Distance threshold of 0.45 allows ~45% character differences
        - Uses inline Levenshtein implementation to avoid dependencies

    """
    name = name.lower().strip()
    scored = []

    def lev(a: str, b: str) -> int:
        """Compute Levenshtein distance between two lower-cased strings."""
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
        """Create an error message showing available templates and closest matches."""
        base = f"SOP template '{name}' not found."
        msg_parts = [base]
        if available:
            msg_parts.append(f"Available: {', '.join(sorted(available))}.")
        if suggestions:
            msg_parts.append(f"Did you mean: {', '.join(suggestions)}?")
        super().__init__(" ".join(msg_parts))
