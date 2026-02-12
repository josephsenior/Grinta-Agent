"""GitHub-specific implementations of resolver issue and pull handlers."""

from __future__ import annotations

from typing import Any

import httpx

from backend.core.logger import forge_logger as logger
from backend.resolver.interfaces.issue import (
    Issue,
    IssueHandlerInterface,
    ReviewThread,
)
from backend.resolver.utils import extract_issue_references


class GithubIssueHandler(IssueHandlerInterface):
    """GitHub implementation of issue handler interface.

    Handles GitHub-specific operations for issues, pull requests, branches,
    and comments using the GitHub REST and GraphQL APIs.
    """

    def __init__(
        self,
        owner: str,
        repo: str,
        token: str,
        username: str | None = None,
        base_domain: str = "github.com",
    ) -> None:
        """Initialize a GitHub issue handler.

        Args:
            owner: The owner of the repository
            repo: The name of the repository
            token: The GitHub personal access token
            username: Optional GitHub username
            base_domain: The domain for GitHub Enterprise (default: "github.com")

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
        """Get HTTP headers for GitHub API requests."""
        return {
            "Authorization": f"token {self.token}",
            "Accept": "application/vnd.github.v3+json",
        }

    def get_base_url(self) -> str:
        """Get base GitHub API URL for repository."""
        if self.base_domain == "github.com":
            return f"https://api.github.com/repos/{self.owner}/{self.repo}"
        return f"https://{self.base_domain}/api/v3/repos/{self.owner}/{self.repo}"

    def get_authorize_url(self) -> str:
        """Get authenticated URL for git operations."""
        return f"https://{self.username}:{self.token}@{self.base_domain}/"

    def get_branch_url(self, branch_name: str) -> str:
        """Get GitHub API URL for a specific branch."""
        return f"{self.get_base_url()}/branches/{branch_name}"

    def get_download_url(self) -> str:
        """Get GitHub API URL for issues endpoint."""
        return f"{self.base_url}/issues"

    def get_clone_url(self) -> str:
        """Get authenticated git clone URL."""
        username_and_token = (
            f"{self.username}:{self.token}"
            if self.username
            else f"x-auth-token:{self.token}"
        )
        return f"https://{username_and_token}@{self.base_domain}/{self.owner}/{self.repo}.git"

    def get_graphql_url(self) -> str:
        """Get GitHub GraphQL API URL."""
        if self.base_domain == "github.com":
            return "https://api.github.com/graphql"
        return f"https://{self.base_domain}/api/graphql"

    def get_compare_url(self, branch_name: str) -> str:
        """Get GitHub web URL for comparing branch with default branch."""
        return f"https://{self.base_domain}/{self.owner}/{self.repo}/compare/{branch_name}?expand=1"

    def get_converted_issues(
        self,
        issue_numbers: list[int] | None = None,
        comment_id: int | None = None,
    ) -> list[Issue]:
        """Download issues from Github.

        Args:
            issue_numbers: The numbers of the issues to download
            comment_id: The ID of a single comment, if provided, otherwise all comments

        Returns:
            List of Github issues

        Raises:
            ValueError: If no issue numbers provided or issue not found

        """
        if not issue_numbers:
            msg = "Unspecified issue number"
            raise ValueError(msg)

        all_issues = self._filter_requested_issues(issue_numbers)
        return self._convert_issues_to_details(all_issues, comment_id)

    def _filter_requested_issues(self, issue_numbers: list[int]) -> list[dict]:
        """Filter downloaded issues to requested numbers.

        Args:
            issue_numbers: List of issue numbers to filter for

        Returns:
            Filtered list of issues

        Raises:
            ValueError: If single issue not found

        """
        all_issues = self.download_issues()
        logger.info("Limiting resolving to issues %s.", issue_numbers)

        filtered = [
            issue
            for issue in all_issues
            if issue["number"] in issue_numbers and "pull_request" not in issue
        ]

        if len(issue_numbers) == 1 and not filtered:
            msg = f"Issue {issue_numbers[0]} not found"
            raise ValueError(msg)

        return filtered

    def _convert_issues_to_details(
        self, all_issues: list[dict], comment_id: int | None
    ) -> list[Issue]:
        """Convert raw issues to Issue objects.

        Args:
            all_issues: List of raw issue dictionaries
            comment_id: Optional specific comment ID

        Returns:
            List of Issue objects

        """
        converted_issues = []

        for issue in all_issues:
            if not self._is_valid_issue(issue):
                continue

            if issue.get("body") is None:
                issue["body"] = ""

            thread_comments = self.get_issue_comments(
                issue["number"], comment_id=comment_id
            )

            issue_details = Issue(
                owner=self.owner,
                repo=self.repo,
                number=issue["number"],
                title=issue["title"],
                body=issue["body"],
                thread_comments=thread_comments,
                review_comments=None,
            )
            converted_issues.append(issue_details)

        return converted_issues

    def _is_valid_issue(self, issue: dict) -> bool:
        """Check if issue has required fields.

        Args:
            issue: Issue dictionary

        Returns:
            True if valid

        """
        if any(issue.get(key) is None for key in ["number", "title"]):
            logger.warning("Skipping issue %s as it is missing number or title.", issue)
            return False
        return True

    def download_issues(self) -> list[Any]:
        """Download all open issues from GitHub repository.

        Returns:
            List of issue dictionaries from GitHub API

        """
        params: dict[str, int | str] = {"state": "open", "per_page": 100, "page": 1}
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
                msg = "Expected list of dictionaries from Service Github API."
                raise ValueError(msg)
            all_issues.extend(issues)
            assert isinstance(params["page"], int)
            params["page"] += 1
        return all_issues

    def get_issue_comments(
        self, issue_number: int, comment_id: int | None = None
    ) -> list[str] | None:
        """Download comments for a specific issue from Github.

        Args:
            issue_number: Issue number to get comments for
            comment_id: Optional specific comment ID to retrieve

        Returns:
            List of comment bodies or None if no comments

        """
        url = f"{self.download_url}/{issue_number}/comments"
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
            f"{self.base_url}/branches/{branch_name}", headers=self.headers
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
        """Reply to a review thread comment using GraphQL API.

        Args:
            pr_number: Pull request number
            comment_id: Review thread comment ID
            reply: Reply message to post

        """
        query = "\n            mutation($body: String!, $pullRequestReviewThreadId: ID!) {\n                addPullRequestReviewThreadReply(input: { body: $body, pullRequestReviewThreadId: $pullRequestReviewThreadId }) {\n                    comment {\n                        id\n                        body\n                        createdAt\n                    }\n                }\n            }\n            "
        comment_reply = f"Forge fix success summary\n\n\n{reply}"
        variables = {"body": comment_reply, "pullRequestReviewThreadId": comment_id}
        url = self.get_graphql_url()
        headers = {
            "Authorization": f"Bearer {self.token}",
            "Content-Type": "application/json",
        }
        response = httpx.post(
            url, json={"query": query, "variables": variables}, headers=headers
        )
        response.raise_for_status()

    def get_pull_url(self, pr_number: int) -> str:
        """Get GitHub web URL for a pull request."""
        return f"https://{self.base_domain}/{self.owner}/{self.repo}/pull/{pr_number}"

    def get_default_branch_name(self) -> str:
        """Get default branch name from repository settings."""
        response = httpx.get(f"{self.base_url}", headers=self.headers)
        response.raise_for_status()
        data = response.json()
        return str(data["default_branch"])

    def create_pull_request(self, data: dict[str, Any] | None = None) -> dict[str, Any]:
        """Create a pull request with the provided data.

        Args:
            data: PR data dictionary (title, body, head, base, etc.)

        Returns:
            Dictionary with created PR data

        Raises:
            RuntimeError: If token lacks push permissions

        """
        if data is None:
            data = {}
        response = httpx.post(f"{self.base_url}/pulls", headers=self.headers, json=data)
        if response.status_code == 403:
            msg = "Failed to create pull request due to missing permissions. Make sure that the provided token has push permissions for the repository."
            raise RuntimeError(
                msg,
            )
        response.raise_for_status()
        pr_data = response.json()
        return dict(pr_data)

    def request_reviewers(self, reviewer: str, pr_number: int) -> None:
        """Request review from a user on a pull request.

        Args:
            reviewer: GitHub username to request review from
            pr_number: Pull request number

        """
        review_data = {"reviewers": [reviewer]}
        review_response = httpx.post(
            f"{self.base_url}/pulls/{pr_number}/requested_reviewers",
            headers=self.headers,
            json=review_data,
        )
        if review_response.status_code != 201:
            logger.warning(
                "Failed to request review from %s: %s", reviewer, review_response.text
            )

    def send_comment_msg(self, issue_number: int, msg: str) -> None:
        """Send a comment message to a GitHub issue or pull request.

        Args:
            issue_number: The issue or pull request number
            msg: The message content to post as a comment

        """
        comment_url = f"{self.base_url}/issues/{issue_number}/comments"
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
            List of context strings (empty for GitHub)

        """
        return closing_issues


