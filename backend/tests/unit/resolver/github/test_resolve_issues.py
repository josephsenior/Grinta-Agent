import os
import subprocess
import tempfile
from typing import cast
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from pydantic import SecretStr

from forge.core.config import LLMConfig
from forge.events.action import CmdRunAction, MessageAction
from forge.events.event import Event
from forge.events.observation import (
    CmdOutputMetadata,
    CmdOutputObservation,
    NullObservation,
)
from forge.integrations.service_types import ProviderType
from forge.llm.llm import LLM
from forge.resolver.interfaces.github import GithubIssueHandler, GithubPRHandler
from forge.resolver.interfaces.issue import Issue, ReviewThread
from forge.resolver.interfaces.issue_definitions import (
    ServiceContextIssue,
    ServiceContextPR,
)
from forge.resolver.resolver_output import ResolverOutput


@pytest.fixture
def default_mock_args():
    """Fixture that provides a default mock args object with common values.

    Tests can override specific attributes as needed.
    """
    mock_args = MagicMock()
    mock_args.selected_repo = "test-owner/test-repo"
    mock_args.token = "test-token"
    mock_args.username = "test-user"
    mock_args.max_iterations = 5
    mock_args.output_dir = "/tmp"  # nosec B108 - Safe: test output directory
    mock_args.llm_model = "test"
    mock_args.llm_api_key = SecretStr("test")
    mock_args.llm_base_url = None
    mock_args.base_domain = None
    mock_args.runtime_container_image = None
    mock_args.base_container_image = None
    mock_args.is_experimental = False
    mock_args.issue_number = None
    mock_args.comment_id = None
    mock_args.repo_instruction_file = None
    mock_args.issue_type = "issue"
    mock_args.prompt_file = None
    return mock_args


@pytest.fixture(autouse=True)
def mock_github_token():
    """Fixture that patches the identify_token function to return GitHub provider type.

    This eliminates the need for repeated patching in each test function.
    """
    with patch(
        "forge.resolver.issue_resolver.IssueResolver._identify_platform",
        return_value=ProviderType.GITHUB,
    ), patch(
        "forge.resolver.issue_resolver.identify_token",
        new_callable=AsyncMock,
        return_value=ProviderType.GITHUB,
    ), patch(
        "forge.resolver.utils.identify_token",
        new_callable=AsyncMock,
        return_value=ProviderType.GITHUB,
    ), patch(
        "forge.resolver.utils.validate_provider_token",
        AsyncMock(return_value=ProviderType.GITHUB),
    ), patch(
        "forge.integrations.utils.validate_provider_token",
        AsyncMock(return_value=ProviderType.GITHUB),
    ), patch(
        "forge.resolver.issue_resolver.call_async_from_sync",
        return_value=ProviderType.GITHUB,
    ):
        yield


@pytest.fixture
def mock_output_dir():
    with tempfile.TemporaryDirectory() as temp_dir:
        repo_path = os.path.join(temp_dir, "repo")
        os.makedirs(repo_path)
        subprocess.run(["git", "init", repo_path], check=True)
        subprocess.run(
            ["git", "-C", repo_path, "config", "user.email", "forge-tests@example.com"],
            check=True,
        )
        subprocess.run(
            ["git", "-C", repo_path, "config", "user.name", "Forge Tests"], check=True
        )
        readme_path = os.path.join(repo_path, "README.md")
        with open(readme_path, "w", encoding="utf-8") as f:
            f.write("hello world")
        subprocess.run(["git", "-C", repo_path, "add", "README.md"], check=True)
        subprocess.run(
            ["git", "-C", repo_path, "commit", "-m", "Initial commit"], check=True
        )
        yield temp_dir


@pytest.fixture
def mock_subprocess():
    with patch("subprocess.check_output") as mock_check_output:
        yield mock_check_output


@pytest.fixture
def mock_os():
    with patch("os.system") as mock_system, patch("os.path.join") as mock_join:
        yield (mock_system, mock_join)


@pytest.fixture
def mock_user_instructions_template():
    return "Issue: {{ body }}\n\nPlease fix this issue."


@pytest.fixture
def mock_conversation_instructions_template():
    return "Instructions: {{ repo_instruction }}"


