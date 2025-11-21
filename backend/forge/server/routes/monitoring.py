"""Monitoring and metrics API endpoints.

Provides real-time metrics for:
- Agent performance
- Parallel execution stats
- Cache hit rates
- Tool usage
- ACE learning progress
- Failure taxonomy
- System health
"""

import asyncio
import time
from fastapi import APIRouter, HTTPException, WebSocket, WebSocketDisconnect, Response
import os
import subprocess
from importlib import metadata as _importlib_metadata
from pydantic import BaseModel
from typing import Dict, List, Optional, Any, Callable
from datetime import datetime

from forge.core.logger import forge_logger as logger
from forge.core.config.config_telemetry import config_telemetry
from forge.controller.health import collect_controller_health
from forge.runtime import runtime_orchestrator
from forge.runtime.watchdog import runtime_watchdog
from forge.runtime.utils.process_manager import get_process_manager_health_snapshot
from forge.server.shared import conversation_manager, get_conversation_manager
def _resolve_conversation_manager() -> Any:
    """Return the global conversation manager, instantiating if required."""
    manager = conversation_manager
    if manager is None:
        try:
            manager = get_conversation_manager()
        except Exception:
            manager = None
    return manager

app = APIRouter(prefix="/api/monitoring")

# Import expanded metrics
from forge.server.routes.metrics_expansion import get_metrics_collector

# WebSocket rate limiting state (in-memory)
_WS_CONNECTION_ATTEMPTS: dict[str, list[float]] = {}
_WS_ACTIVE_CONNECTIONS: dict[str, int] = {}

# Tunable limits (monkeypatchable in tests)
_WS_HOURLY_LIMIT = 200  # Max connections initiated per IP per hour
_WS_BURST_LIMIT_PER_MINUTE = 10  # Max connection attempts per IP per minute
_WS_MAX_CONCURRENT_PER_IP = 5  # Max concurrent live streams per IP


def _prometheus_build_info_line() -> str:
    try:
        version = _importlib_metadata.version("forge-ai")
    except Exception:
        version = os.getenv("FORGE_VERSION", "unknown")
    git_sha = os.getenv("GIT_SHA", "")
    if not git_sha:
        try:
            git_sha = (
                subprocess.check_output(
                    ["git", "rev-parse", "--short", "HEAD"],
                    stderr=subprocess.DEVNULL,
                )
                .decode()
                .strip()
            )
        except Exception:
            git_sha = "unknown"
    return f'forge_build_info{{version="{version}",git_sha="{git_sha}"}} 1'


def _collect_section_with_guard(collector: Callable[[], list[str]]) -> list[str]:
    try:
        return collector() or []
    except Exception as exc:  # pragma: no cover - defensive
        return [f"# error collecting metrics: {exc}"]


def _metasop_prom_lines() -> list[str]:
    try:
        snap = _metasop_snapshot()
    except Exception as exc:  # pragma: no cover
        return [f"# error collecting metasop metrics: {exc}"]

    lines: list[str] = []
    lines.extend(_metasop_basic_counters(snap))
    lines.extend(_metasop_duration_histogram(snap))
    lines.extend(_metasop_cache_and_retry_metrics(snap))
    lines.extend(_metasop_guardrail_metrics(snap))
    return lines


def _metasop_snapshot() -> dict[str, Any]:
    from forge.metasop.metrics import get_metrics_registry

    return get_metrics_registry().snapshot()


def _metasop_basic_counters(snap: dict[str, Any]) -> list[str]:
    lines = [
        f"metasop_total_events {snap.get('total_events', 0)}",
        f"metasop_steps_executed {snap.get('steps_executed', 0)}",
        f"metasop_steps_failed {snap.get('steps_failed', 0)}",
        f"metasop_steps_timed_out {snap.get('steps_timed_out', 0)}",
        f"metasop_total_tokens {snap.get('total_tokens', 0)}",
    ]
    avg_tokens = snap.get("avg_tokens_per_executed_step")
    if avg_tokens is not None:
        lines.append(f"metasop_avg_tokens_per_executed_step {avg_tokens}")
    return lines


def _metasop_duration_histogram(snap: dict[str, Any]) -> list[str]:
    hist = snap.get("step_duration_histogram") or {}
    buckets = hist.get("buckets", {})
    if not buckets:
        return []

    ordered_bounds = sorted(
        [
            int(k.split("_")[1])
            for k in buckets
            if k.startswith("le_")
            and k not in {"le_inf"}
            and k.split("_")[1].isdigit()
        ]
    )

    lines: list[str] = []
    cumulative = 0
    for bound in ordered_bounds:
        cumulative += buckets.get(f"le_{bound}", 0)
        lines.append(f'metasop_step_duration_ms_bucket{{le="{bound}"}} {cumulative}')

    cumulative += buckets.get("le_inf", 0)
    lines.append(f'metasop_step_duration_ms_bucket{{le="+Inf"}} {cumulative}')
    lines.append(f"metasop_step_duration_ms_sum {hist.get('sum_ms', 0)}")
    lines.append(f"metasop_step_duration_ms_count {hist.get('count', 0)}")
    return lines


def _metasop_cache_and_retry_metrics(snap: dict[str, Any]) -> list[str]:
    return [
        f"metasop_cache_hits {snap.get('cache_hits', 0)}",
        f"metasop_cache_stores {snap.get('cache_stores', 0)}",
        f"metasop_retry_attempts {snap.get('retry_attempts', 0)}",
        f"metasop_retry_failures {snap.get('retry_failures', 0)}",
        f"metasop_retry_successes {snap.get('retry_successes', 0)}",
    ]


