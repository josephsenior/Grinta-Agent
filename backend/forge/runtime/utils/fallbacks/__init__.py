"""Fallback utilities for cross-platform runtime."""

from forge.runtime.utils.fallbacks.file_ops import PythonFileOps
from forge.runtime.utils.fallbacks.search import PythonSearcher

__all__ = ["PythonFileOps", "PythonSearcher"]