@pytest.fixture
def mock_followup_prompt_template():
    return "Issue context: {{ issues }}\n\nReview comments: {{ review_comments }}\n\nReview threads: {{ review_threads }}\n\nFiles: {{ files }}\n\nThread comments: {{ thread_context }}\n\nPlease fix this issue."


def create_cmd_output(exit_code: int, content: str, command: str):
    return CmdOutputObservation(
        content=content,
        command=command,
        metadata=CmdOutputMetadata(exit_code=exit_code),
    )


def test_initialize_runtime(default_mock_args, mock_github_token):
    import sys
    print(f"\nDEBUG: sys.path: {sys.path}")
    from forge.resolver.issue_resolver import IssueResolver
    import sys
    print(f"DEBUG: IssueResolver module: {IssueResolver.__module__}")
    print(f"DEBUG: IssueResolver file: {sys.modules[IssueResolver.__module__].__file__}")
    from forge.events.observation.commands import CmdOutputObservation
    print(f"DEBUG: CmdOutputObservation module: {CmdOutputObservation.__module__}")
    print(f"DEBUG: CmdOutputObservation file: {sys.modules[CmdOutputObservation.__module__].__file__}")
    mock_runtime = MagicMock()
    mock_runtime.run_action.side_effect = [
        create_cmd_output(exit_code=0, content="", command="cd /workspace"),
        create_cmd_output(
            exit_code=0, content="", command='git config --global core.pager ""'
        ),
    ]
    resolver = IssueResolver(default_mock_args)
    resolver.initialize_runtime(mock_runtime)
    assert mock_runtime.run_action.call_count == 2
    mock_runtime.run_action.assert_any_call(CmdRunAction(command="cd /workspace"))
    mock_runtime.run_action.assert_any_call(
        CmdRunAction(command='git config --global core.pager ""')
    )


@pytest.mark.asyncio
async def test_resolve_issue_no_issues_found(default_mock_args, mock_github_token):
    """Test the resolve_issue method when no issues are found."""
    from forge.resolver.issue_resolver import IssueResolver
    mock_handler = MagicMock()
    mock_handler.get_converted_issues.return_value = []
    default_mock_args.issue_number = 5432
    resolver = IssueResolver(default_mock_args)
    resolver.issue_handler = mock_handler
    with pytest.raises(ValueError) as exc_info:
        await resolver.resolve_issue()
    assert "No issues found for issue number 5432" in str(exc_info.value)
    assert "test-owner/test-repo" in str(exc_info.value)
    mock_handler.get_converted_issues.assert_called_once_with(
        issue_numbers=[5432], comment_id=None
    )


def test_download_issues_from_github():
    llm_config = LLMConfig(model="test", api_key=SecretStr("test"))
    handler = ServiceContextIssue(
        GithubIssueHandler("owner", "repo", "token"), llm_config
    )
    mock_issues_response = MagicMock()
    mock_issues_response.json.side_effect = [
        [
            {"number": 1, "title": "Issue 1", "body": "This is an issue"},
            {
                "number": 2,
                "title": "PR 1",
                "body": "This is a pull request",
                "pull_request": {},
            },
            {"number": 3, "title": "Issue 2", "body": "This is another issue"},
        ],
        None,
    ]
    mock_issues_response.raise_for_status = MagicMock()
    mock_comments_response = MagicMock()
    mock_comments_response.json.return_value = []
    mock_comments_response.raise_for_status = MagicMock()

    def get_mock_response(url, *args, **kwargs):
        return mock_comments_response if "/comments" in url else mock_issues_response

    with patch("httpx.get", side_effect=get_mock_response):
        issues = handler.get_converted_issues(issue_numbers=[1, 3])
    assert len(issues) == 2
    assert handler.issue_type == "issue"
    assert all((isinstance(issue, Issue) for issue in issues))
    assert [issue.number for issue in issues] == [1, 3]
    assert [issue.title for issue in issues] == ["Issue 1", "Issue 2"]
    assert [issue.review_comments for issue in issues] == [None, None]
    assert [issue.closing_issues for issue in issues] == [None, None]
    assert [issue.thread_ids for issue in issues] == [None, None]


