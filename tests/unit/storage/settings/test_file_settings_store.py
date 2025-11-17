from unittest.mock import MagicMock, patch

import pytest

from forge.core.config.forge_config import ForgeConfig
from forge.storage.data_models.settings import Settings
from forge.storage.files import FileStore
from forge.storage.settings import file_settings_store as file_settings_module
from forge.storage.settings.file_settings_store import FileSettingsStore


@pytest.fixture
def mock_file_store():
    return MagicMock(spec=FileStore)


@pytest.fixture
def file_settings_store(mock_file_store):
    return FileSettingsStore(mock_file_store)


@pytest.fixture(autouse=True)
def reset_settings_cache():
    file_settings_module._file_settings_cache.clear()
    file_settings_module._file_settings_locks.clear()
    yield
    file_settings_module._file_settings_cache.clear()
    file_settings_module._file_settings_locks.clear()


@pytest.mark.asyncio
async def test_load_nonexistent_data(file_settings_store):
    with patch(
        "forge.storage.data_models.settings.load_FORGE_config",
        MagicMock(return_value=ForgeConfig()),
    ):
        file_settings_store.file_store.read.side_effect = FileNotFoundError()
        assert await file_settings_store.load() is None


@pytest.mark.asyncio
async def test_store_and_load_data(file_settings_store):
    init_data = Settings(
        language="python",
        agent="test-agent",
        max_iterations=100,
        security_analyzer="default",
        confirmation_mode=True,
        llm_model="test-model",
        llm_api_key="test-key",
        llm_base_url="https://test.com",
    )
    await file_settings_store.store(init_data)
    expected_json = init_data.model_dump_json(context={"expose_secrets": True})
    file_settings_store.file_store.write.assert_called_once_with(
        "settings.json", expected_json
    )
    file_settings_store.file_store.read.return_value = expected_json
    loaded_data = await file_settings_store.load()
    assert loaded_data is not None
    assert loaded_data.language == init_data.language
    assert loaded_data.agent == init_data.agent
    assert loaded_data.max_iterations == init_data.max_iterations
    assert loaded_data.security_analyzer == init_data.security_analyzer
    assert loaded_data.confirmation_mode == init_data.confirmation_mode
    assert loaded_data.llm_model == init_data.llm_model
    assert loaded_data.llm_api_key
    assert init_data.llm_api_key
    assert (
        loaded_data.llm_api_key.get_secret_value()
        == init_data.llm_api_key.get_secret_value()
    )
    assert loaded_data.llm_base_url == init_data.llm_base_url


@pytest.mark.asyncio
async def test_load_uses_cache(file_settings_store, monkeypatch: pytest.MonkeyPatch):
    init_data = Settings(agent="cached-agent")
    json_payload = init_data.model_dump_json(context={"expose_secrets": True})
    file_settings_store.file_store.read.return_value = json_payload

    fake_time = {"value": 100.0}
    monkeypatch.setattr(file_settings_module.time, "time", lambda: fake_time["value"])

    first = await file_settings_store.load()
    assert first is not None
    assert file_settings_store.file_store.read.call_count == 1

    file_settings_store.file_store.read.reset_mock()
    fake_time["value"] = 120.0  # within TTL, should hit cache
    second = await file_settings_store.load()
    assert second is first
    file_settings_store.file_store.read.assert_not_called()


@pytest.mark.asyncio
async def test_store_invalidates_cache(
    file_settings_store, monkeypatch: pytest.MonkeyPatch
):
    init_data = Settings(agent="invalidate-agent")
    json_payload = init_data.model_dump_json(context={"expose_secrets": True})
    file_settings_store.file_store.read.return_value = json_payload

    fake_time = {"value": 200.0}
    monkeypatch.setattr(file_settings_module.time, "time", lambda: fake_time["value"])

    await file_settings_store.load()
    assert file_settings_store.file_store.read.call_count == 1

    new_settings = Settings(agent="updated")
    await file_settings_store.store(new_settings)
    file_settings_store.file_store.write.assert_called_once()

    file_settings_store.file_store.read.reset_mock()
    fake_time["value"] = 210.0
    await file_settings_store.load()
    file_settings_store.file_store.read.assert_called_once()


@pytest.mark.asyncio
async def test_get_instance():
    config = ForgeConfig(file_store="local", file_store_path="/test/path")
    with patch(
        "forge.storage.settings.file_settings_store.get_file_store"
    ) as mock_get_store:
        mock_store = MagicMock(spec=FileStore)
        mock_get_store.return_value = mock_store
        store = await FileSettingsStore.get_instance(config, None)
        assert isinstance(store, FileSettingsStore)
        assert store.file_store == mock_store
        mock_get_store.assert_called_once_with(
            file_store_type="local",
            file_store_path="/test/path",
            file_store_web_hook_url=None,
            file_store_web_hook_headers=None,
            file_store_web_hook_batch=False,
        )
