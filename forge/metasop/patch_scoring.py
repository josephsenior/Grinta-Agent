"""Patch scoring utilities combining multiple heuristic dimensions.

Dimensions considered (if underlying tool available):
    - Lint issues (ruff) : fewer issues -> higher score
    - Cyclomatic complexity delta (radon) : lower complexity -> higher score
    - Diff size (line count / additions) : smaller -> higher score
    - Content length (total chars) : shorter -> higher score (regularized)

This module is dependency-light: optional imports are guarded so absence
of radon, ruff or diff-match-patch does not crash scoring. Where external
tools are missing we fall back to lightweight approximations.
"""

from __future__ import annotations

import contextlib
import difflib
import hashlib
import json
import os
import subprocess
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Any, Dict, Iterable, List, TypedDict, cast

from forge.structural import available as structural_available
from forge.structural import semantic_diff_counts

try:
    import diff_match_patch as dmp_module  # type: ignore[import-untyped]
except Exception:  # pragma: no cover - optional dependency
    dmp_module = None  # type: ignore[assignment]
try:
    from radon.complexity import cc_visit  # type: ignore[import-untyped]
except Exception:  # pragma: no cover - optional dependency
    cc_visit = None


Numeric = float | int


class DiffMetrics(TypedDict):
    """Typed mapping describing diff statistics."""

    lines: int
    added: int
    removed: int
    char_added: int
    char_removed: int
    hunks: int
    max_hunk_chars: int
    ratio: float
    fingerprint: str


class ComplexityMetrics(TypedDict, total=False):
    """Typed mapping describing complexity stats."""

    complexity: float
    base_complexity: float
    complexity_delta: float


SemanticDelta = dict[str, Numeric]
CandidateMetrics = dict[str, Numeric | str | SemanticDelta]


@dataclass
class PatchCandidate:
    """Patch content/diff pairing along with metadata used for scoring."""

    content: str
    diff: str
    meta: dict[str, Any]
    __test__ = False


@dataclass
class PatchScore:
    """Final scoring output capturing composite score and feature breakdown."""

    composite: float
    features: dict[str, float]
    raw: dict[str, float]
    __test__ = False


def _safe_mean(values):
    """Compute mean of numeric values, filtering non-numeric entries.

    Args:
        values: Iterable of values, may contain non-numeric types

    Returns:
        float: Mean of numeric (int, float) values, or 0.0 if no numeric values found

    Side Effects:
        None - Pure function

    Notes:
        - Skips None, strings, and other non-numeric types
        - Returns 0.0 for empty or all-non-numeric input
        - Used for aggregating complexity metrics across code blocks

    Example:
        >>> _safe_mean([1, 2, 3, "four", None])
        2.0
        >>> _safe_mean([])
        0.0

    """
    vals = [v for v in values if isinstance(v, (int, float))]
    return sum(vals) / len(vals) if vals else 0.0


@lru_cache(maxsize=512)
def _complexity_score(source: str) -> float:
    """Compute cyclomatic complexity score for Python source code.

    Uses radon library to analyze code blocks and compute complexity metrics.
    Results are LRU cached to avoid redundant analysis of identical source.

    Args:
        source: Python source code to analyze

    Returns:
        float: Mean cyclomatic complexity of code blocks, or 0.0 if analysis fails

    Side Effects:
        None - Results cached via lru_cache decorator

    Raises:
        Never - All exceptions caught and 0.0 returned

    Notes:
        - Skips analysis if source > 200KB (too large to analyze)
        - Aborts if analysis takes > 2 seconds (performance safety)
        - Returns 0.0 if radon unavailable or no code blocks found
        - Used in patch scoring to penalize overly complex changes

    Example:
        >>> score = _complexity_score("def hello(): return 42")
        >>> isinstance(score, float)
        True

    """
    if not cc_visit:
        return 0.0
    try:
        if len(source) > 200000:
            return 0.0
        import time as _time

        t0 = _time.time()
        blocks = cc_visit(source)
        if _time.time() - t0 > 2.0:
            return 0.0
        if not blocks:
            return 0.0
        comps = [b.complexity for b in blocks if hasattr(b, "complexity")]
        return _safe_mean(comps)
    except Exception:
        return 0.0


