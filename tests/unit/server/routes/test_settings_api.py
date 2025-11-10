from __future__ import annotations

import pytest
import json

from fastapi import FastAPI, status
from fastapi.testclient import TestClient
from pydantic import SecretStr
from unittest.mock import AsyncMock

from forge.integrations.provider import ProviderToken
from forge.integrations.service_types import ProviderType
from forge.server.routes import settings as settings_routes
from forge.server.settings import GETSettingsModel
from forge.server.shared import config
from forge.storage.data_models.settings import Settings
from forge.storage.data_models.user_secrets import UserSecrets


@pytest.fixture(autouse=True)
def clear_settings_cache():
    settings_routes._settings_cache.clear()
    yield
    settings_routes._settings_cache.clear()


@pytest.fixture
def settings_api_client(monkeypatch):
    monkeypatch.setattr("forge.server.dependencies._SESSION_API_KEY", None)
    fastapi_app = FastAPI()
    fastapi_app.include_router(settings_routes.app)
    with TestClient(fastapi_app) as client:
        yield client


@pytest.fixture
def restore_config():
    original_git_name = config.git_user_name
    original_git_email = config.git_user_email
    sandbox = getattr(config, "sandbox", None)
    original_resource_factor = getattr(sandbox, "remote_runtime_resource_factor", None)
    yield
    config.git_user_name = original_git_name
    config.git_user_email = original_git_email
    if sandbox is not None and original_resource_factor is not None:
        sandbox.remote_runtime_resource_factor = original_resource_factor


def _apply_overrides(client: TestClient, overrides: dict) -> None:
    for dep, func in overrides.items():
        client.app.dependency_overrides[dep] = func


def _clear_overrides(client: TestClient, overrides: dict) -> None:
    for dep in overrides:
        client.app.dependency_overrides.pop(dep, None)


def test_load_settings_returns_cached_response(settings_api_client: TestClient, monkeypatch):
    async def override_provider_tokens():
        return {ProviderType.GITHUB: ProviderToken(token=SecretStr("token"), host="github.com")}

    async def override_settings_store():
        return AsyncMock()

    async def override_settings():
        return Settings(llm_model="openai/gpt-4", llm_api_key=SecretStr("abc"))

    async def override_secrets_store():
        return AsyncMock()

    async def override_user_id():
        return "user-123"

    overrides = {
        settings_routes.get_provider_tokens: override_provider_tokens,
        settings_routes.get_user_settings_store: override_settings_store,
        settings_routes.get_user_settings: override_settings,
        settings_routes.get_secrets_store: override_secrets_store,
        settings_routes.get_user_id: override_user_id,
    }

    _apply_overrides(settings_api_client, overrides)

    call_counter = {"count": 0}
    original_build = settings_routes._build_settings_response

    def wrapped_build(settings: Settings, tokens):
        call_counter["count"] += 1
        return original_build(settings, tokens)

    monkeypatch.setattr(settings_routes, "_build_settings_response", wrapped_build)

    try:
        resp1 = settings_api_client.get("/api/settings")
        assert resp1.status_code == 200
        resp2 = settings_api_client.get("/api/settings")
        assert resp2.status_code == 200
        assert call_counter["count"] == 1
    finally:
        _clear_overrides(settings_api_client, overrides)
        monkeypatch.setattr(settings_routes, "_build_settings_response", original_build)


def test_load_settings_returns_default_when_missing(settings_api_client: TestClient):
    async def override_provider_tokens():
        return {}

    async def override_settings_store():
        return AsyncMock()

    async def override_settings():
        return None

    async def override_secrets_store():
        return AsyncMock()

    overrides = {
        settings_routes.get_provider_tokens: override_provider_tokens,
        settings_routes.get_user_settings_store: override_settings_store,
        settings_routes.get_user_settings: override_settings,
        settings_routes.get_secrets_store: override_secrets_store,
    }

    _apply_overrides(settings_api_client, overrides)
    try:
        response = settings_api_client.get("/api/settings")
        assert response.status_code == 200
        payload = response.json()
        assert payload["llm_model"] == "Openhands/claude-sonnet-4-20250514"
        assert payload["llm_api_key"] is None
    finally:
        _clear_overrides(settings_api_client, overrides)


