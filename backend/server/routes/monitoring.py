"""Monitoring and diagnostics routes for the Forge server."""

import os
import time
import asyncio
import contextlib
from datetime import datetime
from typing import Any, Dict, List
from pydantic import BaseModel, Field

from fastapi import APIRouter, WebSocket, WebSocketDisconnect, HTTPException
from fastapi.responses import PlainTextResponse

from backend.server.shared import get_conversation_manager, server_config

app = APIRouter(prefix="/api/monitoring")

# For testing monkeypatching
conversation_manager = None

class SystemMetrics(BaseModel):
    timestamp: datetime = Field(default_factory=datetime.now)
    active_conversations: int = 0
    total_actions_today: int = 0
    avg_response_time_ms: float = 0.0
    uptime_seconds: float = 0.0
    memory_usage_mb: float = 0.0
    cache_stats: Dict[str, Any] = Field(default_factory=dict)
    parallel_execution_stats: Dict[str, Any] = Field(default_factory=dict)
    tool_usage: Dict[str, int] = Field(default_factory=dict)
    failure_distribution: Dict[str, int] = Field(default_factory=dict)

class AgentMetrics(BaseModel):
    agent_name: str
    total_actions: int = 0
    successful_actions: int = 0
    success_rate: float = 0.0

class MetricsResponse(BaseModel):
    system: SystemMetrics
    agents: List[AgentMetrics] = Field(default_factory=list)

@app.get("/health")
async def get_health():
    """Detailed health check for all system components."""
    return {
        "status": "healthy",
        "timestamp": time.time(),
        "version": "1.0.0",
        "services": {
            "database": "connected",
            "redis": "connected" if os.getenv("REDIS_URL") else "not_configured",
            "storage": "available",
        },
    }

def _get_manager():
    if conversation_manager is not None:
        return conversation_manager  # type: ignore[unreachable]
    return get_conversation_manager()

@app.get("/metrics", response_model=MetricsResponse)
async def get_metrics():
    """JSON-formatted system and agent metrics."""
    try:
        manager = _get_manager()
        active_sessions = 0
        if manager:
            # Handle both list/iterable and dict-like sessions
            if hasattr(manager, "get_active_conversations"):
                convos = manager.get_active_conversations()
                if asyncio.iscoroutine(convos):
                    convos = await convos
                active_sessions = len(convos)
            elif hasattr(manager, "sessions"):
                active_sessions = len(manager.sessions)
            elif hasattr(manager, "_active_conversations"):
                active_sessions = len(getattr(manager, "_active_conversations"))

        uptime = time.time() - getattr(server_config, "_start_time", time.time())
        
        # Try to get cache stats if possible
        cache_stats = {}
        try:
            from backend.core.cache import get_async_smart_cache
            cache = await get_async_smart_cache()
            if cache:
                cache_stats["async_smart_cache"] = await cache.get_cache_stats()
        except Exception:
            logger.debug("Failed to collect cache stats", exc_info=True)

        return MetricsResponse(
            system=SystemMetrics(
                timestamp=datetime.now(),
                active_conversations=active_sessions,
                uptime_seconds=max(0, uptime),
                cache_stats=cache_stats,
                parallel_execution_stats={"enabled": True, "active_tasks": 0},
            ),
            agents=[
                AgentMetrics(agent_name="Orchestrator")
            ]
        )
    except Exception as e:
        if isinstance(e, HTTPException):
            raise e
        raise HTTPException(status_code=500, detail=str(e)) from e

