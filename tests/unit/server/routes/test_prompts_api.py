"""Unit tests for prompts API routes."""

import os
from unittest.mock import AsyncMock, MagicMock, patch
import pytest
from fastapi import Request
from fastapi.testclient import TestClient
from pydantic import SecretStr
from forge.integrations.provider import ProviderToken, ProviderType
from forge.server.app import app
from forge.server.user_auth.user_auth import UserAuth
from forge.storage.data_models.user_secrets import UserSecrets
from forge.storage.memory import InMemoryFileStore
from forge.storage.secrets.secrets_store import SecretsStore
from forge.storage.settings.file_settings_store import FileSettingsStore
from forge.storage.settings.settings_store import SettingsStore


class MockUserAuth(UserAuth):
    """Mock implementation of UserAuth for testing."""

    def __init__(self):
        self._settings = None
        self._settings_store = MagicMock()
        self._settings_store.load = AsyncMock(return_value=None)
        self._settings_store.store = AsyncMock()

    async def get_user_id(self) -> str | None:
        return "test-user"

    async def get_user_email(self) -> str | None:
        return "test@example.com"

    async def get_access_token(self) -> SecretStr | None:
        return SecretStr("test-token")

    async def get_provider_tokens(self) -> dict[ProviderType, ProviderToken] | None:
        return None

    async def get_user_settings_store(self) -> SettingsStore | None:
        return self._settings_store

    async def get_secrets_store(self) -> SecretsStore | None:
        return None

    async def get_user_secrets(self) -> UserSecrets | None:
        return None

    @classmethod
    async def get_instance(cls, request: Request) -> UserAuth:
        return MockUserAuth()


@pytest.fixture
def test_client(tmp_path):
    # Set up workspace directory
    workspace_dir = str(tmp_path / "workspace")
    os.makedirs(workspace_dir, exist_ok=True)
    
    with patch.dict(os.environ, {
        "SESSION_API_KEY": "",
        "CSRF_PROTECTION_ENABLED": "false",  # Disable CSRF for tests
        "RATE_LIMITING_ENABLED": "false",  # Disable rate limiting for tests
    }, clear=False), patch(
        "forge.server.dependencies._SESSION_API_KEY", None
    ), patch(
        "forge.server.user_auth.user_auth.UserAuth.get_instance",
        return_value=MockUserAuth(),
    ), patch(
        "forge.storage.settings.file_settings_store.FileSettingsStore.get_instance",
        AsyncMock(return_value=FileSettingsStore(InMemoryFileStore())),
    ), patch(
        "forge.server.shared.config.workspace_base", workspace_dir
    ):
        yield TestClient(app)


@pytest.mark.asyncio
async def test_create_prompt(test_client):
    """Test creating a new prompt."""
    prompt_data = {
        "title": "Test Prompt",
        "content": "This is a test prompt: {{variable1}}",
        "description": "Test description",
        "category": "coding",
        "variables": [{"name": "variable1", "description": "Test variable", "required": True}],
        "tags": ["test", "example"],
    }

    response = test_client.post("/api/prompts/", json=prompt_data)
    assert response.status_code in [200, 201]  # Accept both OK and Created
    data = response.json()
    assert data["title"] == "Test Prompt"
    assert data["category"] == "coding"
    assert len(data["tags"]) == 2
    assert "id" in data


@pytest.mark.asyncio
async def test_list_prompts(test_client):
    """Test listing prompts."""
    # Create a prompt first
    prompt_data = {
        "title": "List Test Prompt",
        "content": "Test content",
        "category": "coding",
    }
    test_client.post("/api/prompts/", json=prompt_data)

    # List prompts
    response = test_client.get("/api/prompts/")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)


@pytest.mark.asyncio
async def test_get_prompt(test_client):
    """Test getting a specific prompt."""
    # Create a prompt
    prompt_data = {"title": "Get Test", "content": "Test", "category": "coding"}
    create_response = test_client.post("/api/prompts/", json=prompt_data)
    prompt_id = create_response.json()["id"]

    # Get the prompt
    response = test_client.get(f"/api/prompts/{prompt_id}")
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == prompt_id
    assert data["title"] == "Get Test"


@pytest.mark.asyncio
async def test_update_prompt(test_client):
    """Test updating a prompt."""
    # Create a prompt
    prompt_data = {"title": "Update Test", "content": "Original", "category": "coding"}
    create_response = test_client.post("/api/prompts/", json=prompt_data)
    prompt_id = create_response.json()["id"]

    # Update the prompt
    update_data = {"title": "Updated Title", "content": "Updated content"}
    response = test_client.patch(f"/api/prompts/{prompt_id}", json=update_data)
    assert response.status_code == 200
    data = response.json()
    assert data["title"] == "Updated Title"
    assert data["content"] == "Updated content"


@pytest.mark.asyncio
async def test_delete_prompt(test_client):
    """Test deleting a prompt."""
    # Create a prompt
    prompt_data = {"title": "Delete Test", "content": "Test", "category": "coding"}
    create_response = test_client.post("/api/prompts/", json=prompt_data)
    prompt_id = create_response.json()["id"]

    # Delete the prompt
    response = test_client.delete(f"/api/prompts/{prompt_id}")
    assert response.status_code == 204  # 204 No Content for successful deletion

    # Verify it's deleted
    get_response = test_client.get(f"/api/prompts/{prompt_id}")
    assert get_response.status_code == 404


