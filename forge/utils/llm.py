"""Model discovery helpers aggregating LiteLLM, OpenRouter, Bedrock, and more."""

import warnings
from typing import Any

import httpx

with warnings.catch_warnings():
    warnings.simplefilter("ignore")
    import litellm
from forge.core.config import LLMConfig, ForgeConfig
from forge.core.logger import forge_logger as logger
from forge.llm import bedrock


def _get_openrouter_models() -> list[str]:
    """Fetch the latest OpenRouter models from their API.

    Queries the OpenRouter API for available models and prioritizes free models
    (those with $0 pricing) above paid alternatives. Falls back to a curated
    list of popular models if the API request fails.

    Returns:
        list[str]: List of OpenRouter model identifiers with free models prioritized.
            Format: "openrouter/{model-name}:free" or "openrouter/{model-name}"

    Raises:
        No exceptions raised; failures return fallback model list and log warnings.

    Example:
        >>> models = _get_openrouter_models()
        >>> print(models[0])
        "openrouter/meta-llama/llama-3.3-70b-instruct:free"

    """
    try:
        # Fetch OpenRouter models from their API
        resp = httpx.get("https://openrouter.ai/api/v1/models", timeout=10)
        if resp.status_code == 200:
            data = resp.json()
            models = []
            
            # Prioritize free models first, then paid ones
            free_models = []
            paid_models = []
            
            for model_data in data.get("data", []):
                model_id = model_data.get("id", "")
                if model_id.startswith("openrouter/"):
                    # For display, use the full model ID with openrouter/ prefix
                    pricing = model_data.get("pricing", {})
                    is_free = pricing.get("prompt") == "0" and pricing.get("completion") == "0"
                    
                    if is_free:
                        free_models.append(model_id)
                    else:
                        paid_models.append(model_id)
            
            # Return free models first, then paid models
            return sorted(free_models) + sorted(paid_models)
                    
    except Exception as e:
        logger.warning("Failed to fetch OpenRouter models from API: %s", e)
    
    # Fallback: Return curated list of popular OpenRouter models with free ones first
    return [
        # Free models (prioritized)
        "openrouter/meta-llama/llama-3.3-70b-instruct:free",
        "openrouter/google/gemini-flash-1.5:free", 
        "openrouter/microsoft/phi-3.5-mini-128k-instruct:free",
        "openrouter/tngtech/deepseek-r1t2-chimera:free",
        "openrouter/togethercomputer/llama-3.1-8b-instruct:free",
        "openrouter/meta-llama/llama-3.1-8b-instruct:free",
        "openrouter/qwen/qwen-2.5-7b-instruct:free",
        "openrouter/togethercomputer/llama-3.1-70b-instruct:free",
        
        # Popular paid models
        "openrouter/anthropic/claude-3.5-sonnet",
        "openrouter/openai/gpt-4o",
        "openrouter/openai/gpt-4o-mini",
        "openrouter/anthropic/claude-3-opus",
        "openrouter/google/gemini-pro-1.5",
        "openrouter/x-ai/grok-4",
        "openrouter/x-ai/grok-code-fast-1",
    ]


def _get_litellm_models() -> list[str]:
    """Get LiteLLM built-in models with Bedrock error models filtered.

    Retrieves the comprehensive list of models supported by LiteLLM, including
    those with pricing information. Automatically removes Bedrock models that are
    known to cause errors during initialization.

    Returns:
        list[str]: List of LiteLLM model identifiers, Bedrock error models removed.

    Raises:
        No exceptions raised; errors are logged and empty list returned.

    Example:
        >>> models = _get_litellm_models()
        >>> "gpt-4" in models
        True

    """
    try:
        litellm_model_list = litellm.model_list + list(litellm.model_cost.keys())
        models = bedrock.remove_error_modelId(litellm_model_list)
        logger.debug("Added %d LiteLLM models", len(models))
        return models
    except Exception as e:
        logger.warning("Error getting LiteLLM models: %s", e)
        return []


def _get_bedrock_models(config: ForgeConfig) -> list[str]:
    """Get AWS Bedrock models if credentials are configured.

    Connects to AWS Bedrock to retrieve available foundation models.
    Requires AWS credentials (region, access key, secret key) to be configured
    in the LLM configuration.

    Args:
        config: Forge configuration containing AWS and LLM settings

    Returns:
        list[str]: List of Bedrock model identifiers, or empty list if unconfigured

    Raises:
        No exceptions raised; AWS errors are logged and empty list returned.

    Example:
        >>> from forge.core.config import ForgeConfig
        >>> config = ForgeConfig()
        >>> models = _get_bedrock_models(config)
        >>> "anthropic.claude-v2" in models
        False  # If AWS creds not configured

    """
    llm_config: LLMConfig = config.get_llm_config()
    
    if not (llm_config.aws_region_name and 
            llm_config.aws_access_key_id and 
            llm_config.aws_secret_access_key):
        return []
    
    try:
        models = bedrock.list_foundation_models(
            llm_config.aws_region_name,
            llm_config.aws_access_key_id.get_secret_value(),
            llm_config.aws_secret_access_key.get_secret_value(),
        )
        logger.debug("Added %d Bedrock models", len(models))
        return models
    except Exception as e:
        logger.warning("Error getting Bedrock models: %s", e)
        return []


