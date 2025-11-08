"""HTTP Client Protocol for Git Service Integrations."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, Any

from pydantic import SecretStr

from forge.core.logger import forge_logger as logger
from forge.integrations.service_types import (
    AuthenticationError,
    RateLimitError,
    RequestMethod,
    ResourceNotFoundError,
    UnknownException,
)

if TYPE_CHECKING:
    from httpx import AsyncClient, HTTPError, HTTPStatusError


class HTTPClient(ABC):
    """Abstract base class defining the HTTP client interface for Git service integrations.

    This class abstracts the common HTTP client functionality needed by all
    Git service providers (GitHub, GitLab, BitBucket) while keeping inheritance in place.
    """

    token: SecretStr = SecretStr("")
    refresh: bool = False
    external_auth_id: str | None = None
    external_auth_token: SecretStr | None = None
    external_token_manager: bool = False
    base_domain: str | None = None

    @property
    @abstractmethod
    def provider(self) -> str:
        """Return provider identifier string for concrete integration."""
        ...

    @abstractmethod
    async def get_latest_token(self) -> SecretStr | None:
        """Get the latest working token for the service."""
        ...

    @abstractmethod
    async def _get_headers(self) -> dict[str, Any]:
        """Get HTTP headers for API requests."""
        ...

    @abstractmethod
    async def _make_request(
        self,
        url: str,
        params: dict | None = None,
        method: RequestMethod = RequestMethod.GET,
    ) -> tuple[Any, dict]:
        """Make an HTTP request to the Git service API."""
        ...

    def _has_token_expired(self, status_code: int) -> bool:
        """Check if the token has expired based on HTTP status code."""
        return status_code == 401

    async def execute_request(
        self,
        client: AsyncClient,
        url: str,
        headers: dict,
        params: dict | None,
        method: RequestMethod = RequestMethod.GET,
    ):
        """Execute an HTTP request using the provided client."""
        if method == RequestMethod.POST:
            return await client.post(url, headers=headers, json=params)
        return await client.get(url, headers=headers, params=params)

    def handle_http_status_error(
        self,
        e: HTTPStatusError,
    ) -> AuthenticationError | RateLimitError | ResourceNotFoundError | UnknownException:
        """Handle HTTP status errors and convert them to appropriate exceptions."""
        if e.response.status_code == 401:
            return AuthenticationError(f"Invalid {self.provider} token")
        if e.response.status_code == 404:
            return ResourceNotFoundError(f"Resource not found on {self.provider} API: {e}")
        if e.response.status_code == 429:
            logger.warning("Rate limit exceeded on %s API: %s", self.provider, e)
            return RateLimitError(f"{self.provider} API rate limit exceeded")
        logger.warning("Status error on %s API: %s", self.provider, e)
        return UnknownException(f"Unknown error: {e}")

    def handle_http_error(self, e: HTTPError) -> UnknownException:
        """Handle general HTTP errors."""
        logger.warning("HTTP error on %s API: %s : %s", self.provider, type(e).__name__, e)
        return UnknownException(f"HTTP error {type(e).__name__} : {e}")
