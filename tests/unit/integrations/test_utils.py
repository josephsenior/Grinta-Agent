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


class GitLabSuccessStub(_BaseStub):
    async def get_user(self) -> dict:
        return {"id": 1}


class GitLabFailureStub(_BaseStub):
    async def get_user(self) -> dict:
        raise RuntimeError("gitlab auth failed")


class BitbucketSuccessStub(_BaseStub):
    async def get_user(self) -> dict:
        return {"id": 2}


class BitbucketFailureStub(_BaseStub):
    async def get_user(self) -> dict:
        raise RuntimeError("bitbucket auth failed")


@pytest.mark.asyncio
async def test_validate_provider_token_prefers_github(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(utils, "GitHubService", GitHubSuccessStub)
    monkeypatch.setattr(utils, "GitLabService", GitLabFailureStub)
    monkeypatch.setattr(utils, "BitBucketService", BitbucketFailureStub)

    result = await utils.validate_provider_token(SecretStr("token"))
    assert result == ProviderType.GITHUB


@pytest.mark.asyncio
async def test_validate_provider_token_falls_back_to_gitlab(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(utils, "GitHubService", GitHubFailureStub)
    monkeypatch.setattr(utils, "GitLabService", GitLabSuccessStub)
    monkeypatch.setattr(utils, "BitBucketService", BitbucketFailureStub)

    result = await utils.validate_provider_token(
        SecretStr("token"), base_domain="git.example.com"
    )
    assert result == ProviderType.GITLAB


@pytest.mark.asyncio
async def test_validate_provider_token_falls_back_to_bitbucket(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(utils, "GitHubService", GitHubFailureStub)
    monkeypatch.setattr(utils, "GitLabService", GitLabFailureStub)
    monkeypatch.setattr(utils, "BitBucketService", BitbucketSuccessStub)

    result = await utils.validate_provider_token(SecretStr("token"))
    assert result == ProviderType.BITBUCKET


@pytest.mark.asyncio
async def test_validate_provider_token_returns_none_when_all_fail(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(utils, "GitHubService", GitHubFailureStub)
    monkeypatch.setattr(utils, "GitLabService", GitLabFailureStub)
    monkeypatch.setattr(utils, "BitBucketService", BitbucketFailureStub)

    result = await utils.validate_provider_token(SecretStr("token"))
    assert result is None


@pytest.mark.asyncio
async def test_validate_provider_token_returns_none_for_missing_token(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    result = await utils.validate_provider_token(None)
    assert result is None
