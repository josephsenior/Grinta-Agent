"""Tests for CLI server management functionality."""

from unittest.mock import AsyncMock, MagicMock, patch
import pytest
from openhands.cli.commands import display_mcp_servers, remove_mcp_server
from openhands.core.config import OpenHandsConfig
from openhands.core.config.mcp_config import MCPConfig, MCPSSEServerConfig, MCPStdioServerConfig


class TestMCPServerManagement:
    """Test MCP server management functions."""

    def setup_method(self):
        """Set up test fixtures."""
        self.config = MagicMock(spec=OpenHandsConfig)
        self.config.cli = MagicMock()
        self.config.cli.vi_mode = False

    @patch("openhands.cli.commands.print_formatted_text")
    def test_display_mcp_servers_no_servers(self, mock_print):
        """Test displaying MCP servers when none are configured."""
        self.config.mcp = MCPConfig()
        display_mcp_servers(self.config)
        mock_print.assert_called_once()
        call_args = mock_print.call_args[0][0]
        assert "No custom MCP servers configured" in call_args

    @patch("openhands.cli.commands.print_formatted_text")
    def test_display_mcp_servers_with_servers(self, mock_print):
        """Test displaying MCP servers when some are configured."""
        self.config.mcp = MCPConfig(
            sse_servers=[MCPSSEServerConfig(url="http://test.com")],
            stdio_servers=[MCPStdioServerConfig(name="test-stdio", command="python")],
        )
        display_mcp_servers(self.config)
        assert mock_print.call_count >= 2
        first_call = mock_print.call_args_list[0][0][0]
        assert "Configured MCP servers:" in first_call
        assert "SSE servers: 1" in first_call
        assert "Stdio servers: 1" in first_call

    @pytest.mark.asyncio
    @patch("openhands.cli.commands.cli_confirm")
    @patch("openhands.cli.commands.print_formatted_text")
    async def test_remove_mcp_server_no_servers(self, mock_print, mock_cli_confirm):
        """Test removing MCP server when none are configured."""
        self.config.mcp = MCPConfig()
        await remove_mcp_server(self.config)
        mock_print.assert_called_once_with("No MCP servers configured to remove.")
        mock_cli_confirm.assert_not_called()

    @pytest.mark.asyncio
    @patch("openhands.cli.commands.prompt_for_restart", new_callable=AsyncMock)
    @patch("openhands.cli.commands.cli_confirm")
    @patch("openhands.cli.commands.load_config_file")
    @patch("openhands.cli.commands.save_config_file")
    @patch("openhands.cli.commands.print_formatted_text")
    async def test_remove_mcp_server_success(
        self, mock_print, mock_save, mock_load, mock_cli_confirm, mock_prompt_restart
    ):
        """Test successfully removing an MCP server."""
        self.config.mcp = MCPConfig(
            sse_servers=[MCPSSEServerConfig(url="http://test.com")],
            stdio_servers=[MCPStdioServerConfig(name="test-stdio", command="python")],
        )
        mock_cli_confirm.side_effect = [0, 0]
        mock_load.return_value = {
            "mcp": {
                "sse_servers": [{"url": "http://test.com"}],
                "stdio_servers": [{"name": "test-stdio", "command": "python"}],
            }
        }
        mock_prompt_restart.return_value = False
        await remove_mcp_server(self.config)
        mock_prompt_restart.assert_called()
        assert mock_cli_confirm.call_count == 2
        mock_save.assert_called_once()
        success_calls = [call for call in mock_print.call_args_list if "removed" in str(call[0][0])]
        assert success_calls
