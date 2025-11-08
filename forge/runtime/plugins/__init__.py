"""Runtime plugin registration and convenience exports."""

from forge.runtime.plugins.agent_skills import (
    AgentSkillsPlugin,
    AgentSkillsRequirement,
)
from forge.runtime.plugins.jupyter import JupyterPlugin, JupyterRequirement
from forge.runtime.plugins.requirement import Plugin, PluginRequirement
from forge.runtime.plugins.vscode import VSCodePlugin, VSCodeRequirement

__all__ = [
    "AgentSkillsPlugin",
    "AgentSkillsRequirement",
    "JupyterPlugin",
    "JupyterRequirement",
    "Plugin",
    "PluginRequirement",
    "VSCodePlugin",
    "VSCodeRequirement",
]
ALL_PLUGINS = {"jupyter": JupyterPlugin, "agent_skills": AgentSkillsPlugin, "vscode": VSCodePlugin}
