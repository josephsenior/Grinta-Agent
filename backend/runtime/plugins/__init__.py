"""Runtime plugin registration and convenience exports."""

from typing import Callable

from backend.runtime.plugins.agent_skills import (
    AgentSkillsPlugin,
    AgentSkillsRequirement,
)
from backend.runtime.plugins.requirement import Plugin, PluginRequirement

__all__ = [
    "AgentSkillsPlugin",
    "AgentSkillsRequirement",
    "Plugin",
    "PluginRequirement",
]
ALL_PLUGINS: dict[str, Callable[[], Plugin]] = {
    "agent_skills": AgentSkillsPlugin,
}
