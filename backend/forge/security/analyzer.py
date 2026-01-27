from typing import Any
from forge.events.action import Action, ActionSecurityRisk

class SecurityAnalyzer:
    async def security_risk(self, action: Action) -> ActionSecurityRisk:
        return ActionSecurityRisk.LOW
