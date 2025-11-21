from __future__ import annotations

from forge.agenthub.readonly_agent.tools.semantic_search import create_semantic_search_tool
from forge.agenthub.readonly_agent.tools.ultimate_explorer import (
    create_ultimate_explorer_tool,
)


def test_create_semantic_search_tool_structure():
    tool = create_semantic_search_tool()
    assert tool["type"] == "function"
    function = tool["function"]
    assert function["name"] == "semantic_search"
    description = function["description"]
    assert "Semantic code search" in description
    params = function["parameters"]
    assert params["type"] == "object"
    assert "query" in params["properties"]
    assert params["properties"]["query"]["type"] == "string"
    assert "max_results" in params["properties"]


def test_create_ultimate_explorer_tool_structure():
    tool = create_ultimate_explorer_tool()
    assert tool["type"] == "function"
    function = tool["function"]
    assert function["name"] == "ultimate_explorer"
    assert "Structure-aware code explorer" in function["description"]
    properties = function["parameters"]["properties"]
    assert properties["command"]["enum"] == [
        "find_symbol",
        "explore_file",
        "get_symbol_context",
    ]
    assert properties["symbol_type"]["enum"] == ["function", "class", "method"]
    assert set(function["parameters"]["required"]) == {"command", "file_path"}

