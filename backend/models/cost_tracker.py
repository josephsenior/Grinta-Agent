"""Hook for recording LLM costs to quota system.

Automatically tracks LLM API costs and reports them to the cost quota middleware.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Optional, Dict

from backend.core.logger import forge_logger as logger

if TYPE_CHECKING:
    from backend.models.metrics import Metrics
    from backend.core.config import LLMConfig

# Model pricing per 1M tokens (USD)
MODEL_PRICES = {
    # OpenAI
    "openai/gpt-4o": {"input": 5.00, "output": 15.00},
    "openai/gpt-4o-mini": {"input": 0.15, "output": 0.60},
    "gpt-4o": {"input": 5.00, "output": 15.00},
    "gpt-4o-mini": {"input": 0.15, "output": 0.60},
    
    # Anthropic
    "anthropic/claude-3-5-sonnet-latest": {"input": 3.00, "output": 15.00},
    "claude-3-5-sonnet-latest": {"input": 3.00, "output": 15.00},
    
    # Google
    "google/gemini-1.5-pro-latest": {"input": 3.50, "output": 10.50},
    "gemini-1.5-pro-latest": {"input": 3.50, "output": 10.50},
    
    # xAI
    "xai/grok-2-latest": {"input": 2.00, "output": 10.00},
    "grok-2-latest": {"input": 2.00, "output": 10.00},
}

def get_completion_cost(
    model: str, 
    prompt_tokens: int, 
    completion_tokens: int, 
    config: Optional[LLMConfig] = None
) -> float:
    """Calculate the cost of a completion call in USD."""
    # Check for config overrides first
    if config:
        if config.input_cost_per_token is not None and config.output_cost_per_token is not None:
            return (prompt_tokens * config.input_cost_per_token) + (completion_tokens * config.output_cost_per_token)

    # Use default pricing
    prices = MODEL_PRICES.get(model)
    if not prices:
        # Try matching without provider prefix
        if "/" in model:
            model_name = model.split("/")[-1]
            prices = MODEL_PRICES.get(model_name)
    
    if prices:
        input_cost = (prompt_tokens / 1_000_000) * prices["input"]
        output_cost = (completion_tokens / 1_000_000) * prices["output"]
        return input_cost + output_cost
    
    return 0.0

def record_llm_cost_from_metrics(user_key: str, metrics: Metrics) -> None:
    """Record LLM cost from metrics object.

    Args:
        user_key: User quota key (user:id or ip:address)
        metrics: LLM metrics object containing cost information

    """
    try:
        from backend.server.middleware.cost_quota import record_llm_cost

        # Get accumulated cost from metrics
        if hasattr(metrics, "accumulated_cost"):
            cost = metrics.accumulated_cost
            if cost > 0:
                record_llm_cost(user_key, cost)
                logger.debug(f"Recorded LLM cost ${cost:.4f} for {user_key}")
    except ImportError:
        # Cost quota middleware not available
        pass
    except Exception as e:
        logger.error(f"Failed to record LLM cost: {e}")


def record_llm_cost_from_response(user_key: str, response: dict, model: str, config: Optional[LLMConfig] = None) -> None:
    """Record LLM cost from API response.

    Args:
        user_key: User quota key
        response: LLM API response dict with usage information
        model: Model name used
        config: LLM configuration for cost overrides

    """
    try:
        from backend.server.middleware.cost_quota import record_llm_cost

        usage = response.get("usage", {})
        prompt_tokens = usage.get("prompt_tokens", 0)
        completion_tokens = usage.get("completion_tokens", 0)
        
        cost = get_completion_cost(model, prompt_tokens, completion_tokens, config)
        
        if cost > 0:
            record_llm_cost(user_key, cost)
            logger.debug(f"Recorded LLM cost ${cost:.4f} for {user_key} using {model}")
        else:
            logger.debug(f"LLM usage for {user_key} using {model}: {prompt_tokens} prompt, {completion_tokens} completion")
        
    except ImportError:
        pass
    except Exception as e:
        logger.error(f"Failed to record LLM cost from response: {e}")