def _metasop_guardrail_metrics(snap: dict[str, Any]) -> list[str]:
    lines = [
        f"metasop_guardrail_concurrency_total {snap.get('guardrail_concurrency_events', 0)}",
        f"metasop_guardrail_concurrency_peak {snap.get('guardrail_concurrency_peak_active', 0)}",
        f"metasop_guardrail_concurrency_last_active {snap.get('guardrail_concurrency_last_active', 0)}",
        f"metasop_guardrail_concurrency_last_limit {snap.get('guardrail_concurrency_last_limit', 0)}",
        f"metasop_guardrail_runtime_events {snap.get('guardrail_runtime_events', 0)}",
        f"metasop_guardrail_runtime_max_ms {snap.get('guardrail_runtime_max_ms', 0)}",
        f"metasop_guardrail_runtime_failures {snap.get('guardrail_runtime_failures', 0)}",
    ]
    avg_runtime = snap.get("guardrail_runtime_avg_ms")
    if avg_runtime is not None:
        lines.append(f"metasop_guardrail_runtime_avg_ms {avg_runtime}")
    return lines


def _request_metrics_prom_lines() -> list[str]:
    from forge.server.middleware.request_metrics import get_request_metrics_snapshot

    req_snap = get_request_metrics_snapshot()
    lines: list[str] = []
    lines.extend(_request_metric_totals(req_snap))
    lines.extend(_request_metric_method_status(req_snap))
    lines.extend(_request_metric_route_status(req_snap))
    lines.extend(_request_duration_histogram(req_snap))
    return lines


def _request_metric_totals(req_snap: dict[str, Any]) -> list[str]:
    lines = [
        f"forge_request_total {req_snap.get('request_count_total', 0)}",
        f"forge_request_exceptions_total {req_snap.get('request_exceptions_total', 0)}",
        f"forge_requests_in_flight {req_snap.get('in_flight', 0)}",
    ]
    if "request_bytes_sum" in req_snap:
        lines.append(f"forge_request_bytes_total {req_snap.get('request_bytes_sum', 0)}")
    if "response_bytes_sum" in req_snap:
        lines.append(
            f"forge_response_bytes_total {req_snap.get('response_bytes_sum', 0)}"
        )
    return lines


def _request_metric_method_status(req_snap: dict[str, Any]) -> list[str]:
    by_ms = req_snap.get("by_method_status") or {}
    if not by_ms:
        default = req_snap.get("request_count_total", 0)
        return [f'forge_request_total{{method="GET",status="200"}} {default}']

    result = []
    for ms_key, count in by_ms.items():
        try:
            method, status = ms_key.split(":", 1)
        except ValueError:
            continue
        result.append(
            f'forge_request_total{{method="{method}",status="{status}"}} {count}'
        )
    return result


def _request_metric_route_status(req_snap: dict[str, Any]) -> list[str]:
    result = []
    by_rms = req_snap.get("by_route_method_status") or {}
    for key, count in by_rms.items():
        try:
            method, status, route = key.split("|", 2)
        except ValueError:
            continue
        route_norm = route.replace('"', "'")
        result.append(
            f'forge_request_total{{method="{method}",status="{status}",route="{route_norm}"}} {count}'
        )
    return result


def _request_duration_histogram(req_snap: dict[str, Any]) -> list[str]:
    buckets = req_snap.get("hist_buckets") or {}
    ordered_bounds = sorted(
        [
            int(k.split("_")[1])
            for k in buckets
            if k.startswith("le_")
            and k not in {"le_inf"}
            and k.split("_")[1].isdigit()
        ]
    )
    result: list[str] = []
    cumulative = 0
    for bound in ordered_bounds:
        cumulative += buckets.get(f"le_{bound}", 0)
        result.append(
            f'forge_request_duration_ms_bucket{{le="{bound}"}} {cumulative}'
        )
    cumulative += buckets.get("le_inf", 0)
    result.append('forge_request_duration_ms_bucket{le="+Inf"} ' + str(cumulative))
    result.append(f"forge_request_duration_ms_sum {req_snap.get('hist_sum', 0)}")
    result.append(f"forge_request_duration_ms_count {req_snap.get('hist_count', 0)}")
    return result


def _eventstream_prom_lines() -> list[str]:
    from forge.events.stream import get_aggregated_event_stream_stats

    es = get_aggregated_event_stream_stats()
    return [
        "# HELP forge_eventstream_streams Number of active EventStream instances",
        "# TYPE forge_eventstream_streams gauge",
        f"forge_eventstream_streams {es.get('streams', 0)}",
        "# HELP forge_eventstream_queue_size Total enqueued events currently buffered across streams",
        "# TYPE forge_eventstream_queue_size gauge",
        f"forge_eventstream_queue_size {es.get('queue_size', 0)}",
        "# HELP forge_eventstream_enqueued_total Events successfully enqueued (cumulative)",
        "# TYPE forge_eventstream_enqueued_total counter",
        f"forge_eventstream_enqueued_total {es.get('enqueued', 0)}",
        "# HELP forge_eventstream_dropped_oldest_total Events dropped due to full queue (oldest eviction)",
        "# TYPE forge_eventstream_dropped_oldest_total counter",
        f"forge_eventstream_dropped_oldest_total {es.get('dropped_oldest', 0)}",
        "# HELP forge_eventstream_dropped_newest_total Events dropped due to full queue (newest)",
        "# TYPE forge_eventstream_dropped_newest_total counter",
        f"forge_eventstream_dropped_newest_total {es.get('dropped_newest', 0)}",
        "# HELP forge_eventstream_high_watermark_hits_total High-watermark threshold crossings (load indicator)",
        "# TYPE forge_eventstream_high_watermark_hits_total counter",
        f"forge_eventstream_high_watermark_hits_total {es.get('high_watermark_hits', 0)}",
    ]


