"""Agents for locating files and content within a repository."""

from forge.agenthub.loc_agent.loc_agent import LocAgent
from forge.agenthub.loc_agent.loc_agent_ultimate import UltimateLocAgent
from forge.controller.agent import Agent

# Register Ultimate as DEFAULT - Use enhanced version everywhere
Agent.register("LocAgent", UltimateLocAgent)  # ← Ultimate is now the default!
Agent.register("LocAgentBasic", LocAgent)  # ← Basic version renamed (fallback)
Agent.register("UltimateLocAgent", UltimateLocAgent)  # ← Keep explicit name too
