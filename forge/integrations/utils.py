"""Utilities for identifying which Git provider a token belongs to."""

from __future__ import annotations

from typing import TYPE_CHECKING

from forge.core.logger import forge_logger as logger
from forge.integrations.bitbucket.bitbucket_service import BitBucketService
from forge.integrations.github.github_service import GitHubService
from forge.integrations.gitlab.gitlab_service import GitLabService
from forge.integrations.provider import ProviderType

if TYPE_CHECKING:
    from pydantic import SecretStr


async def validate_provider_token(token: SecretStr, base_domain: str | None = None) -> ProviderType | None:
    """Determine whether a token is for GitHub, GitLab, or Bitbucket by attempting to get user info.

    from the services.

    Args:
        token: The token to check
        base_domain: Optional base domain for the service

    Returns:
        'github' if it's a GitHub token
        'gitlab' if it's a GitLab token
        'bitbucket' if it's a Bitbucket token
        None if the token is invalid for all services

    """
    if token is None:
        return None
    github_error = None
    try:
        github_service = GitHubService(token=token, base_domain=base_domain)
        await github_service.verify_access()
        return ProviderType.GITHUB
    except Exception as e:
        github_error = e
    gitlab_error = None
    try:
        gitlab_service = GitLabService(token=token, base_domain=base_domain)
        await gitlab_service.get_user()
        return ProviderType.GITLAB
    except Exception as e:
        gitlab_error = e
    bitbucket_error = None
    try:
        bitbucket_service = BitBucketService(token=token, base_domain=base_domain)
        await bitbucket_service.get_user()
        return ProviderType.BITBUCKET
    except Exception as e:
        bitbucket_error = e
    logger.debug("Failed to validate token: %s \n %s \n %s", github_error, gitlab_error, bitbucket_error)
    return None
