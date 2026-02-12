"""Deterministic test agent for end-to-end validation."""

from backend.engines.echo.agent import Echo
from backend.controller.agent import Agent

Agent.register("Echo", Echo)
