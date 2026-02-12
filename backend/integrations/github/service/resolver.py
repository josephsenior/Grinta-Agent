"""GitHub mixin providing helper queries for the resolver workflow."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from backend.core.logger import forge_logger as logger
from backend.integrations.github.queries import (
    get_review_threads_graphql_query,
    get_thread_comments_graphql_query,
    get_thread_from_comment_graphql_query,
)
from backend.integrations.github.service.base import GitHubMixinBase
from backend.integrations.service_types import Comment


class GitHubResolverMixin(GitHubMixinBase):
    """Helper methods used for the GitHub Resolver."""

    async def get_issue_or_pr_title_and_body(
        self, repository: str, issue_number: int
    ) -> tuple[str, str]:
        """Get the title and body of an issue.

        Args:
            repository: Repository name in format 'owner/repo'
            issue_number: The issue number

        Returns:
            A tuple of (title, body)

        """
        url = f"{self.BASE_URL}/repos/{repository}/issues/{issue_number}"
        response, _ = await self._make_request(url)
        title = response.get("title") or ""
        body = response.get("body") or ""
        return (title, body)

    async def get_issue_or_pr_comments(
        self,
        repository: str,
        issue_number: int,
        max_comments: int = 10,
    ) -> list[Comment]:
        """Get comments for an issue.

        Args:
            repository: Repository name in format 'owner/repo'
            issue_number: The issue number
            max_comments: Maximum number of comments to retrieve

        Returns:
            List of Comment objects ordered by creation date

        """
        url = f"{self.BASE_URL}/repos/{repository}/issues/{issue_number}/comments"
        page = 1
        all_comments: list[dict] = []
        while len(all_comments) < max_comments:
            params = {
                "per_page": 10,
                "sort": "created",
                "direction": "asc",
                "page": page,
            }
            response, headers = await self._make_request(url, params=params)
            all_comments.extend(response or [])
            link_header = headers.get("Link", "")
            if 'rel="next"' not in link_header:
                break
            page += 1
        return self._process_raw_comments(all_comments)

    async def _get_comment_node(self, comment_id: str) -> dict | None:
        """Get comment node from GraphQL query."""
        variables = {"commentId": comment_id}
        data = await self.execute_graphql_query(
            get_thread_from_comment_graphql_query, variables
        )
        return data.get("data", {}).get("node")

    def _find_root_comment_id(self, comment_node: dict, comment_id: str) -> str:
        """Find the root comment ID by traversing up the reply chain."""
        return (
            reply_to["id"] if (reply_to := comment_node.get("replyTo")) else comment_id
        )

    async def _find_thread_id(
        self, root_comment_id: str, owner: str, repo: str, pr_number: int
    ) -> str | None:
        """Find the thread ID by searching through review threads."""
        thread_id = None
        after_cursor = None
        has_next_page = True

        while has_next_page and not thread_id:
            threads_variables: dict[str, Any] = {
                "owner": owner,
                "repo": repo,
                "number": pr_number,
                "first": 50,
            }
            if after_cursor:
                threads_variables["after"] = after_cursor

            threads_data = await self.execute_graphql_query(
                get_review_threads_graphql_query, threads_variables
            )
            review_threads_data = (
                threads_data.get("data", {})
                .get("repository", {})
                .get("pullRequest", {})
                .get("reviewThreads", {})
            )
            review_threads = review_threads_data.get("nodes", [])
            page_info = review_threads_data.get("pageInfo", {})

            thread_id = self._search_threads_for_root_comment(
                review_threads, root_comment_id
            )

            has_next_page = page_info.get("hasNextPage", False)
            after_cursor = page_info.get("endCursor")

        return thread_id

    def _search_threads_for_root_comment(
        self, review_threads: list, root_comment_id: str
    ) -> str | None:
        """Search through review threads to find the one containing the root comment."""
        for thread in review_threads:
            first_comments = thread.get("comments", {}).get("nodes", [])
            for first_comment in first_comments:
                if first_comment.get("id") == root_comment_id:
                    return thread.get("id")
        return None

    async def _get_all_thread_comments(self, thread_id: str) -> list[dict]:
        """Get all comments in the identified thread."""
        all_thread_comments = []
        after_cursor = None
        has_next_page = True
        while has_next_page:
            comments_variables: dict[str, Any] = {"threadId": thread_id, "page": 50}
            if after_cursor:
                comments_variables["after"] = after_cursor
            thread_comments_data = await self.execute_graphql_query(
                get_thread_comments_graphql_query,
                comments_variables,
            )
            thread_node = thread_comments_data.get("data", {}).get("node")
            if not thread_node:
                break
            comments_data = thread_node.get("comments", {})
            comments_nodes = comments_data.get("nodes", [])
            page_info = comments_data.get("pageInfo", {})
            all_thread_comments.extend(comments_nodes)
            has_next_page = page_info.get("hasNextPage", False)
            after_cursor = page_info.get("endCursor")
        return all_thread_comments

    async def get_review_thread_comments(
        self, comment_id: str, repository: str, pr_number: int
    ) -> list[Comment]:
        """Get all comments in a review thread starting from a specific comment.

        Uses GraphQL to traverse the reply chain from the given comment up to the root
        comment, then finds the review thread and returns all comments in the thread.

        Args:
            comment_id: The GraphQL node ID of any comment in the thread
            repository: Repository name
            pr_number: Pull request number

        Returns:
            List of Comment objects representing the entire thread

        """
        comment_node = await self._get_comment_node(comment_id)
        if not comment_node:
            return []

        root_comment_id = self._find_root_comment_id(comment_node, comment_id)
        owner, repo = repository.split("/")

        thread_id = await self._find_thread_id(root_comment_id, owner, repo, pr_number)
        if not thread_id:
            logger.warning(
                "Could not find review thread for comment %s, returning traversed comments",
                comment_id,
            )
            return []

        raw_comments = await self._get_all_thread_comments(thread_id)
        return self._process_raw_comments(raw_comments)

    def _process_raw_comments(
        self, comments_data: list, max_comments: int = 10
    ) -> list[Comment]:
        """Convert raw comment data to Comment objects."""
        comments: list[Comment] = []
        for comment in comments_data:
            author = "unknown"
            if comment.get("author"):
                author = comment.get("author", {}).get("login", "unknown")
            elif comment.get("user"):
                author = comment.get("user", {}).get("login", "unknown")
            comments.append(
                Comment(
                    id=str(comment.get("id", "unknown")),
                    body=self._truncate_comment(comment.get("body", "")),
                    author=author,
                    created_at=(
                        datetime.fromisoformat(
                            comment.get("createdAt", "").replace("Z", "+00:00")
                        )
                        if comment.get("createdAt")
                        else datetime.fromtimestamp(0)
                    ),
                    updated_at=(
                        datetime.fromisoformat(
                            comment.get("updatedAt", "").replace("Z", "+00:00")
                        )
                        if comment.get("updatedAt")
                        else datetime.fromtimestamp(0)
                    ),
                    system=False,
                ),
            )
        comments.sort(key=lambda c: c.created_at)
        return comments[-max_comments:]
