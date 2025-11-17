"""Persistence backends for prompt optimization performance history."""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Iterable

from .models import PromptMetrics, PromptPerformance


class PromptHistoryStore:
    """In-memory store used by ``PerformanceTracker``."""

    def __init__(self) -> None:
        self._performance_data: list[PromptPerformance] = []
        self._variant_metrics: dict[str, PromptMetrics] = {}
        self._dirty = False
        self._backend_label = "memory"
        self._history_path: str | None = None
        self._auto_flush = False
        self._last_flush: datetime | None = None
        self._last_record_at: datetime | None = None

    # ------------------------------------------------------------------ #
    # Performance data helpers
    # ------------------------------------------------------------------ #
    def add_performance(self, performance: PromptPerformance) -> None:
        self._performance_data.append(performance)
        self._dirty = True
        self._last_record_at = performance.timestamp

    def get_all_performances(self) -> list[PromptPerformance]:
        return self._performance_data

    def get_variant_performances(
        self, variant_id: str, limit: int | None = None
    ) -> list[PromptPerformance]:
        items = [p for p in self._performance_data if p.variant_id == variant_id]
        if limit is not None and limit > 0:
            return items[-limit:]
        return items

    def get_variant_ids_for_prompt(self, prompt_id: str) -> list[str]:
        return list({p.variant_id for p in self._performance_data if p.prompt_id == prompt_id})

    def get_variant_ids_for_category(self, category: str) -> list[str]:
        return list(
            {
                p.variant_id
                for p in self._performance_data
                if p.category.value == category
            }
        )

    # ------------------------------------------------------------------ #
    # Variant metrics helpers
    # ------------------------------------------------------------------ #
    def ensure_variant_metrics(self, variant_id: str, weights: dict[str, float]) -> PromptMetrics:
        if variant_id not in self._variant_metrics:
            self._variant_metrics[variant_id] = PromptMetrics(
                success_weight=weights["success"],
                time_weight=weights["time"],
                error_weight=weights["error"],
                cost_weight=weights["cost"],
            )
            self._dirty = True
        return self._variant_metrics[variant_id]

    def get_variant_metrics(self, variant_id: str) -> PromptMetrics | None:
        return self._variant_metrics.get(variant_id)

    def iter_metrics(self) -> Iterable[tuple[str, PromptMetrics]]:
        return self._variant_metrics.items()

    # ------------------------------------------------------------------ #
    # Persistence helpers
    # ------------------------------------------------------------------ #
    def clear(self) -> None:
        self._performance_data.clear()
        self._variant_metrics.clear()
        self._dirty = False

    def export_payload(self) -> dict:
        return {
            "performance_data": [p.to_dict() for p in self._performance_data],
            "variant_metrics": {
                vid: metrics.to_dict() for vid, metrics in self._variant_metrics.items()
            },
        }

    def import_payload(self, data: dict) -> None:
        self.clear()
        for perf_data in data.get("performance_data", []):
            self._performance_data.append(PromptPerformance.from_dict(perf_data))

        for vid, metrics_data in data.get("variant_metrics", {}).items():
            self._variant_metrics[vid] = PromptMetrics(**metrics_data)
        self._dirty = False
        self._last_flush = datetime.utcnow()

    # ------------------------------------------------------------------ #
    # Hooks for subclasses
    # ------------------------------------------------------------------ #
    def flush(self) -> None:
        """Persist to backing store (no-op for in-memory store)."""
        self._dirty = False
        self._last_flush = datetime.utcnow()

    def on_record(self) -> None:
        """Hook invoked by tracker after each record."""
        if self._dirty:
            self.flush()

    def get_stats(self, total_records: int) -> dict[str, object]:
        """Return backend/state information for health snapshots."""
        return {
            "backend": self._backend_label,
            "history_path": self._history_path,
            "auto_flush": self._auto_flush,
            "dirty": self._dirty,
            "last_record_at": self._last_record_at.isoformat()
            if self._last_record_at
            else None,
            "last_flush_at": self._last_flush.isoformat() if self._last_flush else None,
            "total_records": total_records,
        }


class JsonPromptHistoryStore(PromptHistoryStore):
    """JSON file-backed history store."""

    def __init__(self, path: str | Path, auto_flush: bool = False) -> None:
        super().__init__()
        self.path = Path(path)
        self._auto_flush = auto_flush
        self._backend_label = "json"
        self._history_path = str(self.path)
        if self.path.exists():
            self._load_from_disk()

    def _load_from_disk(self) -> None:
        try:
            with self.path.open("r", encoding="utf-8") as fh:
                data = json.load(fh)
            self.import_payload(data)
            self._dirty = False
        except FileNotFoundError:
            self._dirty = False

    def flush(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.path.open("w", encoding="utf-8") as fh:
            json.dump(self.export_payload(), fh, indent=2)
        super().flush()

    def on_record(self) -> None:
        if self._auto_flush:
            self.flush()