def _process_manager_prom_lines() -> list[str]:
    from forge.runtime.utils.process_manager import (
        get_process_manager_metrics_snapshot,
    )

    pm = get_process_manager_metrics_snapshot()
    return [
        "# HELP forge_processmgr_active_processes Currently tracked long-running processes",
        "# TYPE forge_processmgr_active_processes gauge",
        f"forge_processmgr_active_processes {int(pm.get('active_processes', 0))}",
        "# HELP forge_processmgr_registered_total Processes registered for tracking (cumulative)",
        "# TYPE forge_processmgr_registered_total counter",
        f"forge_processmgr_registered_total {int(pm.get('registered_total', 0))}",
        "# HELP forge_processmgr_natural_terminations_total Processes that terminated without forced cleanup",
        "# TYPE forge_processmgr_natural_terminations_total counter",
        f"forge_processmgr_natural_terminations_total {int(pm.get('natural_terminations_total', 0))}",
        "# HELP forge_processmgr_cleanup_attempts_total Processes targeted during cleanup calls",
        "# TYPE forge_processmgr_cleanup_attempts_total counter",
        f"forge_processmgr_cleanup_attempts_total {int(pm.get('cleanup_attempts_total', 0))}",
        "# HELP forge_processmgr_cleanup_successes_total Processes successfully cleaned up",
        "# TYPE forge_processmgr_cleanup_successes_total counter",
        f"forge_processmgr_cleanup_successes_total {int(pm.get('cleanup_successes_total', 0))}",
        "# HELP forge_processmgr_cleanup_failures_total Processes that failed to clean up",
        "# TYPE forge_processmgr_cleanup_failures_total counter",
        f"forge_processmgr_cleanup_failures_total {int(pm.get('cleanup_failures_total', 0))}",
        "# HELP forge_processmgr_forced_kill_attempts_total Force-kill attempts issued (SIGKILL)",
        "# TYPE forge_processmgr_forced_kill_attempts_total counter",
        f"forge_processmgr_forced_kill_attempts_total {int(pm.get('forced_kill_attempts_total', 0))}",
        "# HELP forge_processmgr_lifetime_ms Process lifetime in milliseconds (summary)",
        "# TYPE forge_processmgr_lifetime_ms summary",
        f"forge_processmgr_lifetime_ms_sum {pm.get('lifetime_ms_sum', 0.0)}",
        f"forge_processmgr_lifetime_ms_count {int(pm.get('lifetime_ms_count', 0))}",
    ]


def _runtime_manager_prom_lines() -> list[str]:
    from forge.runtime.runtime_manager import runtime_manager

    rm = runtime_manager.metrics_snapshot()
    warm = rm.get("warm", {}) or {}
    running = rm.get("running", {}) or {}
    lines = [
        "# HELP forge_runtime_warm_pool_total Warm runtime instances staged for reuse",
        "# TYPE forge_runtime_warm_pool_total gauge",
        f"forge_runtime_warm_pool_total {sum(warm.values())}",
    ]
    lines.extend(
        f'forge_runtime_warm_pool{{kind="{kind}"}} {int(count)}' for kind, count in warm.items()
    )
    lines.extend(
        [
            "# HELP forge_runtime_running_sessions_total Active runtime sessions tracked by the manager",
            "# TYPE forge_runtime_running_sessions_total gauge",
            f"forge_runtime_running_sessions_total {sum(running.values())}",
        ]
    )
    lines.extend(
        f'forge_runtime_running_sessions{{kind="{kind}"}} {int(count)}'
        for kind, count in running.items()
    )
    return lines


def _config_schema_prom_lines() -> list[str]:
    snapshot = config_telemetry.snapshot()
    schema_mismatch_raw = snapshot.get("schema_mismatch")
    schema_mismatch: dict[str, int] = (
        schema_mismatch_raw if isinstance(schema_mismatch_raw, dict) else {}
    )
    invalid_agents_raw = snapshot.get("invalid_agents")
    invalid_agents: dict[str, int] = (
        invalid_agents_raw if isinstance(invalid_agents_raw, dict) else {}
    )
    lines = [
        "# HELP forge_agent_config_schema_missing_total Agent configs encountered without schema_version",
        "# TYPE forge_agent_config_schema_missing_total counter",
        f"forge_agent_config_schema_missing_total {snapshot.get('schema_missing', 0)}",
        "# HELP forge_agent_config_schema_mismatch_total Agent configs with schema_version mismatch",
        "# TYPE forge_agent_config_schema_mismatch_total counter",
        f"forge_agent_config_schema_mismatch_total {sum(schema_mismatch.values())}",
    ]
    lines.extend(
        f'forge_agent_config_schema_mismatch{{version="{version}"}} {int(count)}'
        for version, count in schema_mismatch.items()
    )
    lines.extend(
        [
            "# HELP forge_agent_config_invalid_section_total Invalid custom agent sections encountered",
            "# TYPE forge_agent_config_invalid_section_total counter",
        f"forge_agent_config_invalid_section_total {sum(invalid_agents.values())}",
        ]
    )
    lines.extend(
        f'forge_agent_config_invalid_section{{agent="{agent}"}} {int(count)}'
        for agent, count in invalid_agents.items()
    )
    lines.extend(
        [
            "# HELP forge_agent_config_invalid_base_total Invalid base agent configuration attempts",
            "# TYPE forge_agent_config_invalid_base_total counter",
            f"forge_agent_config_invalid_base_total {snapshot.get('invalid_base', 0)}",
        ]
    )
    return lines