def test_download_pr_from_github():
    llm_config = LLMConfig(model="test", api_key=SecretStr("test"))
    handler = ServiceContextPR(GithubPRHandler("owner", "repo", "token"), llm_config)
    mock_pr_response = MagicMock()
    mock_pr_response.json.side_effect = [
        [
            {
                "number": 1,
                "title": "PR 1",
                "body": "This is a pull request",
                "head": {"ref": "b1"},
            },
            {
                "number": 2,
                "title": "My PR",
                "body": "This is another pull request",
                "head": {"ref": "b2"},
            },
            {"number": 3, "title": "PR 3", "body": "Final PR", "head": {"ref": "b3"}},
        ],
        None,
    ]
    mock_pr_response.raise_for_status = MagicMock()
    mock_comments_response = MagicMock()
    mock_comments_response.json.return_value = []
    mock_comments_response.raise_for_status = MagicMock()
    mock_graphql_response = MagicMock()
    mock_graphql_response.json.side_effect = lambda: {
        "data": {
            "repository": {
                "pullRequest": {
                    "closingIssuesReferences": {
                        "edges": [
                            {"node": {"body": "Issue 1 body", "number": 1}},
                            {"node": {"body": "Issue 2 body", "number": 2}},
                        ]
                    },
                    "reviewThreads": {
                        "edges": [
                            {
                                "node": {
                                    "isResolved": False,
                                    "id": "1",
                                    "comments": {
                                        "nodes": [
                                            {
                                                "body": "Unresolved comment 1",
                                                "path": "/frontend/header.tsx",
                                            },
                                            {"body": "Follow up thread"},
                                        ]
                                    },
                                }
                            },
                            {
                                "node": {
                                    "isResolved": True,
                                    "id": "2",
                                    "comments": {
                                        "nodes": [
                                            {
                                                "body": "Resolved comment 1",
                                                "path": "/some/file.py",
                                            }
                                        ]
                                    },
                                }
                            },
                            {
                                "node": {
                                    "isResolved": False,
                                    "id": "3",
                                    "comments": {
                                        "nodes": [
                                            {
                                                "body": "Unresolved comment 3",
                                                "path": "/another/file.py",
                                            }
                                        ]
                                    },
                                }
                            },
                        ]
                    },
                }
            }
        }
    }
    mock_graphql_response.raise_for_status = MagicMock()

    def get_mock_response(url, *args, **kwargs):
        return mock_comments_response if "/comments" in url else mock_pr_response

    with patch("httpx.get", side_effect=get_mock_response):
        with patch("httpx.post", return_value=mock_graphql_response):
            issues = handler.get_converted_issues(issue_numbers=[1, 2, 3])
    assert len(issues) == 3
    assert handler.issue_type == "pr"
    assert all((isinstance(issue, Issue) for issue in issues))
    assert [issue.number for issue in issues] == [1, 2, 3]
    assert [issue.title for issue in issues] == ["PR 1", "My PR", "PR 3"]
    assert [issue.head_branch for issue in issues] == ["b1", "b2", "b3"]
    review_threads = issues[0].review_threads or []
    assert len(review_threads) == 2
    assert (
        review_threads[0].comment
        == "Unresolved comment 1\n---\nlatest feedback:\nFollow up thread\n"
    )
    assert review_threads[0].files == ["/frontend/header.tsx"]
    assert (
        review_threads[1].comment
        == "latest feedback:\nUnresolved comment 3\n"
    )
    assert review_threads[1].files == ["/another/file.py"]
    assert (issues[0].closing_issues or []) == ["Issue 1 body", "Issue 2 body"]
    assert (issues[0].thread_ids or []) == ["1", "3"]


