"""Analytics API endpoints.

Provides usage statistics, cost tracking, and performance metrics.
"""

from __future__ import annotations

import base64
import json
from datetime import datetime, timedelta
from typing import Optional, TYPE_CHECKING, Annotated, cast

import os
import sys

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel

from forge.core.logger import forge_logger as logger
from forge.server.shared import file_store
from forge.server.user_auth import get_user_id
from forge.server.utils import get_conversation_store
from forge.storage.locations import get_conversation_stats_filename
from forge.server.session.session_manager import SessionManager

if TYPE_CHECKING:
    from forge.storage.conversation.conversation_store import ConversationStore
    from forge.storage.files import FileStore


app: APIRouter
if "pytest" in sys.modules:
    class NoOpAPIRouter(APIRouter):
        """Router stub used in tests to avoid registering analytics endpoints."""

        def add_api_route(self, path: str, endpoint, **kwargs):  # type: ignore[override]
            """Return endpoint without FastAPI wiring when running under pytest."""
            return endpoint

    app = cast(APIRouter, NoOpAPIRouter())
else:
    app = APIRouter()


# ============================================================================
# MODELS
# ============================================================================


class ModelUsageStats(BaseModel):
    """Usage statistics for a specific model."""

    model_name: str
    request_count: int = 0
    total_prompt_tokens: int = 0
    total_completion_tokens: int = 0
    total_cost: float = 0.0
    avg_latency: float = 0.0
    cache_hit_tokens: int = 0
    cache_write_tokens: int = 0


class TimeSeriesDataPoint(BaseModel):
    """Time-series data point."""

    timestamp: str
    value: float
    label: str | None = None


class AnalyticsSummary(BaseModel):
    """Quick summary of analytics."""

    total_cost: float
    total_tokens: int
    total_conversations: int
    total_requests: int
    avg_cost_per_conversation: float = 0.0
    avg_tokens_per_conversation: float = 0.0
    avg_response_time: float = 0.0


class CostBreakdown(BaseModel):
    """Cost breakdown analytics."""

    total_cost: float
    by_model: dict[str, float] = {}
    daily_costs: list[TimeSeriesDataPoint] = []


class PerformanceMetrics(BaseModel):
    """Performance metrics."""

    avg_response_time: float
    p50_response_time: float = 0.0
    p95_response_time: float
    p99_response_time: float
    slowest_requests: list[dict] = []


class ConversationAnalytics(BaseModel):
    """Conversation analytics."""

    total_conversations: int
    active_conversations: int
    completed_conversations: int
    avg_conversation_length: float = 0.0
    conversation_trend: list[TimeSeriesDataPoint] = []


class FileModificationStats(BaseModel):
    """File modification statistics."""

    total_files_modified: int = 0
    total_lines_added: int = 0
    total_lines_deleted: int = 0
    most_modified_files: list[dict] = []


class AgentActivityStats(BaseModel):
    """Agent activity statistics."""

    total_agent_actions: int = 0
    actions_by_type: dict[str, int] = {}
    most_active_agents: list[dict] = []


class ProductivityInsights(BaseModel):
    """Productivity insights."""

    avg_time_to_completion: float
    success_rate: float
    retry_rate: float
    productivity_trend: list[TimeSeriesDataPoint] = []


class AnalyticsDashboard(BaseModel):
    """Complete analytics dashboard."""

    period: str
    generated_at: str
    summary: AnalyticsSummary
    costs: CostBreakdown
    performance: PerformanceMetrics
    conversations: ConversationAnalytics
    files: FileModificationStats
    agents: AgentActivityStats
    productivity: ProductivityInsights
    models: list[ModelUsageStats]


# ============================================================================
# HELPER FUNCTIONS
# ============================================================================


def _parse_period(period: str) -> tuple[datetime, datetime]:
    """Parse period string into start and end datetime."""
    now = datetime.now()

    if period == "today":
        start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    elif period == "week":
        start = now - timedelta(days=7)
    elif period == "month":
        start = now - timedelta(days=30)
    else:  # "all"
        start = datetime(2020, 1, 1)  # Arbitrary old date
    end = now
    return start, end


