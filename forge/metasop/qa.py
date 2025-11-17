"""QA command detection and coverage utilities for MetaSOP workflows."""

from __future__ import annotations

import contextlib
import hashlib
import json
import os
import shutil
import subprocess
import tempfile
from pathlib import Path
from typing import Any

from .models import Artifact

BASE_STATE_DIR = Path.home() / ".Forge" / "metasop_state"
BASE_STATE_DIR.mkdir(parents=True, exist_ok=True)
_LAST_COVERAGE_FILE = BASE_STATE_DIR / "last_coverage.json"


def _hash_path_list(paths: list[str]) -> str:
    m = hashlib.sha256()
    for p in sorted(paths):
        m.update(p.encode())
    return m.hexdigest()


def _maybe_read_json(path: Path) -> dict[str, Any] | None:
    try:
        if path.exists():
            return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None
    return None


def _detect_commands(repo_root: str | None) -> list[list[str]]:
    """Detect available test and lint commands in the repository.

    Args:
        repo_root: Repository root directory

    Returns:
        List of command arrays

    """
    root = repo_root or os.getcwd()
    cmds: list[list[str]] = []

    _detect_pytest_commands(root, cmds)
    _detect_npm_commands(root, cmds)

    # Fallback to pytest if no commands detected
    if not cmds and shutil.which("pytest"):
        cmds.append(["pytest", "-q"])

    return cmds


def _detect_pytest_commands(root: str, cmds: list[list[str]]) -> None:
    """Detect pytest commands based on project files.

    Args:
        root: Repository root
        cmds: List to append commands to

    """
    if shutil.which("pytest"):
        has_config = os.path.exists(
            os.path.join(root, "pyproject.toml")
        ) or os.path.exists(
            os.path.join(root, "pytest.ini"),
        )
        if has_config:
            cmds.append(["pytest", "-q"])


def _detect_npm_commands(root: str, cmds: list[list[str]]) -> None:
    """Detect npm test/lint commands from package.json.

    Args:
        root: Repository root
        cmds: List to append commands to

    """
    pkg_path = os.path.join(root, "package.json")
    if not os.path.exists(pkg_path):
        return

    try:
        with open(pkg_path, encoding="utf-8") as f:
            pkg_json = json.load(f)

        scripts = pkg_json.get("scripts", {})
        if "test" in scripts:
            cmds.append(["npm", "run", "-s", "test"])
        if "lint" in scripts:
            cmds.append(["npm", "run", "-s", "lint"])
    except Exception:
        pass


def _run_cmd(cmd: list[str], repo_root: str | None) -> dict[str, Any]:
    res = subprocess.run(
        cmd, check=False, cwd=repo_root or None, capture_output=True, text=True
    )
    return {
        "cmd": cmd,
        "returncode": res.returncode,
        "stdout": res.stdout[-12000:],
        "stderr": res.stderr[-12000:],
    }


def _run_detected_commands(repo_root: str | None) -> tuple[list[dict[str, Any]], bool]:
    """Run all detected commands and return results and success status."""
    results: list[dict[str, Any]] = []
    ok = True
    detected = _detect_commands(repo_root)
    for cmd in detected:
        r = _run_cmd(cmd, repo_root)
        results.append(r)
        ok = ok and r["returncode"] == 0
    return (results, ok)


