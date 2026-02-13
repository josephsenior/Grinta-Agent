"""Forge plugin system — lightweight hook-based extension API.

There are **two** plugin surfaces in Forge — this module provides the
*core hook API* while :mod:`backend.runtime.plugins` provides the
*sandbox runtime plugin API*.  They serve different purposes:

+------------------------------+--------------------------------------------+
| This module (core hooks)     | runtime.plugins (sandbox extensions)       |
+==============================+============================================+
| ``ForgePlugin`` — lifecycle   | ``Plugin`` — initialise / run inside sandbox|
| hooks (action, event, LLM,   |                                            |
| session).                    |                                            |
+------------------------------+--------------------------------------------+
| Registered via entry-point   | Declared via ``PluginRequirement`` +       |
| ``forge.plugins`` →          | ``ALL_PLUGINS`` or entry-point discovery.  |
| ``register(registry)``       |                                            |
+------------------------------+--------------------------------------------+
| Runs **in the Forge process**| Runs **inside the sandbox/container**.     |
+------------------------------+--------------------------------------------+

If a third-party package needs both, it should register *two* objects —
one ``ForgePlugin`` for host-side hooks, and one ``Plugin`` subclass for
sandbox behaviour.

Plugins are Python packages that expose a ``forge_plugin`` entry point
(group: ``forge.plugins``).  Each entry point must resolve to a callable
that accepts a :class:`PluginRegistry` and calls ``registry.register(...)``
to install one or more :class:`ForgePlugin` instances.

Example ``pyproject.toml`` entry for a plugin::

    [project.entry-points.\"forge.plugins\"]
    my_plugin = \"my_plugin:register\"

Example plugin implementation::

    from backend.core.plugin import ForgePlugin, PluginRegistry, HookType

    class MyPlugin(ForgePlugin):
        name = \"my-plugin\"
        version = \"0.1.0\"

        async def on_action_pre(self, action):
            # Modify or inspect actions before execution
            return action

    def register(registry: PluginRegistry):
        registry.register(MyPlugin())
"""

from __future__ import annotations

import logging
from abc import ABC
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from backend.events.action import Action
    from backend.events.observation import Observation
    from backend.events.event import Event

logger = logging.getLogger(__name__)

# ------------------------------------------------------------------
# API version — bump MINOR for additive hook changes, MAJOR for
# breaking contract changes.  Plugins can declare ``min_api_version``
# to fail-fast when loaded into an incompatible host.
# ------------------------------------------------------------------
PLUGIN_API_VERSION: tuple[int, int] = (1, 0)

# How many minor versions back we support.  Plugins whose
# ``min_api_version`` is more than PLUGIN_COMPAT_WINDOW minor versions
# behind the current PLUGIN_API_VERSION will emit a deprecation
# warning at registration time, signalling that support may be dropped
# in a future release.
PLUGIN_COMPAT_WINDOW: int = 2

# Contract stability marker — when True the hook signatures in
# ``ForgePlugin`` are considered stable and will follow semver.
# Third-party plugins may rely on this guarantee.
__plugin_contract_frozen__: bool = True


# ------------------------------------------------------------------
# Hook types
# ------------------------------------------------------------------

class HookType(str, Enum):
    """Lifecycle hooks that plugins can tap into."""

    ACTION_PRE = "action_pre"
    """Called before an action is dispatched to the runtime."""

    ACTION_POST = "action_post"
    """Called after an action is executed, with its observation."""

    EVENT_EMITTED = "event_emitted"
    """Called when any event is emitted to the event stream."""

    SESSION_START = "session_start"
    """Called when a new agent session begins."""

    SESSION_END = "session_end"
    """Called when an agent session ends."""

    LLM_PRE = "llm_pre"
    """Called before an LLM completion request is made."""

    LLM_POST = "llm_post"
    """Called after an LLM completion response is received."""


# ------------------------------------------------------------------
# Plugin ABC
# ------------------------------------------------------------------

