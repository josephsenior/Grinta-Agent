# pragma: no cover
"""GitLab mixin supplying feature-specific helpers like suggested tasks."""

from forge.integrations.gitlab.service.base import GitLabMixinBase
from forge.integrations.service_types import (
    MicroagentContentResponse,
    ProviderType,
    RequestMethod,
    SuggestedTask,
    TaskType,
)


class GitLabFeaturesMixin(GitLabMixinBase):
    """Methods used for custom features in UI driven via GitLab integration."""

    async def _get_cursorrules_url(self, repository: str) -> str:
        """Get the URL for checking .cursorrules file."""
        project_id = self._extract_project_id(repository)
        return (
            f"{self.BASE_URL}/projects/{project_id}/repository/files/.cursorrules/raw"
        )

    async def _get_microagents_directory_url(
        self, repository: str, microagents_path: str
    ) -> str:
        """Get the URL for checking microagents directory."""
        project_id = self._extract_project_id(repository)
        return f"{self.BASE_URL}/projects/{project_id}/repository/tree"

    def _get_microagents_directory_params(self, microagents_path: str) -> dict:
        """Get parameters for the microagents directory request."""
        return {"path": microagents_path, "recursive": "true"}

    def _is_valid_microagent_file(self, item: dict) -> bool:
        """Check if an item represents a valid microagent file."""
        return (
            item["type"] == "blob"
            and item["name"].endswith(".md")
            and (item["name"] != "README.md")
        )

    def _get_file_name_from_item(self, item: dict) -> str:
        """Extract file name from directory item."""
        return item["name"]

    def _get_file_path_from_item(self, item: dict, microagents_path: str) -> str:
        """Extract file path from directory item."""
        return item["path"]

    def _get_merge_requests_query(self) -> str:
        """Get the GraphQL query for merge requests."""
        return """
        query GetUserTasks {
          currentUser {
            authoredMergeRequests(state: opened, sort: UPDATED_DESC, first: 100) {
              nodes {
                id
                iid
                title
                project {
                  fullPath
                }
                conflicts
                mergeStatus
                pipelines(first: 1) {
                  nodes {
                    status
                  }
                }
                discussions(first: 100) {
                  nodes {
                    notes {
                      nodes {
                        resolvable
                        resolved
                      }
                    }
                  }
                }
              }
            }
          }
        }
        """

    def _determine_merge_request_task_type(self, mr: dict) -> TaskType:
        """Determine the task type for a merge request based on its state."""
        if mr.get("conflicts"):
            return TaskType.MERGE_CONFLICTS

        pipelines = mr.get("pipelines", {}).get("nodes", [])
        if pipelines and pipelines[0].get("status") == "FAILED":
            return TaskType.FAILING_CHECKS

        if self._has_unresolved_comments(mr):
            return TaskType.UNRESOLVED_COMMENTS

        return TaskType.OPEN_PR

    def _has_unresolved_comments(self, mr: dict) -> bool:
        """Check if merge request has unresolved comments."""
        discussions = mr.get("discussions", {}).get("nodes", [])
        for discussion in discussions:
            notes = discussion.get("notes", {}).get("nodes", [])
            for note in notes:
                if note.get("resolvable") and not note.get("resolved"):
                    return True
        return False

    def _create_merge_request_task(
        self, mr: dict, task_type: TaskType
    ) -> SuggestedTask:
        """Create a SuggestedTask from merge request data."""
        repo_name = mr.get("project", {}).get("fullPath", "") or ""
        mr_number_raw = mr.get("iid")
        mr_number = 0
        if mr_number_raw is not None:
            try:
                mr_number = int(mr_number_raw)
            except (TypeError, ValueError):
                mr_number = 0
        title = mr.get("title", "")
        return SuggestedTask(
            git_provider=ProviderType.GITLAB,
            task_type=task_type,
            repo=repo_name,
            issue_number=mr_number,
            title=title,
        )

    def _create_issue_task(self, issue: dict) -> SuggestedTask:
        """Create a SuggestedTask from issue data."""
        repo_name = issue.get("references", {}).get("full", "").split("#")[0].strip()
        issue_number_raw = issue.get("iid")
        issue_number = 0
        if issue_number_raw is not None:
            try:
                issue_number = int(issue_number_raw)
            except (TypeError, ValueError):
                issue_number = 0
        title = issue.get("title", "")
        return SuggestedTask(
            git_provider=ProviderType.GITLAB,
            task_type=TaskType.OPEN_ISSUE,
            repo=repo_name,
            issue_number=issue_number,
            title=title,
        )

    async def _process_merge_requests(
        self, merge_requests: list
    ) -> list[SuggestedTask]:
        """Process merge requests and return suggested tasks."""
        tasks = []
        for mr in merge_requests:
            task_type = self._determine_merge_request_task_type(mr)
            if task_type != TaskType.OPEN_PR:
                task = self._create_merge_request_task(mr, task_type)
                tasks.append(task)
        return tasks

    async def _process_assigned_issues(self, username: str) -> list[SuggestedTask]:
        """Process assigned issues and return suggested tasks."""
        url = f"{self.BASE_URL}/issues"
        params = {
            "assignee_username": username,
            "state": "opened",
            "scope": "assigned_to_me",
        }
        issues_response, _ = await self._make_request(
            method=RequestMethod.GET, url=url, params=params
        )

        tasks = []
        for issue in issues_response:
            task = self._create_issue_task(issue)
            tasks.append(task)
        return tasks

    async def get_suggested_tasks(self) -> list[SuggestedTask]:
        """Get suggested tasks for the authenticated user across all repositories.

        Returns:
        - Merge requests authored by the user.
        - Issues assigned to the user.

        """
        try:
            user = await self.get_user()
            username = user.login

            # Process merge requests
            query = self._get_merge_requests_query()
            response = await self.execute_graphql_query(query)
            data = response.get("currentUser", {})
            merge_requests = data.get("authoredMergeRequests", {}).get("nodes", [])
            merge_request_tasks = await self._process_merge_requests(merge_requests)

            # Process assigned issues
            issue_tasks = await self._process_assigned_issues(username)

            return merge_request_tasks + issue_tasks
        except Exception:
            return []

    async def get_microagent_content(
        self, repository: str, file_path: str
    ) -> MicroagentContentResponse:
        """Fetch individual file content from GitLab repository.

        Args:
            repository: Repository name in format 'owner/repo' or 'domain/owner/repo'
            file_path: Path to the file within the repository

        Returns:
            MicroagentContentResponse with parsed content and triggers

        Raises:
            RuntimeError: If file cannot be fetched or doesn't exist

        """
        project_id = self._extract_project_id(repository)
        encoded_file_path = file_path.replace("/", "%2F")
        base_url = f"{self.BASE_URL}/projects/{project_id}"
        file_url = f"{base_url}/repository/files/{encoded_file_path}/raw"
        response, _ = await self._make_request(file_url)
        return self._parse_microagent_content(response, file_path)
