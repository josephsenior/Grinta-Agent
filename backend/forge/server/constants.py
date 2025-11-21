"""Server Constants and Configuration.

This module contains global constants used throughout the server.
"""

# API Versioning
API_VERSION_V1 = "v1"
CURRENT_API_VERSION = API_VERSION_V1

# During beta, allow non-versioned endpoints for backward compatibility
# After public launch, set this to True to enforce versioning
ENFORCE_API_VERSIONING = False


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
ROOM_KEY = "room_{sid}"
