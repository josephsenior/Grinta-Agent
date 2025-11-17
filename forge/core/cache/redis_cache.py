"""Redis-based distributed cache for multi-user scaling.

Provides shared caching across multiple backend instances for 1000+ concurrent users.
Falls back to local cache if Redis unavailable.
"""

from __future__ import annotations

import json
import os
import pickle
from collections.abc import Mapping
from typing import Any, Optional, cast
from datetime import timedelta

from forge.core.logger import forge_logger as logger

# Optional Redis dependency (graceful degradation)
try:
    import redis
    from redis import Redis, ConnectionPool

    REDIS_AVAILABLE = True
except ImportError:
    REDIS_AVAILABLE = False
    logger.warning("Redis not available. Install with: pip install redis")


class DistributedCache:
    """Distributed cache using Redis for multi-user scaling.

    Features:
    - Shared cache across multiple backend instances
    - TTL-based expiration
    - LRU eviction (configured in Redis)
    - Atomic operations
    - Connection pooling
    - Automatic fallback to local dict if Redis unavailable

    Perfect for:
    - 1000+ concurrent users
    - Multi-instance deployments
    - Shared file/graph caching
    - Session data
    """

    def __init__(
        self,
        prefix: str = "forge",
        host: str | None = None,
        port: int = 6379,
        password: str | None = None,
        db: int = 0,
        ttl_seconds: int = 3600,
        max_connections: int = 100,  # ⚡ PERFORMANCE: Increased for 1000+ users
    ) -> None:
        """Initialize distributed cache.

        Args:
            prefix: Key prefix for namespacing
            host: Redis host (reads from REDIS_HOST env if None)
            port: Redis port
            password: Redis password (reads from REDIS_PASSWORD env if None)
            db: Redis database number
            ttl_seconds: Default TTL for cached items
            max_connections: Max connection pool size

        """
        self.prefix = prefix
        self.ttl_seconds = ttl_seconds
        self.enabled = REDIS_AVAILABLE
        self.client: Optional[Redis] = None
        self._local_fallback: dict[str, Any] = {}

        # Stats
        self.stats = {
            "hits": 0,
            "misses": 0,
            "sets": 0,
            "deletes": 0,
            "errors": 0,
        }

        if not REDIS_AVAILABLE:
            logger.warning(
                f"Redis not available, using local fallback cache for {prefix}"
            )
            return

        # Get connection details from environment
        host = host or os.getenv("REDIS_HOST")
        if not host:
            logger.warning(
                f"REDIS_HOST not set, using local fallback cache for {prefix}"
            )
            self.enabled = False
            return

        password = password or os.getenv("REDIS_PASSWORD") or None

        try:
            # Create connection pool for efficiency
            pool = ConnectionPool(
                host=host,
                port=port,
                password=password,
                db=db,
                max_connections=max_connections,
                socket_connect_timeout=5,
                socket_timeout=5,
                decode_responses=False,  # We'll handle encoding
            )

            self.client = Redis(connection_pool=pool)

            # Test connection
            self.client.ping()
            logger.info(
                f"✅ Redis distributed cache initialized for {prefix} (ttl={ttl_seconds}s)"
            )
            logger.info(
                f"   Connected to {host}:{port}, max_connections={max_connections}"
            )

        except Exception as e:
            logger.error(f"Failed to connect to Redis: {e}")
            logger.warning(f"Falling back to local cache for {prefix}")
            self.enabled = False
            self.client = None

    def _make_key(self, key: str) -> str:
        """Create prefixed key."""
        return f"{self.prefix}:{key}"

    def get(self, key: str) -> Any | None:
        """Get value from cache.

        Args:
            key: Cache key

        Returns:
            Cached value or None if not found/expired

        """
        if not self.enabled or not self.client:
            # Local fallback
            value = self._local_fallback.get(key)
            if value is not None:
                self.stats["hits"] += 1
            else:
                self.stats["misses"] += 1
            return value

        try:
            redis_key = self._make_key(key)
            data = self.client.get(redis_key)

            if data is None:
                self.stats["misses"] += 1
                return None

            self.stats["hits"] += 1

            # Deserialize (supports both JSON and pickle)
            try:
                decoded = cast(bytes, data).decode("utf-8")
                return json.loads(decoded)
            except (json.JSONDecodeError, UnicodeDecodeError):
                return pickle.loads(cast(bytes, data))

        except Exception as e:
            logger.error(f"Redis GET error for {key}: {e}")
            self.stats["errors"] += 1
            return None

    def set(self, key: str, value: Any, ttl: int | None = None) -> bool:
        """Set value in cache.

        Args:
            key: Cache key
            value: Value to cache
            ttl: Time-to-live in seconds (uses default if None)

        Returns:
            True if successful, False otherwise

        """
        if not self.enabled or not self.client:
            # Local fallback
            self._local_fallback[key] = value
            self.stats["sets"] += 1
            return True

        try:
            redis_key = self._make_key(key)
            ttl = ttl if ttl is not None else self.ttl_seconds

            # Serialize (try JSON first, fallback to pickle)
            try:
                data = json.dumps(value)
                payload: bytes = data.encode("utf-8")
            except (TypeError, ValueError):
                payload = pickle.dumps(value)

            self.client.setex(redis_key, timedelta(seconds=ttl), payload)

            self.stats["sets"] += 1
            return True

        except Exception as e:
            logger.error(f"Redis SET error for {key}: {e}")
            self.stats["errors"] += 1
            return False

    def delete(self, key: str) -> bool:
        """Delete key from cache.

        Args:
            key: Cache key

        Returns:
            True if deleted, False otherwise

        """
        if not self.enabled or not self.client:
            # Local fallback
            if key in self._local_fallback:
                del self._local_fallback[key]
                self.stats["deletes"] += 1
                return True
            return False

        try:
            redis_key = self._make_key(key)
            deleted_count = cast(int, self.client.delete(redis_key))
            self.stats["deletes"] += deleted_count
            return deleted_count > 0

        except Exception as e:
            logger.error(f"Redis DELETE error for {key}: {e}")
            self.stats["errors"] += 1
            return False

    def clear(self) -> bool:
        """Clear all keys with this prefix.

        Returns:
            True if successful

        """
        if not self.enabled or not self.client:
            # Local fallback
            self._local_fallback.clear()
            return True

        try:
            pattern = f"{self.prefix}:*"
            cursor = 0
            deleted = 0

            while True:
                cursor, keys = cast(
                    tuple[int, list[bytes]],
                    self.client.scan(cursor, match=pattern, count=100),
                )
                if keys:
                    deleted += cast(int, self.client.delete(*keys))
                if cursor == 0:
                    break

            logger.info(f"Cleared {deleted} keys from {self.prefix} cache")
            return True

        except Exception as e:
            logger.error(f"Redis CLEAR error: {e}")
            self.stats["errors"] += 1
            return False

    def exists(self, key: str) -> bool:
        """Check if key exists.

        Args:
            key: Cache key

        Returns:
            True if exists, False otherwise

        """
        if not self.enabled or not self.client:
            return key in self._local_fallback

        try:
            redis_key = self._make_key(key)
            return cast(int, self.client.exists(redis_key)) > 0
        except Exception as e:
            logger.error(f"Redis EXISTS error for {key}: {e}")
            return False

    def get_stats(self) -> dict[str, Any]:
        """Get cache statistics.

        Returns:
            Dictionary of cache stats

        """
        total_requests = self.stats["hits"] + self.stats["misses"]
        hit_rate = self.stats["hits"] / total_requests if total_requests > 0 else 0.0

        stats = {
            "enabled": self.enabled,
            "backend": "redis" if self.enabled and self.client else "local",
            "hits": self.stats["hits"],
            "misses": self.stats["misses"],
            "sets": self.stats["sets"],
            "deletes": self.stats["deletes"],
            "errors": self.stats["errors"],
            "total_requests": total_requests,
            "hit_rate": hit_rate,
            "hit_rate_percent": hit_rate * 100,
        }

        # Add Redis-specific stats if available
        if self.enabled and self.client:
            try:
                info = cast(Mapping[str, Any], self.client.info("stats"))
                stats["redis_total_commands"] = cast(
                    int, info.get("total_commands_processed", 0)
                )
                stats["redis_keyspace_hits"] = cast(int, info.get("keyspace_hits", 0))
                stats["redis_keyspace_misses"] = cast(
                    int, info.get("keyspace_misses", 0)
                )

                # Memory info
                memory_info = cast(Mapping[str, Any], self.client.info("memory"))
                used_memory = cast(int, memory_info.get("used_memory", 0))
                max_memory = cast(int, memory_info.get("maxmemory", 0))
                stats["redis_used_memory_mb"] = used_memory / (1024 * 1024)
                stats["redis_max_memory_mb"] = max_memory / (1024 * 1024)
            except Exception as e:
                logger.debug(f"Could not get Redis stats: {e}")

        return stats

    def get_size(self) -> int:
        """Get number of keys in cache.

        Returns:
            Number of keys with this prefix

        """
        if not self.enabled or not self.client:
            return len(self._local_fallback)

        try:
            pattern = f"{self.prefix}:*"
            return sum(1 for _ in self.client.scan_iter(match=pattern, count=100))
        except Exception as e:
            logger.error(f"Redis SIZE error: {e}")
            return 0

    def close(self) -> None:
        """Close Redis connection."""
        if self.client:
            try:
                self.client.close()
                logger.info(f"Redis connection closed for {self.prefix}")
            except Exception as e:
                logger.error(f"Error closing Redis connection: {e}")
