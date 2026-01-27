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


_ensure_sitepackages_first()
