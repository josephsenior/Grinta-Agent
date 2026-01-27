"""Data models describing tool call metadata within events."""

from typing import Any

from pydantic import BaseModel, Field, field_validator
from pydantic import ConfigDict, PrivateAttr

from .model_response_lite import ModelResponseLite

def build_tool_call_metadata(
    *,
    function_name: str,
    tool_call_id: str,
    response_obj: Any,
    total_calls_in_response: int,
) -> "ToolCallMetadata":
    """Unified helper to construct ToolCallMetadata across agent implementations.

    Uses `ToolCallMetadata.from_sdk` when available (preferred path that stores a
    lightweight stable representation of the model response). Falls back to direct
    construction if a monkeypatched version without `from_sdk` is present.

    All callers (CodeAct, ReadOnly, Loc agents) should use this to ensure
    consistent metadata shape and avoid divergence in test expectations.
    """
    if hasattr(ToolCallMetadata, "from_sdk"):
        return ToolCallMetadata.from_sdk(
            function_name=function_name,
            tool_call_id=tool_call_id,
            response_obj=response_obj,
            total_calls_in_response=total_calls_in_response,
        )
    # Fallback: preserve existing legacy behavior (minimal fields, omit full response)
    return ToolCallMetadata(
        function_name=function_name,
        tool_call_id=tool_call_id,
        model_response=None,
        total_calls_in_response=total_calls_in_response,
    )


class ToolCallMetadata(BaseModel):
    """Metadata for LLM tool/function calls.

    Attributes:
        function_name: Name of the function called
        tool_call_id: Unique ID for this tool call
        model_response: Complete LLM response containing the tool call
        total_calls_in_response: Number of tool calls in the response

    """

    # Allow arbitrary external SDK types without schema generation errors
    model_config = ConfigDict(arbitrary_types_allowed=True)

    # Keep raw SDK response out of the public schema
    _raw_response: Any = PrivateAttr(default=None)

    function_name: str = Field(
        ...,
        min_length=1,
        description="Name of the function called"
    )
    tool_call_id: str = Field(
        ...,
        min_length=1,
        description="Unique ID for this tool call"
    )
    # Stable, serializable subset of the response
    model_response: dict[str, Any] | ModelResponseLite | None = Field(
        default=None,
        description="Complete LLM response containing the tool call (lightweight representation)"
    )
    total_calls_in_response: int = Field(
        ...,
        ge=1,
        description="Number of tool calls in the response"
    )

    @field_validator("function_name", "tool_call_id")
    @classmethod
    def validate_required_strings(cls, v: str) -> str:
        """Validate required string fields are non-empty."""
        from forge.core.security.type_safety import validate_non_empty_string
        return validate_non_empty_string(v, name="field")

    @classmethod
    def from_sdk(
        cls,
        *,
        function_name: str,
        tool_call_id: str,
        response_obj: Any,
        total_calls_in_response: int,
    ) -> "ToolCallMetadata":
        lite = ModelResponseLite.from_sdk(response_obj)
        md = cls(
            function_name=function_name,
            tool_call_id=tool_call_id,
            model_response=lite,
            total_calls_in_response=total_calls_in_response,
        )
        md._raw_response = response_obj
        return md
