"""Forge MetaSOP adapters package."""

import sys

from .forge import LLMRegistry, load_schema, run_step_with_Forge

__all__ = ["LLMRegistry", "load_schema", "run_step_with_Forge"]

# Ensure legacy import paths still resolve (OpenHands, capitalized Forge)
sys.modules.setdefault(__name__ + ".Forge", sys.modules[__name__ + ".forge"])
sys.modules.setdefault(__name__ + ".openhands", sys.modules[__name__ + ".forge"])