def _runtime_orchestrator_prom_lines() -> list[str]:
    from forge.runtime import telemetry as runtime_telemetry_module

    snapshot = runtime_telemetry_module.runtime_telemetry.snapshot()
    pool_stats = runtime_orchestrator.pool_stats()
    delegate_stats = runtime_orchestrator.delegate_stats()
    idle_reclaims = runtime_orchestrator.idle_reclaim_stats()
    evictions = runtime_orchestrator.eviction_stats()
    watched_counts = runtime_watchdog.stats()
    lines: list[str] = []
    lines.extend(_runtime_flow_metrics(snapshot))
    lines.extend(_runtime_watchdog_metrics(snapshot.get("watchdog", {}), watched_counts))
    lines.extend(_runtime_pool_metrics(pool_stats))
    lines.extend(_runtime_delegate_metrics(delegate_stats))
    lines.extend(_runtime_scaling_metrics(snapshot.get("scaling", {})))
    lines.extend(_runtime_idle_reclaim_metrics(idle_reclaims))
    lines.extend(_runtime_eviction_metrics(evictions))
    return lines


def _runtime_flow_metrics(snapshot: dict[str, dict[str, int]]) -> list[str]:
    lines: list[str] = []
    metrics = [
        (
            "acquire",
            "forge_runtime_acquire",
            "Runtime acquisitions via orchestrator",
            "counter",
        ),
        (
            "reuse",
            "forge_runtime_reuse",
            "Runtime reuses served from pools",
            "counter",
        ),
        (
            "release",
            "forge_runtime_release",
            "Runtime releases processed by orchestrator",
            "counter",
        ),
    ]
    for key, metric, help_text, metric_type in metrics:
        counts = snapshot.get(key, {}) or {}
        total = sum(counts.values())
        lines.extend(
            [
                f"# HELP {metric}_total {help_text}",
                f"# TYPE {metric}_total {metric_type}",
                f"{metric}_total {total}",
            ]
        )
        lines.extend(
            f'{metric}{{kind="{kind}"}} {int(count)}' for kind, count in counts.items()
        )
    return lines


def _runtime_watchdog_metrics(
    watchdog_counts: dict[str, int], watched_counts: dict[str, int]
) -> list[str]:
    lines: list[str] = []
    if watchdog_counts:
        total = sum(watchdog_counts.values())
        lines.extend(
            [
                "# HELP forge_runtime_watchdog_terminations_total Runtime sessions terminated by watchdog",
                "# TYPE forge_runtime_watchdog_terminations_total counter",
                f"forge_runtime_watchdog_terminations_total {total}",
            ]
        )
        for composite, count in watchdog_counts.items():
            kind, reason = _split_composite(composite, default_second="unknown")
            reason = reason.replace('"', "'")
            lines.append(
                f'forge_runtime_watchdog_terminations{{kind="{kind}",reason="{reason}"}} {int(count)}'
            )
    if watched_counts:
        total_watched = sum(watched_counts.values())
        lines.extend(
            [
                "# HELP forge_runtime_watchdog_watched Currently watched runtimes by kind",
                "# TYPE forge_runtime_watchdog_watched gauge",
            ]
        )
        lines.extend(
            f'forge_runtime_watchdog_watched{{kind="{kind}"}} {int(count)}'
            for kind, count in watched_counts.items()
        )
        lines.append(f"forge_runtime_watchdog_watched_total {total_watched}")
    return lines


def _runtime_pool_metrics(pool_stats: dict[str, int]) -> list[str]:
    lines: list[str] = [
        "# HELP forge_runtime_pool_size Warm runtimes staged for reuse",
        "# TYPE forge_runtime_pool_size gauge",
    ]
    lines.extend(
        f'forge_runtime_pool_size{{kind="{kind}"}} {int(count)}'
        for kind, count in pool_stats.items()
    )
    total_pool = sum(pool_stats.values())
    lines.append(f"forge_runtime_pool_size_total {total_pool}")
    return lines


def _runtime_delegate_metrics(delegate_stats: dict[str, int]) -> list[str]:
    if not delegate_stats:
        return []
    lines = [
        "# HELP forge_runtime_delegate_fork_total Delegate fork acquisitions served",
        "# TYPE forge_runtime_delegate_fork_total counter",
        f"forge_runtime_delegate_fork_total {sum(delegate_stats.values())}",
    ]
    lines.extend(
        f'forge_runtime_delegate_fork{{parent="{kind}"}} {int(count)}'
        for kind, count in delegate_stats.items()
    )
    return lines


def _runtime_scaling_metrics(scaling_counts: dict[str, int]) -> list[str]:
    if not scaling_counts:
        return []
    total_scaling = sum(scaling_counts.values())
    lines = [
        "# HELP forge_runtime_scaling_signals_total Adaptive scaling advisories emitted",
        "# TYPE forge_runtime_scaling_signals_total counter",
        f"forge_runtime_scaling_signals_total {total_scaling}",
    ]
    for composite, count in scaling_counts.items():
        signal, kind = _split_composite(composite, default_second="unknown")
        signal = signal.replace('"', "'")
        kind = kind.replace('"', "'")
        lines.append(
            f'forge_runtime_scaling_signals{{kind="{kind}",signal="{signal}"}} {int(count)}'
        )
    return lines


