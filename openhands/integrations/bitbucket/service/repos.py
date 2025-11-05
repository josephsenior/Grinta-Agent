from __future__ import annotations

import re
from typing import TYPE_CHECKING, Any
from urllib.parse import urlparse

from openhands.integrations.bitbucket.service.base import BitBucketMixinBase

if TYPE_CHECKING:
    from openhands.integrations.service_types import Repository, SuggestedTask
    from openhands.server.types import AppMode


class BitBucketReposMixin(BitBucketMixinBase):
    """Mixin for BitBucket repository-related operations."""

    async def _search_public_repository(self, query: str) -> list[Repository]:
        """Search for a public repository by URL."""
        repositories = []
        try:
            parsed_url = urlparse(query)
            path_segments = [segment for segment in parsed_url.path.split("/") if segment]
            if len(path_segments) >= 2:
                workspace_slug = path_segments[0]
                repo_name = path_segments[1]
                repo = await self.get_repository_details_from_repo_name(f"{workspace_slug}/{repo_name}")
                repositories.append(repo)
        except (ValueError, IndexError):
            pass
        return repositories

    async def _search_workspace_repository(self, query: str, per_page: int, sort: str) -> list[Repository]:
        """Search for repository within a specific workspace."""
        workspace_slug, repo_query = query.split("/", 1)
        return await self.get_paginated_repos(1, per_page, sort, workspace_slug, repo_query)

    async def _search_matching_workspaces(
        self,
        query: str,
        per_page: int,
        sort: str,
        all_installations: list,
    ) -> list[Repository]:
        """Search repositories in workspaces that match the query."""
        repositories = []
        matching_workspace_slugs = [installation for installation in all_installations if query in installation]

        for workspace_slug in matching_workspace_slugs:
            try:
                repos = await self.get_paginated_repos(1, per_page, sort, workspace_slug)
                repositories.extend(repos)
            except Exception:
                continue

        return repositories

    async def _search_all_workspaces(
        self,
        query: str,
        per_page: int,
        sort: str,
        all_installations: list,
    ) -> list[Repository]:
        """Search repositories across all workspaces."""
        repositories = []

        for workspace_slug in all_installations:
            try:
                repos = await self.get_paginated_repos(1, per_page, sort, workspace_slug, query)
                repositories.extend(repos)
            except Exception:
                continue

        return repositories

    async def search_repositories(
        self,
        query: str,
        per_page: int,
        sort: str,
        order: str,
        public: bool,
    ) -> list[Repository]:
        """Search for repositories."""
        if public:
            return await self._search_public_repository(query)

        if "/" in query:
            return await self._search_workspace_repository(query, per_page, sort)

        all_installations = await self.get_installations()
        repositories = []

        # Search in matching workspaces
        matching_repos = await self._search_matching_workspaces(query, per_page, sort, all_installations)
        repositories.extend(matching_repos)

        # Search across all workspaces
        all_workspace_repos = await self._search_all_workspaces(query, per_page, sort, all_installations)
        repositories.extend(all_workspace_repos)

        return repositories

    async def _get_user_workspaces(self) -> list[dict[str, Any]]:
        """Get all workspaces the user has access to."""
        url = f"{self.BASE_URL}/workspaces"
        data, _ = await self._make_request(url)
        return data.get("values", [])

    async def get_installations(self, query: str | None = None, limit: int = 100) -> list[str]:
        workspaces_url = f"{self.BASE_URL}/workspaces"
        params = {}
        if query:
            params["q"] = f'name~"{query}"'
        workspaces = await self._fetch_paginated_data(workspaces_url, params, limit)
        installations: list[str] = [workspace["slug"] for workspace in workspaces]
        return installations

    async def get_paginated_repos(
        self,
        page: int,
        per_page: int,
        sort: str,
        installation_id: str | None,
        query: str | None = None,
    ) -> list[Repository]:
        """Get paginated repositories for a specific workspace.

        Args:
            page: The page number to fetch
            per_page: The number of repositories per page
            sort: The sort field ('pushed', 'updated', 'created', 'full_name')
            installation_id: The workspace slug to fetch repositories from (as int, will be converted to string)
            query: Optional search query to filter repositories by name

        Returns:
            A list of Repository objects
        """
        if not installation_id:
            return []
        workspace_slug = installation_id
        workspace_repos_url = f"{self.BASE_URL}/repositories/{workspace_slug}"
        bitbucket_sort = sort
        if bitbucket_sort == "created":
            bitbucket_sort = "-created_on"
        elif bitbucket_sort == "full_name":
            bitbucket_sort = "name"
        else:
            bitbucket_sort = "-updated_on"
        params = {"pagelen": per_page, "page": page, "sort": bitbucket_sort}
        if query:
            params["q"] = f'name~"{query}"'
        response, _headers = await self._make_request(workspace_repos_url, params)
        repos = response.get("values", [])
        next_link = response.get("next", "")
        formatted_link_header = ""
        if next_link:
            if page_match := re.search("[?&]page=(\\d+)", next_link):
                next_page = page_match[1]
                formatted_link_header = f'<{workspace_repos_url}?page={next_page}>; rel="next"'
            else:
                formatted_link_header = f'<{next_link}>; rel="next"'
        return [self._parse_repository(repo, link_header=formatted_link_header) for repo in repos]

    async def get_all_repositories(self, sort: str, app_mode: AppMode) -> list[Repository]:
        """Get repositories for the authenticated user using workspaces endpoint.

        This method gets all repositories (both public and private) that the user has access to
        by iterating through their workspaces and fetching repositories from each workspace.
        This approach is more comprehensive and efficient than the previous implementation
        that made separate calls for public and private repositories.
        """
        MAX_REPOS = 1000
        PER_PAGE = 100
        repositories: list[Repository] = []
        workspaces_url = f"{self.BASE_URL}/workspaces"
        workspaces = await self._fetch_paginated_data(workspaces_url, {}, MAX_REPOS)
        for workspace in workspaces:
            workspace_slug = workspace.get("slug")
            if not workspace_slug:
                continue
            workspace_repos_url = f"{self.BASE_URL}/repositories/{workspace_slug}"
            bitbucket_sort = sort
            if bitbucket_sort == "created":
                bitbucket_sort = "-created_on"
            elif bitbucket_sort == "full_name":
                bitbucket_sort = "name"
            else:
                bitbucket_sort = "-updated_on"
            params = {"pagelen": PER_PAGE, "sort": bitbucket_sort}
            workspace_repos = await self._fetch_paginated_data(
                workspace_repos_url,
                params,
                MAX_REPOS - len(repositories),
            )
            for repo in workspace_repos:
                repositories.append(self._parse_repository(repo))
                if len(repositories) >= MAX_REPOS:
                    break
            if len(repositories) >= MAX_REPOS:
                break
        return repositories

    async def get_suggested_tasks(self) -> list[SuggestedTask]:
        """Get suggested tasks for the authenticated user across all repositories."""
        return []
