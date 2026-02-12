"""Runtime backends and supporting infrastructure for Forge agents.

This module provides the Runtime interface and its implementations. 
In this version, only LocalRuntime (in-process) is supported.
"""

from __future__ import annotations

import importlib
from typing import TYPE_CHECKING, Any

from backend.runtime.base import Runtime
from backend.runtime.orchestrator import (
    RuntimeAcquireResult,
    RuntimeOrchestrator,
    runtime_orchestrator,
)
from backend.runtime.pool import (
    PooledRuntime,
    RuntimePool,
    SingleUseRuntimePool,
    WarmPoolPolicy,
    WarmRuntimePool,
)
from backend.runtime.watchdog import runtime_watchdog
from backend.utils.import_utils import get_impl

if TYPE_CHECKING:  # Only for static type checking
    from backend.runtime.drivers.local.local_runtime_inprocess import LocalRuntime


def _lazy_import(module_path: str, attr: str) -> Any:
    module = importlib.import_module(module_path)
    return getattr(module, attr)


# Map runtime keys to (module, attribute) for lazy loading
_DEFAULT_RUNTIME_IMPORTS: dict[str, tuple[str, str]] = {
    "local": ("backend.runtime.drivers.local.local_runtime_inprocess", "LocalRuntime"),
}

_ALL_RUNTIME_KEYS = set(_DEFAULT_RUNTIME_IMPORTS.keys())


def get_runtime_cls(name: str) -> type[Runtime]:
    """If name is one of the predefined runtime names (e.g. 'local'), return its class.

    Otherwise attempt to resolve name as subclass of Runtime and return it.
    Raise on invalid selections.
    """
    # Built-in lazy imports
    if name in _DEFAULT_RUNTIME_IMPORTS:
        module_path, attr = _DEFAULT_RUNTIME_IMPORTS[name]
        return _lazy_import(module_path, attr)
    try:
        return get_impl(Runtime, name)
    except Exception as e:
        known_keys = _ALL_RUNTIME_KEYS
        msg = f"Runtime {name} not supported, known are: {known_keys}"
        raise ValueError(msg) from e


__all__ = [
    "PooledRuntime",
    "LocalRuntime",
    "RuntimePool",
    "Runtime",
    "RuntimeOrchestrator",
    "RuntimeAcquireResult",
    "runtime_orchestrator",
    "runtime_watchdog",
    "SingleUseRuntimePool",
    "WarmPoolPolicy",
    "WarmRuntimePool",
    "get_runtime_cls",
]


def __getattr__(name: str) -> Any:  # Lazy access to runtime classes
    if name == "LocalRuntime":
        return _lazy_import("backend.runtime.drivers.local.local_runtime_inprocess", "LocalRuntime")
    raise AttributeError(name)
