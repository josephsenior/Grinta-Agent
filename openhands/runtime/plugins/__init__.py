from openhands.runtime.plugins.agent_skills import (
    AgentSkillsPlugin,
    AgentSkillsRequirement,
)
from openhands.runtime.plugins.jupyter import JupyterPlugin, JupyterRequirement
from openhands.runtime.plugins.requirement import Plugin, PluginRequirement
from openhands.runtime.plugins.vscode import VSCodePlugin, VSCodeRequirement

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
