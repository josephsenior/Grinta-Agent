import asyncio
import pytest
from forge.core.config.mcp_config import MCPSSEServerConfig
from forge.mcp_client.client import MCPClient
from forge.mcp_client.utils import create_mcp_clients


@pytest.mark.asyncio
async def test_create_mcp_clients_timeout_with_invalid_url():
    """Test that create_mcp_clients properly times out when given an invalid URL."""
    server = MCPSSEServerConfig(url="http://non-existent-domain-that-will-timeout.invalid")
    original_connect_connect_http = MCPClient.connect_http

    async def connect_http_with_short_timeout(self, server_url, timeout=30.0):
        return await original_connect_connect_http(self, server_url, timeout=0.5)

    try:
        MCPClient.connect_http = connect_http_with_short_timeout
        start_time = asyncio.get_event_loop().time()
        clients = await create_mcp_clients([server], [])
        end_time = asyncio.get_event_loop().time()
        assert len(clients) == 0
        assert end_time - start_time < 5.0, "Operation took too long, timeout may not be working"
    finally:
        MCPClient.connect_http = original_connect_connect_http


@pytest.mark.asyncio
async def test_create_mcp_clients_with_unreachable_host():
    """Test that create_mcp_clients handles unreachable hosts properly."""
    unreachable_url = "http://192.0.2.1:8080"
    original_connect_http = MCPClient.connect_http

    async def connect_http_with_short_timeout(self, server_url, timeout=30.0):
        return await original_connect_http(self, server_url, timeout=1.0)

    try:
        MCPClient.connect_http = connect_http_with_short_timeout
        start_time = asyncio.get_event_loop().time()
        clients = await create_mcp_clients([unreachable_url], [])
        end_time = asyncio.get_event_loop().time()
        assert len(clients) == 0
        assert end_time - start_time < 5.0, "Operation took too long, timeout may not be working"
    finally:
        MCPClient.connect_http = original_connect_http
