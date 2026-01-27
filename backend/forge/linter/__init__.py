"""Production-grade linter module for forge.

Provides advanced code linting with multiple backend support (ruff, pylint)
and proper error formatting. Fully self-contained implementation.
"""

from forge.linter.impl import DefaultLinter, LintError, LintResult

__all__ = ["DefaultLinter", "LintResult", "LintError"]
