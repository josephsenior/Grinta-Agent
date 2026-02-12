"""Agents for locating files and content within a repository."""

from backend.engines.locator.locator_ultimate import UltimateLocator
from backend.controller.agent import Agent

Agent.register("Locator", UltimateLocator)
Agent.register("UltimateLocator", UltimateLocator)