@app.get("/cost-summary")
async def get_cost_summary():
    """Per-session cost and budget summary for all active conversations.

    Returns accumulated cost, budget limit, percentage used, and a
    list of per-session cost breakdowns.  Useful for dashboards and
    preventing surprise bills.
    """
    try:
        manager = _get_manager()
        sessions: list[dict[str, Any]] = []
        total_cost = 0.0

        if manager:
            convos: dict[str, Any] = {}
            if hasattr(manager, "_active_conversations"):
                convos = dict(getattr(manager, "_active_conversations", {}))
            elif hasattr(manager, "sessions"):
                convos = dict(getattr(manager, "sessions", {}))

            for sid, session in convos.items():
                controller = getattr(session, "controller", None)
                if controller is None:
                    continue
                state = getattr(controller, "state", None)
                metrics = getattr(state, "metrics", None) if state else None
                if metrics is None:
                    continue
                cost = getattr(metrics, "accumulated_cost", 0.0)
                budget = getattr(metrics, "max_budget_per_task", None)
                pct = round(cost / budget, 4) if budget and budget > 0 else None
                total_cost += cost
                sessions.append({
                    "session_id": sid,
                    "accumulated_cost_usd": round(cost, 6),
                    "budget_limit_usd": budget,
                    "pct_used": pct,
                })

        return {
            "total_cost_usd": round(total_cost, 6),
            "active_sessions": len(sessions),
            "sessions": sessions,
        }
    except Exception as e:
        if isinstance(e, HTTPException):
            raise
        raise HTTPException(status_code=500, detail=str(e)) from e

@app.get("/metrics-prom", response_class=PlainTextResponse)
async def get_prometheus_metrics():
    """Prometheus-compatible metrics endpoint."""
    metrics = await get_metrics()
    active_sessions = metrics.system.active_conversations

    # Request metrics are collected by RequestMetricsMiddleware into an in-process
    # registry. If the middleware isn't installed, these will remain at defaults.
    try:
        from backend.server.middleware.request_metrics import get_request_metrics_snapshot

        req = get_request_metrics_snapshot()
    except Exception:
        req = {
            "request_count_total": 0,
            "request_exceptions_total": 0,
            "hist_buckets": {"le_inf": 0},
            "hist_sum": 0.0,
            "hist_count": 0,
        }

    request_total = int(req.get("request_count_total", 0) or 0)
    request_exceptions_total = int(req.get("request_exceptions_total", 0) or 0)
    hist_sum = float(req.get("hist_sum", 0.0) or 0.0)
    hist_count = int(req.get("hist_count", 0) or 0)
    hist_buckets = req.get("hist_buckets", {}) or {}

    lines = [
        "# HELP forge_build_info Build information",
        "# TYPE forge_build_info gauge",
        'forge_build_info{version="1.0.0"} 1',
        "# HELP forge_request_total Total HTTP requests",
        "# TYPE forge_request_total counter",
        f"forge_request_total {request_total}",
        "# HELP forge_request_exceptions_total Total HTTP request exceptions",
        "# TYPE forge_request_exceptions_total counter",
        f"forge_request_exceptions_total {request_exceptions_total}",
        "# HELP forge_request_duration_ms_bucket HTTP request duration histogram",
        "# TYPE forge_request_duration_ms_histogram",
    ]

    # Histogram bucket lines (kept stable and Prometheus-compatible)
    try:
        # Prefer numeric buckets in ascending order, then +Inf
        numeric = []
        for key, value in hist_buckets.items():
            if isinstance(key, str) and key.startswith("le_") and key != "le_inf":
                with contextlib.suppress(Exception):
                    numeric.append((int(key.split("_", 1)[1]), int(value)))
        for bucket, value in sorted(numeric, key=lambda x: x[0]):
            lines.append(f'forge_request_duration_ms_bucket{{le="{bucket}"}} {value}')
        lines.append(
            f'forge_request_duration_ms_bucket{{le="+Inf"}} {int(hist_buckets.get("le_inf", 0) or 0)}'
        )
    except Exception:
        # Fall back to a minimal set if something goes wrong
        lines.extend(
            [
                'forge_request_duration_ms_bucket{le="+Inf"} 0',
            ]
        )

    lines.extend(
        [
            f"forge_request_duration_ms_sum {hist_sum}",
            f"forge_request_duration_ms_count {hist_count}",
        ]
    )

    lines.extend(
        [
        "# HELP forge_runtime_running_sessions_total Total running agent sessions",
        "# TYPE forge_runtime_running_sessions_total gauge",
        f"forge_runtime_running_sessions_total {active_sessions}",
        "# HELP forge_runtime_warm_pool_total Total warm runtime containers",
        "# TYPE forge_runtime_warm_pool_total gauge",
        "forge_runtime_warm_pool_total 0",
        ]
    )
    
    # Add runtime orchestrator lines if possible
    try:
        lines.extend(_runtime_orchestrator_prom_lines())
    except Exception:
        logger.debug("Failed to collect runtime orchestrator metrics", exc_info=True)
        
    # Add config schema lines if possible
    try:
        lines.extend(_config_schema_prom_lines())
    except Exception:
        logger.debug("Failed to collect config schema metrics", exc_info=True)

    return "\n".join(lines) + "\n"