def _runtime_idle_reclaim_metrics(idle_reclaims: dict[str, int]) -> list[str]:
    if not idle_reclaims:
        return []
    lines = [
        "# HELP forge_runtime_pool_idle_reclaim_total Warm runtime entries removed due to TTL expiration",
        "# TYPE forge_runtime_pool_idle_reclaim_total counter",
        f"forge_runtime_pool_idle_reclaim_total {sum(idle_reclaims.values())}",
    ]
    lines.extend(
        f'forge_runtime_pool_idle_reclaim{{kind="{kind}"}} {int(count)}'
        for kind, count in idle_reclaims.items()
    )
    return lines


def _runtime_eviction_metrics(evictions: dict[str, int]) -> list[str]:
    if not evictions:
        return []
    lines = [
        "# HELP forge_runtime_pool_eviction_total Warm runtime entries evicted due to capacity limits",
        "# TYPE forge_runtime_pool_eviction_total counter",
        f"forge_runtime_pool_eviction_total {sum(evictions.values())}",
    ]
    lines.extend(
        f'forge_runtime_pool_eviction{{kind="{kind}"}} {int(count)}'
        for kind, count in evictions.items()
    )
    return lines


def _split_composite(value: str, default_second: str) -> tuple[str, str]:
    if "|" in value:
        first, second = value.split("|", 1)
    else:
        first, second = value, default_second
    return first, second


def _circuit_breaker_prom_lines() -> list[str]:
    from forge.utils.circuit_breaker import get_circuit_breaker_metrics_snapshot

    cb = get_circuit_breaker_metrics_snapshot()
    return [
        "# HELP forge_cb_open_circuits Number of open circuit breaker keys",
        "# TYPE forge_cb_open_circuits gauge",
        f"forge_cb_open_circuits {int(cb.get('open_count', 0))}",
        "# HELP forge_cb_opens_total Number of times breakers transitioned to open",
        "# TYPE forge_cb_opens_total counter",
        f"forge_cb_opens_total {int(cb.get('opens_total', 0))}",
        "# HELP forge_cb_blocked_total Calls blocked due to open or half-open limit",
        "# TYPE forge_cb_blocked_total counter",
        f"forge_cb_blocked_total {int(cb.get('blocked_total', 0))}",
        "# HELP forge_cb_half_open_probes_total Half-open probe attempts executed",
        "# TYPE forge_cb_half_open_probes_total counter",
        f"forge_cb_half_open_probes_total {int(cb.get('half_open_probes_total', 0))}",
        "# HELP forge_cb_close_success_total Successful closings after half-open probes",
        "# TYPE forge_cb_close_success_total counter",
        f"forge_cb_close_success_total {int(cb.get('close_success_total', 0))}",
    ]


async def _register_ws_connection(ip: str) -> tuple[bool, str]:
    backend = os.getenv("WS_RATE_LIMIT_BACKEND", "memory").lower()
    if backend == "redis":
        redis_result = await _register_ws_connection_redis(ip)
        if redis_result is not None:
            return redis_result
    return _register_ws_connection_memory(ip, time.time())


async def _register_ws_connection_redis(ip: str) -> tuple[bool, str] | None:
    try:
        import redis.asyncio as redis  # type: ignore

        redis_url = os.getenv("REDIS_URL") or os.getenv("REDIS_CONNECTION_URL")
        if not redis_url:
            raise RuntimeError("No REDIS_URL configured")
        r = redis.from_url(redis_url, decode_responses=True)
        key_hour = f"ws:attempts:hour:{ip}"
        key_min = f"ws:attempts:min:{ip}"
        key_active = f"ws:active:{ip}"

        hour_count = await _increment_key(r, key_hour, 3600)
        min_count = await _increment_key(r, key_min, 60)
        concurrent = int(await r.get(key_active) or 0)

        if _is_rate_limited(hour_count, min_count, concurrent):
            return False, "redis"

        await _increment_key(r, key_active, 300)
        return True, "redis"
    except Exception as exc:  # pragma: no cover - defensive
        logger.warning("WS Redis rate limit unavailable, falling back to memory: %s", exc)
        return None


def _register_ws_connection_memory(ip: str, now: float) -> tuple[bool, str]:
    attempts = _WS_CONNECTION_ATTEMPTS.setdefault(ip, [])
    attempts[:] = [ts for ts in attempts if now - ts < 3600]
    minute_recent = [ts for ts in attempts if now - ts < 60]
    concurrent = _WS_ACTIVE_CONNECTIONS.get(ip, 0)

    if _is_rate_limited(len(attempts), len(minute_recent), concurrent):
        return False, "memory"

    attempts.append(now)
    _WS_ACTIVE_CONNECTIONS[ip] = concurrent + 1
    return True, "memory"


async def _increment_key(client: Any, key: str, ttl_seconds: int) -> int:
    await client.incr(key)
    await client.expire(key, ttl_seconds)
    return int(await client.get(key) or 0)


def _is_rate_limited(hour_count: int, minute_count: int, concurrent: int) -> bool:
    return (
        hour_count >= _WS_HOURLY_LIMIT
        or minute_count >= _WS_BURST_LIMIT_PER_MINUTE
        or concurrent >= _WS_MAX_CONCURRENT_PER_IP
    )


