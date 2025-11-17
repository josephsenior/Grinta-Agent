"""GitHub mixin handling repository listing, search, and installations."""

from __future__ import annotations

from datetime import datetime

from forge.core.logger import forge_logger as logger
from forge.integrations.github.service.base import GitHubMixinBase
from forge.integrations.service_types import OwnerType, ProviderType, Repository
from forge.server.types import AppMode


class GitHubReposMixin(GitHubMixinBase):
    """Methods for interacting with GitHub repositories (from both personal and app installations)."""

    async def get_installations(self) -> list[str]:
        """Return installation IDs accessible to the authenticated user/app."""
        url = f"{self.BASE_URL}/user/installations"
        response, _ = await self._make_request(url)
        installations = response.get("installations", [])
        return [str(i["id"]) for i in installations]

    async def _fetch_paginated_repos(
        self,
        url: str,
        params: dict,
        max_repos: int,
        extract_key: str | None = None,
    ) -> list[dict]:
        """Fetch repositories with pagination support.

        Args:
            url: The API endpoint URL
            params: Query parameters for the request
            max_repos: Maximum number of repositories to fetch
            extract_key: If provided, extract repositories from this key in the response

        Returns:
            List of repository dictionaries

        """
        repos: list[dict] = []
        page = 1
        while len(repos) < max_repos:
            page_params = {**params, "page": str(page)}
            response, headers = await self._make_request(url, page_params)
            page_repos = response.get(extract_key, []) if extract_key else response
            if not page_repos:
                break
            repos.extend(page_repos)
            page += 1
            link_header = headers.get("Link", "")
            if 'rel="next"' not in link_header:
                break
        return repos[:max_repos]

    def parse_pushed_at_date(self, repo):
        """Parse pushed_at timestamp from repository data.

        Args:
            repo: Repository dictionary from GitHub API

        Returns:
            Parsed datetime or datetime.min if not available

        """
        ts = repo.get("pushed_at")
        return datetime.strptime(ts, "%Y-%m-%dT%H:%M:%SZ") if ts else datetime.min

    def _parse_repository(
        self, repo: dict, link_header: str | None = None
    ) -> Repository:
        """Parse a GitHub API repository response into a Repository object.

        Args:
            repo: Repository data from GitHub API
            link_header: Optional link header for pagination

        Returns:
            Repository object

        """
        full_name = repo.get("full_name")
        if not isinstance(full_name, str):
            fallback = repo.get("name")
            owner = repo.get("owner", {}).get("login")
            if isinstance(owner, str) and isinstance(fallback, str):
                full_name = f"{owner}/{fallback}"
            else:
                fallback = fallback or ""
                full_name = str(fallback)

        return Repository(
            id=str(repo.get("id")),
            full_name=full_name,
            stargazers_count=repo.get("stargazers_count"),
            git_provider=ProviderType.GITHUB,
            is_public=not repo.get("private", True),
            owner_type=(
                OwnerType.ORGANIZATION
                if repo.get("owner", {}).get("type") == "Organization"
                else OwnerType.USER
            ),
            link_header=link_header,
            main_branch=repo.get("default_branch"),
        )

    async def get_paginated_repos(
        self,
        page: int,
        per_page: int,
        sort: str,
        installation_id: str | None,
        query: str | None = None,
    ):
        """Fetch a single page of repositories, supporting both user and app installations."""
        params = {"page": str(page), "per_page": str(per_page)}
        if installation_id:
            url = f"{self.BASE_URL}/user/installations/{installation_id}/repositories"
            response, headers = await self._make_request(url, params)
            response = response.get("repositories", [])
        else:
            url = f"{self.BASE_URL}/user/repos"
            params["sort"] = sort
            response, headers = await self._make_request(url, params)
        next_link: str = headers.get("Link", "")
        return [
            self._parse_repository(repo, link_header=next_link) for repo in response
        ]

    async def get_all_repositories(
        self, sort: str, app_mode: AppMode
    ) -> list[Repository]:
        """Collect up to 1000 repositories, aggregating across installations when running as SaaS."""
        MAX_REPOS = 1000
        PER_PAGE = 100
        all_repos: list[dict] = []
        if app_mode == AppMode.SAAS:
            installation_ids = await self.get_installations()
            for installation_id in installation_ids:
                params = {"per_page": str(PER_PAGE)}
                url = (
                    f"{self.BASE_URL}/user/installations/{installation_id}/repositories"
                )
                installation_repos = await self._fetch_paginated_repos(
                    url,
                    params,
                    MAX_REPOS - len(all_repos),
                    extract_key="repositories",
                )
                all_repos.extend(installation_repos)
                if len(all_repos) >= MAX_REPOS:
                    break
            if sort == "pushed":
                all_repos.sort(key=self.parse_pushed_at_date, reverse=True)
        else:
            params = {"per_page": str(PER_PAGE), "sort": sort}
            url = f"{self.BASE_URL}/user/repos"
            all_repos = await self._fetch_paginated_repos(url, params, MAX_REPOS)
        return [self._parse_repository(repo) for repo in all_repos]

    async def get_user_organizations(self) -> list[str]:
        """Get list of organization logins that the user is a member of."""
        url = f"{self.BASE_URL}/user/orgs"
        try:
            response, _ = await self._make_request(url)
            return [org["login"] for org in response]
        except Exception as e:
            logger.warning("Failed to get user organizations: %s", e)
            return []

    def _fuzzy_match_org_name(self, query: str, org_name: str) -> bool:
        """Check if query fuzzy matches organization name."""
        query_lower = query.lower().replace("-", "").replace("_", "").replace(" ", "")
        org_lower = org_name.lower().replace("-", "").replace("_", "").replace(" ", "")
        if query_lower == org_lower:
            return True
        return True if query_lower in org_lower else org_lower in query_lower

    def _build_public_search_params(
        self, query: str, params: dict
    ) -> tuple[dict, bool]:
        """Build search parameters for public repository search."""
        url_parts = query.split("/")
        if len(url_parts) < 4:
            return params, False

        org = url_parts[3]
        repo_name = url_parts[4]
        params["q"] = f"in:name {org}/{repo_name} is:public"
        return params, True

    def _build_org_search_params(self, query: str, params: dict) -> dict:
        """Build search parameters for organization-specific search."""
        org, repo_query = query.split("/", 1)
        query_with_user = f"org:{org} in:name {repo_query}"
        params["q"] = query_with_user
        return params

    async def _search_user_repositories(
        self, url: str, query: str, params: dict, user
    ) -> list[dict]:
        """Search repositories for the authenticated user."""
        formatted_query = query[:1].upper() + query[1:] if query else query
        user_query = f"{formatted_query} user:{user.login}"
        user_params = params.copy()
        user_params["q"] = user_query

        try:
            user_response, _ = await self._make_request(url, user_params)
            return user_response.get("items", [])
        except Exception as e:
            logger.warning("User search failed: %s", e)
            return []

    async def _search_organization_repositories(
        self,
        url: str,
        query: str,
        params: dict,
        user_orgs: list,
    ) -> list[dict]:
        """Search repositories for user organizations."""
        all_repos = []
        formatted_query = query[:1].upper() + query[1:] if query else query

        for org in user_orgs:
            org_query = f"{formatted_query} org:{org}"
            org_params = params.copy()
            org_params["q"] = org_query

            try:
                org_response, _ = await self._make_request(url, org_params)
                org_items = org_response.get("items", [])
                all_repos.extend(org_items)
            except Exception as e:
                logger.warning("Org %s search failed: %s", org, e)

        return all_repos

    async def _search_fuzzy_matched_orgs(
        self, url: str, query: str, params: dict, user_orgs: list
    ) -> list[dict]:
        """Search repositories for organizations that fuzzy match the query."""
        all_repos = []

        for org in user_orgs:
            if self._fuzzy_match_org_name(query, org):
                org_repos_query = f"org:{org}"
                org_repos_params = params.copy()
                org_repos_params["q"] = org_repos_query
                org_repos_params["sort"] = "stars"
                org_repos_params["per_page"] = 2

                try:
                    org_repos_response, _ = await self._make_request(
                        url, org_repos_params
                    )
                    org_repo_items = org_repos_response.get("items", [])
                    all_repos.extend(org_repo_items)
                except Exception as e:
                    logger.warning("Org repos search for %s failed: %s", org, e)

        return all_repos

    async def search_repositories(
        self,
        query: str,
        per_page: int,
        sort: str,
        order: str,
        public: bool,
    ) -> list[Repository]:
        """Search repositories using GitHub search API and personalized fallbacks."""
        url = f"{self.BASE_URL}/search/repositories"
        params = {"per_page": per_page, "sort": sort, "order": order}

        if public:
            params, success = self._build_public_search_params(query, params)
            if not success:
                return []
        elif "/" in query:
            params = self._build_org_search_params(query, params)
        else:
            user = await self.get_user()
            user_orgs = await self.get_user_organizations()
            all_repos = []

            # Search user repositories
            user_repos = await self._search_user_repositories(url, query, params, user)
            all_repos.extend(user_repos)

            # Search organization repositories
            org_repos = await self._search_organization_repositories(
                url, query, params, user_orgs
            )
            all_repos.extend(org_repos)

            # Search fuzzy matched organizations
            fuzzy_repos = await self._search_fuzzy_matched_orgs(
                url, query, params, user_orgs
            )
            all_repos.extend(fuzzy_repos)
            return [self._parse_repository(repo) for repo in all_repos]
        response, _ = await self._make_request(url, params)
        repo_items = response.get("items", [])
        return [self._parse_repository(repo) for repo in repo_items]

    async def get_repository_details_from_repo_name(
        self, repository: str
    ) -> Repository:
        """Fetch repository metadata for a full name like 'owner/repo'."""
        url = f"{self.BASE_URL}/repos/{repository}"
        repo, _ = await self._make_request(url)
        return self._parse_repository(repo)
