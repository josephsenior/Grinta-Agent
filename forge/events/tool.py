"""Data models describing tool call metadata within events."""

from litellm import ModelResponse
from pydantic import BaseModel


class ToolCallMetadata(BaseModel):
    """Metadata for LLM tool/function calls.
    
    Attributes:
        function_name: Name of the function called
        tool_call_id: Unique ID for this tool call
        model_response: Complete LLM response containing the tool call
        total_calls_in_response: Number of tool calls in the response

    """
    function_name: str
    tool_call_id: str
    model_response: ModelResponse
    total_calls_in_response: int
