"""Health snapshot utilities for AgentController instances."""

from __future__ import annotations

import contextlib
from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from typing import Any

from backend.core.schemas import AgentState


@dataclass
class IterationHealth:
    current: int | None
    max: int | None
    limit_hit: bool


@dataclass
class BudgetHealth:
    current: float | None
    max: float | None
    limit_hit: bool
    pct_used: float | None = None


@dataclass
class RetryHealth:
    enabled: bool
    pending: bool
    retry_count: int
    worker_running: bool


@dataclass
class CircuitBreakerHealth:
    enabled: bool
    consecutive_errors: int | None = None
    high_risk_actions: int | None = None
    stuck_detections: int | None = None
    error_rate_window: int | None = None
    max_consecutive_errors: int | None = None
    max_high_risk_actions: int | None = None
    max_stuck_detections: int | None = None
    last_check: dict[str, Any] | None = None


def _iteration_health(state: Any) -> IterationHealth | None:
    iteration_flag = getattr(state, "iteration_flag", None)
    if not iteration_flag:
        return None
    current = getattr(iteration_flag, "current_value", None)
    max_value = getattr(iteration_flag, "max_value", None)
    limit_hit = (
        current is not None and max_value is not None and current >= max_value
    )
    return IterationHealth(current=current, max=max_value, limit_hit=limit_hit)


def _budget_health(state: Any) -> BudgetHealth | None:
    budget_flag = getattr(state, "budget_flag", None)
    if not budget_flag:
        return None
    current = getattr(budget_flag, "current_value", None)
    max_value = getattr(budget_flag, "max_value", None)
    limit_hit = (
        current is not None
        and max_value is not None
        and current >= max_value
    )
    pct_used = None
    if current is not None and max_value is not None and max_value > 0:
        pct_used = round(current / max_value, 4)
    return BudgetHealth(current=current, max=max_value, limit_hit=limit_hit, pct_used=pct_used)


def _retry_health(controller: Any) -> RetryHealth | None:
    retry_service = getattr(controller, "retry_service", None)
    if not retry_service:
        return None
    queue = getattr(retry_service, "_retry_queue", None)
    worker_task = getattr(retry_service, "_retry_worker_task", None)
    return RetryHealth(
        enabled=queue is not None,
        pending=bool(getattr(retry_service, "retry_pending", False)),
        retry_count=int(getattr(retry_service, "retry_count", 0)),
        worker_running=bool(worker_task and not worker_task.done()),
    )


def _circuit_breaker_health(controller: Any) -> CircuitBreakerHealth | None:
    service = getattr(controller, "circuit_breaker_service", None)
    if not service:
        return None
    breaker = getattr(service, "circuit_breaker", None)
    if not breaker:
        return CircuitBreakerHealth(enabled=False)

    config = getattr(breaker, "config", None)
    config_values = {}
    if config:
        config_values = {
            "max_consecutive_errors": getattr(
                config, "max_consecutive_errors", None
            ),
            "max_high_risk_actions": getattr(
                config, "max_high_risk_actions", None
            ),
            "max_stuck_detections": getattr(
                config, "max_stuck_detections", None
            ),
            "error_rate_window": getattr(config, "error_rate_window", None),
        }

    last_check: dict[str, Any] | None = None
    try:
        result = service.check()
        if result is not None:
            last_check = {
                "tripped": bool(getattr(result, "tripped", False)),
                "reason": getattr(result, "reason", ""),
                "action": getattr(result, "action", ""),
            }
    except Exception:
        logger.debug("Circuit breaker check failed", exc_info=True)

    return CircuitBreakerHealth(
        enabled=True,
        consecutive_errors=getattr(breaker, "consecutive_errors", None),
        high_risk_actions=getattr(breaker, "high_risk_action_count", None),
        stuck_detections=getattr(breaker, "stuck_detection_count", None),
        last_check=last_check,
        **config_values,
    )


def _sync_budget_metrics(controller: Any) -> None:
    state_tracker = getattr(controller, "state_tracker", None)
    if state_tracker and hasattr(state_tracker, "sync_budget_flag_with_metrics"):
        try:
            state_tracker.sync_budget_flag_with_metrics()
        except Exception:
            logger.debug("Failed to sync budget metrics", exc_info=True)


def _extract_agent_state(state: Any) -> str:
    agent_state = getattr(state, "agent_state", AgentState.LOADING)
    return agent_state.value if isinstance(agent_state, AgentState) else str(agent_state)