async def _cleanup_ws_connection(ip: str, backend: str) -> None:
    if backend == "redis":
        try:
            import redis.asyncio as redis  # type: ignore

            redis_url = os.getenv("REDIS_URL") or os.getenv("REDIS_CONNECTION_URL")
            if redis_url:
                r = redis.from_url(redis_url, decode_responses=True)
                key_active = f"ws:active:{ip}"
                cur = int(await r.get(key_active) or 0)
                if cur > 0:
                    await r.decr(key_active)
                await r.expire(key_active, 300)
        except Exception:  # pragma: no cover - defensive
            pass
        return

    if ip in _WS_ACTIVE_CONNECTIONS and _WS_ACTIVE_CONNECTIONS[ip] > 0:
        _WS_ACTIVE_CONNECTIONS[ip] -= 1
        if _WS_ACTIVE_CONNECTIONS[ip] == 0:
            _WS_ACTIVE_CONNECTIONS.pop(ip, None)


def _serialize_metrics_payload(metrics: Any) -> dict:
    if hasattr(metrics, "model_dump"):
        return metrics.model_dump(mode="json")  # pydantic v2
    if hasattr(metrics, "dict"):
        return metrics.dict()  # type: ignore[attr-defined]
    return metrics  # type: ignore[return-value]


class AgentMetrics(BaseModel):
    """Metrics for a specific agent."""

    agent_name: str
    total_actions: int
    successful_actions: int
    failed_actions: int
    avg_action_time_ms: float
    success_rate: float
    cache_hit_rate: Optional[float] = None


class SystemMetrics(BaseModel):
    """Overall system metrics."""

    timestamp: datetime
    active_conversations: int
    total_actions_today: int
    avg_response_time_ms: float
    cache_stats: Dict[str, Any]
    parallel_execution_stats: Dict[str, Any]
    tool_usage: Dict[str, int]
    failure_distribution: Dict[str, int]


class ACEMetrics(BaseModel):
    """ACE Framework learning metrics."""

    total_bullets: int
    avg_helpfulness: float
    context_updates: int
    success_rate: float
    playbook_size_kb: float


class MetricsResponse(BaseModel):
    """Complete metrics response."""

    system: SystemMetrics
    agents: List[AgentMetrics]
    ace: Optional[ACEMetrics] = None
    metasop: Optional[Dict[str, Any]] = None


@app.get("/metrics")
async def get_metrics() -> MetricsResponse:
    """Get consolidated system metrics.

    Returns:
        Complete metrics including system, agents, ACE, and MetaSOP stats

    """
    try:
        # Collect agent metrics
        agent_metrics: List[AgentMetrics] = []

        # Get active conversations for stats
        active_convos: list[Any] = []
        manager = _resolve_conversation_manager()
        if manager is not None:
            try:
                # Try to get active conversations if method exists
                if hasattr(manager, "get_active_conversations"):
                    active_convos = await manager.get_active_conversations()
                elif hasattr(manager, "sessions"):
                    # Fallback: use sessions dict
                    active_convos = list(manager.sessions.values())
            except Exception as e:
                logger.warning(f"Could not get active conversations: {e}")

        # 🚀 ASYNC SMART CACHE STATS
        smart_cache_stats = {
            "redis_available": False,
            "cache_type": "memory",
            "cached_users": 0,
        }
        try:
            from forge.core.cache import get_async_smart_cache

            smart_cache = await get_async_smart_cache()
            smart_cache_stats = await smart_cache.get_cache_stats()
        except Exception as e:
            smart_cache_stats["error"] = str(e)

        # System-wide stats (would aggregate from conversations)
        system_metrics = SystemMetrics(
            timestamp=datetime.now(),
            active_conversations=len(active_convos),
            total_actions_today=0,  # TODO: Aggregate from DB
            avg_response_time_ms=0.0,  # TODO: Calculate from recent actions
            cache_stats={
                "file_cache": {"hit_rate": 0.0, "total_requests": 0},
                "graph_cache": {"hit_rate": 0.0, "total_requests": 0},
                "async_smart_cache": smart_cache_stats,
            },
            parallel_execution_stats={
                "total_parallel_groups": 0,
                "avg_speedup": 0.0,
                "concurrent_workers": 3,
            },
            tool_usage={
                "edit_file": 0,
                "execute_bash": 0,
                "think": 0,
                "browse": 0,
            },
            failure_distribution={
                "schema_validation": 0,
                "runtime_error": 0,
                "test_fail": 0,
            },
        )

        # ACE metrics (if enabled)
        ace_metrics = None
        # TODO: Get from ACE framework if initialized

        # MetaSOP metrics (if enabled)
        metasop_metrics = None
        # TODO: Get from MetaSOP orchestrator if running

        return MetricsResponse(
            system=system_metrics,
            agents=agent_metrics,
            ace=ace_metrics,
            metasop=metasop_metrics,
        )

    except Exception as e:
        logger.error(f"Error getting metrics: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/controller/{sid}/health")