def test_load_settings_handles_exception_returns_default(settings_api_client: TestClient, monkeypatch):
    async def override_provider_tokens():
        return {}

    async def override_settings_store():
        return AsyncMock()

    async def override_settings():
        return Settings(llm_model="openai/gpt-4")

    async def override_secrets_store():
        return AsyncMock()

    overrides = {
        settings_routes.get_provider_tokens: override_provider_tokens,
        settings_routes.get_user_settings_store: override_settings_store,
        settings_routes.get_user_settings: override_settings,
        settings_routes.get_secrets_store: override_secrets_store,
    }

    _apply_overrides(settings_api_client, overrides)

    def raising_build(*_args, **_kwargs):
        raise RuntimeError("boom")

    monkeypatch.setattr(settings_routes, "_build_settings_response", raising_build)

    try:
        response = settings_api_client.get("/api/settings")
        assert response.status_code == 200
        payload = response.json()
        assert payload["llm_model"] == "Openhands/claude-sonnet-4-20250514"
    finally:
        _clear_overrides(settings_api_client, overrides)


def test_build_provider_tokens_set_prefers_user_secrets():
    user_secrets = UserSecrets(
        provider_tokens={
            ProviderType.GITLAB: ProviderToken(token=SecretStr("gl"), host="gitlab.com"),
        }
    )
    incoming = {ProviderType.GITHUB: ProviderToken(token=SecretStr("gh"), host="github.com")}
    result = settings_routes._build_provider_tokens_set(user_secrets, incoming)
    assert ProviderType.GITLAB in result
    assert ProviderType.GITHUB not in result
    assert result[ProviderType.GITLAB] == "gitlab.com"


def test_build_settings_response_masks_keys():
    settings = Settings(
        llm_model="openai/gpt-4",
        llm_api_key=SecretStr("secret"),
        search_api_key=SecretStr("search"),
        sandbox_api_key=SecretStr("sandbox"),
    )
    provider_tokens = {ProviderType.GITHUB: "github.com"}
    response = settings_routes._build_settings_response(settings, provider_tokens)
    assert isinstance(response, GETSettingsModel)
    assert response.llm_api_key is None
    assert response.search_api_key is None
    assert response.llm_api_key_set is True
    assert response.provider_tokens_set == {"github": "github.com"}


def _patch_api_key_manager(monkeypatch, *, provider: str, api_key: SecretStr | None):
    monkeypatch.setattr(
        settings_routes.api_key_manager.__class__,
        "_extract_provider",
        lambda self, model: provider,
    )
    monkeypatch.setattr(
        settings_routes.api_key_manager.__class__,
        "set_environment_variables",
        lambda self, model, key: None,
    )
    monkeypatch.setattr(
        settings_routes.api_key_manager.__class__,
        "get_api_key_for_model",
        (lambda self, model, key: api_key) if api_key is not None else (lambda self, model, key: None),
    )


def test_build_unauthorized_response_returns_401():
    settings = Settings(user_consents_to_analytics=True)
    response = settings_routes._build_unauthorized_response(settings)
    assert response.status_code == status.HTTP_401_UNAUTHORIZED
    assert response.body


def test_reset_settings_returns_gone(settings_api_client: TestClient):
    response = settings_api_client.post("/api/reset-settings")
    assert response.status_code == status.HTTP_410_GONE
    assert response.json()["error"].startswith("Reset settings")


@pytest.mark.asyncio
async def test_store_settings_preserves_placeholder_api_key(monkeypatch, restore_config):
    existing_settings = Settings(
        llm_model="openai/gpt-4",
        llm_api_key=SecretStr("keep-me"),
        git_user_name="original",
        git_user_email="original@example.com",
    )
    incoming = Settings(
        llm_model="openai/gpt-4",
        llm_api_key=SecretStr("**********"),
        git_user_name="new-name",
        git_user_email="new@example.com",
        remote_runtime_resource_factor=2,
    )
    settings_store = AsyncMock()
    settings_store.load = AsyncMock(side_effect=[existing_settings, existing_settings])
    settings_store.store = AsyncMock()

    async def fake_store_llm(settings: Settings, *_args):
        return settings

    monkeypatch.setattr(settings_routes, "store_llm_settings", fake_store_llm)
    _patch_api_key_manager(monkeypatch, provider="openai", api_key=existing_settings.llm_api_key)

    class DummyCache:
        def __init__(self):
            self.invalidated: list[str] = []

        async def invalidate_user_cache(self, user_id: str) -> None:
            self.invalidated.append(user_id)

    dummy_cache = DummyCache()
    monkeypatch.setattr("forge.core.cache.get_async_smart_cache", AsyncMock(return_value=dummy_cache))

    response = await settings_routes.store_settings(incoming, settings_store)
    assert response.status_code == status.HTTP_200_OK
    stored_settings = settings_store.store.await_args[0][0]
    assert stored_settings.llm_api_key.get_secret_value() == "keep-me"
    assert config.git_user_name == "new-name"
    assert config.git_user_email == "new@example.com"
    assert dummy_cache.invalidated == ["default"]


