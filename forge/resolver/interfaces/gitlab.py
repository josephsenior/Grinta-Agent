"""GitLab-specific implementations of resolver issue and merge request handlers."""

from __future__ import annotations

from typing import Any
from urllib.parse import quote

import httpx

from forge.core.logger import forge_logger as logger
from forge.resolver.interfaces.issue import (
    Issue,
    IssueHandlerInterface,
    ReviewThread,
)
from forge.resolver.utils import extract_issue_references


class GitlabIssueHandler(IssueHandlerInterface):
    """GitLab implementation of issue handler interface.

    Handles GitLab-specific operations for issues, merge requests, branches,
    and comments using the GitLab REST and GraphQL APIs.
    """

    def __init__(
        self,
        owner: str,
        repo: str,
        token: str,
        username: str | None = None,
        base_domain: str = "gitlab.com",
    ) -> None:
        """Initialize a GitLab issue handler.

        Args:
            owner: The owner of the repository
            repo: The name of the repository
            token: The GitLab personal access token
            username: Optional GitLab username
            base_domain: The domain for GitLab Enterprise (default: "gitlab.com")

        """
        self.owner = owner
        self.repo = repo
        self.token = token
        self.username = username
        self.base_domain = base_domain
        self.base_url = self.get_base_url()
        self.download_url = self.get_download_url()
        self.clone_url = self.get_clone_url()
        self.headers = self.get_headers()

    def set_owner(self, owner: str) -> None:
        """Update repository owner.

        Args:
            owner: New repository owner name

        """
        self.owner = owner

    def get_headers(self) -> dict[str, str]:
        """Get HTTP headers for GitLab API requests."""
        return {"Authorization": f"Bearer {self.token}", "Accept": "application/json"}

    def get_base_url(self) -> str:
        """Get base GitLab API URL for project."""
        project_path = quote(f"{self.owner}/{self.repo}", safe="")
        return f"https://{self.base_domain}/api/v4/projects/{project_path}"

    def get_authorize_url(self) -> str:
        """Get authenticated URL for git operations."""
        return f"https://{self.username}:{self.token}@{self.base_domain}/"

    def get_branch_url(self, branch_name: str) -> str:
        """Get GitLab API URL for a specific branch."""
        return f"{self.get_base_url()}/repository/branches/{branch_name}"

    def get_download_url(self) -> str:
        """Get GitLab API URL for issues endpoint."""
        return f"{self.base_url}/issues"

    def get_clone_url(self) -> str:
        """Get authenticated git clone URL."""
        username_and_token = self.token
        if self.username:
            username_and_token = f"{self.username}:{self.token}"
        return f"https://{username_and_token}@{self.base_domain}/{self.owner}/{self.repo}.git"

    def get_graphql_url(self) -> str:
        """Get GitLab GraphQL API URL."""
        return f"https://{self.base_domain}/api/graphql"

    def get_compare_url(self, branch_name: str) -> str:
        """Get GitLab web URL for comparing branch with default branch."""
        return f"https://{self.base_domain}/{self.owner}/{self.repo}/-/compare/{self.get_default_branch_name()}...{branch_name}"

    def get_converted_issues(
        self,
        issue_numbers: list[int] | None = None,
        comment_id: int | None = None,
    ) -> list[Issue]:
        """Download issues from Gitlab.

        Args:
            issue_numbers: The numbers of the issues to download
            comment_id: The ID of a single comment, if provided, otherwise all comments

        Returns:
            List of Gitlab issues.

        """
        if not issue_numbers:
            msg = "Unspecified issue number"
            raise ValueError(msg)
        all_issues = self.download_issues()
        logger.info("Limiting resolving to issues %s.", issue_numbers)
        all_issues = [issue for issue in all_issues if issue["iid"] in issue_numbers]
        if len(issue_numbers) == 1 and (not all_issues):
            msg = f"Issue {issue_numbers[0]} not found"
            raise ValueError(msg)
        converted_issues = []
        for issue in all_issues:
            if any(issue.get(key) is None for key in ["iid", "title"]):
                logger.warning(
                    "Skipping issue %s as it is missing iid or title.", issue
                )
                continue
            if issue.get("description") is None:
                issue["description"] = ""
            thread_comments = self.get_issue_comments(
                issue["iid"], comment_id=comment_id
            )
            issue_details = Issue(
                owner=self.owner,
                repo=self.repo,
                number=issue["iid"],
                title=issue["title"],
                body=issue["description"],
                thread_comments=thread_comments,
                review_comments=None,
            )
            converted_issues.append(issue_details)
        return converted_issues

    def download_issues(self) -> list[Any]:
        """Download all open issues from GitLab repository.

        Returns:
            List of issue dictionaries from GitLab API

        """
        params: dict[str, int | str] = {
            "state": "opened",
            "scope": "all",
            "per_page": 100,
            "page": 1,
        }
        all_issues = []
        while True:
            response = httpx.get(self.download_url, headers=self.headers, params=params)
            response.raise_for_status()
            issues = response.json()
            if not issues:
                break
            if not isinstance(issues, list) or any(
                not isinstance(issue, dict) for issue in issues
            ):
                msg = "Expected list of dictionaries from Service Gitlab API."
                raise ValueError(msg)
            all_issues.extend(issues)
            assert isinstance(params["page"], int)
            params["page"] += 1
        return all_issues

    def get_issue_comments(
        self, issue_number: int, comment_id: int | None = None
    ) -> list[str] | None:
        """Download comments for a specific issue from Gitlab.

        Args:
            issue_number: Issue number to get comments for
            comment_id: Optional specific comment ID to retrieve

        Returns:
            List of comment bodies or None if no comments

        """
        url = f"{self.download_url}/{issue_number}/notes"
        params = {"per_page": 100, "page": 1}
        all_comments = []
        while True:
            response = httpx.get(url, headers=self.headers, params=params)
            response.raise_for_status()
            comments = response.json()
            if not comments:
                break
            if comment_id:
                if matching_comment := next(
                    (
                        comment["body"]
                        for comment in comments
                        if comment["id"] == comment_id
                    ),
                    None,
                ):
                    return [matching_comment]
            else:
                all_comments.extend([comment["body"] for comment in comments])
            params["page"] += 1
        return all_comments or None

    def branch_exists(self, branch_name: str) -> bool:
        """Check if a branch exists in the repository.

        Args:
            branch_name: Name of branch to check

        Returns:
            True if branch exists, False otherwise

        """
        logger.info("Checking if branch %s exists...", branch_name)
        response = httpx.get(
            f"{self.base_url}/repository/branches/{branch_name}", headers=self.headers
        )
        exists = response.status_code == 200
        logger.info("Branch %s exists: %s", branch_name, exists)
        return exists

    def get_branch_name(self, base_branch_name: str) -> str:
        """Generate unique branch name by appending attempt number if needed.

        Args:
            base_branch_name: Base name for the branch

        Returns:
            Unique branch name that doesn't exist yet

        """
        branch_name = base_branch_name
        attempt = 1
        while self.branch_exists(branch_name):
            attempt += 1
            branch_name = f"{base_branch_name}-try{attempt}"
        return branch_name

    def reply_to_comment(self, pr_number: int, comment_id: str, reply: str) -> None:
        """Reply to a discussion thread comment.

        Args:
            pr_number: Merge request number
            comment_id: Discussion thread ID
            reply: Reply message to post

        """
        response = httpx.get(
            f"{self.base_url}/merge_requests/{pr_number}/discussions/{comment_id.split('/')[-1]}",
            headers=self.headers,
        )
        response.raise_for_status()
        discussions = response.json()
        if len(discussions.get("notes", [])) > 0:
            data = {
                "body": f"Forge fix success summary\n\n\n{reply}",
                "note_id": discussions.get("notes", [])[-1]["id"],
            }
            response = httpx.post(
                f"{self.base_url}/merge_requests/{pr_number}/discussions/{comment_id.split('/')[-1]}/notes",
                headers=self.headers,
                json=data,
            )
            response.raise_for_status()

    def get_pull_url(self, pr_number: int) -> str:
        """Get GitLab web URL for a merge request."""
        return f"https://{self.base_domain}/{self.owner}/{self.repo}/-/merge_requests/{pr_number}"

    def get_default_branch_name(self) -> str:
        """Get default branch name from project settings."""
        response = httpx.get(f"{self.base_url}", headers=self.headers)
        response.raise_for_status()
        data = response.json()
        return str(data["default_branch"])

    def create_pull_request(self, data: dict[str, Any] | None = None) -> dict[str, Any]:
        """Create a merge request with the provided data.

        Args:
            data: MR data dictionary (title, description, source_branch, target_branch, etc.)

        Returns:
            Dictionary with created MR data (normalized to match GitHub format)

        Raises:
            RuntimeError: If token lacks push permissions

        """
        if data is None:
            data = {}
        response = httpx.post(
            f"{self.base_url}/merge_requests", headers=self.headers, json=data
        )
        if response.status_code == 403:
            msg = "Failed to create pull request due to missing permissions. Make sure that the provided token has push permissions for the repository."
            raise RuntimeError(
                msg,
            )
        response.raise_for_status()
        pr_data = response.json()
        if "web_url" in pr_data:
            pr_data["html_url"] = pr_data["web_url"]
        if "iid" in pr_data:
            pr_data["number"] = pr_data["iid"]
        return dict(pr_data)

    def request_reviewers(self, reviewer: str, pr_number: int) -> None:
        """Request review from a user on a merge request.

        Args:
            reviewer: GitLab username to request review from
            pr_number: Merge request number

        """
        response = httpx.get(
            f"https://{self.base_domain}/api/v4/users?username={reviewer}",
            headers=self.headers,
        )
        response.raise_for_status()
        user_data = response.json()
        if len(user_data) > 0:
            review_data = {"reviewer_ids": [user_data[0]["id"]]}
            review_response = httpx.put(
                f"{self.base_url}/merge_requests/{pr_number}",
                headers=self.headers,
                json=review_data,
            )
            if review_response.status_code != 200:
                logger.warning(
                    "Failed to request review from %s: %s",
                    reviewer,
                    review_response.text,
                )

    def send_comment_msg(self, issue_number: int, msg: str) -> None:
        """Send a comment message to a GitLab issue or merge request.

        Args:
            issue_number: The issue or merge request number
            msg: The message content to post as a comment

        """
        comment_url = f"{self.base_url}/issues/{issue_number}/notes"
        comment_data = {"body": msg}
        comment_response = httpx.post(
            comment_url, headers=self.headers, json=comment_data
        )
        if comment_response.status_code != 201:
            logger.error(
                "Failed to post comment: %s %s",
                comment_response.status_code,
                comment_response.text,
            )
        else:
            logger.info("Comment added to the PR: %s", msg)

    def get_context_from_external_issues_references(
        self,
        closing_issues: list[str],
        closing_issue_numbers: list[int],
        issue_body: str,
        review_comments: list[str] | None,
        review_threads: list[ReviewThread],
        thread_comments: list[str] | None,
    ) -> list[str]:
        """Extract context from external issue references.

        Args:
            closing_issues: List of closing issue references
            closing_issue_numbers: List of closing issue numbers
            issue_body: Issue body text
            review_comments: Optional review comments
            review_threads: List of review threads
            thread_comments: Optional thread comments

        Returns:
            List of context strings (empty for GitLab)

        """
        return closing_issues


