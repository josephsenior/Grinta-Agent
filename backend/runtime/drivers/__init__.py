"""Runtime implementations for Forge.

This package exposes implementation classes lazily to avoid importing heavy
dependencies (like Docker) unless they are actually used.

Non-local runtime implementations (Docker/Remote/Kubernetes) were removed
from this branch; the package now lazily exposes `LocalRuntime` only.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:  # Only for static typing
    from backend.runtime.drivers.local.local_runtime_inprocess import LocalRuntime as LocalRuntime


__all__ = ["LocalRuntime"]

def __getattr__(name: str):
    if name == "LocalRuntime":
        from importlib import import_module

        return getattr(import_module("backend.runtime.drivers.local.local_runtime_inprocess"), "LocalRuntime")
    raise AttributeError(name)
