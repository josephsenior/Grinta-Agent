"""File-based user storage implementation.

Stores user accounts in JSON files on the filesystem.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Optional
from datetime import datetime

from forge.core.logger import forge_logger as logger
from forge.storage.user.user_store import UserStore
from forge.storage.data_models.user import User
from forge.server.middleware.auth import UserRole
from forge.utils.async_utils import call_sync_from_async
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    pass


class FileUserStore(UserStore):
    """File-based implementation of UserStore."""

    def __init__(self, storage_path: str | None = None):
        """Initialize file-based user store with path validation.

        Args:
            storage_path: Path to user storage directory (default: .forge/users)

        Raises:
            ValueError: If storage_path is invalid or contains security risks
        """
        if storage_path is None:
            storage_path = os.path.join(
                os.getcwd(), ".forge", "users"
            )
        
        # Validate storage path for security
        try:
            from forge.core.security.path_validation import SafePath
            
            # Validate the storage path (allow absolute paths for storage)
            safe_path = SafePath.validate(
                storage_path,
                workspace_root=os.getcwd(),
                must_be_relative=False,  # Storage paths can be absolute
            )
            self.storage_path = safe_path.path
        except Exception:
            # Fallback to basic path creation for backward compatibility
            logger.warning(
                f"Path validation failed for storage_path {storage_path}, using legacy path. "
                "This may be a security risk."
            )
            self.storage_path = Path(storage_path)
        
        self.storage_path.mkdir(parents=True, exist_ok=True)
        self._users_cache: dict[str, User] = {}
        self._load_users()

    def _load_users(self) -> None:
        """Load all users from storage into cache."""
        users_file = self.storage_path / "users.json"
        if not users_file.exists():
            return

        try:
            with open(users_file, "r") as f:
                data = json.load(f)
                for user_data in data.get("users", []):
                    user = self._dict_to_user(user_data)
                    self._users_cache[user.id] = user
            logger.info(f"Loaded {len(self._users_cache)} users from storage")
        except Exception as e:
            logger.error(f"Error loading users: {e}")

    def _save_users(self) -> None:
        """Save all users from cache to storage."""
        users_file = self.storage_path / "users.json"
        try:
            data = {
                "users": [self._user_to_dict(user) for user in self._users_cache.values()]
            }
            with open(users_file, "w") as f:
                json.dump(data, f, indent=2, default=str)
        except Exception as e:
            logger.error(f"Error saving users: {e}")

    def _user_to_dict(self, user: User) -> dict:
        """Convert User to dictionary."""
        return {
            "id": user.id,
            "email": user.email,
            "username": user.username,
            "password_hash": user.password_hash,
            "role": user.role.value,
            "email_verified": user.email_verified,
            "is_active": user.is_active,
            "created_at": user.created_at.isoformat(),
            "updated_at": user.updated_at.isoformat(),
            "last_login": user.last_login.isoformat() if user.last_login else None,
            "failed_login_attempts": user.failed_login_attempts,
            "locked_until": user.locked_until.isoformat() if user.locked_until else None,
        }

    def _dict_to_user(self, data: dict) -> User:
        """Convert dictionary to User."""
        return User(
            id=data["id"],
            email=data["email"],
            username=data["username"],
            password_hash=data["password_hash"],
            role=UserRole(data.get("role", "user")),
            email_verified=data.get("email_verified", False),
            is_active=data.get("is_active", True),
            created_at=datetime.fromisoformat(data["created_at"]) if isinstance(data.get("created_at"), str) else data.get("created_at", datetime.utcnow()),
            updated_at=datetime.fromisoformat(data["updated_at"]) if isinstance(data.get("updated_at"), str) else data.get("updated_at", datetime.utcnow()),
            last_login=datetime.fromisoformat(data["last_login"]) if data.get("last_login") else None,
            failed_login_attempts=data.get("failed_login_attempts", 0),
            locked_until=datetime.fromisoformat(data["locked_until"]) if data.get("locked_until") else None,
        )

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

        # Add to cache
        self._users_cache[user.id] = user

        # Save to disk
        await call_sync_from_async(self._save_users)

        logger.info(f"Created user: {user.email} ({user.id})")
        return user

    async def get_user_by_id(self, user_id: str) -> Optional[User]:
        """Get user by ID."""
        return self._users_cache.get(user_id)

    async def get_user_by_email(self, email: str) -> Optional[User]:
        """Get user by email."""
        for user in self._users_cache.values():
            if user.email.lower() == email.lower():
                return user
        return None

    async def get_user_by_username(self, username: str) -> Optional[User]:
        """Get user by username."""
        for user in self._users_cache.values():
            if user.username.lower() == username.lower():
                return user
        return None

    async def update_user(self, user: User) -> User:
        """Update user."""
        if user.id not in self._users_cache:
            raise ValueError(f"User {user.id} not found")

        user.updated_at = datetime.utcnow()
        self._users_cache[user.id] = user

        # Save to disk
        await call_sync_from_async(self._save_users)

        logger.info(f"Updated user: {user.email} ({user.id})")
        return user

    async def delete_user(self, user_id: str) -> bool:
        """Delete user."""
        if user_id not in self._users_cache:
            return False

        user = self._users_cache.pop(user_id)

        # Save to disk
        await call_sync_from_async(self._save_users)

        logger.info(f"Deleted user: {user.email} ({user_id})")
        return True

    async def list_users(self, skip: int = 0, limit: int = 100) -> list[User]:
        """List users with pagination."""
        users = list(self._users_cache.values())
        return users[skip : skip + limit]

