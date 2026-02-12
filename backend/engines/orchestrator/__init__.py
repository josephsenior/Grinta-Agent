"""Agents that edit code through tool-augmented execution."""

from backend.engines.orchestrator.orchestrator import Orchestrator
from backend.controller.agent import Agent

Agent.register("Orchestrator", Orchestrator)
