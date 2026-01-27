from __future__ import annotations

import pytest

from forge.agenthub.codeact_agent.tools import _compat


def test_build_tool_param():
    tool = _compat.build_tool_param(
        name="test",
        description="desc",
        parameters={"type": "object", "properties": {}},
    )

    # Fallback objects expose type/function attributes to downstream callers.
    assert hasattr(tool, "type") and tool.type == "function"
    assert hasattr(tool, "function")
    assert tool.function.name == "test"
    assert tool.function.description == "desc"
    assert tool.function.parameters == {"type": "object", "properties": {}}
