from unittest.mock import patch, MagicMock
import pytest
from forge.llm.exceptions import APIConnectionError
from pydantic import SecretStr
from forge.core.config import LLMConfig
from forge.llm.llm import LLM
from forge.llm.direct_clients import LLMResponse


@pytest.fixture
def default_config():
    return LLMConfig(
        model="gpt-4o",
        api_key=SecretStr("test_key"),
        num_retries=2,
        retry_min_wait=1,
        retry_max_wait=2,
    )


@patch("forge.llm.llm.get_direct_client")
def test_completion_retries_api_connection_error(
    mock_get_direct_client, default_config
):
    """Test that APIConnectionError is properly retried."""
    mock_client = MagicMock()
    mock_get_direct_client.return_value = mock_client
    
    mock_client.completion.side_effect = [
        APIConnectionError("API connection error"),
        LLMResponse(
            content="Retry successful",
            model="gpt-4o",
            usage={}
        ),
    ]
    llm = LLM(config=default_config, service_id="test-service")
    response = llm.completion(
        messages=[{"role": "user", "content": "Hello!"}], stream=False
    )
    assert response["choices"][0]["message"]["content"] == "Retry successful"
    assert mock_client.completion.call_count == 2


@patch("forge.llm.llm.get_direct_client")
def test_completion_max_retries_api_connection_error(
    mock_get_direct_client, default_config
):
    """Test that APIConnectionError respects max retries."""
    mock_client = MagicMock()
    mock_get_direct_client.return_value = mock_client
    
    mock_client.completion.side_effect = [
        APIConnectionError("API connection error 1"),
        APIConnectionError("API connection error 2"),
        APIConnectionError("API connection error 3"),
    ]
    llm = LLM(config=default_config, service_id="test-service")
    with pytest.raises(APIConnectionError) as excinfo:
        llm.completion(messages=[{"role": "user", "content": "Hello!"}], stream=False)
    assert mock_client.completion.call_count == default_config.num_retries
    assert "API connection error" in str(excinfo.value)
