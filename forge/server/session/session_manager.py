"""Session Manager for handling active sessions."""

from __future__ import annotations

from typing import TYPE_CHECKING

from forge.core.logger import forge_logger as logger

if TYPE_CHECKING:
    from forge.server.session.session import Session


class SessionManager:
    """Manages active sessions in the application."""
    
    def __init__(self):
        """Initialize the active session registry."""
        self._active_sessions: dict[str, Session] = {}
        logger.info("SessionManager initialized")
    
    def get_active_sessions(self) -> dict[str, Session]:
        """Get all active sessions.
        
        Returns:
            Dictionary of active sessions keyed by session ID

        """
        return self._active_sessions.copy()
    
    def add_session(self, session: Session) -> None:
        """Add a session to the active sessions.
        
        Args:
            session: The session to add

        """
        self._active_sessions[session.sid] = session
        logger.info(f"Added session {session.sid}")
    
    def remove_session(self, session_id: str) -> None:
        """Remove a session from active sessions.
        
        Args:
            session_id: The ID of the session to remove

        """
        if session_id in self._active_sessions:
            del self._active_sessions[session_id]
            logger.info(f"Removed session {session_id}")
    
    def get_session(self, session_id: str) -> Session | None:
        """Get a specific session by ID.
        
        Args:
            session_id: The ID of the session to retrieve
            
        Returns:
            The session if found, None otherwise

        """
        return self._active_sessions.get(session_id)
    
    def get_session_count(self) -> int:
        """Get the number of active sessions.
        
        Returns:
            Number of active sessions

        """
        return len(self._active_sessions)
