"""Heuristics for classifying MetaSOP step failures and offering corrective hints."""

from __future__ import annotations

import re
from typing import Any

BUILD_PATTERNS = [
    "ModuleNotFoundError",
    "ImportError",
    "cannot find module",
    "No module named",
]
RUNTIME_PATTERNS = [
    "Traceback (most recent call last)",
    "TypeError",
    "ValueError",
    "ReferenceError",
    "NameError",
]
DEPENDENCY_PATTERNS = [
    "version conflict",
    "dependency",
    "Could not resolve",
    "npm ERR!",
    "poetry.lock",
]
TEST_FAIL_PATTERNS = ["FAILED", "AssertionError", "expect\\("]
LINT_PATTERNS = ["lint", "eslint", "flake8"]


def _match_any(text: str, patterns) -> bool:
    return any(re.search(p, text, re.IGNORECASE) for p in patterns)


def _classify_validation_error(validation_err: str) -> tuple[str, dict[str, Any]]:
    """Classify validation errors into specific types.

    Args:
        validation_err: The validation error message.

    Returns:
        tuple[str, dict[str, Any]]: Classification type and metadata.

    """
    if validation_err.startswith("JSON parse/repair failed"):
        return ("json_parse", {"error": validation_err})
    if validation_err.startswith("Schema validation failed"):
        return ("schema_validation", {"error": validation_err})
    return ("validation_error", {"error": validation_err})


def _classify_output_patterns(stdout: str, stderr: str) -> tuple[str, dict[str, Any]]:
    """Classify output patterns to determine failure type.

    Args:
        stdout: Standard output content.
        stderr: Standard error content.

    Returns:
        tuple[str, dict[str, Any]]: Classification type and metadata.

    """
    combo = (stdout + "\n" + stderr)[:16000]

    # Test different pattern categories
    pattern_mappings = [
        (TEST_FAIL_PATTERNS, "qa_test_fail"),
        (LINT_PATTERNS, "qa_lint_fail"),
        (BUILD_PATTERNS, "build_error"),
        (DEPENDENCY_PATTERNS, "dependency_error"),
        (RUNTIME_PATTERNS, "runtime_error"),
    ]

    return next(
        (
            (failure_type, {"summary": combo[-4000:]})
            for patterns, failure_type in pattern_mappings
            if _match_any(combo, patterns)
        ),
        (
            "semantic_gap",
            {
                "detail": "Output failed without clear structural/build/test signature",
            },
        ),
    )


def classify_failure(
    step_id: str,
    role: str,
    stderr: str = "",
    stdout: str = "",
    validation_err: str | None = None,
    retries_exhausted: bool = False,
    budget_exceeded: bool = False,
) -> tuple[str, dict[str, Any]]:
    """Classify a failure into a specific type with metadata.

    Args:
        step_id: The step identifier.
        role: The role that failed.
        stderr: Standard error output.
        stdout: Standard output.
        validation_err: Validation error message if any.
        retries_exhausted: Whether retries were exhausted.
        budget_exceeded: Whether budget was exceeded.

    Returns:
        tuple[str, dict[str, Any]]: Failure type and metadata.

    """
    # Check budget and retry conditions first
    if budget_exceeded:
        return ("budget_exceeded", {"detail": "Hard token budget exceeded"})
    if retries_exhausted:
        return ("retries_exhausted", {"detail": "Maximum retries reached"})

    # Check validation errors
    if validation_err:
        return _classify_validation_error(validation_err)

    # Classify based on output patterns
    return _classify_output_patterns(stdout, stderr)


def corrective_hint(failure_type: str) -> str | None:
    """Return human-friendly remediation hint for known failure types."""
    hints = {
        "json_parse": "Ensure you output STRICT JSON. Remove commentary and markdown fences.",
        "schema_validation": "Re-check required keys and types; fill arrays/objects even if empty.",
        "qa_test_fail": "Analyze failing assertion trace; propose minimal code diff to satisfy expected behavior.",
        "qa_lint_fail": "Run lint locally (eslint/flake8) and fix style errors before re-running.",
        "build_error": "Resolve import/module errors (missing file, wrong path, dependency not installed).",
        "dependency_error": "Adjust dependency spec or install version compatible with existing lockfile.",
        "runtime_error": "Inspect stack trace variable values; guard against None/undefined and type mismatches.",
        "semantic_gap": "Clarify ambiguous requirement—ensure acceptance criteria fully addressed.",
        "retries_exhausted": "Stop repeating same structure—rewrite response from scratch guided by schema.",
        "budget_exceeded": "Reduce verbosity; consolidate sections; avoid repeating unchanged code.",
    }
    base = hints.get(failure_type, "Address the underlying issue and retry.")
    return base
