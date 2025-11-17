"""Health snapshot helpers for prompt optimization subsystems."""

from __future__ import annotations

from dataclasses import dataclass, asdict
from datetime import datetime
from typing import Any


@dataclass
class TrackerHealth:
    total_performances: int
    variants_tracked: int
    store: dict[str, Any]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class RealtimeHealth:
    system_status: dict[str, Any]
    streaming_engine: dict[str, Any] | None
    live_optimizer: dict[str, Any] | None
    monitor: dict[str, Any] | None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class PromptOptimizationHealthSnapshot:
    timestamp: str
    registry: dict[str, Any]
    tracker: TrackerHealth
    storage: dict[str, Any] | None
    realtime: RealtimeHealth | None
    warnings: list[str]

    def to_dict(self) -> dict[str, Any]:
        snapshot = asdict(self)
        snapshot["tracker"] = self.tracker.to_dict()
        if self.realtime:
            snapshot["realtime"] = self.realtime.to_dict()
        return snapshot


_DEFAULT_STORE_STATS = {
    "backend": "unknown",
    "history_path": None,
    "auto_flush": False,
    "dirty": False,
    "last_record_at": None,
    "last_flush_at": None,
    "total_records": 0,
}


def _safe_registry_stats(registry: Any) -> dict[str, Any]:
    try:
        if hasattr(registry, "get_statistics"):
            return registry.get_statistics()
    except Exception:
        pass
    return {
        "total_variants": 0,
        "total_prompts": 0,
        "active_variants": 0,
        "testing_variants": 0,
        "category_counts": {},
    }


def _safe_tracker_stats(tracker: Any) -> dict[str, Any]:
    try:
        if hasattr(tracker, "get_health_snapshot"):
            return tracker.get_health_snapshot()
    except Exception:
        pass
    return {
        "total_performances": 0,
        "variants_tracked": 0,
        "store": dict(_DEFAULT_STORE_STATS),
    }


def collect_health_snapshot(
    registry,
    tracker,
    storage: Any | None = None,
    realtime_system: Any | None = None,
) -> dict[str, Any]:
    """Collect a consolidated health snapshot from the provided components."""
    registry_stats = _safe_registry_stats(registry)
    tracker_health = _build_tracker_health(tracker)
    storage_stats = storage.get_health_snapshot() if storage else None
    warnings = _collect_warnings(tracker_health)
    realtime_stats, realtime_warnings = _collect_realtime_stats(realtime_system)
    warnings.extend(realtime_warnings)

    snapshot = PromptOptimizationHealthSnapshot(
        timestamp=datetime.utcnow().isoformat(),
        registry=registry_stats,
        tracker=tracker_health,
        storage=storage_stats,
        realtime=realtime_stats,
        warnings=warnings,
    )
    return snapshot.to_dict()


def _build_tracker_health(tracker: Any) -> TrackerHealth:
    tracker_stats = _safe_tracker_stats(tracker)
    return TrackerHealth(
        total_performances=tracker_stats["total_performances"],
        variants_tracked=tracker_stats["variants_tracked"],
        store=tracker_stats.get("store", dict(_DEFAULT_STORE_STATS)),
    )


def _collect_warnings(tracker_health: TrackerHealth) -> list[str]:
    warnings: list[str] = []
    store_stats = tracker_health.store or {}
    if store_stats.get("dirty") and not store_stats.get("auto_flush"):
        warnings.append("history_store_pending_flush")
    return warnings


def _collect_realtime_stats(
    realtime_system: Any | None,
) -> tuple[RealtimeHealth | None, list[str]]:
    if realtime_system is None:
        return None, []

    streaming_stats = _safe_streaming_stats(realtime_system)
    live_stats = _safe_live_optimizer_stats(realtime_system)
    monitor_stats = _safe_monitor_stats(realtime_system)
    system_status = realtime_system.get_system_status()

    realtime_stats = RealtimeHealth(
        system_status=system_status,
        streaming_engine=streaming_stats,
        live_optimizer=live_stats,
        monitor=monitor_stats,
    )

    warnings = []
    if streaming_stats:
        max_size = streaming_stats.get("max_queue_size") or 1
        queue_size = streaming_stats.get("queue_size", 0)
        if max_size and queue_size / max_size >= 0.8:
            warnings.append("streaming_queue_high_watermark")

    return realtime_stats, warnings


def _safe_streaming_stats(realtime_system: Any) -> dict[str, Any] | None:
    streaming_engine = getattr(realtime_system, "streaming_engine", None)
    if streaming_engine:
        return streaming_engine.get_processing_stats()
    return None


def _safe_live_optimizer_stats(realtime_system: Any) -> dict[str, Any]:
    live_optimizer = getattr(realtime_system, "live_optimizer", None)
    if live_optimizer:
        return getattr(live_optimizer, "optimization_stats", {})
    return {}


def _safe_monitor_stats(realtime_system: Any) -> dict[str, Any] | None:
    monitor = getattr(realtime_system, "real_time_monitor", None)
    if monitor:
        return monitor.get_monitoring_stats()
    return None

