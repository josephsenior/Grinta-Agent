"""Browser-enabled agent used for web navigation scenarios."""

from backend.engines.navigator.navigator_ultimate import UltimateNavigator
from backend.controller.agent import Agent

# Register ultimate implementation under the canonical names.
Agent.register("Navigator", UltimateNavigator)
Agent.register("UltimateNavigator", UltimateNavigator)
