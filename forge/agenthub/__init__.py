"""Collection of built-in Forge agent implementations and utilities."""

from dotenv import load_dotenv

from forge.agenthub import (
    browsing_agent,
    codeact_agent,
    dummy_agent,
    loc_agent,
    readonly_agent,
    visualbrowsing_agent,
)
from forge.controller.agent import Agent

load_dotenv()
__all__ = [
    "Agent",
    "browsing_agent",
    "codeact_agent",
    "dummy_agent",
    "loc_agent",
    "readonly_agent",
    "visualbrowsing_agent",
]
