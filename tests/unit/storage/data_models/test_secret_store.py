from __future__ import annotations
from types import MappingProxyType
from typing import Any

import pytest
from pydantic import SecretStr

from forge.integrations.provider import CustomSecret, ProviderToken, ProviderType
from forge.storage.data_models.user_secrets import UserSecrets


class TestUserSecrets:
    def test_adding_only_provider_tokens(self):
        """Test adding only provider tokens to the UserSecrets."""
        github_token = ProviderToken(
            token=SecretStr("github-token-123"), user_id="user1"
        )
        gitlab_token = ProviderToken(
            token=SecretStr("gitlab-token-456"), user_id="user2"
        )
        provider_tokens = {
            ProviderType.GITHUB: github_token,
            ProviderType.GITLAB: gitlab_token,
        }
        store = UserSecrets(provider_tokens=provider_tokens)
        assert isinstance(store.provider_tokens, MappingProxyType)
        assert len(store.provider_tokens) == 2
        assert (
            store.provider_tokens[ProviderType.GITHUB].token.get_secret_value()
            == "github-token-123"
        )
        assert store.provider_tokens[ProviderType.GITHUB].user_id == "user1"
        assert (
            store.provider_tokens[ProviderType.GITLAB].token.get_secret_value()
            == "gitlab-token-456"
        )
        assert store.provider_tokens[ProviderType.GITLAB].user_id == "user2"
        assert isinstance(store.custom_secrets, MappingProxyType)
        assert len(store.custom_secrets) == 0

    def test_adding_only_custom_secrets(self):
        """Test adding only custom secrets to the UserSecrets."""
        custom_secrets = {
            "API_KEY": CustomSecret(
                secret=SecretStr("api-key-123"), description="API key"
            ),
            "DATABASE_PASSWORD": CustomSecret(
                secret=SecretStr("db-pass-456"), description="Database password"
            ),
        }
        store = UserSecrets(custom_secrets=custom_secrets)
        assert isinstance(store.custom_secrets, MappingProxyType)
        assert len(store.custom_secrets) == 2
        assert (
            store.custom_secrets["API_KEY"].secret.get_secret_value() == "api-key-123"
        )
        assert (
            store.custom_secrets["DATABASE_PASSWORD"].secret.get_secret_value()
            == "db-pass-456"
        )
        assert isinstance(store.provider_tokens, MappingProxyType)
        assert len(store.provider_tokens) == 0

    def test_initializing_with_mixed_types(self):
        """Test initializing the store with mixed types (dict and MappingProxyType)."""
        provider_tokens_dict = {
            ProviderType.GITHUB: {"token": "github-token-123", "user_id": "user1"}
        }
        custom_secret = CustomSecret(
            secret=SecretStr("api-key-123"), description="API key"
        )
        custom_secrets_proxy = MappingProxyType({"API_KEY": custom_secret})
        store1 = UserSecrets(
            provider_tokens=provider_tokens_dict, custom_secrets=custom_secrets_proxy
        )
        assert isinstance(store1.provider_tokens, MappingProxyType)
        assert isinstance(store1.custom_secrets, MappingProxyType)
        assert (
            store1.provider_tokens[ProviderType.GITHUB].token.get_secret_value()
            == "github-token-123"
        )
        assert (
            store1.custom_secrets["API_KEY"].secret.get_secret_value() == "api-key-123"
        )
        provider_token = ProviderToken(
            token=SecretStr("gitlab-token-456"), user_id="user2"
        )
        provider_tokens_proxy = MappingProxyType({ProviderType.GITLAB: provider_token})
        custom_secrets_dict = {
            "API_KEY": {"secret": "api-key-123", "description": "API key"}
        }
        store2 = UserSecrets(
            provider_tokens=provider_tokens_proxy, custom_secrets=custom_secrets_dict
        )
        assert isinstance(store2.provider_tokens, MappingProxyType)
        assert isinstance(store2.custom_secrets, MappingProxyType)
        assert (
            store2.provider_tokens[ProviderType.GITLAB].token.get_secret_value()
            == "gitlab-token-456"
        )
        assert (
            store2.custom_secrets["API_KEY"].secret.get_secret_value() == "api-key-123"
        )

    def test_model_copy_update_fields(self):
        """Test using model_copy to update fields without affecting other fields."""
        github_token = ProviderToken(
            token=SecretStr("github-token-123"), user_id="user1"
        )
        custom_secret = {
            "API_KEY": CustomSecret(
                secret=SecretStr("api-key-123"), description="API key"
            )
        }
        initial_store = UserSecrets(
            provider_tokens=MappingProxyType({ProviderType.GITHUB: github_token}),
            custom_secrets=MappingProxyType(custom_secret),
        )
        gitlab_token = ProviderToken(
            token=SecretStr("gitlab-token-456"), user_id="user2"
        )
        updated_provider_tokens = MappingProxyType(
            {ProviderType.GITHUB: github_token, ProviderType.GITLAB: gitlab_token}
        )
        updated_store1 = initial_store.model_copy(
            update={"provider_tokens": updated_provider_tokens}
        )
        assert len(updated_store1.provider_tokens) == 2
        assert (
            updated_store1.provider_tokens[ProviderType.GITHUB].token.get_secret_value()
            == "github-token-123"
        )
        assert (
            updated_store1.provider_tokens[ProviderType.GITLAB].token.get_secret_value()
            == "gitlab-token-456"
        )
        assert len(updated_store1.custom_secrets) == 1
        assert (
            updated_store1.custom_secrets["API_KEY"].secret.get_secret_value()
            == "api-key-123"
        )
        updated_custom_secrets = MappingProxyType(
            {
                "API_KEY": CustomSecret(
                    secret=SecretStr("api-key-123"), description="API key"
                ),
                "DATABASE_PASSWORD": CustomSecret(
                    secret=SecretStr("db-pass-456"), description="DB password"
                ),
            }
        )
        updated_store2 = initial_store.model_copy(
            update={"custom_secrets": updated_custom_secrets}
        )
        assert len(updated_store2.provider_tokens) == 1
        assert (
            updated_store2.provider_tokens[ProviderType.GITHUB].token.get_secret_value()
            == "github-token-123"
        )
        assert len(updated_store2.custom_secrets) == 2
        assert (
            updated_store2.custom_secrets["API_KEY"].secret.get_secret_value()
            == "api-key-123"
        )
        assert (
            updated_store2.custom_secrets["DATABASE_PASSWORD"].secret.get_secret_value()
            == "db-pass-456"
        )

    def test_serialization_with_expose_secrets(self):
        """Test serializing the UserSecrets with expose_secrets=True."""
        github_token = ProviderToken(
            token=SecretStr("github-token-123"), user_id="user1"
        )
        custom_secrets = {
            "API_KEY": CustomSecret(
                secret=SecretStr("api-key-123"), description="API key"
            )
        }
        store = UserSecrets(
            provider_tokens=MappingProxyType({ProviderType.GITHUB: github_token}),
            custom_secrets=MappingProxyType(custom_secrets),
        )
        serialized_provider_tokens = store.provider_tokens_serializer(
            store.provider_tokens, SerializationInfo(context={"expose_secrets": True})
        )
        serialized_custom_secrets = store.custom_secrets_serializer(
            store.custom_secrets, SerializationInfo(context={"expose_secrets": True})
        )
        assert serialized_provider_tokens["github"]["token"] == "github-token-123"
        assert serialized_provider_tokens["github"]["user_id"] == "user1"
        assert serialized_custom_secrets["API_KEY"]["secret"] == "api-key-123"
        assert serialized_custom_secrets["API_KEY"]["description"] == "API key"
        hidden_provider_tokens = store.provider_tokens_serializer(
            store.provider_tokens, SerializationInfo(context={"expose_secrets": False})
        )
        hidden_custom_secrets = store.custom_secrets_serializer(
            store.custom_secrets, SerializationInfo(context={"expose_secrets": False})
        )
        assert hidden_provider_tokens["github"]["token"] != "github-token-123"
        assert "**" in hidden_provider_tokens["github"]["token"]
        assert hidden_custom_secrets["API_KEY"]["secret"] != "api-key-123"
        assert "**" in hidden_custom_secrets["API_KEY"]["secret"]

    def test_initializing_provider_tokens_with_mixed_value_types(self):
        """Test initializing provider tokens with both plain strings and SecretStr objects."""
        provider_tokens_dict = {
            ProviderType.GITHUB: {"token": "github-token-123", "user_id": "user1"},
            ProviderType.GITLAB: {"token": "gitlab-token-456", "user_id": "user2"},
        }
        gitlab_token = ProviderToken(
            token=SecretStr("gitlab-token-456"), user_id="user2"
        )
        mixed_provider_tokens = {
            ProviderType.GITHUB: provider_tokens_dict[ProviderType.GITHUB],
            ProviderType.GITLAB: gitlab_token,
        }
        store = UserSecrets(provider_tokens=mixed_provider_tokens)
        assert isinstance(store.provider_tokens, MappingProxyType)
        assert len(store.provider_tokens) == 2
        github_token = store.provider_tokens[ProviderType.GITHUB]
        assert isinstance(github_token.token, SecretStr)
        assert github_token.token.get_secret_value() == "github-token-123"
        assert github_token.user_id == "user1"
        gitlab_token_result = store.provider_tokens[ProviderType.GITLAB]
        assert isinstance(gitlab_token_result.token, SecretStr)
        assert gitlab_token_result.token.get_secret_value() == "gitlab-token-456"
        assert gitlab_token_result.user_id == "user2"

    def test_initializing_custom_secrets_with_mixed_value_types(self):
        """Test initializing custom secrets with both plain strings and SecretStr objects."""
        custom_secrets_dict = {
            "API_KEY": {"secret": "api-key-123", "description": "API key"},
            "DATABASE_PASSWORD": CustomSecret(
                secret=SecretStr("db-pass-456"), description="DB password"
            ),
        }
        store = UserSecrets(custom_secrets=custom_secrets_dict)
        assert isinstance(store.custom_secrets, MappingProxyType)
        assert len(store.custom_secrets) == 2
        assert isinstance(store.custom_secrets["API_KEY"], CustomSecret)
        assert (
            store.custom_secrets["API_KEY"].secret.get_secret_value() == "api-key-123"
        )
        assert store.custom_secrets["API_KEY"].description == "API key"
        assert isinstance(store.custom_secrets["DATABASE_PASSWORD"], CustomSecret)
        assert (
            store.custom_secrets["DATABASE_PASSWORD"].secret.get_secret_value()
            == "db-pass-456"
        )
        assert store.custom_secrets["DATABASE_PASSWORD"].description == "DB password"

    def test_set_event_stream_secrets_and_env_helpers(self):
        """Ensure event stream receives redacted secrets and helper accessors behave."""
        secrets = {
            "API_KEY": CustomSecret(
                secret=SecretStr("api-key-xyz"), description="Primary API key"
            ),
            "SECONDARY": CustomSecret(
                secret=SecretStr("secondary-456"), description="Backup key"
            ),
        }
        store = UserSecrets(custom_secrets=secrets)
        captured: dict[str, str] = {}

        class DummyEventStream:
            def set_secrets(self, values: dict[str, str]) -> None:
                captured.update(values)

        store.set_event_stream_secrets(DummyEventStream())
        assert captured == {"API_KEY": "api-key-xyz", "SECONDARY": "secondary-456"}
        assert store.get_env_vars() == captured
        assert store.get_custom_secrets_descriptions() == {
            "API_KEY": "Primary API key",
            "SECONDARY": "Backup key",
        }

    def test_convert_dict_to_mappingproxy_none_and_invalid(self):
        """Validate convert helper handles None and invalid inputs."""
        converted = UserSecrets.convert_dict_to_mappingproxy(None)
        assert converted["provider_tokens"] is None
        assert isinstance(converted["custom_secrets"], MappingProxyType)
        assert len(converted["custom_secrets"]) == 0

        with pytest.raises(ValueError):
            UserSecrets.convert_dict_to_mappingproxy(["not", "a", "dict"])  # type: ignore[arg-type]

    def test_internal_conversion_helpers_ignore_invalid_entries(self):
        """Ensure helper conversions ignore invalid entries gracefully."""
        provider_result = UserSecrets._convert_provider_tokens(
            {"unknown": {"token": "abc", "user_id": "1"}}
        )
        assert isinstance(provider_result, MappingProxyType)
        assert len(provider_result) == 0

        custom_result = UserSecrets._convert_custom_secrets({"bad": {"secret": None}})
        assert isinstance(custom_result, MappingProxyType)
        assert isinstance(custom_result["bad"].secret, SecretStr)
        assert custom_result["bad"].description == ""

    def test_model_post_init_normalizes_none_values(self):
        """Ensure model post init normalizes None values into mapping proxies."""
        store = UserSecrets(provider_tokens=None, custom_secrets=None)
        assert isinstance(store.provider_tokens, MappingProxyType)
        assert len(store.provider_tokens) == 0
        assert isinstance(store.custom_secrets, MappingProxyType)
        assert len(store.custom_secrets) == 0


class SerializationInfo:
    def __init__(self, context: dict[str, Any] | None = None):
        self.context = context or {}
