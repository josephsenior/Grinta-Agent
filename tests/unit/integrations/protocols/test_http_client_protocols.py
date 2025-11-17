from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
from pydantic import SecretStr

from forge.integrations.protocols.http_client import HTTPClient
from forge.integrations.service_types import (
    AuthenticationError,
    RateLimitError,
    RequestMethod,
    ResourceNotFoundError,
    UnknownException,
)


class DummyHTTPClient(HTTPClient):
    def __init__(self) -> None:
        self.token = SecretStr("dummy")

    @property
    def provider(self) -> str:
        return "dummy"

    async def get_latest_token(self) -> SecretStr | None:
        return self.token

    async def _get_headers(self) -> dict[str, str]:
        return {"Authorization": f"Bearer {self.token.get_secret_value()}"}

    async def _make_request(
        self,
        url: str,
        params: dict | None = None,
        method: RequestMethod = RequestMethod.GET,
    ) -> tuple[dict, dict]:
        return {"url": url, "params": params or {}, "method": method.value}, {}


@pytest.mark.asyncio
async def test_execute_request_get_method() -> None:
    client = DummyHTTPClient()
    http_client = SimpleNamespace(get=AsyncMock(return_value={"status": 200}))
    result = await client.execute_request(
        http_client, "https://example.com", {"h": "1"}, {"a": 1}
    )
    assert result == {"status": 200}
    http_client.get.assert_awaited_once_with(
        "https://example.com", headers={"h": "1"}, params={"a": 1}
    )


@pytest.mark.asyncio
async def test_execute_request_post_method() -> None:
    client = DummyHTTPClient()
    http_client = SimpleNamespace(post=AsyncMock(return_value={"status": 201}))
    result = await client.execute_request(
        http_client,
        "https://example.com",
        {"h": "1"},
        {"a": 1},
        method=RequestMethod.POST,
    )
    assert result == {"status": 201}
    http_client.post.assert_awaited_once_with(
        "https://example.com", headers={"h": "1"}, json={"a": 1}
    )


def test_has_token_expired_checks_status_code() -> None:
    client = DummyHTTPClient()
    assert client._has_token_expired(401)
    assert not client._has_token_expired(200)


class FakeHTTPStatusError(Exception):
    def __init__(self, status_code: int) -> None:
        self.response = SimpleNamespace(status_code=status_code)


def test_handle_http_status_error_authentication() -> None:
    client = DummyHTTPClient()
    exc = client.handle_http_status_error(FakeHTTPStatusError(401))
    assert isinstance(exc, AuthenticationError)


def test_handle_http_status_error_not_found() -> None:
    client = DummyHTTPClient()
    exc = client.handle_http_status_error(FakeHTTPStatusError(404))
    assert isinstance(exc, ResourceNotFoundError)


def test_handle_http_status_error_rate_limit() -> None:
    client = DummyHTTPClient()
    exc = client.handle_http_status_error(FakeHTTPStatusError(429))
    assert isinstance(exc, RateLimitError)


def test_handle_http_status_error_unknown() -> None:
    client = DummyHTTPClient()
    exc = client.handle_http_status_error(FakeHTTPStatusError(500))
    assert isinstance(exc, UnknownException)


def test_handle_http_error_returns_unknown_exception() -> None:
    client = DummyHTTPClient()
    exc = client.handle_http_error(RuntimeError("boom"))
    assert isinstance(exc, UnknownException)
