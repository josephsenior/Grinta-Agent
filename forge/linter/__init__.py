"""Linter module for forge.

Part of this Linter module is adapted from Aider (Apache 2.0 License, [original
code](https://github.com/paul-gauthier/aider/blob/main/aider/linter.py)).
- Please see the [original repository](https://github.com/paul-gauthier/aider) for more information.
- The detailed implementation of the linter can be found at: https://github.com/All-Hands-AI/Forge-aci.
"""

from types import SimpleNamespace
from typing import Any

try:  # pragma: no cover - exercised when forge_aci is installed
    from forge_aci import linter as forge_linter
except ImportError:  # pragma: no cover - provide lightweight fallback

    class _FallbackLintResult:
        """Stub LintResult for when forge_aci is not installed."""

        def __init__(self, *args: Any, **kwargs: Any) -> None:
            """Initialize empty collections for errors and warnings."""
            self.errors: list[Any] = []
            self.warnings: list[Any] = []

    class _FallbackDefaultLinter:
        """Stub DefaultLinter for when forge_aci is not installed."""

        def __init__(self, *args: Any, **kwargs: Any) -> None:
            """Allow instantiation without performing setup."""

        def lint(self, *args: Any, **kwargs: Any) -> "_FallbackLintResult":
            """Return empty lint result when forge_aci dependency is unavailable."""
            return _FallbackLintResult()

    forge_linter = SimpleNamespace(
        DefaultLinter=_FallbackDefaultLinter,
        LintResult=_FallbackLintResult,
    )

DefaultLinter = forge_linter.DefaultLinter
LintResult = forge_linter.LintResult

__all__ = ["DefaultLinter", "LintResult"]
