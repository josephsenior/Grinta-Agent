"""Tests for the custom secrets API endpoints."""

import os
from types import MappingProxyType, SimpleNamespace
from unittest.mock import AsyncMock, patch

import pytest
from fastapi import FastAPI, status
from fastapi.testclient import TestClient
from pydantic import SecretStr
from typing import Any, Mapping, cast
from forge.integrations.provider import CustomSecret, ProviderToken, ProviderType
from forge.server.routes import secrets as secrets_routes
from forge.server.settings import POSTProviderModel
from forge.storage import get_file_store
from forge.storage.data_models.user_secrets import UserSecrets
from forge.storage.secrets.file_secrets_store import FileSecretsStore
from forge.storage.data_models.settings import Settings


@pytest.fixture
def test_client():
    """Create a test client for the settings API."""
    app = FastAPI()
    app.include_router(secrets_routes.router)
    with patch.dict(os.environ, {"SESSION_API_KEY": ""}, clear=False):
        with patch("forge.server.dependencies._SESSION_API_KEY", None):
            with TestClient(app) as client:
                yield client


@pytest.fixture(autouse=True)
def reset_migration_cache():
    secrets_routes._migration_done_cache.clear()
    yield
    secrets_routes._migration_done_cache.clear()


@pytest.fixture
def temp_dir(tmp_path_factory: pytest.TempPathFactory) -> str:
    return str(tmp_path_factory.mktemp("secrets_store"))


@pytest.fixture
def file_secrets_store(temp_dir):
    file_store = get_file_store("local", temp_dir)
    store = FileSecretsStore(file_store)
    with patch(
        "forge.storage.secrets.file_secrets_store.FileSecretsStore.get_instance",
        AsyncMock(return_value=store),
    ):
        yield store


@pytest.mark.asyncio
async def test_invalidate_legacy_secrets_store_migrates_once(monkeypatch):
    class DummySettings:
        def __init__(self, user_id: str, secrets_store):
            self.user_id = user_id
            self.secrets_store = secrets_store

        def model_copy(
            self,
            *,
            update: Mapping[str, Any] | None = None,
            deep: bool = False,
        ):
            del deep
            next_store = self.secrets_store
            if update and "secrets_store" in update:
                next_store = update["secrets_store"]
            return DummySettings(self.user_id, next_store)

    settings_store = AsyncMock()
    secrets_store = AsyncMock()
    provider_tokens = MappingProxyType(
        {
            ProviderType.GITHUB: ProviderToken(
                token=SecretStr("gh-key"), host="github.com"
            )
        }
    )
    dummy_settings = cast(
        Settings,
        DummySettings(
            user_id="user-1",
            secrets_store=SimpleNamespace(provider_tokens=provider_tokens),
        ),
    )

    result = await secrets_routes.invalidate_legacy_secrets_store(
        dummy_settings,
        settings_store,
        secrets_store,
    )

    assert isinstance(result, UserSecrets)
    secrets_store.store.assert_awaited()
    settings_store.store.assert_awaited()

    secrets_store.store.reset_mock()
    settings_store.store.reset_mock()

    second_result = await secrets_routes.invalidate_legacy_secrets_store(
        dummy_settings,
        settings_store,
        secrets_store,
    )
    assert second_result is None
    secrets_store.store.assert_not_called()
    settings_store.store.assert_not_called()


@pytest.mark.asyncio
async def test_invalidate_legacy_secrets_store_no_tokens(monkeypatch):
    class DummySettings:
        def __init__(self, user_id: str, secrets_store):
            self.user_id = user_id
            self.secrets_store = secrets_store

        def model_copy(
            self,
            *,
            update: Mapping[str, Any] | None = None,
            deep: bool = False,
        ):
            del deep
            next_store = self.secrets_store
            if update and "secrets_store" in update:
                next_store = update["secrets_store"]
            return DummySettings(self.user_id, next_store)

    settings_store = AsyncMock()
    secrets_store = AsyncMock()
    dummy_settings = cast(
        Settings, DummySettings("user-2", SimpleNamespace(provider_tokens={}))
    )

    result = await secrets_routes.invalidate_legacy_secrets_store(
        dummy_settings,
        settings_store,
        secrets_store,
    )

    assert result is None
    secrets_store.store.assert_not_called()
    settings_store.store.assert_not_called()


