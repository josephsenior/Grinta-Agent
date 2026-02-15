"""Agents for locating files and content within a repository."""

from backend.controller.agent import Agent
from backend.engines.locator.locator import Locator

Agent.register("Locator", Locator)