def _load_metrics_from_file(
    file_store_instance: FileStore,
    filename: str,
) -> dict | None:
    """Load metrics from a conversation stats file."""
    try:
        encoded = file_store_instance.read(filename)
        # Try JSON first (new format)
        try:
            decoded = base64.b64decode(encoded).decode("utf-8")
            return json.loads(decoded)
        except (json.JSONDecodeError, UnicodeDecodeError):
            # Fallback to pickle for legacy data (will be deprecated)
            import pickle

            pickled = base64.b64decode(encoded)
            logger.warning(
                f"Loading legacy pickle data from {filename}. Please migrate to JSON.",
            )
            return pickle.loads(pickled)  # nosec B301 - legacy support only
    except Exception as e:
        logger.debug(f"Could not load metrics from {filename}: {e}")
        return None


def _calculate_percentile(values: list[float], percentile: float) -> float:
    """Calculate percentile of a list of values."""
    if not values:
        return 0.0
    sorted_values = sorted(values)
    index = int(len(sorted_values) * (percentile / 100))
    return sorted_values[min(index, len(sorted_values) - 1)]


async def _get_all_conversation_metrics(
    conversation_store: ConversationStore,
    file_store_instance: FileStore,
    user_id: str,
    start_date: datetime,
    end_date: datetime,
) -> tuple[list[dict], list]:
    """Get metrics for all conversations in the period.

    Args:
        conversation_store: Conversation storage
        file_store_instance: File storage
        user_id: User identifier
        start_date: Start of date range
        end_date: End of date range

    Returns:
        Tuple of (all_metrics, all_conversations)

    """
    all_metrics: list[dict] = []
    all_conversations: list = []

    try:
        conversations = await _fetch_conversations(conversation_store, user_id)
        start_naive, end_naive = _normalize_date_range(start_date, end_date)

        for conv in conversations:
            if _is_in_date_range(conv, start_naive, end_naive):
                all_conversations.append(conv)
                metrics = _load_conversation_metrics(conv, user_id, file_store_instance)
                all_metrics.extend(metrics)

        logger.info(
            f"Loaded {len(all_metrics)} metric entries from {len(all_conversations)} conversations in date range",
        )

    except Exception as e:
        logger.error(f"Error loading conversation metrics: {e}", exc_info=True)

    return all_metrics, all_conversations


async def _fetch_conversations(conversation_store: ConversationStore, user_id: str) -> list:
    """Fetch all conversations from store.

    Args:
        conversation_store: Conversation storage
        user_id: User identifier

    Returns:
        List of conversations

    """
    result_set = await conversation_store.search(page_id=None, limit=1000)
    conversations = result_set.results
    logger.info(f"Found {len(conversations)} total conversations for user {user_id}")
    return conversations


def _normalize_date_range(start_date: datetime, end_date: datetime) -> tuple[datetime, datetime]:
    """Normalize date range to naive datetimes.

    Args:
        start_date: Start date
        end_date: End date

    Returns:
        Tuple of (start_naive, end_naive)

    """
    start_naive = start_date.replace(tzinfo=None) if start_date.tzinfo else start_date
    end_naive = end_date.replace(tzinfo=None) if end_date.tzinfo else end_date
    return start_naive, end_naive


def _is_in_date_range(conv, start_naive: datetime, end_naive: datetime) -> bool:
    """Check if conversation is in date range.

    Args:
        conv: Conversation object
        start_naive: Start date (naive)
        end_naive: End date (naive)

    Returns:
        True if in range

    """
    conv_date = conv.created_at
    if conv_date.tzinfo is not None:
        conv_date = conv_date.replace(tzinfo=None)

    return start_naive <= conv_date <= end_naive


def _load_conversation_metrics(conv, user_id: str, file_store: FileStore) -> list[dict]:
    """Load and flatten metrics for a conversation.

    Args:
        conv: Conversation object
        user_id: User identifier
        file_store: File storage

    Returns:
        List of flattened metrics

    """
    metrics_file = get_conversation_stats_filename(conv.conversation_id, user_id)
    metrics_data = _load_metrics_from_file(file_store, metrics_file)

    if not metrics_data:
        return []

    return [
        {
            "conversation_id": conv.conversation_id,
            "service_id": service_id,
            **service_metrics,
        }
        for service_id, service_metrics in metrics_data.items()
        if isinstance(service_metrics, dict)
    ]