_DISK_CACHE_ENV = os.environ.get("OPH_PATCH_SCORING_CACHE")
try:
    _DISK_CACHE_PATH: Path | None = Path(_DISK_CACHE_ENV) if _DISK_CACHE_ENV else None
except TypeError:
    _DISK_CACHE_PATH = None
_ON_DISK_ENABLED = _DISK_CACHE_PATH is not None


def _hash_source(s: str) -> str:
    """Compute SHA256 hash of source code for caching and deduplication.

    Args:
        s: Source code string

    Returns:
        str: SHA256 hex digest

    Side Effects:
        None - Pure function

    Raises:
        Never - Handles encoding errors gracefully

    Notes:
        - Used as cache key in disk-based patch scoring cache
        - Deterministic across runs for identical source
        - Falls back to empty string if input is None

    Example:
        >>> h1 = _hash_source("x = 1")
        >>> h2 = _hash_source("x = 1")
        >>> h1 == h2
        True

    """
    try:
        return hashlib.sha256(s.encode("utf-8")).hexdigest()
    except Exception:
        return hashlib.sha256((s or "").encode("utf-8")).hexdigest()


def _disk_get(key: str):
    """Retrieve a cached value from disk-based patch scoring cache.

    Args:
        key: Cache key to retrieve

    Returns:
        Cached value if found, None if cache disabled, key not found, or error occurs

    Side Effects:
        None - Read-only operation

    Raises:
        Never - All exceptions caught silently

    Notes:
        - Cache file path set via OPH_PATCH_SCORING_CACHE environment variable
        - Returns None if caching disabled (OPH_PATCH_SCORING_CACHE not set)
        - Used to avoid re-computing complexity scores for identical source

    Example:
        >>> value = _disk_get("cc:abc123def456")
        >>> if value is not None:
        ...     print(f"Found cached score: {value}")

    """
    if not _ON_DISK_ENABLED or _DISK_CACHE_PATH is None:
        return None
    try:
        if _DISK_CACHE_PATH.exists():
            with _DISK_CACHE_PATH.open(encoding="utf-8") as f:
                store = cast(dict[str, Any], json.load(f) or {})
                return store.get(key)
    except Exception:
        return None


def _disk_set(key: str, value) -> None:
    """Store a value in disk-based patch scoring cache.

    Args:
        key: Cache key to store under
        value: Value to cache (should be JSON-serializable)

    Returns:
        None

    Side Effects:
        - Writes to cache file at path specified by OPH_PATCH_SCORING_CACHE env var
        - Reads entire cache file, updates entry, writes back (atomic)
        - Non-fatal: errors are caught and ignored

    Raises:
        Never - All exceptions suppressed to prevent cache failures from breaking scoring

    Notes:
        - No-op if OPH_PATCH_SCORING_CACHE not set (caching disabled)
        - Preserves existing cache entries (read-update-write pattern)
        - Used to persist complexity scores across process invocations

    Example:
        >>> _disk_set("cc:abc123def456", 2.5)
        >>> # Value now persisted to disk for future retrievals

    """
    if not _ON_DISK_ENABLED or _DISK_CACHE_PATH is None:
        return
    try:
        store: dict[str, Any] = {}
        if _DISK_CACHE_PATH.exists():
            try:
                with _DISK_CACHE_PATH.open(encoding="utf-8") as f:
                    store = cast(dict[str, Any], json.load(f) or {})
            except Exception:
                store = {}
        store[key] = value
        try:
            with _DISK_CACHE_PATH.open("w", encoding="utf-8") as f:
                json.dump(store, f)
        except Exception:
            pass
    except Exception:
        pass


def cached_complexity_score(source: str) -> float:
    """Cached wrapper for radon complexity computations."""
    key = f"cc:{_hash_source(source)}"
    try:
        if _ON_DISK_ENABLED:
            v = _disk_get(key)
            if isinstance(v, (int, float)):
                return v
    except Exception:
        pass
    try:
        v = _complexity_score(source)
    except Exception:
        v = 0.0
    try:
        if _ON_DISK_ENABLED:
            _disk_set(key, v)
    except Exception:
        pass
    return v


