"""Shared registry for canonical classes across reloads."""

from __future__ import annotations

import builtins
from typing import Any

from pydantic._internal._model_construction import ModelMetaclass

# Use builtins to ensure the registry survives module reloads and sys.modules manipulation
if not hasattr(builtins, "__FORGE_CANONICAL_CLASSES__"):
    setattr(builtins, "__FORGE_CANONICAL_CLASSES__", {})

_CLASSES: dict[str, Any] = getattr(builtins, "__FORGE_CANONICAL_CLASSES__")


def canonicalize(name: str, cls: Any) -> Any:
    """Return stable class identity for the given class name."""
    existing = _CLASSES.get(name)
    if existing is None:
        _CLASSES[name] = cls
        return cls
    return existing


class CanonicalModelMetaclass(ModelMetaclass):
    """Metaclass that ensures Pydantic models behave consistently across reloads.

    Instead of trying to return the same class object (which causes issues with super()),
    this metaclass overrides __instancecheck__ and __subclasscheck__ to support
    isinstance() and issubclass() checks across reloaded versions of the same class.
    """

    def __instancecheck__(cls, instance):
        if super().__instancecheck__(instance):
            return True
        # Check if the class names match. This allows isinstance(reloaded_obj, original_class) to be True.
        return type(instance).__name__ == cls.__name__

    def __subclasscheck__(cls, subclass):
        if super().__subclasscheck__(subclass):
            return True
        # Check if the class names match. This allows issubclass(reloaded_class, original_class) to be True.
        return getattr(subclass, "__name__", None) == cls.__name__