@pytest.mark.asyncio
async def test_store_settings_no_api_key_preserves_existing_and_clears_invalid_base_url(
    monkeypatch, restore_config
):
    existing_settings = Settings(
        llm_model="openrouter/test",
        llm_api_key=SecretStr("existing-key"),
        llm_base_url="https://valid.url",
    )
    incoming = Settings(
        llm_model="openrouter/test",
        llm_api_key=None,
        llm_base_url="gemini",
        git_user_name=None,
        git_user_email=None,
    )
    settings_store = AsyncMock()
    settings_store.load = AsyncMock(side_effect=[existing_settings, existing_settings])
    settings_store.store = AsyncMock()

    async def fake_store_llm(settings: Settings, *_args):
        return settings

    monkeypatch.setattr(settings_routes, "store_llm_settings", fake_store_llm)
    _patch_api_key_manager(monkeypatch, provider="openrouter", api_key=existing_settings.llm_api_key)
    monkeypatch.setattr("forge.core.cache.get_async_smart_cache", AsyncMock(return_value=AsyncMock()))

    response = await settings_routes.store_settings(incoming, settings_store)
    assert response.status_code == status.HTTP_200_OK
    stored_settings = settings_store.store.await_args[0][0]
    assert stored_settings.llm_api_key.get_secret_value() == "existing-key"
    assert stored_settings.llm_base_url is None


@pytest.mark.asyncio
async def test_store_settings_failure_returns_500(monkeypatch):
    incoming = Settings(llm_model="openai/gpt-4", llm_api_key=SecretStr("abc"))
    settings_store = AsyncMock()
    settings_store.load = AsyncMock(return_value=None)
    settings_store.store = AsyncMock(side_effect=RuntimeError("boom"))

    async def fake_store_llm(settings: Settings, *_args):
        return settings

    monkeypatch.setattr(settings_routes, "store_llm_settings", fake_store_llm)
    _patch_api_key_manager(monkeypatch, provider="openai", api_key=None)
    monkeypatch.setattr("forge.core.cache.get_async_smart_cache", AsyncMock(return_value=AsyncMock()))

    response = await settings_routes.store_settings(incoming, settings_store)
    assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
    payload = json.loads(response.body)
    assert "error" in payload


def test_convert_to_settings_openrouter_fix(monkeypatch):
    monkeypatch.setenv("OPENROUTER_API_KEY", "openrouter-secret")
    settings = Settings(
        llm_model="openrouter/test",
        llm_api_key=SecretStr("AIza-gemini"),
        llm_base_url="gemini-2.5-pro",
    )
    result = settings_routes.convert_to_settings(settings)
    assert result.llm_base_url in ("", None)
    assert result.llm_api_key.get_secret_value() == "openrouter-secret"


@pytest.mark.asyncio
async def test_store_llm_settings_openrouter_autopopulates_tokens(monkeypatch):
    settings = Settings(
        llm_model="openrouter/test",
        llm_api_key=SecretStr("key"),
        llm_base_url="gemini-2.5-pro",
    )
    settings_store = AsyncMock()
    settings_store.load = AsyncMock(return_value=None)

    monkeypatch.setattr(
        settings_routes.api_key_manager.__class__,
        "_extract_provider",
        lambda self, model: "openrouter",
    )

    result = await settings_routes.store_llm_settings(settings, settings_store)
    assert result.llm_base_url in ("", None)
    settings_store.load.assert_awaited()
    assert isinstance(result, Settings)


@pytest.mark.asyncio
async def test_store_llm_settings_openrouter_settings_dict_fix(monkeypatch):
    sequence = iter(["forge", "forge", "openrouter", "openrouter"])
    monkeypatch.setattr(
        settings_routes.api_key_manager.__class__,
        "_extract_provider",
        lambda self, model: next(sequence, "openrouter"),
    )
    settings = Settings(
        llm_model="openrouter/test",
        llm_api_key=SecretStr("key"),
        llm_base_url="gemini-2.5-pro",
    )
    settings_store = AsyncMock()
    settings_store.load = AsyncMock(return_value=None)

    result = await settings_routes.store_llm_settings(settings, settings_store)
    assert result.llm_base_url in ("", None)