class ForgePlugin(ABC):
    """Base class for Forge plugins.

    Subclasses should set ``name`` and ``version`` and override any
    ``on_*`` methods they want to hook into.  All hooks are optional —
    the default implementations are no-ops.

    Set ``min_api_version`` to the minimum ``PLUGIN_API_VERSION`` your
    plugin is compatible with.  The registry will reject plugins whose
    ``min_api_version`` exceeds the host version.
    """

    name: str = "unnamed-plugin"
    version: str = "0.0.0"
    description: str = ""
    min_api_version: tuple[int, int] = (1, 0)

    # ── Action hooks ─────────────────────────────────────

    async def on_action_pre(self, action: Action) -> Action:
        """Called before an action is executed.

        Return the (possibly modified) action.  To block execution,
        raise an exception.
        """
        return action

    async def on_action_post(
        self, action: Action, observation: Observation
    ) -> Observation:
        """Called after an action is executed.

        Return the (possibly modified) observation.
        """
        return observation

    # ── Event hooks ──────────────────────────────────────

    async def on_event(self, event: Event) -> None:
        """Called whenever an event is emitted to the stream."""

    # ── Session hooks ────────────────────────────────────

    async def on_session_start(self, session_id: str, metadata: dict[str, Any]) -> None:
        """Called when a new agent session begins."""

    async def on_session_end(self, session_id: str, metadata: dict[str, Any]) -> None:
        """Called when an agent session ends."""

    # ── LLM hooks ────────────────────────────────────────

    async def on_llm_pre(self, messages: list[dict[str, Any]], **kwargs: Any) -> list[dict[str, Any]]:
        """Called before an LLM request. Return (possibly modified) messages."""
        return messages

    async def on_llm_post(self, response: Any) -> Any:
        """Called after an LLM response is received."""
        return response

    # ── Repr ─────────────────────────────────────────────

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(name={self.name!r}, v={self.version})"


# ------------------------------------------------------------------
# Plugin Registry
# ------------------------------------------------------------------

@dataclass
class PluginRegistry:
    """Central registry managing loaded plugins and dispatching hooks.

    The registry is a singleton-like object — typically one per process.
    """

    _plugins: dict[str, ForgePlugin] = field(default_factory=dict)

    def register(self, plugin: ForgePlugin) -> None:
        """Register a plugin. Duplicate names and incompatible versions are rejected.

        Version compatibility rules:

        * ``min_api_version > PLUGIN_API_VERSION`` → **rejected** (hard error).
        * ``min_api_version`` within ``PLUGIN_COMPAT_WINDOW`` of the current
          minor version → **accepted** normally.
        * ``min_api_version`` older than the compat window → **accepted** with
          a deprecation warning.
        """
        if plugin.name in self._plugins:
            logger.warning(
                "Plugin %r already registered — skipping duplicate",
                plugin.name,
            )
            return
        # Version gate — hard reject when the plugin requires a newer API
        required = getattr(plugin, "min_api_version", (1, 0))
        if required > PLUGIN_API_VERSION:
            logger.error(
                "Plugin %r requires API v%s.%s but host provides v%s.%s — skipping",
                plugin.name,
                *required,
                *PLUGIN_API_VERSION,
            )
            return
        # Deprecation warning — plugin targets an API version near the
        # edge of the compatibility window.
        host_major, host_minor = PLUGIN_API_VERSION
        req_major, req_minor = required
        if req_major == host_major and (host_minor - req_minor) >= PLUGIN_COMPAT_WINDOW:
            import warnings

            msg = (
                f"Plugin {plugin.name!r} targets API v{req_major}.{req_minor} "
                f"which is at the edge of the compatibility window "
                f"(current v{host_major}.{host_minor}, window={PLUGIN_COMPAT_WINDOW}). "
                f"Update the plugin to a newer min_api_version before support is dropped."
            )
            warnings.warn(msg, DeprecationWarning, stacklevel=2)
            logger.warning(msg)
        self._plugins[plugin.name] = plugin
        logger.info("Plugin registered: %s v%s", plugin.name, plugin.version)

    def unregister(self, name: str) -> None:
        """Unregister a plugin by name."""
        removed = self._plugins.pop(name, None)
        if removed:
            logger.info("Plugin unregistered: %s", name)

    @property
    def plugins(self) -> list[ForgePlugin]:
        """Return a list of all registered plugins."""
        return list(self._plugins.values())

    def get_plugin(self, name: str) -> Optional[ForgePlugin]:
        """Get a plugin by name."""
        return self._plugins.get(name)

    # ── Hook dispatch helpers ────────────────────────────

    async def dispatch_action_pre(self, action: Action) -> Action:
        """Chain all ACTION_PRE hooks, passing modified action forward."""
        for plugin in self._plugins.values():
            try:
                action = await plugin.on_action_pre(action)
            except Exception:
                logger.exception("Plugin %s.on_action_pre failed", plugin.name)
        return action

    async def dispatch_action_post(
        self, action: Action, observation: Observation
    ) -> Observation:
        """Chain all ACTION_POST hooks."""
        for plugin in self._plugins.values():
            try:
                observation = await plugin.on_action_post(action, observation)
            except Exception:
                logger.exception("Plugin %s.on_action_post failed", plugin.name)
        return observation

    async def dispatch_event(self, event: Event) -> None:
        """Fan-out EVENT_EMITTED to all plugins."""
        for plugin in self._plugins.values():
            try:
                await plugin.on_event(event)
            except Exception:
                logger.exception("Plugin %s.on_event failed", plugin.name)

    async def dispatch_session_start(
        self, session_id: str, metadata: dict[str, Any] | None = None
    ) -> None:
        for plugin in self._plugins.values():
            try:
                await plugin.on_session_start(session_id, metadata or {})
            except Exception:
                logger.exception("Plugin %s.on_session_start failed", plugin.name)

    async def dispatch_session_end(
        self, session_id: str, metadata: dict[str, Any] | None = None
    ) -> None:
        for plugin in self._plugins.values():
            try:
                await plugin.on_session_end(session_id, metadata or {})
            except Exception:
                logger.exception("Plugin %s.on_session_end failed", plugin.name)

    async def dispatch_llm_pre(
        self, messages: list[dict[str, Any]], **kwargs: Any
    ) -> list[dict[str, Any]]:
        for plugin in self._plugins.values():
            try:
                messages = await plugin.on_llm_pre(messages, **kwargs)
            except Exception:
                logger.exception("Plugin %s.on_llm_pre failed", plugin.name)
        return messages

    async def dispatch_llm_post(self, response: Any) -> Any:
        for plugin in self._plugins.values():
            try:
                response = await plugin.on_llm_post(response)
            except Exception:
                logger.exception("Plugin %s.on_llm_post failed", plugin.name)
        return response