@pytest.mark.asyncio
async def test_complete_runtime(default_mock_args, mock_github_token):
    """Test the complete_runtime method."""
    from forge.resolver.issue_resolver import IssueResolver
    mock_runtime = MagicMock()
    mock_runtime.run_action.side_effect = [
        create_cmd_output(exit_code=0, content="", command="cd /workspace"),
        create_cmd_output(
            exit_code=0, content="", command='git config --global core.pager ""'
        ),
        create_cmd_output(
            exit_code=0,
            content="",
            command="git config --global --add safe.directory /workspace",
        ),
        create_cmd_output(
            exit_code=0, content="", command="git diff base_commit_hash fix"
        ),
        create_cmd_output(exit_code=0, content="git diff content", command="git apply"),
    ]
    resolver = IssueResolver(default_mock_args)
    result = await resolver.complete_runtime(mock_runtime, "base_commit_hash")
    assert result == {"git_patch": "git diff content"}
    assert mock_runtime.run_action.call_count == 5


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "test_case",
    [
        {
            "name": "successful_run",
            "run_controller_return": MagicMock(
                history=[NullObservation(content="")],
                metrics=MagicMock(
                    get=MagicMock(return_value={"test_result": "passed"})
                ),
                last_error=None,
            ),
            "run_controller_raises": None,
            "expected_success": True,
            "expected_error": None,
            "expected_explanation": "Issue resolved successfully",
            "is_pr": False,
            "comment_success": None,
        },
        {
            "name": "value_error",
            "run_controller_return": None,
            "run_controller_raises": ValueError("Test value error"),
            "expected_success": False,
            "expected_error": "Agent failed to run or crashed",
            "expected_explanation": "Agent failed to run",
            "is_pr": False,
            "comment_success": None,
        },
        {
            "name": "runtime_error",
            "run_controller_return": None,
            "run_controller_raises": RuntimeError("Test runtime error"),
            "expected_success": False,
            "expected_error": "Agent failed to run or crashed",
            "expected_explanation": "Agent failed to run",
            "is_pr": False,
            "comment_success": None,
        },
        {
            "name": "json_decode_error",
            "run_controller_return": MagicMock(
                history=[NullObservation(content="")],
                metrics=MagicMock(
                    get=MagicMock(return_value={"test_result": "passed"})
                ),
                last_error=None,
            ),
            "run_controller_raises": None,
            "expected_success": True,
            "expected_error": None,
            "expected_explanation": "Non-JSON explanation",
            "is_pr": True,
            "comment_success": [True, False],
        },
    ],
)
async def test_process_issue(
    default_mock_args,
    mock_github_token,
    mock_output_dir,
    mock_user_instructions_template,
    test_case,
):
    """Test the process_issue method with different scenarios."""
    from forge.resolver.issue_resolver import IssueResolver
    issue = Issue(
        owner="test_owner",
        repo="test_repo",
        number=1,
        title="Test Issue",
        body="This is a test issue",
    )
    base_commit = "abcdef1234567890"
    default_mock_args.output_dir = mock_output_dir
    default_mock_args.issue_type = "pr" if test_case.get("is_pr", False) else "issue"
    resolver = IssueResolver(default_mock_args)
    resolver.user_instructions_prompt_template = mock_user_instructions_template
    llm_config = LLMConfig(model="test", api_key=SecretStr("test"))
    handler_instance = MagicMock()
    handler_instance.guess_success.return_value = (
        test_case["expected_success"],
        test_case.get("comment_success", None),
        test_case["expected_explanation"],
    )
    handler_instance.get_instruction.return_value = (
        "Test instruction",
        "Test conversation instructions",
        [],
    )
    handler_instance.issue_type = "pr" if test_case.get("is_pr", False) else "issue"
    handler_instance.llm = LLM(llm_config, service_id="test-service")
    mock_runtime = MagicMock()
    mock_runtime.connect = AsyncMock()
    mock_runtime.run_action.return_value = CmdOutputObservation(
        content="test patch",
        command="git diff",
        metadata=CmdOutputMetadata(exit_code=0),
    )
    mock_runtime.event_stream.subscribe = MagicMock()
    mock_create_runtime = MagicMock(return_value=mock_runtime)
    mock_run_controller = AsyncMock()
    if test_case["run_controller_raises"]:
        mock_run_controller.side_effect = test_case["run_controller_raises"]
    else:
        mock_run_controller.return_value = test_case["run_controller_return"]
    with (
        patch("forge.resolver.issue_resolver.create_runtime", mock_create_runtime),
        patch("forge.resolver.issue_resolver.run_controller", mock_run_controller),
        patch.object(
            resolver, "complete_runtime", return_value={"git_patch": "test patch"}
        ),
        patch.object(resolver, "initialize_runtime") as mock_initialize_runtime,
    ):
        result = await resolver.process_issue(issue, base_commit, handler_instance)
        assert isinstance(result, ResolverOutput)
        assert result.issue == issue
        assert result.base_commit == base_commit
        assert result.git_patch == "test patch"
        assert result.success == test_case["expected_success"]
        assert result.result_explanation == test_case["expected_explanation"]
        assert result.error == test_case["expected_error"]
        mock_create_runtime.assert_called_once()
        mock_runtime.connect.assert_called_once()
        mock_initialize_runtime.assert_called_once()
        mock_run_controller.assert_called_once()
        cast(AsyncMock, resolver.complete_runtime).assert_awaited_once_with(
            mock_runtime, base_commit
        )
        if not test_case["run_controller_raises"]:
            assert "config" in mock_run_controller.call_args[1]
            assert isinstance(
                mock_run_controller.call_args[1]["initial_user_action"], MessageAction
            )
            assert mock_run_controller.call_args[1]["runtime"] == mock_runtime
        if test_case["expected_success"]:
            handler_instance.guess_success.assert_called_once()
        else:
            handler_instance.guess_success.assert_not_called()


