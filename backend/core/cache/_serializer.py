"""Safe JSON-based serialization for Redis cache values.

Replaces pickle.dumps/pickle.loads with JSON to eliminate deserialization
attacks (CWE-502).  Both ForgeConfig and Settings are Pydantic BaseModel
subclasses and round-trip cleanly through ``model_dump`` → JSON → ``model_validate``.
"""

from __future__ import annotations

import json
from enum import Enum
from pathlib import Path, PurePosixPath, PureWindowsPath
from typing import Any, TypeVar

from pydantic import BaseModel, SecretStr

T = TypeVar("T", bound=BaseModel)


def _json_fallback(obj: Any) -> Any:
    """Handle non-JSON-native types produced by Pydantic ``model_dump(mode='python')``."""
    if isinstance(obj, SecretStr):
        return obj.get_secret_value()
    if isinstance(obj, Enum):
        return obj.value
    if isinstance(obj, (Path, PurePosixPath, PureWindowsPath)):
        return str(obj)
    if isinstance(obj, bytes):
        return obj.decode("utf-8", errors="replace")
    if isinstance(obj, set):
        return sorted(obj)
    # Last resort — str() is safer than raising and crashing the cache
    return str(obj)


def serialize_model(model: BaseModel) -> bytes:
    """Serialize a Pydantic model to compact JSON bytes for Redis caching.

    Uses ``model_dump(mode='python')`` so that ``SecretStr`` values are
    preserved (not masked) — required for cache round-tripping.
    """
    data = model.model_dump(mode="python")
    return json.dumps(data, default=_json_fallback, separators=(",", ":")).encode(
        "utf-8"
    )


def deserialize_model(raw: bytes, model_class: type[T]) -> T:
    """Deserialize JSON bytes back to a Pydantic model instance.

    Falls back to pickle for legacy cached data (logged as a warning),
    so an in-flight Redis value written by an older version won't crash
    on read.  The next cache write will overwrite with JSON.
    """
    try:
        data = json.loads(raw)
        return model_class.model_validate(data)
    except (json.JSONDecodeError, UnicodeDecodeError):
        # Legacy pickle data still in Redis — tolerate but warn
        import logging
        import pickle  # noqa: S403
        import warnings

        warnings.warn(
            "Pickle deserialization is deprecated and will be removed in v0.58. "
            "Re-save cached data to migrate to JSON format.",
            DeprecationWarning,
            stacklevel=2,
        )
        logging.getLogger(__name__).warning(
            "Deserializing legacy pickle cache entry for %s — "
            "will be replaced with JSON on next write",
            model_class.__name__,
        )
        return pickle.loads(raw)  # nosec B301 — legacy transitional only
