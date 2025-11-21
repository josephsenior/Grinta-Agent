"""Agents for locating files and content within a repository."""

from forge.agenthub.loc_agent.loc_agent_ultimate import UltimateLocAgent
from forge.controller.agent import Agent

Agent.register("LocAgent", UltimateLocAgent)
Agent.register("UltimateLocAgent", UltimateLocAgent)