class GithubPRHandler(GithubIssueHandler):
    """GitHub handler specialized for pull request operations.

    Extends GithubIssueHandler with PR-specific functionality including
    review thread handling and PR metadata extraction.
    """

    def __init__(
        self,
        owner: str,
        repo: str,
        token: str,
        username: str | None = None,
        base_domain: str = "github.com",
    ) -> None:
        """Initialize a GitHub PR handler.

        Args:
            owner: The owner of the repository
            repo: The name of the repository
            token: The GitHub personal access token
            username: Optional GitHub username
            base_domain: The domain for GitHub Enterprise (default: "github.com")

        """
        super().__init__(owner, repo, token, username, base_domain)
        if self.base_domain == "github.com":
            self.download_url = (
                f"https://api.github.com/repos/{self.owner}/{self.repo}/pulls"
            )
        else:
            self.download_url = f"https://{self.base_domain}/api/v3/repos/{self.owner}/{self.repo}/pulls"

    def download_pr_metadata(
        self,
        pull_number: int,
        comment_id: int | None = None,
    ) -> tuple[list[str], list[int], list[str], list[ReviewThread], list[str]]:
        """Run a GraphQL query against the GitHub API for information.

        Retrieves information about:
            1. unresolved review comments
            2. referenced issues the pull request would close

        Args:
            pull_number: The number of the pull request to query.
            comment_id: Optional ID of a specific comment to focus on.
            query: The GraphQL query as a string.
            variables: A dictionary of variables for the query.
            token: Your GitHub personal access token.

        Returns:
            The JSON response from the GitHub API.

        """
        # Execute GraphQL query
        response_json = self._execute_graphql_query(pull_number)

        # Extract PR data
        pr_data = self._extract_pr_data(response_json)

        # Process closing issues
        closing_issues_bodies, closing_issue_numbers = self._process_closing_issues(
            pr_data
        )

        # Process reviews
        review_bodies = self._process_reviews(pr_data, comment_id)

        # Process review threads
        review_threads, thread_ids = self._process_review_threads(pr_data, comment_id)

        return (
            closing_issues_bodies,
            closing_issue_numbers,
            review_bodies,
            review_threads,
            thread_ids,
        )

    def _execute_graphql_query(self, pull_number: int) -> dict:
        """Execute the GraphQL query against GitHub API."""
        query = self._build_graphql_query()
        variables = {"owner": self.owner, "repo": self.repo, "pr": pull_number}
        url = self.get_graphql_url()
        headers = {
            "Authorization": f"Bearer {self.token}",
            "Content-Type": "application/json",
        }

        response = httpx.post(
            url, json={"query": query, "variables": variables}, headers=headers
        )
        response.raise_for_status()
        return response.json()

    def _build_graphql_query(self) -> str:
        """Build the GraphQL query for PR metadata."""
        return """
                query($owner: String!, $repo: String!, $pr: Int!) {
                    repository(owner: $owner, name: $repo) {
                        pullRequest(number: $pr) {
                            closingIssuesReferences(first: 10) {
                                edges {
                                    node {
                                        body
                                        number
                                    }
                                }
                            }
                            url
                            reviews(first: 100) {
                                nodes {
                                    body
                                    state
                                    fullDatabaseId
                                }
                            }
                            reviewThreads(first: 100) {
                                edges{
                                    node{
                                        id
                                        isResolved
                                        comments(first: 100) {
                                            totalCount
                                            nodes {
                                                body
                                                path
                                                fullDatabaseId
                                            }
                                        }
                                    }
                                }
                            }
                        }
                    }
                }
            """

    def _extract_pr_data(self, response_json: dict) -> dict:
        """Extract PR data from the GraphQL response."""
        return (
            response_json.get("data", {}).get("repository", {}).get("pullRequest", {})
        )

    def _process_closing_issues(self, pr_data: dict) -> tuple[list[str], list[int]]:
        """Process closing issues from PR data."""
        closing_issues = pr_data.get("closingIssuesReferences", {}).get("edges", [])
        closing_issues_bodies = [issue["node"]["body"] for issue in closing_issues]
        closing_issue_numbers = [issue["node"]["number"] for issue in closing_issues]
        return closing_issues_bodies, closing_issue_numbers

    def _process_reviews(self, pr_data: dict, comment_id: int | None) -> list[str]:
        """Process reviews from PR data."""
        reviews = pr_data.get("reviews", {}).get("nodes", [])

        if comment_id is not None:
            reviews = [
                review
                for review in reviews
                if int(review["fullDatabaseId"]) == comment_id
            ]

        return [review["body"] for review in reviews]

    def _process_review_threads(
        self, pr_data: dict, comment_id: int | None
    ) -> tuple[list[ReviewThread], list[str]]:
        """Process review threads from PR data."""
        review_threads = []
        thread_ids = []
        raw_review_threads = pr_data.get("reviewThreads", {}).get("edges", [])

        for thread in raw_review_threads:
            node = thread.get("node", {})
            if not node.get("isResolved", True):
                thread_id = node.get("id")
                thread_contains_comment_id = False
                my_review_threads = node.get("comments", {}).get("nodes", [])

                message, files, thread_contains_comment_id = (
                    self._process_thread_comments(
                        my_review_threads,
                        comment_id,
                    )
                )

                if comment_id is None or thread_contains_comment_id:
                    unresolved_thread = ReviewThread(comment=message, files=files)
                    review_threads.append(unresolved_thread)
                    thread_ids.append(thread_id)

        return review_threads, thread_ids

    def _process_thread_comments(
        self,
        my_review_threads: list,
        comment_id: int | None,
    ) -> tuple[str, list[str], bool]:
        """Process comments within a review thread."""
        message = ""
        files = []
        thread_contains_comment_id = False

        for i, review_thread in enumerate(my_review_threads):
            if comment_id is not None:
                try:
                    comment_identifier = review_thread.get("fullDatabaseId")
                    if (
                        comment_identifier is not None
                        and int(comment_identifier) == comment_id
                    ):
                        thread_contains_comment_id = True
                except (TypeError, ValueError):
                    pass
            if i == len(my_review_threads) - 1:
                if len(my_review_threads) > 1:
                    message += "---\n"
                message += "latest feedback:\n" + review_thread["body"] + "\n"
            else:
                message += review_thread["body"] + "\n"

            file = review_thread.get("path")
            if file and file not in files:
                files.append(file)

        return message, files, thread_contains_comment_id

    def get_pr_comments(
        self, pr_number: int, comment_id: int | None = None
    ) -> list[str] | None:
        """Download comments for a specific pull request from Github."""
        if self.base_domain == "github.com":
            url = f"https://api.github.com/repos/{self.owner}/{self.repo}/issues/{pr_number}/comments"
        else:
            url = f"https://{self.base_domain}/api/v3/repos/{self.owner}/{self.repo}/issues/{pr_number}/comments"
        headers = {
            "Authorization": f"token {self.token}",
            "Accept": "application/vnd.github.v3+json",
        }
        params = {"per_page": 100, "page": 1}
        all_comments = []
        while True:
            response = httpx.get(url, headers=headers, params=params)
            response.raise_for_status()
            comments = response.json()
            if not comments:
                break
            if comment_id is None:
                all_comments.extend([comment["body"] for comment in comments])
            elif matching_comment := next(
                (
                    comment["body"]
                    for comment in comments
                    if comment["id"] == comment_id
                ),
                None,
            ):
                return [matching_comment]
            params["page"] += 1
        return all_comments or None

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
            # Build URL based on domain
            if self.base_domain == "github.com":
                url = f"https://api.github.com/repos/{self.owner}/{self.repo}/issues/{issue_number}"
            else:
                url = f"https://{self.base_domain}/api/v3/repos/{self.owner}/{self.repo}/issues/{issue_number}"

            headers = {
                "Authorization": f"Bearer {self.token}",
                "Accept": "application/vnd.github.v3+json",
            }
            response = httpx.get(url, headers=headers)
            response.raise_for_status()
            issue_data = response.json()
            return issue_data.get("body", "")
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
        """Convert selected issues into Issue dataclasses for downstream processing."""
        if not issue_numbers:
            msg = "Unspecified issue numbers"
            raise ValueError(msg)
        all_issues = self.download_issues()
        logger.info("Limiting resolving to issues %s.", issue_numbers)
        all_issues = [issue for issue in all_issues if issue["number"] in issue_numbers]
        converted_issues = []
        for issue in all_issues:
            if any(issue.get(key) is None for key in ["number", "title"]):
                logger.warning("Skipping #%s as it is missing number or title.", issue)
                continue
            body = issue.get("body") if issue.get("body") is not None else ""
            (
                closing_issues,
                closing_issues_numbers,
                review_comments,
                review_threads,
                thread_ids,
            ) = self.download_pr_metadata(issue["number"], comment_id=comment_id)
            head_branch = issue["head"]["ref"]
            thread_comments = self.get_pr_comments(
                issue["number"], comment_id=comment_id
            )
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
                number=issue["number"],
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