def _run_coverage_analysis(
    repo_root: str | None,
    detected: list[list[str]],
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    """Run coverage analysis if pytest is available."""
    coverage_summary: dict[str, Any] = {}
    results: list[dict[str, Any]] = []

    # Check if pytest is available
    if not _is_pytest_available(detected):
        return (coverage_summary, results)

    try:
        # Run coverage analysis
        tmp_dir = tempfile.mkdtemp(prefix="metasop_cov_")
        cov_res = _execute_pytest_coverage(repo_root)
        results.append({**cov_res, "purpose": "coverage_run"})

        # Parse coverage results
        coverage_summary = _parse_coverage_results(repo_root, tmp_dir)

    except Exception:
        pass

    return (coverage_summary, results)


def _is_pytest_available(detected: list[list[str]]) -> bool:
    """Check if pytest is available in the detected commands."""
    has_pytest = any("pytest" in c for cmd in detected for c in cmd)
    return has_pytest and shutil.which("pytest") is not None


def _execute_pytest_coverage(repo_root: str | None) -> dict[str, Any]:
    """Execute pytest with coverage analysis."""
    cov_cmd = ["pytest", "--cov", "--cov-report=json", "-q"]
    return _run_cmd(cov_cmd, repo_root)


def _parse_coverage_results(repo_root: str | None, tmp_dir: str) -> dict[str, Any]:
    """Parse coverage results from JSON files."""
    coverage_summary: dict[str, Any] = {}

    # Find coverage file
    cov_path = _find_coverage_file(repo_root, tmp_dir)
    if not cov_path or not cov_path.exists():
        return coverage_summary

    try:
        # Parse coverage data
        raw_cov = json.loads(cov_path.read_text(encoding="utf-8"))
        coverage_summary = _extract_coverage_summary(raw_cov)
    except Exception:
        pass

    return coverage_summary


def _find_coverage_file(repo_root: str | None, tmp_dir: str) -> Path | None:
    """Find the coverage JSON file in candidate locations."""
    candidate_paths = []
    if repo_root:
        candidate_paths.append(Path(repo_root) / "coverage.json")
    candidate_paths.append(Path(tmp_dir) / "coverage.json")

    return next((p for p in candidate_paths if p.exists()), None)


def _extract_coverage_summary(raw_cov: dict[str, Any]) -> dict[str, Any]:
    """Extract coverage summary from raw coverage data."""
    totals = raw_cov.get("totals", {})
    files = raw_cov.get("files", {})

    overall = totals.get("percent_covered") if "percent_covered" in totals else None

    return {
        "overall_percent": overall,
        "files": {k: v.get("summary", {}) for k, v in files.items()},
    }


def _compute_coverage_delta(coverage_summary: dict[str, Any]) -> dict[str, float]:
    """Compute coverage delta from previous run.

    Args:
        coverage_summary: Current coverage summary

    Returns:
        Dictionary mapping file paths to coverage percentage changes

    """
    previous = _maybe_read_json(_LAST_COVERAGE_FILE) or {}

    if not coverage_summary.get("files"):
        return {}

    delta = _calculate_file_deltas(coverage_summary["files"], previous)
    _persist_coverage_summary(coverage_summary)

    return delta


def _calculate_file_deltas(current_files: dict, previous: dict) -> dict[str, float]:
    """Calculate coverage delta for each file.

    Args:
        current_files: Current file coverage data
        previous: Previous coverage data

    Returns:
        Dictionary of file deltas

    """
    prev_files = previous.get("files", {}) if isinstance(previous, dict) else {}
    delta = {}

    for f, summ in current_files.items():
        prev = prev_files.get(f, {})

        new_pct = _extract_coverage_percent(summ)
        old_pct = _extract_coverage_percent(prev)

        if new_pct is not None and old_pct is not None:
            delta[f] = round(new_pct - old_pct, 2)

    return delta


def _extract_coverage_percent(data: dict) -> float | None:
    """Extract coverage percentage from data dict.

    Args:
        data: Coverage data dictionary

    Returns:
        Coverage percentage or None

    """
    return data.get("percent_covered") or data.get("percent_covered_display") or None


def _persist_coverage_summary(coverage_summary: dict[str, Any]) -> None:
    """Persist coverage summary to file.

    Args:
        coverage_summary: Coverage data to persist

    """
    with contextlib.suppress(Exception):
        _LAST_COVERAGE_FILE.write_text(json.dumps(coverage_summary), encoding="utf-8")


def run_pytest(repo_root: str | None) -> Artifact:
    """Execute detected test/lint commands and attempt to gather coverage & deltas.

    Coverage strategy:
      1. If `pytest` command is present and `coverage.json` appears in repo root or `.coverage` present
         attempt `pytest --cov --cov-report=json` in an isolated run.
      2. Persist last run coverage summary to state; compute delta per file & overall.
    """
    results, ok = _run_detected_commands(repo_root)
    detected = _detect_commands(repo_root)
    coverage_summary, coverage_results = _run_coverage_analysis(repo_root, detected)
    results.extend(coverage_results)
    delta = _compute_coverage_delta(coverage_summary)
    passed = 1 if ok else 0
    failed = 0 if ok else 1
    shaped = {
        "ok": ok,
        "tests": {"passed": passed, "failed": failed},
        "lint": {},
        "report": results,
        "coverage": coverage_summary or None,
        "coverage_delta": delta or None,
    }
    return Artifact(step_id="qa_verify", role="QA", content=shaped)


def shape_failure_report(
    events: list[dict], metadata: dict[str, Any]
) -> dict[str, Any]:
    """Normalize QA failure report payload for downstream logging/analytics."""
    return {
        "failures": 1 if "FAILED" in events[0]["stdout"] or events[0]["stderr"] else 0,
        "summary": (events[0]["stdout"] + "\n" + events[0]["stderr"])[-4000:],
    }
