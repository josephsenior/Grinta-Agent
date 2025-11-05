import os
import subprocess
import tempfile
from unittest.mock import MagicMock, call, patch
from urllib.parse import quote
import pytest
from openhands.core.config import LLMConfig
from openhands.integrations.service_types import ProviderType
from openhands.resolver.interfaces.gitlab import GitlabIssueHandler
from openhands.resolver.interfaces.issue import ReviewThread
from openhands.resolver.resolver_output import Issue, ResolverOutput
from openhands.resolver.send_pull_request import (
    apply_patch,
    initialize_repo,
    load_single_resolver_output,
    main,
    make_commit,
    process_single_issue,
    send_pull_request,
    update_existing_pull_request,
)


@pytest.fixture
def mock_output_dir():
    with tempfile.TemporaryDirectory() as temp_dir:
        repo_path = os.path.join(temp_dir, "repo")
        os.makedirs(repo_path)
        subprocess.run(["git", "init", repo_path], check=True)
        readme_path = os.path.join(repo_path, "README.md")
        with open(readme_path, "w", encoding='utf-8') as f:
            f.write("hello world")
        subprocess.run(["git", "-C", repo_path, "add", "README.md"], check=True)
        subprocess.run(["git", "-C", repo_path, "commit", "-m", "Initial commit"], check=True)
        yield temp_dir


@pytest.fixture
def mock_issue():
    return Issue(number=42, title="Test Issue", owner="test-owner", repo="test-repo", body="Test body")


@pytest.fixture
def mock_llm_config():
    return LLMConfig()


def test_load_single_resolver_output():
    mock_output_jsonl = "tests/unit/resolver/mock_output/output.jsonl"
    resolver_output = load_single_resolver_output(mock_output_jsonl, 5)
    assert isinstance(resolver_output, ResolverOutput)
    assert resolver_output.issue.number == 5
    assert resolver_output.issue.title == "Add MIT license"
    assert resolver_output.issue.owner == "neubig"
    assert resolver_output.issue.repo == "pr-viewer"
    with pytest.raises(ValueError):
        load_single_resolver_output(mock_output_jsonl, 999)


def test_apply_patch(mock_output_dir):
    sample_file = os.path.join(mock_output_dir, "sample.txt")
    with open(sample_file, "w", encoding='utf-8') as f:
        f.write("Original content")
    patch_content = "\ndiff --git a/sample.txt b/sample.txt\nindex 9daeafb..b02def2 100644\n--- a/sample.txt\n+++ b/sample.txt\n@@ -1 +1,2 @@\n-Original content\n+Updated content\n+New line\n"
    apply_patch(mock_output_dir, patch_content)
    with open(sample_file, "r", encoding='utf-8') as f:
        updated_content = f.read()
    assert updated_content.strip() == "Updated content\nNew line".strip()


def test_apply_patch_preserves_line_endings(mock_output_dir):
    unix_file = os.path.join(mock_output_dir, "unix_style.txt")
    dos_file = os.path.join(mock_output_dir, "dos_style.txt")
    with open(unix_file, "w", newline="\n", encoding='utf-8') as f:
        f.write("Line 1\nLine 2\nLine 3")
    with open(dos_file, "w", newline="\r\n", encoding='utf-8') as f:
        f.write("Line 1\r\nLine 2\r\nLine 3")
    unix_patch = "\ndiff --git a/unix_style.txt b/unix_style.txt\nindex 9daeafb..b02def2 100644\n--- a/unix_style.txt\n+++ b/unix_style.txt\n@@ -1,3 +1,3 @@\n Line 1\n-Line 2\n+Updated Line 2\n Line 3\n"
    dos_patch = "\ndiff --git a/dos_style.txt b/dos_style.txt\nindex 9daeafb..b02def2 100644\n--- a/dos_style.txt\n+++ b/dos_style.txt\n@@ -1,3 +1,3 @@\n Line 1\n-Line 2\n+Updated Line 2\n Line 3\n"
    apply_patch(mock_output_dir, unix_patch)
    apply_patch(mock_output_dir, dos_patch)
    with open(unix_file, "rb") as f:
        unix_content = f.read()
    with open(dos_file, "rb") as f:
        dos_content = f.read()
    assert b"\r\n" not in unix_content, "Unix-style line endings were changed to DOS-style"
    assert b"\r\n" in dos_content, "DOS-style line endings were changed to Unix-style"
    assert unix_content.decode("utf-8").split("\n")[1] == "Updated Line 2"
    assert dos_content.decode("utf-8").split("\r\n")[1] == "Updated Line 2"


