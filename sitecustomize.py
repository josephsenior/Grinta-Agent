"""Adjust sys.path and dependency stubs before the test suite imports packages."""

from __future__ import annotations

import site
import sys
import types


def _ensure_sitepackages_first() -> None:
    try:
        site_dirs = list(site.getsitepackages())
    except Exception:
        site_dirs = []
    try:
        user = site.getusersitepackages()
        if user:
            site_dirs.append(user)
    except Exception:
        pass

    # Insert site-packages entries at front if not already present.
    for d in reversed(site_dirs):
        if d and d not in sys.path:
            sys.path.insert(0, d)


def _ensure_tokenizers_stub() -> None:
    """Provide a lightweight stub to satisfy litellm's optional dependency."""
    if "tokenizers" in sys.modules:
        return

    tokenizers_stub = types.ModuleType("tokenizers")

    class _Tokenizer:  # pragma: no cover - simple compatibility shim
        def __init__(self, *_, **__):
            self.config = {}

        def encode(self, *_args, **_kwargs):
            return []

    tokenizers_stub.Tokenizer = _Tokenizer  # type: ignore[attr-defined]
    sys.modules["tokenizers"] = tokenizers_stub


_ensure_sitepackages_first()
_ensure_tokenizers_stub()

# Pre-import litellm once so later imports during coverage runs use the cached module.
try:  # pragma: no cover - defensive import
    import litellm  # noqa: F401
except Exception:
    pass
