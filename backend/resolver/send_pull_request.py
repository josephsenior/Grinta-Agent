"""Utilities for preparing local patches, applying changes, and filing pull requests."""

from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
from typing import TYPE_CHECKING

import jinja2
from pydantic import SecretStr

from forge.core.config import LLMConfig
from forge.core.logger import forge_logger as logger
from forge.integrations.service_types import ProviderType
from forge.llm.llm import LLM
from forge.resolver.interfaces.github import GithubIssueHandler
from forge.resolver.interfaces.issue_definitions import ServiceContextIssue
from forge.resolver.io_utils import load_single_resolver_output
from forge.resolver.patching import apply_diff, parse_patch
from forge.resolver.utils import identify_token
from forge.utils.async_utils import GENERAL_TIMEOUT, call_async_from_sync

if TYPE_CHECKING:
    from forge.resolver.interfaces.issue import Issue
    from forge.resolver.resolver_output import ResolverOutput


def _normalize_path(repo_dir: str, path: str | None) -> str | None:
    """Normalize a path by removing git prefixes and joining with repo directory."""
    if not path or path == "/dev/null":
        return None
    normalized = path.removeprefix("a/").removeprefix("b/")
    return os.path.join(repo_dir, normalized)


def _handle_file_deletion(old_path: str | None) -> None:
    """Handle deletion of a file."""
    if old_path is None:
        return

    if os.path.exists(old_path):
        os.remove(old_path)
        logger.info("Deleted file: %s", old_path)


def _handle_file_rename(old_path: str | None, new_path: str, repo_dir: str) -> None:
    """Handle renaming of a file."""
    if not old_path or not new_path:
        return

    os.makedirs(os.path.dirname(new_path), exist_ok=True)

    try:
        shutil.move(old_path, new_path)
    except shutil.SameFileError:
        shutil.copy2(old_path, new_path)
        os.remove(old_path)

    # Clean up empty directories
    old_dir = os.path.dirname(old_path)
    while old_dir and old_dir.startswith(repo_dir):
        try:
            os.rmdir(old_dir)
            old_dir = os.path.dirname(old_dir)
        except OSError:
            break


def _detect_newline_style(file_path: str) -> str | None:
    """Detect the newline style of a file."""
    try:
        with open(file_path, "rb") as f:
            content = f.read()

        if b"\r\n" in content:
            return "\r\n"
        if b"\n" in content:
            return "\n"
        return None
    except Exception:
        return None


def _read_file_content(file_path: str, newline: str | None) -> list[str]:
    """Read file content with proper newline handling."""
    try:
        with open(file_path, newline=newline, encoding="utf-8") as f:
            return [x.strip(newline) for x in f]
    except UnicodeDecodeError as e:
        logger.error("Error reading file %s: %s", file_path, e)
        return []


def _prepare_file_for_patch(old_path: str | None, newline: str | None) -> list[str]:
    """Prepare file content for patching."""
    return _read_file_content(old_path, newline) if old_path else []


def _apply_file_changes(
    diff, split_content: list[str], new_path: str, newline: str | None
) -> None:
    """Apply changes to a file."""
    if diff.changes is None:
        logger.warning("No changes to apply for %s", new_path)
        return

    new_content = apply_diff(diff, split_content)
    os.makedirs(os.path.dirname(new_path), exist_ok=True)

    with open(new_path, "w", newline=newline, encoding="utf-8") as f:
        for line in new_content:
            print(line, file=f)


def apply_patch(repo_dir: str, patch: str) -> None:
    """Apply a patch to a repository.

    Args:
        repo_dir: The directory containing the repository
        patch: The patch to apply

    """
    diffs = parse_patch(patch)

    for diff in diffs:
        if not diff.header.new_path:
            logger.warning("Could not determine file to patch")
            continue

        # Normalize paths
        old_path = _normalize_path(repo_dir, diff.header.old_path)
        new_path = _normalize_path(repo_dir, diff.header.new_path)

        # Handle file deletion
        if diff.header.new_path == "/dev/null":
            _handle_file_deletion(old_path)
            continue

        # Handle file rename
        if old_path and new_path and ("rename from" in patch):
            _handle_file_rename(old_path, new_path, repo_dir)
            continue

        # Prepare for content changes
        if old_path:
            newline = _detect_newline_style(old_path)
            split_content = _prepare_file_for_patch(old_path, newline)
        else:
            newline = "\n"
            split_content = []

        if new_path is None:
            logger.warning("Skipping diff with unknown target path: %s", diff.header)
            continue

        # Apply changes
        _apply_file_changes(diff, split_content, new_path, newline)

    logger.info("Patch applied successfully")