def test_apply_patch_create_new_file(mock_output_dir):
    patch_content = "\ndiff --git a/new_file.txt b/new_file.txt\nnew file mode 100644\nindex 0000000..3b18e51\n--- /dev/null\n+++ b/new_file.txt\n@@ -0,0 +1 @@\n+hello world\n"
    apply_patch(mock_output_dir, patch_content)
    new_file_path = os.path.join(mock_output_dir, "new_file.txt")
    assert os.path.exists(new_file_path), "New file was not created"
    with open(new_file_path, "r", encoding='utf-8') as f:
        content = f.read().strip()
    assert content == "hello world", "File content is incorrect"


def test_apply_patch_rename_file(mock_output_dir):
    old_file = os.path.join(mock_output_dir, "old_name.txt")
    with open(old_file, "w", encoding='utf-8') as f:
        f.write("This file will be renamed")
    patch_content = "diff --git a/old_name.txt b/new_name.txt\nsimilarity index 100%\nrename from old_name.txt\nrename to new_name.txt"
    apply_patch(mock_output_dir, patch_content)
    new_file = os.path.join(mock_output_dir, "new_name.txt")
    assert not os.path.exists(old_file), "Old file still exists"
    assert os.path.exists(new_file), "New file was not created"
    with open(new_file, "r", encoding='utf-8') as f:
        content = f.read()
    assert content == "This file will be renamed"


def test_apply_patch_delete_file(mock_output_dir):
    sample_file = os.path.join(mock_output_dir, "to_be_deleted.txt")
    with open(sample_file, "w", encoding='utf-8') as f:
        f.write("This file will be deleted")
    patch_content = "\ndiff --git a/to_be_deleted.txt b/to_be_deleted.txt\ndeleted file mode 100644\nindex 9daeafb..0000000\n--- a/to_be_deleted.txt\n+++ /dev/null\n@@ -1 +0,0 @@\n-This file will be deleted\n"
    apply_patch(mock_output_dir, patch_content)
    assert not os.path.exists(sample_file), "File was not deleted"


def test_initialize_repo(mock_output_dir):
    issue_type = "issue"
    ISSUE_NUMBER = 3
    initialize_repo(mock_output_dir, ISSUE_NUMBER, issue_type)
    patches_dir = os.path.join(mock_output_dir, "patches", f"issue_{ISSUE_NUMBER}")
    assert os.path.exists(os.path.join(patches_dir, "README.md"))
    with open(os.path.join(patches_dir, "README.md"), "r") as f:
        assert f.read() == "hello world"


@patch("openhands.resolver.interfaces.gitlab.GitlabIssueHandler.reply_to_comment")
@patch("httpx.post")
@patch("subprocess.run")
@patch("openhands.resolver.send_pull_request.LLM")
def test_update_existing_pull_request(mock_llm_class, mock_subprocess_run, mock_requests_post, mock_reply_to_comment):
    issue = Issue(
        owner="test-owner",
        repo="test-repo",
        number=1,
        title="Test PR",
        body="This is a test PR",
        thread_ids=["comment1", "comment2"],
        head_branch="test-branch",
    )
    token = "test-token"
    username = "test-user"
    patch_dir = "/path/to/patch"
    additional_message = '["Fixed bug in function A", "Updated documentation for B"]'
    mock_subprocess_run.return_value = MagicMock(returncode=0)
    mock_requests_post.return_value.status_code = 201
    mock_llm_instance = MagicMock()
    mock_completion_response = MagicMock()
    mock_completion_response.choices = [MagicMock(message=MagicMock(content="This is an issue resolution."))]
    mock_llm_instance.completion.return_value = mock_completion_response
    mock_llm_class.return_value = mock_llm_instance
    llm_config = LLMConfig()
    result = update_existing_pull_request(
        issue,
        token,
        username,
        ProviderType.GITLAB,
        patch_dir,
        llm_config,
        comment_message=None,
        additional_message=additional_message,
    )
    push_command = f"git -C {patch_dir} push https://{username}:{token}@gitlab.com/{issue.owner}/{issue.repo}.git {issue.head_branch}"
    mock_subprocess_run.assert_called_once_with(push_command, shell=True, capture_output=True, text=True)  # nosec B604 - Safe: test assertion, not executing
    comment_url = f"https://gitlab.com/api/v4/projects/{quote(f'{issue.owner}/{issue.repo}', safe='')}/issues/{
        issue.number}/notes"
    expected_comment = "This is an issue resolution."
    mock_requests_post.assert_called_once_with(
        comment_url,
        headers={"Authorization": f"Bearer {token}", "Accept": "application/json"},
        json={"body": expected_comment},
    )
    mock_reply_to_comment.assert_has_calls(
        [
            call(issue.number, "comment1", "Fixed bug in function A"),
            call(issue.number, "comment2", "Updated documentation for B"),
        ]
    )
    assert result == f"https://gitlab.com/{issue.owner}/{issue.repo}/-/merge_requests/{issue.number}"


