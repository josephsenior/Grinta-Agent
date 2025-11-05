"""Tests for the custom secrets API endpoints."""

import os
from unittest.mock import AsyncMock, patch
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from pydantic import SecretStr
from openhands.integrations.provider import CustomSecret, ProviderToken, ProviderType
from openhands.server.routes.secrets import app as secrets_app
from openhands.storage import get_file_store
from openhands.storage.data_models.user_secrets import UserSecrets
from openhands.storage.secrets.file_secrets_store import FileSecretsStore


@pytest.fixture
def test_client():
    """Create a test client for the settings API."""
    app = FastAPI()
    app.include_router(secrets_app)
    with patch.dict(os.environ, {"SESSION_API_KEY": ""}, clear=False):
        with patch("openhands.server.dependencies._SESSION_API_KEY", None):
            yield TestClient(app)


@pytest.fixture
def temp_dir(tmp_path_factory: pytest.TempPathFactory) -> str:
    return str(tmp_path_factory.mktemp("secrets_store"))


@pytest.fixture
def file_secrets_store(temp_dir):
    file_store = get_file_store("local", temp_dir)
    store = FileSecretsStore(file_store)
    with patch(
        "openhands.storage.secrets.file_secrets_store.FileSecretsStore.get_instance", AsyncMock(return_value=store)
    ):
        yield store


@pytest.mark.asyncio
async def test_load_custom_secrets_names(test_client, file_secrets_store):
    """Test loading custom secrets names."""
    custom_secrets = {
        "API_KEY": CustomSecret(secret=SecretStr("api-key-value")),
        "DB_PASSWORD": CustomSecret(secret=SecretStr("db-password-value")),
    }
    provider_tokens = {ProviderType.GITHUB: ProviderToken(token=SecretStr("github-token"))}
    user_secrets = UserSecrets(custom_secrets=custom_secrets, provider_tokens=provider_tokens)
    await file_secrets_store.store(user_secrets)
    response = test_client.get("/api/secrets")
    print(response)
    assert response.status_code == 200
    data = response.json()
    assert "custom_secrets" in data
    secret_names = [secret["name"] for secret in data["custom_secrets"]]
    assert sorted(secret_names) == ["API_KEY", "DB_PASSWORD"]
    stored_settings = await file_secrets_store.load()
    assert stored_settings.custom_secrets["API_KEY"].secret.get_secret_value() == "api-key-value"
    assert stored_settings.custom_secrets["DB_PASSWORD"].secret.get_secret_value() == "db-password-value"
    assert ProviderType.GITHUB in stored_settings.provider_tokens


@pytest.mark.asyncio
async def test_load_custom_secrets_names_empty(test_client, file_secrets_store):
    """Test loading custom secrets names when there are no custom secrets."""
    provider_tokens = {ProviderType.GITHUB: ProviderToken(token=SecretStr("github-token"))}
    user_secrets = UserSecrets(provider_tokens=provider_tokens, custom_secrets={})
    await file_secrets_store.store(user_secrets)
    response = test_client.get("/api/secrets")
    assert response.status_code == 200
    data = response.json()
    assert "custom_secrets" in data
    assert data["custom_secrets"] == []


@pytest.mark.asyncio
async def test_add_custom_secret(test_client, file_secrets_store):
    """Test adding a new custom secret."""
    provider_tokens = {ProviderType.GITHUB: ProviderToken(token=SecretStr("github-token"))}
    user_secrets = UserSecrets(provider_tokens=provider_tokens)
    await file_secrets_store.store(user_secrets)
    add_secret_data = {"name": "API_KEY", "value": "api-key-value", "description": None}
    response = test_client.post("/api/secrets", json=add_secret_data)
    assert response.status_code == 201
    stored_settings = await file_secrets_store.load()
    assert "API_KEY" in stored_settings.custom_secrets
    assert stored_settings.custom_secrets["API_KEY"].secret.get_secret_value() == "api-key-value"


@pytest.mark.asyncio
async def test_create_custom_secret_with_no_existing_secrets(test_client, file_secrets_store):
    """Test creating a custom secret when there are no existing secrets at all."""
    add_secret_data = {"name": "NEW_API_KEY", "value": "new-api-key-value", "description": "Test API Key"}
    response = test_client.post("/api/secrets", json=add_secret_data)
    assert response.status_code == 201
    stored_settings = await file_secrets_store.load()
    assert "NEW_API_KEY" in stored_settings.custom_secrets
    assert stored_settings.custom_secrets["NEW_API_KEY"].secret.get_secret_value() == "new-api-key-value"
    assert stored_settings.custom_secrets["NEW_API_KEY"].description == "Test API Key"
    assert stored_settings.provider_tokens == {}


