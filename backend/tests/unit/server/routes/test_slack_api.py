"""Unit tests for Slack API routes."""

import json
import uuid
from unittest.mock import MagicMock, patch

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from forge.core.config import AppConfig
from forge.server.routes.slack import app
from forge.storage.data_models.slack_integration import (
    SlackConversationLink,
    SlackOAuthState,
    SlackUserLink,
    SlackWorkspace,
)
from forge.storage.slack_store import SlackStore


@pytest.fixture
def test_client(tmp_path):
    """Create test client with temporary storage."""
    # Mock config
    with patch("forge.server.routes.slack.FORGE_config") as mock_config:
        mock_config.SLACK_CLIENT_ID = "test-client-id"
        mock_config.SLACK_CLIENT_SECRET = MagicMock(
            get_secret_value=lambda: "test-client-secret"
        )
        mock_config.SLACK_SIGNING_SECRET = MagicMock(
            get_secret_value=lambda: "test-signing-secret"
        )

        # Create temporary workspace
        workspace_dir = tmp_path / "workspace"
        workspace_dir.mkdir()

        # Mock AppConfig
        mock_app_config = AppConfig()
        mock_app_config.workspace_base = str(workspace_dir)

        slack_store = SlackStore(mock_app_config)
        with patch(
            "forge.server.routes.slack.get_slack_store",
            autospec=True,
            return_value=slack_store,
        ):
            fastapi_app = FastAPI()
            fastapi_app.include_router(app)
            with TestClient(fastapi_app) as client:
                yield client, slack_store


def test_slack_install_url_generation(test_client):
    """Test generating Slack OAuth install URL."""
    client, _ = test_client

    response = client.get("/install?user_id=user123&redirect_url=https://example.com")

    assert response.status_code in (200, 201)
    data = response.json()
    assert "url" in data
    assert "test-client-id" in data["url"]
    assert "state=" in data["url"]


def test_slack_install_without_config():
    """Test Slack install fails without configuration."""
    with patch("forge.server.routes.slack.FORGE_config") as mock_config:
        mock_config.SLACK_CLIENT_ID = None

        fastapi_app = FastAPI()
        fastapi_app.include_router(app)
        with TestClient(fastapi_app) as client:
            response = client.get("/install?user_id=user123")

        assert response.status_code == 501
        assert "not configured" in response.json()["detail"]


def test_slack_oauth_callback_invalid_state(test_client):
    """Test OAuth callback with invalid state."""
    client, _ = test_client

    response = client.get("/callback?code=test-code&state=invalid-state")

    assert response.status_code == 400
    assert "Invalid OAuth state" in response.text


def test_slack_oauth_callback_with_error(test_client):
    """Test OAuth callback with error parameter."""
    client, _ = test_client

    response = client.get("/callback?error=access_denied&state=test-state")

    assert response.status_code == 400
    assert "access_denied" in response.text


@patch("forge.server.routes.slack.SLACK_SDK_AVAILABLE", False)
def test_slack_oauth_callback_without_sdk(test_client):
    """Test OAuth callback without Slack SDK installed."""
    client, slack_store = test_client

    # Create valid state
    state = slack_store.generate_oauth_state("user123")

    response = client.get(f"/callback?code=test-code&state={state}")

    assert response.status_code == 501
    assert "Slack SDK not installed" in response.json()["detail"]


def test_slack_events_url_verification(test_client):
    """Test Slack URL verification challenge."""
    client, _ = test_client

    challenge_payload = {"type": "url_verification", "challenge": "test-challenge-123"}

    response = client.post("/events", json=challenge_payload)

    assert response.status_code == 200, response.json()
    data = response.json()
    assert data["challenge"] == "test-challenge-123"


def test_list_workspaces_empty(test_client):
    """Test listing workspaces when none exist."""
    client, _ = test_client

    response = client.get("/workspaces?user_id=user123")

    assert response.status_code == 200
    data = response.json()
    assert data["workspaces"] == []


def test_list_workspaces_with_data(test_client):
    """Test listing workspaces with existing data."""
    client, slack_store = test_client

    # Create test workspace
    workspace = SlackWorkspace(
        id="T123ABC",
        team_id="T123ABC",
        team_name="Test Workspace",
        bot_token="xoxb-test-token",
        bot_user_id="U123BOT",
        installed_by_user_id="user123",
    )
    slack_store.save_workspace(workspace)

    response = client.get("/workspaces?user_id=user123")

    assert response.status_code == 200
    data = response.json()
    assert len(data["workspaces"]) == 1
    assert data["workspaces"][0]["team_id"] == "T123ABC"
    assert data["workspaces"][0]["team_name"] == "Test Workspace"


