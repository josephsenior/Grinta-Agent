import asyncio
from unittest import mock
import pytest
from forge.core.config.mcp_config import MCPConfig, MCPSSEServerConfig
from forge.mcp_client import MCPClient, create_mcp_clients, fetch_mcp_tools_from_config


@pytest.mark.asyncio
async def test_sse_connection_timeout():
    """Test that SSE connection timeout is handled gracefully."""
    mock_client = mock.MagicMock(spec=MCPClient)

    async def mock_connect_http(*args, **kwargs):
        await asyncio.sleep(0.1)
        raise asyncio.TimeoutError("Connection timed out")

    mock_client.connect_http = mock.AsyncMock(side_effect=mock_connect_http)
    mock_client.disconnect = mock.AsyncMock()
    with mock.patch("sys.platform", "linux"):
        with mock.patch("forge.mcp_client.utils.MCPClient", return_value=mock_client):
            servers = [
                MCPSSEServerConfig(url="http://server1:8080"),
                MCPSSEServerConfig(url="http://server2:8080"),
            ]
            clients = await create_mcp_clients(sse_servers=servers, shttp_servers=[])
            assert len(clients) == 0
            assert mock_client.connect_http.call_count == 2


@pytest.mark.asyncio
async def test_fetch_mcp_tools_with_timeout():
    """Test that fetch_mcp_tools_from_config handles timeouts gracefully."""
    mock_config = mock.MagicMock(spec=MCPConfig)
    mock_config.sse_servers = ["http://server1:8080"]
    mock_config.shttp_servers = []
    with mock.patch("forge.mcp_client.utils.create_mcp_clients", return_value=[]):
        tools = await fetch_mcp_tools_from_config(mock_config, None)
        assert tools == []


@pytest.mark.asyncio
async def test_mixed_connection_results():
    """Test that fetch_mcp_tools_from_config returns tools even when some connections fail."""
    mock_config = mock.MagicMock(spec=MCPConfig)
    mock_config.sse_servers = ["http://server1:8080", "http://server2:8080"]
    mock_config.shttp_servers = []
    successful_client = mock.MagicMock(spec=MCPClient)
    mock_tool = mock.MagicMock()
    mock_tool.name = "mock_tool"
    mock_tool.to_param.return_value = {
        "type": "function",
        "function": {
            "name": "mock_tool",
            "description": "A mock tool for testing",
            "parameters": {},
        },
    }
    successful_client.tools = [mock_tool]
    with mock.patch("sys.platform", "linux"):
        with mock.patch(
            "forge.mcp_client.utils.create_mcp_clients",
            return_value=[successful_client],
        ):
            tools = await fetch_mcp_tools_from_config(mock_config, None)
            assert len(tools) > 0
            assert tools[0]["function"]["name"] == "mock_tool"
