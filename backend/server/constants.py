"""Server Constants and Configuration.

This module contains global constants used throughout the server.
"""

from backend.core.constants import (
    API_VERSION_V1,
    CURRENT_API_VERSION,
    ENFORCE_API_VERSIONING,
    ROOM_KEY_TEMPLATE,
)


# API versioning enforcement — strict by default.  Override with
# FORGE_PERMISSIVE_API=1 env var for legacy unversioned routes.
ENFORCE_API_VERSIONING = ENFORCE_API_VERSIONING


# API Version prefix for new endpoints
def get_api_prefix(version: str = CURRENT_API_VERSION) -> str:
    """Get the API prefix for a given version.

    Args:
        version: API version (default: current version)

    Returns:
        API prefix string (e.g., "/api/v1")

    """
    return f"/api/{version}"


# Socket.IO room key format for conversations
ROOM_KEY = ROOM_KEY_TEMPLATE