def _compute_complexity_pair(
    new_source: str,
    base_source: str | None,
) -> ComplexityMetrics:
    """Return a dict with absolute complexity for new_source and delta vs base_source.

    If radon is unavailable or analysis fails, returns zeros.
    """
    new_c = _complexity_score(new_source)
    base_c = 0.0
    delta = 0.0
    try:
        if base_source and cc_visit:
            base_c = _complexity_score(base_source)
            delta = new_c - base_c
    except Exception:
        base_c = 0.0
        delta = 0.0
    return {"complexity": new_c, "base_complexity": base_c, "complexity_delta": delta}


def _try_local_ruff_fallback(tf_name: str) -> subprocess.CompletedProcess | None:
    """Try to run ruff using local installation as fallback.

    Args:
        tf_name: Name of the temporary file to check.

    Returns:
        subprocess.CompletedProcess or None if failed.

    """
    from pathlib import Path

    repo_root = Path(__file__).resolve().parents[3]
    local_ruff = repo_root / "ruff" / "ruff-main"

    if not local_ruff.exists():
        return None

    cmd2 = [
        "python",
        "-m",
        "ruff",
        "check",
        tf_name,
        "--select",
        "E,F,W",
        "--format",
        "json",
    ]
    try:
        return subprocess.run(cmd2, check=False, capture_output=True, text=True)
    except Exception:
        return None


def _parse_ruff_output(output: str) -> int:
    """Parse ruff JSON output to count issues.

    Args:
        output: The JSON output from ruff.

    Returns:
        int: Number of lint issues found.

    """
    if not output.strip():
        return 0

    try:
        parsed = json.loads(output)
        if isinstance(parsed, list):
            return len(parsed)
    except Exception:
        return 0

    return 0


def _run_lint_check(src_text: str) -> int:
    """Run lint check on source text and return issue count.

    Args:
        src_text: The source code to lint.

    Returns:
        int: Number of lint issues found.

    """
    import tempfile

    try:
        with tempfile.NamedTemporaryFile("w", suffix=".py", delete=True) as tf:
            tf.write(src_text)
            tf.flush()

            # Try primary ruff command
            cmd = ["ruff", "check", tf.name, "--select", "E,F,W", "--format", "json"]
            proc = None

            try:
                proc = subprocess.run(cmd, check=False, capture_output=True, text=True)
            except FileNotFoundError:
                # Try local ruff fallback
                proc = _try_local_ruff_fallback(tf.name)

            if not proc:
                return 0

            return 0 if proc.returncode not in (0, 1) else _parse_ruff_output(proc.stdout)
    except Exception:
        return 0


def _lint_issue_count(source: str) -> int:
    """Try to obtain a lint issue count using installed `ruff` CLI.

    We prefer calling `ruff` via subprocess with JSON output. If ruff is not
    available, return 0 as a conservative (optimistic) default.

    Args:
        source: The source code to analyze.

    Returns:
        int: Number of lint issues found.

    """

    @lru_cache(maxsize=1024)
    def _run_on_source(src_text: str) -> int:
        """Internal cached lint check runner for source code.

        Args:
            src_text: Python source code to lint

        Returns:
            int: Number of lint issues found

        Side Effects:
            Results cached via lru_cache decorator (maxsize=1024)

        Notes:
            - Nested within _lint_issue_count for caching scope
            - Delegates to _run_lint_check for actual linting
            - Prevents duplicate lint analysis of identical code

        Example:
            >>> count = _run_on_source("x = 1")
            >>> isinstance(count, int)
            True

        """
        return _run_lint_check(src_text)

    return _run_on_source(source)


