"""Model Context Protocol client wrapper for managing remote tool registries."""

from __future__ import annotations

from typing import TYPE_CHECKING

from fastmcp import Client
from fastmcp.client.transports import (
    SSETransport,
    StdioTransport,
    StreamableHttpTransport,
)
from mcp import McpError
from pydantic import BaseModel, ConfigDict, Field

from forge.core.config.mcp_config import (
    MCPSHTTPServerConfig,
    MCPSSEServerConfig,
    MCPStdioServerConfig,
)
from forge.core.logger import forge_logger as logger
from forge.mcp_client.error_collector import mcp_error_collector
from forge.mcp_client.tool import MCPClientTool

if TYPE_CHECKING:
    from mcp.types import CallToolResult


class MCPClient(BaseModel):
    """A collection of tools that connects to an MCP server and manages available tools through the Model Context Protocol."""

    model_config = ConfigDict(arbitrary_types_allowed=True)
    client: Client | None = None
    description: str = "MCP client tools for server interaction"
    tools: list[MCPClientTool] = Field(default_factory=list)
    tool_map: dict[str, MCPClientTool] = Field(default_factory=dict)

    async def _initialize_and_list_tools(self) -> None:
        """Initialize session and populate tool map."""
        if not self.client:
            msg = "Session not initialized."
            raise RuntimeError(msg)
        async with self.client:
            tools = await self.client.list_tools()
        self.tools = []
        for tool in tools:
            server_tool = MCPClientTool(
                name=tool.name,
                description=tool.description,
                inputSchema=tool.inputSchema,
            )
            self.tool_map[tool.name] = server_tool
            self.tools.append(server_tool)
        logger.info("Connected to server with tools: %s", [tool.name for tool in tools])

    async def connect_http(
        self,
        server: MCPSSEServerConfig | MCPSHTTPServerConfig,
        conversation_id: str | None = None,
        timeout: float = 30.0,
    ) -> None:
        """Connect to MCP server using SHTTP or SSE transport.

        Args:
            server: Server configuration
            conversation_id: Optional conversation ID
            timeout: Connection timeout in seconds

        Raises:
            ValueError: If server URL is missing
            McpError: On MCP-specific errors
            Exception: On other connection errors

        """
        server_url = server.url
        if not server_url:
            msg = "Server URL is required."
            raise ValueError(msg)

        try:
            headers = self._build_http_headers(server.api_key, conversation_id)
            transport = self._create_http_transport(server, server_url, headers)
            self.client = Client(transport, timeout=timeout)
            await self._initialize_and_list_tools()
        except McpError as e:
            self._handle_connection_error(server_url, server, e, is_mcp_error=True)
            raise
        except Exception as e:
            self._handle_connection_error(server_url, server, e, is_mcp_error=False)
            raise

    def _build_http_headers(
        self, api_key: str | None, conversation_id: str | None
    ) -> dict:
        """Build HTTP headers for connection.

        Args:
            api_key: Optional API key
            conversation_id: Optional conversation ID

        Returns:
            Dictionary of headers

        """
        headers = {}
        if api_key:
            headers.update(
                {
                    "Authorization": f"Bearer {api_key}",
                    "s": api_key,
                    "X-Session-API-Key": api_key,
                },
            )
        if conversation_id:
            headers["X-Forge-ServerConversation-ID"] = conversation_id
        return headers

    def _create_http_transport(self, server, server_url: str, headers: dict):
        """Create appropriate HTTP transport.

        Args:
            server: Server configuration
            server_url: Server URL
            headers: HTTP headers

        Returns:
            Transport instance

        """
        if isinstance(server, MCPSHTTPServerConfig):
            return StreamableHttpTransport(url=server_url, headers=headers or None)
        return SSETransport(url=server_url, headers=headers or None)

    def _handle_connection_error(
        self, server_url: str, server, error: Exception, is_mcp_error: bool = False
    ) -> None:
        """Handle connection errors.

        Args:
            server_url: Server URL
            server: Server configuration
            error: Exception that occurred
            is_mcp_error: Whether this is an MCP-specific error

        """
        error_prefix = "McpError" if is_mcp_error else "Error"
        error_msg = f"{error_prefix} connecting to {server_url}: {error}"
        logger.error(error_msg)

        server_type = "shttp" if isinstance(server, MCPSHTTPServerConfig) else "sse"
        mcp_error_collector.add_error(
            server_name=server_url,
            server_type=server_type,
            error_message=error_msg,
            exception_details=str(error),
        )

    async def connect_stdio(
        self, server: MCPStdioServerConfig, timeout: float = 30.0
    ) -> None:
        """Connect to MCP server using stdio transport."""
        try:
            transport = StdioTransport(
                command=server.command, args=server.args or [], env=server.env
            )
            self.client = Client(transport, timeout=timeout)
            await self._initialize_and_list_tools()
        except Exception as e:
            server_name = getattr(
                server, "name", f"{server.command} {' '.join(server.args or [])}"
            )
            error_msg = f"Failed to connect to stdio server {server_name}: {e}"
            logger.error(error_msg)
            mcp_error_collector.add_error(
                server_name=server_name,
                server_type="stdio",
                error_message=error_msg,
                exception_details=str(e),
            )
            raise

    async def call_tool(self, tool_name: str, args: dict) -> CallToolResult:
        """Call a tool on the MCP server."""
        if tool_name not in self.tool_map:
            msg = f"Tool {tool_name} not found."
            raise ValueError(msg)
        if not self.client:
            msg = "Client session is not available."
            raise RuntimeError(msg)
        async with self.client:
            return await self.client.call_tool_mcp(name=tool_name, arguments=args)
