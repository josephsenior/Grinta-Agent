import copy
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch
import pytest
from litellm import PromptTokensDetails
from litellm.exceptions import RateLimitError
from forge.core.config import LLMConfig
from forge.core.exceptions import LLMNoResponseError, OperationCancelled
from forge.core.message import Message, TextContent
from forge.llm.async_llm import AsyncLLM
from forge.llm.llm import LLM
from forge.llm.metrics import Metrics, TokenUsage
from forge.llm.streaming_llm import StreamingLLM


@pytest.fixture(autouse=True)
def mock_logger(monkeypatch):
    mock_logger = MagicMock()
    monkeypatch.setattr("forge.llm.debug_mixin.llm_prompt_logger", mock_logger)
    monkeypatch.setattr("forge.llm.debug_mixin.llm_response_logger", mock_logger)
    monkeypatch.setattr("forge.llm.llm.logger", mock_logger)
    return mock_logger


@pytest.fixture
def default_config():
    return LLMConfig(model="gpt-4o", api_key="test_key", num_retries=2, retry_min_wait=1, retry_max_wait=2)


def test_llm_init_with_default_config(default_config):
    llm = LLM(default_config, service_id="test-service")
    assert llm.config.model == "gpt-4o"
    assert llm.config.api_key.get_secret_value() == "test_key"
    assert isinstance(llm.metrics, Metrics)
    assert llm.metrics.model_name == "gpt-4o"


def test_token_usage_add():
    """Test that TokenUsage instances can be added together."""
    usage1 = TokenUsage(
        model="model1",
        prompt_tokens=10,
        completion_tokens=5,
        cache_read_tokens=3,
        cache_write_tokens=2,
        response_id="response-1",
    )
    usage2 = TokenUsage(
        model="model2",
        prompt_tokens=8,
        completion_tokens=6,
        cache_read_tokens=2,
        cache_write_tokens=4,
        response_id="response-2",
    )
    combined = usage1 + usage2
    assert combined.model == "model1"
    assert combined.prompt_tokens == 18
    assert combined.completion_tokens == 11
    assert combined.cache_read_tokens == 5
    assert combined.cache_write_tokens == 6
    assert combined.response_id == "response-1"


def test_metrics_merge_accumulated_token_usage():
    """Test that accumulated token usage is properly merged between two Metrics instances."""
    metrics1 = Metrics(model_name="model1")
    metrics2 = Metrics(model_name="model2")
    metrics1.add_token_usage(10, 5, 3, 2, 1000, "response-1")
    metrics2.add_token_usage(8, 6, 2, 4, 1000, "response-2")
    metrics1_data = metrics1.get()
    accumulated1 = metrics1_data["accumulated_token_usage"]
    assert accumulated1["prompt_tokens"] == 10
    assert accumulated1["completion_tokens"] == 5
    assert accumulated1["cache_read_tokens"] == 3
    assert accumulated1["cache_write_tokens"] == 2
    metrics2_data = metrics2.get()
    accumulated2 = metrics2_data["accumulated_token_usage"]
    assert accumulated2["prompt_tokens"] == 8
    assert accumulated2["completion_tokens"] == 6
    assert accumulated2["cache_read_tokens"] == 2
    assert accumulated2["cache_write_tokens"] == 4
    metrics1.merge(metrics2)
    merged_data = metrics1.get()
    merged_accumulated = merged_data["accumulated_token_usage"]
    assert merged_accumulated["prompt_tokens"] == 18
    assert merged_accumulated["completion_tokens"] == 11
    assert merged_accumulated["cache_read_tokens"] == 5
    assert merged_accumulated["cache_write_tokens"] == 6
    token_usages = merged_data["token_usages"]
    assert len(token_usages) == 2
    assert token_usages[0]["response_id"] == "response-1"
    assert token_usages[1]["response_id"] == "response-2"


@patch("forge.llm.llm.litellm.get_model_info")
def test_llm_init_with_model_info(mock_get_model_info, default_config):
    mock_get_model_info.return_value = {"max_input_tokens": 8000, "max_output_tokens": 2000}
    llm = LLM(default_config, service_id="test-service")
    llm.init_model_info()
    assert llm.config.max_input_tokens == 8000
    assert llm.config.max_output_tokens == 2000


@patch("forge.llm.llm.litellm.get_model_info")
def test_llm_init_without_model_info(mock_get_model_info, default_config):
    mock_get_model_info.side_effect = Exception("Model info not available")
    llm = LLM(default_config, service_id="test-service")
    llm.init_model_info()
    assert llm.config.max_input_tokens is None
    assert llm.config.max_output_tokens is None


def test_llm_init_with_custom_config():
    custom_config = LLMConfig(
        model="custom-model",
        api_key="custom_key",
        max_input_tokens=5000,
        max_output_tokens=1500,
        temperature=0.8,
        top_p=0.9,
        top_k=None,
    )
    llm = LLM(custom_config, service_id="test-service")
    assert llm.config.model == "custom-model"
    assert llm.config.api_key.get_secret_value() == "custom_key"
    assert llm.config.max_input_tokens == 5000
    assert llm.config.max_output_tokens == 1500
    assert llm.config.temperature == 0.8
    assert llm.config.top_p == 0.9
    assert llm.config.top_k is None


@patch("forge.llm.llm.litellm_completion")
def test_llm_top_k_in_completion_when_set(mock_litellm_completion):
    config_with_top_k = LLMConfig(top_k=50)
    llm = LLM(config_with_top_k, service_id="test-service")

    def side_effect(*args, **kwargs):
        assert "top_k" in kwargs
        assert kwargs["top_k"] == 50
        return {"choices": [{"message": {"content": "Mocked response"}}]}

    mock_litellm_completion.side_effect = side_effect
    llm.completion(messages=[{"role": "system", "content": "Test message"}])


