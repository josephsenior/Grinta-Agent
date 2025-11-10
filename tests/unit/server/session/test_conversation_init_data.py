"""Tests for `ConversationInitData` model."""

from __future__ import annotations

import pytest

from types import MappingProxyType

from forge.server.session.conversation_init_data import ConversationInitData
from forge.integrations.service_types import ProviderType
from pydantic import ValidationError


def test_conversation_init_data_defaults():
    data = ConversationInitData()
    assert data.git_provider_tokens is None
    assert data.custom_secrets is None
    assert data.selected_repository is None
    assert data.model_dump()["enable_default_condenser"] is True


def test_conversation_init_data_assignment_frozen_fields():
    tokens = MappingProxyType({"github": "token"})
    secrets = MappingProxyType({"secret": "value"})
    data = ConversationInitData(git_provider_tokens=tokens, custom_secrets=secrets, git_provider=ProviderType.GITHUB)
    with pytest.raises(ValidationError):
        data.git_provider_tokens = {}
    with pytest.raises(ValidationError):
        data.custom_secrets = {}
    assert data.git_provider == ProviderType.GITHUB
