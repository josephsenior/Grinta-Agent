"""Tests for the `forge.linter` import wrapper."""

from __future__ import annotations

import pytest

from forge.linter import DefaultLinter, LintError, LintResult


def test_module_exports() -> None:
    """Test that the module exports the expected classes."""
    import forge.linter as linter_module

    assert hasattr(linter_module, "DefaultLinter")
    assert hasattr(linter_module, "LintResult")
    assert hasattr(linter_module, "LintError")
    assert set(linter_module.__all__) == {"DefaultLinter", "LintResult", "LintError"}


def test_lint_error_creation() -> None:
    """Test that LintError can be created with proper attributes."""
    error = LintError(
        line=10,
        column=5,
        message="Test error",
        code="E001",
        severity="error",
    )
    assert error.line == 10
    assert error.column == 5
    assert error.message == "Test error"
    assert error.code == "E001"
    assert error.severity == "error"


def test_lint_result_separation() -> None:
    """Test that LintResult properly separates errors and warnings."""
    error = LintError(line=1, column=1, message="Error", severity="error")
    warning = LintError(line=2, column=1, message="Warning", severity="warning")

    result = LintResult(errors=[error], warnings=[warning])
    assert len(result.errors) == 1
    assert len(result.warnings) == 1
    assert result.errors[0].severity == "error"
    assert result.warnings[0].severity == "warning"