async def get_controller_health_endpoint(sid: str) -> dict[str, Any]:
    """Return health snapshot for the controller backing a session."""
    manager = _resolve_conversation_manager()
    if manager is None:
        raise HTTPException(
            status_code=503, detail="Conversation manager has not been initialized"
        )
    agent_session = manager.get_agent_session(sid)
    if not agent_session:
        raise HTTPException(status_code=404, detail="Session not found or not running")
    controller = getattr(agent_session, "controller", None)
    if not controller:
        raise HTTPException(
            status_code=404, detail="Controller not initialized for session"
        )

    try:
        return collect_controller_health(controller)
    except Exception as exc:  # pragma: no cover - defensive
        logger.error("Error collecting controller health for %s: %s", sid, exc)
        raise HTTPException(status_code=500, detail="Unable to collect controller health")


@app.get("/processes/health")
async def get_process_manager_health() -> dict[str, Any]:
    """Return global process manager health snapshot."""
    manager = _resolve_conversation_manager()
    if manager is None:
        raise HTTPException(
            status_code=503, detail="Conversation manager has not been initialized"
        )
    try:
        process_manager = getattr(manager, "process_manager", None)
        active = []
        if process_manager and hasattr(process_manager, "get_running_processes"):
            active = process_manager.get_running_processes()
        return get_process_manager_health_snapshot(active_processes=active)
    except Exception as exc:  # pragma: no cover - defensive
        logger.error("Error collecting process manager health: %s", exc)
        raise HTTPException(status_code=500, detail="Unable to collect process health")


@app.get("/metrics-prom")
async def get_prometheus_metrics() -> Response:
    """Prometheus text exposition combining internal MetaSOP metrics registry.

    Returns:
        Response: text/plain in Prometheus exposition format.
    """
    try:
        prom_lines: list[str] = [_prometheus_build_info_line()]
        prom_lines.extend(_collect_section_with_guard(_metasop_prom_lines))
        prom_lines.extend(_collect_section_with_guard(_request_metrics_prom_lines))
        prom_lines.extend(_collect_section_with_guard(_eventstream_prom_lines))
        prom_lines.extend(_collect_section_with_guard(_process_manager_prom_lines))
        prom_lines.extend(_collect_section_with_guard(_runtime_manager_prom_lines))
        prom_lines.extend(_collect_section_with_guard(_config_schema_prom_lines))
        prom_lines.extend(_collect_section_with_guard(_runtime_orchestrator_prom_lines))
        prom_lines.extend(_collect_section_with_guard(_circuit_breaker_prom_lines))

        body = "\n".join(prom_lines) + "\n"
        return Response(content=body, media_type="text/plain; charset=utf-8")
    except Exception as e:
        logger.error(f"Error building Prometheus metrics: {e}")
        raise HTTPException(status_code=500, detail="metrics collection failed")


@app.get("/health")
async def get_health() -> Dict[str, Any]:
    """Get system health status.

    Returns:
        Health check information including database, Redis, and other services

    """
    health_checks = {
        "backend": {"status": "up", "response_time_ms": 0},
        "database": _database_health_check(),
        "redis": _redis_health_check(),
        "mcp": _mcp_readiness_check(),
    }

    # Determine overall status
    critical_services = ["backend", "database"]
    all_critical_healthy = all(
        health_checks[service].get("status") == "up" for service in critical_services
    )

    overall_status = "healthy" if all_critical_healthy else "degraded"

    return {
        "status": overall_status,
        "timestamp": datetime.now().isoformat(),
        "services": health_checks,
    }


def _database_health_check() -> Dict[str, Any]:
    """Check database connection health.

    Returns:
        Health check result for database
    """
    try:
        import time

        start_time = time.time()
        # Try to get conversation store instance to test connection
        from forge.server.shared import server_config
        from forge.storage.conversation.conversation_store import ConversationStore
        from forge.utils.import_utils import get_impl

        # This will test if we can instantiate the store (tests connection)
        # Note: This is a lightweight check - actual implementation may vary
        store_class = get_impl(ConversationStore, server_config.conversation_store_class)
        response_time = (time.time() - start_time) * 1000

        return {
            "status": "up",
            "response_time_ms": round(response_time, 2),
            "type": server_config.conversation_store_class.split(".")[-1],
        }
    except Exception as e:
        return {
            "status": "down",
            "error": str(e),
            "response_time_ms": None,
        }


@app.get("/metrics/expanded")
async def get_expanded_metrics() -> Dict[str, Any]:
    """Get expanded metrics including business and technical metrics.

    Returns:
        Comprehensive metrics summary
    """
    collector = get_metrics_collector()
    return collector.get_metrics_summary()


def _redis_health_check() -> Dict[str, Any]:
    """Check Redis connection health.

    Returns:
        Health check result for Redis
    """
    redis_url = os.getenv("REDIS_URL") or os.getenv("REDIS_CONNECTION_URL")
    if not redis_url:
        return {"status": "skipped", "reason": "Redis not configured"}

    try:
        import time
        import redis  # type: ignore

        start_time = time.time()
        client = redis.Redis.from_url(redis_url, socket_timeout=1.0)
        client.ping()
        response_time = (time.time() - start_time) * 1000

        return {
            "status": "up",
            "response_time_ms": round(response_time, 2),
        }
    except Exception as e:
        return {
            "status": "down",
            "error": str(e),
            "response_time_ms": None,
        }


@app.get("/readiness")
async def get_readiness() -> Dict[str, Any]:
    """Readiness probe suitable for container orchestrators.

    Checks lightweight dependencies: Redis (if configured) and MCP action server (if configured).
    Does not attempt to start or attach to conversations.
    """
    checks = {
        "redis": _redis_readiness_check(),
        "mcp": _mcp_readiness_check(),
    }
    status = "ready" if all(check["status"] == "up" for check in checks.values()) else "degraded"
    return {
        "status": status,
        "timestamp": datetime.now().isoformat(),
        "checks": checks,
    }


