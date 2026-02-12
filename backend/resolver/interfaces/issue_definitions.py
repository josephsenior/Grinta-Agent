"""Typed wrappers for resolver issue and pull request service contexts."""

from __future__ import annotations

import json
import os
import re
from typing import TYPE_CHECKING, Any, ClassVar

import jinja2
from backend.models.exceptions import RateLimitError as RateLimitErrorType

from backend.models.llm import LLM
from backend.resolver.utils import extract_image_urls

if TYPE_CHECKING:
    from backend.core.config import LLMConfig
    from backend.events.event import Event
    from backend.resolver.interfaces.issue import (
        Issue,
        IssueHandlerInterface,
        ReviewThread,
    )


class ServiceContext:
    """Base service context for issue resolution strategies.

    Provides common functionality for interacting with issue tracking systems
    and managing LLM-based resolution strategies.
    """

    issue_type: ClassVar[str]
    default_git_patch: ClassVar[str] = "No changes made yet"

    def __init__(
        self, strategy: IssueHandlerInterface, llm_config: LLMConfig | None
    ) -> None:
        """Initialize service context with resolution strategy and LLM config.

        Args:
            strategy: Issue handler implementation for specific platform
            llm_config: Optional LLM configuration for AI-assisted resolution

        """
        self._strategy = strategy
        if llm_config is not None:
            self.llm = LLM(llm_config, service_id="resolver")

    def set_strategy(self, strategy: IssueHandlerInterface) -> None:
        """Update the issue resolution strategy.

        Args:
            strategy: New strategy implementation to use

        """
        self._strategy = strategy