def initialize_repo(
    output_dir: str, issue_number: int, issue_type: str, base_commit: str | None = None
) -> str:
    """Initialize the repository.

    Args:
        output_dir: The output directory to write the repository to
        issue_number: The issue number to fix
        issue_type: The type of the issue
        base_commit: The base commit to checkout (if issue_type is pr)

    """
    src_dir = os.path.join(output_dir, "repo")
    dest_dir = os.path.join(output_dir, "patches", f"{issue_type}_{issue_number}")
    if not os.path.exists(src_dir):
        msg = f"Source directory {src_dir} does not exist."
        raise ValueError(msg)
    if os.path.exists(dest_dir):
        shutil.rmtree(dest_dir)
    shutil.copytree(src_dir, dest_dir)
    logger.info("Copied repository to %s", dest_dir)
    if base_commit:
        result = subprocess.run(
            ["git", "-C", dest_dir, "checkout", base_commit],
            check=False,
            shell=False,
            capture_output=True,
            text=True,
        )
        if result.returncode != 0:
            logger.info("Error checking out commit: %s", result.stderr)
            msg = "Failed to check out commit"
            raise RuntimeError(msg)
    return dest_dir


def make_commit(
    repo_dir: str,
    issue: Issue,
    issue_type: str,
    git_user_name: str = "forge",
    git_user_email: str = "Forge@forge.dev",
) -> None:
    """Make a commit with the changes to the repository.

    Args:
        repo_dir: The directory containing the repository
        issue: The issue to fix
        issue_type: The type of the issue
        git_user_name: Git username for commits
        git_user_email: Git email for commits

    """
    result = subprocess.run(
        ["git", "-C", repo_dir, "config", "user.name"],
        check=False,
        shell=False,
        capture_output=True,
        text=True,
    )
    if not result.stdout.strip():
        subprocess.run(
            ["git", "-C", repo_dir, "config", "user.name", git_user_name],
            shell=False,
            check=True,
        )
        subprocess.run(
            ["git", "-C", repo_dir, "config", "user.email", git_user_email],
            shell=False,
            check=True,
        )
        subprocess.run(
            ["git", "-C", repo_dir, "config", "alias.git", "git --no-pager"],
            shell=False,
            check=True,
        )
        logger.info("Git user configured as %s <%s>", git_user_name, git_user_email)
    result = subprocess.run(
        ["git", "-C", repo_dir, "add", "."],
        check=False,
        shell=False,
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        logger.error("Error adding files: %s", result.stderr)
        msg = "Failed to add files to git"
        raise RuntimeError(msg)
    status_result = subprocess.run(
        ["git", "-C", repo_dir, "status", "--porcelain"],
        check=False,
        shell=False,
        capture_output=True,
        text=True,
    )
    if not status_result.stdout.strip():
        logger.error(
            "No changes to commit for issue #%s. Skipping commit.", issue.number
        )
        msg = "ERROR: Forge failed to make code changes."
        raise RuntimeError(msg)
    commit_message = f"Fix {issue_type} #{issue.number}: {issue.title}"
    result = subprocess.run(
        ["git", "-C", repo_dir, "commit", "-m", commit_message],
        check=False,
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        msg = f"Failed to commit changes: {result}"
        raise RuntimeError(msg)


def _validate_pr_type(pr_type: str) -> None:
    """Validate the pull request type."""
    if pr_type not in ["branch", "draft", "ready"]:
        msg = f"Invalid pr_type: {pr_type}"
        raise ValueError(msg)


def _get_default_base_domain(platform: ProviderType) -> str:
    """Get the default base domain for the platform."""
    return "github.com"


def _create_issue_handler(
    issue: Issue,
    token: str,
    username: str | None,
    platform: ProviderType,
    base_domain: str,
) -> ServiceContextIssue:
    """Create the appropriate issue handler for the platform."""
    return ServiceContextIssue(
        GithubIssueHandler(issue.owner, issue.repo, token, username, base_domain),
        None,
    )


def _determine_base_branch(
    handler: ServiceContextIssue, target_branch: str | None
) -> str:
    """Determine the base branch for the pull request."""
    if not target_branch:
        return handler.get_default_branch_name()
    if handler.branch_exists(branch_name=target_branch):
        return target_branch
    msg = f"Target branch {target_branch} does not exist"
    raise ValueError(msg)


def _create_and_checkout_branch(patch_dir: str, branch_name: str) -> None:
    """Create and checkout a new branch."""
    result = subprocess.run(
        ["git", "-C", patch_dir, "checkout", "-b", branch_name],
        check=False,
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        logger.error("Error creating new branch: %s", result.stderr)
        msg = f"Failed to create a new branch {branch_name} in {patch_dir}:"
        raise RuntimeError(msg)


def _push_changes(
    handler: ServiceContextIssue,
    patch_dir: str,
    branch_name: str,
    fork_owner: str | None,
    issue: Issue,
) -> None:
    """Push changes to the remote repository."""
    push_owner = fork_owner or issue.owner
    handler._strategy.set_owner(push_owner)

    push_url = handler.get_clone_url()
    result = subprocess.run(
        ["git", "-C", patch_dir, "push", push_url, branch_name],
        check=False,
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        logger.error("Error pushing changes: %s", result.stderr)
        msg = "Failed to push changes to the remote repository"
        raise RuntimeError(msg)


def _build_pr_content(
    issue: Issue, pr_title: str | None, additional_message: str | None
) -> tuple[str, str]:
    """Build the pull request title and body."""
    final_pr_title = pr_title or f"Fix issue #{issue.number}: {issue.title}"
    pr_body = f"This pull request fixes #{issue.number}."

    if additional_message:
        pr_body += f"\n\n{additional_message}"

    pr_body += "\n\nAutomatic fix generated by [Forge](https://github.com/Forge/Forge/) 🙌"

    return final_pr_title, pr_body


def _create_pull_request(
    handler: ServiceContextIssue,
    platform: ProviderType,
    final_pr_title: str,
    pr_body: str,
    head_branch: str,
    base_branch: str,
    pr_type: str,
    reviewer: str | None,
) -> str:
    """Create the pull request and return its URL."""
    data = {
        "title": final_pr_title,
        "body": pr_body,
        "head": head_branch,
        "base": base_branch,
        "draft": pr_type == "draft",
    }

    pr_data = handler.create_pull_request(data)
    url = pr_data["html_url"]

    if reviewer:
        number = pr_data["number"]
        handler.request_reviewers(reviewer, number)

    return url


def send_pull_request(
    issue: Issue,
    token: str,
    username: str | None,
    platform: ProviderType,
    patch_dir: str,
    pr_type: str,
    fork_owner: str | None = None,
    additional_message: str | None = None,
    target_branch: str | None = None,
    reviewer: str | None = None,
    pr_title: str | None = None,
    base_domain: str = "github.com",
    git_user_name: str = "forge",
    git_user_email: str = "Forge@forge.dev",
) -> str:
    """Send a pull request to a GitHub repository.

    Args:
        issue: The issue to send the pull request for
        token: The token to use for authentication
        username: The username, if provided
        platform: The platform of the repository.
        patch_dir: The directory containing the patches to apply
        pr_type: The type: branch (no PR created), draft or ready (regular PR created)
        fork_owner: The owner of the fork to push changes to (if different from the original repo owner)
        additional_message: The additional messages to post as a comment on the PR in json list format
        target_branch: The target branch to create the pull request against (defaults to repository default branch)
        reviewer: The username of the reviewer to assign
        pr_title: Custom title for the pull request (optional)
        base_domain: The base domain for the git server (defaults to "github.com")
        git_user_name: Git user name for commits
        git_user_email: Git user email for commits

    """
    # Validate inputs
    _validate_pr_type(pr_type)

    # Set default base domain
    if base_domain is None:
        base_domain = _get_default_base_domain(platform)

    # Create issue handler
    handler = _create_issue_handler(issue, token, username, platform, base_domain)

    # Setup branch
    base_branch_name = f"Forge-fix-issue-{issue.number}"
    branch_name = handler.get_branch_name(base_branch_name=base_branch_name)

    logger.info("Getting base branch...")
    base_branch = _determine_base_branch(handler, target_branch)
    logger.info("Base branch: %s", base_branch)

    # Create and checkout branch
    logger.info("Creating new branch...")
    _create_and_checkout_branch(patch_dir, branch_name)

    # Push changes
    logger.info("Pushing changes...")
    _push_changes(handler, patch_dir, branch_name, fork_owner, issue)

    # Build PR content
    final_pr_title, pr_body = _build_pr_content(issue, pr_title, additional_message)

    # Determine head branch
    if fork_owner and platform == ProviderType.GITHUB:
        head_branch = f"{fork_owner}:{branch_name}"
    else:
        head_branch = branch_name

    # Create pull request or get compare URL
    if pr_type == "branch":
        url = handler.get_compare_url(branch_name)
    else:
        url = _create_pull_request(
            handler,
            platform,
            final_pr_title,
            pr_body,
            head_branch,
            base_branch,
            pr_type,
            reviewer,
        )

    logger.info(
        "%s created: %s\n\n--- Title: %s\n\n--- Body:\n%s",
        pr_type,
        url,
        final_pr_title,
        pr_body,
    )
    return url


def _create_issue_handler_with_llm(
    issue: Issue,
    token: str,
    username: str | None,
    platform: ProviderType,
    llm_config: LLMConfig,
    base_domain: str,
) -> ServiceContextIssue:
    """Create appropriate issue handler with LLM config based on platform."""
    if platform == ProviderType.GITHUB:
        return ServiceContextIssue(
            GithubIssueHandler(issue.owner, issue.repo, token, username, base_domain),
            llm_config,
        )
    msg = f"Unsupported platform: {platform}"
    raise ValueError(msg)


def _push_changes_to_remote(
    patch_dir: str, handler: ServiceContextIssue, issue: Issue
) -> None:
    """Push changes to remote repository."""
    head_branch = issue.head_branch or ""
    if not head_branch:
        msg = "Issue head branch is not specified"
        raise ValueError(msg)
    push_command = [
        "git",
        "-C",
        patch_dir,
        "push",
        f"{handler.get_authorize_url()}{issue.owner}/{issue.repo}.git",
        head_branch,
    ]
    result = subprocess.run(
        push_command, check=False, shell=False, capture_output=True, text=True
    )
    if result.returncode != 0:
        logger.error("Error pushing changes: %s", result.stderr)
        msg = "Failed to push changes to the remote repository"
        raise RuntimeError(msg)


def _build_pr_comment_from_explanations(
    explanations: list, llm_config: LLMConfig | None
) -> str:
    """Build PR comment from explanation list, optionally using LLM to summarize."""
    comment_message = "Forge made the following changes to resolve the issues:\n\n"
    for explanation in explanations:
        comment_message += f"- {explanation}\n"

    if llm_config is not None:
        llm = LLM(llm_config, service_id="resolver")
        with open(
            os.path.join(
                os.path.dirname(__file__), "prompts/resolve/pr-changes-summary.jinja"
            ),
            encoding="utf-8",
        ) as f:
            template = jinja2.Template(f.read())
        prompt = template.render(comment_message=comment_message)
        response = llm.completion(messages=[{"role": "user", "content": prompt}])
        comment_message = response.choices[0].message.content.strip()

    return comment_message


def _generate_comment_message(
    comment_message: str | None,
    additional_message: str | None,
    llm_config: LLMConfig,
) -> str | None:
    """Generate comment message from additional message if main message not provided."""
    if comment_message or not additional_message:
        return comment_message

    try:
        if explanations := json.loads(additional_message):
            return _build_pr_comment_from_explanations(explanations, llm_config)
    except (json.JSONDecodeError, TypeError):
        return f"A new Forge update is available, but failed to parse or summarize the changes:\n{additional_message}"

    return comment_message


def _reply_to_threads(
    handler: ServiceContextIssue, issue: Issue, additional_message: str
) -> None:
    """Reply to individual threads with explanations."""
    try:
        explanations = json.loads(additional_message)
        thread_ids: list[str] = list(issue.thread_ids or [])
        for count, reply_comment in enumerate(explanations):
            if count >= len(thread_ids):
                break
            comment_id = thread_ids[count]
            handler.reply_to_comment(issue.number, comment_id, reply_comment)
    except (json.JSONDecodeError, TypeError):
        msg = f"Error occurred when replying to threads; success explanations {additional_message}"
        handler.send_comment_msg(issue.number, msg)


def update_existing_pull_request(
    issue: Issue,
    token: str,
    username: str | None,
    platform: ProviderType,
    patch_dir: str,
    llm_config: LLMConfig,
    comment_message: str | None = None,
    additional_message: str | None = None,
    base_domain: str | None = None,
) -> str:
    """Update an existing pull request with the new patches."""
    base_domain = base_domain or "github.com"

    # Create handler and push changes
    handler = _create_issue_handler_with_llm(
        issue, token, username, platform, llm_config, base_domain
    )
    _push_changes_to_remote(patch_dir, handler, issue)

    # Get PR URL
    pr_url = handler.get_pull_url(issue.number)
    logger.info("Updated pull request %s with new patches.", pr_url)

    if comment_message := _generate_comment_message(
        comment_message,
        additional_message,
        llm_config,
    ):
        handler.send_comment_msg(issue.number, comment_message)

    # Reply to individual threads
    if additional_message and issue.thread_ids:
        _reply_to_threads(handler, issue, additional_message)

    return pr_url


def process_single_issue(
    output_dir: str,
    resolver_output: ResolverOutput,
    token: str,
    username: str,
    platform: ProviderType,
    pr_type: str,
    llm_config: LLMConfig,
    fork_owner: str | None,
    send_on_failure: bool,
    target_branch: str | None = None,
    reviewer: str | None = None,
    pr_title: str | None = None,
    base_domain: str | None = None,
    git_user_name: str = "forge",
    git_user_email: str = "Forge@forge.dev",
) -> None:
    """Process a single issue and send a pull request if applicable."""
    if base_domain is None:
        base_domain = "github.com"
    if not resolver_output.success and (not send_on_failure):
        logger.info(
            "Issue %s was not successfully resolved. Skipping PR creation.",
            resolver_output.issue.number,
        )
        return
    issue_type = resolver_output.issue_type
    if issue_type == "issue":
        patched_repo_dir = initialize_repo(
            output_dir,
            resolver_output.issue.number,
            issue_type,
            resolver_output.base_commit,
        )
    elif issue_type == "pr":
        patched_repo_dir = initialize_repo(
            output_dir,
            resolver_output.issue.number,
            issue_type,
            resolver_output.issue.head_branch,
        )
    else:
        msg = f"Invalid issue type: {issue_type}"
        raise ValueError(msg)
    apply_patch(patched_repo_dir, resolver_output.git_patch)
    make_commit(
        patched_repo_dir,
        resolver_output.issue,
        issue_type,
        git_user_name,
        git_user_email,
    )
    if issue_type == "pr":
        update_existing_pull_request(
            issue=resolver_output.issue,
            token=token,
            username=username,
            platform=platform,
            patch_dir=patched_repo_dir,
            additional_message=resolver_output.result_explanation,
            llm_config=llm_config,
            base_domain=base_domain,
        )
    else:
        send_pull_request(
            issue=resolver_output.issue,
            token=token,
            username=username,
            platform=platform,
            patch_dir=patched_repo_dir,
            pr_type=pr_type,
            fork_owner=fork_owner,
            additional_message=resolver_output.result_explanation,
            target_branch=target_branch,
            reviewer=reviewer,
            pr_title=pr_title,
            base_domain=base_domain,
            git_user_name=git_user_name,
            git_user_email=git_user_email,
        )


def main() -> None:
    """Main entry point for sending pull requests."""
    parser = _create_argument_parser()
    my_args = parser.parse_args()

    config = _build_config_from_args(my_args)
    _validate_config(config)

    process_single_issue(
        config["output_dir"],
        config["resolver_output"],
        config["token"],
        config["username"],
        config["platform"],
        config["pr_type"],
        config["llm_config"],
        config["fork_owner"],
        config["send_on_failure"],
        config["target_branch"],
        config["reviewer"],
        config["pr_title"],
        config["base_domain"],
        config["git_user_name"],
        config["git_user_email"],
    )


def _create_argument_parser() -> argparse.ArgumentParser:
    """Create and configure argument parser.

    Returns:
        Configured ArgumentParser

    """
    parser = argparse.ArgumentParser(
        description="Send a pull request to GitHub."
    )
    parser.add_argument(
        "--selected-repo",
        type=str,
        default=None,
        help="repository to send pull request in form of `owner/repo`.",
    )
    parser.add_argument(
        "--token", type=str, default=None, help="token to access the repository."
    )
    parser.add_argument(
        "--username", type=str, default=None, help="username to access the repository."
    )
    parser.add_argument(
        "--output-dir",
        type=str,
        default="output",
        help="Output directory to write the results.",
    )
    parser.add_argument(
        "--pr-type",
        type=str,
        default="draft",
        choices=["branch", "draft", "ready"],
        help="Type of the pull request to send [branch, draft, ready]",
    )
    parser.add_argument(
        "--issue-number",
        type=str,
        required=True,
        help="Issue number to send the pull request for, or 'all_successful' to process all successful issues.",
    )
    parser.add_argument(
        "--fork-owner",
        type=str,
        default=None,
        help="Owner of the fork to push changes to (if different from the original repo owner).",
    )
    parser.add_argument(
        "--send-on-failure",
        action="store_true",
        help="Send a pull request even if the issue was not successfully resolved.",
    )
    parser.add_argument(
        "--llm-model",
        type=str,
        default=None,
        help="LLM model to use for summarizing changes.",
    )
    parser.add_argument(
        "--llm-api-key", type=str, default=None, help="API key for the LLM model."
    )
    parser.add_argument(
        "--llm-base-url", type=str, default=None, help="Base URL for the LLM model."
    )
    parser.add_argument(
        "--target-branch",
        type=str,
        default=None,
        help="Target branch to create the pull request against (defaults to repository default branch)",
    )
    parser.add_argument(
        "--reviewer",
        type=str,
        help="GitHub username of the person to request review from",
        default=None,
    )
    parser.add_argument(
        "--pr-title", type=str, help="Custom title for the pull request", default=None
    )
    parser.add_argument(
        "--base-domain",
        type=str,
        default=None,
        help='Base domain for the git server (defaults to "github.com")',
    )
    parser.add_argument(
        "--git-user-name", type=str, default="forge", help="Git user name for commits"
    )
    parser.add_argument(
        "--git-user-email",
        type=str,
        default="Forge@forge.dev",
        help="Git user email for commits",
    )
    return parser


def _build_config_from_args(args) -> dict:
    """Build configuration dictionary from parsed arguments.

    Args:
        args: Parsed command line arguments

    Returns:
        Configuration dictionary

    Raises:
        ValueError: If required values missing

    """
    token = _resolve_token(args)
    username = _resolve_username(args)
    platform = call_async_from_sync(
        identify_token, GENERAL_TIMEOUT, token, args.base_domain
    )
    llm_config = _build_llm_config(args)
    resolver_output = _load_resolver_output(args)

    return {
        "output_dir": args.output_dir,
        "resolver_output": resolver_output,
        "token": token,
        "username": username,
        "platform": platform,
        "pr_type": args.pr_type,
        "llm_config": llm_config,
        "fork_owner": args.fork_owner,
        "send_on_failure": args.send_on_failure,
        "target_branch": args.target_branch,
        "reviewer": args.reviewer,
        "pr_title": args.pr_title,
        "base_domain": args.base_domain,
        "git_user_name": args.git_user_name,
        "git_user_email": args.git_user_email,
    }


def _resolve_token(args) -> str:
    token = args.token or os.getenv("GITHUB_TOKEN")
    if not token:
        msg = "token is not set, set via --token or GITHUB_TOKEN environment variable."
        raise ValueError(msg)
    return token


def _resolve_username(args) -> str:
    username = args.username or os.getenv("GIT_USERNAME")
    if not username:
        msg = "username is required."
        raise ValueError(msg)
    return username


def _build_llm_config(args) -> LLMConfig:
    api_key = args.llm_api_key or os.environ.get("LLM_API_KEY")
    model = args.llm_model or os.environ.get("LLM_MODEL")
    if not model:
        msg = "LLM model must be provided via --llm-model or LLM_MODEL environment variable."
        raise ValueError(msg)
    return LLMConfig(
        model=model,
        api_key=SecretStr(api_key) if api_key else None,
        base_url=args.llm_base_url or os.environ.get("LLM_BASE_URL"),
    )


def _load_resolver_output(args):
    output_path = os.path.join(args.output_dir, "output.jsonl")
    issue_number = _parse_issue_number(args.issue_number)
    return load_single_resolver_output(output_path, issue_number)


def _parse_issue_number(raw_issue: str | int) -> int:
    try:
        return int(raw_issue)
    except (TypeError, ValueError) as exc:
        msg = "issue-number must be an integer"
        raise ValueError(msg) from exc


def _validate_config(config: dict) -> None:
    """Validate configuration values.

    Args:
        config: Configuration dictionary

    Raises:
        ValueError: If validation fails

    """
    if not os.path.exists(config["output_dir"]):
        msg = f"Output directory {config['output_dir']} does not exist."
        raise ValueError(msg)


if __name__ == "__main__":
    main()

