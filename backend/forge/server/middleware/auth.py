"""Authentication middleware and user roles.

This module provides authentication utilities and user role definitions.
"""

from enum import Enum


class UserRole(str, Enum):
    """User role enumeration for authorization."""

    USER = "user"
    ADMIN = "admin"
    MODERATOR = "moderator"


def get_current_user_id(request):
    """Get current user ID from request.

    This is a placeholder function. Implement proper authentication
    based on your auth system (JWT, session, etc.).
    """
    # TODO: Implement proper authentication
    # For now, return None to indicate no authenticated user
    return None
