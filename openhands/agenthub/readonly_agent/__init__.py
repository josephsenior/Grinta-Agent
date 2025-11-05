from openhands.agenthub.readonly_agent.readonly_agent import ReadOnlyAgent
from openhands.agenthub.readonly_agent.readonly_agent_ultimate import UltimateReadOnlyAgent
from openhands.controller.agent import Agent

# Register Ultimate as DEFAULT - Use enhanced version everywhere
Agent.register("ReadOnlyAgent", UltimateReadOnlyAgent)  # ← Ultimate is now the default!
Agent.register("ReadOnlyAgentBasic", ReadOnlyAgent)  # ← Basic version renamed (fallback)
Agent.register("UltimateReadOnlyAgent", UltimateReadOnlyAgent)  # ← Keep explicit name too