class GitlabPRHandler(GitlabIssueHandler):
    """GitLab handler specialized for merge request operations.

    Extends GitlabIssueHandler with MR-specific functionality including
    discussion thread handling and MR metadata extraction.
    """

    def __init__(
        self,
        owner: str,
        repo: str,
        token: str,
        username: str | None = None,
        base_domain: str = "gitlab.com",
    ) -> None:
        """Initialize a GitLab PR handler.

        Args:
            owner: The owner of the repository
            repo: The name of the repository
            token: The GitLab personal access token
            username: Optional GitLab username
            base_domain: The domain for GitLab Enterprise (default: "gitlab.com")

        """
        super().__init__(owner, repo, token, username, base_domain)
        self.download_url = f"{self.base_url}/merge_requests"

    def _fetch_closing_issues(self, pull_number: int) -> tuple[list[str], list[int]]:
        """Fetch issues that will be closed by the PR.

        Args:
            pull_number: Merge request number

        Returns:
            Tuple of (closing_issue_bodies, closing_issue_numbers)

        """
        response = httpx.get(
            f"{self.base_url}/merge_requests/{pull_number}/related_issues",
            headers=self.headers,
        )
        response.raise_for_status()
        closing_issues = response.json()
        closing_issues_bodies = [issue["description"] for issue in closing_issues]
        closing_issue_numbers = [issue["iid"] for issue in closing_issues]
        return closing_issues_bodies, closing_issue_numbers

    def _fetch_pr_discussions(self, pull_number: int) -> dict:
        """Fetch PR discussions via GraphQL.

        Args:
            pull_number: Merge request number

        Returns:
            GraphQL response dictionary with discussions data

        """
        query = "\n                query($projectPath: ID!, $pr: String!) {\n                    project(fullPath: $projectPath) {\n                        mergeRequest(iid: $pr) {\n                            webUrl\n                            discussions(first: 100) {\n                                edges {\n                                    node {\n                                        id\n                                        resolved\n                                        resolvable\n                                        notes(first: 100) {\n                                            nodes {\n                                                body\n                                                id\n                                                position {\n                                                    filePath\n                                                }\n                                            }\n                                        }\n                                    }\n                                }\n                            }\n                        }\n                    }\n                }\n            "
        project_path = f"{self.owner}/{self.repo}"
        variables = {"projectPath": project_path, "pr": str(pull_number)}
        response = httpx.post(
            self.get_graphql_url(),
            json={"query": query, "variables": variables},
            headers=self.headers,
        )
        response.raise_for_status()
        return response.json()

    def _process_review_thread(
        self, my_review_threads: list, comment_id: int | None
    ) -> tuple[str, list[str], bool]:
        """Process review thread notes to build message and file list.

        Args:
            my_review_threads: List of review thread note dictionaries
            comment_id: Optional comment ID to check for

        Returns:
            Tuple of (message, files, thread_contains_comment_id)

        """
        message = ""
        files = []
        thread_contains_comment_id = False

        for i, review_thread in enumerate(my_review_threads):
            if (
                comment_id is not None
                and int(review_thread["id"].split("/")[-1]) == comment_id
            ):
                thread_contains_comment_id = True

            if i == len(my_review_threads) - 1:
                if len(my_review_threads) > 1:
                    message += "---\n"
                message += "latest feedback:\n" + review_thread["body"] + "\n"
            else:
                message += review_thread["body"] + "\n"

            file = review_thread.get("position", {})
            file = file.get("filePath") if file is not None else None
            if file and file not in files:
                files.append(file)

        return message, files, thread_contains_comment_id

    def download_pr_metadata(
        self,
        pull_number: int,
        comment_id: int | None = None,
    ) -> tuple[list[str], list[int], list[str] | None, list[ReviewThread], list[str]]:
        """Run a GraphQL query against the Gitlab API for information.

        Retrieves information about:
            1. unresolved review comments
            2. referenced issues the pull request would close

        Args:
            pull_number: Merge request number
            comment_id: Optional comment ID to filter by

        Returns:
            Tuple of (closing_issues, closing_issue_numbers, review_comments, review_threads, thread_comments)

        """
        # Fetch closing issues
        closing_issues_bodies, closing_issue_numbers = self._fetch_closing_issues(
            pull_number
        )

        # Fetch discussions
        response_json = self._fetch_pr_discussions(pull_number)
        pr_data = (
            response_json.get("data", {}).get("project", {}).get("mergeRequest", {})
        )

        # Process review threads
        review_threads = []
        thread_ids = []
        raw_review_threads = pr_data.get("discussions", {}).get("edges", [])

        for thread in raw_review_threads:
            node = thread.get("node", {})
            if not node.get("resolved", True) and node.get("resolvable", True):
                thread_id = node.get("id")
                my_review_threads = node.get("notes", {}).get("nodes", [])
                message, files, thread_contains_comment_id = (
                    self._process_review_thread(my_review_threads, comment_id)
                )

                if comment_id is None or thread_contains_comment_id:
                    unresolved_thread = ReviewThread(comment=message, files=files)
                    review_threads.append(unresolved_thread)
                    thread_ids.append(thread_id)

        return (
            closing_issues_bodies,
            closing_issue_numbers,
            None,
            review_threads,
            thread_ids,
        )

    def get_pr_comments(
        self, pr_number: int, comment_id: int | None = None
    ) -> list[str] | None:
        """Download comments for a specific pull request from Gitlab.

        Args:
            pr_number: Pull request number
            comment_id: Optional specific comment ID

        Returns:
            List of comment bodies or None if empty

        """
        url = f"{self.base_url}/merge_requests/{pr_number}/notes"
        all_comments = []
        page = 1

        while True:
            comments = self._fetch_comment_page(url, page)
            if not comments:
                break

            if comment_id is not None:
                if matching := next(
                    (c["body"] for c in comments if c["id"] == comment_id), None
                ):
                    return [matching]
            else:
                all_comments.extend([c["body"] for c in comments])

            page += 1

        return all_comments or None

    def _fetch_comment_page(self, url: str, page: int) -> list[dict]:
        """Fetch a single page of comments.

        Args:
            url: API URL
            page: Page number

        Returns:
            List of filtered comments

        """
        params = {"per_page": 100, "page": page}
        response = httpx.get(url, headers=self.headers, params=params)
        response.raise_for_status()

        comments = response.json()

        # Filter out system and non-resolvable comments
        return [
            comment
            for comment in comments
            if comment.get("resolvable", True) and not comment.get("system", True)
        ]

    def _collect_issue_references(
        self,
        issue_body: str,
        review_comments: list[str] | None,
        review_threads: list[ReviewThread],
        thread_comments: list[str] | None,
    ) -> list[int]:
        """Collect issue references from various sources.

        Args:
            issue_body: The issue body text.
            review_comments: List of review comments.
            review_threads: List of review threads.
            thread_comments: List of thread comments.

        Returns:
            list[int]: List of issue references found.

        """
        new_issue_references: list[int] = []

        # Extract from issue body
        if issue_body:
            new_issue_references.extend(extract_issue_references(issue_body))

        # Extract from review comments
        if review_comments:
            for comment in review_comments:
                new_issue_references.extend(extract_issue_references(comment))

        # Extract from review threads
        if review_threads:
            for review_thread in review_threads:
                new_issue_references.extend(
                    extract_issue_references(review_thread.comment)
                )

        # Extract from thread comments
        if thread_comments:
            for thread_comment in thread_comments:
                new_issue_references.extend(extract_issue_references(thread_comment))

        return new_issue_references

    def _fetch_issue_content(self, issue_number: int) -> str | None:
        """Fetch the content of a specific issue.

        Args:
            issue_number: The issue number to fetch.

        Returns:
            str | None: The issue content if successful, None otherwise.

        """
        try:
            url = f"{self.base_url}/issues/{issue_number}"
            response = httpx.get(url, headers=self.headers)
            response.raise_for_status()
            issue_data = response.json()
            return issue_data.get("description", "")
        except httpx.HTTPError as e:
            logger.warning("Failed to fetch issue %s: %s", issue_number, str(e))
            return None

    def get_context_from_external_issues_references(
        self,
        closing_issues: list[str],
        closing_issue_numbers: list[int],
        issue_body: str,
        review_comments: list[str] | None,
        review_threads: list[ReviewThread],
        thread_comments: list[str] | None,
    ) -> list[str]:
        """Get context from external issue references.

        Args:
            closing_issues: List of closing issue references.
            closing_issue_numbers: List of closing issue numbers.
            issue_body: The issue body text.
            review_comments: List of review comments.
            review_threads: List of review threads.
            thread_comments: List of thread comments.

        Returns:
            list[str]: Context from external issue references.

        """
        # Collect all issue references
        new_issue_references = self._collect_issue_references(
            issue_body,
            review_comments,
            review_threads,
            thread_comments,
        )

        # Remove duplicates and filter out already processed issues
        non_duplicate_references = set(new_issue_references)
        unique_issue_references = non_duplicate_references.difference(
            closing_issue_numbers
        )

        # Fetch content for unique issues
        for issue_number in unique_issue_references:
            if issue_content := self._fetch_issue_content(issue_number):
                closing_issues.append(issue_content)

        return closing_issues

    def get_converted_issues(
        self,
        issue_numbers: list[int] | None = None,
        comment_id: int | None = None,
    ) -> list[Issue]:
        """Convert selected GitLab issues into Issue dataclasses for resolver usage."""
        if not issue_numbers:
            msg = "Unspecified issue numbers"
            raise ValueError(msg)
        all_issues = self.download_issues()
        logger.info("Limiting resolving to issues %s.", issue_numbers)
        all_issues = [issue for issue in all_issues if issue["iid"] in issue_numbers]
        converted_issues = []
        for issue in all_issues:
            if any(issue.get(key) is None for key in ["iid", "title"]):
                logger.warning("Skipping #%s as it is missing iid or title.", issue)
                continue
            body = (
                issue.get("description") if issue.get("description") is not None else ""
            )
            (
                closing_issues,
                closing_issues_numbers,
                review_comments,
                review_threads,
                thread_ids,
            ) = self.download_pr_metadata(issue["iid"], comment_id=comment_id)
            head_branch = issue["source_branch"]
            thread_comments = self.get_pr_comments(issue["iid"], comment_id=comment_id)
            closing_issues = self.get_context_from_external_issues_references(
                closing_issues,
                closing_issues_numbers,
                body,
                review_comments,
                review_threads,
                thread_comments,
            )
            issue_details = Issue(
                owner=self.owner,
                repo=self.repo,
                number=issue["iid"],
                title=issue["title"],
                body=body,
                closing_issues=closing_issues,
                review_comments=review_comments,
                review_threads=review_threads,
                thread_ids=thread_ids,
                head_branch=head_branch,
                thread_comments=thread_comments,
            )
            converted_issues.append(issue_details)
        return converted_issues
