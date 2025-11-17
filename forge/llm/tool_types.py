from __future__ import annotations

from typing import Any, TypedDict, NotRequired

try:  # Prefer real LiteLLM types if available
    import litellm as _litellm
except Exception:  # pragma: no cover - optional dependency
    _litellm = None  # type: ignore


class FunctionChunkArgs(TypedDict):
    name: str
    description: NotRequired[str]
    parameters: NotRequired[dict[str, Any]]
    strict: NotRequired[bool]


def make_function_chunk(**chunk_kwargs: Any) -> Any:
    """Create a ChatCompletionToolParamFunctionChunk or a dict fallback.

    The result supports both dict-style and attribute-style access when using the
    fallback, matching tests and production code expectations.
    """
    if _litellm is not None:
        try:
            cls = getattr(_litellm, "ChatCompletionToolParamFunctionChunk")
        except Exception:  # missing on some versions
            cls = None
        if cls is not None:
            return cls(**chunk_kwargs)

    class _Chunk(dict):  # attribute-friendly dict
        def __getattr__(self, key):
            return self[key]

        def __setattr__(self, key, value):
            self[key] = value

    return _Chunk({k: v for k, v in chunk_kwargs.items()})


def make_tool_param(function: Any, type: str = "function", **extras: Any) -> Any:
    """Create a ChatCompletionToolParam or a dict fallback.

    Keeps interface consistent across LiteLLM versions and during tests.
    """
    if _litellm is not None:
        try:
            cls = getattr(_litellm, "ChatCompletionToolParam")
        except Exception:
            cls = None
        if cls is not None:
            return cls(function=function, type=type, **extras)

    class _Tool(dict):  # attribute-friendly dict
        def __getattr__(self, key):
            return self[key]

        def __setattr__(self, key, value):
            self[key] = value

    payload = {"type": type, "function": function}
    payload.update(extras)
    return _Tool(payload)


__all__ = ["FunctionChunkArgs", "make_function_chunk", "make_tool_param"]
