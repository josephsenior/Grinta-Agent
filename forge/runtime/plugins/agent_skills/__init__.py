"""Agent skills plugin metadata and placeholder runtime integration."""

from dataclasses import dataclass

from forge.events.action import Action
from forge.events.observation import Observation
from forge.runtime.plugins.agent_skills import agentskills
from forge.runtime.plugins.requirement import Plugin, PluginRequirement


@dataclass
class AgentSkillsRequirement(PluginRequirement):
    """Plugin requirement metadata describing agent skill capabilities."""

    name: str = "agent_skills"
    documentation: str = agentskills.DOCUMENTATION


class AgentSkillsPlugin(Plugin):
    """Placeholder plugin entry for agent skill toolkits (no runtime behavior)."""

    name: str = "agent_skills"

    async def initialize(self, username: str) -> None:
        """Initialize the plugin."""

    async def run(self, action: Action) -> Observation:
        """Run the plugin for a given action."""
        msg = "AgentSkillsPlugin does not support run method"
        raise NotImplementedError(msg)
