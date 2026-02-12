"""Database connection pooling utilities.

Provides optimized database connection management with:
- Connection pooling
- Connection health checks
- Automatic reconnection
- Query optimization helpers
"""

from __future__ import annotations

import os
from typing import Optional, Any
from contextlib import asynccontextmanager

from backend.core.logger import forge_logger as logger


class DatabasePool:
    """Database connection pool manager."""

    def __init__(
        self,
        pool_size: int = 20,
        max_overflow: int = 10,
        pool_pre_ping: bool = True,
        pool_recycle: int = 3600,
    ):
        """Initialize database connection pool.

        Args:
            pool_size: Number of connections to maintain
            max_overflow: Maximum overflow connections
            pool_pre_ping: Test connections before using
            pool_recycle: Recycle connections after this many seconds
        """
        self.pool_size = pool_size
        self.max_overflow = max_overflow
        self.pool_pre_ping = pool_pre_ping
        self.pool_recycle = pool_recycle
        self._engine: Optional[Any] = None

    def create_engine(self, database_url: str) -> Any:
        """Create SQLAlchemy engine with connection pooling.

        Args:
            database_url: Database connection URL

        Returns:
            SQLAlchemy engine
        """
        try:
            from sqlalchemy import create_engine
            from sqlalchemy.pool import QueuePool

            self._engine = create_engine(
                database_url,
                poolclass=QueuePool,
                pool_size=self.pool_size,
                max_overflow=self.max_overflow,
                pool_pre_ping=self.pool_pre_ping,
                pool_recycle=self.pool_recycle,
                echo=False,  # Set to True for SQL query logging
            )
            logger.info(
                f"Database connection pool created: size={self.pool_size}, "
                f"max_overflow={self.max_overflow}"
            )
            return self._engine
        except ImportError:
            logger.warning("SQLAlchemy not available, connection pooling disabled")
            return None

    @asynccontextmanager
    async def get_connection(self):
        """Get a database connection from the pool.

        Yields:
            Database connection
        """
        if not self._engine:
            raise RuntimeError("Database engine not initialized")

        # For async SQLAlchemy, use async engine
        try:
            from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
            from sqlalchemy.orm import sessionmaker

            # This is a placeholder - actual implementation depends on your DB setup
            async with AsyncSession(self._engine) as session:
                yield session
        except ImportError:
            # Fallback to sync
            connection = self._engine.connect()
            try:
                yield connection
            finally:
                connection.close()

    def get_pool_status(self) -> dict[str, Any]:
        """Get connection pool status.

        Returns:
            Dictionary with pool statistics
        """
        if not self._engine:
            return {"status": "not_initialized"}

        pool = self._engine.pool
        return {
            "status": "active",
            "size": pool.size(),
            "checked_in": pool.checkedin(),
            "checked_out": pool.checkedout(),
            "overflow": pool.overflow(),
            "invalid": pool.invalid(),
        }


# Global database pool instance
_db_pool: Optional[DatabasePool] = None


def get_db_pool() -> DatabasePool:
    """Get or create global database pool instance.

    Returns:
        DatabasePool instance
    """
    global _db_pool
    if _db_pool is None:
        pool_size = int(os.getenv("DB_POOL_SIZE", "20"))
        max_overflow = int(os.getenv("DB_POOL_MAX_OVERFLOW", "10"))
        pool_pre_ping = os.getenv("DB_POOL_PRE_PING", "true").lower() == "true"
        pool_recycle = int(os.getenv("DB_POOL_RECYCLE", "3600"))

        _db_pool = DatabasePool(
            pool_size=pool_size,
            max_overflow=max_overflow,
            pool_pre_ping=pool_pre_ping,
            pool_recycle=pool_recycle,
        )
    return _db_pool