def test_process_token_validation_result_returns_error():
    msg = secrets_routes.process_token_validation_result(None, ProviderType.GITHUB)
    assert "Invalid token" in msg


@pytest.mark.asyncio
async def test_check_provider_tokens_detects_host_mismatch(monkeypatch):
    incoming = POSTProviderModel.model_validate(
        {
            "provider_tokens": {
                "github": {
                    "token": "new-token",
                    "host": "github.enterprise.com",
                }
            }
        }
    )
    existing = MappingProxyType(
        {
            ProviderType.GITHUB: ProviderToken(
                token=SecretStr("existing-token"), host="github.com"
            ),
        }
    )

    validate_mock = AsyncMock(side_effect=[ProviderType.GITHUB, None])
    monkeypatch.setattr(secrets_routes, "validate_provider_token", validate_mock)

    msg, normalized = await secrets_routes.check_provider_tokens(incoming, existing)

    assert "Invalid token" in msg
    assert normalized["github"].host == "github.enterprise.com"
    assert validate_mock.await_count == 2


@pytest.mark.asyncio
async def test_load_custom_secrets_names(test_client, file_secrets_store):
    """Test loading custom secrets names."""
    custom_secrets = {
        "API_KEY": CustomSecret(secret=SecretStr("api-key-value")),
        "DB_PASSWORD": CustomSecret(secret=SecretStr("db-password-value")),
    }
    provider_tokens = {
        ProviderType.GITHUB: ProviderToken(token=SecretStr("github-token"))
    }
    user_secrets = UserSecrets(
        custom_secrets=custom_secrets, provider_tokens=provider_tokens
    )
    await file_secrets_store.store(user_secrets)
    response = test_client.get("/api/secrets")
    print(response)
    assert response.status_code == 200
    data = response.json()
    assert "custom_secrets" in data
    secret_names = [secret["name"] for secret in data["custom_secrets"]]
    assert sorted(secret_names) == ["API_KEY", "DB_PASSWORD"]
    stored_settings = await file_secrets_store.load()
    assert (
        stored_settings.custom_secrets["API_KEY"].secret.get_secret_value()
        == "api-key-value"
    )
    assert (
        stored_settings.custom_secrets["DB_PASSWORD"].secret.get_secret_value()
        == "db-password-value"
    )
    assert ProviderType.GITHUB in stored_settings.provider_tokens


@pytest.mark.asyncio
async def test_load_custom_secrets_names_empty(test_client, file_secrets_store):
    """Test loading custom secrets names when there are no custom secrets."""
    provider_tokens = {
        ProviderType.GITHUB: ProviderToken(token=SecretStr("github-token"))
    }
    user_secrets = UserSecrets(provider_tokens=provider_tokens, custom_secrets={})
    await file_secrets_store.store(user_secrets)
    response = test_client.get("/api/secrets")
    assert response.status_code == 200
    data = response.json()
    assert "custom_secrets" in data
    assert data["custom_secrets"] == []


def test_load_custom_secrets_names_none_returns_empty(test_client):
    async def override_user_secrets():
        return None

    test_client.app.dependency_overrides[secrets_routes.get_user_secrets] = (
        override_user_secrets
    )
    try:
        response = test_client.get("/api/secrets")
    finally:
        test_client.app.dependency_overrides.pop(secrets_routes.get_user_secrets, None)

    assert response.status_code == status.HTTP_200_OK
    assert response.json() == {"custom_secrets": []}


def test_load_custom_secrets_names_error(test_client):
    user_secrets = UserSecrets(
        custom_secrets={
            "ERR": CustomSecret(secret=SecretStr("value"), description="desc"),
        },
    )
    with patch(
        "forge.server.routes.secrets.get_user_secrets",
        AsyncMock(return_value=user_secrets),
    ):
        with patch(
            "forge.server.routes.secrets.GETCustomSecrets",
            side_effect=Exception("boom"),
        ):
            response = test_client.get("/api/secrets")
    assert response.status_code == status.HTTP_401_UNAUTHORIZED
    assert "error" in response.json()