def _collect_event_stream_stats(controller: Any) -> dict[str, Any]:
    event_stream = getattr(controller, "event_stream", None)
    if not event_stream:
        return {}

    stats: dict[str, Any] = {}
    if hasattr(event_stream, "get_stats"):
        try:
            stats.update(event_stream.get_stats() or {})
        except Exception:
            logger.debug("Failed to collect event stream stats", exc_info=True)
    if hasattr(event_stream, "get_backpressure_snapshot"):
        try:
            stats.update(event_stream.get_backpressure_snapshot() or {})
        except Exception:
            logger.debug("Failed to collect backpressure snapshot", exc_info=True)
    if stats:
        return stats
    return {}


def _is_stuck(controller: Any) -> bool:
    stuck_service = getattr(controller, "stuck_detection_service", None)
    if stuck_service and hasattr(stuck_service, "is_stuck"):
        try:
            return bool(stuck_service.is_stuck())
        except Exception:
            logger.debug("Stuck detection check failed", exc_info=True)
    return False


def _build_warnings(
    iteration: IterationHealth | None,
    budget: BudgetHealth | None,
    retry: RetryHealth | None,
    circuit_breaker: CircuitBreakerHealth | None,
    is_stuck: bool,
    agent_state: str,
    event_stream_stats: dict[str, Any] | None = None,
) -> list[str]:
    warnings: list[str] = []
    warnings.extend(_iteration_warnings(iteration))
    warnings.extend(_budget_warnings(budget))
    warnings.extend(_retry_warnings(retry))
    warnings.extend(_circuit_warnings(circuit_breaker))
    warnings.extend(_stuck_warnings(is_stuck))
    warnings.extend(_agent_state_warnings(agent_state))
    warnings.extend(_event_stream_warnings(event_stream_stats or {}))
    return warnings


def _event_stream_warnings(event_stream_stats: dict[str, Any]) -> list[str]:
    warnings: list[str] = []
    if int(event_stream_stats.get("dropped_oldest", 0) or 0) > 0:
        warnings.append("event_stream_dropped_oldest")
    if int(event_stream_stats.get("dropped_newest", 0) or 0) > 0:
        warnings.append("event_stream_dropped_newest")
    if int(event_stream_stats.get("persist_failures", 0) or 0) > 0:
        warnings.append("event_stream_persist_failures")
    if int(event_stream_stats.get("durable_writer_errors", 0) or 0) > 0:
        warnings.append("event_stream_durable_writer_errors")
    if int(event_stream_stats.get("durable_enqueue_failures", 0) or 0) > 0:
        warnings.append("event_stream_durable_enqueue_failures")
    if int(event_stream_stats.get("critical_queue_blocked", 0) or 0) > 0:
        warnings.append("event_stream_critical_blocked")
    return warnings


def _health_severity(warnings: list[str], agent_state: str) -> str:
    """Classify overall controller health severity (green/yellow/red)."""
    if agent_state == AgentState.ERROR.value:
        return "red"

    red_markers = {
        "iteration_limit_reached",
        "budget_limit_reached",
        "circuit_breaker_tripped",
        "stuck_detector_triggered",
        "event_stream_persist_failures",
        "event_stream_durable_writer_errors",
        "event_stream_durable_enqueue_failures",
    }
    if any(marker in red_markers for marker in warnings):
        return "red"

    yellow_markers = {
        "budget_90_percent",
        "budget_80_percent",
        "budget_50_percent",
        "retry_pending",
        "circuit_breaker_near_limit",
        "event_stream_dropped_oldest",
        "event_stream_dropped_newest",
        "event_stream_critical_blocked",
    }
    if any(marker in yellow_markers for marker in warnings):
        return "yellow"

    return "green"


def _health_recommendations(warnings: list[str]) -> list[str]:
    """Translate warnings into concise operator actions."""
    recommendations: list[str] = []
    if "event_stream_persist_failures" in warnings:
        recommendations.append("inspect_event_storage_and_permissions")
    if "event_stream_durable_writer_errors" in warnings:
        recommendations.append("check_durable_writer_and_disk_health")
    if "event_stream_durable_enqueue_failures" in warnings:
        recommendations.append("reduce_event_pressure_or_raise_writer_capacity")
    if "event_stream_dropped_oldest" in warnings or "event_stream_dropped_newest" in warnings:
        recommendations.append("increase_event_queue_capacity_or_reduce_event_volume")
    if "event_stream_critical_blocked" in warnings:
        recommendations.append("investigate_delivery_worker_saturation")
    if "circuit_breaker_tripped" in warnings or "circuit_breaker_near_limit" in warnings:
        recommendations.append("review_recent_action_failures_and_risk_patterns")
    if "budget_90_percent" in warnings or "budget_limit_reached" in warnings:
        recommendations.append("adjust_budget_or_task_scope")
    if "iteration_limit_reached" in warnings:
        recommendations.append("increase_iteration_limit_or_refine_task_prompt")
    if "stuck_detector_triggered" in warnings:
        recommendations.append("inspect_looping_actions_and_add_guardrails")
    return recommendations