# ------------------------------------------------------------------
# Entry-point discovery
# ------------------------------------------------------------------

def discover_plugins(registry: PluginRegistry | None = None) -> PluginRegistry:
    """Discover and load plugins from ``forge.plugins`` entry points.

    Args:
        registry: Existing registry to populate. Creates a new one if ``None``.

    Returns:
        The populated :class:`PluginRegistry`.
    """
    if registry is None:
        registry = PluginRegistry()

    try:
        from importlib.metadata import entry_points
    except ImportError:
        from importlib_metadata import entry_points  # type: ignore[no-redef]

    eps = entry_points()
    # Python 3.12+ returns a SelectableGroups / dict-like
    group = eps.get("forge.plugins", []) if isinstance(eps, dict) else eps.select(group="forge.plugins")  # type: ignore[union-attr]

    for ep in group:
        try:
            register_fn = ep.load()
            if callable(register_fn):
                register_fn(registry)
                logger.debug("Loaded plugin entry point: %s", ep.name)
            else:
                logger.warning(
                    "Plugin entry point %s is not callable — skipping", ep.name
                )
        except Exception:
            logger.exception("Failed to load plugin entry point: %s", ep.name)

    return registry


# ------------------------------------------------------------------
# Module-level singleton (lazy)
# ------------------------------------------------------------------

_global_registry: PluginRegistry | None = None


def get_plugin_registry() -> PluginRegistry:
    """Return the global plugin registry, creating it on first call."""
    global _global_registry
    if _global_registry is None:
        _global_registry = discover_plugins()
    return _global_registry


__all__ = [
    "ForgePlugin",
    "HookType",
    "PLUGIN_API_VERSION",
    "PLUGIN_COMPAT_WINDOW",
    "PluginRegistry",
    "__plugin_contract_frozen__",
    "discover_plugins",
    "get_plugin_registry",
]