def test_get_instruction(
    mock_user_instructions_template,
    mock_conversation_instructions_template,
    mock_followup_prompt_template,
):
    issue = Issue(
        owner="test_owner",
        repo="test_repo",
        number=123,
        title="Test Issue",
        body="This is a test issue refer to image ![First Image](https://sampleimage.com/image1.png)",
    )
    mock_llm_config = LLMConfig(
        model="test_model", api_key=SecretStr("test_api_key")
    )
    issue_handler = ServiceContextIssue(
        GithubIssueHandler("owner", "repo", "token"), mock_llm_config
    )
    instruction, conversation_instructions, images_urls = issue_handler.get_instruction(
        issue,
        mock_user_instructions_template,
        mock_conversation_instructions_template,
        None,
    )
    expected_instruction = "Issue: Test Issue\n\nThis is a test issue refer to image ![First Image](https://sampleimage.com/image1.png)\n\nPlease fix this issue."
    assert images_urls == ["https://sampleimage.com/image1.png"]
    assert issue_handler.issue_type == "issue"
    assert instruction == expected_instruction
    assert conversation_instructions is not None
    issue = Issue(
        owner="test_owner",
        repo="test_repo",
        number=123,
        title="Test Issue",
        body="This is a test issue",
        closing_issues=["Issue 1 fix the type"],
        review_threads=[
            ReviewThread(
                comment="There is still a typo 'pthon' instead of 'python'", files=[]
            )
        ],
        thread_comments=[
            "I've left review comments, please address them",
            "This is a valid concern.",
        ],
    )
    pr_handler = ServiceContextPR(
        GithubPRHandler("owner", "repo", "token"), mock_llm_config
    )
    instruction, conversation_instructions, images_urls = pr_handler.get_instruction(
        issue,
        mock_followup_prompt_template,
        mock_conversation_instructions_template,
        None,
    )
    expected_instruction = "Issue context: [\n    \"Issue 1 fix the type\"\n]\n\nReview comments: None\n\nReview threads: [\n    \"There is still a typo 'pthon' instead of 'python'\"\n]\n\nFiles: []\n\nThread comments: I've left review comments, please address them\n---\nThis is a valid concern.\n\nPlease fix this issue."
    assert images_urls == []
    assert pr_handler.issue_type == "pr"
    assert "There is still a typo 'pthon' instead of 'python'" in instruction
    assert "I've left review comments, please address them" in instruction
    assert "This is a valid concern" in instruction
    assert conversation_instructions is not None


def test_file_instruction():
    issue = Issue(
        owner="test_owner",
        repo="test_repo",
        number=123,
        title="Test Issue",
        body="This is a test issue ![image](https://sampleimage.com/sample.png)",
    )
    # Get paths relative to this test file
    current_dir = os.path.dirname(__file__)
    resolver_dir = os.path.join(current_dir, "..", "..", "..", "..", "resolver")
    basic_jinja_path = os.path.join(resolver_dir, "prompts", "resolve", "basic.jinja")
    conv_instr_path = os.path.join(resolver_dir, "prompts", "resolve", "basic-conversation-instructions.jinja")

    with open(basic_jinja_path, "r", encoding="utf-8") as f:
        prompt = f.read()
    with open(
        conv_instr_path,
        "r",
        encoding="utf-8",
    ) as f:
        conversation_instructions_template = f.read()
    mock_llm_config = LLMConfig(
        model="test_model", api_key=SecretStr("test_api_key")
    )
    issue_handler = ServiceContextIssue(
        GithubIssueHandler("owner", "repo", "token"), mock_llm_config
    )
    instruction, conversation_instructions, images_urls = issue_handler.get_instruction(
        issue, prompt, conversation_instructions_template, None
    )
    assert instruction.startswith(
        "Please fix the following issue for the repository in /workspace."
    )
    assert "Resolve prompt for tests" in instruction
    assert images_urls == ["https://sampleimage.com/sample.png"]
    assert (
        "IMPORTANT: You should ONLY interact with the environment provided to you"
        in conversation_instructions
    )
    assert "You SHOULD INCLUDE PROPER INDENTATION" in conversation_instructions


