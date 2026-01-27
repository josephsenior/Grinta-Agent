from __future__ import annotations

import pytest
from pydantic import SecretStr

import forge.integrations.utils as utils
from forge.integrations.service_types import ProviderType


class _BaseStub:
    def __init__(self, token: SecretStr, base_domain: str | None = None) -> None:
        self.token = token
        self.base_domain = base_domain


class GitHubSuccessStub(_BaseStub):
    async def verify_access(self) -> None:
        return None


class GitHubFailureStub(_BaseStub):
    async def verify_access(self) -> None:
        raise RuntimeError("github auth failed")


@pytest.mark.asyncio
async def test_validate_provider_token_success(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(utils, "GitHubService", GitHubSuccessStub)

    result = await utils.validate_provider_token(SecretStr("token"))
    assert result == ProviderType.GITHUB


@pytest.mark.asyncio
async def test_validate_provider_token_failure(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(utils, "GitHubService", GitHubFailureStub)

    result = await utils.validate_provider_token(SecretStr("token"))
    assert result is None


@pytest.mark.asyncio
async def test_validate_provider_token_returns_none_for_missing_token(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    result = await utils.validate_provider_token(None)
    assert result is None
