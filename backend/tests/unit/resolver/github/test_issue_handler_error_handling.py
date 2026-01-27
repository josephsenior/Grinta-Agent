from unittest.mock import MagicMock, patch
import httpx
import pytest
from forge.llm.exceptions import RateLimitError
from pydantic import SecretStr
from forge.core.config import LLMConfig
from forge.events.action.message import MessageAction
from forge.llm.direct_clients import LLMResponse
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
        api_key=SecretStr("test_key"),
        num_retries=2,
        retry_min_wait=1,
        retry_max_wait=2,
    )


def test_handle_nonexistent_issue_reference():
    llm_config = LLMConfig(model="test", api_key=SecretStr("test"))
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
    llm_config = LLMConfig(model="test", api_key=SecretStr("test"))
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
    llm_config = LLMConfig(model="test", api_key=SecretStr("test"))
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
    llm_config = LLMConfig(model="test", api_key=SecretStr("test"))
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
    __getattr__ = dict.get
    __setattr__ = dict.__setitem__
    __delattr__ = dict.__delitem__


@patch("forge.llm.llm.get_direct_client")
def test_guess_success_rate_limit_wait_time(mock_get_direct_client, default_config):
    """Test the retry mechanism in guess_success with rate limit wait time."""
    with patch("time.sleep") as mock_sleep:
        mock_client = MagicMock()
        mock_get_direct_client.return_value = mock_client
        
        # Ensure LLMResponse is used correctly
        mock_client.completion.side_effect = [
            RateLimitError(
                "Rate limit exceeded", llm_provider="test_provider", model="test_model"
            ),
            LLMResponse(
                content="--- success\ntrue\n--- explanation\nRetry successful",
                model="gpt-4o",
                usage={"prompt_tokens": 10, "completion_tokens": 5}
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
        
        # We need to make sure LLM.completion uses our mock_client
        # LLM.__init__ calls get_direct_client, so llm.client should be mock_client
        
        success, _, explanation = handler.guess_success(issue, history)
        assert success is True
        assert explanation == "Retry successful"
        assert mock_client.completion.call_count == 2
        mock_sleep.assert_called_once()
        wait_time = mock_sleep.call_args[0][0]
        assert (
            default_config.retry_min_wait <= wait_time <= default_config.retry_max_wait
        ), f"Expected wait time between {default_config.retry_min_wait} and {
            default_config.retry_max_wait
        } seconds, but got {wait_time}"


@patch("forge.llm.llm.get_direct_client")
def test_guess_success_exhausts_retries(mock_get_direct_client, default_config):
    """Test the retry mechanism in guess_success exhausts retries and raises an error."""
    mock_client = MagicMock()
    mock_get_direct_client.return_value = mock_client
    
    mock_client.completion.side_effect = RateLimitError(
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
    assert mock_client.completion.call_count == default_config.num_retries
