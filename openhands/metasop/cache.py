"""Context-hash based step result cache.

Lightweight LRU cache (thread-safe) used to short-circuit step execution
when an identical deterministic context recurs. Designed to be dependency-free
while allowing optional persistence to a directory.

Persistence model (if step_cache_dir configured):
- Each entry stored as <cache_dir>/<context_hash>.json
- An index file (index.json) maintains insertion order for warm reload
- Eviction updates on-disk state best-effort; IO failures are non-fatal

NOTE: We intentionally do not store *raw* event streams; only the
minimal artifact + provenance necessary to reconstruct an executed_cached
step event and artifact injection into the orchestrator.
"""

from __future__ import annotations

import json
import os
import threading
import time
from collections import OrderedDict
from dataclasses import asdict, dataclass
from typing import Any


@dataclass
class StepCacheEntry:
    context_hash: str
    step_id: str
    role: str
    artifact_content: Any
    artifact_hash: str | None
    step_hash: str | None
    rationale: str | None
    model_name: str | None
    total_tokens: int | None
    diff_fingerprint: str | None
    created_ts: float

    def to_json(self) -> dict[str, Any]:
        return asdict(self)

    __test__ = False

    @classmethod
    def from_json(cls, data: dict[str, Any]) -> StepCacheEntry:
        return cls(
            context_hash=data["context_hash"],
            step_id=data["step_id"],
            role=data["role"],
            artifact_content=data.get("artifact_content"),
            artifact_hash=data.get("artifact_hash"),
            step_hash=data.get("step_hash"),
            rationale=data.get("rationale"),
            model_name=data.get("model_name"),
            total_tokens=data.get("total_tokens"),
            diff_fingerprint=data.get("diff_fingerprint"),
            created_ts=data.get("created_ts") or time.time(),
        )