@pytest.mark.asyncio
async def test_store_llm_settings_final_fix_clears_remaining_base_url(monkeypatch):
    sequence = iter(["forge", "forge"])
    monkeypatch.setattr(
        settings_routes.api_key_manager.__class__,
        "_extract_provider",
        lambda self, model: next(sequence, "openrouter"),
    )
    settings = Settings(
        llm_model="openrouter/test",
        llm_api_key=None,
        llm_base_url="gemini-2.5-pro",
    )
    settings_store = AsyncMock()
    settings_store.load = AsyncMock(return_value=None)

    result = await settings_routes.store_llm_settings(settings, settings_store)
    assert result.llm_base_url == ""


@pytest.mark.asyncio
async def test_store_settings_placeholder_without_existing(monkeypatch):
    incoming = Settings(llm_model="openai/gpt-4", llm_api_key=SecretStr("**********"))
    settings_store = AsyncMock()
    settings_store.load = AsyncMock(side_effect=[None, None])
    settings_store.store = AsyncMock()

    async def passthrough(settings: Settings, *_args):
        return settings

    monkeypatch.setattr(settings_routes, "store_llm_settings", passthrough)
    _patch_api_key_manager(monkeypatch, provider="openai", api_key=None)
    monkeypatch.setattr("forge.core.cache.get_async_smart_cache", AsyncMock(return_value=AsyncMock()))

    response = await settings_routes.store_settings(incoming, settings_store)
    assert response.status_code == status.HTTP_200_OK
    stored_settings = settings_store.store.await_args[0][0]
    assert stored_settings.llm_api_key is None


@pytest.mark.asyncio
async def test_store_settings_fallback_sets_environment(monkeypatch, restore_config):
    incoming = Settings(
        llm_model="openai/gpt-4",
        llm_api_key=SecretStr("provided"),
        llm_base_url="https://api.openai.com",
    )
    settings_store = AsyncMock()
    settings_store.load = AsyncMock(return_value=None)
    settings_store.store = AsyncMock()

    call_log: list[tuple[str, str, str]] = []

    def set_env(self, model: str, key: SecretStr | None) -> None:
        value = key.get_secret_value() if isinstance(key, SecretStr) else key
        call_log.append(("set", model, value))

    monkeypatch.setattr(settings_routes.api_key_manager.__class__, "set_environment_variables", set_env)
    monkeypatch.setattr(
        settings_routes.api_key_manager.__class__,
        "get_api_key_for_model",
        lambda self, model, key: None,
    )
    monkeypatch.setattr("forge.core.cache.get_async_smart_cache", AsyncMock(return_value=AsyncMock()))

    async def passthrough(settings: Settings, *_args):
        return settings

    monkeypatch.setattr(settings_routes, "store_llm_settings", passthrough)

    response = await settings_routes.store_settings(incoming, settings_store)
    assert response.status_code == status.HTTP_200_OK
    assert len(call_log) >= 2


@pytest.mark.asyncio
async def test_store_settings_clears_invalid_base_url(monkeypatch):
    incoming = Settings(
        llm_model="openai/gpt-4",
        llm_api_key=None,
        llm_base_url="invalid-url",
    )
    settings_store = AsyncMock()
    settings_store.load = AsyncMock(return_value=None)
    settings_store.store = AsyncMock()

    async def passthrough(settings: Settings, *_args):
        return settings

    monkeypatch.setattr(settings_routes, "store_llm_settings", passthrough)
    _patch_api_key_manager(monkeypatch, provider="openai", api_key=None)
    monkeypatch.setattr("forge.core.cache.get_async_smart_cache", AsyncMock(return_value=AsyncMock()))

    response = await settings_routes.store_settings(incoming, settings_store)
    assert response.status_code == status.HTTP_200_OK
    stored_settings = settings_store.store.await_args[0][0]
    assert stored_settings.llm_base_url is None


def test_convert_to_settings_converts_string_keys():
    settings = Settings(
        llm_model="model",
        llm_api_key="plain-key",
        search_api_key="search-key",
    )
    result = settings_routes.convert_to_settings(settings)
    assert isinstance(result.llm_api_key, SecretStr)
    assert isinstance(result.search_api_key, SecretStr)