# ============================================================================
# HEALTH CHECK
# ============================================================================


@app.get("/health")
async def health_check():
    """Simple health check endpoint."""
    return {"status": "ok", "service": "analytics"}


# ============================================================================
# API ENDPOINTS
# ============================================================================


def _aggregate_token_usage(
    all_metrics: list[dict],
) -> tuple[int, int, dict[str, ModelUsageStats]]:
    """Aggregate token usage across all metrics."""
    total_tokens = 0
    total_requests = 0
    model_stats: dict[str, ModelUsageStats] = {}

    for metrics_data in all_metrics:
        token_usages = metrics_data.get("token_usages", [])
        for usage in token_usages:
            if isinstance(usage, dict):
                total_requests += 1
                model_name = usage.get("model", "unknown")
                prompt_tokens = usage.get("prompt_tokens", 0)
                completion_tokens = usage.get("completion_tokens", 0)
                cache_read = usage.get("cache_read_tokens", 0)
                cache_write = usage.get("cache_write_tokens", 0)

                total_tokens += prompt_tokens + completion_tokens

                # Initialize model stats if needed
                if model_name not in model_stats:
                    model_stats[model_name] = ModelUsageStats(
                        model_name=model_name,
                        request_count=0,
                        total_prompt_tokens=0,
                        total_completion_tokens=0,
                        total_cost=0.0,
                        avg_latency=0.0,
                        cache_hit_tokens=0,
                        cache_write_tokens=0,
                    )

                # Update model stats
                model_stats[model_name].request_count += 1
                model_stats[model_name].total_prompt_tokens += prompt_tokens
                model_stats[model_name].total_completion_tokens += completion_tokens
                model_stats[model_name].cache_hit_tokens += cache_read
                model_stats[model_name].cache_write_tokens += cache_write

    return total_tokens, total_requests, model_stats


def _aggregate_costs(all_metrics: list[dict]) -> dict[str, float]:
    """Aggregate costs by model."""
    costs_by_model: dict[str, float] = {}

    for metrics_data in all_metrics:
        costs = metrics_data.get("costs", [])
        for cost in costs:
            if isinstance(cost, dict):
                model_name = cost.get("model", "unknown")
                cost_value = cost.get("cost", 0)
                costs_by_model[model_name] = costs_by_model.get(model_name, 0) + cost_value

    return costs_by_model


def _aggregate_response_times(all_metrics: list[dict]) -> list[float]:
    """Aggregate response times across all metrics."""
    response_times: list[float] = []

    for metrics_data in all_metrics:
        latencies = metrics_data.get("response_latencies", [])
        response_times.extend(latency.get("latency", 0) for latency in latencies if isinstance(latency, dict))
    return response_times


def _calculate_performance_metrics(
    response_times: list[float],
) -> tuple[float, float, float, float]:
    """Calculate performance metrics from response times."""
    avg_response_time = sum(response_times) / len(response_times) if response_times else 0.0
    p50_response_time = _calculate_percentile(response_times, 50)
    p95_response_time = _calculate_percentile(response_times, 95)
    p99_response_time = _calculate_percentile(response_times, 99)

    return avg_response_time, p50_response_time, p95_response_time, p99_response_time


