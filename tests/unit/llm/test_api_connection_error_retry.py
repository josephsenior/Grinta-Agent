from unittest.mock import patch
import pytest
from litellm.exceptions import APIConnectionError
from forge.core.config import LLMConfig
from forge.llm.llm import LLM


@pytest.fixture
def default_config():
    return LLMConfig(model="gpt-4o", api_key="test_key", num_retries=2, retry_min_wait=1, retry_max_wait=2)


@patch("forge.llm.llm.litellm_completion")
def test_completion_retries_api_connection_error(mock_litellm_completion, default_config):
    """Test that APIConnectionError is properly retried."""
    mock_litellm_completion.side_effect = [
        APIConnectionError(message="API connection error", llm_provider="test_provider", model="test_model"),
        {"choices": [{"message": {"content": "Retry successful"}}]},
    ]
    llm = LLM(config=default_config, service_id="test-service")
    response = llm.completion(messages=[{"role": "user", "content": "Hello!"}], stream=False)
    assert response["choices"][0]["message"]["content"] == "Retry successful"
    assert mock_litellm_completion.call_count == 2


@patch("forge.llm.llm.litellm_completion")
def test_completion_max_retries_api_connection_error(mock_litellm_completion, default_config):
    """Test that APIConnectionError respects max retries."""
    mock_litellm_completion.side_effect = [
        APIConnectionError(message="API connection error 1", llm_provider="test_provider", model="test_model"),
        APIConnectionError(message="API connection error 2", llm_provider="test_provider", model="test_model"),
        APIConnectionError(message="API connection error 3", llm_provider="test_provider", model="test_model"),
    ]
    llm = LLM(config=default_config, service_id="test-service")
    with pytest.raises(APIConnectionError) as excinfo:
        llm.completion(messages=[{"role": "user", "content": "Hello!"}], stream=False)
    assert mock_litellm_completion.call_count == default_config.num_retries
    assert "API connection error" in str(excinfo.value)