@pytest.mark.parametrize(
    "pr_type,target_branch,pr_title",
    [
        ("branch", None, None),
        ("draft", None, None),
        ("ready", None, None),
        ("branch", "feature", None),
        ("draft", "develop", None),
        ("ready", "staging", None),
        ("ready", None, "Custom PR Title"),
        ("draft", "develop", "Another Custom Title"),
    ],
)
@patch("subprocess.run")
@patch("httpx.post")
@patch("httpx.get")
def test_send_pull_request(
    mock_get, mock_post, mock_run, mock_issue, mock_llm_config, mock_output_dir, pr_type, target_branch, pr_title
):
    repo_path = os.path.join(mock_output_dir, "repo")
    if target_branch:
        mock_get.side_effect = [
            MagicMock(status_code=404),
            MagicMock(status_code=200),
            MagicMock(json=lambda: {"default_branch": "main"}),
        ]
    else:
        mock_get.side_effect = [
            MagicMock(status_code=404),
            MagicMock(json=lambda: {"default_branch": "main"}),
            MagicMock(json=lambda: {"default_branch": "main"}),
        ]
    mock_post.return_value.json.return_value = {"web_url": "https://gitlab.com/test-owner/test-repo/-/merge_requests/1"}
    mock_run.side_effect = [MagicMock(returncode=0), MagicMock(returncode=0)]
    result = send_pull_request(
        issue=mock_issue,
        token="test-token",
        username="test-user",
        platform=ProviderType.GITLAB,
        patch_dir=repo_path,
        pr_type=pr_type,
        target_branch=target_branch,
        pr_title=pr_title,
    )
    expected_get_calls = 3 if pr_type == "branch" else 2
    assert mock_get.call_count == expected_get_calls
    assert mock_run.call_count == 2
    checkout_call, push_call = mock_run.call_args_list
    assert checkout_call == call(
        ["git", "-C", repo_path, "checkout", "-b", "openhands-fix-issue-42"], capture_output=True, text=True
    )
    assert push_call == call(
        [
            "git",
            "-C",
            repo_path,
            "push",
            "https://test-user:test-token@gitlab.com/test-owner/test-repo.git",
            "openhands-fix-issue-42",
        ],
        capture_output=True,
        text=True,
    )
    if pr_type == "branch":
        assert result == "https://gitlab.com/test-owner/test-repo/-/compare/main...openhands-fix-issue-42"
        mock_post.assert_not_called()
    else:
        assert result == "https://gitlab.com/test-owner/test-repo/-/merge_requests/1"
        mock_post.assert_called_once()
        post_data = mock_post.call_args[1]["json"]
        expected_title = pr_title or "Fix issue #42: Test Issue"
        assert post_data["title"] == expected_title
        assert post_data["description"].startswith("This pull request fixes #42.")
        assert post_data["source_branch"] == "openhands-fix-issue-42"
        assert post_data["target_branch"] == (target_branch or "main")
        assert post_data["draft"] == (pr_type == "draft")


