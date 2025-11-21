from __future__ import annotations

import sys
from types import ModuleType

import pytest

from forge.agenthub.codeact_agent.tools import _compat


def test_build_tool_param_with_explicit_classes():
    class FakeFunctionChunk:
        def __init__(self, *, name, description, parameters):
            self.name = name
            self.description = description
            self.parameters = parameters

    class FakeToolParam:
        def __init__(self, *, type, function):
            self.type = type
            self.function = function

    tool = _compat.build_tool_param(
        FakeToolParam,
        FakeFunctionChunk,
        name="test",
        description="desc",
        parameters={"type": "object", "properties": {}},
    )

    assert isinstance(tool, FakeToolParam)
    assert tool.type == "function"
    assert isinstance(tool.function, FakeFunctionChunk)
    assert tool.function.name == "test"


def test_build_tool_param_falls_back_when_classes_fail():
    class ExplodingFunctionChunk:
        def __init__(self, *_, **__):
            raise TypeError("boom")

    class ExplodingToolParam:
        def __init__(self, *_, **__):
            raise TypeError("boom")

    tool = _compat.build_tool_param(
        ExplodingToolParam,
        ExplodingFunctionChunk,
        name="test",
        description="desc",
        parameters={},
    )

    # Fallback objects expose type/function attributes to downstream callers.
    assert hasattr(tool, "type") and tool.type == "function"
    assert hasattr(tool, "function")
    assert tool.function.name == "test"


def test_build_tool_param_import_fallback_monkeypatched(monkeypatch):
    # Simulate import failure so build_tool_param uses fallback path without explicit classes.
    fake_module = ModuleType("litellm")

    def fake_import(name, *args, **kwargs):
        if name == "litellm":
            return fake_module
        return original_import(name, *args, **kwargs)

    original_import = __import__
    monkeypatch.setattr("builtins.__import__", fake_import)

    tool = _compat.build_tool_param(
        name="test",
        description="desc",
        parameters={"type": "object", "properties": {}},
    )
    assert tool.type == "function"
    assert tool.function.description == "desc"

