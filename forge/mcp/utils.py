"""Backward-compatible MCP utility wrappers.

The Forge codebase previously exposed MCP helper utilities from the
``forge.mcp`` package. The implementations now live in
``forge.mcp_client.utils``. To avoid circular import issues while keeping the
legacy API, this module provides thin async wrappers that defer importing the
canonical implementations until call time.
"""

from __future__ import annotations

__all__ = ["call_tool_mcp", "create_mcp_clients"]


async def create_mcp_clients(*args, **kwargs):
    """Proxy ``create_mcp_clients`` to the canonical implementation."""
    from forge.mcp_client.utils import create_mcp_clients as _create_mcp_clients

    return await _create_mcp_clients(*args, **kwargs)


async def call_tool_mcp(*args, **kwargs):
    """Proxy ``call_tool_mcp`` to the canonical implementation."""
    from forge.mcp_client.utils import call_tool_mcp as _call_tool_mcp

    return await _call_tool_mcp(*args, **kwargs)