@patch("subprocess.run")
@patch("httpx.post")
@patch("httpx.put")
@patch("httpx.get")
def test_send_pull_request_with_reviewer(
    mock_get, mock_put, mock_post, mock_run, mock_issue, mock_output_dir, mock_llm_config
):
    repo_path = os.path.join(mock_output_dir, "repo")
    reviewer = "test-reviewer"
    mock_get.side_effect = [
        MagicMock(status_code=404),
        MagicMock(json=lambda: {"default_branch": "main"}),
        MagicMock(json=lambda: [{"id": 123}]),
    ]
    mock_post.side_effect = [
        MagicMock(
            status_code=200,
            json=lambda: {"web_url": "https://gitlab.com/test-owner/test-repo/-/merge_requests/1", "iid": 1},
        )
    ]
    mock_put.side_effect = [MagicMock(status_code=200)]
    mock_run.side_effect = [MagicMock(returncode=0), MagicMock(returncode=0)]
    result = send_pull_request(
        issue=mock_issue,
        token="test-token",
        username="test-user",
        platform=ProviderType.GITLAB,
        patch_dir=repo_path,
        pr_type="ready",
        reviewer=reviewer,
    )
    assert mock_get.call_count == 3
    assert mock_post.call_count == 1
    assert mock_put.call_count == 1
    pr_create_call = mock_post.call_args_list[0]
    assert pr_create_call[1]["json"]["title"] == "Fix issue #42: Test Issue"
    reviewer_request_call = mock_put.call_args_list[0]
    assert reviewer_request_call[0][0] == "https://gitlab.com/api/v4/projects/test-owner%2Ftest-repo/merge_requests/1"
    assert reviewer_request_call[1]["json"] == {"reviewer_ids": [123]}
    assert result == "https://gitlab.com/test-owner/test-repo/-/merge_requests/1"


@patch("httpx.get")
def test_send_pull_request_invalid_target_branch(mock_get, mock_issue, mock_output_dir, mock_llm_config):
    """Test that an error is raised when specifying a non-existent target branch."""
    repo_path = os.path.join(mock_output_dir, "repo")
    mock_get.side_effect = [MagicMock(status_code=404), MagicMock(status_code=404)]
    with pytest.raises(ValueError, match="Target branch nonexistent-branch does not exist"):
        send_pull_request(
            issue=mock_issue,
            token="test-token",
            username="test-user",
            platform=ProviderType.GITLAB,
            patch_dir=repo_path,
            pr_type="ready",
            target_branch="nonexistent-branch",
        )
    assert mock_get.call_count == 2


@patch("subprocess.run")
@patch("httpx.post")
@patch("httpx.get")
def test_send_pull_request_git_push_failure(
    mock_get, mock_post, mock_run, mock_issue, mock_output_dir, mock_llm_config
):
    repo_path = os.path.join(mock_output_dir, "repo")
    mock_get.return_value = MagicMock(json=lambda: {"default_branch": "main"})
    mock_run.side_effect = [MagicMock(returncode=0), MagicMock(returncode=1, stderr="Error: failed to push some refs")]
    with pytest.raises(RuntimeError, match="Failed to push changes to the remote repository"):
        send_pull_request(
            issue=mock_issue,
            token="test-token",
            username="test-user",
            platform=ProviderType.GITLAB,
            patch_dir=repo_path,
            pr_type="ready",
        )
    assert mock_run.call_count == 2
    checkout_call = mock_run.call_args_list[0]
    assert checkout_call[0][0] == ["git", "-C", repo_path, "checkout", "-b", "openhands-fix-issue-42"]
    push_call = mock_run.call_args_list[1]
    assert push_call[0][0] == [
        "git",
        "-C",
        repo_path,
        "push",
        "https://test-user:test-token@gitlab.com/test-owner/test-repo.git",
        "openhands-fix-issue-42",
    ]
    mock_post.assert_not_called()


@patch("subprocess.run")
@patch("httpx.post")
@patch("httpx.get")
def test_send_pull_request_permission_error(
    mock_get, mock_post, mock_run, mock_issue, mock_output_dir, mock_llm_config
):
    repo_path = os.path.join(mock_output_dir, "repo")
    mock_get.return_value = MagicMock(json=lambda: {"default_branch": "main"})
    mock_post.return_value.status_code = 403
    mock_run.side_effect = [MagicMock(returncode=0), MagicMock(returncode=0)]
    with pytest.raises(RuntimeError, match="Failed to create pull request due to missing permissions."):
        send_pull_request(
            issue=mock_issue,
            token="test-token",
            username="test-user",
            platform=ProviderType.GITLAB,
            patch_dir=repo_path,
            pr_type="ready",
        )
    assert mock_run.call_count == 2
    mock_post.assert_called_once()


