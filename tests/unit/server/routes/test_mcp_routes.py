from unittest.mock import AsyncMock, patch
import pytest
from openhands.integrations.service_types import GitService
from openhands.server.routes.mcp import get_conversation_link
from openhands.server.types import AppMode


@pytest.mark.asyncio
async def test_get_conversation_link_non_saas_mode():
    """Test get_conversation_link in non-SAAS mode."""
    mock_service = AsyncMock(spec=GitService)
    with patch("openhands.server.routes.mcp.server_config") as mock_config:
        mock_config.app_mode = AppMode.OSS
        result = await get_conversation_link(
            service=mock_service, conversation_id="test-convo-id", body="Original body"
        )
        assert result == "Original body"
        mock_service.get_user.assert_not_called()


@pytest.mark.asyncio
async def test_get_conversation_link_saas_mode():
    """Test get_conversation_link in SAAS mode."""
    mock_service = AsyncMock(spec=GitService)
    mock_user = AsyncMock()
    mock_user.login = "testuser"
    mock_service.get_user.return_value = mock_user
    with patch("openhands.server.routes.mcp.server_config") as mock_config, patch(
        "openhands.server.routes.mcp.CONVERSATION_URL", "https://test.example.com/conversations/{}"
    ):
        mock_config.app_mode = AppMode.SAAS
        result = await get_conversation_link(
            service=mock_service, conversation_id="test-convo-id", body="Original body"
        )
        expected_link = "@testuser can click here to [continue refining the PR](https://test.example.com/conversations/test-convo-id)"
        assert result == f"Original body\n\n{expected_link}"
        mock_service.get_user.assert_called_once()


@pytest.mark.asyncio
async def test_get_conversation_link_empty_body():
    """Test get_conversation_link with an empty body."""
    mock_service = AsyncMock(spec=GitService)
    mock_user = AsyncMock()
    mock_user.login = "testuser"
    mock_service.get_user.return_value = mock_user
    with patch("openhands.server.routes.mcp.server_config") as mock_config, patch(
        "openhands.server.routes.mcp.CONVERSATION_URL", "https://test.example.com/conversations/{}"
    ):
        mock_config.app_mode = AppMode.SAAS
        result = await get_conversation_link(service=mock_service, conversation_id="test-convo-id", body="")
        expected_link = "@testuser can click here to [continue refining the PR](https://test.example.com/conversations/test-convo-id)"
        assert result == f"\n\n{expected_link}"
        mock_service.get_user.assert_called_once()
