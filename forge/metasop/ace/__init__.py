"""Agentic Context Engineering (ACE) Framework.

A self-improving AI system that learns from its own performance through
evolving context playbooks that prevent context collapse and accumulate
domain-specific knowledge.

Components:
    ContextPlaybook - Structured knowledge management system
    ACEGenerator - Produces reasoning trajectories using playbook
    ACEReflector - Analyzes performance and extracts insights
    ACECurator - Synthesizes insights into context updates
    ACEFramework - Main orchestrator for the three-agent system
"""

from .context_playbook import ContextPlaybook, BulletPoint, BulletSection
from .generator import ACEGenerator
from .reflector import ACEReflector
from .curator import ACECurator
from .ace_framework import ACEFramework
from .models import (
    ACEInsight,
    ACEDeltaUpdate,
    ACEExecutionResult,
    ACEPerformanceMetrics,
    ACETrajectory,
    ACEFrameworkResult,
    ACEGenerationResult,
    ACEReflectionResult,
    ACECurationResult,
    ACEConfig,
)

__all__ = [
    "ContextPlaybook",
    "BulletPoint", 
    "BulletSection",
    "ACEGenerator",
    "ACEReflector",
    "ACECurator",
    "ACEFramework",
    "ACEInsight",
    "ACEDeltaUpdate",
    "ACEExecutionResult",
    "ACEPerformanceMetrics",
    "ACETrajectory",
    "ACEFrameworkResult",
    "ACEGenerationResult",
    "ACEReflectionResult",
    "ACECurationResult",
    "ACEConfig",
]

__version__ = "1.0.0"