@patch("httpx.post")
@patch("httpx.get")
def test_reply_to_comment(mock_get, mock_post, mock_issue):
    token = "test_token"
    comment_id = "GID/test_comment_id"
    reply = "This is a test reply."
    handler = GitlabIssueHandler(owner="test-owner", repo="test-repo", token=token, username="test-user")
    mock_get.return_value = MagicMock(json=lambda: {"notes": [{"id": 123}]})
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "id": 123,
        "body": "Openhands fix success summary\n\n\nThis is a test reply.",
        "createdAt": "2024-10-01T12:34:56Z",
    }
    mock_post.return_value = mock_response
    handler.reply_to_comment(mock_issue.number, comment_id, reply)
    data = {"body": "Openhands fix success summary\n\n\nThis is a test reply.", "note_id": 123}
    mock_post.assert_called_once_with(
        f"https://gitlab.com/api/v4/projects/{quote(f'{mock_issue.owner}/{mock_issue.repo}', safe='')}/merge_requests/{
            mock_issue.number}/discussions/{comment_id.split('/')[-1]}/notes",
        headers={"Authorization": f"Bearer {token}", "Accept": "application/json"},
        json=data,
    )
    mock_response.raise_for_status.assert_called_once()


@patch("openhands.resolver.send_pull_request.initialize_repo")
@patch("openhands.resolver.send_pull_request.apply_patch")
@patch("openhands.resolver.send_pull_request.update_existing_pull_request")
@patch("openhands.resolver.send_pull_request.make_commit")
def test_process_single_pr_update(
    mock_make_commit,
    mock_update_existing_pull_request,
    mock_apply_patch,
    mock_initialize_repo,
    mock_output_dir,
    mock_llm_config,
):
    token = "test_token"
    username = "test_user"
    pr_type = "draft"
    resolver_output = ResolverOutput(
        issue=Issue(
            owner="test-owner",
            repo="test-repo",
            number=1,
            title="Issue 1",
            body="Body 1",
            closing_issues=[],
            review_threads=[ReviewThread(comment="review comment for feedback", files=[])],
            thread_ids=["1"],
            head_branch="branch 1",
        ),
        issue_type="pr",
        instruction="Test instruction 1",
        base_commit="def456",
        git_patch="Test patch 1",
        history=[],
        metrics={},
        success=True,
        comment_success=None,
        result_explanation="[Test success 1]",
        error=None,
    )
    mock_update_existing_pull_request.return_value = "https://gitlab.com/test-owner/test-repo/-/merge_requests/1"
    mock_initialize_repo.return_value = f"{mock_output_dir}/patches/pr_1"
    process_single_issue(
        mock_output_dir,
        resolver_output,
        token,
        username,
        ProviderType.GITLAB,
        pr_type,
        mock_llm_config,
        None,
        False,
        None,
        None,
        None,
        None,
        "openhands",
        "openhands@all-hands.dev",
    )
    mock_initialize_repo.assert_called_once_with(mock_output_dir, 1, "pr", "branch 1")
    mock_apply_patch.assert_called_once_with(f"{mock_output_dir}/patches/pr_1", resolver_output.git_patch)
    mock_make_commit.assert_called_once_with(
        f"{mock_output_dir}/patches/pr_1", resolver_output.issue, "pr", "openhands", "openhands@all-hands.dev"
    )
    mock_update_existing_pull_request.assert_called_once_with(
        issue=resolver_output.issue,
        token=token,
        username=username,
        platform=ProviderType.GITLAB,
        patch_dir=f"{mock_output_dir}/patches/pr_1",
        additional_message="[Test success 1]",
        llm_config=mock_llm_config,
        base_domain="gitlab.com",
    )


@patch("openhands.resolver.send_pull_request.initialize_repo")
@patch("openhands.resolver.send_pull_request.apply_patch")
@patch("openhands.resolver.send_pull_request.send_pull_request")
@patch("openhands.resolver.send_pull_request.make_commit")
def test_process_single_issue(
    mock_make_commit, mock_send_pull_request, mock_apply_patch, mock_initialize_repo, mock_output_dir, mock_llm_config
):
    token = "test_token"
    username = "test_user"
    pr_type = "draft"
    platform = ProviderType.GITLAB
    resolver_output = ResolverOutput(
        issue=Issue(owner="test-owner", repo="test-repo", number=1, title="Issue 1", body="Body 1"),
        issue_type="issue",
        instruction="Test instruction 1",
        base_commit="def456",
        git_patch="Test patch 1",
        history=[],
        metrics={},
        success=True,
        comment_success=None,
        result_explanation="Test success 1",
        error=None,
    )
    mock_send_pull_request.return_value = "https://gitlab.com/test-owner/test-repo/-/merge_requests/1"
    mock_initialize_repo.return_value = f"{mock_output_dir}/patches/issue_1"
    process_single_issue(
        mock_output_dir,
        resolver_output,
        token,
        username,
        platform,
        pr_type,
        mock_llm_config,
        None,
        False,
        None,
        None,
        None,
        None,
        "openhands",
        "openhands@all-hands.dev",
    )
    mock_initialize_repo.assert_called_once_with(mock_output_dir, 1, "issue", "def456")
    mock_apply_patch.assert_called_once_with(f"{mock_output_dir}/patches/issue_1", resolver_output.git_patch)
    mock_make_commit.assert_called_once_with(
        f"{mock_output_dir}/patches/issue_1", resolver_output.issue, "issue", "openhands", "openhands@all-hands.dev"
    )
    mock_send_pull_request.assert_called_once_with(
        issue=resolver_output.issue,
        token=token,
        username=username,
        platform=platform,
        patch_dir=f"{mock_output_dir}/patches/issue_1",
        pr_type=pr_type,
        fork_owner=None,
        additional_message=resolver_output.result_explanation,
        target_branch=None,
        reviewer=None,
        pr_title=None,
        base_domain="gitlab.com",
        git_user_name="openhands",
        git_user_email="openhands@all-hands.dev",
    )


