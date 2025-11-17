"""Tool for requesting conversation condensation within the CodeAct agent."""

from __future__ import annotations

from forge.llm.tool_types import make_function_chunk, make_tool_param

_CONDENSATION_REQUEST_DESCRIPTION = "Request a condensation of the conversation history when the context becomes too long or when you need to focus on the most relevant information."
CondensationRequestTool = make_tool_param(
    type="function",
    function=make_function_chunk(
        name="request_condensation",
        description=_CONDENSATION_REQUEST_DESCRIPTION,
        parameters={"type": "object", "properties": {}, "required": []},
    ),
)