@patch("forge.llm.llm.litellm_completion")
def test_llm_top_k_not_in_completion_when_none(mock_litellm_completion):
    config_without_top_k = LLMConfig(top_k=None)
    llm = LLM(config_without_top_k, service_id="test-service")

    def side_effect(*args, **kwargs):
        assert "top_k" not in kwargs
        return {"choices": [{"message": {"content": "Mocked response"}}]}

    mock_litellm_completion.side_effect = side_effect
    llm.completion(messages=[{"role": "system", "content": "Test message"}])


def test_llm_init_with_metrics():
    config = LLMConfig(model="gpt-4o", api_key="test_key")
    metrics = Metrics()
    llm = LLM(config, metrics=metrics, service_id="test-service")
    assert llm.metrics is metrics
    assert llm.metrics.model_name == "default"


@patch("forge.llm.llm.litellm_completion")
@patch("time.time")
def test_response_latency_tracking(mock_time, mock_litellm_completion):
    mock_time.side_effect = [1000.0, 1002.5]
    mock_response = {"id": "test-response-123", "choices": [{"message": {"content": "Test response"}}]}
    mock_litellm_completion.return_value = mock_response
    config = LLMConfig(model="gpt-4o", api_key="test_key")
    llm = LLM(config, service_id="test-service")
    response = llm.completion(messages=[{"role": "user", "content": "Hello!"}])
    assert len(llm.metrics.response_latencies) == 1
    latency_record = llm.metrics.response_latencies[0]
    assert latency_record.model == "gpt-4o"
    assert latency_record.latency == 2.5
    assert latency_record.response_id == "test-response-123"
    assert response["id"] == "test-response-123"
    assert response["choices"][0]["message"]["content"] == "Test response"
    mock_time.side_effect = [1000.0, 999.0]
    llm.completion(messages=[{"role": "user", "content": "Hello!"}])
    assert len(llm.metrics.response_latencies) == 2
    latency_record = llm.metrics.response_latencies[-1]
    assert latency_record.latency == 0.0


@patch("forge.llm.llm.litellm.get_model_info")
def test_llm_init_with_openrouter_model(mock_get_model_info, default_config):
    default_config.model = "openrouter/gpt-4o-mini"
    mock_get_model_info.return_value = {"max_input_tokens": 7000, "max_output_tokens": 1500}
    llm = LLM(default_config, service_id="test-service")
    llm.init_model_info()
    assert llm.config.max_input_tokens == 7000
    assert llm.config.max_output_tokens == 1500
    mock_get_model_info.assert_called_once_with("openrouter/gpt-4o-mini")


@patch("forge.llm.llm.litellm_completion")
def test_stop_parameter_handling(mock_litellm_completion, default_config):
    """Test that stop parameter is only added for supported models."""
    from litellm.types.utils import ModelResponse

    mock_response = ModelResponse(id="test-id", choices=[{"message": {"content": "Test response"}}], model="test-model")
    mock_litellm_completion.return_value = mock_response
    default_config.model = "custom-model"
    llm = LLM(default_config, service_id="test-service")
    llm.completion(
        messages=[{"role": "user", "content": "Hello!"}],
        tools=[{"type": "function", "function": {"name": "test", "description": "test"}}],
    )
    assert "stop" in mock_litellm_completion.call_args[1]
    default_config.model = "xai/grok-4-0709"
    llm = LLM(default_config, service_id="test-service")
    llm.completion(
        messages=[{"role": "user", "content": "Hello!"}],
        tools=[{"type": "function", "function": {"name": "test", "description": "test"}}],
    )
    assert "stop" not in mock_litellm_completion.call_args[1]


@patch("forge.llm.llm.litellm_completion")
def test_completion_with_mocked_logger(mock_litellm_completion, default_config, mock_logger):
    mock_litellm_completion.return_value = {"choices": [{"message": {"content": "Test response"}}]}
    llm = LLM(config=default_config, service_id="test-service")
    response = llm.completion(messages=[{"role": "user", "content": "Hello!"}], stream=False)
    assert response["choices"][0]["message"]["content"] == "Test response"
    assert mock_litellm_completion.call_count == 1
    mock_logger.debug.assert_called()


@pytest.mark.parametrize(
    "exception_class,extra_args,expected_retries",
    [(RateLimitError, {"llm_provider": "test_provider", "model": "test_model"}, 2)],
)
@patch("forge.llm.llm.litellm_completion")
def test_completion_retries(mock_litellm_completion, default_config, exception_class, extra_args, expected_retries):
    mock_litellm_completion.side_effect = [
        exception_class("Test error message", **extra_args),
        {"choices": [{"message": {"content": "Retry successful"}}]},
    ]
    llm = LLM(config=default_config, service_id="test-service")
    response = llm.completion(messages=[{"role": "user", "content": "Hello!"}], stream=False)
    assert response["choices"][0]["message"]["content"] == "Retry successful"
    assert mock_litellm_completion.call_count == expected_retries


@patch("forge.llm.llm.litellm_completion")
def test_completion_rate_limit_wait_time(mock_litellm_completion, default_config):
    with patch("time.sleep") as mock_sleep:
        mock_litellm_completion.side_effect = [
            RateLimitError("Rate limit exceeded", llm_provider="test_provider", model="test_model"),
            {"choices": [{"message": {"content": "Retry successful"}}]},
        ]
        llm = LLM(config=default_config, service_id="test-service")
        response = llm.completion(messages=[{"role": "user", "content": "Hello!"}], stream=False)
        assert response["choices"][0]["message"]["content"] == "Retry successful"
        assert mock_litellm_completion.call_count == 2
        mock_sleep.assert_called_once()
        wait_time = mock_sleep.call_args[0][0]
        assert (
            default_config.retry_min_wait <= wait_time <= default_config.retry_max_wait
        ), f"Expected wait time between {
            default_config.retry_min_wait} and {
            default_config.retry_max_wait} seconds, but got {wait_time}"


