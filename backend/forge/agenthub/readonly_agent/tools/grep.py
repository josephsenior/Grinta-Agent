"""Read-only grep tool definition for regex-based content search."""

from forge.llm.tool_types import make_function_chunk, make_tool_param

_GREP_DESCRIPTION = 'Fast content search tool.\n* Searches file contents using regular expressions\n* Supports full regex syntax (eg. "log.*Error", "function\\s+\\w+", etc.)\n* Filter files by pattern with the include parameter (eg. "*.js", "*.{ts,tsx}")\n* Returns matching file paths sorted by modification time.\n* Only the first 100 results are returned. Consider narrowing your search with stricter regex patterns or provide path parameter if you need more results.\n* Use this tool when you need to find files containing specific patterns\n* When you are doing an open ended search that may require multiple rounds of globbing and grepping, use the Agent tool instead\n'
GrepTool = make_tool_param(
    type="function",
    function=make_function_chunk(
        name="grep",
        description=_GREP_DESCRIPTION,
        parameters={
            "type": "object",
            "properties": {
                "pattern": {
                    "type": "string",
                    "description": "The regex pattern to search for in file contents",
                },
                "path": {
                    "type": "string",
                    "description": "The directory (absolute path) to search in. Defaults to the current working directory.",
                },
                "include": {
                    "type": "string",
                    "description": 'Optional file pattern to filter which files to search (e.g., "*.js", "*.{ts,tsx}")',
                },
            },
            "required": ["pattern"],
        },
    ),
)
