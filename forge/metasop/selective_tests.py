"""Selective test discovery & narrowing utilities.

Strategy (initial minimal implementation):

Modes:
  imports  - Given a set of changed source files, find test files that import those modules.
  changed  - Directly map changed test files (if any) + tests whose filename matches changed source stem.
  hybrid   - Union of imports + changed (deduped).

Future extensions (placeholders):
  - coverage map based selection
  - historical failure weighting

Inputs expected by selector:
  changed_paths: list[str] of paths relative to repo root (may include non-Python files)
  repo_root: absolute path to repository root

Output: list[str] of test file paths (relative to repo root) to pass to pytest. If empty, caller should fall back to full test run.

Performance considerations:
  - We avoid importing modules; we only parse test files' AST to extract import statements.
  - We short-circuit if changed_paths is large (> threshold) to avoid O(N*M) scanning; in that case we return [] -> full run.
"""

from __future__ import annotations

import ast
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Iterable

MAX_CHANGED_FOR_IMPORT_SCAN = 150
TEST_FILE_GLOB = "tests"
PYTEST_FILE_PREFIX = "test_"
PYTEST_FILE_SUFFIX = "_test"


def _module_name_from_path(path: Path, repo_root: Path) -> str | None:
    try:
        rel = path.relative_to(repo_root)
    except Exception:
        return None
    if rel.suffix != ".py":
        return None
    parts = list(rel.parts)
    if not parts:
        return None
    parts[-1] = parts[-1][:-3]
    return ".".join(p for p in parts if p)


def _gather_test_files(repo_root: Path) -> list[Path]:
    tests_dir = repo_root / TEST_FILE_GLOB
    out: list[Path] = []
    if not tests_dir.exists():
        return out
    for p in tests_dir.rglob("*.py"):
        name = p.name
        if name.startswith(PYTEST_FILE_PREFIX) or name.endswith(f"{PYTEST_FILE_SUFFIX}.py"):
            out.append(p)
    return out


def _parse_imported_modules(test_file: Path) -> set[str]:
    try:
        text = test_file.read_text(encoding="utf-8")
    except Exception:
        return set()
    try:
        tree = ast.parse(text)
    except Exception:
        return set()
    modules: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                if alias.name:
                    modules.add(alias.name.split(".")[0])
        elif isinstance(node, ast.ImportFrom) and node.module:
            modules.add(node.module.split(".")[0])
    return modules


def _candidate_modules_from_changed(changed_paths: Iterable[str], repo_root: Path) -> set[str]:
    mods: set[str] = set()
    for rel in changed_paths:
        try:
            p = (repo_root / rel).resolve()
        except Exception:
            continue
        if p.suffix != ".py":
            continue
        try:
            if dotted := _module_name_from_path(p, repo_root):
                if top := dotted.split(".")[0]:
                    mods.add(top)
                    continue
        except Exception:
            pass
        name = p.stem
        if name == "__init__":
            try:
                if parent_mod := p.parent.relative_to(repo_root).parts[-1]:
                    mods.add(parent_mod)
            except Exception:
                pass
        else:
            mods.add(name)
    return mods


def select_tests(
    changed_paths: list[str],
    repo_root: str,
    mode: str = "imports",
    max_tests: int | None = None,
) -> list[str]:
    """Select relevant test files based on changed paths and mode."""
    # Validate inputs
    if not _should_process_changes(changed_paths):
        return []

    # Setup paths and mode
    repo_root_path = Path(repo_root).resolve()
    mode = (mode or "imports").lower()

    # Gather test files
    test_files = _gather_test_files(repo_root_path)
    if not test_files:
        return []

    # Select candidates based on mode
    candidate = _select_candidates_by_mode(changed_paths, repo_root_path, test_files, mode)

    # Convert to relative paths and apply limits
    return _format_and_limit_results(candidate, repo_root_path, max_tests)


def _should_process_changes(changed_paths: list[str]) -> bool:
    """Check if changes should be processed."""
    return bool(changed_paths) and len(changed_paths) <= MAX_CHANGED_FOR_IMPORT_SCAN


def _select_candidates_by_mode(
    changed_paths: list[str],
    repo_root_path: Path,
    test_files: list[Path],
    mode: str,
) -> set[Path]:
    """Select candidate test files based on the specified mode."""
    candidate: set[Path] = set()
    changed_set = set(changed_paths)

    # Import-based selection
    if mode in {"imports", "hybrid"}:
        candidate.update(_select_by_imports(changed_paths, repo_root_path, test_files))

    # Changed file-based selection
    if mode in {"changed", "hybrid"}:
        candidate.update(_select_by_changed_files(changed_set, repo_root_path))

    return candidate


def _select_by_imports(changed_paths: list[str], repo_root_path: Path, test_files: list[Path]) -> set[Path]:
    """Select test files based on import analysis."""
    candidate: set[Path] = set()

    if candidate_mods := _candidate_modules_from_changed(changed_paths, repo_root_path):
        for tf in test_files:
            imported = _parse_imported_modules(tf)
            if imported & candidate_mods:
                candidate.add(tf)

    return candidate


def _select_by_changed_files(changed_set: set[str], repo_root_path: Path) -> set[Path]:
    """Select test files based on changed files."""
    candidate: set[Path] = set()

    for rel in changed_set:
        p = (repo_root_path / rel).resolve()

        # Direct test files
        if _is_direct_test_file(p):
            candidate.add(p)

        # Corresponding test files
        if _is_python_file(p):
            if corresponding_test := _find_corresponding_test_file(p, repo_root_path):
                candidate.add(corresponding_test)

    return candidate


def _is_direct_test_file(path: Path) -> bool:
    """Check if path is a direct test file."""
    return path.name.startswith(PYTEST_FILE_PREFIX) and path.suffix == ".py"


def _is_python_file(path: Path) -> bool:
    """Check if path is a Python file."""
    return path.suffix == ".py"


def _find_corresponding_test_file(python_file: Path, repo_root_path: Path) -> Path | None:
    """Find corresponding test file for a Python file."""
    stem = python_file.stem
    match = repo_root_path / TEST_FILE_GLOB / f"test_{stem}.py"
    return match if match.exists() else None


def _format_and_limit_results(candidate: set[Path], repo_root_path: Path, max_tests: int | None) -> list[str]:
    """Format results as relative paths and apply limits."""
    out = [str(p.relative_to(repo_root_path)).replace("\\", "/") for p in sorted(candidate)]

    if max_tests and len(out) > max_tests:
        out = out[:max_tests]

    return out


__all__ = ["select_tests"]
