"""Hook for recording LLM costs to quota system.

Automatically tracks LLM API costs and reports them to the cost quota middleware.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Optional, Dict

from backend.core.logger import forge_logger as logger

if TYPE_CHECKING:
    from backend.models.metrics import Metrics
    from backend.core.config import LLMConfig

# Model pricing per 1M tokens (USD) — updated 2025-06
# Each entry maps a canonical model name to input/output costs.
# Aliases (with/without provider prefix) are resolved in _resolve_pricing().
_MODEL_PRICES: Dict[str, Dict[str, float]] = {
    # ── OpenAI ──────────────────────────────────────────
    "gpt-4o": {"input": 2.50, "output": 10.00},
    "gpt-4o-mini": {"input": 0.15, "output": 0.60},
    "gpt-4.1": {"input": 2.00, "output": 8.00},
    "gpt-4.1-mini": {"input": 0.40, "output": 1.60},
    "gpt-4.1-nano": {"input": 0.10, "output": 0.40},
    "gpt-4-turbo": {"input": 10.00, "output": 30.00},
    "o3": {"input": 10.00, "output": 40.00},
    "o3-mini": {"input": 1.10, "output": 4.40},
    "o4-mini": {"input": 1.10, "output": 4.40},

    # ── Anthropic ───────────────────────────────────────
    "claude-sonnet-4-20250514": {"input": 3.00, "output": 15.00},
    "claude-3-5-sonnet-latest": {"input": 3.00, "output": 15.00},
    "claude-3-5-sonnet-20241022": {"input": 3.00, "output": 15.00},
    "claude-3-5-haiku-latest": {"input": 0.80, "output": 4.00},
    "claude-3-opus-latest": {"input": 15.00, "output": 75.00},
    "claude-3-haiku-20240307": {"input": 0.25, "output": 1.25},

    # ── Google Gemini ───────────────────────────────────
    "gemini-2.5-pro-preview-06-05": {"input": 1.25, "output": 10.00},
    "gemini-2.5-flash-preview-05-20": {"input": 0.15, "output": 0.60},
    "gemini-2.0-flash": {"input": 0.10, "output": 0.40},
    "gemini-1.5-pro-latest": {"input": 3.50, "output": 10.50},
    "gemini-1.5-flash-latest": {"input": 0.075, "output": 0.30},

    # ── xAI ─────────────────────────────────────────────
    "grok-3": {"input": 3.00, "output": 15.00},
    "grok-3-mini": {"input": 0.30, "output": 0.50},
    "grok-2-latest": {"input": 2.00, "output": 10.00},

    # ── DeepSeek ────────────────────────────────────────
    "deepseek-chat": {"input": 0.27, "output": 1.10},
    "deepseek-reasoner": {"input": 0.55, "output": 2.19},

    # ── Mistral ─────────────────────────────────────────
    "mistral-large-latest": {"input": 2.00, "output": 6.00},
    "codestral-latest": {"input": 0.30, "output": 0.90},
}

# Fallback tier pricing for unknown model variants
_TIER_PRICING: list[tuple[str, Dict[str, float]]] = [
    ("gpt-4.1", {"input": 2.00, "output": 8.00}),
    ("gpt-4o", {"input": 2.50, "output": 10.00}),
    ("gpt-4", {"input": 10.00, "output": 30.00}),
    ("gpt-3.5", {"input": 0.50, "output": 1.50}),
    ("o3-mini", {"input": 1.10, "output": 4.40}),
    ("o4-mini", {"input": 1.10, "output": 4.40}),
    ("claude-sonnet-4", {"input": 3.00, "output": 15.00}),
    ("claude-3-5-sonnet", {"input": 3.00, "output": 15.00}),
    ("claude-3-5-haiku", {"input": 0.80, "output": 4.00}),
    ("claude-3-opus", {"input": 15.00, "output": 75.00}),
    ("claude-3-haiku", {"input": 0.25, "output": 1.25}),
    ("gemini-2.5-pro", {"input": 1.25, "output": 10.00}),
    ("gemini-2.5-flash", {"input": 0.15, "output": 0.60}),
    ("gemini-2.0-flash", {"input": 0.10, "output": 0.40}),
    ("gemini-1.5-pro", {"input": 3.50, "output": 10.50}),
    ("gemini-1.5-flash", {"input": 0.075, "output": 0.30}),
    ("grok-3-mini", {"input": 0.30, "output": 0.50}),
    ("grok-3", {"input": 3.00, "output": 15.00}),
    ("grok-2", {"input": 2.00, "output": 10.00}),
    ("deepseek", {"input": 0.27, "output": 1.10}),
    ("mistral", {"input": 2.00, "output": 6.00}),
    ("codestral", {"input": 0.30, "output": 0.90}),
]


def _resolve_pricing(model: str) -> Optional[Dict[str, float]]:
    """Resolve model name to pricing entry.

    Resolution order:
      1. Exact match in ``_MODEL_PRICES``.
      2. Strip provider prefix (e.g. ``openai/gpt-4o`` → ``gpt-4o``) and retry.
      3. Substring-based tier matching via ``_TIER_PRICING``.
    """
    prices = _MODEL_PRICES.get(model)
    if prices:
        return prices

    # Strip provider prefix
    bare = model.split("/")[-1] if "/" in model else None
    if bare:
        prices = _MODEL_PRICES.get(bare)
        if prices:
            return prices

    # Tier / substring fallback
    lookup = (bare or model).lower()
    for prefix, tier_prices in _TIER_PRICING:
        if prefix in lookup:
            return tier_prices

    return None

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

    prices = _resolve_pricing(model)
    if prices:
        input_cost = (prompt_tokens / 1_000_000) * prices["input"]
        output_cost = (completion_tokens / 1_000_000) * prices["output"]
        return input_cost + output_cost
    
    logger.debug("No pricing data for model %s — cost reported as $0.00", model)
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
                logger.debug("Recorded LLM cost $%.4f for %s", cost, user_key)
    except ImportError:
        # Cost quota middleware not available
        pass
    except Exception as e:
        logger.error("Failed to record LLM cost: %s", e)


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
            logger.debug("Recorded LLM cost $%.4f for %s using %s", cost, user_key, model)
        else:
            logger.debug(
                "LLM usage for %s using %s: %d prompt, %d completion",
                user_key, model, prompt_tokens, completion_tokens,
            )
        
    except ImportError:
        pass
    except Exception as e:
        logger.error("Failed to record LLM cost from response: %s", e)