@patch("openhands.resolver.send_pull_request.initialize_repo")
@patch("openhands.resolver.send_pull_request.apply_patch")
@patch("openhands.resolver.send_pull_request.send_pull_request")
@patch("openhands.resolver.send_pull_request.make_commit")
def test_process_single_issue_unsuccessful(
    mock_make_commit, mock_send_pull_request, mock_apply_patch, mock_initialize_repo, mock_output_dir, mock_llm_config
):
    token = "test_token"
    username = "test_user"
    pr_type = "draft"
    resolver_output = ResolverOutput(
        issue=Issue(owner="test-owner", repo="test-repo", number=1, title="Issue 1", body="Body 1"),
        issue_type="issue",
        instruction="Test instruction 1",
        base_commit="def456",
        git_patch="Test patch 1",
        history=[],
        metrics={},
        success=False,
        comment_success=None,
        result_explanation="",
        error="Test error",
    )
    process_single_issue(
        mock_output_dir,
        resolver_output,
        token,
        username,
        ProviderType.GITLAB,
        pr_type,
        mock_llm_config,
        None,
        False,
        None,
        None,
        None,
        None,
        "openhands",
        "openhands@all-hands.dev",
    )
    mock_initialize_repo.assert_not_called()
    mock_apply_patch.assert_not_called()
    mock_make_commit.assert_not_called()
    mock_send_pull_request.assert_not_called()


@patch("httpx.get")
@patch("subprocess.run")
def test_send_pull_request_branch_naming(mock_run, mock_get, mock_issue, mock_output_dir, mock_llm_config):
    repo_path = os.path.join(mock_output_dir, "repo")
    mock_get.side_effect = [
        MagicMock(status_code=200),
        MagicMock(status_code=200),
        MagicMock(status_code=404),
        MagicMock(json=lambda: {"default_branch": "main"}),
        MagicMock(json=lambda: {"default_branch": "main"}),
    ]
    mock_run.side_effect = [MagicMock(returncode=0), MagicMock(returncode=0)]
    result = send_pull_request(
        issue=mock_issue,
        token="test-token",
        username="test-user",
        platform=ProviderType.GITLAB,
        patch_dir=repo_path,
        pr_type="branch",
    )
    assert mock_get.call_count == 5
    assert mock_run.call_count == 2
    checkout_call, push_call = mock_run.call_args_list
    assert checkout_call == call(
        ["git", "-C", repo_path, "checkout", "-b", "openhands-fix-issue-42-try3"], capture_output=True, text=True
    )
    assert push_call == call(
        [
            "git",
            "-C",
            repo_path,
            "push",
            "https://test-user:test-token@gitlab.com/test-owner/test-repo.git",
            "openhands-fix-issue-42-try3",
        ],
        capture_output=True,
        text=True,
    )
    assert result == "https://gitlab.com/test-owner/test-repo/-/compare/main...openhands-fix-issue-42-try3"


