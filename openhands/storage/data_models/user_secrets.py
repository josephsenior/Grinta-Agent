from __future__ import annotations

from types import MappingProxyType
from typing import TYPE_CHECKING, Any

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    SerializationInfo,
    field_serializer,
    model_validator,
)
from pydantic.json import pydantic_encoder

from openhands.core.pydantic_compat import model_dump_with_options
from openhands.integrations.provider import (
    CUSTOM_SECRETS_TYPE,
    CUSTOM_SECRETS_TYPE_WITH_JSON_SCHEMA,
    PROVIDER_TOKEN_TYPE,
    PROVIDER_TOKEN_TYPE_WITH_JSON_SCHEMA,
    CustomSecret,
    ProviderToken,
)
from openhands.integrations.service_types import ProviderType

if TYPE_CHECKING:
    from openhands.events.stream import EventStream


class UserSecrets(BaseModel):
    provider_tokens: PROVIDER_TOKEN_TYPE_WITH_JSON_SCHEMA = Field(default_factory=lambda: MappingProxyType({}))
    custom_secrets: CUSTOM_SECRETS_TYPE_WITH_JSON_SCHEMA = Field(default_factory=lambda: MappingProxyType({}))
    model_config = ConfigDict(frozen=True, validate_assignment=True, arbitrary_types_allowed=True)

    @field_serializer("provider_tokens")
    def provider_tokens_serializer(
        self,
        provider_tokens: PROVIDER_TOKEN_TYPE,
        info: SerializationInfo,
    ) -> dict[str, dict[str, str | Any]]:
        tokens = {}
        expose_secrets = info.context and info.context.get("expose_secrets", False)
        for token_type, provider_token in provider_tokens.items():
            if not provider_token or not provider_token.token:
                continue
            token_type_str = token_type.value if isinstance(token_type, ProviderType) else str(token_type)
            token = None
            token = (
                provider_token.token.get_secret_value() if expose_secrets else pydantic_encoder(provider_token.token)
            )
            tokens[token_type_str] = {"token": token, "host": provider_token.host, "user_id": provider_token.user_id}
        return tokens

    @field_serializer("custom_secrets")
    def custom_secrets_serializer(self, custom_secrets: CUSTOM_SECRETS_TYPE, info: SerializationInfo):
        secrets = {}
        expose_secrets = info.context and info.context.get("expose_secrets", False)
        if custom_secrets:
            for secret_name, secret_value in custom_secrets.items():
                secrets[secret_name] = {
                    "secret": (
                        secret_value.secret.get_secret_value()
                        if expose_secrets
                        else pydantic_encoder(secret_value.secret)
                    ),
                    "description": secret_value.description,
                }
        return secrets

    @classmethod
    def _convert_provider_tokens(cls, tokens: dict | MappingProxyType) -> MappingProxyType:
        """Convert provider tokens dictionary to MappingProxyType.

        Args:
            tokens: Provider tokens as dict or MappingProxyType.

        Returns:
            MappingProxyType: Converted provider tokens.
        """
        if isinstance(tokens, MappingProxyType):
            return tokens

        converted_tokens = {}
        for key, value in tokens.items():
            try:
                provider_type = ProviderType(key) if isinstance(key, str) else key
                converted_tokens[provider_type] = ProviderToken.from_value(value)
            except ValueError:
                continue

        return MappingProxyType(converted_tokens)

    @classmethod
    def _convert_custom_secrets(cls, secrets: dict | MappingProxyType) -> MappingProxyType:
        """Convert custom secrets dictionary to MappingProxyType.

        Args:
            secrets: Custom secrets as dict or MappingProxyType.

        Returns:
            MappingProxyType: Converted custom secrets.
        """
        if isinstance(secrets, MappingProxyType):
            return secrets

        converted_secrets = {}
        for key, value in secrets.items():
            try:
                converted_secrets[key] = CustomSecret.from_value(value)
            except ValueError:
                continue

        return MappingProxyType(converted_secrets)

    @model_validator(mode="before")
    @classmethod
    def convert_dict_to_mappingproxy(
        cls,
        data: dict[str, dict[str, Any] | MappingProxyType] | PROVIDER_TOKEN_TYPE,
    ) -> dict[str, MappingProxyType | None]:
        """Custom deserializer to convert dictionary into MappingProxyType.

        Args:
            data: Input data containing provider tokens and custom secrets.

        Returns:
            dict: Dictionary with converted MappingProxyType objects.

        Raises:
            ValueError: If data is not a dictionary.
        """
        if not isinstance(data, dict):
            msg = "UserSecrets must be initialized with a dictionary"
            raise ValueError(msg)

        new_data: dict[str, MappingProxyType | None] = {}

        # Convert provider tokens if present
        if "provider_tokens" in data:
            new_data["provider_tokens"] = cls._convert_provider_tokens(data["provider_tokens"])

        # Convert custom secrets if present
        if "custom_secrets" in data:
            new_data["custom_secrets"] = cls._convert_custom_secrets(data["custom_secrets"])

        return new_data

    def set_event_stream_secrets(self, event_stream: EventStream) -> None:
        """This ensures that provider tokens and custom secrets are masked from the event stream.

        Args:
            event_stream: Agent session's event stream
        """
        secrets = self.get_env_vars()
        event_stream.set_secrets(secrets)

    def get_env_vars(self) -> dict[str, str]:
        secret_store = model_dump_with_options(self, context={"expose_secrets": True})
        custom_secrets = secret_store.get("custom_secrets", {})
        return {secret_name: value["secret"] for secret_name, value in custom_secrets.items()}

    def get_custom_secrets_descriptions(self) -> dict[str, str]:
        return {secret_name: secret.description for secret_name, secret in self.custom_secrets.items()}
