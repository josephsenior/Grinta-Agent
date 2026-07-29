"""Unit tests for backend.persistence.auth module."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from backend.persistence.auth import (
    get_access_token,
    get_current_user_id,
    get_provider_tokens,
    get_secrets_store,
    get_user_id,
    get_user_secret_store,
    get_user_secrets,
    get_user_settings,
    get_user_settings_store,
)
from backend.persistence.data_models.settings import Settings
from backend.persistence.data_models.user_secrets import UserSecrets
from backend.persistence.secrets.file_secrets_store import FileSecretsStore
from backend.persistence.settings.file_settings_store import FileSettingsStore


def test_get_user_id():
    """Test get_user_id returns constant OSS user ID."""
    assert get_user_id() == "oss_user"


def test_get_current_user_id():
    """Test get_current_user_id returns constant OSS user ID."""
    assert get_current_user_id() == "oss_user"


def test_get_access_token():
    """Test get_access_token returns None for OSS mode."""
    assert get_access_token() is None


def test_get_provider_tokens():
    """Test get_provider_tokens returns empty dict for OSS mode."""
    assert get_provider_tokens() == {}


def test_get_user_settings_store():
    """Test get_user_settings_store returns a FileSettingsStore instance."""
    with patch("backend.persistence.auth.get_app_settings_root", return_value="/tmp/test_settings"):
        with patch("backend.persistence.auth.get_file_store") as mock_get_file_store:
            mock_file_store = MagicMock()
            mock_get_file_store.return_value = mock_file_store
            
            store = get_user_settings_store()
            
            assert isinstance(store, FileSettingsStore)
            mock_get_file_store.assert_called_once_with("local", local_data_root="/tmp/test_settings")


def test_get_user_secret_store():
    """Test get_user_secret_store returns a FileSecretsStore instance."""
    with patch("backend.persistence.auth.get_app_settings_root", return_value="/tmp/test_secrets"):
        with patch("backend.persistence.auth.get_file_store") as mock_get_file_store:
            mock_file_store = MagicMock()
            mock_get_file_store.return_value = mock_file_store
            
            store = get_user_secret_store()
            
            assert isinstance(store, FileSecretsStore)
            mock_get_file_store.assert_called_once_with("local", local_data_root="/tmp/test_secrets")


def test_get_secrets_store():
    """Test get_secrets_store aliases get_user_secret_store."""
    with patch("backend.persistence.auth.get_user_secret_store") as mock_get_store:
        mock_store = MagicMock()
        mock_get_store.return_value = mock_store
        
        result = get_secrets_store()
        
        assert result == mock_store
        mock_get_store.assert_called_once()


@pytest.mark.asyncio
async def test_get_user_settings():
    """Test get_user_settings loads settings from user settings store."""
    mock_settings = Settings(language="en")
    mock_store = MagicMock()
    mock_store.load = AsyncMock(return_value=mock_settings)

    with patch("backend.persistence.auth.get_user_settings_store", return_value=mock_store):
        settings = await get_user_settings()
        assert settings == mock_settings
        mock_store.load.assert_called_once()


@pytest.mark.asyncio
async def test_get_user_secrets():
    """Test get_user_secrets loads secrets from user secrets store."""
    mock_secrets = UserSecrets()
    mock_store = MagicMock()
    mock_store.load = AsyncMock(return_value=mock_secrets)

    with patch("backend.persistence.auth.get_user_secret_store", return_value=mock_store):
        secrets = await get_user_secrets()
        assert secrets == mock_secrets
        mock_store.load.assert_called_once()
