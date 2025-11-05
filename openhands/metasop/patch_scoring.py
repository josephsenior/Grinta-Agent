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
from typing import Any

from openhands.structural import available as structural_available
from openhands.structural import semantic_diff_counts

try:
    import diff_match_patch as dmp_module
except Exception:
    dmp_module = None
try:
    from radon.complexity import cc_visit
except Exception:
    cc_visit = None


@dataclass
class PatchCandidate:
    content: str
    diff: str
    meta: dict[str, Any]
    __test__ = False


@dataclass
class PatchScore:
    composite: float
    features: dict[str, float]
    raw: dict[str, float]
    __test__ = False


def _safe_mean(values):
    vals = [v for v in values if isinstance(v, (int, float))]
    return sum(vals) / len(vals) if vals else 0.0


@lru_cache(maxsize=512)
def _complexity_score(source: str) -> float:
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


_DISK_CACHE_PATH = os.environ.get("OPH_PATCH_SCORING_CACHE") or None
_ON_DISK_ENABLED = bool(_DISK_CACHE_PATH)


def _hash_source(s: str) -> str:
    try:
        return hashlib.sha256(s.encode("utf-8")).hexdigest()
    except Exception:
        return hashlib.sha256((s or "").encode("utf-8")).hexdigest()


def _disk_get(key: str):
    if not _ON_DISK_ENABLED:
        return None
    try:
        if os.path.exists(_DISK_CACHE_PATH):
            with open(_DISK_CACHE_PATH, encoding="utf-8") as f:
                store = json.load(f) or {}
                return store.get(key)
    except Exception:
        return None


def _disk_set(key: str, value) -> None:
    if not _ON_DISK_ENABLED:
        return
    try:
        store = {}
        if os.path.exists(_DISK_CACHE_PATH):
            try:
                with open(_DISK_CACHE_PATH, encoding="utf-8") as f:
                    store = json.load(f) or {}
            except Exception:
                store = {}
        store[key] = value
        try:
            with open(_DISK_CACHE_PATH, "w", encoding="utf-8") as f:
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
) -> dict[str, float]:
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


def _process_dmp_diffs(diffs):
    additions = sum(diff[0] == 1 for diff in diffs)
    deletions = sum(diff[0] == -1 for diff in diffs)
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


def _count_dmp_hunks(diffs: list) -> tuple[int, int]:
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


def _count_dmp_chars(diffs: list) -> tuple[int, int]:
    """Count added and removed characters.

    Args:
        diffs: List of diff operations

    Returns:
        Tuple of (char_added, char_removed)
    """
    char_added = sum(len(t) for op, t in diffs if op == 1)
    char_removed = sum(len(t) for op, t in diffs if op == -1)
    return char_added, char_removed


def _calculate_dmp_ratio(dmp, diffs: list, removed_text: str, added_text: str) -> float:
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
        return dmp.diff_levenshtein(diffs)
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


def _diff_size_metrics(diff_text: str) -> dict[str, int]:
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
) -> dict:
    """Compute complexity metrics for a candidate."""
    complexity_info = _compute_complexity_pair(candidate.content, base_src)
    with contextlib.suppress(Exception):
        complexity_info["complexity"] = cached_complexity_score(candidate.content)

    return {
        "complexity": complexity_info.get("complexity", 0.0),
        "base_complexity": complexity_info.get("base_complexity", 0.0),
        "complexity_delta": complexity_info.get("complexity_delta", 0.0),
    }


def _compute_semantic_delta(candidate: PatchCandidate, base_src: str | None) -> dict:
    """Compute semantic delta for a candidate."""
    try:
        if structural_available():
            return semantic_diff_counts(base_src or "", candidate.content) if candidate.content else {}
    except Exception:
        pass
    return {}


def _build_candidate_metrics(candidate: PatchCandidate) -> dict:
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
        "diff_char_added": diff_stats.get("char_added", 0),
        "diff_char_removed": diff_stats.get("char_removed", 0),
        "diff_hunks": diff_stats.get("hunks", 0),
        "diff_max_hunk_chars": diff_stats.get("max_hunk_chars", 0),
        "diff_ratio": diff_stats.get("ratio", 1.0),
        "diff_fingerprint": diff_stats.get("fingerprint", ""),
        "content_len": content_len,
        "semantic_delta": semantic_delta,
    }


def _normalize_low(values):
    """Normalize values to 0-1 range with lower values being better."""
    vals = list(values)
    mn, mx = min(vals), max(vals)
    if mx == mn:
        return [1.0 for _ in vals]
    return [1 - (v - mn) / (mx - mn) for v in vals]


def _calculate_normalizations(raw_list: list[dict]) -> dict[str, list[float]]:
    """Calculate normalized values for all metrics."""
    complexity_values = [
        (r.get("complexity_delta") if r.get("complexity_delta") is not None else r.get("complexity")) for r in raw_list
    ]

    return {
        "complexity": _normalize_low(complexity_values),
        "lint": _normalize_low([r["lint_issues"] for r in raw_list]),
        "diffsize": _normalize_low([r["diff_lines"] for r in raw_list]),
        "length": _normalize_low([r["content_len"] for r in raw_list]),
        "semantic": _normalize_low(
            [sum(abs(v) for v in (r.get("semantic_delta") or {}).values()) for r in raw_list],
        ),
    }


def _get_scoring_weights(settings) -> tuple[float, float, float, float, float, float]:
    """Get scoring weights from settings with fallback defaults."""
    w_complexity = settings.patch_score_weight_complexity or 0.0
    w_lint = settings.patch_score_weight_lint or 0.0
    w_diff = settings.patch_score_weight_diffsize or 0.0
    w_len = settings.patch_score_weight_length or 0.0
    w_sem = getattr(settings, "patch_score_weight_semantic", 0.0) or 0.0

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


def score_candidates(candidates: list[PatchCandidate], settings) -> list[PatchScore]:
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