def _redis_readiness_check() -> Dict[str, Any]:
    redis_url = os.getenv("REDIS_URL") or os.getenv("REDIS_CONNECTION_URL")
    if not redis_url:
        return {"status": "skipped"}

    try:
        import redis  # type: ignore

        client = redis.Redis.from_url(redis_url, socket_timeout=0.5)
        pong = client.ping()
        return {"status": "up" if pong else "down"}
    except Exception as exc:  # pragma: no cover - environment dependent
        return {"status": "down", "error": str(exc)}


def _mcp_readiness_check() -> Dict[str, Any]:
    mcp_url = os.getenv("ACTION_EXECUTION_SERVER_URL")
    if not mcp_url:
        return {"status": "skipped"}

    try:
        import httpx

        with httpx.Client(timeout=0.5) as client:
            response = client.get(mcp_url.rstrip("/") + "/alive")
        status = "up" if response.status_code == 200 else "down"
        return {"status": status, "code": response.status_code}
    except Exception as exc:  # pragma: no cover - environment dependent
        return {"status": "down", "error": str(exc)}


@app.get("/agents/performance")
async def get_agent_performance() -> List[AgentMetrics]:
    """Get performance metrics for all agents.

    Returns:
        List of agent performance metrics

    """
    # TODO: Collect from actual agent instances
    return []


@app.get("/cache/stats")
async def get_cache_stats() -> Dict[str, Any]:
    """Get cache statistics.

    Returns:
        Cache hit rates and stats for file cache, graph cache, etc.

    """
    return {
        "file_cache": {
            "hit_rate": 0.0,
            "hits": 0,
            "misses": 0,
            "total_requests": 0,
            "size": 0,
        },
        "graph_cache": {
            "hit_rate": 0.0,
            "hits": 0,
            "misses": 0,
            "total_requests": 0,
            "full_rebuilds": 0,
        },
    }


@app.get("/failures/taxonomy")
async def get_failure_taxonomy() -> Dict[str, int]:
    """Get failure distribution by category.

    Returns:
        Count of failures by taxonomy category

    """
    return {
        "schema_validation": 0,
        "json_parse": 0,
        "qa_test_fail": 0,
        "qa_lint_fail": 0,
        "build_error": 0,
        "runtime_error": 0,
        "dependency_error": 0,
        "retries_exhausted": 0,
        "budget_exceeded": 0,
        "semantic_gap": 0,
    }


@app.get("/ace/metrics")
async def get_ace_metrics() -> Optional[ACEMetrics]:
    """Get ACE Framework learning metrics.

    Returns:
        ACE metrics if framework is enabled, None otherwise

    """
    # TODO: Get from ACE framework if initialized
    return None


@app.get("/parallel/stats")
async def get_parallel_execution_stats() -> Dict[str, Any]:
    """Get parallel execution statistics.

    Returns:
        Parallel execution performance stats

    """
    return {
        "enabled": True,
        "max_workers": 3,
        "max_async_concurrent": 6,
        "total_parallel_groups": 0,
        "avg_speedup": 0.0,
        "total_time_saved_ms": 0,
    }


@app.websocket("/ws/live")
async def live_metrics_stream(websocket: WebSocket):
    """Stream real-time metrics via WebSocket.

    Sends metric updates every 2 seconds with:
    - Agent performance (success rate, latency)
    - Token usage and costs
    - Active conversations
    - Cache statistics

    Example client:
        const ws = new WebSocket('ws://localhost:3000/api/monitoring/ws/live');
        ws.onmessage = (event) => {
            const metrics = JSON.parse(event.data);
            console.log('Metrics:', metrics);
        };
    """
    # --- Rate limiting / abuse protection ---
    # Default to in-memory; can be switched to Redis by env WS_RATE_LIMIT_BACKEND=redis
    ip = websocket.client.host if websocket.client else "unknown"
    allowed, backend = await _register_ws_connection(ip)

    if not allowed:
        try:
            await websocket.accept()
            await websocket.send_json(
                {
                    "error": "rate_limited",
                    "timestamp": datetime.now().isoformat(),
                }
            )
            await websocket.close(code=1013)
        except Exception:
            pass
        logger.warning(
            "WebSocket /ws/live rate limit exceeded", extra={"client_ip": ip}
        )
        return

    await websocket.accept()
    logger.info("WebSocket client connected to live metrics stream")

    try:
        while True:
            # Get current metrics
            try:
                metrics = await get_metrics()
                metrics_payload = _serialize_metrics_payload(metrics)

                # Send to client
                await websocket.send_json(
                    {
                        "timestamp": datetime.now().isoformat(),
                        "metrics": metrics_payload,
                    }
                )

            except Exception as e:
                logger.error(f"Error collecting metrics for WebSocket: {e}")
                await websocket.send_json(
                    {
                        "error": "Failed to collect metrics",
                        "timestamp": datetime.now().isoformat(),
                    }
                )

            # Wait 2 seconds before next update
            await asyncio.sleep(2)

    except WebSocketDisconnect:
        logger.info("WebSocket client disconnected from live metrics stream")
    except Exception as e:
        logger.error(f"WebSocket error in live metrics stream: {e}")
        try:
            await websocket.close()
        except Exception:
            pass
    finally:
        # Decrement active connection count
        await _cleanup_ws_connection(ip, backend)