@lru_cache(maxsize=1024)
def cached_lint_issue_count(source: str) -> int:
    """Cached wrapper for lint issue count using LRU + optional disk persistence."""
    key = f"lint:{_hash_source(source)}"
    try:
        if _ON_DISK_ENABLED:
            v = _disk_get(key)
            if isinstance(v, int):
                return v
    except Exception:
        pass
    v = _lint_issue_count(source)
    try:
        if _ON_DISK_ENABLED:
            _disk_set(key, v)
    except Exception:
        pass
    return v


def _process_dmp_diffs(diffs: Iterable[tuple[int, str]]) -> tuple[int, int]:
    """Count additions and deletions from diff-match-patch operation list.

    Args:
        diffs: List of (op, text) tuples where op is 1 (add), -1 (delete), or 0 (equal)

    Returns:
        tuple: (additions, deletions) counts

    Side Effects:
        None - Pure function

    Notes:
        - Only counts diff operations, not full character counts
        - Used to calculate patch size metrics for scoring
        - Part of diff-match-patch output processing pipeline

    Example:
        >>> diffs = [(1, "new"), (0, "same"), (-1, "old")]
        >>> _process_dmp_diffs(diffs)
        (1, 1)

    """
    diffs_list = list(diffs)
    additions = sum(op == 1 for op, _ in diffs_list)
    deletions = sum(op == -1 for op, _ in diffs_list)
    return additions, deletions


def _parse_diff_lines(
    diff_text: str,
    max_lines: int = 200000,
) -> tuple[list[str], list[str], int]:
    """Parse diff text to extract added and removed lines."""
    added_lines = []
    removed_lines = []
    lines = 0

    for i, line in enumerate(diff_text.splitlines()):
        if i > max_lines:
            break
        if line.startswith(("+++", "---")):
            continue
        if line.startswith("+") and (not line.startswith("++")):
            added_lines.append(line[1:])
        elif line.startswith("-") and (not line.startswith("--")):
            removed_lines.append(line[1:])
        lines += 1

    return added_lines, removed_lines, lines


def _calculate_basic_metrics(
    added_lines: list[str],
    removed_lines: list[str],
) -> tuple[int, int, int, int]:
    """Calculate basic line and character metrics."""
    added = len(added_lines)
    removed = len(removed_lines)
    char_added = sum(len(line) for line in added_lines)
    char_removed = sum(len(line) for line in removed_lines)
    return added, removed, char_added, char_removed


def _calculate_dmp_metrics(
    removed_text: str,
    added_text: str,
) -> tuple[int, int, int, int, float]:
    """Calculate metrics using diff-match-patch.

    Args:
        removed_text: Original text
        added_text: Modified text

    Returns:
        Tuple of (hunks, max_hunk_chars, char_added, char_removed, ratio)

    """
    try:
        dmp = dmp_module.diff_match_patch()
        diffs = dmp.diff_main(removed_text, added_text)
        dmp.diff_cleanupSemantic(diffs)

        hunks, max_hunk_chars = _count_dmp_hunks(diffs)
        char_added, char_removed = _count_dmp_chars(diffs)
        ratio = _calculate_dmp_ratio(dmp, diffs, removed_text, added_text)

        return hunks, max_hunk_chars, char_added, char_removed, ratio
    except Exception:
        return 0, 0, 0, 0, difflib.SequenceMatcher(a=removed_text, b=added_text).ratio()


def _count_dmp_hunks(diffs: list[tuple[int, str]]) -> tuple[int, int]:
    """Count hunks and max hunk size from diffs.

    Args:
        diffs: List of diff operations

    Returns:
        Tuple of (hunk_count, max_hunk_chars)

    """
    hunks = 0
    max_hunk_chars = 0
    cur_hunk_chars = 0

    for op, txt in diffs:
        if op == 0:  # Equal operation
            if cur_hunk_chars > 0:
                hunks += 1
                max_hunk_chars = max(max_hunk_chars, cur_hunk_chars)
                cur_hunk_chars = 0
        else:
            cur_hunk_chars += len(txt)

    if cur_hunk_chars > 0:
        hunks += 1
        max_hunk_chars = max(max_hunk_chars, cur_hunk_chars)

    return hunks, max_hunk_chars


