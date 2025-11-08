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
from fastapi import APIRouter, HTTPException, WebSocket, WebSocketDisconnect
from pydantic import BaseModel
from typing import Dict, List, Optional, Any
from datetime import datetime

from forge.core.logger import forge_logger as logger
from forge.server.shared import conversation_manager

app = APIRouter(prefix="/api/monitoring")


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
        active_convos = []
        try:
            # Try to get active conversations if method exists
            if hasattr(conversation_manager, 'get_active_conversations'):
                active_convos = await conversation_manager.get_active_conversations()
            elif hasattr(conversation_manager, 'sessions'):
                # Fallback: use sessions dict
                active_convos = list(conversation_manager.sessions.values())
        except Exception as e:
            logger.warning(f"Could not get active conversations: {e}")
        
        # 🚀 ASYNC SMART CACHE STATS
        smart_cache_stats = {"redis_available": False, "cache_type": "memory", "cached_users": 0}
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
            }
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
            metasop=metasop_metrics
        )
        
    except Exception as e:
        logger.error(f"Error getting metrics: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/health")
async def get_health() -> Dict[str, Any]:
    """Get system health status.

    Returns:
        Health check information

    """
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "services": {
            "backend": "up",
            "mcp": "up",  # TODO: Check actual MCP status
            "redis": "unknown",  # TODO: Check Redis if configured
        }
    }


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
        }
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
    await websocket.accept()
    logger.info("WebSocket client connected to live metrics stream")
    
    try:
        while True:
            # Get current metrics
            try:
                metrics = await get_metrics()
                
                # Send to client
                await websocket.send_json({
                    "timestamp": datetime.now().isoformat(),
                    "metrics": metrics.model_dump() if hasattr(metrics, 'model_dump') else metrics
                })
                
            except Exception as e:
                logger.error(f"Error collecting metrics for WebSocket: {e}")
                await websocket.send_json({
                    "error": "Failed to collect metrics",
                    "timestamp": datetime.now().isoformat()
                })
            
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