class ServiceContextPR(ServiceContext):
    """Service context for pull request resolution workflows.

    Handles PR-specific operations including review feedback processing,
    closing issue verification, and success evaluation.
    """

    issue_type: ClassVar[str] = "pr"

    def __init__(self, strategy: IssueHandlerInterface, llm_config: LLMConfig) -> None:
        """Initialize PR service context.

        Args:
            strategy: Issue handler for PR operations
            llm_config: LLM configuration for AI-assisted resolution

        """
        super().__init__(strategy, llm_config)

    def get_clone_url(self) -> str:
        """Get repository clone URL for the PR.

        Returns:
            Git clone URL string

        """
        return self._strategy.get_clone_url()

    def download_issues(self) -> list[Any]:
        """Download associated issues for the PR.

        Returns:
            List of issue data dictionaries

        """
        return self._strategy.download_issues()

    def guess_success(
        self,
        issue: Issue,
        history: list[Event],
        git_patch: str | None = None,
    ) -> tuple[bool, None | list[bool], str]:
        """Guess if the issue is fixed based on the history, issue description and git patch.

        Args:
            issue: The issue to check
            history: The agent's history
            git_patch: Optional git patch showing the changes made

        Returns:
            Tuple of (overall_success, success_list, explanations_json)

        """
        last_message = history[-1].message
        issues_context = json.dumps(issue.closing_issues, indent=4)

        success_list, explanation_list = self._check_all_feedback_sources(
            issue,
            issues_context,
            last_message,
            git_patch,
        )

        if not success_list:
            return (False, None, "No feedback was found to process")

        return (all(success_list), success_list, json.dumps(explanation_list))

    def _check_all_feedback_sources(
        self,
        issue: Issue,
        issues_context: str,
        last_message: str | None,
        git_patch: str | None,
    ) -> tuple[list[bool], list[str]]:
        """Check all feedback sources for success.

        Args:
            issue: Issue to check
            issues_context: JSON context of closing issues
            last_message: Last message from history
            git_patch: Optional git patch

        Returns:
            Tuple of (success_list, explanation_list)

        """
        success_list: list[bool] = []
        explanation_list: list[str] = []

        if issue.review_threads:
            self._check_review_threads(
                issue.review_threads,
                issues_context,
                last_message,
                git_patch,
                success_list,
                explanation_list,
            )
        elif issue.thread_comments:
            self._check_single_source(
                lambda: self._check_thread_comments(
                    issue.thread_comments, issues_context, last_message, git_patch
                ),
                "Missing thread comments, context or message",
                success_list,
                explanation_list,
            )
        elif issue.review_comments:
            self._check_single_source(
                lambda: self._check_review_comments(
                    issue.review_comments, issues_context, last_message, git_patch
                ),
                "Missing review comments, context or message",
                success_list,
                explanation_list,
            )

        return success_list, explanation_list

    def _check_review_threads(
        self,
        review_threads,
        issues_context: str,
        last_message: str | None,
        git_patch: str | None,
        success_list: list[bool],
        explanation_list: list[str],
    ) -> None:
        """Check review threads for success.

        Args:
            review_threads: List of review threads
            issues_context: Issues context
            last_message: Last message
            git_patch: Git patch
            success_list: List to append success bools to
            explanation_list: List to append explanations to

        """
        for review_thread in review_threads:
            if issues_context and last_message:
                success, explanation = self._check_review_thread(
                    review_thread,
                    issues_context,
                    last_message,
                    git_patch,
                )
            else:
                success, explanation = (False, "Missing context or message")
            success_list.append(success)
            explanation_list.append(explanation)

    def _check_single_source(
        self,
        check_func,
        error_msg: str,
        success_list: list[bool],
        explanation_list: list[str],
    ) -> None:
        """Check a single feedback source.

        Args:
            check_func: Function to call for checking
            error_msg: Error message if missing
            success_list: List to append success bool to
            explanation_list: List to append explanation to

        """
        try:
            success, explanation = check_func()
        except RateLimitErrorType:
            raise
        except Exception:
            success, explanation = (False, error_msg)

        success_list.append(success)
        explanation_list.append(explanation)

    def get_converted_issues(
        self,
        issue_numbers: list[int] | None = None,
        comment_id: int | None = None,
    ) -> list[Issue]:
        """Get issues converted to internal format.

        Args:
            issue_numbers: Optional list of specific issue numbers to retrieve
            comment_id: Optional comment ID to include

        Returns:
            List of Issue objects in internal format

        """
        return self._strategy.get_converted_issues(issue_numbers, comment_id)

    def get_instruction(
        self,
        issue: Issue,
        user_instructions_prompt_template: str,
        conversation_instructions_prompt_template: str,
        repo_instruction: str | None = None,
    ) -> tuple[str, str, list[str]]:
        """Generate instructions for agent from issue and PR feedback.

        Renders Jinja2 templates with issue context, review comments, review threads,
        and extracts any image URLs from the content.

        Args:
            issue: Issue object with review data
            user_instructions_prompt_template: Template for user-specific instructions
            conversation_instructions_prompt_template: Template for conversation instructions
            repo_instruction: Optional repository-specific instructions

        Returns:
            Tuple of (user_instruction, conversation_instructions, image_urls)

        """
        # nosec B701 - Template rendering for prompts (not HTML), controlled input
        user_instruction_template = jinja2.Template(user_instructions_prompt_template)
        conversation_instructions_template = jinja2.Template(
            conversation_instructions_prompt_template,
        )
        images = []
        issues_str = None
        if issue.closing_issues:
            issues_str = json.dumps(issue.closing_issues, indent=4)
            images.extend(extract_image_urls(issues_str))
        review_comments_str = None
        if issue.review_comments:
            review_comments_str = json.dumps(issue.review_comments, indent=4)
            images.extend(extract_image_urls(review_comments_str))
        review_thread_str = None
        review_thread_file_str = None
        if issue.review_threads:
            review_threads = [
                review_thread.comment for review_thread in issue.review_threads
            ]
            review_thread_files = []
            for review_thread in issue.review_threads:
                review_thread_files.extend(review_thread.files)
            review_thread_str = json.dumps(review_threads, indent=4)
            review_thread_file_str = json.dumps(review_thread_files, indent=4)
            images.extend(extract_image_urls(review_thread_str))
        thread_context = ""
        if issue.thread_comments:
            thread_context = "\n---\n".join(issue.thread_comments)
            images.extend(extract_image_urls(thread_context))
        user_instruction = user_instruction_template.render(
            review_comments=review_comments_str,
            review_threads=review_thread_str,
            files=review_thread_file_str,
            thread_context=thread_context,
        )
        conversation_instructions = conversation_instructions_template.render(
            issues=issues_str,
            repo_instruction=repo_instruction,
        )
        return (user_instruction, conversation_instructions, images)

    def _check_feedback_with_llm(self, prompt: str) -> tuple[bool, str]:
        """Helper function to check feedback with LLM and parse response."""
        response = self.llm.completion(messages=[{"role": "user", "content": prompt}])
        answer = response.choices[0].message.content.strip()
        pattern = "--- success\\n*(true|false)\\n*--- explanation*\\n((?:.|\\n)*)"
        if match := re.search(pattern, answer):
            return (match[1].lower() == "true", match[2].strip())
        return (False, f"Failed to decode answer from LLM response: {answer}")

    def _check_review_thread(
        self,
        review_thread: ReviewThread,
        issues_context: str,
        last_message: str,
        git_patch: str | None = None,
    ) -> tuple[bool, str]:
        """Check if a review thread's feedback has been addressed."""
        files_context = json.dumps(review_thread.files, indent=4)
        template_path = os.path.join(
            os.path.dirname(__file__),
            "../prompts/guess_success/pr-feedback-check.jinja",
        )
        with open(template_path, "r", encoding="utf-8") as f:
            template = jinja2.Template(f.read())
        prompt = template.render(
            issue_context=issues_context,
            feedback=review_thread.comment,
            files_context=files_context,
            last_message=last_message,
            git_patch=git_patch or self.default_git_patch,
        )
        return self._check_feedback_with_llm(prompt)

    def _check_thread_comments(
        self,
        thread_comments: list[str],
        issues_context: str,
        last_message: str | None,
        git_patch: str | None = None,
    ) -> tuple[bool, str]:
        """Check if thread comments feedback has been addressed."""
        thread_context = "\n---\n".join(thread_comments)
        template_path = os.path.join(
            os.path.dirname(__file__),
            "../prompts/guess_success/pr-thread-check.jinja",
        )
        with open(template_path, "r", encoding="utf-8") as f:
            template = jinja2.Template(f.read())
        prompt = template.render(
            issue_context=issues_context,
            thread_context=thread_context,
            last_message=last_message or "",
            git_patch=git_patch or self.default_git_patch,
        )
        return self._check_feedback_with_llm(prompt)

    def _check_review_comments(
        self,
        review_comments: list[str],
        issues_context: str,
        last_message: str | None,
        git_patch: str | None = None,
    ) -> tuple[bool, str]:
        """Check if review comments feedback has been addressed."""
        review_context = "\n---\n".join(review_comments)
        template_path = os.path.join(
            os.path.dirname(__file__),
            "../prompts/guess_success/pr-review-check.jinja",
        )
        with open(template_path, "r", encoding="utf-8") as f:
            template = jinja2.Template(f.read())
        prompt = template.render(
            issue_context=issues_context,
            review_context=review_context,
            last_message=last_message or "",
            git_patch=git_patch or self.default_git_patch,
        )
        return self._check_feedback_with_llm(prompt)


