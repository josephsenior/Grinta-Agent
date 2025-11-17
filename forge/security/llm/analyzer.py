"""Security analyzer that uses LLM-provided risk assessments."""

from typing import Any

from fastapi import Request

from forge.core.logger import forge_logger as logger
from forge.events.action.action import Action, ActionSecurityRisk
from forge.security.analyzer import SecurityAnalyzer


class LLMRiskAnalyzer(SecurityAnalyzer):
    """Security analyzer that respects LLM-provided risk assessments."""

    async def handle_api_request(self, request: Request) -> Any:
        """Handles the incoming API request."""
        return {"status": "ok"}

    async def security_risk(self, action: Action) -> ActionSecurityRisk:
        """Evaluates the Action for security risks and returns the risk level.

        This analyzer checks if the action has a 'security_risk' attribute set by the LLM.
        If it does, it uses that value. Otherwise, it returns UNKNOWN.
        """
        if not hasattr(action, "security_risk"):
            return ActionSecurityRisk.UNKNOWN
        security_risk = action.security_risk
        if security_risk in {
            ActionSecurityRisk.LOW,
            ActionSecurityRisk.MEDIUM,
            ActionSecurityRisk.HIGH,
        }:
            return security_risk
        if security_risk == ActionSecurityRisk.UNKNOWN:
            return ActionSecurityRisk.UNKNOWN
        logger.warning("Unrecognized security_risk value: %s", security_risk)
        return ActionSecurityRisk.UNKNOWN
