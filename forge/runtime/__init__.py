"""Runtime backends and supporting infrastructure for Forge agents.

This module avoids importing heavy optional dependencies (e.g., docker, k8s)
at import time. Public attributes like `DockerRuntime` are provided lazily via
module-level `__getattr__` so importing `forge.runtime` doesn't require Docker
unless you actually use `DockerRuntime`.
"""

from __future__ import annotations

import importlib
from typing import TYPE_CHECKING, Any

from forge.runtime.base import Runtime
from forge.runtime.orchestrator import (
    RuntimeAcquireResult,
    RuntimeOrchestrator,
    runtime_orchestrator,
)
from forge.runtime.pool import (
    DelegateForkPool,
    PooledRuntime,
    RuntimePool,
    SingleUseRuntimePool,
    WarmPoolPolicy,
    WarmRuntimePool,
)
from forge.runtime.watchdog import runtime_watchdog
from forge.utils.import_utils import get_impl

if TYPE_CHECKING:  # Only for static type checking
    from forge.runtime.impl.cli.cli_runtime import CLIRuntime as CLIRuntime
    from forge.runtime.impl.docker.docker_runtime import (
        DockerRuntime as DockerRuntime,
    )
    from forge.runtime.impl.kubernetes.kubernetes_runtime import (
        KubernetesRuntime as KubernetesRuntime,
    )
    from forge.runtime.impl.local.local_runtime import LocalRuntime as LocalRuntime
    from forge.runtime.impl.remote.remote_runtime import (
        RemoteRuntime as RemoteRuntime,
    )


def _lazy_import(module_path: str, attr: str) -> Any:
    module = importlib.import_module(module_path)
    return getattr(module, attr)


# Map runtime keys to (module, attribute) for lazy loading
_DEFAULT_RUNTIME_IMPORTS: dict[str, tuple[str, str]] = {
    "eventstream": ("forge.runtime.impl.docker.docker_runtime", "DockerRuntime"),
    "docker": ("forge.runtime.impl.docker.docker_runtime", "DockerRuntime"),
    "remote": ("forge.runtime.impl.remote.remote_runtime", "RemoteRuntime"),
    "local": ("forge.runtime.impl.local.local_runtime", "LocalRuntime"),
    "kubernetes": (
        "forge.runtime.impl.kubernetes.kubernetes_runtime",
        "KubernetesRuntime",
    ),
    "cli": ("forge.runtime.impl.cli.cli_runtime", "CLIRuntime"),
}

_THIRD_PARTY_RUNTIME_CLASSES: dict[str, type[Runtime]] = {}
try:
    import third_party.runtime.impl

    third_party_base = "third_party.runtime.impl"
    potential_runtimes = []
    try:
        import pkgutil

        # Only consider valid Python identifiers as potential runtime names.
        # Filesystem directories like 'tree-sitter-python' are not valid module
        # names and will cause import errors like "X is not a package" when
        # used with importlib.import_module. Filter them out.
        for _importer, modname, ispkg in pkgutil.iter_modules(
            third_party.runtime.impl.__path__
        ):
            if not ispkg:
                continue
            # Accept only valid Python identifiers (letters, digits, underscores,
            # not starting with a digit).
            if modname.isidentifier():
                potential_runtimes.append(modname)
    except Exception:
        potential_runtimes = []
    for runtime_name in potential_runtimes:
        try:
            module_path = f"{third_party_base}.{runtime_name}.{runtime_name}_runtime"
            module = importlib.import_module(module_path)
            possible_class_names = [
                f"{runtime_name.upper()}Runtime",
                f"{runtime_name.capitalize()}Runtime",
            ]
            runtime_class = None
            for class_name in possible_class_names:
                try:
                    runtime_class = getattr(module, class_name)
                    break
                except AttributeError:
                    continue
            if runtime_class:
                _THIRD_PARTY_RUNTIME_CLASSES[runtime_name] = runtime_class
        except ImportError:
            pass
        except Exception as e:
            from forge.core.logger import forge_logger as logger

            logger.warning(
                "Failed to import third-party runtime %s: %s", module_path, e
            )
except ImportError:
    pass
_ALL_RUNTIME_KEYS = set(_DEFAULT_RUNTIME_IMPORTS.keys()) | set(
    _THIRD_PARTY_RUNTIME_CLASSES.keys()
)


def get_runtime_cls(name: str) -> type[Runtime]:
    """If name is one of the predefined runtime names (e.g. 'docker'), return its class.

    Otherwise attempt to resolve name as subclass of Runtime and return it.
    Raise on invalid selections.
    """
    # Prefer discovered third-party classes
    if name in _THIRD_PARTY_RUNTIME_CLASSES:
        return _THIRD_PARTY_RUNTIME_CLASSES[name]
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
    "DelegateForkPool",
    "PooledRuntime",
    "CLIRuntime",
    "DockerRuntime",
    "KubernetesRuntime",
    "LocalRuntime",
    "RemoteRuntime",
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
__all__.extend(
    (
        runtime_class.__name__
        for runtime_name, runtime_class in _THIRD_PARTY_RUNTIME_CLASSES.items()
    )
)


def __getattr__(name: str) -> Any:  # Lazy access to runtime classes
    if name == "DockerRuntime":
        return _lazy_import("forge.runtime.impl.docker.docker_runtime", "DockerRuntime")
    if name == "CLIRuntime":
        return _lazy_import("forge.runtime.impl.cli.cli_runtime", "CLIRuntime")
    if name == "LocalRuntime":
        return _lazy_import("forge.runtime.impl.local.local_runtime", "LocalRuntime")
    if name == "RemoteRuntime":
        return _lazy_import("forge.runtime.impl.remote.remote_runtime", "RemoteRuntime")
    if name == "KubernetesRuntime":
        return _lazy_import(
            "forge.runtime.impl.kubernetes.kubernetes_runtime", "KubernetesRuntime"
        )
    raise AttributeError(name)
