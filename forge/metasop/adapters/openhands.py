"""Legacy OpenHands adapter shim.

The Forge project has rebranded the MetaSOP adapter to ``forge.py``. This module
keeps the old ``openhands`` import path functioning by re-exporting the Forge
implementation.
"""

from .forge import LLMRegistry, load_schema, run_step_with_Forge

__all__ = ["LLMRegistry", "load_schema", "run_step_with_Forge"]