@pytest.mark.asyncio
async def test_add_custom_secret(test_client, file_secrets_store):
    """Test adding a new custom secret."""
    provider_tokens = {
        ProviderType.GITHUB: ProviderToken(token=SecretStr("github-token"))
    }
    user_secrets = UserSecrets(provider_tokens=provider_tokens)
    await file_secrets_store.store(user_secrets)
    add_secret_data = {"name": "API_KEY", "value": "api-key-value", "description": None}
    response = test_client.post("/api/secrets", json=add_secret_data)
    assert response.status_code == 201
    stored_settings = await file_secrets_store.load()
    assert "API_KEY" in stored_settings.custom_secrets
    assert (
        stored_settings.custom_secrets["API_KEY"].secret.get_secret_value()
        == "api-key-value"
    )


@pytest.mark.asyncio
async def test_create_custom_secret_duplicate_returns_400(
    test_client, file_secrets_store
):
    await file_secrets_store.store(
        UserSecrets(
            custom_secrets={"API_KEY": CustomSecret(secret=SecretStr("api-key-value"))},
            provider_tokens={},
        )
    )
    add_secret_data = {"name": "API_KEY", "value": "new-value", "description": ""}
    response = test_client.post("/api/secrets", json=add_secret_data)
    assert response.status_code == status.HTTP_400_BAD_REQUEST


@pytest.mark.asyncio
async def test_unset_provider_tokens_success(test_client, file_secrets_store):
    provider_tokens = {
        ProviderType.GITHUB: ProviderToken(token=SecretStr("github-token"))
    }
    await file_secrets_store.store(UserSecrets(provider_tokens=provider_tokens))
    response = test_client.post("/api/unset-provider-tokens")
    assert response.status_code == status.HTTP_200_OK
    stored_settings = await file_secrets_store.load()
    assert stored_settings.provider_tokens == {}


@pytest.mark.asyncio
async def test_create_custom_secret_store_failure_returns_500(
    test_client, file_secrets_store
):
    file_secrets_store.load = AsyncMock(return_value=None)
    file_secrets_store.store = AsyncMock(side_effect=Exception("boom"))
    response = test_client.post(
        "/api/secrets",
        json={"name": "FAIL", "value": "val", "description": "desc"},
    )
    assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR


@pytest.mark.asyncio
async def test_update_existing_custom_secret(test_client, file_secrets_store):
    """Test updating an existing custom secret's name and description (cannot change value once set)."""
    custom_secrets = {"API_KEY": CustomSecret(secret=SecretStr("old-api-key"))}
    provider_tokens = {
        ProviderType.GITHUB: ProviderToken(token=SecretStr("github-token"))
    }
    user_secrets = UserSecrets(
        custom_secrets=custom_secrets, provider_tokens=provider_tokens
    )
    await file_secrets_store.store(user_secrets)
    update_secret_data = {"name": "API_KEY", "description": None}
    response = test_client.put("/api/secrets/API_KEY", json=update_secret_data)
    assert response.status_code == 200
    stored_settings = await file_secrets_store.load()
    assert "API_KEY" in stored_settings.custom_secrets
    assert (
        stored_settings.custom_secrets["API_KEY"].secret.get_secret_value()
        == "old-api-key"
    )
    assert ProviderType.GITHUB in stored_settings.provider_tokens


@pytest.mark.asyncio
async def test_update_custom_secret_not_found_returns_404(
    test_client, file_secrets_store
):
    await file_secrets_store.store(UserSecrets(custom_secrets={}, provider_tokens={}))
    update_secret_data = {"name": "MISSING", "description": ""}
    response = test_client.put("/api/secrets/MISSING", json=update_secret_data)
    assert response.status_code == status.HTTP_404_NOT_FOUND


@pytest.mark.asyncio
async def test_update_custom_secret_name_conflict_returns_400(
    test_client, file_secrets_store
):
    custom_secrets = {
        "FIRST": CustomSecret(secret=SecretStr("v1")),
        "SECOND": CustomSecret(secret=SecretStr("v2")),
    }
    await file_secrets_store.store(
        UserSecrets(custom_secrets=custom_secrets, provider_tokens={})
    )
    update_secret_data = {"name": "SECOND", "description": "conflict"}
    response = test_client.put("/api/secrets/FIRST", json=update_secret_data)
    assert response.status_code == status.HTTP_400_BAD_REQUEST


