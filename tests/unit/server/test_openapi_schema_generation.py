import json
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
        return "test-email@whatever.com"

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
def test_client():
    with patch("forge.server.user_auth.user_auth.UserAuth.get_instance", return_value=MockUserAuth()), patch(
        "forge.storage.settings.file_settings_store.FileSettingsStore.get_instance",
        AsyncMock(return_value=FileSettingsStore(InMemoryFileStore())),
    ):
        yield TestClient(app)


@pytest.mark.asyncio
async def test_openapi_schema_generation(test_client):
    """Test that the OpenAPI schema can be generated without errors.

    This test ensures that the FastAPI app can generate a valid OpenAPI schema,
    which is important for API documentation and client generation.
    """
    response = test_client.get("/openapi.json")
    assert response.status_code == 200
    schema = response.json()
    assert "openapi" in schema
    assert "info" in schema
    assert "paths" in schema
    json_str = json.dumps(schema)
    assert json_str is not None
    assert "/api/settings" in schema["paths"]
    assert "/health" in schema["paths"]