class StepCache:

    def __init__(
        self,
        max_entries: int | None = 256,
        cache_dir: str | None = None,
        ttl_seconds: int | None = None,
        min_tokens_threshold: int | None = None,
        exclude_roles: list[str] | None = None,
    ) -> None:
        self.max_entries = max_entries or 0
        self.cache_dir = cache_dir
        self.ttl_seconds = ttl_seconds
        self.min_tokens_threshold = min_tokens_threshold
        self.exclude_roles = {r.lower() for r in exclude_roles or []}
        self._lock = threading.Lock()
        self._store: OrderedDict[str, StepCacheEntry] = OrderedDict()
        self._hits = 0
        self._misses = 0
        self._stores = 0
        self._evictions = 0
        if self.cache_dir:
            try:
                os.makedirs(self.cache_dir, exist_ok=True)
                self._warm_load()
            except Exception:
                pass

    def get(self, context_hash: str, role: str) -> StepCacheEntry | None:
        with self._lock:
            entry = self._store.get(context_hash)
            if not entry:
                self._misses += 1
                return None
            if role.lower() in self.exclude_roles:
                self._misses += 1
                return None
            if self.ttl_seconds is not None and time.time() - entry.created_ts > self.ttl_seconds:
                self._store.pop(context_hash, None)
                self._misses += 1
                try:
                    if self.cache_dir:
                        path = os.path.join(self.cache_dir, f"{context_hash}.json")
                        if os.path.exists(path):
                            os.remove(path)
                except Exception:
                    pass
                return None
            self._store.move_to_end(context_hash, last=True)
            self._hits += 1
            return StepCacheEntry(**entry.to_json())

    def get_by_fingerprint(self, diff_fingerprint: str, role: str) -> StepCacheEntry | None:
        """Lookup a cache entry by its diff_fingerprint (best-effort).

        This scans the in-memory store for a matching fingerprint and returns
        the first non-expired entry matching role and fingerprint.
        """
        if not diff_fingerprint:
            return None
        with self._lock:
            for key, entry in reversed(self._store.items()):
                try:
                    if role.lower() in self.exclude_roles:
                        return None
                    if entry.diff_fingerprint and entry.diff_fingerprint == diff_fingerprint:
                        if self.ttl_seconds is not None and time.time() - entry.created_ts > self.ttl_seconds:
                            continue
                        self._store.move_to_end(key, last=True)
                        self._hits += 1
                        return StepCacheEntry(**entry.to_json())
                except Exception:
                    continue
        self._misses += 1
        return None

    def put(self, entry: StepCacheEntry) -> bool:
        """Insert entry if allowed.

        Returns True if stored, False otherwise.
        Conditions:
          - caching enabled (max_entries > 0)
          - role not excluded
          - min_tokens_threshold satisfied (if set)
        """
        # Validate entry eligibility
        if not self._is_entry_eligible(entry):
            return False

        # Store entry and handle eviction
        with self._lock:
            evicted_entries = self._store_entry(entry)

            # Persist to disk if cache directory is configured
            if self.cache_dir:
                self._persist_cache_operations(entry, evicted_entries)

        return True

    def _is_entry_eligible(self, entry: StepCacheEntry) -> bool:
        """Check if entry meets eligibility criteria for caching."""
        # Check if caching is enabled
        if self.max_entries <= 0:
            return False

        # Check if role is excluded
        if entry.role.lower() in self.exclude_roles:
            return False

        # Check minimum tokens threshold
        return self.min_tokens_threshold is None or (
            isinstance(entry.total_tokens, int) and entry.total_tokens >= self.min_tokens_threshold
        )

    def _store_entry(self, entry: StepCacheEntry) -> list[tuple[str, StepCacheEntry]]:
        """Store entry in cache and handle eviction if needed."""
        self._store[entry.context_hash] = entry
        self._store.move_to_end(entry.context_hash, last=True)
        self._stores += 1

        return self._evict_excess_entries() if self.max_entries and len(self._store) > self.max_entries else []

    def _evict_excess_entries(self) -> list[tuple[str, StepCacheEntry]]:
        """Evict excess entries from cache."""
        evicted_entries: list[tuple[str, StepCacheEntry]] = []

        while len(self._store) > self.max_entries:
            k, v = self._store.popitem(last=False)
            evicted_entries.append((k, v))
            self._evictions += 1

        return evicted_entries

    def _persist_cache_operations(
        self, entry: StepCacheEntry, evicted_entries: list[tuple[str, StepCacheEntry]],
    ) -> None:
        """Persist cache operations to disk."""
        try:
            # Persist the new entry
            self._persist_entry(entry)

            # Remove evicted entries from disk
            if evicted_entries:
                self._remove_evicted_entries_from_disk(evicted_entries)

            # Update index
            self._persist_index()

        except Exception:
            # Silently ignore persistence errors to avoid breaking cache functionality
            pass

    def _remove_evicted_entries_from_disk(self, evicted_entries: list[tuple[str, StepCacheEntry]]) -> None:
        """Remove evicted entries from disk storage."""
        for k, _ in evicted_entries:
            path = os.path.join(self.cache_dir, f"{k}.json")
            if os.path.exists(path):
                os.remove(path)

    def stats(self) -> dict[str, Any]:
        with self._lock:
            return {
                "entries": len(self._store),
                "hits": self._hits,
                "misses": self._misses,
                "stores": self._stores,
                "evictions": self._evictions,
                "ttl_seconds": self.ttl_seconds,
                "max_entries": self.max_entries,
            }

    def _persist_entry(self, entry: StepCacheEntry) -> None:
        if not self.cache_dir:
            return
        path = os.path.join(self.cache_dir, f"{entry.context_hash}.json")
        try:
            with open(path, "w", encoding="utf-8") as f:
                json.dump(entry.to_json(), f, ensure_ascii=False, separators=(",", ":"), sort_keys=True)
        except Exception:
            pass

    def _persist_index(self) -> None:
        if not self.cache_dir:
            return
        idx_path = os.path.join(self.cache_dir, "index.json")
        try:
            with open(idx_path, "w", encoding="utf-8") as f:
                json.dump({"order": list(self._store.keys())}, f, separators=(",", ":"), sort_keys=True)
        except Exception:
            pass

    def _warm_load(self) -> None:
        """Warm load cache entries from disk.

        Loads cache entries according to index order, respecting max_entries and TTL.
        """
        order = self._load_cache_index()
        self._load_cache_entries(order)

    def _load_cache_index(self) -> list[str]:
        """Load cache index with entry order.

        Returns:
            List of cache keys in order
        """
        idx_path = os.path.join(self.cache_dir, "index.json")
        try:
            if os.path.exists(idx_path):
                with open(idx_path, encoding="utf-8") as f:
                    data = json.load(f)
                    return data.get("order") or []
        except Exception:
            pass
        return []

    def _load_cache_entries(self, order: list[str]) -> None:
        """Load cache entries from disk.

        Args:
            order: List of cache keys to load
        """
        loaded = 0
        for key in order:
            if self.max_entries and loaded >= self.max_entries:
                break

            if self._load_single_entry(key):
                loaded += 1

    def _load_single_entry(self, key: str) -> bool:
        """Load a single cache entry.

        Args:
            key: Cache key to load

        Returns:
            True if entry was loaded successfully
        """
        path = os.path.join(self.cache_dir, f"{key}.json")
        try:
            if not os.path.exists(path):
                return False

            with open(path, encoding="utf-8") as f:
                data = json.load(f)
                entry = StepCacheEntry.from_json(data)

                # Check TTL
                if self.ttl_seconds is not None and time.time() - entry.created_ts > self.ttl_seconds:
                    return False

                self._store[key] = entry
                return True
        except Exception:
            return False


__all__ = ["StepCache", "StepCacheEntry"]
