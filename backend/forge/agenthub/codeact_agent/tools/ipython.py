"""IPython execution tool definitions used by the CodeAct agent.

Provides both a modern name (execute_ipython_cell) and a backward-compatible
name (run_ipython) since other runtime components and security policies refer
to `run_ipython`.
"""

from litellm import ChatCompletionToolParam, ChatCompletionToolParamFunctionChunk

from forge.agenthub.codeact_agent.tools.security_utils import (
    RISK_LEVELS,
    SECURITY_RISK_DESC,
)

from ._compat import build_tool_param

_IPYTHON_DESCRIPTION = (
    "Execute Python code in the project's Jupyter environment. Use this to run data analysis, "
    "quick computations, or inspect variables. The execution is sandboxed, and results are captured."
)

_IPYTHON_PARAMETERS = {
    "type": "object",
    "properties": {
        "code": {
            "type": "string",
            "description": "Python code to execute in the Jupyter environment.",
        },
        "security_risk": {
            "type": "string",
            "description": SECURITY_RISK_DESC,
            "enum": RISK_LEVELS,
            "default": "LOW",
        },
    },
    "required": ["code", "security_risk"],
}

# Modern name expected by unit tests
IPythonTool = build_tool_param(
    ChatCompletionToolParam,
    ChatCompletionToolParamFunctionChunk,
    name="execute_ipython_cell",
    description=_IPYTHON_DESCRIPTION,
    parameters=_IPYTHON_PARAMETERS,
)

# Backward compatibility for existing runtime/security references
RunIPythonTool = build_tool_param(
    ChatCompletionToolParam,
    ChatCompletionToolParamFunctionChunk,
    name="run_ipython",
    description=_IPYTHON_DESCRIPTION,
    parameters=_IPYTHON_PARAMETERS,
)
