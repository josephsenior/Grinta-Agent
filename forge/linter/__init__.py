"""Linter module for forge.

Part of this Linter module is adapted from Aider (Apache 2.0 License, [original
code](https://github.com/paul-gauthier/aider/blob/main/aider/linter.py)).
- Please see the [original repository](https://github.com/paul-gauthier/aider) for more information.
- The detailed implementation of the linter can be found at: https://github.com/All-Hands-AI/Forge-aci.
"""

try:
    from forge_aci.linter import DefaultLinter, LintResult
    __all__ = ["DefaultLinter", "LintResult"]
except ImportError:
    # forge_aci not installed - provide stub classes for testing
    from typing import Any
    
    class LintResult:
        """Stub LintResult for when forge_aci is not installed."""
        def __init__(self, *args, **kwargs):
            """Initialize empty collections for errors and warnings."""
            self.errors = []
            self.warnings = []
    
    class DefaultLinter:
        """Stub DefaultLinter for when forge_aci is not installed."""
        def __init__(self, *args, **kwargs):
            """Allow instantiation without performing setup."""
        
        def lint(self, *args, **kwargs) -> LintResult:
            """Return empty lint result when forge_aci dependency is unavailable."""
            return LintResult()
    
    __all__ = ["DefaultLinter", "LintResult"]
