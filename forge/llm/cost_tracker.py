"""Hook for recording LLM costs to quota system.

Automatically tracks LLM API costs and reports them to the cost quota middleware.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from forge.core.logger import forge_logger as logger

if TYPE_CHECKING:
    from forge.llm.metrics import Metrics


def record_llm_cost_from_metrics(user_key: str, metrics: Metrics) -> None:
    """Record LLM cost from metrics object.

    Args:
        user_key: User quota key (user:id or ip:address)
        metrics: LLM metrics object containing cost information

    """
    try:
        from forge.server.middleware.cost_quota import record_llm_cost

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


def record_llm_cost_from_response(user_key: str, response: dict) -> None:
    """Record LLM cost from API response.

    Args:
        user_key: User quota key
        response: LLM API response dict with usage information

    """
    try:
        from litellm import completion_cost
        from forge.server.middleware.cost_quota import record_llm_cost

        # Calculate cost using litellm
        cost = completion_cost(completion_response=response)
        if cost > 0:
            record_llm_cost(user_key, cost)
            logger.debug(f"Recorded LLM cost ${cost:.4f} for {user_key}")
    except ImportError:
        pass
    except Exception as e:
        logger.error(f"Failed to record LLM cost from response: {e}")

