"""Test MCP settings merging functionality."""

from unittest.mock import patch
import pytest
from forge.core.config.mcp_config import (
    MCPConfig,
    MCPSSEServerConfig,
    MCPStdioServerConfig,
)
from forge.storage.data_models.settings import Settings


@pytest.mark.asyncio
async def test_mcp_settings_merge_config_only():
    """Test merging when only config.toml has MCP settings."""
    mock_config_settings = Settings(
        mcp_config=MCPConfig(
            sse_servers=[MCPSSEServerConfig(url="http://config-server.com")]
        )
    )
    frontend_settings = Settings(llm_model="gpt-4")
    with patch.object(Settings, "from_config", return_value=mock_config_settings):
        merged_settings = frontend_settings.merge_with_config_settings()
    assert merged_settings.mcp_config is not None
    assert len(merged_settings.mcp_config.sse_servers) == 1
    assert merged_settings.mcp_config.sse_servers[0].url == "http://config-server.com"
    assert merged_settings.llm_model == "gpt-4"


@pytest.mark.asyncio
async def test_mcp_settings_merge_frontend_only():
    """Test merging when only frontend has MCP settings."""
    mock_config_settings = Settings(llm_model="claude-3")
    frontend_settings = Settings(
        llm_model="gpt-4",
        mcp_config=MCPConfig(
            sse_servers=[MCPSSEServerConfig(url="http://frontend-server.com")]
        ),
    )
    with patch.object(Settings, "from_config", return_value=mock_config_settings):
        merged_settings = frontend_settings.merge_with_config_settings()
    assert merged_settings.mcp_config is not None
    assert len(merged_settings.mcp_config.sse_servers) == 1
    assert merged_settings.mcp_config.sse_servers[0].url == "http://frontend-server.com"
    assert merged_settings.llm_model == "gpt-4"


@pytest.mark.asyncio
async def test_mcp_settings_merge_both_present():
    """Test merging when both config.toml and frontend have MCP settings."""
    mock_config_settings = Settings(
        mcp_config=MCPConfig(
            sse_servers=[MCPSSEServerConfig(url="http://config-server.com")],
            stdio_servers=[
                MCPStdioServerConfig(
                    name="config-stdio", command="config-cmd", args=["arg1"]
                )
            ],
        )
    )
    frontend_settings = Settings(
        llm_model="gpt-4",
        mcp_config=MCPConfig(
            sse_servers=[MCPSSEServerConfig(url="http://frontend-server.com")],
            stdio_servers=[
                MCPStdioServerConfig(
                    name="frontend-stdio", command="frontend-cmd", args=["arg2"]
                )
            ],
        ),
    )
    with patch.object(Settings, "from_config", return_value=mock_config_settings):
        merged_settings = frontend_settings.merge_with_config_settings()
    assert merged_settings.mcp_config is not None
    assert len(merged_settings.mcp_config.sse_servers) == 2
    assert merged_settings.mcp_config.sse_servers[0].url == "http://config-server.com"
    assert merged_settings.mcp_config.sse_servers[1].url == "http://frontend-server.com"
    assert len(merged_settings.mcp_config.stdio_servers) == 2
    assert merged_settings.mcp_config.stdio_servers[0].name == "config-stdio"
    assert merged_settings.mcp_config.stdio_servers[1].name == "frontend-stdio"
    assert merged_settings.llm_model == "gpt-4"


@pytest.mark.asyncio
async def test_mcp_settings_merge_no_config():
    """Test merging when config.toml has no MCP settings."""
    mock_config_settings = None
    frontend_settings = Settings(
        llm_model="gpt-4",
        mcp_config=MCPConfig(
            sse_servers=[MCPSSEServerConfig(url="http://frontend-server.com")]
        ),
    )
    with patch.object(Settings, "from_config", return_value=mock_config_settings):
        merged_settings = frontend_settings.merge_with_config_settings()
    assert merged_settings.mcp_config is not None
    assert len(merged_settings.mcp_config.sse_servers) == 1
    assert merged_settings.mcp_config.sse_servers[0].url == "http://frontend-server.com"
    assert merged_settings.llm_model == "gpt-4"


@pytest.mark.asyncio
async def test_mcp_settings_merge_neither_present():
    """Test merging when neither config.toml nor frontend have MCP settings."""
    mock_config_settings = Settings(llm_model="claude-3")
    frontend_settings = Settings(llm_model="gpt-4")
    with patch.object(Settings, "from_config", return_value=mock_config_settings):
        merged_settings = frontend_settings.merge_with_config_settings()
    assert merged_settings.mcp_config is None
    assert merged_settings.llm_model == "gpt-4"