@pytest.mark.asyncio
async def test_update_existing_custom_secret(test_client, file_secrets_store):
    """Test updating an existing custom secret's name and description (cannot change value once set)."""
    custom_secrets = {"API_KEY": CustomSecret(secret=SecretStr("old-api-key"))}
    provider_tokens = {ProviderType.GITHUB: ProviderToken(token=SecretStr("github-token"))}
    user_secrets = UserSecrets(custom_secrets=custom_secrets, provider_tokens=provider_tokens)
    await file_secrets_store.store(user_secrets)
    update_secret_data = {"name": "API_KEY", "description": None}
    response = test_client.put("/api/secrets/API_KEY", json=update_secret_data)
    assert response.status_code == 200
    stored_settings = await file_secrets_store.load()
    assert "API_KEY" in stored_settings.custom_secrets
    assert stored_settings.custom_secrets["API_KEY"].secret.get_secret_value() == "old-api-key"
    assert ProviderType.GITHUB in stored_settings.provider_tokens


@pytest.mark.asyncio
async def test_add_multiple_custom_secrets(test_client, file_secrets_store):
    """Test adding multiple custom secrets at once."""
    custom_secrets = {"EXISTING_SECRET": CustomSecret(secret=SecretStr("existing-value"))}
    provider_tokens = {ProviderType.GITHUB: ProviderToken(token=SecretStr("github-token"))}
    user_secrets = UserSecrets(custom_secrets=custom_secrets, provider_tokens=provider_tokens)
    await file_secrets_store.store(user_secrets)
    add_secret_data1 = {"name": "API_KEY", "value": "api-key-value", "description": None}
    response1 = test_client.post("/api/secrets", json=add_secret_data1)
    assert response1.status_code == 201
    add_secret_data2 = {"name": "DB_PASSWORD", "value": "db-password-value", "description": None}
    response = test_client.post("/api/secrets", json=add_secret_data2)
    assert response.status_code == 201
    stored_settings = await file_secrets_store.load()
    assert "API_KEY" in stored_settings.custom_secrets
    assert stored_settings.custom_secrets["API_KEY"].secret.get_secret_value() == "api-key-value"
    assert "DB_PASSWORD" in stored_settings.custom_secrets
    assert stored_settings.custom_secrets["DB_PASSWORD"].secret.get_secret_value() == "db-password-value"
    assert "EXISTING_SECRET" in stored_settings.custom_secrets
    assert stored_settings.custom_secrets["EXISTING_SECRET"].secret.get_secret_value() == "existing-value"
    assert ProviderType.GITHUB in stored_settings.provider_tokens


@pytest.mark.asyncio
async def test_delete_custom_secret(test_client, file_secrets_store):
    """Test deleting a custom secret."""
    custom_secrets = {
        "API_KEY": CustomSecret(secret=SecretStr("api-key-value")),
        "DB_PASSWORD": CustomSecret(secret=SecretStr("db-password-value")),
    }
    provider_tokens = {ProviderType.GITHUB: ProviderToken(token=SecretStr("github-token"))}
    user_secrets = UserSecrets(custom_secrets=custom_secrets, provider_tokens=provider_tokens)
    await file_secrets_store.store(user_secrets)
    response = test_client.delete("/api/secrets/API_KEY")
    assert response.status_code == 200
    stored_settings = await file_secrets_store.load()
    assert "API_KEY" not in stored_settings.custom_secrets
    assert "DB_PASSWORD" in stored_settings.custom_secrets
    assert stored_settings.custom_secrets["DB_PASSWORD"].secret.get_secret_value() == "db-password-value"
    assert ProviderType.GITHUB in stored_settings.provider_tokens


@pytest.mark.asyncio
async def test_delete_nonexistent_custom_secret(test_client, file_secrets_store):
    """Test deleting a custom secret that doesn't exist."""
    custom_secrets = {"API_KEY": CustomSecret(secret=SecretStr("api-key-value"), description="")}
    provider_tokens = {ProviderType.GITHUB: ProviderToken(token=SecretStr("github-token"))}
    user_secrets = UserSecrets(custom_secrets=custom_secrets, provider_tokens=provider_tokens)
    await file_secrets_store.store(user_secrets)
    response = test_client.delete("/api/secrets/NONEXISTENT_KEY")
    assert response.status_code == 404
    stored_settings = await file_secrets_store.load()
    assert "API_KEY" in stored_settings.custom_secrets
    assert stored_settings.custom_secrets["API_KEY"].secret.get_secret_value() == "api-key-value"
    assert ProviderType.GITHUB in stored_settings.provider_tokens