@patch("openhands.resolver.send_pull_request.argparse.ArgumentParser")
@patch("openhands.resolver.send_pull_request.process_single_issue")
@patch("openhands.resolver.send_pull_request.load_single_resolver_output")
@patch("openhands.resolver.send_pull_request.identify_token")
@patch("os.path.exists")
@patch("os.getenv")
def test_main(
    mock_getenv,
    mock_path_exists,
    mock_identify_token,
    mock_load_single_resolver_output,
    mock_process_single_issue,
    mock_parser,
):
    """Test main function with valid GitLab inputs."""
    # Setup test data
    mock_args = _create_gitlab_mock_args()
    _setup_gitlab_mocks(
        mock_parser, mock_getenv, mock_path_exists, mock_load_single_resolver_output, mock_identify_token, mock_args
    )

    # Execute main function
    main()

    # Verify successful execution
    _verify_gitlab_successful_execution(
        mock_identify_token,
        mock_process_single_issue,
        mock_args,
        mock_parser,
        mock_getenv,
        mock_path_exists,
        mock_load_single_resolver_output,
    )

    # Test error cases
    _test_gitlab_error_cases(mock_args, mock_getenv)


def _create_gitlab_mock_args():
    """Create mock arguments for GitLab testing."""
    mock_args = MagicMock()
    mock_args.token = None
    mock_args.username = "mock_username"
    mock_args.output_dir = "/mock/output"
    mock_args.pr_type = "draft"
    mock_args.issue_number = "42"
    mock_args.fork_owner = None
    mock_args.send_on_failure = False
    mock_args.llm_model = "mock_model"
    mock_args.llm_base_url = "mock_url"
    mock_args.llm_api_key = "mock_key"
    mock_args.target_branch = None
    mock_args.reviewer = None
    mock_args.pr_title = None
    mock_args.selected_repo = None
    mock_args.git_user_name = "openhands"
    mock_args.git_user_email = "openhands@all-hands.dev"
    return mock_args


def _setup_gitlab_mocks(
    mock_parser, mock_getenv, mock_path_exists, mock_load_single_resolver_output, mock_identify_token, mock_args
):
    """Setup all mocks for GitLab testing."""
    mock_parser.return_value.parse_args.return_value = mock_args
    mock_getenv.side_effect = lambda key, default=None: "mock_token" if key == "GITLAB_TOKEN" else default
    mock_path_exists.return_value = True
    mock_resolver_output = MagicMock()
    mock_load_single_resolver_output.return_value = mock_resolver_output
    mock_identify_token.return_value = ProviderType.GITLAB


def _verify_gitlab_successful_execution(
    mock_identify_token,
    mock_process_single_issue,
    mock_args,
    mock_parser,
    mock_getenv,
    mock_path_exists,
    mock_load_single_resolver_output,
):
    """Verify that main function executed successfully with correct GitLab parameters."""
    # Verify token identification
    mock_identify_token.assert_called_with("mock_token", mock_args.base_domain)

    # Verify LLM config creation
    llm_config = LLMConfig(model=mock_args.llm_model, base_url=mock_args.llm_base_url, api_key=mock_args.llm_api_key)

    # Verify process_single_issue call
    _verify_gitlab_process_single_issue_call(mock_process_single_issue, mock_args, llm_config)

    # Verify other function calls
    _verify_gitlab_other_function_calls(mock_parser, mock_getenv, mock_path_exists, mock_load_single_resolver_output)


def _verify_gitlab_process_single_issue_call(mock_process_single_issue, mock_args, llm_config):
    """Verify process_single_issue was called with correct GitLab arguments."""
    assert mock_process_single_issue.called
    called_args = mock_process_single_issue.call_args[0]
    expected_output_dir = os.path.normpath("/mock/output")

    assert os.path.normpath(called_args[0]) == expected_output_dir
    assert called_args[1] is not None  # mock_resolver_output
    assert called_args[2] == "mock_token"
    assert called_args[3] == "mock_username"
    assert called_args[4] == ProviderType.GITLAB
    assert called_args[5] == "draft"
    assert called_args[6] == llm_config
    assert called_args[7] is None
    assert called_args[8] is False
    assert called_args[9] == mock_args.target_branch
    assert called_args[10] == mock_args.reviewer
    assert called_args[11] == mock_args.pr_title


def _verify_gitlab_other_function_calls(mock_parser, mock_getenv, mock_path_exists, mock_load_single_resolver_output):
    """Verify other function calls were made correctly for GitLab."""
    mock_parser.assert_called_once()
    mock_getenv.assert_any_call("GITLAB_TOKEN")

    # Verify path existence check
    assert mock_path_exists.called
    called_exists_arg = mock_path_exists.call_args[0][0]
    expected_output_dir = os.path.normpath("/mock/output")
    assert os.path.normpath(called_exists_arg) == expected_output_dir

    # Verify load_single_resolver_output call
    assert mock_load_single_resolver_output.called
    load_call_args = mock_load_single_resolver_output.call_args[0]
    expected_output_jsonl = os.path.normpath("/mock/output/output.jsonl")
    assert os.path.normpath(load_call_args[0]) == expected_output_jsonl
    assert load_call_args[1] == 42


