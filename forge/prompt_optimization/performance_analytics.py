"""Pure analytics helpers for prompt performance tracking."""

from __future__ import annotations

import statistics
from collections import defaultdict
from typing import Any, DefaultDict, Sequence, TypedDict

from .models import PromptPerformance


class VariantStats(TypedDict):
    success_rate: float
    error_rate: float
    avg_execution_time: float
    avg_token_cost: float
    sample_count: int


class DailyMetrics(TypedDict):
    total_executions: int
    success_rate: float
    avg_execution_time: float
    avg_token_cost: float


class OverallMetrics(TypedDict):
    total_executions: int
    overall_success_rate: float
    overall_avg_execution_time: float
    overall_avg_token_cost: float
    total_variants: int
    total_prompts: int


class CategoryStats(TypedDict):
    total_executions: int
    success_rate: float
    avg_execution_time: float
    avg_token_cost: float
    unique_variants: int
    unique_prompts: int


def calculate_variant_statistics(
    variant_performances: Sequence[PromptPerformance],
) -> VariantStats:
    """Calculate aggregate statistics for a single variant."""

    total_executions = len(variant_performances)
    successful_executions = sum(1 for p in variant_performances if p.success)

    success_rate = (
        successful_executions / total_executions if total_executions > 0 else 0.0
    )
    error_rate = 1.0 - success_rate

    execution_times = [p.execution_time for p in variant_performances]
    avg_execution_time = statistics.mean(execution_times) if execution_times else 0.0

    token_costs = [p.token_cost for p in variant_performances]
    avg_token_cost = statistics.mean(token_costs) if token_costs else 0.0

    return VariantStats(
        success_rate=success_rate,
        error_rate=error_rate,
        avg_execution_time=avg_execution_time,
        avg_token_cost=avg_token_cost,
        sample_count=total_executions,
    )


def group_performances_by_day(
    variant_performances: Sequence[PromptPerformance],
) -> dict[str, list[PromptPerformance]]:
    """Group performances by YYYY-MM-DD."""

    daily_data: DefaultDict[str, list[PromptPerformance]] = defaultdict(list)
    for perf in variant_performances:
        day_key = perf.timestamp.date().isoformat()
        daily_data[day_key].append(perf)
    return daily_data


def calculate_daily_metrics(performances: Sequence[PromptPerformance]) -> DailyMetrics:
    """Calculate success rate, execution time, and cost for a day."""

    total_executions = len(performances)
    successful_executions = sum(1 for p in performances if p.success)
    success_rate = (
        successful_executions / total_executions if total_executions > 0 else 0.0
    )

    execution_times = [p.execution_time for p in performances]
    avg_execution_time = statistics.mean(execution_times) if execution_times else 0.0

    token_costs = [p.token_cost for p in performances]
    avg_token_cost = statistics.mean(token_costs) if token_costs else 0.0

    return DailyMetrics(
        total_executions=total_executions,
        success_rate=success_rate,
        avg_execution_time=avg_execution_time,
        avg_token_cost=avg_token_cost,
    )


def calculate_overall_metrics(
    performances: Sequence[PromptPerformance],
) -> OverallMetrics:
    """Calculate overall stats for all recorded performances."""

    total_executions = len(performances)
    successful_executions = sum(1 for p in performances if p.success)
    overall_success_rate = (
        successful_executions / total_executions if total_executions > 0 else 0.0
    )

    execution_times = [p.execution_time for p in performances]
    overall_avg_execution_time = (
        statistics.mean(execution_times) if execution_times else 0.0
    )

    token_costs = [p.token_cost for p in performances]
    overall_avg_token_cost = statistics.mean(token_costs) if token_costs else 0.0

    unique_variants = len(set(p.variant_id for p in performances))
    unique_prompts = len(set(p.prompt_id for p in performances))

    return OverallMetrics(
        total_executions=total_executions,
        overall_success_rate=overall_success_rate,
        overall_avg_execution_time=overall_avg_execution_time,
        overall_avg_token_cost=overall_avg_token_cost,
        total_variants=unique_variants,
        total_prompts=unique_prompts,
    )


def calculate_category_statistics(
    performances: Sequence[PromptPerformance],
) -> dict[str, CategoryStats]:
    """Aggregate statistics per prompt category."""

    category_map: DefaultDict[str, list[PromptPerformance]] = defaultdict(list)
    for performance in performances:
        category_map[performance.category.value].append(performance)

    category_stats: dict[str, CategoryStats] = {}
    for category, perf_list in category_map.items():
        category_stats[category] = _build_category_stats(perf_list)

    return category_stats


def _build_category_stats(perf_list: Sequence[PromptPerformance]) -> CategoryStats:
    total_executions = len(perf_list)
    success_count = sum(1 for p in perf_list if p.success)
    success_rate = success_count / total_executions if total_executions else 0.0
    execution_times = [p.execution_time for p in perf_list]
    avg_execution_time = statistics.mean(execution_times) if execution_times else 0.0
    token_costs = [p.token_cost for p in perf_list]
    avg_token_cost = statistics.mean(token_costs) if token_costs else 0.0
    unique_variants = len({p.variant_id for p in perf_list})
    unique_prompts = len({p.prompt_id for p in perf_list})

    return CategoryStats(
        total_executions=total_executions,
        success_rate=success_rate,
        avg_execution_time=avg_execution_time,
        avg_token_cost=avg_token_cost,
        unique_variants=unique_variants,
        unique_prompts=unique_prompts,
    )

