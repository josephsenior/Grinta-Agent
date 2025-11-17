"""Tests for CLI Runtime MCP functionality."""

from unittest.mock import MagicMock, patch
import pytest
from forge.core.config import ForgeConfig
from forge.core.config.mcp_config import (
    MCPConfig,
    MCPSSEServerConfig,
    MCPStdioServerConfig,
)
from forge.events.action.mcp import MCPAction
from forge.events.observation import ErrorObservation
from forge.events.observation.mcp import MCPObservation
from forge.llm.llm_registry import LLMRegistry
from forge.runtime.impl.cli.cli_runtime import CLIRuntime


class TestCLIRuntimeMCP:
    """Test MCP functionality in CLI Runtime."""

    def setup_method(self):
        """Set up test fixtures."""
        self.config = ForgeConfig()
        self.event_stream = MagicMock()
        llm_registry = LLMRegistry(config=ForgeConfig())
        self.runtime = CLIRuntime(
            config=self.config,
            event_stream=self.event_stream,
            sid="test-session",
            llm_registry=llm_registry,
        )

    @pytest.mark.asyncio
    async def test_call_tool_mcp_no_servers_configured(self):
        """Test MCP call with no servers configured."""
        self.runtime.config.mcp = MCPConfig()
        action = MCPAction(name="test_tool", arguments={"arg1": "value1"})
        with patch("sys.platform", "linux"):
            result = await self.runtime.call_tool_mcp(action)
        assert isinstance(result, ErrorObservation)
        assert "No MCP servers configured" in result.content

    @pytest.mark.asyncio
    @patch("forge.mcp.utils.create_mcp_clients")
    async def test_call_tool_mcp_no_clients_created(self, mock_create_clients):
        """Test MCP call when no clients can be created."""
        self.runtime.config.mcp = MCPConfig(
            sse_servers=[MCPSSEServerConfig(url="http://test.com")]
        )
        mock_create_clients.return_value = []
        action = MCPAction(name="test_tool", arguments={"arg1": "value1"})
        with patch("sys.platform", "linux"):
            result = await self.runtime.call_tool_mcp(action)
        assert isinstance(result, ErrorObservation)
        assert "No MCP clients could be created" in result.content
        mock_create_clients.assert_called_once()

    @pytest.mark.asyncio
    @patch("forge.mcp.utils.create_mcp_clients")
    @patch("forge.mcp.utils.call_tool_mcp")
    async def test_call_tool_mcp_success(self, mock_call_tool, mock_create_clients):
        """Test successful MCP tool call."""
        self.runtime.config.mcp = MCPConfig(
            sse_servers=[MCPSSEServerConfig(url="http://test.com")],
            stdio_servers=[MCPStdioServerConfig(name="test-stdio", command="python")],
        )
        mock_client = MagicMock()
        mock_create_clients.return_value = [mock_client]
        expected_observation = MCPObservation(
            content='{"result": "success"}',
            name="test_tool",
            arguments={"arg1": "value1"},
        )
        mock_call_tool.return_value = expected_observation
        action = MCPAction(name="test_tool", arguments={"arg1": "value1"})
        with patch("sys.platform", "linux"):
            result = await self.runtime.call_tool_mcp(action)
        assert result == expected_observation
        mock_create_clients.assert_called_once_with(
            self.runtime.config.mcp.sse_servers,
            self.runtime.config.mcp.shttp_servers,
            self.runtime.sid,
            self.runtime.config.mcp.stdio_servers,
        )
        mock_call_tool.assert_called_once_with([mock_client], action)

    @pytest.mark.asyncio
    @patch("forge.mcp.utils.create_mcp_clients")
    async def test_call_tool_mcp_exception_handling(self, mock_create_clients):
        """Test exception handling in MCP tool call."""
        self.runtime.config.mcp = MCPConfig(
            sse_servers=[MCPSSEServerConfig(url="http://test.com")]
        )
        mock_create_clients.side_effect = Exception("Connection error")
        action = MCPAction(name="test_tool", arguments={"arg1": "value1"})
        with patch("sys.platform", "linux"):
            result = await self.runtime.call_tool_mcp(action)
        assert isinstance(result, ErrorObservation)
        assert "Error executing MCP tool test_tool" in result.content
        assert "Connection error" in result.content

    def test_get_mcp_config_basic(self):
        """Test basic MCP config retrieval."""
        expected_config = MCPConfig(
            sse_servers=[MCPSSEServerConfig(url="http://test.com")],
            stdio_servers=[MCPStdioServerConfig(name="test-stdio", command="python")],
        )
        self.runtime.config.mcp = expected_config
        with patch("sys.platform", "linux"):
            result = self.runtime.get_mcp_config()
        assert result == expected_config

    def test_get_mcp_config_with_extra_stdio_servers(self):
        """Test MCP config with extra stdio servers."""
        initial_stdio_server = MCPStdioServerConfig(name="initial", command="python")
        self.runtime.config.mcp = MCPConfig(stdio_servers=[initial_stdio_server])
        extra_servers = [
            MCPStdioServerConfig(name="extra1", command="node"),
            MCPStdioServerConfig(name="extra2", command="java"),
        ]
        with patch("sys.platform", "linux"):
            result = self.runtime.get_mcp_config(extra_stdio_servers=extra_servers)
        assert len(result.stdio_servers) == 3
        assert initial_stdio_server in result.stdio_servers
        assert extra_servers[0] in result.stdio_servers
        assert extra_servers[1] in result.stdio_servers
