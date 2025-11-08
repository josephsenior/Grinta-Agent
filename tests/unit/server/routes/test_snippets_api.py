"""Unit tests for snippets API routes."""

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
    
    with patch.dict(os.environ, {"SESSION_API_KEY": ""}, clear=False), patch(
        "forge.server.dependencies._SESSION_API_KEY", None
    ), patch(
        "forge.server.user_auth.user_auth.UserAuth.get_instance",
        return_value=MockUserAuth(),
    ), patch(
        "forge.storage.settings.file_settings_store.FileSettingsStore.get_instance",
        AsyncMock(return_value=FileSettingsStore(InMemoryFileStore())),
    ), patch(
        "forge.core.config.AppConfig.workspace_base", workspace_dir
    ):
        yield TestClient(app)


@pytest.mark.asyncio
async def test_create_snippet(test_client):
    """Test creating a new code snippet."""
    snippet_data = {
        "title": "Test Snippet",
        "code": 'def hello():\n    print("Hello, World!")',
        "language": "python",
        "description": "A simple test snippet",
        "category": "utility",
        "tags": ["test", "python"],
    }

    response = test_client.post("/api/snippets/", json=snippet_data)
    assert response.status_code in [200, 201]  # Accept both OK and Created
    data = response.json()
    assert data["title"] == "Test Snippet"
    assert data["language"] == "python"
    assert "id" in data


@pytest.mark.asyncio
async def test_list_snippets(test_client):
    """Test listing snippets."""
    # Create a snippet
    snippet_data = {
        "title": "List Test",
        "code": "console.log('test');",
        "language": "javascript",
        "category": "utility",
    }
    test_client.post("/api/snippets/", json=snippet_data)

    # List snippets
    response = test_client.get("/api/snippets/")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)


@pytest.mark.asyncio
async def test_filter_snippets_by_language(test_client):
    """Test filtering snippets by language."""
    # Create snippets in different languages
    test_client.post(
        "/api/snippets/",
        json={"title": "Python Snippet", "code": "print('hi')", "language": "python"},
    )
    test_client.post(
        "/api/snippets/",
        json={"title": "JS Snippet", "code": "console.log('hi')", "language": "javascript"},
    )

    # Filter by Python
    response = test_client.get("/api/snippets/?language=python")
    assert response.status_code == 200
    data = response.json()
    assert all(s["language"] == "python" for s in data)


@pytest.mark.asyncio
async def test_update_snippet(test_client):
    """Test updating a snippet."""
    # Create snippet
    snippet_data = {
        "title": "Update Test",
        "code": "original code",
        "language": "python",
    }
    create_response = test_client.post("/api/snippets/", json=snippet_data)
    snippet_id = create_response.json()["id"]

    # Update
    update_data = {"title": "Updated Title", "code": "updated code"}
    response = test_client.patch(f"/api/snippets/{snippet_id}", json=update_data)
    assert response.status_code == 200
    data = response.json()
    assert data["title"] == "Updated Title"
    assert data["code"] == "updated code"


@pytest.mark.asyncio
async def test_delete_snippet(test_client):
    """Test deleting a snippet."""
    # Create snippet
    snippet_data = {"title": "Delete Test", "code": "code", "language": "python"}
    create_response = test_client.post("/api/snippets/", json=snippet_data)
    snippet_id = create_response.json()["id"]

    # Delete
    response = test_client.delete(f"/api/snippets/{snippet_id}")
    assert response.status_code in [200, 204]  # Accept OK or No Content

    # Verify deleted
    get_response = test_client.get(f"/api/snippets/{snippet_id}")
    assert get_response.status_code == 404


@pytest.mark.asyncio
async def test_track_snippet_usage(test_client):
    """Test tracking snippet usage."""
    # Create snippet
    snippet_data = {"title": "Usage Test", "code": "code", "language": "python"}
    create_response = test_client.post("/api/snippets/", json=snippet_data)
    snippet_id = create_response.json()["id"]

    # Track usage
    response = test_client.post(f"/api/snippets/{snippet_id}/use")
    assert response.status_code == 200

    # Get snippet and verify usage count increased
    get_response = test_client.get(f"/api/snippets/{snippet_id}")
    data = get_response.json()
    assert data["usage_count"] >= 1


@pytest.mark.asyncio
async def test_export_import_snippets(test_client):
    """Test exporting and importing snippets."""
    # Create snippets
    test_client.post(
        "/api/snippets/",
        json={"title": "Export 1", "code": "code1", "language": "python"},
    )
    test_client.post(
        "/api/snippets/",
        json={"title": "Export 2", "code": "code2", "language": "javascript"},
    )

    # Export
    response = test_client.get("/api/snippets/export")
    assert response.status_code == 200
    export_data = response.json()
    assert "snippets" in export_data
    assert len(export_data["snippets"]) >= 2

    # Import
    import_response = test_client.post("/api/snippets/import", json=export_data)
    assert import_response.status_code == 200
    result = import_response.json()
    assert "total" in result