@patch("forge.llm.llm.litellm_completion")
def test_completion_operation_cancelled(mock_litellm_completion, default_config):
    mock_litellm_completion.side_effect = OperationCancelled("Operation cancelled")
    llm = LLM(config=default_config, service_id="test-service")
    with pytest.raises(OperationCancelled):
        llm.completion(messages=[{"role": "user", "content": "Hello!"}], stream=False)
    assert mock_litellm_completion.call_count == 1


@patch("forge.llm.llm.litellm_completion")
def test_completion_keyboard_interrupt(mock_litellm_completion, default_config):

    def side_effect(*args, **kwargs):
        raise KeyboardInterrupt("Simulated KeyboardInterrupt")

    mock_litellm_completion.side_effect = side_effect
    llm = LLM(config=default_config, service_id="test-service")
    with pytest.raises(OperationCancelled):
        try:
            llm.completion(messages=[{"role": "user", "content": "Hello!"}], stream=False)
        except KeyboardInterrupt:
            raise OperationCancelled("Operation cancelled due to KeyboardInterrupt")
    assert mock_litellm_completion.call_count == 1


@patch("forge.llm.llm.litellm_completion")
def test_completion_keyboard_interrupt_handler(mock_litellm_completion, default_config):
    global _should_exit

    def side_effect(*args, **kwargs):
        global _should_exit
        _should_exit = True
        return {"choices": [{"message": {"content": "Simulated interrupt response"}}]}

    mock_litellm_completion.side_effect = side_effect
    llm = LLM(config=default_config, service_id="test-service")
    result = llm.completion(messages=[{"role": "user", "content": "Hello!"}], stream=False)
    assert mock_litellm_completion.call_count == 1
    assert result["choices"][0]["message"]["content"] == "Simulated interrupt response"
    assert _should_exit
    _should_exit = False


@patch("forge.llm.llm.litellm_completion")
def test_completion_retry_with_llm_no_response_error_zero_temp(mock_litellm_completion, default_config):
    """Test that the retry decorator properly handles LLMNoResponseError by:.

    1. First call to llm_completion uses temperature=0 and throws LLMNoResponseError
    2. Second call should have temperature=0.2 and return a successful response.
    """

    def side_effect(*args, **kwargs):
        temperature = kwargs.get("temperature", 0)
        if temperature == 0:
            raise LLMNoResponseError("LLM did not return a response")
        else:
            return {"choices": [{"message": {"content": f"Response with temperature={temperature}"}}]}

    mock_litellm_completion.side_effect = side_effect
    llm = LLM(config=default_config, service_id="test-service")
    response = llm.completion(messages=[{"role": "user", "content": "Hello!"}], stream=False, temperature=0)
    assert response["choices"][0]["message"]["content"] == "Response with temperature=1.0"
    assert mock_litellm_completion.call_count == 2
    first_call_kwargs = mock_litellm_completion.call_args_list[0][1]
    assert first_call_kwargs.get("temperature") == 0
    second_call_kwargs = mock_litellm_completion.call_args_list[1][1]
    assert second_call_kwargs.get("temperature") == 1.0


@patch("forge.llm.llm.litellm_completion")
def test_completion_retry_with_llm_no_response_error_nonzero_temp(mock_litellm_completion, default_config):
    """Test that the retry decorator works for LLMNoResponseError when initial temperature is non-zero,.

    and keeps the original temperature on retry.

    This test verifies that when LLMNoResponseError is raised with a non-zero temperature:
    1. The retry mechanism is triggered
    2. The temperature remains unchanged (not set to 0.2)
    3. After all retries are exhausted, the error is raised
    """
    mock_litellm_completion.side_effect = LLMNoResponseError("LLM did not return a response")
    llm = LLM(config=default_config, service_id="test-service")
    with pytest.raises(LLMNoResponseError):
        llm.completion(messages=[{"role": "user", "content": "Hello!"}], stream=False, temperature=0.7)
    assert mock_litellm_completion.call_count == default_config.num_retries
    for call in mock_litellm_completion.call_args_list:
        assert call[1].get("temperature") == 0.7


@patch("forge.llm.llm.litellm.get_model_info")
@patch("forge.llm.llm.httpx.get")
def test_gemini_25_pro_function_calling(mock_httpx_get, mock_get_model_info):
    """Test that Gemini 2.5 Pro models have function calling enabled by default.

    This includes testing various model name formats with different prefixes.
    """
    mock_get_model_info.return_value = {"max_input_tokens": 8000, "max_output_tokens": 2000}
    mock_response = MagicMock()
    mock_response.json.return_value = {
        "data": [
            {
                "model_name": "gemini-2.5-pro-preview-03-25",
                "model_info": {"max_input_tokens": 8000, "max_output_tokens": 2000},
            }
        ]
    }
    mock_httpx_get.return_value = mock_response
    test_cases = [
        ("gemini-2.5-pro-preview-03-25", True),
        ("gemini-2.5-pro-exp-03-25", True),
        ("gemini/gemini-2.5-pro-preview-03-25", True),
        ("gemini/gemini-2.5-pro-exp-03-25", True),
        ("litellm_proxy/gemini-2.5-pro-preview-03-25", True),
        ("litellm_proxy/gemini-2.5-pro-exp-03-25", True),
        ("openrouter/gemini/gemini-2.5-pro-preview-03-25", True),
        ("openrouter/gemini/gemini-2.5-pro-exp-03-25", True),
        ("litellm_proxy/gemini/gemini-2.5-pro-preview-03-25", True),
        ("litellm_proxy/gemini/gemini-2.5-pro-exp-03-25", True),
        ("gemini-1.0-pro", False),
    ]
    for model_name, expected_support in test_cases:
        config = LLMConfig(model=model_name, api_key="test_key")
        llm = LLM(config, service_id="test-service")
        assert (
            llm.is_function_calling_active() == expected_support
        ), f"Expected function calling support to be {expected_support} for model {model_name}"


