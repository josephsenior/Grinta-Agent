"""Pydantic models and enums describing Forge microagent metadata and responses."""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import TYPE_CHECKING

from pydantic import BaseModel, Field

from forge.core.config.mcp_config import MCPConfig


class MicroagentType(str, Enum):
    """Type of microagent."""

    KNOWLEDGE = "knowledge"
    REPO_KNOWLEDGE = "repo"
    TASK = "task"


class InputMetadata(BaseModel):
    """Metadata for task microagent inputs."""

    name: str
    description: str


class MicroagentMetadata(BaseModel):
    """Metadata for all microagents."""

    name: str = "default"
    type: MicroagentType = Field(default=MicroagentType.REPO_KNOWLEDGE)
    version: str = Field(default="1.0.0")
    agent: str = Field(default="CodeActAgent")
    triggers: list[str] = []
    inputs: list[InputMetadata] = []
    mcp_tools: MCPConfig | None = None


class MicroagentResponse(BaseModel):
    """Response model for microagents endpoint.

    Note: This model only includes basic metadata that can be determined
    without parsing microagent content. Use the separate content API
    to get detailed microagent information.
    """

    name: str
    path: str
    created_at: datetime


class MicroagentContentResponse(BaseModel):
    """Response model for individual microagent content endpoint."""

    content: str
    path: str
    triggers: list[str] = []
    git_provider: str | None = None


# Resolve any forward references after imports are available
MicroagentMetadata.model_rebuild()
MicroagentResponse.model_rebuild()
MicroagentContentResponse.model_rebuild()
