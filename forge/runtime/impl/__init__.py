"""Runtime implementations for forge.

This package exposes implementation classes lazily to avoid importing heavy
dependencies (like Docker) unless they are actually used.
"""

from __future__ import annotations

import importlib
from typing import TYPE_CHECKING, Any

from forge.runtime.impl.action_execution.action_execution_client import (
    ActionExecutionClient,
)

if TYPE_CHECKING:  # Only for static typing
    from forge.runtime.impl.cli.cli_runtime import CLIRuntime as CLIRuntime
    from forge.runtime.impl.docker.docker_runtime import (
        DockerRuntime as DockerRuntime,
    )
    from forge.runtime.impl.local.local_runtime import LocalRuntime as LocalRuntime
    from forge.runtime.impl.remote.remote_runtime import (
        RemoteRuntime as RemoteRuntime,
    )


def _lazy_import(module_path: str, attr: str) -> Any:
    module = importlib.import_module(module_path)
    return getattr(module, attr)


__all__ = [
    "ActionExecutionClient",
    "CLIRuntime",
    "DockerRuntime",
    "LocalRuntime",
    "RemoteRuntime",
]


def __getattr__(name: str) -> Any:
    if name == "CLIRuntime":
        return _lazy_import("forge.runtime.impl.cli.cli_runtime", "CLIRuntime")
    if name == "DockerRuntime":
        return _lazy_import("forge.runtime.impl.docker.docker_runtime", "DockerRuntime")
    if name == "LocalRuntime":
        return _lazy_import("forge.runtime.impl.local.local_runtime", "LocalRuntime")
    if name == "RemoteRuntime":
        return _lazy_import("forge.runtime.impl.remote.remote_runtime", "RemoteRuntime")
    raise AttributeError(name)
