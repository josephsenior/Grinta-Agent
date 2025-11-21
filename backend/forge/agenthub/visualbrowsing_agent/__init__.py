"""Agents that combine browsing and visual understanding capabilities."""

from forge.agenthub.visualbrowsing_agent.visualbrowsing_agent import (
    VisualBrowsingAgent,
)
from forge.controller.agent import Agent

Agent.register("VisualBrowsingAgent", VisualBrowsingAgent)