def _get_ollama_models(config: ForgeConfig) -> list[str]:
    """Get Ollama models from locally configured Ollama endpoints.

    Iterates through LLM configurations to find Ollama endpoints, then queries
    each endpoint's API for available models. Used to support local open-source
    models via Ollama.

    Args:
        config: Forge configuration containing Ollama endpoint URLs

    Returns:
        list[str]: List of Ollama model identifiers with "ollama/" prefix,
            or empty list if no Ollama endpoints are configured

    Raises:
        No exceptions raised; HTTP errors are logged and empty list returned.

    Example:
        >>> models = _get_ollama_models(config)
        >>> "ollama/llama2" in models
        False  # If Ollama not running

    """
    for llm_config in config.llms.values():
        ollama_base_url = llm_config.ollama_base_url or (
            llm_config.base_url if llm_config.model.startswith("ollama") else None
        )
        
        if not ollama_base_url:
            continue
        
        ollama_url = ollama_base_url.strip("/") + "/api/tags"
        try:
            ollama_models_list = httpx.get(ollama_url, timeout=3).json()["models"]
            models = ["ollama/" + model["name"] for model in ollama_models_list]
            logger.debug("Added %d Ollama models", len(models))
            return models
        except httpx.HTTPError as e:
            logger.error("Error getting OLLAMA models: %s", e)
    
    return []


def _get_openhands_proprietary_models() -> list[str]:
    """Get Openhands proprietary model list.
    
    Returns:
        List of Openhands proprietary model names (including legacy Forge aliases)

    """
    base_model_ids = [
        # Claude 4 series
        "claude-sonnet-4-20250514",
        "claude-opus-4-20250514",
        "claude-opus-4-1-20250805",
        # Claude 4.5 series
        "claude-sonnet-4-5-20250929",
        "claude-haiku-4-5-20251001",
        # GPT-5 series
        "gpt-5-2025-08-07",
        "gpt-5-mini-2025-08-07",
        # Gemini series
        "gemini-2.5-pro",
        # OpenAI o-series
        "o3",
        "o4-mini",
        # Devstral series
        "devstral-small-2505",
        "devstral-small-2507",
        "devstral-medium-2507",
        # Other models
        "kimi-k2-0711-preview",
        "qwen3-coder-480b",
    ]
    openhands_models = [f"Openhands/{model_id}" for model_id in base_model_ids]
    # Legacy Forge-prefixed aliases for backwards compatibility
    legacy_forge_models = [f"Forge/{model_id}" for model_id in base_model_ids]
    return openhands_models + legacy_forge_models


def _deduplicate_and_prioritize(models: list[str]) -> list[str]:
    """Remove duplicates and prioritize models by source and alphabetically.

    Deduplicates the model list while maintaining priority ordering where
    OpenRouter models (known to have good free tier support) appear first,
    followed by other providers in alphabetical order.

    Args:
        models: List of model identifiers, potentially with duplicates

    Returns:
        list[str]: Deduplicated list sorted by (non-OpenRouter, alphabetical)

    Example:
        >>> models = ["gpt-4", "openrouter/llama:free", "gpt-4", "claude-3"]
        >>> result = _deduplicate_and_prioritize(models)
        >>> result[0]
        "openrouter/llama:free"
        >>> result[1]
        "claude-3"

    """
    unique_models = []
    seen = set()
    
    # First add OpenRouter models for priority
    openrouter_models = [m for m in models if m.startswith('openrouter/') and m not in seen]
    unique_models.extend(openrouter_models)
    seen.update(openrouter_models)
    
    # Then add remaining models
    for model in models:
        if model not in seen:
            unique_models.append(model)
            seen.add(model)
    
    return sorted(unique_models, key=lambda x: (not x.startswith('openrouter/'), x))


def get_supported_llm_models(config: ForgeConfig) -> list[str]:
    """Get all models supported by LiteLLM with enhanced OpenRouter support.

    This function dynamically fetches the latest models from various sources,
    with special attention to OpenRouter free models for production use.

    Args:
        config: Forge configuration

    Returns:
        A sorted list of unique model names with free models prioritized.

    """
    # Collect models from all sources
    model_list = []
    
    # 1. LiteLLM built-in models
    model_list.extend(_get_litellm_models())
    
    # 2. OpenRouter models (prioritized)
    try:
        openrouter_models = _get_openrouter_models()
        model_list = openrouter_models + model_list  # Add at beginning for priority
        logger.debug("Added %d OpenRouter models", len(openrouter_models))
    except Exception as e:
        logger.warning("Error getting OpenRouter models: %s", e)
    
    # 3. Bedrock models
    model_list.extend(_get_bedrock_models(config))
    
    # 4. Ollama models
    model_list.extend(_get_ollama_models(config))
    
    # 5. Forge proprietary models
    model_list.extend(_get_openhands_proprietary_models())
    
    # Deduplicate and prioritize
    unique_models = _deduplicate_and_prioritize(model_list)
    
    openrouter_count = len([m for m in unique_models if m.startswith('openrouter/')])
    logger.info("Total models available: %d (including %d OpenRouter models)", 
                len(unique_models), openrouter_count)
    
    return unique_models
