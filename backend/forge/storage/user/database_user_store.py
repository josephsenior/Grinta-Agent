"""Database-based user storage implementation using PostgreSQL.

Stores user accounts in a PostgreSQL database for production use.
"""

from __future__ import annotations

import os
from typing import Optional
from datetime import datetime

import asyncpg
from asyncpg import Pool, Connection

from forge.core.logger import forge_logger as logger
from forge.storage.user.user_store import UserStore
from forge.storage.data_models.user import User
from forge.server.middleware.auth import UserRole


# Global connection pool
_db_pool: Optional[Pool] = None


async def get_db_pool() -> Pool:
    """Get or create database connection pool."""
    global _db_pool
    if _db_pool is None:
        # Get connection parameters from environment
        host = os.getenv("DB_HOST", "localhost")
        port = int(os.getenv("DB_PORT", "5432"))
        database = os.getenv("DB_NAME", "forge")
        user = os.getenv("DB_USER", "forge")
        password = os.getenv("DB_PASSWORD", "forge")
        
        # Build connection string
        dsn = f"postgresql://{user}:{password}@{host}:{port}/{database}"
        
        # Create connection pool
        _db_pool = await asyncpg.create_pool(
            dsn,
            min_size=2,
            max_size=10,
            command_timeout=60,
        )
        logger.info(f"Created database connection pool for {database}@{host}:{port}")
    
    return _db_pool


async def close_db_pool() -> None:
    """Close database connection pool."""
    global _db_pool
    if _db_pool:
        await _db_pool.close()
        _db_pool = None
        logger.info("Closed database connection pool")


class DatabaseUserStore(UserStore):
    """PostgreSQL-based implementation of UserStore."""

    def __init__(self, pool: Optional[Pool] = None):
        """Initialize database user store.

        Args:
            pool: Optional asyncpg connection pool (will create one if not provided)
        """
        self._pool = pool

    async def _get_pool(self) -> Pool:
        """Get database connection pool."""
        if self._pool:
            return self._pool
        return await get_db_pool()

    async def create_user(self, user: User) -> User:
        """Create a new user."""
        # Check if email already exists
        existing = await self.get_user_by_email(user.email)
        if existing:
            raise ValueError(f"User with email {user.email} already exists")

        # Check if username already exists
        existing = await self.get_user_by_username(user.username)
        if existing:
            raise ValueError(f"User with username {user.username} already exists")

        pool = await self._get_pool()
        async with pool.acquire() as conn:
            # Use explicit transaction to ensure commit
            async with conn.transaction():
                await conn.execute(
                    """
                    INSERT INTO users (
                        id, email, username, password_hash, role, email_verified,
                        is_active, created_at, updated_at, last_login,
                        failed_login_attempts, locked_until
                    ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12)
                    """,
                    user.id,
                    user.email.lower(),
                    user.username.lower(),
                    user.password_hash,
                    user.role.value,
                    user.email_verified,
                    user.is_active,
                    user.created_at,
                    user.updated_at,
                    user.last_login,
                    user.failed_login_attempts,
                    user.locked_until,
                )

        logger.info(f"Created user in database: {user.email} ({user.id})")
        return user

    async def get_user_by_id(self, user_id: str) -> Optional[User]:
        """Get user by ID."""
        pool = await self._get_pool()
        async with pool.acquire() as conn:
            row = await conn.fetchrow(
                "SELECT * FROM users WHERE id = $1",
                user_id,
            )
            if not row:
                return None
            return self._row_to_user(row)

    async def get_user_by_email(self, email: str) -> Optional[User]:
        """Get user by email."""
        pool = await self._get_pool()
        async with pool.acquire() as conn:
            row = await conn.fetchrow(
                "SELECT * FROM users WHERE LOWER(email) = LOWER($1)",
                email,
            )
            if not row:
                return None
            return self._row_to_user(row)

    async def get_user_by_username(self, username: str) -> Optional[User]:
        """Get user by username."""
        pool = await self._get_pool()
        async with pool.acquire() as conn:
            row = await conn.fetchrow(
                "SELECT * FROM users WHERE LOWER(username) = LOWER($1)",
                username,
            )
            if not row:
                return None
            return self._row_to_user(row)

    async def update_user(self, user: User) -> User:
        """Update user."""
        pool = await self._get_pool()
        async with pool.acquire() as conn:
            # Use explicit transaction to ensure commit
            async with conn.transaction():
                result = await conn.execute(
                    """
                    UPDATE users SET
                        email = $2,
                        username = $3,
                        password_hash = $4,
                        role = $5,
                        email_verified = $6,
                        is_active = $7,
                        updated_at = $8,
                        last_login = $9,
                        failed_login_attempts = $10,
                        locked_until = $11
                    WHERE id = $1
                    """,
                    user.id,
                    user.email.lower(),
                    user.username.lower(),
                    user.password_hash,
                    user.role.value,
                    user.email_verified,
                    user.is_active,
                    datetime.utcnow(),
                    user.last_login,
                    user.failed_login_attempts,
                    user.locked_until,
                )
                
                if result == "UPDATE 0":
                    raise ValueError(f"User {user.id} not found")

        logger.info(f"Updated user in database: {user.email} ({user.id})")
        return user

    async def delete_user(self, user_id: str) -> bool:
        """Delete user."""
        pool = await self._get_pool()
        async with pool.acquire() as conn:
            # Use explicit transaction to ensure commit
            async with conn.transaction():
                result = await conn.execute(
                    "DELETE FROM users WHERE id = $1",
                    user_id,
                )
                deleted = result == "DELETE 1"
                if deleted:
                    logger.info(f"Deleted user from database: {user_id}")
                return deleted

    async def list_users(self, skip: int = 0, limit: int = 100) -> list[User]:
        """List users with pagination."""
        pool = await self._get_pool()
        async with pool.acquire() as conn:
            rows = await conn.fetch(
                "SELECT * FROM users ORDER BY created_at DESC LIMIT $1 OFFSET $2",
                limit,
                skip,
            )
            return [self._row_to_user(row) for row in rows]

    def _row_to_user(self, row: asyncpg.Record) -> User:
        """Convert database row to User object."""
        return User(
            id=str(row["id"]),
            email=row["email"],
            username=row["username"],
            password_hash=row["password_hash"],
            role=UserRole(row["role"]),
            email_verified=row["email_verified"],
            is_active=row["is_active"],
            created_at=row["created_at"],
            updated_at=row["updated_at"],
            last_login=row["last_login"],
            failed_login_attempts=row["failed_login_attempts"],
            locked_until=row["locked_until"],
        )

