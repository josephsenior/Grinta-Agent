"""Tests for the `forge.linter` module."""

from __future__ import annotations

import pytest

from forge.linter import DefaultLinter, LintResult


def test_linter_initialization() -> None:
    """Test that DefaultLinter can be initialized."""
    linter = DefaultLinter()
    assert linter is not None


def test_linter_returns_lint_result() -> None:
    """Test that lint() returns a LintResult."""
    linter = DefaultLinter()
    result = linter.lint()
    assert isinstance(result, LintResult)
    assert hasattr(result, "errors")
    assert hasattr(result, "warnings")
    assert isinstance(result.errors, list)
    assert isinstance(result.warnings, list)


def test_lint_result_has_errors_and_warnings() -> None:
    """Test that LintResult has errors and warnings attributes."""
    result = LintResult(errors=[], warnings=[])
    assert result.errors == []
    assert result.warnings == []