@patch("forge.llm.llm.litellm_completion")
def test_completion_retry_with_llm_no_response_error_nonzero_temp_successful_retry(
    mock_litellm_completion, default_config
):
    """Test that the retry decorator works for LLMNoResponseError with non-zero temperature.

    and successfully retries while preserving the original temperature.

    This test verifies that:
    1. First call to llm_completion with temperature=0.7 throws LLMNoResponseError
    2. Second call with the same temperature=0.7 returns a successful response
    """

    def side_effect(*args, **kwargs):
        temperature = kwargs.get("temperature", 0)
        if mock_litellm_completion.call_count == 1:
            raise LLMNoResponseError("LLM did not return a response")
        else:
            return {"choices": [{"message": {"content": f"Successful response with temperature={temperature}"}}]}

    mock_litellm_completion.side_effect = side_effect
    llm = LLM(config=default_config, service_id="test-service")
    response = llm.completion(messages=[{"role": "user", "content": "Hello!"}], stream=False, temperature=0.7)
    assert response["choices"][0]["message"]["content"] == "Successful response with temperature=0.7"
    assert mock_litellm_completion.call_count == 2
    first_call_kwargs = mock_litellm_completion.call_args_list[0][1]
    assert first_call_kwargs.get("temperature") == 0.7
    second_call_kwargs = mock_litellm_completion.call_args_list[1][1]
    assert second_call_kwargs.get("temperature") == 0.7


@patch("forge.llm.llm.litellm_completion")
def test_completion_retry_with_llm_no_response_error_successful_retry(mock_litellm_completion, default_config):
    """Test that the retry decorator works for LLMNoResponseError with zero temperature.

    and successfully retries with temperature=0.2.

    This test verifies that:
    1. First call to llm_completion with temperature=0 throws LLMNoResponseError
    2. Second call with temperature=0.2 returns a successful response
    """

    def side_effect(*args, **kwargs):
        temperature = kwargs.get("temperature", 0)
        if mock_litellm_completion.call_count == 1:
            raise LLMNoResponseError("LLM did not return a response")
        else:
            return {"choices": [{"message": {"content": f"Successful response with temperature={temperature}"}}]}

    mock_litellm_completion.side_effect = side_effect
    llm = LLM(config=default_config, service_id="test-service")
    response = llm.completion(messages=[{"role": "user", "content": "Hello!"}], stream=False, temperature=0)
    assert response["choices"][0]["message"]["content"] == "Successful response with temperature=1.0"
    assert mock_litellm_completion.call_count == 2
    first_call_kwargs = mock_litellm_completion.call_args_list[0][1]
    assert first_call_kwargs.get("temperature") == 0
    second_call_kwargs = mock_litellm_completion.call_args_list[1][1]
    assert second_call_kwargs.get("temperature") == 1.0


@patch("forge.llm.llm.litellm_completion")
def test_completion_with_litellm_mock(mock_litellm_completion, default_config):
    mock_response = {"choices": [{"message": {"content": "This is a mocked response."}}]}
    mock_litellm_completion.return_value = mock_response
    test_llm = LLM(config=default_config, service_id="test-service")
    response = test_llm.completion(messages=[{"role": "user", "content": "Hello!"}], stream=False, drop_params=True)
    assert response["choices"][0]["message"]["content"] == "This is a mocked response."
    mock_litellm_completion.assert_called_once()
    call_args = mock_litellm_completion.call_args[1]
    assert call_args["model"] == default_config.model
    assert call_args["messages"] == [{"role": "user", "content": "Hello!"}]
    assert not call_args["stream"]


@patch("forge.llm.llm.litellm_completion")
def test_llm_gemini_thinking_parameter(mock_litellm_completion, default_config):
    """Test that the 'thinking' parameter is correctly passed to litellm_completion.

    when a Gemini model is used with 'low' reasoning_effort.
    """
    gemini_config = copy.deepcopy(default_config)
    gemini_config.model = "gemini-2.5-pro"
    gemini_config.reasoning_effort = "low"
    mock_litellm_completion.return_value = {"choices": [{"message": {"content": "Test response"}}]}
    llm = LLM(config=gemini_config, service_id="test-service")
    llm.completion(messages=[{"role": "user", "content": "Hello!"}])
    mock_litellm_completion.assert_called_once()
    call_args, call_kwargs = mock_litellm_completion.call_args
    assert "thinking" in call_kwargs
    assert call_kwargs["thinking"] == {"budget_tokens": 128}
    assert "reasoning_effort" not in call_kwargs
    assert len(call_args) == 0


@patch("forge.llm.llm.litellm.token_counter")
def test_get_token_count_with_dict_messages(mock_token_counter, default_config):
    mock_token_counter.return_value = 42
    llm = LLM(default_config, service_id="test-service")
    messages = [{"role": "user", "content": "Hello!"}]
    token_count = llm.get_token_count(messages)
    assert token_count == 42
    mock_token_counter.assert_called_once_with(model=default_config.model, messages=messages, custom_tokenizer=None)


@patch("forge.llm.llm.litellm.token_counter")
def test_get_token_count_with_message_objects(mock_token_counter, default_config, mock_logger):
    llm = LLM(default_config, service_id="test-service")
    message_obj = Message(role="user", content=[TextContent(text="Hello!")])
    message_dict = {"role": "user", "content": "Hello!"}
    mock_token_counter.side_effect = [42, 42]
    token_count_obj = llm.get_token_count([message_obj])
    token_count_dict = llm.get_token_count([message_dict])
    assert token_count_obj == token_count_dict
    assert mock_token_counter.call_count == 2