def _count_dmp_chars(diffs: list[tuple[int, str]]) -> tuple[int, int]:
    """Count added and removed characters.

    Args:
        diffs: List of diff operations

    Returns:
        Tuple of (char_added, char_removed)

    """
    char_added = sum(len(t) for op, t in diffs if op == 1)
    char_removed = sum(len(t) for op, t in diffs if op == -1)
    return char_added, char_removed


def _calculate_dmp_ratio(dmp: Any, diffs: list[tuple[int, str]], removed_text: str, added_text: str) -> float:
    """Calculate similarity ratio.

    Args:
        dmp: Diff-match-patch instance
        diffs: List of diff operations
        removed_text: Original text
        added_text: Modified text

    Returns:
        Similarity ratio

    """
    if hasattr(dmp, "diff_levenshtein"):
        try:
            distance = float(dmp.diff_levenshtein(diffs))
            normalizer = float(max(len(removed_text), len(added_text), 1))
            ratio = 1.0 - min(distance / normalizer, 1.0)
            return ratio
        except Exception:
            pass
    return difflib.SequenceMatcher(a=removed_text, b=added_text).ratio()


def _calculate_difflib_metrics(
    removed_text: str,
    added_text: str,
) -> tuple[int, int, float]:
    """Calculate metrics using difflib."""
    try:
        sm = difflib.SequenceMatcher(a=removed_text, b=added_text)
        opcodes = sm.get_opcodes()

        hunks = 0
        max_hunk_chars = 0
        cur_hunk_chars = 0

        for tag, i1, i2, j1, j2 in opcodes:
            if tag == "equal":
                if cur_hunk_chars > 0:
                    hunks += 1
                    max_hunk_chars = max(max_hunk_chars, cur_hunk_chars)
                    cur_hunk_chars = 0
            else:
                cur_hunk_chars += max(i2 - i1, j2 - j1)

        if cur_hunk_chars > 0:
            hunks += 1
            max_hunk_chars = max(max_hunk_chars, cur_hunk_chars)

        ratio = sm.ratio()
        return hunks, max_hunk_chars, ratio
    except Exception:
        return 0, 0, difflib.SequenceMatcher(a=removed_text, b=added_text).ratio()


def _calculate_advanced_metrics(
    removed_text: str,
    added_text: str,
) -> tuple[int, int, int, int, float]:
    """Calculate advanced metrics using available diff libraries."""
    if dmp_module:
        hunks, max_hunk_chars, char_added, char_removed, ratio = _calculate_dmp_metrics(
            removed_text,
            added_text,
        )
    else:
        hunks, max_hunk_chars, ratio = _calculate_difflib_metrics(
            removed_text,
            added_text,
        )
        char_added = len(added_text)
        char_removed = len(removed_text)

    return hunks, max_hunk_chars, char_added, char_removed, ratio


def _calculate_fingerprint(diff_text: str) -> str:
    """Calculate fingerprint for the diff text."""
    try:
        return hashlib.sha256(diff_text.encode("utf-8")).hexdigest()[:16]
    except Exception:
        return ""


def _diff_size_metrics(diff_text: str) -> DiffMetrics:
    """Return rich diff metrics.

    Metrics returned:
      - lines: total non-header diff lines parsed
      - added: number of added lines
      - removed: number of removed lines
      - char_added: total added characters
      - char_removed: total removed characters
      - hunks: estimated number of contiguous change blocks
      - max_hunk_chars: size (chars) of the largest hunk
      - ratio: similarity ratio between removed and added content (0..1)
      - fingerprint: short hex fingerprint of the diff_text

    We use diff-match-patch for char-level diffing when available and fall
    back to difflib/line heuristics otherwise.
    """
    if not diff_text:
        return {
            "lines": 0,
            "added": 0,
            "removed": 0,
            "char_added": 0,
            "char_removed": 0,
            "hunks": 0,
            "max_hunk_chars": 0,
            "ratio": 1.0,
            "fingerprint": "",
        }

    # Parse diff lines
    added_lines, removed_lines, lines = _parse_diff_lines(diff_text)

    # Calculate basic metrics
    added, removed, char_added, char_removed = _calculate_basic_metrics(
        added_lines,
        removed_lines,
    )

    # Prepare texts for advanced analysis
    added_text = "\n".join(added_lines)
    removed_text = "\n".join(removed_lines)

    # Calculate advanced metrics
    hunks, max_hunk_chars, char_added, char_removed, ratio = _calculate_advanced_metrics(removed_text, added_text)

    # Calculate fingerprint
    fingerprint = _calculate_fingerprint(diff_text)

    return {
        "lines": lines,
        "added": added,
        "removed": removed,
        "char_added": char_added,
        "char_removed": char_removed,
        "hunks": hunks,
        "max_hunk_chars": max_hunk_chars,
        "ratio": ratio,
        "fingerprint": fingerprint,
    }


