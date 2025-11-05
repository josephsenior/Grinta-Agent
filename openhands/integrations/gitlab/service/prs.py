from __future__ import annotations

from openhands.core.logger import openhands_logger as logger
from openhands.integrations.gitlab.service.base import GitLabMixinBase
from openhands.integrations.service_types import RequestMethod


class GitLabPRsMixin(GitLabMixinBase):
    """Methods for interacting with GitLab merge requests (PRs)."""

    async def create_mr(
        self,
        id: int | str,
        source_branch: str,
        target_branch: str,
        title: str,
        description: str | None = None,
        labels: list[str] | None = None,
    ) -> str:
        """Creates a merge request in GitLab.

        Args:
            id: The ID or URL-encoded path of the project
            source_branch: The name of the branch where your changes are implemented
            target_branch: The name of the branch you want the changes merged into
            title: The title of the merge request (optional, defaults to a generic title)
            description: The description of the merge request (optional)
            labels: A list of labels to apply to the merge request (optional)

        Returns:
            - MR URL when successful
            - Error message when unsuccessful
        """
        project_id = str(id).replace("/", "%2F") if isinstance(id, str) else id
        url = f"{self.BASE_URL}/projects/{project_id}/merge_requests"
        if not description:
            description = f"Merging changes from {source_branch} into {target_branch}"
        payload = {
            "source_branch": source_branch,
            "target_branch": target_branch,
            "title": title,
            "description": description,
        }
        if labels and len(labels) > 0:
            payload["labels"] = ",".join(labels)
        response, _ = await self._make_request(url=url, params=payload, method=RequestMethod.POST)
        return response["web_url"]

    async def get_pr_details(self, repository: str, pr_number: int) -> dict:
        """Get detailed information about a specific merge request.

        Args:
            repository: Repository name in format 'owner/repo'
            pr_number: The merge request number (iid)

        Returns:
            Raw GitLab API response for the merge request
        """
        project_id = self._extract_project_id(repository)
        url = f"{self.BASE_URL}/projects/{project_id}/merge_requests/{pr_number}"
        mr_data, _ = await self._make_request(url)
        return mr_data

    async def is_pr_open(self, repository: str, pr_number: int) -> bool:
        """Check if a GitLab merge request is still active (not closed/merged).

        Args:
            repository: Repository name in format 'owner/repo'
            pr_number: The merge request number (iid)

        Returns:
            True if MR is active (opened), False if closed/merged
        """
        try:
            mr_details = await self.get_pr_details(repository, pr_number)
            if "state" in mr_details:
                return mr_details["state"] == "opened"
            if "merged_at" in mr_details and "closed_at" in mr_details:
                return not (mr_details["merged_at"] or mr_details["closed_at"])
            logger.warning(
                "Could not determine GitLab MR status for %s#%s. Response keys: %s. Assuming MR is active.",
                repository,
                pr_number,
                list(mr_details.keys()),
            )
            return True
        except Exception as e:
            logger.warning(
                "Could not determine GitLab MR status for %s#%s: %s. Including conversation to be safe.",
                repository,
                pr_number,
                e,
            )
            return True
