"""Browser-enabled agent used for web navigation scenarios."""

from backend.controller.agent import Agent
from backend.engines.navigator.navigator import Navigator

Agent.register("Navigator", Navigator)
