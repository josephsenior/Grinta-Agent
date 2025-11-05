"""Structural utilities using Tree-sitter.

This module provides a small safe wrapper around py-tree-sitter. If the
bindings are not available, the functions will raise a clear ImportError so
callers can fall back to text-based diffs.
"""

from __future__ import annotations

import ast
import os
import platform
from typing import Any

try:
    from tree_sitter import Language, Parser

    _HAS_TS = True
except Exception:
    _HAS_TS = False


def available() -> bool:
    """Return True if structural utilities are available.

    We provide a pure-Python AST fallback so structural features are
    available even when the compiled tree-sitter language library is
    missing. If a compiled language exists and py-tree-sitter is
    importable, we'll prefer that implementation.
    """
    return True


def _find_lang_lib() -> str | None:
    base = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "third_party"))
    system = platform.system().lower()
    if system == "windows":
        ext = "dll"
    elif system == "darwin":
        ext = "dylib"
    else:
        ext = "so"
    lang_lib = os.path.join(base, f"my-langs.{ext}")
    return lang_lib if os.path.exists(lang_lib) else None


def parse_python_source(source: str) -> Any:
    """Parse Python source into either a Tree-sitter tree or an ast.Module.

    Prefer Tree-sitter when available and when the compiled language
    shared library exists; otherwise fall back to the stdlib `ast` parser.
    """
    if _HAS_TS and (lang_lib := _find_lang_lib()):
        PY = Language(lang_lib, "python")
        p = Parser()
        p.set_language(PY)
        return p.parse(bytes(source, "utf8"))
    return ast.parse(source)


def node_type_counts(tree_or_ast) -> dict[str, int]:
    """Return a histogram of node types for either a tree-sitter tree or an ast.Module."""
    out: dict[str, int] = {}
    if _HAS_TS and hasattr(tree_or_ast, "root_node"):

        def _walk(n) -> None:
            out[n.type] = out.get(n.type, 0) + 1
            for c in n.children:
                _walk(c)

        _walk(tree_or_ast.root_node)
        return out

    def _walk_ast(n) -> None:
        t = type(n).__name__
        out[t] = out.get(t, 0) + 1
        for child in ast.iter_child_nodes(n):
            _walk_ast(child)

    _walk_ast(tree_or_ast)
    return out


def semantic_diff_counts(src_a: str, src_b: str) -> dict[str, int]:
    """Compute a simple AST-node-type delta between two Python sources.

    Uses tree-sitter when available; otherwise falls back to the stdlib
    ast module. Returns a dict of node type -> (count_b - count_a).
    """
    t_a = parse_python_source(src_a)
    t_b = parse_python_source(src_b)
    ca = node_type_counts(t_a)
    cb = node_type_counts(t_b)
    keys = set(ca.keys()) | set(cb.keys())
    return {k: cb.get(k, 0) - ca.get(k, 0) for k in keys}