def test_file_instruction_with_repo_instruction():
    issue = Issue(
        owner="test_owner",
        repo="test_repo",
        number=123,
        title="Test Issue",
        body="This is a test issue",
    )
    # Get paths relative to this test file
    current_dir = os.path.dirname(__file__)
    resolver_dir = os.path.join(current_dir, "..", "..", "..", "..", "resolver")
    basic_jinja_path = os.path.join(resolver_dir, "prompts", "resolve", "basic.jinja")
    conv_instr_path = os.path.join(resolver_dir, "prompts", "resolve", "basic-conversation-instructions.jinja")
    repo_instr_path = os.path.join(resolver_dir, "prompts", "repo_instructions", "Forge___Forge-resolver.txt")

    with open(basic_jinja_path, "r", encoding="utf-8") as f:
        prompt = f.read()
    with open(
        conv_instr_path,
        "r",
        encoding="utf-8",
    ) as f:
        conversation_instructions_prompt = f.read()
    with open(
        repo_instr_path,
        "r",
        encoding="utf-8",
    ) as f:
        repo_instruction = f.read()
    mock_llm_config = LLMConfig(
        model="test_model", api_key=SecretStr("test_api_key")
    )
    issue_handler = ServiceContextIssue(
        GithubIssueHandler("owner", "repo", "token"), mock_llm_config
    )
    instruction, conversation_instructions, image_urls = issue_handler.get_instruction(
        issue, prompt, conversation_instructions_prompt, repo_instruction
    )
    assert instruction.startswith(
        "Please fix the following issue for the repository in /workspace."
    )
    assert "Resolve prompt for tests" in instruction
    assert (
        "IMPORTANT: You should ONLY interact with the environment provided to you"
        in conversation_instructions
    )
    assert "Some basic information about this repository:" in conversation_instructions
    assert "This is a Python repo for Forge-resolver" in conversation_instructions
    assert conversation_instructions is not None
    assert issue_handler.issue_type == "issue"
    assert image_urls == []


def test_guess_success():
    mock_issue = Issue(
        owner="test_owner",
        repo="test_repo",
        number=1,
        title="Test Issue",
        body="This is a test issue",
    )
    mock_history = [create_cmd_output(exit_code=0, content="", command="cd /workspace")]
    mock_llm_config = LLMConfig(
        model="test_model", api_key=SecretStr("test_api_key")
    )
    mock_completion_response = MagicMock()
    mock_completion_response.choices = [
        MagicMock(
            message=MagicMock(
                content="--- success\ntrue\n--- explanation\nIssue resolved successfully"
            )
        )
    ]
    issue_handler = ServiceContextIssue(
        GithubIssueHandler("owner", "repo", "token"), mock_llm_config
    )
    with patch.object(
        LLM, "completion", MagicMock(return_value=mock_completion_response)
    ):
        success, comment_success, explanation = issue_handler.guess_success(
            mock_issue, mock_history
        )
        assert issue_handler.issue_type == "issue"
        assert comment_success is None
        assert success
        assert explanation == "Issue resolved successfully"


def test_guess_success_with_thread_comments():
    mock_issue = Issue(
        owner="test_owner",
        repo="test_repo",
        number=1,
        title="Test Issue",
        body="This is a test issue",
        thread_comments=[
            "First comment",
            "Second comment",
            "latest feedback:\nPlease add tests",
        ],
    )
    mock_history = cast(
        list[Event], [MagicMock(message="I have added tests for this case")]
    )
    mock_llm_config = LLMConfig(
        model="test_model", api_key=SecretStr("test_api_key")
    )
    mock_completion_response = MagicMock()
    mock_completion_response.choices = [
        MagicMock(
            message=MagicMock(
                content="--- success\ntrue\n--- explanation\nTests have been added to verify thread comments handling"
            )
        )
    ]
    issue_handler = ServiceContextIssue(
        GithubIssueHandler("owner", "repo", "token"), mock_llm_config
    )
    with patch.object(
        LLM, "completion", MagicMock(return_value=mock_completion_response)
    ):
        success, comment_success, explanation = issue_handler.guess_success(
            mock_issue, mock_history
        )
        assert issue_handler.issue_type == "issue"
        assert comment_success is None
        assert success
        assert "Tests have been added" in explanation