def _extract_base_content(candidate: PatchCandidate) -> str | None:
    """Extract base content from candidate metadata."""
    if isinstance(candidate.meta, dict):
        return candidate.meta.get("base_content")
    return None


def _compute_complexity_metrics(
    candidate: PatchCandidate,
    base_src: str | None,
) -> ComplexityMetrics:
    """Compute complexity metrics for a candidate."""
    complexity_info = _compute_complexity_pair(candidate.content, base_src)
    with contextlib.suppress(Exception):
        complexity_info["complexity"] = cached_complexity_score(candidate.content)

    return {
        "complexity": float(complexity_info.get("complexity", 0.0) or 0.0),
        "base_complexity": float(complexity_info.get("base_complexity", 0.0) or 0.0),
        "complexity_delta": float(complexity_info.get("complexity_delta", 0.0) or 0.0),
    }


def _compute_semantic_delta(candidate: PatchCandidate, base_src: str | None) -> SemanticDelta:
    """Compute semantic delta for a candidate."""
    try:
        if structural_available():
            if candidate.content:
                raw_delta = semantic_diff_counts(base_src or "", candidate.content)
                return {k: float(v) for k, v in raw_delta.items()}
    except Exception:
        pass
    return {}


def _build_candidate_metrics(candidate: PatchCandidate) -> CandidateMetrics:
    """Build comprehensive metrics for a candidate."""
    base_src = _extract_base_content(candidate)
    complexity_metrics = _compute_complexity_metrics(candidate, base_src)
    lint_issues = cached_lint_issue_count(candidate.content)
    diff_stats = _diff_size_metrics(candidate.diff)
    semantic_delta = _compute_semantic_delta(candidate, base_src)
    content_len = len(candidate.content)

    return {
        "complexity": complexity_metrics["complexity"],
        "base_complexity": complexity_metrics["base_complexity"],
        "complexity_delta": complexity_metrics["complexity_delta"],
        "lint_issues": lint_issues,
        "diff_added": diff_stats["added"],
        "diff_removed": diff_stats["removed"],
        "diff_lines": diff_stats["lines"],
        "diff_char_added": diff_stats["char_added"],
        "diff_char_removed": diff_stats["char_removed"],
        "diff_hunks": diff_stats["hunks"],
        "diff_max_hunk_chars": diff_stats["max_hunk_chars"],
        "diff_ratio": diff_stats["ratio"],
        "diff_fingerprint": diff_stats["fingerprint"],
        "content_len": content_len,
        "semantic_delta": semantic_delta,
    }


def _normalize_low(values: Iterable[Numeric]) -> list[float]:
    """Normalize values to 0-1 range with lower values being better."""
    vals = list(values)
    mn, mx = min(vals), max(vals)
    if mx == mn:
        return [1.0 for _ in vals]
    return [1 - (v - mn) / (mx - mn) for v in vals]


