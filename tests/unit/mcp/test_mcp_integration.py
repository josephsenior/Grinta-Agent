"""Integration test for MCP settings merging in the full flow."""

from unittest.mock import AsyncMock, patch
import pytest
from openhands.core.config.mcp_config import MCPConfig, MCPSSEServerConfig
from openhands.server.user_auth.default_user_auth import DefaultUserAuth
from openhands.storage.data_models.settings import Settings
from openhands.storage.settings.file_settings_store import FileSettingsStore


@pytest.mark.asyncio
async def test_user_auth_mcp_merging_integration():
    """Test that MCP merging works in the user auth flow."""
    config_settings = Settings(mcp_config=MCPConfig(sse_servers=[MCPSSEServerConfig(url="http://config-server.com")]))
    stored_settings = Settings(
        llm_model="gpt-4", mcp_config=MCPConfig(sse_servers=[MCPSSEServerConfig(url="http://frontend-server.com")])
    )
    user_auth = DefaultUserAuth()
    mock_settings_store = AsyncMock(spec=FileSettingsStore)
    mock_settings_store.load.return_value = stored_settings
    with patch.object(user_auth, "get_user_settings_store", return_value=mock_settings_store):
        with patch.object(Settings, "from_config", return_value=config_settings):
            merged_settings = await user_auth.get_user_settings()
    assert merged_settings is not None
    assert merged_settings.llm_model == "gpt-4"
    assert merged_settings.mcp_config is not None
    assert len(merged_settings.mcp_config.sse_servers) == 2
    assert merged_settings.mcp_config.sse_servers[0].url == "http://config-server.com"
    assert merged_settings.mcp_config.sse_servers[1].url == "http://frontend-server.com"


@pytest.mark.asyncio
async def test_user_auth_caching_behavior():
    """Test that user auth caches the merged settings correctly."""
    config_settings = Settings(mcp_config=MCPConfig(sse_servers=[MCPSSEServerConfig(url="http://config-server.com")]))
    stored_settings = Settings(
        llm_model="gpt-4", mcp_config=MCPConfig(sse_servers=[MCPSSEServerConfig(url="http://frontend-server.com")])
    )
    user_auth = DefaultUserAuth()
    mock_settings_store = AsyncMock(spec=FileSettingsStore)
    mock_settings_store.load.return_value = stored_settings
    with patch.object(user_auth, "get_user_settings_store", return_value=mock_settings_store):
        with patch.object(Settings, "from_config", return_value=config_settings) as mock_from_config:
            settings1 = await user_auth.get_user_settings()
            settings2 = await user_auth.get_user_settings()
    assert settings1 is settings2
    assert len(settings1.mcp_config.sse_servers) == 2
    mock_settings_store.load.assert_called_once()
    mock_from_config.assert_called_once()


@pytest.mark.asyncio
async def test_user_auth_no_stored_settings():
    """Test behavior when no settings are stored (first time user)."""
    user_auth = DefaultUserAuth()
    mock_settings_store = AsyncMock(spec=FileSettingsStore)
    mock_settings_store.load.return_value = None
    with patch.object(user_auth, "get_user_settings_store", return_value=mock_settings_store):
        settings = await user_auth.get_user_settings()
    assert settings is None