def test_uninstall_workspace(test_client):
    """Test uninstalling a workspace."""
    client, slack_store = test_client

    # Create test workspace
    workspace = SlackWorkspace(
        id="T123ABC",
        team_id="T123ABC",
        team_name="Test Workspace",
        bot_token="xoxb-test-token",
        bot_user_id="U123BOT",
        installed_by_user_id="user123",
    )
    slack_store.save_workspace(workspace)

    response = client.delete("/workspaces/T123ABC?user_id=user123")

    assert response.status_code in (200, 204)

    # Verify workspace is deleted
    assert slack_store.get_workspace("T123ABC") is None


def test_uninstall_workspace_not_found(test_client):
    """Test uninstalling a non-existent workspace."""
    client, _ = test_client

    response = client.delete("/workspaces/T999NOTFOUND?user_id=user123")

    assert response.status_code == 404


def test_uninstall_workspace_wrong_user(test_client):
    """Test uninstalling a workspace by different user."""
    client, slack_store = test_client

    # Create test workspace owned by user123
    workspace = SlackWorkspace(
        id="T123ABC",
        team_id="T123ABC",
        team_name="Test Workspace",
        bot_token="xoxb-test-token",
        bot_user_id="U123BOT",
        installed_by_user_id="user123",
    )
    slack_store.save_workspace(workspace)

    # Try to delete as user456
    response = client.delete("/workspaces/T123ABC?user_id=user456")

    assert response.status_code == 404

    # Verify workspace still exists
    assert slack_store.get_workspace("T123ABC") is not None


def test_slack_store_operations(tmp_path):
    """Test SlackStore CRUD operations."""
    # Create temporary workspace
    workspace_dir = tmp_path / "workspace"
    workspace_dir.mkdir()

    mock_config = AppConfig()
    mock_config.workspace_base = str(workspace_dir)
    slack_store = SlackStore(mock_config)

    # Test workspace operations
    workspace = SlackWorkspace(
        id="T123",
        team_id="T123",
        team_name="Test Team",
        bot_token="xoxb-token",
        bot_user_id="U123",
        installed_by_user_id="user1",
    )
    slack_store.save_workspace(workspace)

    retrieved = slack_store.get_workspace("T123")
    assert retrieved is not None
    assert retrieved.team_name == "Test Team"

    # Test user link operations
    user_link = SlackUserLink(
        slack_user_id="U456",
        slack_workspace_id="T123",
        FORGE_user_id="user1",
        user_token="xoxp-user",
    )
    slack_store.save_user_link(user_link)

    retrieved_link = slack_store.get_user_link("T123", "U456")
    assert retrieved_link is not None
    assert retrieved_link.FORGE_user_id == "user1"

    # Test conversation link operations
    conv_link = SlackConversationLink(
        slack_channel_id="C789",
        slack_thread_ts="1234567890.123456",
        slack_workspace_id="T123",
        conversation_id=uuid.uuid4().hex,
        repository="owner/repo",
        created_by_slack_user_id="U456",
    )
    slack_store.save_conversation_link(conv_link)

    retrieved_conv = slack_store.get_conversation_link(
        "T123", "C789", "1234567890.123456"
    )
    assert retrieved_conv is not None
    assert retrieved_conv.slack_channel_id == "C789"


def test_oauth_state_lifecycle(tmp_path):
    """Test OAuth state generation and cleanup."""
    workspace_dir = tmp_path / "workspace"
    workspace_dir.mkdir()

    mock_config = AppConfig()
    mock_config.workspace_base = str(workspace_dir)
    slack_store = SlackStore(mock_config)

    # Generate state
    state = slack_store.generate_oauth_state("user123", "https://example.com")
    assert state is not None

    # Retrieve state
    oauth_state = slack_store.get_oauth_state(state)
    assert oauth_state is not None
    assert oauth_state.user_id == "user123"
    assert oauth_state.redirect_url == "https://example.com"

    # Delete state
    deleted = slack_store.delete_oauth_state(state)
    assert deleted is True

    # Verify deletion
    assert slack_store.get_oauth_state(state) is None
