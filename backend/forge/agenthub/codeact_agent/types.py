from __future__ import annotations

from typing import TYPE_CHECKING, TypedDict

class AgentSkillsRequirement(TypedDict):
    """Requirement for agent skills."""
    skills: list[str]
