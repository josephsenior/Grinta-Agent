"""Legacy MCP package for backwards compatibility.

This module re-exports helper utilities that were previously available under
``forge.mcp``. The canonical implementations now live in
``forge.mcp_client``. Tests and extensions that still import from the old
module path can continue to do so safely via these shims.
"""

from __future__ import annotations

from forge.mcp import utils as utils  # noqa: F401  (re-export for compatibility)

__all__ = ["utils"]
