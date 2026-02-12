"""Utilities for identifying which Git provider a token belongs to."""

from __future__ import annotations

from pydantic import SecretStr

from backend.core.logger import forge_logger as logger
from backend.integrations.github.github_service import GitHubService
from backend.integrations.service_types import ProviderType


async def validate_provider_token(
    token: SecretStr | None, base_domain: str | None = None
) -> ProviderType | None:
    """Determine whether a token is for GitHub by attempting to get user info.

    from the services.

    Args:
        token: The token to check
        base_domain: Optional base domain for the service

    Returns:
        'github' if it's a GitHub token
        None if the token is invalid for all services

    """
    if token is None:
        return None
    try:
        github_service = GitHubService(token=token, base_domain=base_domain)
        await github_service.verify_access()
        return ProviderType.GITHUB
    except Exception as e:
        logger.debug(f"Failed to validate token against GitHub: {e}")
    logger.debug("Failed to validate token against supported providers")
    return None
