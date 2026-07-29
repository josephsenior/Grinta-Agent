"""Tests for backend.persistence.conversation.conversation_validator."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from backend.persistence.conversation.conversation_validator import (
    ConversationAccessDenied,
    ConversationValidator,
    create_conversation_validator,
)

# ── ConversationAccessDenied ──────────────────────────────────────────


class TestConversationAccessDenied:
    def test_is_exception(self):
        exc = ConversationAccessDenied('nope')
        assert isinstance(exc, Exception)

    def test_message_preserved(self):
        exc = ConversationAccessDenied('access denied for user X')
        assert 'access denied for user X' in str(exc)


# ── ConversationValidator.__init__ ────────────────────────────────────


class TestConversationValidatorInit:
    def test_explicit_mode_permissive(self):
        v = ConversationValidator(mode='permissive')
        assert v._mode == 'permissive'

    def test_explicit_mode_strict(self):
        v = ConversationValidator(mode='strict')
        assert v._mode == 'strict'

    def test_env_var_override(self, monkeypatch):
        monkeypatch.setenv('APP_VALIDATION_MODE', 'strict')
        v = ConversationValidator()
        assert v._mode == 'strict'

    def test_env_var_permissive(self, monkeypatch):
        monkeypatch.setenv('APP_VALIDATION_MODE', 'permissive')
        v = ConversationValidator()
        assert v._mode == 'permissive'

    def test_env_var_invalid_falls_to_config(self, monkeypatch):
        monkeypatch.setenv('APP_VALIDATION_MODE', 'bogus')
        mock_config = MagicMock()
        mock_config.security.validation_mode = 'strict'
        with patch(
            'backend.persistence.conversation.conversation_validator.load_app_config',
            return_value=mock_config,
        ):
            v = ConversationValidator()
            assert v._mode == 'strict'

    def test_fallback_default_permissive(self, monkeypatch):
        monkeypatch.delenv('APP_VALIDATION_MODE', raising=False)
        with patch(
            'backend.persistence.conversation.conversation_validator.load_app_config',
            side_effect=RuntimeError('no config'),
        ):
            v = ConversationValidator()
            assert v._mode == 'permissive'


# ── _extract_user_id ──────────────────────────────────────────────────


class TestExtractUserId:
    def test_returns_none_by_default(self):
        v = ConversationValidator(mode='permissive')
        assert v._extract_user_id('Bearer token') is None

    def test_returns_none_for_none_header(self):
        v = ConversationValidator(mode='permissive')
        assert v._extract_user_id(None) is None


# ── validate (permissive) ────────────────────────────────────────────


class TestValidatePermissive:
    @pytest.fixture
    def validator(self):
        return ConversationValidator(mode='permissive')

    async def test_permissive_creates_metadata_when_missing(self, validator):
        mock_meta = MagicMock()
        mock_meta.user_id = None
        validator._ensure_metadata_exists = AsyncMock(return_value=mock_meta)

        result = await validator.validate('conv-1', '', None)
        assert result == 'oss_user'


class TestEnsureMetadataExists:
    @pytest.mark.asyncio
    async def test_ensure_metadata_creates_on_file_not_found(self):
        validator = ConversationValidator(mode='permissive')
        mock_store = MagicMock()
        mock_store.get_metadata = AsyncMock(
            side_effect=FileNotFoundError('Missing metadata')
        )
        mock_new_meta = MagicMock()
        validator._create_metadata = AsyncMock(return_value=mock_new_meta)

        with (
            patch(
                'backend.persistence.conversation.conversation_validator.load_app_config'
            ),
            patch(
                'backend.persistence.conversation.conversation_validator.get_impl'
            ) as mock_impl,
        ):
            mock_store_cls = MagicMock()
            mock_store_cls.get_instance = AsyncMock(return_value=mock_store)
            mock_impl.return_value = mock_store_cls

            res = await validator._ensure_metadata_exists('conv_new', 'user_1')
            assert res == mock_new_meta
            validator._create_metadata.assert_called_once_with(
                mock_store, 'conv_new', 'user_1'
            )


class TestValidateStrict:
    @pytest.mark.asyncio
    async def test_strict_anonymous_rejected(self):
        validator = ConversationValidator(mode='strict')
        with patch.object(validator, '_extract_user_id', return_value=None):
            with pytest.raises(
                ConversationAccessDenied, match='Anonymous access is not allowed'
            ):
                await validator.validate('conv_123', '', None)

    @pytest.mark.asyncio
    async def test_create_conversation_validator_factory(self):
        v = create_conversation_validator()
        assert isinstance(v, ConversationValidator)