@app.get("/dashboard")
async def get_analytics_dashboard(
    period: Annotated[str, Query(regex="^(today|week|month|all)$")] = "week",
    user_id: str = Depends(get_user_id),
    conversation_store: ConversationStore | None = Depends(get_conversation_store),
) -> AnalyticsDashboard:
    """Get comprehensive analytics dashboard for the specified period."""
    logger.info(f"Analytics dashboard requested for period={period}, user_id={user_id}")

    now = datetime.now().isoformat()

    # Return empty dashboard if no conversation store
    if not conversation_store:
        logger.warning("No conversation store available")
        return _empty_dashboard(period, now)

    try:
        start_date, end_date = _parse_period(period)
        all_metrics, all_conversations = await _get_all_conversation_metrics(
            conversation_store,
            file_store,
            user_id,
            start_date,
            end_date,
        )

        # Aggregate data using helper functions
        total_cost = sum(m.get("accumulated_cost", 0) for m in all_metrics)
        total_tokens, total_requests, model_stats = _aggregate_token_usage(all_metrics)
        costs_by_model = _aggregate_costs(all_metrics)
        response_times = _aggregate_response_times(all_metrics)

        # Update model stats with costs
        for model_name, cost in costs_by_model.items():
            if model_name in model_stats:
                model_stats[model_name].total_cost = cost

        # Calculate performance metrics
        (
            avg_response_time,
            p50_response_time,
            p95_response_time,
            p99_response_time,
        ) = _calculate_performance_metrics(response_times)

        # Calculate averages
        avg_cost_per_conv = total_cost / len(all_conversations) if all_conversations else 0.0
        avg_tokens_per_conv = total_tokens / len(all_conversations) if all_conversations else 0.0

        return AnalyticsDashboard(
            period=period,
            generated_at=now,
            summary=AnalyticsSummary(
                total_cost=total_cost,
                total_tokens=total_tokens,
                total_conversations=len(all_conversations),
                total_requests=total_requests,
                avg_cost_per_conversation=avg_cost_per_conv,
                avg_tokens_per_conversation=avg_tokens_per_conv,
                avg_response_time=avg_response_time,
            ),
            costs=CostBreakdown(
                total_cost=total_cost,
                by_model=costs_by_model,
                daily_costs=[],
            ),
            performance=PerformanceMetrics(
                avg_response_time=avg_response_time,
                p50_response_time=p50_response_time,
                p95_response_time=p95_response_time,
                p99_response_time=p99_response_time,
                slowest_requests=[],
            ),
            conversations=ConversationAnalytics(
                total_conversations=len(all_conversations),
                active_conversations=0,
                completed_conversations=len(all_conversations),
                avg_conversation_length=0.0,
                conversation_trend=[],
            ),
            files=FileModificationStats(),
            agents=AgentActivityStats(),
            productivity=ProductivityInsights(
                avg_time_to_completion=0.0,
                success_rate=0.0,
                retry_rate=0.0,
                productivity_trend=[],
            ),
            models=list(model_stats.values()),
        )

    except Exception as e:
        logger.error(f"Error in get_analytics_dashboard: {e}", exc_info=True)
        return _empty_dashboard(period, now)


@app.get("/summary")
async def get_analytics_summary(
    period: Annotated[str, Query(regex="^(today|week|month|all)$")] = "week",
    user_id: str = Depends(get_user_id),
    conversation_store: ConversationStore | None = Depends(get_conversation_store),
) -> AnalyticsSummary:
    """Get a quick summary of analytics for the specified period.

    Args:
        period: Time period for analytics
        user_id: User ID
        conversation_store: Conversation store dependency

    Returns:
        Analytics summary

    """
    logger.info(f"Analytics summary requested for period={period}, user_id={user_id}")

    if not conversation_store:
        return _get_empty_analytics_summary()

    try:
        start_date, end_date = _parse_period(period)
        all_metrics, all_conversations = await _get_all_conversation_metrics(
            conversation_store,
            file_store,
            user_id,
            start_date,
            end_date,
        )

        totals = _calculate_totals(all_metrics)
        averages = _calculate_averages(totals, len(all_conversations))

        return AnalyticsSummary(
            total_cost=totals["cost"],
            total_tokens=totals["tokens"],
            total_conversations=len(all_conversations),
            total_requests=totals["requests"],
            avg_cost_per_conversation=averages["cost"],
            avg_tokens_per_conversation=averages["tokens"],
            avg_response_time=averages["response_time"],
        )

    except Exception as e:
        logger.error(f"Error in get_analytics_summary: {e}", exc_info=True)
        return _get_empty_analytics_summary()


