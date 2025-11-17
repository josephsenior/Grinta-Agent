"""User storage abstraction for authentication.

Provides interface for storing and retrieving user accounts.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, Optional

if TYPE_CHECKING:
    from forge.storage.data_models.user import User


class UserStore(ABC):
    """Abstract base class for user storage backends."""

    @abstractmethod
    async def create_user(self, user: "User") -> "User":
        """Create a new user.

        Args:
            user: User object to create

        Returns:
            Created user with generated ID

        Raises:
            ValueError: If user with email/username already exists
        """
        pass

    @abstractmethod
    async def get_user_by_id(self, user_id: str) -> Optional["User"]:
        """Get user by ID.

        Args:
            user_id: User ID

        Returns:
            User object or None if not found
        """
        pass

    @abstractmethod
    async def get_user_by_email(self, email: str) -> Optional["User"]:
        """Get user by email.

        Args:
            email: User email

        Returns:
            User object or None if not found
        """
        pass

    @abstractmethod
    async def get_user_by_username(self, username: str) -> Optional["User"]:
        """Get user by username.

        Args:
            username: Username

        Returns:
            User object or None if not found
        """
        pass

    @abstractmethod
    async def update_user(self, user: "User") -> "User":
        """Update user.

        Args:
            user: User object with updated fields

        Returns:
            Updated user

        Raises:
            ValueError: If user not found
        """
        pass

    @abstractmethod
    async def delete_user(self, user_id: str) -> bool:
        """Delete user.

        Args:
            user_id: User ID

        Returns:
            True if deleted, False if not found
        """
        pass

    @abstractmethod
    async def list_users(
        self, skip: int = 0, limit: int = 100
    ) -> list["User"]:
        """List users with pagination.

        Args:
            skip: Number of users to skip
            limit: Maximum number of users to return

        Returns:
            List of users
        """
        pass

