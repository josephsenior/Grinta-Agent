"""Read-only agent variants used for inspection-focused workflows."""

from forge.agenthub.readonly_agent.readonly_agent_ultimate import (
    UltimateReadOnlyAgent,
)
from forge.controller.agent import Agent

Agent.register("ReadOnlyAgent", UltimateReadOnlyAgent)
Agent.register("UltimateReadOnlyAgent", UltimateReadOnlyAgent)