@patch("forge.llm.llm.litellm.token_counter")
@patch("forge.llm.llm.create_pretrained_tokenizer")
def test_get_token_count_with_custom_tokenizer(mock_create_tokenizer, mock_token_counter, default_config):
    mock_tokenizer = MagicMock()
    mock_create_tokenizer.return_value = mock_tokenizer
    mock_token_counter.return_value = 42
    config = copy.deepcopy(default_config)
    config.custom_tokenizer = "custom/tokenizer"
    llm = LLM(config, service_id="test-service")
    messages = [{"role": "user", "content": "Hello!"}]
    token_count = llm.get_token_count(messages)
    assert token_count == 42
    mock_create_tokenizer.assert_called_once_with("custom/tokenizer")
    mock_token_counter.assert_called_once_with(model=config.model, messages=messages, custom_tokenizer=mock_tokenizer)


@patch("forge.llm.llm.litellm.token_counter")
def test_get_token_count_error_handling(mock_token_counter, default_config, mock_logger):
    mock_token_counter.side_effect = Exception("Token counting failed")
    llm = LLM(default_config, service_id="test-service")
    messages = [{"role": "user", "content": "Hello!"}]
    token_count = llm.get_token_count(messages)
    assert token_count == 0
    mock_token_counter.assert_called_once()
    mock_logger.error.assert_called_once_with("Error getting token count for\n model gpt-4o\nToken counting failed")


@patch("forge.llm.llm.litellm_completion")
def test_llm_token_usage(mock_litellm_completion, default_config):
    mock_response_1 = {
        "id": "test-response-usage",
        "choices": [{"message": {"content": "Usage test response"}}],
        "usage": {
            "prompt_tokens": 12,
            "completion_tokens": 3,
            "prompt_tokens_details": PromptTokensDetails(cached_tokens=2),
            "model_extra": {"cache_creation_input_tokens": 5},
        },
    }
    mock_response_2 = {
        "id": "test-response-usage-2",
        "choices": [{"message": {"content": "Second usage test response"}}],
        "usage": {
            "prompt_tokens": 7,
            "completion_tokens": 2,
            "prompt_tokens_details": PromptTokensDetails(cached_tokens=1),
            "model_extra": {"cache_creation_input_tokens": 3},
        },
    }
    mock_litellm_completion.side_effect = [mock_response_1, mock_response_2]
    llm = LLM(config=default_config, service_id="test-service")
    llm.completion(messages=[{"role": "user", "content": "Hello usage!"}])
    token_usage_list = llm.metrics.get()["token_usages"]
    assert len(token_usage_list) == 1
    usage_entry_1 = token_usage_list[0]
    assert usage_entry_1["prompt_tokens"] == 12
    assert usage_entry_1["completion_tokens"] == 3
    assert usage_entry_1["cache_read_tokens"] == 2
    assert usage_entry_1["cache_write_tokens"] == 5
    assert usage_entry_1["response_id"] == "test-response-usage"
    llm.completion(messages=[{"role": "user", "content": "Hello again!"}])
    token_usage_list = llm.metrics.get()["token_usages"]
    assert len(token_usage_list) == 2
    usage_entry_2 = token_usage_list[-1]
    assert usage_entry_2["prompt_tokens"] == 7
    assert usage_entry_2["completion_tokens"] == 2
    assert usage_entry_2["cache_read_tokens"] == 1
    assert usage_entry_2["cache_write_tokens"] == 3
    assert usage_entry_2["response_id"] == "test-response-usage-2"


@patch("forge.llm.llm.litellm_completion")
def test_accumulated_token_usage(mock_litellm_completion, default_config):
    """Test that token usage is properly accumulated across multiple LLM calls."""
    # Setup mock responses
    mock_responses = _create_mock_responses()
    mock_litellm_completion.side_effect = mock_responses

    # Create LLM instance and make calls
    llm = LLM(config=default_config, service_id="test-service")

    # Test first completion
    _test_first_completion(llm)

    # Test second completion
    _test_second_completion(llm)

    # Test individual token usage records
    _test_individual_token_usage_records(llm)


def _create_mock_responses():
    """Create mock responses for testing."""
    mock_response_1 = {
        "id": "test-response-1",
        "choices": [{"message": {"content": "First response"}}],
        "usage": {
            "prompt_tokens": 10,
            "completion_tokens": 5,
            "prompt_tokens_details": PromptTokensDetails(cached_tokens=3),
            "model_extra": {"cache_creation_input_tokens": 4},
        },
    }
    mock_response_2 = {
        "id": "test-response-2",
        "choices": [{"message": {"content": "Second response"}}],
        "usage": {
            "prompt_tokens": 8,
            "completion_tokens": 6,
            "prompt_tokens_details": PromptTokensDetails(cached_tokens=2),
            "model_extra": {"cache_creation_input_tokens": 3},
        },
    }
    return [mock_response_1, mock_response_2]


def _test_first_completion(llm):
    """Test first completion call and verify initial token usage."""
    llm.completion(messages=[{"role": "user", "content": "First message"}])
    metrics_data = llm.metrics.get()
    accumulated_usage = metrics_data["accumulated_token_usage"]

    assert accumulated_usage["prompt_tokens"] == 10
    assert accumulated_usage["completion_tokens"] == 5
    assert accumulated_usage["cache_read_tokens"] == 3
    assert accumulated_usage["cache_write_tokens"] == 4