@pytest.mark.asyncio
async def test_update_custom_secret_store_failure_returns_500(
    test_client, file_secrets_store
):
    custom_secrets = {
        "API_KEY": CustomSecret(secret=SecretStr("old")),
    }
    await file_secrets_store.store(
        UserSecrets(custom_secrets=custom_secrets, provider_tokens={})
    )
    file_secrets_store.store = AsyncMock(side_effect=Exception("boom"))
    response = test_client.put(
        "/api/secrets/API_KEY",
        json={"name": "API_KEY", "description": "updated"},
    )
    assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR


@pytest.mark.asyncio
async def test_add_multiple_custom_secrets(test_client, file_secrets_store):
    """Test adding multiple custom secrets at once."""
    custom_secrets = {
        "EXISTING_SECRET": CustomSecret(secret=SecretStr("existing-value"))
    }
    provider_tokens = {
        ProviderType.GITHUB: ProviderToken(token=SecretStr("github-token"))
    }
    user_secrets = UserSecrets(
        custom_secrets=custom_secrets, provider_tokens=provider_tokens
    )
    await file_secrets_store.store(user_secrets)
    add_secret_data1 = {
        "name": "API_KEY",
        "value": "api-key-value",
        "description": None,
    }
    response1 = test_client.post("/api/secrets", json=add_secret_data1)
    assert response1.status_code == 201
    add_secret_data2 = {
        "name": "DB_PASSWORD",
        "value": "db-password-value",
        "description": None,
    }
    response = test_client.post("/api/secrets", json=add_secret_data2)
    assert response.status_code == 201
    stored_settings = await file_secrets_store.load()
    assert "API_KEY" in stored_settings.custom_secrets
    assert (
        stored_settings.custom_secrets["API_KEY"].secret.get_secret_value()
        == "api-key-value"
    )
    assert "DB_PASSWORD" in stored_settings.custom_secrets
    assert (
        stored_settings.custom_secrets["DB_PASSWORD"].secret.get_secret_value()
        == "db-password-value"
    )
    assert "EXISTING_SECRET" in stored_settings.custom_secrets
    assert (
        stored_settings.custom_secrets["EXISTING_SECRET"].secret.get_secret_value()
        == "existing-value"
    )
    assert ProviderType.GITHUB in stored_settings.provider_tokens


@pytest.mark.asyncio
async def test_delete_custom_secret(test_client, file_secrets_store):
    """Test deleting a custom secret."""
    custom_secrets = {
        "API_KEY": CustomSecret(secret=SecretStr("api-key-value")),
        "DB_PASSWORD": CustomSecret(secret=SecretStr("db-password-value")),
    }
    provider_tokens = {
        ProviderType.GITHUB: ProviderToken(token=SecretStr("github-token"))
    }
    user_secrets = UserSecrets(
        custom_secrets=custom_secrets, provider_tokens=provider_tokens
    )
    await file_secrets_store.store(user_secrets)
    response = test_client.delete("/api/secrets/API_KEY")
    assert response.status_code == 200
    stored_settings = await file_secrets_store.load()
    assert "API_KEY" not in stored_settings.custom_secrets
    assert "DB_PASSWORD" in stored_settings.custom_secrets
    assert (
        stored_settings.custom_secrets["DB_PASSWORD"].secret.get_secret_value()
        == "db-password-value"
    )
    assert ProviderType.GITHUB in stored_settings.provider_tokens


@pytest.mark.asyncio
async def test_delete_nonexistent_custom_secret(test_client, file_secrets_store):
    """Test deleting a custom secret that doesn't exist."""
    custom_secrets = {
        "API_KEY": CustomSecret(secret=SecretStr("api-key-value"), description="")
    }
    provider_tokens = {
        ProviderType.GITHUB: ProviderToken(token=SecretStr("github-token"))
    }
    user_secrets = UserSecrets(
        custom_secrets=custom_secrets, provider_tokens=provider_tokens
    )
    await file_secrets_store.store(user_secrets)
    response = test_client.delete("/api/secrets/NONEXISTENT_KEY")
    assert response.status_code == 404
    stored_settings = await file_secrets_store.load()
    assert "API_KEY" in stored_settings.custom_secrets
    assert (
        stored_settings.custom_secrets["API_KEY"].secret.get_secret_value()
        == "api-key-value"
    )
    assert ProviderType.GITHUB in stored_settings.provider_tokens


