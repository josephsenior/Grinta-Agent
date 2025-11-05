import warnings
from typing import Any

import httpx

with warnings.catch_warnings():
    warnings.simplefilter("ignore")
    import litellm
from openhands.core.config import LLMConfig, OpenHandsConfig
from openhands.core.logger import openhands_logger as logger
from openhands.llm import bedrock


def _get_openrouter_models() -> list[str]:
    """Fetch the latest OpenRouter models from their API.
    
    Returns:
        list[str]: List of OpenRouter model names, with free models prioritized.
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


def get_supported_llm_models(config: OpenHandsConfig) -> list[str]:
    """Get all models supported by LiteLLM with enhanced OpenRouter support.

    This function dynamically fetches the latest models from various sources,
    with special attention to OpenRouter free models for production use.

    Returns:
        list[str]: A sorted list of unique model names with free models prioritized.
    """
    model_list = []
    
    # 1. Get LiteLLM built-in models
    try:
        # Use the latest LiteLLM model list
        litellm_model_list = litellm.model_list + list(litellm.model_cost.keys())
        litellm_model_list_without_bedrock = bedrock.remove_error_modelId(litellm_model_list)
        model_list.extend(litellm_model_list_without_bedrock)
        logger.debug("Added %d LiteLLM models", len(litellm_model_list_without_bedrock))
    except Exception as e:
        logger.warning("Error getting LiteLLM models: %s", e)
    
    # 2. Get OpenRouter models dynamically (prioritized)
    try:
        openrouter_models = _get_openrouter_models()
        # Add OpenRouter models at the beginning for priority
        model_list = openrouter_models + model_list
        logger.debug("Added %d OpenRouter models", len(openrouter_models))
    except Exception as e:
        logger.warning("Error getting OpenRouter models: %s", e)
    
    # 3. Get Bedrock models if credentials are available
    llm_config: LLMConfig = config.get_llm_config()
    if (llm_config.aws_region_name and 
        llm_config.aws_access_key_id and 
        llm_config.aws_secret_access_key):
        try:
            bedrock_model_list = bedrock.list_foundation_models(
                llm_config.aws_region_name,
                llm_config.aws_access_key_id.get_secret_value(),
                llm_config.aws_secret_access_key.get_secret_value(),
            )
            model_list.extend(bedrock_model_list)
            logger.debug("Added %d Bedrock models", len(bedrock_model_list))
        except Exception as e:
            logger.warning("Error getting Bedrock models: %s", e)
    
    # 4. Get Ollama models if configured
    for llm_config in config.llms.values():
        ollama_base_url = llm_config.ollama_base_url
        if llm_config.model.startswith("ollama") and (not ollama_base_url):
            ollama_base_url = llm_config.base_url
        if ollama_base_url:
            ollama_url = ollama_base_url.strip("/") + "/api/tags"
            try:
                ollama_models_list = httpx.get(ollama_url, timeout=3).json()["models"]
                for model in ollama_models_list:
                    model_list.append("ollama/" + model["name"])
                logger.debug("Added %d Ollama models", len(ollama_models_list))
                break
            except httpx.HTTPError as e:
                logger.error("Error getting OLLAMA models: %s", e)
    
    # 5. Add OpenHands proprietary models
    openhands_models = [
        # Claude 4 series
        "openhands/claude-sonnet-4-20250514",
        "openhands/claude-opus-4-20250514",
        "openhands/claude-opus-4-1-20250805",
        # Claude 4.5 series (actual available models from OpenHands proxy)
        "openhands/claude-sonnet-4-5-20250929",
        "openhands/claude-haiku-4-5-20251001",
        # GPT-5 series
        "openhands/gpt-5-2025-08-07",
        "openhands/gpt-5-mini-2025-08-07",
        # Gemini series
        "openhands/gemini-2.5-pro",
        # OpenAI o-series
        "openhands/o3",
        "openhands/o4-mini",
        # Devstral series
        "openhands/devstral-small-2505",
        "openhands/devstral-small-2507",
        "openhands/devstral-medium-2507",
        # Other models
        "openhands/kimi-k2-0711-preview",
        "openhands/qwen3-coder-480b",
    ]
    model_list.extend(openhands_models)
    
    # Remove duplicates and sort, but keep OpenRouter models at the top for better UX
    unique_models = []
    seen = set()
    
    # First add all models that start with 'openrouter/' to prioritize them
    openrouter_models_in_list = [m for m in model_list if m.startswith('openrouter/') and m not in seen]
    unique_models.extend(openrouter_models_in_list)
    seen.update(openrouter_models_in_list)
    
    # Then add the rest
    for model in model_list:
        if model not in seen:
            unique_models.append(model)
            seen.add(model)
    
    logger.info("Total models available: %d (including %d OpenRouter models)", 
                len(unique_models), len([m for m in unique_models if m.startswith('openrouter/')]))
    
    return sorted(unique_models, key=lambda x: (not x.startswith('openrouter/'), x))