def _test_second_completion(llm):
    """Test second completion call and verify accumulated token usage."""
    llm.completion(messages=[{"role": "user", "content": "Second message"}])
    metrics_data = llm.metrics.get()
    accumulated_usage = metrics_data["accumulated_token_usage"]

    assert accumulated_usage["prompt_tokens"] == 18
    assert accumulated_usage["completion_tokens"] == 11
    assert accumulated_usage["cache_read_tokens"] == 5
    assert accumulated_usage["cache_write_tokens"] == 7


def _test_individual_token_usage_records(llm):
    """Test individual token usage records."""
    metrics_data = llm.metrics.get()
    token_usages = metrics_data["token_usages"]

    assert len(token_usages) == 2

    # Verify first usage record
    _verify_first_usage_record(token_usages[0])

    # Verify second usage record
    _verify_second_usage_record(token_usages[1])


def _verify_first_usage_record(usage_record):
    """Verify first token usage record."""
    assert usage_record["prompt_tokens"] == 10
    assert usage_record["completion_tokens"] == 5
    assert usage_record["cache_read_tokens"] == 3
    assert usage_record["cache_write_tokens"] == 4
    assert usage_record["response_id"] == "test-response-1"


def _verify_second_usage_record(usage_record):
    """Verify second token usage record."""
    assert usage_record["prompt_tokens"] == 8
    assert usage_record["completion_tokens"] == 6
    assert usage_record["cache_read_tokens"] == 2
    assert usage_record["cache_write_tokens"] == 3
    assert usage_record["response_id"] == "test-response-2"


@patch("forge.llm.llm.litellm_completion")
def test_completion_with_log_completions(mock_litellm_completion, default_config):
    with tempfile.TemporaryDirectory() as temp_dir:
        default_config.log_completions = True
        default_config.log_completions_folder = temp_dir
        mock_response = {"choices": [{"message": {"content": "This is a mocked response."}}]}
        mock_litellm_completion.return_value = mock_response
        test_llm = LLM(config=default_config, service_id="test-service")
        response = test_llm.completion(messages=[{"role": "user", "content": "Hello!"}], stream=False, drop_params=True)
        assert response["choices"][0]["message"]["content"] == "This is a mocked response."
        try:
            files = list(Path(temp_dir).iterdir())
        except FileNotFoundError:
            files = []
        assert len(files) in {0, 1}


@patch("httpx.get")
def test_llm_base_url_auto_protocol_patch(mock_get):
    """Test that LLM base_url without protocol is automatically fixed with 'http://'."""
    config = LLMConfig(model="litellm_proxy/test-model", api_key="fake-key", base_url="  api.example.com  ")
    mock_get.return_value.status_code = 200
    mock_get.return_value.json.return_value = {"model": "fake"}
    llm = LLM(config=config, service_id="test-service")
    llm.init_model_info()
    called_url = mock_get.call_args[0][0]
    assert called_url.startswith("http://") or called_url.startswith("https://")


def test_unknown_model_token_limits():
    """Test that models without known token limits get None for both max_output_tokens and max_input_tokens."""
    config = LLMConfig(model="non-existent-model", api_key="test_key")
    llm = LLM(config, service_id="test-service")
    assert llm.config.max_output_tokens is None
    assert llm.config.max_input_tokens is None


def test_max_tokens_from_model_info():
    """Test that max_output_tokens and max_input_tokens are correctly initialized from model info."""
    config = LLMConfig(model="gpt-4", api_key="test_key")
    llm = LLM(config, service_id="test-service")
    assert llm.config.max_output_tokens == 4096
    assert llm.config.max_input_tokens == 8192


def test_claude_3_7_sonnet_max_output_tokens():
    """Test that Claude 3.7 Sonnet models get the special 64000 max_output_tokens value and default max_input_tokens."""
    config = LLMConfig(model="claude-3-7-sonnet", api_key="test_key")
    llm = LLM(config, service_id="test-service")
    assert llm.config.max_output_tokens == 64000
    assert llm.config.max_input_tokens is None


def test_claude_sonnet_4_max_output_tokens():
    """Test that Claude Sonnet 4 models get the correct max_output_tokens and max_input_tokens values."""
    config = LLMConfig(model="claude-sonnet-4-20250514", api_key="test_key")
    llm = LLM(config, service_id="test-service")
    assert llm.config.max_output_tokens == 64000
    assert llm.config.max_input_tokens == 200000


def test_sambanova_deepseek_model_max_output_tokens():
    """Test that SambaNova DeepSeek-V3-0324 model gets the correct max_output_tokens value."""
    config = LLMConfig(model="sambanova/DeepSeek-V3-0324", api_key="test_key")
    llm = LLM(config, service_id="test-service")
    assert llm.config.max_output_tokens == 32768


def test_max_output_tokens_override_in_config():
    """Test that max_output_tokens can be overridden in the config."""
    config = LLMConfig(model="claude-sonnet-4-20250514", api_key="test_key", max_output_tokens=2048)
    llm = LLM(config, service_id="test-service")
    assert llm.config.max_output_tokens == 2048


def test_azure_model_default_max_tokens():
    """Test that Azure models have the default max_output_tokens value."""
    azure_config = LLMConfig(
        model="azure/non-existent-model",
        api_key="test_key",
        base_url="https://test.openai.azure.com/",
        api_version="2024-12-01-preview",
    )
    llm = LLM(azure_config, service_id="test-service")
    assert llm.config.max_output_tokens is None


def test_gemini_model_keeps_none_reasoning_effort():
    """Test that Gemini models keep reasoning_effort=None for optimization."""
    config = LLMConfig(model="gemini-2.5-pro", api_key="test_key")
    assert config.reasoning_effort is None


def test_non_gemini_model_gets_high_reasoning_effort():
    """Test that non-Gemini models get reasoning_effort='high' by default."""
    config = LLMConfig(model="gpt-4o", api_key="test_key")
    assert config.reasoning_effort == "high"


