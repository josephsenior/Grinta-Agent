from unittest.mock import AsyncMock, patch
import pytest
from forge.server.listen_socket import forge_action, forge_user_action


@pytest.mark.asyncio
async def test_forge_user_action():
    """Test that forge_user_action correctly forwards data to the conversation manager."""
    connection_id = "test_connection_id"
    test_data = {"action": "test_action", "data": "test_data"}
    with patch("forge.server.listen_socket.conversation_manager") as mock_manager:
        mock_manager.send_to_event_stream = AsyncMock()
        await forge_user_action(connection_id, test_data)
        mock_manager.send_to_event_stream.assert_called_once_with(
            connection_id, test_data
        )


@pytest.mark.asyncio
async def test_forge_action():
    """Test that forge_action (legacy handler) correctly forwards data to the conversation manager."""
    connection_id = "test_connection_id"
    test_data = {"action": "test_action", "data": "test_data"}
    with patch("forge.server.listen_socket.conversation_manager") as mock_manager:
        mock_manager.send_to_event_stream = AsyncMock()
        await forge_action(connection_id, test_data)
        mock_manager.send_to_event_stream.assert_called_once_with(
            connection_id, test_data
        )
