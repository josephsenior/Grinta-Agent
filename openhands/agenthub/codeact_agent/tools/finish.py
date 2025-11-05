from litellm import ChatCompletionToolParam, ChatCompletionToolParamFunctionChunk

from openhands.llm.tool_names import FINISH_TOOL_NAME

_FINISH_DESCRIPTION = "Signals the completion of the current task or conversation.\n\nUse this tool when:\n- You have successfully completed the user's requested task\n- You cannot proceed further due to technical limitations or missing information\n\nThe message should include:\n- A clear summary of actions taken and their results\n- Any next steps for the user\n- Explanation if you're unable to complete the task\n- Any follow-up questions if more information is needed\n"
FinishTool = ChatCompletionToolParam(
    type="function",
    function=ChatCompletionToolParamFunctionChunk(
        name=FINISH_TOOL_NAME,
        description=_FINISH_DESCRIPTION,
        parameters={
            "type": "object",
            "required": ["message"],
            "properties": {"message": {"type": "string", "description": "Final message to send to the user"}},
        },
    ),
)