@pytest.mark.asyncio
async def test_delete_custom_secret_store_failure_returns_500(
    test_client, file_secrets_store
):
    custom_secrets = {
        "API_KEY": CustomSecret(secret=SecretStr("api-key-value")),
    }
    await file_secrets_store.store(
        UserSecrets(custom_secrets=custom_secrets, provider_tokens={})
    )
    file_secrets_store.store = AsyncMock(side_effect=Exception("boom"))
    response = test_client.delete("/api/secrets/API_KEY")
    assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR


@pytest.mark.asyncio
async def test_add_git_providers_with_host(test_client, file_secrets_store):
    """Test adding git providers with host parameter."""
    provider_tokens = {
        ProviderType.GITHUB: ProviderToken(token=SecretStr("github-token"))
    }
    user_secrets = UserSecrets(provider_tokens=provider_tokens)
    await file_secrets_store.store(user_secrets)
    normalized_tokens = {
        "github": ProviderToken(
            token=SecretStr("new-github-token"),
            host="github.enterprise.com",
        )
    }
    with patch(
        "forge.server.routes.secrets.check_provider_tokens",
        AsyncMock(return_value=("", normalized_tokens)),
    ):
        add_provider_data = {
            "provider_tokens": {
                "github": {"token": "new-github-token", "host": "github.enterprise.com"}
            }
        }
        response = test_client.post("/api/add-git-providers", json=add_provider_data)
        assert response.status_code == 200
        stored_secrets = await file_secrets_store.load()
        assert ProviderType.GITHUB in stored_secrets.provider_tokens
        assert (
            stored_secrets.provider_tokens[ProviderType.GITHUB].token.get_secret_value()
            == "new-github-token"
        )
        assert (
            stored_secrets.provider_tokens[ProviderType.GITHUB].host
            == "github.enterprise.com"
        )


@pytest.mark.asyncio
async def test_add_git_providers_update_host_only(test_client, file_secrets_store):
    """Test updating only the host for an existing provider token."""
    provider_tokens = {
        ProviderType.GITHUB: ProviderToken(
            token=SecretStr("github-token"), host="github.com"
        )
    }
    user_secrets = UserSecrets(provider_tokens=provider_tokens)
    await file_secrets_store.store(user_secrets)
    normalized_tokens = {
        "github": ProviderToken(
            token=SecretStr(""),
            host="github.enterprise.com",
        )
    }
    with patch(
        "forge.server.routes.secrets.check_provider_tokens",
        AsyncMock(return_value=("", normalized_tokens)),
    ):
        update_host_data = {
            "provider_tokens": {
                "github": {"token": "", "host": "github.enterprise.com"}
            }
        }
        response = test_client.post("/api/add-git-providers", json=update_host_data)
        assert response.status_code == 200
        stored_secrets = await file_secrets_store.load()
        assert ProviderType.GITHUB in stored_secrets.provider_tokens
        assert (
            stored_secrets.provider_tokens[ProviderType.GITHUB].token.get_secret_value()
            == "github-token"
        )
        assert (
            stored_secrets.provider_tokens[ProviderType.GITHUB].host
            == "github.enterprise.com"
        )


@pytest.mark.asyncio
async def test_add_git_providers_invalid_token_with_host(
    test_client, file_secrets_store
):
    """Test adding an invalid token with a host."""
    user_secrets = UserSecrets()
    await file_secrets_store.store(user_secrets)
    with patch(
        "forge.integrations.utils.validate_provider_token", AsyncMock(return_value=None)
    ):
        add_provider_data = {
            "provider_tokens": {
                "github": {"token": "invalid-token", "host": "github.enterprise.com"}
            }
        }
        response = test_client.post("/api/add-git-providers", json=add_provider_data)
        assert response.status_code == 401
        assert "Invalid token" in response.json()["error"]


