import os
from unittest.mock import AsyncMock, MagicMock, patch
import pytest
from fastapi.testclient import TestClient
from pydantic import SecretStr
from openhands.integrations.provider import ProviderToken
from openhands.integrations.service_types import ProviderType
from openhands.server.routes.secrets import app, check_provider_tokens
from openhands.server.routes.settings import store_llm_settings
from openhands.server.settings import POSTProviderModel
from openhands.storage import get_file_store
from openhands.storage.data_models.settings import Settings
from openhands.storage.data_models.user_secrets import UserSecrets
from openhands.storage.secrets.file_secrets_store import FileSecretsStore


async def get_settings_store(request):
    """Mock function to get settings store."""
    return MagicMock()


@pytest.fixture
def test_client():
    with patch.dict(os.environ, {"SESSION_API_KEY": ""}, clear=False), patch(
        "openhands.server.dependencies._SESSION_API_KEY", None
    ), patch("openhands.server.routes.secrets.check_provider_tokens", AsyncMock(return_value="")):
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
async def test_check_provider_tokens_valid():
    """Test check_provider_tokens with valid tokens."""
    provider_token = ProviderToken(token=SecretStr("valid-token"))
    providers = POSTProviderModel(provider_tokens={ProviderType.GITHUB: provider_token})
    existing_provider_tokens = {}
    with patch("openhands.server.routes.secrets.validate_provider_token") as mock_validate:
        mock_validate.return_value = ProviderType.GITHUB
        result = await check_provider_tokens(providers, existing_provider_tokens)
        assert result == ""
        mock_validate.assert_called_once()


@pytest.mark.asyncio
async def test_check_provider_tokens_invalid():
    """Test check_provider_tokens with invalid tokens."""
    provider_token = ProviderToken(token=SecretStr("invalid-token"))
    providers = POSTProviderModel(provider_tokens={ProviderType.GITHUB: provider_token})
    existing_provider_tokens = {}
    with patch("openhands.server.routes.secrets.validate_provider_token") as mock_validate:
        mock_validate.return_value = None
        result = await check_provider_tokens(providers, existing_provider_tokens)
        assert "Invalid token" in result
        mock_validate.assert_called_once()


@pytest.mark.asyncio
async def test_check_provider_tokens_wrong_type():
    """Test check_provider_tokens with unsupported provider type."""
    providers = POSTProviderModel(provider_tokens={})
    existing_provider_tokens = {}
    result = await check_provider_tokens(providers, existing_provider_tokens)
    assert result == ""


@pytest.mark.asyncio
async def test_check_provider_tokens_no_tokens():
    """Test check_provider_tokens with no tokens."""
    providers = POSTProviderModel(provider_tokens={})
    existing_provider_tokens = {}
    result = await check_provider_tokens(providers, existing_provider_tokens)
    assert result == ""


@pytest.mark.asyncio
async def test_store_llm_settings_new_settings():
    """Test store_llm_settings with new settings."""
    settings = Settings(llm_model="gpt-4", llm_api_key="test-api-key", llm_base_url="https://api.example.com")
    mock_store = MagicMock()
    mock_store.load = AsyncMock(return_value=None)
    result = await store_llm_settings(settings, mock_store)
    assert result.llm_model == "gpt-4"
    assert result.llm_api_key.get_secret_value() == "test-api-key"
    assert result.llm_base_url == "https://api.example.com"


@pytest.mark.asyncio
async def test_store_llm_settings_update_existing():
    """Test store_llm_settings updates existing settings."""
    settings = Settings(llm_model="gpt-4", llm_api_key="new-api-key", llm_base_url="https://new.example.com")
    mock_store = MagicMock()
    existing_settings = Settings(
        llm_model="gpt-3.5", llm_api_key=SecretStr("old-api-key"), llm_base_url="https://old.example.com"
    )
    mock_store.load = AsyncMock(return_value=existing_settings)
    result = await store_llm_settings(settings, mock_store)
    assert result.llm_model == "gpt-4"
    assert result.llm_api_key.get_secret_value() == "new-api-key"
    assert result.llm_base_url == "https://new.example.com"


@pytest.mark.asyncio
async def test_store_llm_settings_partial_update():
    """Test store_llm_settings with partial update."""
    settings = Settings(llm_model="gpt-4")
    mock_store = MagicMock()
    existing_settings = Settings(
        llm_model="gpt-3.5", llm_api_key=SecretStr("existing-api-key"), llm_base_url="https://existing.example.com"
    )
    mock_store.load = AsyncMock(return_value=existing_settings)
    result = await store_llm_settings(settings, mock_store)
    assert result.llm_model == "gpt-4"
    assert result.llm_api_key.get_secret_value() == "existing-api-key"
    assert result.llm_base_url == "https://existing.example.com"


@pytest.mark.asyncio
async def test_store_provider_tokens_new_tokens(test_client, file_secrets_store):
    """Test store_provider_tokens with new tokens."""
    provider_tokens = {"provider_tokens": {"github": {"token": "new-token"}}}
    mock_store = MagicMock()
    mock_store.load = AsyncMock(return_value=None)
    UserSecrets()
    user_secrets = await file_secrets_store.store(UserSecrets())
    response = test_client.post("/api/add-git-providers", json=provider_tokens)
    assert response.status_code == 200
    user_secrets = await file_secrets_store.load()
    assert user_secrets.provider_tokens[ProviderType.GITHUB].token.get_secret_value() == "new-token"


@pytest.mark.asyncio
async def test_store_provider_tokens_update_existing(test_client, file_secrets_store):
    """Test store_provider_tokens updates existing tokens."""
    github_token = ProviderToken(token=SecretStr("old-token"))
    provider_tokens = {ProviderType.GITHUB: github_token}
    user_secrets = UserSecrets(provider_tokens=provider_tokens)
    await file_secrets_store.store(user_secrets)
    response = test_client.post(
        "/api/add-git-providers", json={"provider_tokens": {"github": {"token": "updated-token"}}}
    )
    assert response.status_code == 200
    user_secrets = await file_secrets_store.load()
    assert user_secrets.provider_tokens[ProviderType.GITHUB].token.get_secret_value() == "updated-token"


@pytest.mark.asyncio
async def test_store_provider_tokens_keep_existing(test_client, file_secrets_store):
    """Test store_provider_tokens keeps existing tokens when empty string provided."""
    github_token = ProviderToken(token=SecretStr("existing-token"))
    provider_tokens = {ProviderType.GITHUB: github_token}
    user_secrets = UserSecrets(provider_tokens=provider_tokens)
    await file_secrets_store.store(user_secrets)
    response = test_client.post("/api/add-git-providers", json={"provider_tokens": {"github": {"token": ""}}})
    assert response.status_code == 200
    user_secrets = await file_secrets_store.load()
    assert user_secrets.provider_tokens[ProviderType.GITHUB].token.get_secret_value() == "existing-token"
