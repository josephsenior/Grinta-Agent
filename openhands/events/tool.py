from litellm import ModelResponse
from pydantic import BaseModel


class ToolCallMetadata(BaseModel):
    function_name: str
    tool_call_id: str
    model_response: ModelResponse
    total_calls_in_response: int