@pytest.mark.asyncio
async def test_search_prompts(test_client):
    """Test searching prompts."""
    # Create test prompts
    test_client.post(
        "/api/prompts/",
        json={"title": "Python Debugging", "content": "Debug code", "category": "debugging"},
    )
    test_client.post(
        "/api/prompts/",
        json={
            "title": "Code Review",
            "content": "Review code",
            "category": "code_review",
        },
    )

    # Search for "debug" using POST /api/prompts/search endpoint
    response = test_client.post("/api/prompts/search", json={"query": "debug", "limit": 100, "offset": 0})
    assert response.status_code == 200
    data = response.json()
    assert len(data) >= 1
    assert any("Debug" in p["title"] for p in data)


@pytest.mark.asyncio
async def test_toggle_favorite_prompt(test_client):
    """Test toggling prompt favorite status using PATCH."""
    # Create a prompt
    prompt_data = {"title": "Favorite Test", "content": "Test", "category": "coding"}
    create_response = test_client.post("/api/prompts/", json=prompt_data)
    prompt_id = create_response.json()["id"]

    # Set favorite to true
    response = test_client.patch(f"/api/prompts/{prompt_id}", json={"is_favorite": True})
    assert response.status_code == 200
    data = response.json()
    assert data["is_favorite"] is True

    # Set favorite to false
    response = test_client.patch(f"/api/prompts/{prompt_id}", json={"is_favorite": False})
    assert response.status_code == 200
    data = response.json()
    assert data["is_favorite"] is False


@pytest.mark.asyncio
async def test_export_import_prompts(test_client):
    """Test exporting and importing prompts."""
    # Create prompts
    test_client.post(
        "/api/prompts/",
        json={"title": "Export Test 1", "content": "Content 1", "category": "coding"},
    )
    test_client.post(
        "/api/prompts/",
        json={"title": "Export Test 2", "content": "Content 2", "category": "debugging"},
    )

    # Export
    response = test_client.get("/api/prompts/export")
    assert response.status_code == 200
    export_data = response.json()
    assert "prompts" in export_data
    assert len(export_data["prompts"]) >= 2

    # Import
    import_response = test_client.post("/api/prompts/import", json=export_data)
    assert import_response.status_code == 200
    result = import_response.json()
    assert "imported" in result or "updated" in result


@pytest.mark.asyncio
async def test_get_prompt_stats(test_client):
    """Test getting prompt statistics."""
    # Create some prompts
    test_client.post(
        "/api/prompts/",
        json={"title": "Stats Test 1", "content": "Content 1", "category": "coding", "is_favorite": True},
    )
    test_client.post(
        "/api/prompts/",
        json={"title": "Stats Test 2", "content": "Content 2", "category": "coding"},
    )
    test_client.post(
        "/api/prompts/",
        json={"title": "Stats Test 3", "content": "Content 3", "category": "debugging"},
    )

    # Get stats
    response = test_client.get("/api/prompts/stats")
    assert response.status_code == 200
    stats = response.json()
    assert "total_prompts" in stats
    assert "prompts_by_category" in stats
    assert "total_favorites" in stats
    assert "total_tags" in stats
    assert stats["total_prompts"] >= 3
    assert stats["total_favorites"] >= 1


@pytest.mark.asyncio
async def test_render_prompt_with_variables(test_client):
    """Test rendering a prompt with variables."""
    # Create a prompt with variables
    prompt_data = {
        "title": "Render Test",
        "content": "Hello {{name}}, your task is: {{task}}",
        "category": "coding",
        "variables": [
            {"name": "name", "description": "User name", "required": True},
            {"name": "task", "description": "Task description", "required": True}
        ]
    }
    create_response = test_client.post("/api/prompts/", json=prompt_data)
    prompt_id = create_response.json()["id"]

    # Render the prompt with variables
    render_data = {
        "prompt_id": prompt_id,
        "variables": {
            "name": "Alice",
            "task": "Write a Python function"
        }
    }
    response = test_client.post("/api/prompts/render", json=render_data)
    assert response.status_code == 200
    result = response.json()
    assert "rendered" in result
    assert "Alice" in result["rendered"]
    assert "Write a Python function" in result["rendered"]


@pytest.mark.asyncio
async def test_track_prompt_usage(test_client):
    """Test tracking prompt usage."""
    # Create a prompt
    prompt_data = {"title": "Usage Test", "content": "Test content", "category": "coding"}
    create_response = test_client.post("/api/prompts/", json=prompt_data)
    prompt_id = create_response.json()["id"]
    initial_usage = create_response.json()["usage_count"]

    # Track usage
    response = test_client.post(f"/api/prompts/{prompt_id}/use")
    assert response.status_code == 200
    data = response.json()
    assert data["usage_count"] == initial_usage + 1

    # Track usage again
    response = test_client.post(f"/api/prompts/{prompt_id}/use")
    assert response.status_code == 200
    data = response.json()
    assert data["usage_count"] == initial_usage + 2

