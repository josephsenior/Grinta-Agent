from openhands.agenthub.browsing_agent.browsing_agent import BrowsingAgent
from openhands.agenthub.browsing_agent.browsing_agent_ultimate import UltimateBrowsingAgent
from openhands.controller.agent import Agent

# Register Ultimate as DEFAULT - Use enhanced version everywhere
Agent.register("BrowsingAgent", UltimateBrowsingAgent)  # ← Ultimate is now the default!
Agent.register("BrowsingAgentBasic", BrowsingAgent)  # ← Basic version renamed (fallback)
Agent.register("UltimateBrowsingAgent", UltimateBrowsingAgent)  # ← Keep explicit name too