@pytest.mark.asyncio
async def test_add_multiple_git_providers_with_hosts(test_client, file_secrets_store):
    """Test adding multiple git providers with different hosts."""
    user_secrets = UserSecrets()
    await file_secrets_store.store(user_secrets)
    normalized_tokens = {
        "github": ProviderToken(
            token=SecretStr("github-token"),
            host="github.enterprise.com",
        ),
        "gitlab": ProviderToken(
            token=SecretStr("gitlab-token"),
            host="gitlab.enterprise.com",
        ),
    }
    with patch(
        "forge.server.routes.secrets.check_provider_tokens",
        AsyncMock(return_value=("", normalized_tokens)),
    ):
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
        assert (
            stored_secrets.provider_tokens[ProviderType.GITHUB].token.get_secret_value()
            == "github-token"
        )
        assert (
            stored_secrets.provider_tokens[ProviderType.GITHUB].host
            == "github.enterprise.com"
        )
        assert ProviderType.GITLAB in stored_secrets.provider_tokens
        assert (
            stored_secrets.provider_tokens[ProviderType.GITLAB].token.get_secret_value()
            == "gitlab-token"
        )
        assert (
            stored_secrets.provider_tokens[ProviderType.GITLAB].host
            == "gitlab.enterprise.com"
        )


def test_store_provider_tokens_handles_exception(test_client):
    class DummyStore:
        async def load(self):
            return UserSecrets(provider_tokens={})

        async def store(self, *_args, **_kwargs):
            raise RuntimeError("boom")

    mock_store = DummyStore()
    normalized_tokens = {
        "github": ProviderToken(token=SecretStr("token"), host="github.com"),
    }

    async def override_store():
        return mock_store

    async def override_provider_tokens():
        return {}

    test_client.app.dependency_overrides[secrets_routes.get_secrets_store] = (
        override_store
    )
    test_client.app.dependency_overrides[secrets_routes.get_provider_tokens] = (
        override_provider_tokens
    )
    try:
        with patch(
            "forge.server.routes.secrets.check_provider_tokens",
            AsyncMock(return_value=("", normalized_tokens)),
        ):
            response = test_client.post(
                "/api/add-git-providers",
                json={
                    "provider_tokens": {
                        "github": {"token": "token", "host": "github.com"}
                    }
                },
            )
    finally:
        test_client.app.dependency_overrides.pop(secrets_routes.get_secrets_store, None)
        test_client.app.dependency_overrides.pop(
            secrets_routes.get_provider_tokens, None
        )
    assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR


def test_unset_provider_tokens_error_returns_500(test_client):
    class DummyStore:
        async def load(self):
            return UserSecrets(
                provider_tokens={
                    ProviderType.GITHUB: ProviderToken(token=SecretStr("token"))
                }
            )

        async def store(self, *_args, **_kwargs):
            raise RuntimeError("boom")

    mock_store = DummyStore()

    async def override_store():
        return mock_store

    test_client.app.dependency_overrides[secrets_routes.get_secrets_store] = (
        override_store
    )
    try:
        response = test_client.post("/api/unset-provider-tokens")
    finally:
        test_client.app.dependency_overrides.pop(secrets_routes.get_secrets_store, None)
    assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR


def test_store_provider_tokens_error_message_returns_401(test_client):
    with patch(
        "forge.server.routes.secrets.check_provider_tokens",
        AsyncMock(return_value=("Invalid token", {})),
    ):
        response = test_client.post(
            "/api/add-git-providers",
            json={"provider_tokens": {"github": {"token": "bad"}}},
        )
    assert response.status_code == status.HTTP_401_UNAUTHORIZED
    assert "Invalid token" in response.json()["error"]


def test_secrets_app_proxy_callable():
    async def override_store():
        class DummyStore:
            async def load(self):
                return None

            async def store(self, *_args, **_kwargs):
                return None

        return DummyStore()

    async def override_provider_tokens():
        return {}

    async def override_user_secrets():
        return None

    with TestClient(secrets_routes.app) as client:
        client_app = cast(Any, client.app)
        client_app.dependency_overrides[secrets_routes.get_secrets_store] = (
            override_store
        )
        client_app.dependency_overrides[secrets_routes.get_provider_tokens] = (
            override_provider_tokens
        )
        client_app.dependency_overrides[secrets_routes.get_user_secrets] = (
            override_user_secrets
        )
        try:
            response = client.post("/api/unset-provider-tokens")
            assert response.status_code == status.HTTP_200_OK
        finally:
            client_app.dependency_overrides.clear()
