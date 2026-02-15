"""Read-only agent variants used for inspection-focused workflows."""

from backend.controller.agent import Agent
from backend.engines.auditor.auditor import Auditor

Agent.register("Auditor", Auditor)