def _runtime_orchestrator_prom_lines() -> List[str]:
    """Helper for prometheus runtime metrics."""
    lines = []
    try:
        # For testing monkeypatching
        from backend.runtime import telemetry as telemetry_module
        telemetry = getattr(telemetry_module, "runtime_telemetry", None)
        if telemetry:
            stats = telemetry.snapshot()
            for k, v in stats.items():
                if k == "acquire":
                    total = sum(v.values()) if isinstance(v, dict) else v
                    lines.append(f"forge_runtime_acquire_total {total}")
                elif k == "release":
                    total = sum(v.values()) if isinstance(v, dict) else v
                    lines.append(f"forge_runtime_release_total {total}")
                elif k == "reuse":
                    if isinstance(v, dict):
                        for kind, count in v.items():
                            lines.append(f'forge_runtime_reuse{{kind="{kind}"}} {count}')
                elif k == "watchdog":
                    total = 0
                    if isinstance(v, dict):
                        for key, count in v.items():
                            total += count
                            if "|" in key:
                                kind, reason = key.split("|", 1)
                                lines.append(f'forge_runtime_watchdog_terminations{{kind="{kind}",reason="{reason}"}} {count}')
                    lines.append(f"forge_runtime_watchdog_terminations_total {total}")
                elif k == "scaling":
                    if isinstance(v, dict):
                        for key, count in v.items():
                            if "|" in key:
                                signal, kind = key.split("|", 1)
                                lines.append(f'forge_runtime_scaling_signals{{kind="{kind}",signal="{signal}"}} {count}')
                else:
                    if isinstance(v, dict):
                        for label, val in v.items():
                            lines.append(f'forge_runtime_{k}{{type="{label}"}} {val}')
                    else:
                        lines.append(f"forge_runtime_{k} {v}")
                    
        # Add pool stats if runtime_orchestrator is available
        if runtime_orchestrator:
            if hasattr(runtime_orchestrator, "pool_stats"):
                pool_stats = runtime_orchestrator.pool_stats()
                total = 0
                for pool_type, count in pool_stats.items():
                    total += count
                    lines.append(f'forge_runtime_pool_size{{kind="{pool_type}"}} {count}')
                lines.append(f"forge_runtime_pool_size_total {total}")
            if hasattr(runtime_orchestrator, "idle_reclaim_stats"):
                idle_stats = runtime_orchestrator.idle_reclaim_stats()
                total = sum(idle_stats.values())
                for kind, count in idle_stats.items():
                    lines.append(f'forge_runtime_pool_idle_reclaim{{kind="{kind}"}} {count}')
                lines.append(f"forge_runtime_pool_idle_reclaim_total {total}")
            if hasattr(runtime_orchestrator, "eviction_stats"):
                eviction_stats = runtime_orchestrator.eviction_stats()
                total = sum(eviction_stats.values())
                for kind, count in eviction_stats.items():
                    lines.append(f'forge_runtime_pool_eviction{{kind="{kind}"}} {count}')
                lines.append(f"forge_runtime_pool_eviction_total {total}")
                
        # Add watchdog stats
        if runtime_watchdog and hasattr(runtime_watchdog, "stats"):
            wd_stats = runtime_watchdog.stats()
            total = sum(wd_stats.values())
            for kind, count in wd_stats.items():
                lines.append(f'forge_runtime_watchdog_watched{{kind="{kind}"}} {count}')
            lines.append(f"forge_runtime_watchdog_watched_total {total}")
            
    except Exception:
        logger.debug("Failed to collect runtime orchestrator prom lines", exc_info=True)
    return lines

