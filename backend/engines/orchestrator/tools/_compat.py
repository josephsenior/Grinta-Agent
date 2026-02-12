"""Compatibility helpers for constructing tool parameter objects.

This module provides simple containers for tool parameter objects that mimic
the interface expected by the application code.
"""

from __future__ import annotations

from typing import Any


class _FunctionChunkFallback(dict):
    def __init__(self, name: str, description: str, parameters: dict[str, Any]):
        super().__init__(name=name, description=description, parameters=parameters)
        self.name = name
        self.description = description
        self.parameters = parameters


class _ToolParamFallback(dict):
    def __init__(self, type_: str, function: Any):
        super().__init__(type=type_, function=function)
        self.type = type_
        self.function = function


def build_tool_param(
    name: str,
    description: str,
    parameters: dict[str, Any],
) -> Any:
    """Return a tool parameter object.
    
    This helper ensures consistent tool parameter formatting for CodeAct agent tools.
    """
    func_chunk = _FunctionChunkFallback(
        name=name, description=description, parameters=parameters
    )
    return _ToolParamFallback("function", func_chunk)
