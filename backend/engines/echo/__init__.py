"""Deterministic test agent for end-to-end validation."""

from backend.controller.agent import Agent
from backend.engines.echo.agent import Echo

Agent.register("Echo", Echo)
