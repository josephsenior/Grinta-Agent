"""GitHub service assembly combining mixins for Forge integrations."""

from __future__ import annotations

import os
from typing import TYPE_CHECKING

from backend.integrations.github.service import (
    GitHubBranchesMixin,
    GitHubFeaturesMixin,
    GitHubPRsMixin,
    GitHubReposMixin,
    GitHubResolverMixin,
)
from backend.integrations.service_types import (
    BaseGitService,
    GitService,
    InstallationsService,
    ProviderType,
)
from backend.utils.import_utils import get_impl

if TYPE_CHECKING:
    from pydantic import SecretStr


class GitHubService(
    GitHubBranchesMixin,
    GitHubFeaturesMixin,
    GitHubPRsMixin,
    GitHubReposMixin,
    GitHubResolverMixin,
    BaseGitService,
    GitService,
    InstallationsService,
):
    """Assembled GitHub service class combining mixins by feature area.

    TODO: This doesn't seem a good candidate for the get_impl() pattern. What are the abstract methods we should actually separate and implement here?
    This is an extension point in Forge that allows applications to customize GitHub
    integration behavior. Applications can substitute their own implementation by:
    1. Creating a class that inherits from GitService
    2. Implementing all required methods
    3. Setting server_config.github_service_class to the fully qualified name of the class

    The class is instantiated via get_impl() in forge.server.shared.py.
    """

    BASE_URL = "https://api.github.com"
    GRAPHQL_URL = "https://api.github.com/graphql"

    def __init__(
        self,
        user_id: str | None = None,
        external_auth_id: str | None = None,
        external_auth_token: SecretStr | None = None,
        token: SecretStr | None = None,
        external_token_manager: bool = False,
        base_domain: str | None = None,
    ) -> None:
        """Initialize the GitHub service with authentication context and domain overrides."""
        self.user_id = user_id
        self.external_token_manager = external_token_manager
        self.token = token
        if base_domain and base_domain != "github.com":
            self.BASE_URL = f"https://{base_domain}/api/v3"
            self.GRAPHQL_URL = f"https://{base_domain}/api/graphql"
        self.external_auth_id = external_auth_id
        self.external_auth_token = external_auth_token

    @property
    def provider(self) -> str:
        """Return provider identifier for GitHub service."""
        return ProviderType.GITHUB.value


github_service_cls = os.environ.get(
    "FORGE_GITHUB_SERVICE_CLS",
    "backend.integrations.github.github_service.GitHubService",
)
GithubServiceImpl = get_impl(GitHubService, github_service_cls)