def _calculate_normalizations(raw_list: list[CandidateMetrics]) -> dict[str, list[float]]:
    """Calculate normalized values for all metrics."""
    complexity_values: list[float] = []
    lint_values: list[float] = []
    diff_values: list[float] = []
    length_values: list[float] = []
    semantic_values: list[float] = []

    for metrics in raw_list:
        complex_val = metrics.get("complexity_delta")
        if not isinstance(complex_val, (int, float)):
            complex_val = metrics.get("complexity")
        complexity_values.append(float(complex_val) if isinstance(complex_val, (int, float)) else 0.0)

        lint_val = metrics.get("lint_issues")
        lint_values.append(float(lint_val) if isinstance(lint_val, (int, float)) else 0.0)

        diff_val = metrics.get("diff_lines")
        diff_values.append(float(diff_val) if isinstance(diff_val, (int, float)) else 0.0)

        length_val = metrics.get("content_len")
        length_values.append(float(length_val) if isinstance(length_val, (int, float)) else 0.0)

        sem_delta = metrics.get("semantic_delta")
        if isinstance(sem_delta, dict):
            total_sem = sum(abs(float(v)) for v in sem_delta.values() if isinstance(v, (int, float)))
        else:
            total_sem = 0.0
        semantic_values.append(total_sem)

    return {
        "complexity": _normalize_low(complexity_values),
        "lint": _normalize_low(lint_values),
        "diffsize": _normalize_low(diff_values),
        "length": _normalize_low(length_values),
        "semantic": _normalize_low(semantic_values),
    }


def _get_scoring_weights(settings: Any) -> tuple[float, float, float, float, float, float]:
    """Get scoring weights from settings with fallback defaults."""
    def _coerce(value: Any) -> float:
        return float(value) if isinstance(value, (int, float)) else 0.0

    w_complexity = _coerce(getattr(settings, "patch_score_weight_complexity", 0.0))
    w_lint = _coerce(getattr(settings, "patch_score_weight_lint", 0.0))
    w_diff = _coerce(getattr(settings, "patch_score_weight_diffsize", 0.0))
    w_len = _coerce(getattr(settings, "patch_score_weight_length", 0.0))
    w_sem = _coerce(getattr(settings, "patch_score_weight_semantic", 0.0))

    total_w = w_complexity + w_lint + w_diff + w_len + w_sem

    if total_w <= 0:
        w_complexity = w_lint = w_diff = w_len = 0.25
        total_w = 1.0

    return w_complexity, w_lint, w_diff, w_len, w_sem, total_w


def _calculate_composite_score(
    norm: dict[str, list[float]],
    weights: tuple[float, float, float, float, float, float],
    index: int,
) -> float:
    """Calculate composite score for a candidate at given index."""
    w_complexity, w_lint, w_diff, w_len, w_sem, total_w = weights

    if total_w <= 0:
        return 0.0

    return (
        norm["complexity"][index] * w_complexity
        + norm["lint"][index] * w_lint
        + norm["diffsize"][index] * w_diff
        + norm["length"][index] * w_len
        + norm["semantic"][index] * w_sem
    ) / total_w


def _create_patch_score(
    norm: dict[str, list[float]],
    raw: dict,
    index: int,
    composite: float,
) -> PatchScore:
    """Create a PatchScore object for a candidate."""
    features = {
        "complexity_norm": round(norm["complexity"][index], 4),
        "lint_norm": round(norm["lint"][index], 4),
        "diffsize_norm": round(norm["diffsize"][index], 4),
        "length_norm": round(norm["length"][index], 4),
        "semantic_norm": round(norm["semantic"][index], 4),
    }

    return PatchScore(composite=round(composite, 4), features=features, raw=raw)


def score_candidates(candidates: list[PatchCandidate], settings: Any) -> list[PatchScore]:
    """Score patch candidates based on various metrics."""
    if not candidates:
        return []

    # Build metrics for all candidates
    raw_list = [_build_candidate_metrics(c) for c in candidates]

    # Calculate normalizations
    norm = _calculate_normalizations(raw_list)

    # Get scoring weights
    weights = _get_scoring_weights(settings)

    # Calculate scores
    out: list[PatchScore] = []
    for i, raw in enumerate(raw_list):
        composite = _calculate_composite_score(norm, weights, i)
        patch_score = _create_patch_score(norm, raw, i, composite)
        out.append(patch_score)

    return out


__all__ = ["PatchCandidate", "PatchScore", "score_candidates"]