def _test_gitlab_error_cases(mock_args, mock_getenv):
    """Test error cases for GitLab main function."""
    # Test invalid issue number
    mock_args.issue_number = "invalid"
    with pytest.raises(ValueError):
        main()

    # Reset issue number
    mock_args.issue_number = "42"

    # Test missing token
    mock_getenv.side_effect = lambda key, default=None: None
    with pytest.raises(ValueError, match="token is not set"):
        main()


@patch("subprocess.run")
def test_make_commit_escapes_issue_title(mock_subprocess_run):
    repo_dir = "/path/to/repo"
    issue = Issue(
        owner="test-owner",
        repo="test-repo",
        number=42,
        title='Issue with "quotes" and $pecial characters',
        body="Test body",
    )
    mock_subprocess_run.return_value = MagicMock(returncode=0, stdout="sample output", stderr="")
    issue_type = "issue"
    make_commit(repo_dir, issue, issue_type)
    calls = mock_subprocess_run.call_args_list
    assert len(calls) == 4
    git_commit_call = calls[3][0][0]
    expected_commit_message = 'Fix issue #42: Issue with "quotes" and $pecial characters'
    assert ["git", "-C", "/path/to/repo", "commit", "-m", expected_commit_message] == git_commit_call


@patch("subprocess.run")
def test_make_commit_no_changes(mock_subprocess_run):
    repo_dir = "/path/to/repo"
    issue = Issue(owner="test-owner", repo="test-repo", number=42, title="Issue with no changes", body="Test body")
    mock_subprocess_run.side_effect = [
        MagicMock(returncode=0),
        MagicMock(returncode=0),
        MagicMock(returncode=1, stdout=""),
    ]
    with pytest.raises(RuntimeError, match="ERROR: Openhands failed to make code changes."):
        make_commit(repo_dir, issue, "issue")
    assert mock_subprocess_run.call_count == 3
    git_status_call = mock_subprocess_run.call_args_list[2][0][0]
    assert f"git -C {repo_dir} status --porcelain" in git_status_call


def test_apply_patch_rename_directory(mock_output_dir):
    old_dir = os.path.join(mock_output_dir, "prompts", "resolve")
    os.makedirs(old_dir)
    test_files = ["issue-success-check.jinja", "pr-feedback-check.jinja", "pr-thread-check.jinja"]
    for filename in test_files:
        file_path = os.path.join(old_dir, filename)
        with open(file_path, "w", encoding='utf-8') as f:
            f.write(f"Content of {filename}")
    patch_content = "diff --git a/prompts/resolve/issue-success-check.jinja b/prompts/guess_success/issue-success-check.jinja\nsimilarity index 100%\nrename from prompts/resolve/issue-success-check.jinja\nrename to prompts/guess_success/issue-success-check.jinja\ndiff --git a/prompts/resolve/pr-feedback-check.jinja b/prompts/guess_success/pr-feedback-check.jinja\nsimilarity index 100%\nrename from prompts/resolve/pr-feedback-check.jinja\nrename to prompts/guess_success/pr-feedback-check.jinja\ndiff --git a/prompts/resolve/pr-thread-check.jinja b/prompts/guess_success/pr-thread-check.jinja\nsimilarity index 100%\nrename from prompts/resolve/pr-thread-check.jinja\nrename to prompts/guess_success/pr-thread-check.jinja"
    apply_patch(mock_output_dir, patch_content)
    new_dir = os.path.join(mock_output_dir, "prompts", "guess_success")
    assert not os.path.exists(old_dir), "Old directory still exists"
    assert os.path.exists(new_dir), "New directory was not created"
    for filename in test_files:
        old_path = os.path.join(old_dir, filename)
        new_path = os.path.join(new_dir, filename)
        assert not os.path.exists(old_path), f"Old file {filename} still exists"
        assert os.path.exists(new_path), f"New file {filename} was not created"
        with open(new_path, "r", encoding='utf-8') as f:
            content = f.read()
        assert content == f"Content of {filename}", f"Content mismatch for {filename}"
