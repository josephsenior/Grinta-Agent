"""Fallback utilities for cross-platform runtime."""

from backend.runtime.utils.fallbacks.file_ops import PythonFileOps
from backend.runtime.utils.fallbacks.search import PythonSearcher

__all__ = ["PythonFileOps", "PythonSearcher"]
