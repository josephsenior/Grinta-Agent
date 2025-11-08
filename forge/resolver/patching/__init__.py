"""Helpers for parsing and applying patches inside the resolver."""

from .patch import parse_patch
from .apply import apply_diff

__all__ = ["apply_diff", "parse_patch"]