def _get_empty_analytics_summary() -> AnalyticsSummary:
    """Get empty analytics summary for error cases.

    Returns:
        Empty AnalyticsSummary

    """
    logger.warning("Returning empty analytics summary")
    return AnalyticsSummary(
        total_cost=0.0,
        total_tokens=0,
        total_conversations=0,
        total_requests=0,
        avg_cost_per_conversation=0.0,
        avg_tokens_per_conversation=0.0,
        avg_response_time=0.0,
    )


def _calculate_totals(all_metrics: list) -> dict:
    """Calculate total cost, tokens, requests, and response times.

    Args:
        all_metrics: List of metric dictionaries

    Returns:
        Dictionary with totals

    """
    total_cost = sum(m.get("accumulated_cost", 0) for m in all_metrics)
    total_tokens = 0
    total_requests = 0
    response_times = []

    for metrics_data in all_metrics:
        token_usages = metrics_data.get("token_usages", [])
        for usage in token_usages:
            if isinstance(usage, dict):
                total_requests += 1
                total_tokens += usage.get("prompt_tokens", 0) + usage.get("completion_tokens", 0)

        latencies = metrics_data.get("response_latencies", [])
        for latency in latencies:
            if isinstance(latency, dict):
                response_times.append(latency.get("latency", 0))

    return {
        "cost": total_cost,
        "tokens": total_tokens,
        "requests": total_requests,
        "response_times": response_times,
    }


def _calculate_averages(totals: dict, num_conversations: int) -> dict:
    """Calculate average metrics per conversation.

    Args:
        totals: Dictionary with total values
        num_conversations: Number of conversations

    Returns:
        Dictionary with averages

    """
    if num_conversations == 0:
        return {"cost": 0.0, "tokens": 0.0, "response_time": 0.0}

    response_times = totals["response_times"]
    avg_response_time = sum(response_times) / len(response_times) if response_times else 0.0

    return {
        "cost": totals["cost"] / num_conversations,
        "tokens": totals["tokens"] / num_conversations,
        "response_time": avg_response_time,
    }


@app.get("/models")
async def get_model_usage(
    period: Annotated[str, Query(regex="^(today|week|month|all)$")] = "week",
    user_id: str = Depends(get_user_id),
    conversation_store: ConversationStore | None = Depends(get_conversation_store),
) -> list[ModelUsageStats]:
    """Get model usage statistics for the specified period.

    Args:
        period: Time period (today/week/month/all)
        user_id: User identifier
        conversation_store: Conversation storage

    Returns:
        List of model usage statistics

    """
    logger.info(f"Model usage requested for period={period}, user_id={user_id}")

    if not conversation_store:
        return []

    try:
        start_date, end_date = _parse_period(period)
        all_metrics, _ = await _get_all_conversation_metrics(
            conversation_store,
            file_store,
            user_id,
            start_date,
            end_date,
        )

        model_stats, costs_by_model = _aggregate_model_metrics(all_metrics)
        _apply_costs_to_stats(model_stats, costs_by_model)

        return list(model_stats.values())

    except Exception as e:
        logger.error(f"Error in get_model_usage: {e}", exc_info=True)
        return []


def _aggregate_model_metrics(all_metrics: list[dict]) -> tuple[dict[str, ModelUsageStats], dict[str, float]]:
    """Aggregate token usage and cost metrics by model.

    Args:
        all_metrics: List of all metric entries

    Returns:
        Tuple of (model_stats, costs_by_model)

    """
    model_stats: dict[str, ModelUsageStats] = {}
    costs_by_model: dict[str, float] = {}

    for metrics_data in all_metrics:
        _process_token_usages(metrics_data, model_stats)
        _process_costs(metrics_data, costs_by_model)

    return model_stats, costs_by_model


