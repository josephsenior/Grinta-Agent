"""Read-only agent variants used for inspection-focused workflows."""

from forge.agenthub.readonly_agent.readonly_agent import ReadOnlyAgent
from forge.agenthub.readonly_agent.readonly_agent_ultimate import UltimateReadOnlyAgent
from forge.controller.agent import Agent

# Register Ultimate as DEFAULT - Use enhanced version everywhere
Agent.register("ReadOnlyAgent", UltimateReadOnlyAgent)  # ← Ultimate is now the default!
Agent.register("ReadOnlyAgentBasic", ReadOnlyAgent)  # ← Basic version renamed (fallback)
Agent.register("UltimateReadOnlyAgent", UltimateReadOnlyAgent)  # ← Keep explicit name too