@pytest.mark.asyncio
async def test_add_git_providers_with_host(test_client, file_secrets_store):
    """Test adding git providers with host parameter."""
    provider_tokens = {ProviderType.GITHUB: ProviderToken(token=SecretStr("github-token"))}
    user_secrets = UserSecrets(provider_tokens=provider_tokens)
    await file_secrets_store.store(user_secrets)
    with patch("openhands.server.routes.secrets.check_provider_tokens", AsyncMock(return_value="")):
        add_provider_data = {
            "provider_tokens": {"github": {"token": "new-github-token", "host": "github.enterprise.com"}}
        }
        response = test_client.post("/api/add-git-providers", json=add_provider_data)
        assert response.status_code == 200
        stored_secrets = await file_secrets_store.load()
        assert ProviderType.GITHUB in stored_secrets.provider_tokens
        assert stored_secrets.provider_tokens[ProviderType.GITHUB].token.get_secret_value() == "new-github-token"
        assert stored_secrets.provider_tokens[ProviderType.GITHUB].host == "github.enterprise.com"


@pytest.mark.asyncio
async def test_add_git_providers_update_host_only(test_client, file_secrets_store):
    """Test updating only the host for an existing provider token."""
    provider_tokens = {ProviderType.GITHUB: ProviderToken(token=SecretStr("github-token"), host="github.com")}
    user_secrets = UserSecrets(provider_tokens=provider_tokens)
    await file_secrets_store.store(user_secrets)
    with patch("openhands.server.routes.secrets.check_provider_tokens", AsyncMock(return_value="")):
        update_host_data = {"provider_tokens": {"github": {"token": "", "host": "github.enterprise.com"}}}
        response = test_client.post("/api/add-git-providers", json=update_host_data)
        assert response.status_code == 200
        stored_secrets = await file_secrets_store.load()
        assert ProviderType.GITHUB in stored_secrets.provider_tokens
        assert stored_secrets.provider_tokens[ProviderType.GITHUB].token.get_secret_value() == "github-token"
        assert stored_secrets.provider_tokens[ProviderType.GITHUB].host == "github.enterprise.com"


@pytest.mark.asyncio
async def test_add_git_providers_invalid_token_with_host(test_client, file_secrets_store):
    """Test adding an invalid token with a host."""
    user_secrets = UserSecrets()
    await file_secrets_store.store(user_secrets)
    with patch("openhands.integrations.utils.validate_provider_token", AsyncMock(return_value=None)):
        add_provider_data = {"provider_tokens": {"github": {"token": "invalid-token", "host": "github.enterprise.com"}}}
        response = test_client.post("/api/add-git-providers", json=add_provider_data)
        assert response.status_code == 401
        assert "Invalid token" in response.json()["error"]


@pytest.mark.asyncio
async def test_add_multiple_git_providers_with_hosts(test_client, file_secrets_store):
    """Test adding multiple git providers with different hosts."""
    user_secrets = UserSecrets()
    await file_secrets_store.store(user_secrets)
    with patch("openhands.server.routes.secrets.check_provider_tokens", AsyncMock(return_value="")):
        add_providers_data = {
            "provider_tokens": {
                "github": {"token": "github-token", "host": "github.enterprise.com"},
                "gitlab": {"token": "gitlab-token", "host": "gitlab.enterprise.com"},
            }
        }
        response = test_client.post("/api/add-git-providers", json=add_providers_data)
        assert response.status_code == 200
        stored_secrets = await file_secrets_store.load()
        assert ProviderType.GITHUB in stored_secrets.provider_tokens
        assert stored_secrets.provider_tokens[ProviderType.GITHUB].token.get_secret_value() == "github-token"
        assert stored_secrets.provider_tokens[ProviderType.GITHUB].host == "github.enterprise.com"
        assert ProviderType.GITLAB in stored_secrets.provider_tokens
        assert stored_secrets.provider_tokens[ProviderType.GITLAB].token.get_secret_value() == "gitlab-token"
        assert stored_secrets.provider_tokens[ProviderType.GITLAB].host == "gitlab.enterprise.com"
