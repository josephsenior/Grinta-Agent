import contextlib

from openhands.integrations.gitlab.service.base import GitLabMixinBase
from openhands.integrations.service_types import Branch, PaginatedBranchesResponse


class GitLabBranchesMixin(GitLabMixinBase):
    """Methods for interacting with GitLab branches."""

    async def get_branches(self, repository: str) -> list[Branch]:
        """Get branches for a repository."""
        encoded_name = repository.replace("/", "%2F")
        url = f"{self.BASE_URL}/projects/{encoded_name}/repository/branches"
        MAX_BRANCHES = 1000
        PER_PAGE = 100
        all_branches: list[Branch] = []
        page = 1
        while page <= 10 and len(all_branches) < MAX_BRANCHES:
            params = {"per_page": str(PER_PAGE), "page": str(page)}
            response, headers = await self._make_request(url, params)
            if not response:
                break
            for branch_data in response:
                branch = Branch(
                    name=branch_data.get("name"),
                    commit_sha=branch_data.get("commit", {}).get("id", ""),
                    protected=branch_data.get("protected", False),
                    last_push_date=branch_data.get("commit", {}).get("committed_date"),
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
        encoded_name = repository.replace("/", "%2F")
        url = f"{self.BASE_URL}/projects/{encoded_name}/repository/branches"
        params = {"per_page": str(per_page), "page": str(page)}
        response, headers = await self._make_request(url, params)
        branches: list[Branch] = []
        for branch_data in response:
            branch = Branch(
                name=branch_data.get("name"),
                commit_sha=branch_data.get("commit", {}).get("id", ""),
                protected=branch_data.get("protected", False),
                last_push_date=branch_data.get("commit", {}).get("committed_date"),
            )
            branches.append(branch)
        total_count = None
        has_next_page = bool(headers.get("Link", ""))
        if "X-Total" in headers:
            with contextlib.suppress(ValueError, TypeError):
                total_count = int(headers["X-Total"])
        return PaginatedBranchesResponse(
            branches=branches,
            has_next_page=has_next_page,
            current_page=page,
            per_page=per_page,
            total_count=total_count,
        )

    async def search_branches(self, repository: str, query: str, per_page: int = 30) -> list[Branch]:
        """Search branches using GitLab API which supports `search` param."""
        encoded_name = repository.replace("/", "%2F")
        url = f"{self.BASE_URL}/projects/{encoded_name}/repository/branches"
        params = {"per_page": str(per_page), "search": query}
        response, _ = await self._make_request(url, params)
        branches: list[Branch] = [
            Branch(
                name=branch_data.get("name"),
                commit_sha=branch_data.get("commit", {}).get("id", ""),
                protected=branch_data.get("protected", False),
                last_push_date=branch_data.get("commit", {}).get("committed_date"),
            )
            for branch_data in response
        ]
        return branches
