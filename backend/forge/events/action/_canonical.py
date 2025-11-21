"""Shared registry for canonical action classes across reloads."""

from __future__ import annotations

import sys
import types
from typing import Any

_MODULE_NAME = "forge.events.action._canonical_registry"
_registry_module = sys.modules.get(_MODULE_NAME)
if _registry_module is None:
    _registry_module = types.ModuleType(_MODULE_NAME)
    _registry_module.classes = {}  # type: ignore[attr-defined]
    sys.modules[_MODULE_NAME] = _registry_module

_CLASSES: dict[str, Any] = getattr(
    _registry_module, "classes"
)  # type: ignore[attr-defined]


def canonicalize(name: str, cls: Any) -> Any:
    """Return stable class identity for the given action class name."""
    existing = _CLASSES.get(name)
    if existing is None:
        _CLASSES[name] = cls
        return cls
    return existing