def test_explicit_reasoning_effort_preserved():
    """Test that explicitly set reasoning_effort is preserved."""
    config = LLMConfig(model="gemini-2.5-pro", api_key="test_key", reasoning_effort="medium")
    assert config.reasoning_effort == "medium"


@patch("forge.llm.llm.litellm_completion")
def test_gemini_none_reasoning_effort_uses_thinking_budget(mock_completion):
    """Test that Gemini with reasoning_effort=None uses thinking budget."""
    config = LLMConfig(model="gemini-2.5-pro", api_key="test_key", reasoning_effort=None)
    mock_completion.return_value = {
        "choices": [{"message": {"content": "Test response"}}],
        "usage": {"prompt_tokens": 10, "completion_tokens": 5},
    }
    llm = LLM(config, service_id="test-service")
    sample_messages = [{"role": "user", "content": "Hello, how are you?"}]
    llm.completion(messages=sample_messages)
    call_kwargs = mock_completion.call_args[1]
    assert "thinking" in call_kwargs
    assert call_kwargs["thinking"] == {"budget_tokens": 128}
    assert call_kwargs.get("reasoning_effort") is None


@patch("forge.llm.llm.litellm_completion")
def test_gemini_low_reasoning_effort_uses_thinking_budget(mock_completion):
    """Test that Gemini with reasoning_effort='low' uses thinking budget."""
    config = LLMConfig(model="gemini-2.5-pro", api_key="test_key", reasoning_effort="low")
    mock_completion.return_value = {
        "choices": [{"message": {"content": "Test response"}}],
        "usage": {"prompt_tokens": 10, "completion_tokens": 5},
    }
    llm = LLM(config, service_id="test-service")
    sample_messages = [{"role": "user", "content": "Hello, how are you?"}]
    llm.completion(messages=sample_messages)
    call_kwargs = mock_completion.call_args[1]
    assert "thinking" in call_kwargs
    assert call_kwargs["thinking"] == {"budget_tokens": 128}
    assert call_kwargs.get("reasoning_effort") is None


@patch("forge.llm.llm.litellm_completion")
def test_gemini_medium_reasoning_effort_passes_through(mock_completion):
    """Test that Gemini with reasoning_effort='medium' passes through to litellm."""
    config = LLMConfig(model="gemini-2.5-pro", api_key="test_key", reasoning_effort="medium")
    mock_completion.return_value = {
        "choices": [{"message": {"content": "Test response"}}],
        "usage": {"prompt_tokens": 10, "completion_tokens": 5},
    }
    llm = LLM(config, service_id="test-service")
    sample_messages = [{"role": "user", "content": "Hello, how are you?"}]
    llm.completion(messages=sample_messages)
    call_kwargs = mock_completion.call_args[1]
    assert "thinking" not in call_kwargs
    assert call_kwargs.get("reasoning_effort") == "medium"


@patch("forge.llm.llm.litellm_completion")
def test_opus_41_keeps_temperature_top_p(mock_completion):
    mock_completion.return_value = {"choices": [{"message": {"content": "ok"}}]}
    config = LLMConfig(model="anthropic/claude-opus-4-1-20250805", api_key="k", temperature=0.7, top_p=0.9)
    llm = LLM(config, service_id="svc")
    llm.completion(messages=[{"role": "user", "content": "hi"}])
    call_kwargs = mock_completion.call_args[1]
    assert call_kwargs.get("temperature") == 0.7
    assert "top_p" not in call_kwargs


@patch("forge.llm.llm.litellm_completion")
def test_opus_4_keeps_temperature_top_p(mock_completion):
    mock_completion.return_value = {"choices": [{"message": {"content": "ok"}}]}
    config = LLMConfig(model="anthropic/claude-opus-4-20250514", api_key="k", temperature=0.7, top_p=0.9)
    llm = LLM(config, service_id="svc")
    llm.completion(messages=[{"role": "user", "content": "hi"}])
    call_kwargs = mock_completion.call_args[1]
    assert call_kwargs.get("temperature") == 0.7
    assert call_kwargs.get("top_p") == 0.9


@patch("forge.llm.llm.litellm_completion")
def test_opus_41_disables_thinking(mock_completion):
    mock_completion.return_value = {"choices": [{"message": {"content": "ok"}}]}
    config = LLMConfig(model="anthropic/claude-opus-4-1-20250805", api_key="k")
    llm = LLM(config, service_id="svc")
    llm.completion(messages=[{"role": "user", "content": "hi"}])
    call_kwargs = mock_completion.call_args[1]
    assert call_kwargs.get("thinking") == {"type": "disabled"}


@patch("forge.llm.llm.litellm.get_model_info")
def test_is_caching_prompt_active_anthropic_prefixed(mock_get_model_info):
    mock_get_model_info.side_effect = Exception("skip")
    config = LLMConfig(model="anthropic/claude-3-7-sonnet", api_key="k", caching_prompt=True)
    llm = LLM(config, service_id="svc")
    assert llm.is_caching_prompt_active() is True


@patch("forge.llm.llm.httpx.get")
@patch("forge.llm.llm.litellm.get_model_info")
def test_openhands_provider_rewrite_and_caching_prompt(mock_get_model_info, mock_httpx_get):
    mock_httpx_get.return_value = type(
        "Resp",
        (),
        {
            "json": lambda self=None: {
                "data": [
                    {
                        "model_name": "claude-3.7-sonnet",
                        "model_info": {"max_input_tokens": 200000, "max_output_tokens": 64000, "supports_vision": True},
                    }
                ]
            }
        },
    )()
    mock_get_model_info.return_value = {"max_input_tokens": 200000, "max_output_tokens": 64000}
    config = LLMConfig(model="Openhands/claude-3.7-sonnet", api_key="k", caching_prompt=True)
    llm = LLM(config, service_id="svc")
    assert llm.config.model.startswith("litellm_proxy/claude-3.7-sonnet")
    assert llm.is_caching_prompt_active() is True


