"""Integration tests for Slack integration."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from fastapi.testclient import TestClient

from openhands.server.app import app
from openhands.storage.data_models.slack_integration import SlackWorkspace, SlackUserLink


class TestSlackIntegration:
    """Test suite for Slack integration functionality."""

    @pytest.fixture
    def test_client(self):
        """Create test client."""
        return TestClient(app)

    @pytest.fixture
    def mock_slack_store(self):
        """Create mock Slack store."""
        store = MagicMock()
        store.generate_oauth_state = MagicMock(return_value="test-state-123")
        store.get_oauth_state = MagicMock()
        store.save_workspace = MagicMock()
        store.get_workspace = MagicMock()
        store.delete_workspace = MagicMock()
        store.save_user_link = MagicMock()
        store.get_user_link = MagicMock()
        store.list_workspaces = MagicMock(return_value=[])
        return store

    def test_install_endpoint_requires_client_id(self, test_client):
        """Test that install endpoint requires SLACK_CLIENT_ID."""
        with patch("openhands.server.routes.slack.config") as mock_config:
            mock_config.SLACK_CLIENT_ID = None
            
            response = test_client.get("/api/slack/install?user_id=test-user")
            
            assert response.status_code == 501
            assert "not configured" in response.json()["detail"]

    def test_install_endpoint_returns_oauth_url(self, test_client, mock_slack_store):
        """Test that install endpoint returns valid OAuth URL."""
        with patch("openhands.server.routes.slack.config") as mock_config, \
             patch("openhands.server.routes.slack.get_slack_store", return_value=mock_slack_store):
            
            mock_config.SLACK_CLIENT_ID = "test-client-id"
            
            response = test_client.get("/api/slack/install?user_id=test-user")
            
            assert response.status_code == 200
            data = response.json()
            assert "url" in data
            assert "slack.com/oauth/v2/authorize" in data["url"]
            assert "client_id=test-client-id" in data["url"]

    def test_oauth_callback_validates_state(self, test_client, mock_slack_store):
        """Test that OAuth callback validates state."""
        mock_slack_store.get_oauth_state = MagicMock(return_value=None)
        
        with patch("openhands.server.routes.slack.get_slack_store", return_value=mock_slack_store):
            response = test_client.get("/api/slack/callback?code=test-code&state=invalid-state")
            
            assert response.status_code == 400

    @pytest.mark.integration
    def test_list_workspaces_filters_by_user(self, test_client, mock_slack_store):
        """Test that list workspaces filters by user ID."""
        mock_workspaces = [
            SlackWorkspace(
                id="W1",
                team_id="T1",
                team_name="Workspace 1",
                bot_token="xoxb-token1",
                bot_user_id="U1",
                installed_by_user_id="user-1",
            ),
            SlackWorkspace(
                id="W2",
                team_id="T2",
                team_name="Workspace 2",
                bot_token="xoxb-token2",
                bot_user_id="U2",
                installed_by_user_id="user-2",
            ),
        ]
        mock_slack_store.list_workspaces = MagicMock(return_value=mock_workspaces)
        
        with patch("openhands.server.routes.slack.get_slack_store", return_value=mock_slack_store):
            response = test_client.get("/api/slack/workspaces?user_id=user-1")
            
            assert response.status_code == 200
            data = response.json()
            # The endpoint filters by user_id, so we should only get user-1's workspaces
            assert len(data["workspaces"]) == 1
            assert data["workspaces"][0]["team_id"] == "T1"

    def test_uninstall_workspace_requires_ownership(self, test_client, mock_slack_store):
        """Test that uninstall requires user to own the workspace."""
        mock_workspace = SlackWorkspace(
            id="W1",
            team_id="T1",
            team_name="Workspace 1",
            bot_token="xoxb-token",
            bot_user_id="U1",
            installed_by_user_id="owner-user",
        )
        mock_slack_store.get_workspace = MagicMock(return_value=mock_workspace)
        
        with patch("openhands.server.routes.slack.get_slack_store", return_value=mock_slack_store):
            response = test_client.delete("/api/slack/workspaces/T1?user_id=different-user")
            
            assert response.status_code == 404

    def test_uninstall_workspace_succeeds_for_owner(self, test_client, mock_slack_store):
        """Test that uninstall succeeds for workspace owner."""
        mock_workspace = SlackWorkspace(
            id="W1",
            team_id="T1",
            team_name="Workspace 1",
            bot_token="xoxb-token",
            bot_user_id="U1",
            installed_by_user_id="owner-user",
        )
        mock_slack_store.get_workspace = MagicMock(return_value=mock_workspace)
        
        with patch("openhands.server.routes.slack.get_slack_store", return_value=mock_slack_store):
            response = test_client.delete("/api/slack/workspaces/T1?user_id=owner-user")
            
            assert response.status_code == 200
            assert response.json()["ok"] is True
            mock_slack_store.delete_workspace.assert_called_once_with("T1")

    def test_events_endpoint_handles_url_verification(self, test_client):
        """Test that events endpoint handles Slack URL verification challenge."""
        challenge_body = {
            "type": "url_verification",
            "challenge": "test-challenge-12345",
        }
        
        response = test_client.post("/api/slack/events", json=challenge_body)
        
        assert response.status_code == 200
        assert response.json()["challenge"] == "test-challenge-12345"

    def test_events_endpoint_verifies_signature(self, test_client, mock_slack_store):
        """Test that events endpoint verifies Slack signature."""
        event_body = {
            "type": "event_callback",
            "event": {"type": "app_mention", "text": "test"},
        }
        
        with patch("openhands.server.routes.slack.get_slack_store", return_value=mock_slack_store), \
             patch("openhands.server.routes.slack.verify_slack_signature", return_value=False):
            
            response = test_client.post("/api/slack/events", json=event_body)
            
            assert response.status_code == 401

    def test_cleanup_endpoint_removes_listener(self, test_client):
        """Test that cleanup endpoint removes event listener."""
        from openhands.server.routes.slack import _slack_event_listeners
        
        # Add a test listener
        _slack_event_listeners["test-conv-id"] = (MagicMock(), "C123", "123.456")
        
        response = test_client.post("/api/slack/cleanup/test-conv-id")
        
        assert response.status_code == 200
        assert "test-conv-id" not in _slack_event_listeners