class ServiceContextIssue(ServiceContext):
    """Service context for issue resolution workflows.

    Handles issue-specific operations including branch management, PR creation,
    comments, and resolution verification.
    """

    issue_type: ClassVar[str] = "issue"

    def __init__(
        self, strategy: IssueHandlerInterface, llm_config: LLMConfig | None
    ) -> None:
        """Initialize issue service context.

        Args:
            strategy: Issue handler for issue operations
            llm_config: Optional LLM configuration for AI-assisted resolution

        """
        super().__init__(strategy, llm_config)

    def get_base_url(self) -> str:
        """Get base URL of the repository/issue tracker."""
        return self._strategy.get_base_url()

    def get_branch_url(self, branch_name: str) -> str:
        """Get URL for a specific branch."""
        return self._strategy.get_branch_url(branch_name)

    def get_download_url(self) -> str:
        """Get repository download URL."""
        return self._strategy.get_download_url()

    def get_clone_url(self) -> str:
        """Get repository clone URL."""
        return self._strategy.get_clone_url()

    def get_graphql_url(self) -> str:
        """Get GraphQL API URL for the service."""
        return self._strategy.get_graphql_url()

    def get_headers(self) -> dict[str, str]:
        """Get HTTP headers for API requests."""
        return self._strategy.get_headers()

    def get_authorize_url(self) -> str:
        """Get OAuth authorization URL."""
        return self._strategy.get_authorize_url()

    def get_pull_url(self, pr_number: int) -> str:
        """Get URL for a specific pull request."""
        return self._strategy.get_pull_url(pr_number)

    def get_compare_url(self, branch_name: str) -> str:
        """Get URL for comparing branch with default branch."""
        return self._strategy.get_compare_url(branch_name)

    def download_issues(self) -> list[Any]:
        """Download issues from the tracker."""
        return self._strategy.download_issues()

    def get_branch_name(self, base_branch_name: str) -> str:
        """Generate branch name for issue fix."""
        return self._strategy.get_branch_name(base_branch_name)

    def branch_exists(self, branch_name: str) -> bool:
        """Check if a branch exists in the repository."""
        return self._strategy.branch_exists(branch_name)

    def get_default_branch_name(self) -> str:
        """Get default branch name (e.g., 'main', 'master')."""
        return self._strategy.get_default_branch_name()

    def create_pull_request(self, data: dict[str, Any] | None = None) -> dict[str, Any]:
        """Create a pull request with the provided data."""
        if data is None:
            data = {}
        return self._strategy.create_pull_request(data)

    def request_reviewers(self, reviewer: str, pr_number: int) -> None:
        """Request review from a user on a pull request."""
        return self._strategy.request_reviewers(reviewer, pr_number)

    def reply_to_comment(self, pr_number: int, comment_id: str, reply: str) -> None:
        """Reply to a specific comment on a pull request."""
        return self._strategy.reply_to_comment(pr_number, comment_id, reply)

    def send_comment_msg(self, issue_number: int, msg: str) -> None:
        """Send a comment message to an issue."""
        return self._strategy.send_comment_msg(issue_number, msg)

    def get_issue_comments(
        self,
        issue_number: int,
        comment_id: int | None = None,
    ) -> list[str] | None:
        """Get comments for an issue, optionally starting from a specific comment."""
        return self._strategy.get_issue_comments(issue_number, comment_id)

    def get_instruction(
        self,
        issue: Issue,
        user_instructions_prompt_template: str,
        conversation_instructions_prompt_template: str,
        repo_instruction: str | None = None,
    ) -> tuple[str, str, list[str]]:
        """Generate instructions for agent from issue details.

        Renders Jinja2 templates with issue title, body, thread comments,
        and extracts any image URLs from the content.

        Args:
            issue: Issue object with title, body, and comments
            user_instructions_prompt_template: Template for user-specific instructions
            conversation_instructions_prompt_template: Template for conversation instructions
            repo_instruction: Optional repository-specific instructions

        Returns:
            Tuple of (user_instruction, conversation_instructions, image_urls)

        """
        thread_context = ""
        if issue.thread_comments:
            thread_context = "\n\nIssue Thread Comments:\n" + "\n---\n".join(
                issue.thread_comments,
            )
        images = []
        images.extend(extract_image_urls(issue.body))
        images.extend(extract_image_urls(thread_context))
        # nosec B701 - Template rendering for prompts (not HTML), controlled input
        user_instructions_template = jinja2.Template(user_instructions_prompt_template)
        user_instructions = user_instructions_template.render(
            body=issue.title + "\n\n" + issue.body + thread_context,
        )
        conversation_instructions_template = jinja2.Template(
            conversation_instructions_prompt_template,
        )
        conversation_instructions = conversation_instructions_template.render(
            repo_instruction=repo_instruction,
        )
        return (user_instructions, conversation_instructions, images)

    def guess_success(
        self,
        issue: Issue,
        history: list[Event],
        git_patch: str | None = None,
    ) -> tuple[bool, None | list[bool], str]:
        """Guess if the issue is fixed based on the history and the issue description.

        Uses LLM to analyze the agent's last message, issue context, and git patch
        to determine if the issue has been successfully resolved.

        Args:
            issue: The issue to check
            history: The agent's history
            git_patch: Optional git patch showing the changes made

        Returns:
            Tuple of (success, None, explanation)

        """
        last_message = history[-1].message
        issue_context = issue.body
        if issue.thread_comments:
            issue_context += "\n\nIssue Thread Comments:\n" + "\n---\n".join(
                issue.thread_comments,
            )
        with open(
            os.path.join(
                os.path.dirname(__file__),
                "../prompts/guess_success/issue-success-check.jinja",
            ),
        ) as f:
            template = jinja2.Template(f.read())
        prompt = template.render(
            issue_context=issue_context,
            last_message=last_message,
            git_patch=git_patch or self.default_git_patch,
        )
        response = self.llm.completion(messages=[{"role": "user", "content": prompt}])
        answer = response.choices[0].message.content.strip()
        pattern = "--- success\\n*(true|false)\\n*--- explanation*\\n((?:.|\\n)*)"
        if match := re.search(pattern, answer):
            return (match[1].lower() == "true", None, match[2])
        return (False, None, f"Failed to decode answer from LLM response: {answer}")

    def get_converted_issues(
        self,
        issue_numbers: list[int] | None = None,
        comment_id: int | None = None,
    ) -> list[Issue]:
        """Get issues converted to internal format.

        Args:
            issue_numbers: Optional list of specific issue numbers to retrieve
            comment_id: Optional comment ID to include

        Returns:
            List of Issue objects in internal format

        """
        return self._strategy.get_converted_issues(issue_numbers, comment_id)
