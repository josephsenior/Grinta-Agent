"""Convenience exports for Forge input/output helper functions."""

from forge.io.io import read_input, read_task, read_task_from_file
from forge.io.json import dumps, loads

__all__ = ["dumps", "loads", "read_input", "read_task", "read_task_from_file"]
