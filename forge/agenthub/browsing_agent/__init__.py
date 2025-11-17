"""Browser-enabled agent used for web navigation scenarios."""

from forge.agenthub.browsing_agent.browsing_agent_ultimate import UltimateBrowsingAgent
from forge.controller.agent import Agent

# Register ultimate implementation under the canonical names.
Agent.register("BrowsingAgent", UltimateBrowsingAgent)
Agent.register("UltimateBrowsingAgent", UltimateBrowsingAgent)
