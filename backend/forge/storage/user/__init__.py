"""User storage module with support for file and database backends."""

from __future__ import annotations

import os
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from forge.storage.user.user_store import UserStore

# Global user store instance
_user_store_instance: "UserStore | None" = None


def get_user_store() -> "UserStore":
    """Get or create global user store instance.
    
    Storage backend is determined by USER_STORAGE_TYPE environment variable:
    - "database" or "db": Use PostgreSQL database storage
    - "file" or unset: Use file-based storage (default)
    
    Returns:
        UserStore instance (FileUserStore or DatabaseUserStore)
    """
    global _user_store_instance
    if _user_store_instance is None:
        storage_type = os.getenv("USER_STORAGE_TYPE", "file").lower()
        
        if storage_type in ("database", "db"):
            from forge.storage.user.database_user_store import DatabaseUserStore
            
            _user_store_instance = DatabaseUserStore()
        else:
            from forge.storage.user.file_user_store import FileUserStore
            
            storage_path = os.getenv("USER_STORAGE_PATH")
            _user_store_instance = FileUserStore(storage_path=storage_path)
    
    return _user_store_instance