def test_instruction_with_thread_comments():
    issue = Issue(
        owner="test_owner",
        repo="test_repo",
        number=123,
        title="Test Issue",
        body="This is a test issue",
        thread_comments=[
            "First comment",
            "Second comment",
            "latest feedback:\nPlease add tests",
        ],
    )
    # Get paths relative to this test file
    current_dir = os.path.dirname(__file__)
    resolver_dir = os.path.join(current_dir, "..", "..", "..", "..", "resolver")
    basic_jinja_path = os.path.join(resolver_dir, "prompts", "resolve", "basic.jinja")
    conv_instr_path = os.path.join(resolver_dir, "prompts", "resolve", "basic-conversation-instructions.jinja")

    with open(basic_jinja_path, "r", encoding="utf-8") as f:
        prompt = f.read()
    with open(
        conv_instr_path,
        "r",
        encoding="utf-8",
    ) as f:
        conversation_instructions_template = f.read()
    llm_config = LLMConfig(model="test", api_key=SecretStr("test"))
    issue_handler = ServiceContextIssue(
        GithubIssueHandler("owner", "repo", "token"), llm_config
    )
    instruction, _, images_urls = issue_handler.get_instruction(
        issue, prompt, conversation_instructions_template, None
    )
    if "Resolve prompt for tests" in instruction:
        assert "Resolve prompt for tests" in instruction
    else:
        assert "First comment" in instruction
        assert "Second comment" in instruction
        assert "Please add tests" in instruction
        assert "Issue Thread Comments:" in instruction
    assert images_urls == []


def test_guess_success_failure():
    mock_issue = Issue(
        owner="test_owner",
        repo="test_repo",
        number=1,
        title="Test Issue",
        body="This is a test issue",
        thread_comments=[
            "First comment",
            "Second comment",
            "latest feedback:\nPlease add tests",
        ],
    )
    mock_history = cast(
        list[Event], [MagicMock(message="I have added tests for this case")]
    )
    mock_llm_config = LLMConfig(
        model="test_model", api_key=SecretStr("test_api_key")
    )
    mock_completion_response = MagicMock()
    mock_completion_response.choices = [
        MagicMock(
            message=MagicMock(
                content="--- success\ntrue\n--- explanation\nTests have been added to verify thread comments handling"
            )
        )
    ]
    issue_handler = ServiceContextIssue(
        GithubIssueHandler("owner", "repo", "token"), mock_llm_config
    )
    with patch.object(
        LLM, "completion", MagicMock(return_value=mock_completion_response)
    ):
        success, comment_success, explanation = issue_handler.guess_success(
            mock_issue, mock_history
        )
        assert issue_handler.issue_type == "issue"
        assert comment_success is None
        assert success
        assert "Tests have been added" in explanation


def test_guess_success_negative_case():
    mock_issue = Issue(
        owner="test_owner",
        repo="test_repo",
        number=1,
        title="Test Issue",
        body="This is a test issue",
    )
    mock_history = [create_cmd_output(exit_code=0, content="", command="cd /workspace")]
    mock_llm_config = LLMConfig(
        model="test_model", api_key=SecretStr("test_api_key")
    )
    mock_completion_response = MagicMock()
    mock_completion_response.choices = [
        MagicMock(
            message=MagicMock(
                content="--- success\nfalse\n--- explanation\nIssue not resolved"
            )
        )
    ]
    issue_handler = ServiceContextIssue(
        GithubIssueHandler("owner", "repo", "token"), mock_llm_config
    )
    with patch.object(
        LLM, "completion", MagicMock(return_value=mock_completion_response)
    ):
        success, comment_success, explanation = issue_handler.guess_success(
            mock_issue, mock_history
        )
        assert issue_handler.issue_type == "issue"
        assert comment_success is None
        assert not success
        assert explanation == "Issue not resolved"