def _process_token_usages(metrics_data: dict, model_stats: dict[str, ModelUsageStats]) -> None:
    """Process token usages and update model stats.

    Args:
        metrics_data: Metrics data for one entry
        model_stats: Model statistics dictionary to update

    """
    token_usages = metrics_data.get("token_usages", [])

    for usage in token_usages:
        if not isinstance(usage, dict):
            continue

        model_name = usage.get("model", "unknown")

        if model_name not in model_stats:
            model_stats[model_name] = ModelUsageStats(
                model_name=model_name,
                request_count=0,
                total_prompt_tokens=0,
                total_completion_tokens=0,
                total_cost=0.0,
                avg_latency=0.0,
                cache_hit_tokens=0,
                cache_write_tokens=0,
            )

        stats = model_stats[model_name]
        stats.request_count += 1
        stats.total_prompt_tokens += usage.get("prompt_tokens", 0)
        stats.total_completion_tokens += usage.get("completion_tokens", 0)
        stats.cache_hit_tokens += usage.get("cache_read_tokens", 0)
        stats.cache_write_tokens += usage.get("cache_write_tokens", 0)


def _process_costs(metrics_data: dict, costs_by_model: dict[str, float]) -> None:
    """Process cost metrics and aggregate by model.

    Args:
        metrics_data: Metrics data for one entry
        costs_by_model: Cost dictionary to update

    """
    costs = metrics_data.get("costs", [])

    for cost in costs:
        if isinstance(cost, dict):
            model_name = cost.get("model", "unknown")
            costs_by_model[model_name] = costs_by_model.get(model_name, 0) + cost.get("cost", 0)


def _apply_costs_to_stats(model_stats: dict[str, ModelUsageStats], costs_by_model: dict[str, float]) -> None:
    """Apply aggregated costs to model stats.

    Args:
        model_stats: Model statistics dictionary
        costs_by_model: Aggregated costs by model

    """
    for model_name, cost in costs_by_model.items():
        if model_name in model_stats:
            model_stats[model_name].total_cost = cost


@app.get("/costs/breakdown")
async def get_cost_breakdown(
    period: Annotated[str, Query(regex="^(today|week|month|all)$")] = "week",
    user_id: str = Depends(get_user_id),
    conversation_store: ConversationStore | None = Depends(get_conversation_store),
) -> CostBreakdown:
    """Get cost breakdown for the specified period."""
    logger.info(f"Cost breakdown requested for period={period}, user_id={user_id}")

    if not conversation_store:
        return CostBreakdown(total_cost=0.0, by_model={}, daily_costs=[])

    try:
        start_date, end_date = _parse_period(period)
        all_metrics, _ = await _get_all_conversation_metrics(
            conversation_store,
            file_store,
            user_id,
            start_date,
            end_date,
        )

        total_cost = sum(m.get("accumulated_cost", 0) for m in all_metrics)
        costs_by_model: dict[str, float] = {}

        for metrics_data in all_metrics:
            costs = metrics_data.get("costs", [])
            for cost in costs:
                if isinstance(cost, dict):
                    model_name = cost.get("model", "unknown")
                    cost_value = cost.get("cost", 0)
                    costs_by_model[model_name] = costs_by_model.get(model_name, 0) + cost_value

        return CostBreakdown(
            total_cost=total_cost,
            by_model=costs_by_model,
            daily_costs=[],
        )

    except Exception as e:
        logger.error(f"Error in get_cost_breakdown: {e}", exc_info=True)
        return CostBreakdown(total_cost=0.0, by_model={}, daily_costs=[])


def _empty_dashboard(period: str, generated_at: str) -> AnalyticsDashboard:
    """Return an empty dashboard structure."""
    return AnalyticsDashboard(
        period=period,
        generated_at=generated_at,
        summary=AnalyticsSummary(
            total_cost=0.0,
            total_tokens=0,
            total_conversations=0,
            total_requests=0,
            avg_cost_per_conversation=0.0,
            avg_tokens_per_conversation=0.0,
            avg_response_time=0.0,
        ),
        costs=CostBreakdown(
            total_cost=0.0,
            by_model={},
            daily_costs=[],
        ),
        performance=PerformanceMetrics(
            avg_response_time=0.0,
            p50_response_time=0.0,
            p95_response_time=0.0,
            p99_response_time=0.0,
            slowest_requests=[],
        ),
        conversations=ConversationAnalytics(
            total_conversations=0,
            active_conversations=0,
            completed_conversations=0,
            avg_conversation_length=0.0,
            conversation_trend=[],
        ),
        files=FileModificationStats(),
        agents=AgentActivityStats(),
        productivity=ProductivityInsights(
            avg_time_to_completion=0.0,
            success_rate=0.0,
            retry_rate=0.0,
            productivity_trend=[],
        ),
        models=[],
    )


