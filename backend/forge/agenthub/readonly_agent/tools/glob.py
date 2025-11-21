"""Read-only glob tool definition for path discovery."""

from forge.llm.tool_types import make_function_chunk, make_tool_param

_GLOB_DESCRIPTION = 'Fast file pattern matching tool.\n* Supports glob patterns like "**/*.js" or "src/**/*.ts"\n* Use this tool when you need to find files by name patterns\n* Returns matching file paths sorted by modification time\n* Only the first 100 results are returned. Consider narrowing your search with stricter glob patterns or provide path parameter if you need more results.\n* When you are doing an open ended search that may require multiple rounds of globbing and grepping, use the Agent tool instead\n'
GlobTool = make_tool_param(
    type="function",
    function=make_function_chunk(
        name="glob",
        description=_GLOB_DESCRIPTION,
        parameters={
            "type": "object",
            "properties": {
                "pattern": {
                    "type": "string",
                    "description": 'The glob pattern to match files (e.g., "**/*.js", "src/**/*.ts")',
                },
                "path": {
                    "type": "string",
                    "description": "The directory (absolute path) to search in. Defaults to the current working directory.",
                },
            },
            "required": ["pattern"],
        },
    ),
)
