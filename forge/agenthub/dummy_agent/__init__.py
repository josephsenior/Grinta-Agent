"""Deterministic test agent for end-to-end validation."""

from forge.agenthub.dummy_agent.agent import DummyAgent
from forge.controller.agent import Agent

Agent.register("DummyAgent", DummyAgent)
