"""Compatibility helpers for constructing LiteLLM tool parameter objects.

Some unit tests monkeypatch or stub the `litellm` module, replacing
`ChatCompletionToolParam` / `ChatCompletionToolParamFunctionChunk` with simplistic
stand‑ins that may not accept the keyword arguments used by production code.

To keep the application code resilient (and avoid import‑time failures when these
stubs are in place), we build the tool parameter objects through small wrappers
that gracefully fall back to lightweight attribute containers when the real
classes are unavailable or reject the expected arguments.

The fallback objects preserve attribute access (`obj.type`, `obj.function.name`,
etc.) so downstream code remains compatible.
"""

from __future__ import annotations

from typing import Any


class _FunctionChunkFallback:
    def __init__(self, name: str, description: str, parameters: dict[str, Any]):
        self.name = name
        self.description = description
        self.parameters = parameters


class _ToolParamFallback:
    def __init__(self, type_: str, function: Any):  # noqa: D401 – simple container
        self.type = type_
        self.function = function


def build_tool_param(
    *maybe_classes: Any,
    name: str,
    description: str,
    parameters: dict[str, Any],
) -> Any:
    """Return a tool parameter object resilient to stubbed litellm variants.

    Supports two calling conventions for backward compatibility:
    1. New (preferred): build_tool_param(name=..., description=..., parameters=...)
    2. Legacy: build_tool_param(ChatCompletionToolParam, ChatCompletionToolParamFunctionChunk, name=..., ...)

    Attempts to instantiate the real LiteLLM classes; if that fails (TypeError,
    ValueError, AttributeError, or any unexpected Exception), it falls back to
    simple attribute containers that mimic the interface used elsewhere.
    """
    ChatCompletionToolParam = None
    ChatCompletionToolParamFunctionChunk = None

    if len(maybe_classes) >= 2:
        ChatCompletionToolParam, ChatCompletionToolParamFunctionChunk = maybe_classes[:2]
    else:  # Import lazily
        try:  # pragma: no cover - import side effects not relevant to tests
            from litellm import (
                ChatCompletionToolParam as _ChatCompletionToolParam,
                ChatCompletionToolParamFunctionChunk as _ChatCompletionToolParamFunctionChunk,
            )

            ChatCompletionToolParam = _ChatCompletionToolParam
            ChatCompletionToolParamFunctionChunk = _ChatCompletionToolParamFunctionChunk
        except Exception:  # pragma: no cover - litellm may be stubbed/missing
            ChatCompletionToolParam = None
            ChatCompletionToolParamFunctionChunk = None

    # Build function chunk
    try:
        if ChatCompletionToolParamFunctionChunk is not None:
            func_chunk = ChatCompletionToolParamFunctionChunk(
                name=name, description=description, parameters=parameters
            )
        else:
            raise TypeError("No real function chunk class available")
    except Exception:  # pragma: no cover - defensive fallback
        func_chunk = _FunctionChunkFallback(
            name=name, description=description, parameters=parameters
        )

    # Build tool param wrapper
    try:
        if ChatCompletionToolParam is not None:
            return ChatCompletionToolParam(type="function", function=func_chunk)
        raise TypeError("No real tool param class available")
    except Exception:  # pragma: no cover - defensive fallback
        return _ToolParamFallback("function", func_chunk)
