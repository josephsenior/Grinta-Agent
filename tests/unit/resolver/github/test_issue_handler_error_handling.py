from unittest.mock import MagicMock, patch
import httpx
import pytest
from litellm.exceptions import RateLimitError
from forge.core.config import LLMConfig
from forge.events.action.message import MessageAction
from forge.llm.llm import LLM
from forge.resolver.interfaces.github import GithubIssueHandler, GithubPRHandler
from forge.resolver.interfaces.issue import Issue
from forge.resolver.interfaces.issue_definitions import (
    ServiceContextIssue,
    ServiceContextPR,
)


@pytest.fixture(autouse=True)
def mock_logger(monkeypatch):
    mock_logger = MagicMock()
    monkeypatch.setattr("forge.llm.debug_mixin.llm_prompt_logger", mock_logger)
    monkeypatch.setattr("forge.llm.debug_mixin.llm_response_logger", mock_logger)
    return mock_logger


@pytest.fixture
def default_config():
    return LLMConfig(
        model="gpt-4o",
        api_key="test_key",
        num_retries=2,
        retry_min_wait=1,
        retry_max_wait=2,
    )


def test_handle_nonexistent_issue_reference():
    llm_config = LLMConfig(model="test", api_key="test")
    handler = ServiceContextPR(
        GithubPRHandler("test-owner", "test-repo", "test-token"), llm_config
    )
    mock_response = MagicMock()
    mock_response.raise_for_status.side_effect = httpx.HTTPError(
        "404 Client Error: Not Found"
    )
    with patch("httpx.get", return_value=mock_response):
        result = handler._strategy.get_context_from_external_issues_references(
            closing_issues=[],
            closing_issue_numbers=[],
            issue_body="This references #999999",
            review_comments=[],
            review_threads=[],
            thread_comments=None,
        )
        assert result == []


def test_handle_rate_limit_error():
    llm_config = LLMConfig(model="test", api_key="test")
    handler = ServiceContextPR(
        GithubPRHandler("test-owner", "test-repo", "test-token"), llm_config
    )
    mock_response = MagicMock()
    mock_response.raise_for_status.side_effect = httpx.HTTPError(
        "403 Client Error: Rate Limit Exceeded"
    )
    with patch("httpx.get", return_value=mock_response):
        result = handler._strategy.get_context_from_external_issues_references(
            closing_issues=[],
            closing_issue_numbers=[],
            issue_body="This references #123",
            review_comments=[],
            review_threads=[],
            thread_comments=None,
        )
        assert result == []


def test_handle_network_error():
    llm_config = LLMConfig(model="test", api_key="test")
    handler = ServiceContextPR(
        GithubPRHandler("test-owner", "test-repo", "test-token"), llm_config
    )
    with patch("httpx.get", side_effect=httpx.NetworkError("Network Error")):
        result = handler._strategy.get_context_from_external_issues_references(
            closing_issues=[],
            closing_issue_numbers=[],
            issue_body="This references #123",
            review_comments=[],
            review_threads=[],
            thread_comments=None,
        )
        assert result == []


def test_successful_issue_reference():
    llm_config = LLMConfig(model="test", api_key="test")
    handler = ServiceContextPR(
        GithubPRHandler("test-owner", "test-repo", "test-token"), llm_config
    )
    mock_response = MagicMock()
    mock_response.raise_for_status.return_value = None
    mock_response.json.return_value = {"body": "This is the referenced issue body"}
    with patch("httpx.get", return_value=mock_response):
        result = handler._strategy.get_context_from_external_issues_references(
            closing_issues=[],
            closing_issue_numbers=[],
            issue_body="This references #123",
            review_comments=[],
            review_threads=[],
            thread_comments=None,
        )
        assert result == ["This is the referenced issue body"]


class MockLLMResponse:
    """Mock LLM Response class to mimic the actual LLM response structure."""

    class Choice:
        class Message:
            def __init__(self, content):
                self.content = content

        def __init__(self, content):
            self.message = self.Message(content)

    def __init__(self, content):
        self.choices = [self.Choice(content)]


class DotDict(dict):
    """A dictionary that supports dot notation access."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for key, value in self.items():
            if isinstance(value, dict):
                self[key] = DotDict(value)
            elif isinstance(value, list):
                self[key] = [
                    DotDict(item) if isinstance(item, dict) else item for item in value
                ]

    def __getattr__(self, key):
        if key in self:
            return self[key]
        else:
            raise AttributeError(
                f"'{self.__class__.__name__}' object has no attribute '{key}'"
            )

    def __setattr__(self, key, value):
        self[key] = value

    def __delattr__(self, key):
        if key in self:
            del self[key]
        else:
            raise AttributeError(
                f"'{self.__class__.__name__}' object has no attribute '{key}'"
            )


@patch("forge.llm.llm.litellm_completion")
def test_guess_success_rate_limit_wait_time(mock_litellm_completion, default_config):
    """Test that the retry mechanism in guess_success respects wait time between retries."""
    with patch("time.sleep") as mock_sleep:
        mock_litellm_completion.side_effect = [
            RateLimitError(
                "Rate limit exceeded", llm_provider="test_provider", model="test_model"
            ),
            DotDict(
                {
                    "choices": [
                        {
                            "message": {
                                "content": "--- success\ntrue\n--- explanation\nRetry successful"
                            }
                        }
                    ]
                }
            ),
        ]
        llm = LLM(config=default_config, service_id="test-service")
        handler = ServiceContextIssue(
            GithubIssueHandler("test-owner", "test-repo", "test-token"), default_config
        )
        handler.llm = llm
        issue = Issue(
            owner="test-owner",
            repo="test-repo",
            number=1,
            title="Test Issue",
            body="This is a test issue.",
            thread_comments=["Please improve error handling"],
        )
        history = [MessageAction(content="Fixed error handling.")]
        success, _, explanation = handler.guess_success(issue, history)
        assert success is True
        assert explanation == "Retry successful"
        assert mock_litellm_completion.call_count == 2
        mock_sleep.assert_called_once()
        wait_time = mock_sleep.call_args[0][0]
        assert (
            default_config.retry_min_wait <= wait_time <= default_config.retry_max_wait
        ), f"Expected wait time between {default_config.retry_min_wait} and {
            default_config.retry_max_wait
        } seconds, but got {wait_time}"


@patch("forge.llm.llm.litellm_completion")
def test_guess_success_exhausts_retries(mock_completion, default_config):
    """Test the retry mechanism in guess_success exhausts retries and raises an error."""
    mock_completion.side_effect = RateLimitError(
        "Rate limit exceeded", llm_provider="test_provider", model="test_model"
    )
    llm = LLM(config=default_config, service_id="test-service")
    handler = ServiceContextPR(
        GithubPRHandler("test-owner", "test-repo", "test-token"), default_config
    )
    handler.llm = llm
    issue = Issue(
        owner="test-owner",
        repo="test-repo",
        number=1,
        title="Test Issue",
        body="This is a test issue.",
        thread_comments=["Please improve error handling"],
    )
    history = [MessageAction(content="Fixed error handling.")]
    with pytest.raises(RateLimitError):
        handler.guess_success(issue, history)
    assert mock_completion.call_count == default_config.num_retries