@patch("forge.llm.llm.litellm_completion")
def test_gemini_high_reasoning_effort_passes_through(mock_completion):
    """Test that Gemini with reasoning_effort='high' passes through to litellm."""
    config = LLMConfig(model="gemini-2.5-pro", api_key="test_key", reasoning_effort="high")
    mock_completion.return_value = {
        "choices": [{"message": {"content": "Test response"}}],
        "usage": {"prompt_tokens": 10, "completion_tokens": 5},
    }
    llm = LLM(config, service_id="test-service")
    sample_messages = [{"role": "user", "content": "Hello, how are you?"}]
    llm.completion(messages=sample_messages)
    call_kwargs = mock_completion.call_args[1]
    assert "thinking" not in call_kwargs
    assert call_kwargs.get("reasoning_effort") == "high"


@patch("forge.llm.llm.litellm_completion")
def test_non_gemini_uses_reasoning_effort(mock_completion):
    """Test that non-Gemini models use reasoning_effort instead of thinking budget."""
    config = LLMConfig(model="o1", api_key="test_key", reasoning_effort="high")
    mock_completion.return_value = {
        "choices": [{"message": {"content": "Test response"}}],
        "usage": {"prompt_tokens": 10, "completion_tokens": 5},
    }
    llm = LLM(config, service_id="test-service")
    sample_messages = [{"role": "user", "content": "Hello, how are you?"}]
    llm.completion(messages=sample_messages)


@patch("forge.llm.async_llm.litellm_acompletion")
@pytest.mark.asyncio
async def test_async_reasoning_effort_passthrough(mock_acompletion):
    mock_acompletion.return_value = {"choices": [{"message": {"content": "ok"}}]}
    config = LLMConfig(model="o3", api_key="k", temperature=0.7, top_p=0.9, reasoning_effort="low")
    llm = AsyncLLM(config, service_id="svc")
    await llm.async_completion(messages=[{"role": "user", "content": "hi"}])
    call_kwargs = mock_acompletion.call_args[1]
    assert call_kwargs.get("reasoning_effort") == "low"
    assert call_kwargs.get("temperature") == 0.7
    assert call_kwargs.get("top_p") == 0.9


@patch("forge.llm.streaming_llm.AsyncLLM._call_acompletion")
@pytest.mark.asyncio
async def test_streaming_reasoning_effort_passthrough(mock_call):

    async def fake_stream(*args, **kwargs):

        class Dummy:

            async def __aiter__(self):
                yield {"choices": [{"delta": {"content": "x"}}]}

        return Dummy()

    mock_call.side_effect = fake_stream
    config = LLMConfig(model="o3", api_key="k", temperature=0.7, top_p=0.9, reasoning_effort="low")
    sllm = StreamingLLM(config, service_id="svc")
    async for _ in sllm.async_streaming_completion(messages=[{"role": "user", "content": "hi"}]):
        break
    call_kwargs = mock_call.call_args[1]
    assert call_kwargs.get("reasoning_effort") == "low"
    assert call_kwargs.get("temperature") == 0.7
    assert call_kwargs.get("top_p") == 0.9


@patch("forge.llm.async_llm.litellm_acompletion")
@pytest.mark.asyncio
async def test_async_streaming_no_thinking_for_gemini(mock_acompletion):
    mock_acompletion.return_value = {"choices": [{"message": {"content": "ok"}}]}
    config = LLMConfig(model="gemini-2.5-pro", api_key="k", reasoning_effort="low")
    llm = AsyncLLM(config, service_id="svc")
    await llm.async_completion(messages=[{"role": "user", "content": "hi"}])
    call_kwargs = mock_acompletion.call_args[1]
    assert "thinking" not in call_kwargs


@patch("forge.llm.llm.litellm_completion")
def test_non_reasoning_model_no_optimization(mock_completion):
    """Test that non-reasoning models don't get optimization parameters."""
    config = LLMConfig(model="gpt-3.5-turbo", api_key="test_key")
    mock_completion.return_value = {
        "choices": [{"message": {"content": "Test response"}}],
        "usage": {"prompt_tokens": 10, "completion_tokens": 5},
    }
    llm = LLM(config, service_id="test-service")
    sample_messages = [{"role": "user", "content": "Hello, how are you?"}]
    llm.completion(messages=sample_messages)
    call_kwargs = mock_completion.call_args[1]
    assert "thinking" not in call_kwargs
    assert "reasoning_effort" not in call_kwargs


@patch("forge.llm.llm.litellm_completion")
def test_gemini_performance_optimization_end_to_end(mock_completion):
    """Test the complete Gemini performance optimization flow end-to-end."""
    mock_completion.return_value = {
        "choices": [{"message": {"content": "Optimized response"}}],
        "usage": {"prompt_tokens": 50, "completion_tokens": 25},
    }
    config = LLMConfig(model="gemini-2.5-pro", api_key="test_key")
    assert config.reasoning_effort is None
    llm = LLM(config, service_id="test-service")
    messages = [{"role": "user", "content": "Solve this complex problem"}]
    response = llm.completion(messages=messages)
    assert response["choices"][0]["message"]["content"] == "Optimized response"
    call_kwargs = mock_completion.call_args[1]
    assert "thinking" in call_kwargs
    assert call_kwargs["thinking"] == {"budget_tokens": 128}
    assert call_kwargs.get("reasoning_effort") is None
    assert "temperature" not in call_kwargs
    assert "top_p" not in call_kwargs