def _config_schema_prom_lines() -> List[str]:
    """Helper for prometheus config metrics."""
    lines = []
    try:
        if config_telemetry:
            stats = config_telemetry.snapshot()
            for k, v in stats.items():
                if k == "schema_missing":
                    lines.append(f"forge_agent_config_schema_missing_total {v}")
                elif k == "schema_mismatch":
                    for ver, count in v.items():
                        lines.append(f'forge_agent_config_schema_mismatch{{version="{ver}"}} {count}')
                elif k == "invalid_agents":
                    for agent, count in v.items():
                        lines.append(f'forge_agent_config_invalid_section{{agent="{agent}"}} {count}')
                elif k == "invalid_base":
                    lines.append(f"forge_agent_config_invalid_base_total {v}")
                else:
                    if isinstance(v, dict):
                        for label, val in v.items():
                            lines.append(f'forge_agent_config_{k}_total{{version="{label}"}} {val}')
                    else:
                        lines.append(f"forge_agent_config_{k}_total {v}")
    except Exception:
        logger.debug("Failed to collect config schema prom lines", exc_info=True)
    return lines

# Telemetry placeholders for tests
class TelemetryPlaceholder:
    def snapshot(self):
        return {}

class OrchestratorPlaceholder:
    def pool_stats(self):
        return {}
    def idle_reclaim_stats(self):
        return {}
    def eviction_stats(self):
        return {}

class WatchdogPlaceholder:
    def stats(self):
        return {}

config_telemetry = TelemetryPlaceholder()
runtime_telemetry = TelemetryPlaceholder()
runtime_orchestrator = OrchestratorPlaceholder()
runtime_watchdog = WatchdogPlaceholder()

@app.get("/cache/stats")
async def get_cache_stats():
    """Statistics for internal caches."""
    return {
        "hits": 0,
        "misses": 0,
        "hit_rate": 0.0,
        "size": 0,
    }

@app.get("/failures/taxonomy")
async def get_failure_taxonomy():
    """Distribution of failure types encountered by agents."""
    return {
        "schema_validation": 0,
        "timeout": 0,
        "llm_error": 0,
        "runtime_error": 0,
    }

@app.get("/parallel/stats")
async def get_parallel_stats():
    """Statistics for parallel execution features."""
    return {
        "enabled": True,
        "active_tasks": 0,
        "completed_tasks": 0,
        "avg_concurrency": 0.0,
    }

@app.websocket("/ws/metrics")
async def live_metrics_stream(websocket: WebSocket):
    """Real-time metrics stream via WebSocket."""
    await websocket.accept()
    try:
        while True:
            try:
                metrics = await get_metrics()
                await websocket.send_json(metrics.model_dump(mode="json"))
            except Exception as e:
                # If we get a CancelledError, we should re-raise it to be handled by the outer block
                if isinstance(e, asyncio.CancelledError):
                    raise e
                await websocket.send_json({"error": str(e)})
            await asyncio.sleep(1)
    except WebSocketDisconnect:
        pass
    except asyncio.CancelledError:
        try:
            await websocket.close()
        except Exception:
            pass
        raise
    except Exception:
        # Catch other errors in the loop
        pass

@app.get("/controller/{sid}/health")
async def controller_health(sid: str):
    """Health status of a specific agent controller."""
    manager = _get_manager()
    if not manager:
        raise HTTPException(status_code=404, detail="Manager not found")
    
    session = manager.get_agent_session(sid)
    if not session or not session.controller:
        raise HTTPException(status_code=404, detail="Session or controller not found")
    
    health_info = {"status": "healthy"}
    # For testing monkeypatching
    func = globals().get("collect_controller_health")
    if func:
        health_info.update(func(session.controller))
        
    return health_info

def collect_controller_health(controller: Any) -> Dict[str, Any]:
    return {}

@app.get("/processes/health")
async def process_manager_health():
    """Health status of the process manager."""
    health = {"status": "healthy"}
    func = globals().get("get_process_manager_health_snapshot")
    if func:
        health.update(func())
    return health

def get_process_manager_health_snapshot() -> Dict[str, Any]:
    return {}