def _iteration_warnings(iteration: IterationHealth | None) -> list[str]:
    if iteration and iteration.limit_hit:
        return ["iteration_limit_reached"]
    return []


def _budget_warnings(budget: BudgetHealth | None) -> list[str]:
    if not budget:
        return []
    warnings: list[str] = []
    if budget.limit_hit:
        warnings.append("budget_limit_reached")
    elif (
        budget.current is not None
        and budget.max is not None
        and budget.max > 0
    ):
        pct = budget.current / budget.max
        if pct >= 0.9:
            warnings.append("budget_90_percent")
        elif pct >= 0.8:
            warnings.append("budget_80_percent")
        elif pct >= 0.5:
            warnings.append("budget_50_percent")
    return warnings


def _retry_warnings(retry: RetryHealth | None) -> list[str]:
    if retry and retry.pending:
        return ["retry_pending"]
    return []


def _circuit_warnings(circuit_breaker: CircuitBreakerHealth | None) -> list[str]:
    if circuit_breaker is None:
        return []
    last_check = circuit_breaker.last_check or {}
    if last_check.get("tripped"):
        return ["circuit_breaker_tripped"]
    if _circuit_near_limit(circuit_breaker):
        return ["circuit_breaker_near_limit"]
    return []


def _circuit_near_limit(circuit_breaker: CircuitBreakerHealth) -> bool:
    if (
        circuit_breaker.consecutive_errors is None
        or not circuit_breaker.max_consecutive_errors
    ):
        return False
    return (
        circuit_breaker.consecutive_errors
        >= circuit_breaker.max_consecutive_errors * 0.8
    )


def _stuck_warnings(is_stuck: bool) -> list[str]:
    return ["stuck_detector_triggered"] if is_stuck else []


def _agent_state_warnings(agent_state: str) -> list[str]:
    if agent_state == AgentState.ERROR.value:
        return ["agent_state_error"]
    return []


def _state_snapshot(state: Any, iteration, budget, pending_action) -> dict[str, Any]:
    return {
        "agent_state": _extract_agent_state(state),
        "last_error": getattr(state, "last_error", "") or "",
        "iteration": asdict(iteration) if iteration else None,
        "budget": asdict(budget) if budget else None,
        "pending_action": bool(pending_action),
    }


def _service_snapshot(retry, circuit_breaker, is_stuck) -> dict[str, Any]:
    return {
        "retry": asdict(retry) if retry else None,
        "circuit_breaker": asdict(circuit_breaker) if circuit_breaker else None,
        "stuck_detection": {"is_stuck": is_stuck},
    }


def _controller_state(controller: Any) -> Any:
    state = getattr(controller, "state", None)
    if not state:
        raise ValueError("Controller lacks state; cannot collect health snapshot")
    return state


def _health_components(controller: Any) -> tuple[
    Any,
    IterationHealth | None,
    BudgetHealth | None,
    RetryHealth | None,
    CircuitBreakerHealth | None,
    bool,
    dict[str, Any],
]:
    state = _controller_state(controller)
    iteration = _iteration_health(state)
    budget = _budget_health(state)
    retry = _retry_health(controller)
    circuit_breaker = _circuit_breaker_health(controller)
    stuck = _is_stuck(controller)
    event_stream_stats = _collect_event_stream_stats(controller)
    return state, iteration, budget, retry, circuit_breaker, stuck, event_stream_stats


def collect_controller_health(controller: Any) -> dict[str, Any]:
    """Collect a consolidated health snapshot for an AgentController."""
    _sync_budget_metrics(controller)
    (
        state,
        iteration,
        budget,
        retry,
        circuit_breaker,
        is_stuck,
        event_stream_stats,
    ) = _health_components(controller)

    agent_state_value = _extract_agent_state(state)
    warnings = _build_warnings(
        iteration,
        budget,
        retry,
        circuit_breaker,
        is_stuck,
        agent_state_value,
        event_stream_stats,
    )
    severity = _health_severity(warnings, agent_state_value)
    recommendations = _health_recommendations(warnings)

    pending_action = getattr(controller, "_pending_action", None)

    return {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "controller_id": getattr(controller, "id", None),
        "state": _state_snapshot(state, iteration, budget, pending_action),
        "severity": severity,
        "services": _service_snapshot(retry, circuit_breaker, is_stuck),
        "event_stream": event_stream_stats,
        "warnings": warnings,
        "recommendations": recommendations,
    }

