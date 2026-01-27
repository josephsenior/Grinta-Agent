"""GitHub mixin providing branch listing and search helpers."""

from __future__ import annotations

from forge.core.logger import forge_logger as logger
from forge.integrations.github.queries import search_branches_graphql_query
from forge.integrations.github.service.base import GitHubMixinBase
from forge.integrations.service_types import Branch, PaginatedBranchesResponse


class GitHubBranchesMixin(GitHubMixinBase):
    """Methods for interacting with branches for a repo."""

    async def get_branches(self, repository: str) -> list[Branch]:
        """Get branches for a repository."""
        url = f"{self.BASE_URL}/repos/{repository}/branches"
        MAX_BRANCHES = 5000
        PER_PAGE = 100
        all_branches: list[Branch] = []
        page = 1
        while len(all_branches) < MAX_BRANCHES:
            params = {"per_page": str(PER_PAGE), "page": str(page)}
            response, headers = await self._make_request(url, params)
            if not response:
                break
            for branch_data in response:
                last_push_date = None
                if branch_data.get("commit") and branch_data["commit"].get("commit"):
                    commit_info = branch_data["commit"]["commit"]
                    if commit_info.get("committer") and commit_info["committer"].get(
                        "date"
                    ):
                        last_push_date = commit_info["committer"]["date"]
                branch = Branch(
                    name=branch_data.get("name"),
                    commit_sha=branch_data.get("commit", {}).get("sha", ""),
                    protected=branch_data.get("protected", False),
                    last_push_date=last_push_date,
                )
                all_branches.append(branch)
            page += 1
            link_header = headers.get("Link", "")
            if 'rel="next"' not in link_header:
                break
        return all_branches

    async def get_paginated_branches(
        self,
        repository: str,
        page: int = 1,
        per_page: int = 30,
    ) -> PaginatedBranchesResponse:
        """Get branches for a repository with pagination."""
        url = f"{self.BASE_URL}/repos/{repository}/branches"
        params = {"per_page": str(per_page), "page": str(page)}
        response, headers = await self._make_request(url, params)
        branches: list[Branch] = []
        for branch_data in response:
            last_push_date = None
            if branch_data.get("commit") and branch_data["commit"].get("commit"):
                commit_info = branch_data["commit"]["commit"]
                if commit_info.get("committer") and commit_info["committer"].get(
                    "date"
                ):
                    last_push_date = commit_info["committer"]["date"]
            branch = Branch(
                name=branch_data.get("name"),
                commit_sha=branch_data.get("commit", {}).get("sha", ""),
                protected=branch_data.get("protected", False),
                last_push_date=last_push_date,
            )
            branches.append(branch)
        has_next_page = False
        if "Link" in headers:
            link_header = headers["Link"]
            has_next_page = 'rel="next"' in link_header
        return PaginatedBranchesResponse(
            branches=branches,
            has_next_page=has_next_page,
            current_page=page,
            per_page=per_page,
            total_count=None,
        )

    def _validate_search_inputs(self, query: str, per_page: int) -> tuple[bool, int]:
        """Validate search inputs and return validation result and adjusted per_page."""
        return (True, min(max(per_page, 1), 100)) if query else (False, per_page)

    def _parse_repository_parts(self, repository: str) -> tuple[str, str] | None:
        """Parse repository string into owner and name."""
        parts = repository.split("/")
        return None if len(parts) < 2 else (parts[-2], parts[-1])

    async def _execute_branch_search_query(
        self, owner: str, name: str, query: str, per_page: int
    ) -> dict | None:
        """Execute the GraphQL query for branch search."""
        variables = {"owner": owner, "name": name, "query": query, "perPage": per_page}
        try:
            return await self.execute_graphql_query(
                search_branches_graphql_query, variables
            )
        except Exception as e:
            logger.warning("Failed to search for branches: %s", e)
            return None

    def _extract_branch_data(self, node: dict) -> Branch:
        """Extract branch data from GraphQL node."""
        bname = node.get("name") or ""
        target = node.get("target") or {}
        typename = target.get("__typename")

        commit_sha = ""
        last_push_date = None
        if typename == "Commit":
            commit_sha = target.get("oid", "") or ""
            last_push_date = target.get("committedDate")

        protected = node.get("branchProtectionRule") is not None
        return Branch(
            name=bname,
            commit_sha=commit_sha,
            protected=protected,
            last_push_date=last_push_date,
        )

    def _process_branch_nodes(self, nodes: list) -> list[Branch]:
        """Process branch nodes and return Branch objects."""
        branches: list[Branch] = []
        for node in nodes:
            branch = self._extract_branch_data(node)
            branches.append(branch)
        return branches

    async def search_branches(
        self, repository: str, query: str, per_page: int = 30
    ) -> list[Branch]:
        """Search branches by name using GitHub GraphQL with a partial query."""
        is_valid, adjusted_per_page = self._validate_search_inputs(query, per_page)
        if not is_valid:
            return []

        repo_parts = self._parse_repository_parts(repository)
        if not repo_parts:
            return []

        owner, name = repo_parts
        result = await self._execute_branch_search_query(
            owner, name, query, adjusted_per_page
        )
        if not result:
            return []

        repo = result.get("data", {}).get("repository")
        if not repo or not repo.get("refs"):
            return []

        nodes = repo["refs"].get("nodes", [])
        return self._process_branch_nodes(nodes)
