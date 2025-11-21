"""Convenience exports for Forge's Model Context Protocol client utilities."""

from forge.mcp_client.client import MCPClient
from forge.mcp_client.error_collector import mcp_error_collector
from forge.mcp_client.tool import MCPClientTool
from forge.mcp_client.utils import (
    add_mcp_tools_to_agent,
    call_tool_mcp,
    convert_mcp_clients_to_tools,
    create_mcp_clients,
    fetch_mcp_tools_from_config,
)

__all__ = [
    "MCPClient",
    "MCPClientTool",
    "add_mcp_tools_to_agent",
    "call_tool_mcp",
    "convert_mcp_clients_to_tools",
    "create_mcp_clients",
    "fetch_mcp_tools_from_config",
    "mcp_error_collector",
]
