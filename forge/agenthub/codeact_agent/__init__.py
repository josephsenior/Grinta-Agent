"""Agents that edit code through tool-augmented execution."""

from forge.agenthub.codeact_agent.codeact_agent import CodeActAgent
from forge.controller.agent import Agent

Agent.register("CodeActAgent", CodeActAgent)