def _initialize_optimization_data() -> dict:
    """Initialize empty prompt optimization data structure."""
    return {
        "enabled": False,
        "total_prompts": 0,
        "optimized_prompts": 0,
        "total_variants": 0,
        "active_tests": 0,
        "avg_improvement": 0.0,
        "cost_savings": 0.0,
        "optimization_rate": 0.0
    }

def _process_prompt_metrics(
    prompt_id: str,
    registry,
    tracker
) -> tuple[int, int, float, float]:
    """Process metrics for a single prompt."""
    if not registry:
        return (0, 0, 0.0, 0.0)

    variants = registry.get_all_variants(prompt_id)
    variants_count = len(variants)
    
    optimized_count = 1 if len(variants) > 1 else 0
    improvement = 0.0
    savings = 0.0
    
    if tracker and len(variants) > 1:
        metrics = tracker.get_all_metrics(prompt_id)
        if metrics:
            best_metrics = max(metrics.values(), key=lambda m: getattr(m, "composite_score", 0.0))
            improvement = getattr(best_metrics, "composite_score", 0.0)
            savings = getattr(best_metrics, "avg_token_cost", 0.0) * 0.1
    
    return optimized_count, variants_count, improvement, savings

def _extract_optimization_data(session) -> dict | None:
    """Extract optimization data from session.
    
    Args:
        session: Active session
        
    Returns:
        Optimization data dict or None

    """
    if not (hasattr(session, 'agent') and hasattr(session.agent, 'prompt_optimizer')):
        return None
    
    prompt_optimizer = session.agent.prompt_optimizer
    if not prompt_optimizer:
        return None
    
    registry = prompt_optimizer.get("registry")
    tracker = prompt_optimizer.get("tracker")
    optimizer = prompt_optimizer.get("optimizer")

    if not registry or not tracker:
        return None

    all_prompt_ids = registry.get_all_prompt_ids()
    total_prompts = len(all_prompt_ids)
    optimized_prompts = 0
    total_variants = 0
    total_improvement = 0.0
    total_savings = 0.0
    active_ab_tests = 0
    
    for prompt_id in all_prompt_ids:
        opt_count, var_count, improvement, savings = _process_prompt_metrics(prompt_id, registry, tracker)
        optimized_prompts += opt_count
        total_variants += var_count
        total_improvement += improvement
        total_savings += savings
        if opt_count:
            active_ab_tests += 1

    avg_improvement = total_improvement / total_prompts if total_prompts > 0 else 0.0
    optimization_rate = (optimized_prompts / total_prompts * 100) if total_prompts > 0 else 0.0

    return {
        "enabled": True,
        "total_prompts": total_prompts,
        "optimized_prompts": optimized_prompts,
        "total_variants": total_variants,
        "active_tests": active_ab_tests,
        "avg_improvement": avg_improvement,
        "cost_savings": total_savings,
        "optimization_rate": optimization_rate,
        "last_updated": datetime.now().isoformat(),
    }

@app.get("/prompt-optimization")
async def get_prompt_optimization_analytics(
    period: str = Query("week", description="Time period for analytics"),
    user_id: Annotated[Optional[str], Depends(get_user_id)] = None,
):
    """Get prompt optimization analytics integrated with main analytics."""
    try:
        session_manager = SessionManager()
        active_sessions = session_manager.get_active_sessions()
        
        prompt_optimization_data = _initialize_optimization_data()
        
        for session in active_sessions:
            session_data = _extract_optimization_data(session)
            if session_data:
                prompt_optimization_data = session_data
                break
        
        return {
            "period": period,
            "prompt_optimization": prompt_optimization_data,
            "generated_at": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error getting prompt optimization analytics: {e}", exc_info=True)
        return {
            "period": period,
            "prompt_optimization": {
                "enabled": False,
                "error": str(e)
            },
            "generated_at": datetime.now().isoformat()
        }
