"""GitHub mixin providing pull request creation and inspection helpers."""

from __future__ import annotations

from forge.core.logger import forge_logger as logger
from forge.integrations.github.service.base import GitHubMixinBase
from forge.integrations.service_types import RequestMethod


class GitHubPRsMixin(GitHubMixinBase):
    """Methods for interacting with GitHub PRs."""

    async def create_pr(
        self,
        repo_name: str,
        source_branch: str,
        target_branch: str,
        title: str,
        body: str | None = None,
        draft: bool = True,
        labels: list[str] | None = None,
    ) -> str:
        """Creates a PR using user credentials.

        Args:
            repo_name: The full name of the repository (owner/repo)
            source_branch: The name of the branch where your changes are implemented
            target_branch: The name of the branch you want the changes pulled into
            title: The title of the pull request (optional, defaults to a generic title)
            body: The body/description of the pull request (optional)
            draft: Whether to create the PR as a draft (optional, defaults to False)
            labels: A list of labels to apply to the pull request (optional)

        Returns:
            - PR URL when successful
            - Error message when unsuccessful

        """
        url = f"{self.BASE_URL}/repos/{repo_name}/pulls"
        if not body:
            body = f"Merging changes from {source_branch} into {target_branch}"
        payload = {
            "title": title,
            "head": source_branch,
            "base": target_branch,
            "body": body,
            "draft": draft,
        }
        response, _ = await self._make_request(
            url=url, params=payload, method=RequestMethod.POST
        )
        if labels and len(labels) > 0:
            pr_number = response["number"]
            labels_url = f"{self.BASE_URL}/repos/{repo_name}/issues/{pr_number}/labels"
            labels_payload = {"labels": labels}
            await self._make_request(
                url=labels_url, params=labels_payload, method=RequestMethod.POST
            )
        return response["html_url"]

    async def get_pr_details(self, repository: str, pr_number: int) -> dict:
        """Get detailed information about a specific pull request.

        Args:
            repository: Repository name in format 'owner/repo'
            pr_number: The pull request number

        Returns:
            Raw GitHub API response for the pull request

        """
        url = f"{self.BASE_URL}/repos/{repository}/pulls/{pr_number}"
        pr_data, _ = await self._make_request(url)
        return pr_data

    async def is_pr_open(self, repository: str, pr_number: int) -> bool:
        """Check if a GitHub PR is still active (not closed/merged).

        Args:
            repository: Repository name in format 'owner/repo'
            pr_number: The PR number to check

        Returns:
            True if PR is active (open), False if closed/merged

        """
        try:
            pr_details = await self.get_pr_details(repository, pr_number)
            if "state" in pr_details:
                return pr_details["state"] == "open"
            if "merged" in pr_details and "closed_at" in pr_details:
                return not (pr_details["merged"] or pr_details["closed_at"])
            logger.warning(
                "Could not determine GitHub PR status for %s#%s. Response keys: %s. Assuming PR is active.",
                repository,
                pr_number,
                list(pr_details.keys()),
            )
            return True
        except Exception as e:
            logger.warning(
                "Could not determine GitHub PR status for %s#%s: %s. Including conversation to be safe.",
                repository,
                pr_number,
                e,
            )
            return True
