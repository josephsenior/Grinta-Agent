"""Abstract security analyzer base class for assessing agent actions."""

from typing import Any

from fastapi import Request

from forge.events.action.action import Action, ActionSecurityRisk


class SecurityAnalyzer:
    """Security analyzer that analyzes agent actions for security risks."""

    def __init__(self) -> None:
        """Initializes a new instance of the SecurityAnalyzer class."""

    async def handle_api_request(self, request: Request) -> Any:
        """Handles the incoming API request."""
        msg = "Need to implement handle_api_request method in SecurityAnalyzer subclass"
        raise NotImplementedError(msg)

    async def security_risk(self, action: Action) -> ActionSecurityRisk:
        """Evaluates the Action for security risks and returns the risk level."""
        msg = "Need to implement security_risk method in SecurityAnalyzer subclass"
        raise NotImplementedError(msg)

    async def close(self) -> None:
        """Cleanup resources allocated by the SecurityAnalyzer."""
