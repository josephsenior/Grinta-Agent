"""GitLab mixin handling repository listing, search, and metadata helpers."""

from __future__ import annotations

from typing import TYPE_CHECKING

from forge.integrations.gitlab.service.base import GitLabMixinBase
from forge.integrations.service_types import OwnerType, ProviderType, Repository

if TYPE_CHECKING:
    from forge.server.types import AppMode


class GitLabReposMixin(GitLabMixinBase):
    """Methods for interacting with GitLab repositories."""

    def _parse_repository(
        self, repo: dict, link_header: str | None = None
    ) -> Repository:
        """Parse a GitLab API project response into a Repository object.

        Args:
            repo: Project data from GitLab API
            link_header: Optional link header for pagination

        Returns:
            Repository object

        """
        full_name = repo.get("path_with_namespace")
        if not isinstance(full_name, str):
            fallback = repo.get("path")
            full_name = str(fallback) if fallback is not None else ""

        return Repository(
            id=str(repo.get("id")),
            full_name=full_name,
            stargazers_count=repo.get("star_count"),
            git_provider=ProviderType.GITLAB,
            is_public=repo.get("visibility") == "public",
            owner_type=OwnerType.ORGANIZATION
            if repo.get("namespace", {}).get("kind") == "group"
            else OwnerType.USER,
            link_header=link_header,
            main_branch=repo.get("default_branch"),
        )

    def _parse_gitlab_url(self, url: str) -> str | None:
        """Parse a GitLab URL to extract the repository path.

        Expected format: https://{domain}/{group}/{possibly_subgroup}/{repo}
        Returns the full path from group onwards (e.g., 'group/subgroup/repo' or 'group/repo')
        """
        try:
            if "://" in url:
                url = url.split("://", 1)[1]
            if "/" in url:
                path = url.split("/", 1)[1]
            else:
                return None
            path = path.strip("/")
            if not path:
                return None
            path_parts = [part for part in path.split("/") if part]
            return None if len(path_parts) < 2 else "/".join(path_parts)
        except Exception:
            return None

    async def search_repositories(
        self,
        query: str,
        per_page: int = 30,
        sort: str = "updated",
        order: str = "desc",
        public: bool = False,
    ) -> list[Repository]:
        """Search GitLab projects; support direct URL lookup when public flag set."""
        if public:
            repo_path = self._parse_gitlab_url(query)
            if not repo_path:
                return []
            repository = await self.get_repository_details_from_repo_name(repo_path)
            return [repository]
        return await self.get_paginated_repos(1, per_page, sort, None, query)

    async def get_paginated_repos(
        self,
        page: int,
        per_page: int,
        sort: str,
        installation_id: str | None,
        query: str | None = None,
    ) -> list[Repository]:
        """Fetch a single page of GitLab projects visible to the authenticated user."""
        url = f"{self.BASE_URL}/projects"
        order_by = {
            "pushed": "last_activity_at",
            "updated": "last_activity_at",
            "created": "created_at",
            "full_name": "name",
        }.get(sort, "last_activity_at")
        params = {
            "page": str(page),
            "per_page": str(per_page),
            "order_by": order_by,
            "sort": "desc",
            "membership": True,
        }
        if query:
            params["search"] = query
            params["search_namespaces"] = True
        response, headers = await self._make_request(url, params)
        next_link: str = headers.get("Link", "")
        return [
            self._parse_repository(repo, link_header=next_link) for repo in response
        ]

    async def get_all_repositories(
        self, sort: str, app_mode: AppMode
    ) -> list[Repository]:
        """Return up to 1000 repositories the user has membership access to."""
        MAX_REPOS = 1000
        PER_PAGE = 100
        all_repos: list[dict] = []
        page = 1
        url = f"{self.BASE_URL}/projects"
        order_by = {
            "pushed": "last_activity_at",
            "updated": "last_activity_at",
            "created": "created_at",
            "full_name": "name",
        }.get(sort, "last_activity_at")
        while len(all_repos) < MAX_REPOS:
            params = {
                "page": str(page),
                "per_page": str(PER_PAGE),
                "order_by": order_by,
                "sort": "desc",
                "membership": 1,
            }
            response, headers = await self._make_request(url, params)
            if not response:
                break
            all_repos.extend(response)
            page += 1
            link_header = headers.get("Link", "")
            if 'rel="next"' not in link_header:
                break
        all_repos = all_repos[:MAX_REPOS]
        return [self._parse_repository(repo) for repo in all_repos]

    async def get_repository_details_from_repo_name(
        self, repository: str
    ) -> Repository:
        """Fetch repository metadata by fully-qualified path like group/subgroup/repo."""
        encoded_name = repository.replace("/", "%2F")
        url = f"{self.BASE_URL}/projects/{encoded_name}"
        repo, _ = await self._make_request(url)
        return self._parse_repository(repo)
