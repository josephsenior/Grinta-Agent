"""Forge automation framework package."""

import os
import sys
from pathlib import Path

# Unify packaging logically by extending __path__ to include top-level directories from backend/
# This allows imports like 'forge.integrations' to find 'backend/integrations/'
_backend_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _backend_root not in __path__:
    __path__.append(_backend_root)

__package_name__ = "FORGE_ai"


def get_version():
    """Get the package version from pyproject.toml or installed package metadata.

    Returns:
        Version string or 'unknown' if version cannot be determined

    """
    try:
        root_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        candidate_paths = [
            Path(root_dir) / "pyproject.toml",
            Path(root_dir) / "forge" / "pyproject.toml",
        ]
        for file_path in candidate_paths:
            if file_path.is_file():
                with open(file_path, encoding="utf-8") as f:
                    for line in f:
                        if line.strip().startswith("version ="):
                            return line.split("=", 1)[1].strip().strip('"').strip("'")
    except FileNotFoundError:
        pass
    try:
        from importlib.metadata import version

        return version(__package_name__)
    except ImportError:
        pass
    try:
        from pkg_resources import DistributionNotFound, get_distribution

        return get_distribution(__package_name__).version
    except (ImportError, DistributionNotFound):
        pass
    return "unknown"


try:
    __version__ = get_version()
except Exception:
    __version__ = "unknown"
