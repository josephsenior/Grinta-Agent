"""Startup-time capability matrix for Forge runtimes.

:class:`RuntimeCapabilities` is a frozen snapshot of what a runtime can
(and cannot) do, populated once during ``connect()`` and queryable by
downstream code.  This replaces scattered ``sys.platform`` / ``shutil.which``
checks with a single structured source of truth.
"""

from __future__ import annotations

import os
import shutil
import sys
from dataclasses import dataclass, field


@dataclass(frozen=True, slots=True)
class RuntimeCapabilities:
    """Immutable snapshot of capabilities available in the current runtime.

    Populated once during startup and attached to the :class:`Runtime`
    instance so that any code with a runtime reference can inspect
    capabilities deterministically.
    """

    # -- platform -----------------------------------------------------------
    platform: str = ""
    """``sys.platform`` at snapshot time (e.g. ``'win32'``, ``'linux'``)."""

    is_windows: bool = False
    """True when running on Windows (any variant)."""

    is_container: bool = False
    """True when running inside a Docker / OCI container."""

    # -- tools --------------------------------------------------------------
    has_git: bool = False
    has_tmux: bool = False
    has_docker: bool = False
    has_bash: bool = False

    # -- feature flags ------------------------------------------------------
    can_browse: bool = False
    """True when browser automation is enabled and the package is importable."""

    can_mcp: bool = False
    """True when MCP stdio servers can be spawned (not Windows currently)."""

    can_copy_from_sandbox: bool = True
    """True when ``copy_from`` is available (always True for local runtime)."""

    # -- summary ------------------------------------------------------------
    missing_tools: tuple[str, ...] = ()
    """Names of tools that are expected but missing."""


def detect_capabilities(
    *,
    enable_browser: bool = False,
) -> RuntimeCapabilities:
    """Probe the host environment and return a frozen capability snapshot.

    This function is intentionally *fast* — it only calls ``shutil.which``
    and checks a few env-vars.  It should be called once during
    ``Runtime.connect()`` and the result stored on ``self.capabilities``.
    """
    platform = sys.platform
    is_windows = platform == "win32"

    # Container detection heuristics
    is_container = (
        os.path.isfile("/.dockerenv")
        or os.environ.get("container", "") != ""
        or os.environ.get("KUBERNETES_SERVICE_HOST", "") != ""
    )

    has_git = shutil.which("git") is not None
    has_tmux = shutil.which("tmux") is not None
    has_docker = shutil.which("docker") is not None
    has_bash = shutil.which("bash") is not None

    # Browser: enabled flag + importable dependency
    can_browse = False
    if enable_browser:
        try:
            import importlib

            importlib.import_module("playwright")
            can_browse = True
        except ImportError:
            pass

    # MCP stdio requires subprocess spawning — disabled on Windows for now
    can_mcp = not is_windows

    # Collect missing tools for diagnostic logging
    expected = {"git": has_git}
    if not is_windows:
        expected["tmux"] = has_tmux
        expected["bash"] = has_bash
    missing = tuple(name for name, found in expected.items() if not found)

    return RuntimeCapabilities(
        platform=platform,
        is_windows=is_windows,
        is_container=is_container,
        has_git=has_git,
        has_tmux=has_tmux,
        has_docker=has_docker,
        has_bash=has_bash,
        can_browse=can_browse,
        can_mcp=can_mcp,
        can_copy_from_sandbox=True,
        missing_tools=missing,
    )
