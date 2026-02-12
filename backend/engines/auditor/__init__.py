"""Read-only agent variants used for inspection-focused workflows."""

from backend.engines.auditor.auditor_ultimate import (
    UltimateAuditor,
)
from backend.controller.agent import Agent

Agent.register("Auditor", UltimateAuditor)
Agent.register("UltimateAuditor", UltimateAuditor)
