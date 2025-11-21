from __future__ import annotations

import importlib
import sys
import types
from typing import Any

from pydantic import BaseModel

if "litellm" not in sys.modules:
    _litellm_module = types.ModuleType("litellm")

    class _LiteLLMModelResponse(BaseModel):
        model: str | None = None
        choices: list[Any] = []

    class _LiteLLMModelInfo(BaseModel):
        model: str | None = None

    class _LiteLLMPromptTokensDetails(BaseModel):
        prompt_name: str | None = None

    class _LiteLLMChatCompletionToolParam(BaseModel):
        function: dict[str, Any] = {}

    class _LiteLLMCostPerToken(BaseModel):
        cost: float = 0.0

    class _LiteLLMUsage(BaseModel):
        total_tokens: int = 0

    _litellm_module.ModelResponse = _LiteLLMModelResponse
    _litellm_module.ModelInfo = _LiteLLMModelInfo
    _litellm_module.PromptTokensDetails = _LiteLLMPromptTokensDetails
    _litellm_module.ChatCompletionToolParam = _LiteLLMChatCompletionToolParam
    _litellm_module.CostPerToken = _LiteLLMCostPerToken
    _litellm_module.Usage = _LiteLLMUsage
    _litellm_module.APIConnectionError = RuntimeError
    _litellm_module.APIError = RuntimeError
    _litellm_module.AuthenticationError = RuntimeError
    _litellm_module.BadRequestError = RuntimeError
    _litellm_module.ContentPolicyViolationError = RuntimeError
    _litellm_module.ContextWindowExceededError = RuntimeError
    _litellm_module.InternalServerError = RuntimeError
    _litellm_module.NotFoundError = RuntimeError
    _litellm_module.OpenAIError = RuntimeError
    _litellm_module.RateLimitError = RuntimeError
    _litellm_module.ServiceUnavailableError = RuntimeError
    _litellm_module.Timeout = RuntimeError
    _litellm_module.acompletion = lambda *args, **kwargs: None
    _litellm_module.completion = lambda *args, **kwargs: None
    _litellm_module.completion_cost = lambda *args, **kwargs: 0
    _litellm_module.suppress_debug_info = True
    _litellm_module.set_verbose = False
    _litellm_utils = types.ModuleType("litellm.utils")
    _litellm_utils.create_pretrained_tokenizer = lambda *args, **kwargs: None
    _litellm_utils.get_model_info = lambda *args, **kwargs: {}
    _litellm_exceptions = types.ModuleType("litellm.exceptions")
    for _name, _exc in {
        "APIConnectionError": RuntimeError,
        "APIError": RuntimeError,
        "AuthenticationError": RuntimeError,
        "BadRequestError": RuntimeError,
        "ContentPolicyViolationError": RuntimeError,
        "ContextWindowExceededError": RuntimeError,
        "InternalServerError": RuntimeError,
        "NotFoundError": RuntimeError,
        "OpenAIError": RuntimeError,
        "RateLimitError": RuntimeError,
        "ServiceUnavailableError": RuntimeError,
        "Timeout": RuntimeError,
    }.items():
        setattr(_litellm_exceptions, _name, _exc)
    _litellm_types_utils = types.ModuleType("litellm.types.utils")
    _litellm_types_utils.CostPerToken = _litellm_module.CostPerToken
    _litellm_types_utils.ModelResponse = _litellm_module.ModelResponse
    _litellm_types_utils.Usage = _litellm_module.Usage
    _litellm_module.utils = _litellm_utils
    _litellm_module.exceptions = _litellm_exceptions
    _litellm_module.create_pretrained_tokenizer = (
        _litellm_utils.create_pretrained_tokenizer
    )
    _litellm_module.get_model_info = _litellm_utils.get_model_info
    sys.modules["litellm"] = _litellm_module
    sys.modules["litellm.utils"] = _litellm_utils
    sys.modules["litellm.exceptions"] = _litellm_exceptions
    sys.modules["litellm.types.utils"] = _litellm_types_utils
if "tokenizers" not in sys.modules:
    sys.modules["tokenizers"] = types.ModuleType("tokenizers")


def test_download_module_importable():
    module = importlib.import_module("forge.core.download")
    assert module.__doc__ is not None