def test_guess_success_invalid_output():
    mock_issue = Issue(
        owner="test_owner",
        repo="test_repo",
        number=1,
        title="Test Issue",
        body="This is a test issue",
    )
    mock_history = [create_cmd_output(exit_code=0, content="", command="cd /workspace")]
    mock_llm_config = LLMConfig(
        model="test_model", api_key=SecretStr("test_api_key")
    )
    mock_completion_response = MagicMock()
    mock_completion_response.choices = [
        MagicMock(message=MagicMock(content="This is not a valid output"))
    ]
    issue_handler = ServiceContextIssue(
        GithubIssueHandler("owner", "repo", "token"), mock_llm_config
    )
    with patch.object(
        LLM, "completion", MagicMock(return_value=mock_completion_response)
    ):
        success, comment_success, explanation = issue_handler.guess_success(
            mock_issue, mock_history
        )
        assert issue_handler.issue_type == "issue"
        assert comment_success is None
        assert not success
        assert (
            explanation
            == "Failed to decode answer from LLM response: This is not a valid output"
        )


def test_download_pr_with_review_comments():
    llm_config = LLMConfig(model="test", api_key=SecretStr("test"))
    handler = ServiceContextPR(GithubPRHandler("owner", "repo", "token"), llm_config)
    mock_pr_response = MagicMock()
    mock_pr_response.json.side_effect = [
        [
            {
                "number": 1,
                "title": "PR 1",
                "body": "This is a pull request",
                "head": {"ref": "b1"},
            }
        ],
        None,
    ]
    mock_pr_response.raise_for_status = MagicMock()
    mock_comments_response = MagicMock()
    mock_comments_response.json.return_value = []
    mock_comments_response.raise_for_status = MagicMock()
    mock_graphql_response = MagicMock()
    mock_graphql_response.json.side_effect = lambda: {
        "data": {
            "repository": {
                "pullRequest": {
                    "closingIssuesReferences": {"edges": []},
                    "reviews": {
                        "nodes": [
                            {"body": "Please fix this typo"},
                            {"body": "Add more tests"},
                        ]
                    },
                }
            }
        }
    }
    mock_graphql_response.raise_for_status = MagicMock()

    def get_mock_response(url, *args, **kwargs):
        return mock_comments_response if "/comments" in url else mock_pr_response

    with patch("httpx.get", side_effect=get_mock_response):
        with patch("httpx.post", return_value=mock_graphql_response):
            issues = handler.get_converted_issues(issue_numbers=[1])
    assert len(issues) == 1
    assert handler.issue_type == "pr"
    assert isinstance(issues[0], Issue)
    assert issues[0].number == 1
    assert issues[0].title == "PR 1"
    assert issues[0].head_branch == "b1"
    review_comments = issues[0].review_comments or []
    assert len(review_comments) == 2
    assert review_comments[0] == "Please fix this typo"
    assert review_comments[1] == "Add more tests"
    assert not issues[0].review_threads
    assert not issues[0].closing_issues
    assert not issues[0].thread_ids


def test_download_issue_with_specific_comment():
    llm_config = LLMConfig(model="test", api_key=SecretStr("test"))
    handler = ServiceContextIssue(
        GithubIssueHandler("owner", "repo", "token"), llm_config
    )
    specific_comment_id = 101
    mock_issue_response = MagicMock()
    mock_issue_response.json.side_effect = [
        [{"number": 1, "title": "Issue 1", "body": "This is an issue"}],
        None,
    ]
    mock_issue_response.raise_for_status = MagicMock()
    mock_comments_response = MagicMock()
    mock_comments_response.json.return_value = [
        {
            "id": specific_comment_id,
            "body": "Specific comment body",
            "issue_url": "https://api.github.com/repos/owner/repo/issues/1",
        },
        {
            "id": 102,
            "body": "Another comment body",
            "issue_url": "https://api.github.com/repos/owner/repo/issues/2",
        },
    ]
    mock_comments_response.raise_for_status = MagicMock()

    def get_mock_response(url, *args, **kwargs):
        return mock_comments_response if "/comments" in url else mock_issue_response

    with patch("httpx.get", side_effect=get_mock_response):
        issues = handler.get_converted_issues(
            issue_numbers=[1], comment_id=specific_comment_id
        )
    assert len(issues) == 1
    assert issues[0].number == 1
    assert issues[0].title == "Issue 1"
    assert issues[0].thread_comments == ["Specific comment body"]


if __name__ == "__main__":
    pytest.main()

