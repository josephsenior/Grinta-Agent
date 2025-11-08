"""Ultimate Editor tool providing structure-aware editing for the CodeAct agent."""

from litellm import ChatCompletionToolParam, ChatCompletionToolParamFunctionChunk

from forge.agenthub.codeact_agent.tools.security_utils import (
    RISK_LEVELS,
    SECURITY_RISK_DESC,
)

_DETAILED_ULTIMATE_EDITOR_DESCRIPTION = """Structure-aware editor powered by Tree-sitter (40+ languages)

This is a next-generation editor that understands code structure, not just text.

KEY ADVANTAGES over string matching:
- Edit by symbol name (function/class), not line numbers
- Never breaks on whitespace/indentation issues  
- Works for Python, JS, TS, Go, Rust, Java, C++, and 35+ more languages
- Automatic syntax validation before saving
- Intelligent error messages with suggestions

COMMANDS:

1. `edit_function` - Edit a function by name (any language)
   Required: file_path, function_name, new_body
   Example: Edit function "process_data" in Python/JS/Go/Rust/etc.
   
2. `rename_symbol` - Rename a symbol throughout a file
   Required: file_path, old_name, new_name
   Example: Rename variable "oldName" to "newName" everywhere
   
3. `find_symbol` - Find a symbol's location
   Required: file_path, symbol_name
   Optional: symbol_type ("function", "class", "method")
   Supports dot notation: "MyClass.method_name"
   
4. `replace_range` - Replace lines with new code
   Required: file_path, start_line, end_line, new_code
   Auto-indents new code to match context
   
5. `normalize_indent` - Fix indentation in a file
   Required: file_path
   Optional: style ("spaces" or "tabs"), size (2, 4, 8)
   Automatically detects and normalizes to project standards

FEATURES:
- Language-agnostic: Works with ALL languages via Tree-sitter
- Auto-indentation: New code automatically matches file style
- Syntax validation: Validates before saving (with rollback on error)
- Smart errors: Fuzzy matching suggests corrections for typos
- Whitespace intelligence: Never fails on tabs vs. spaces

BEST PRACTICES:
1. Use `edit_function` instead of line-based replacements when possible
2. Use `find_symbol` first to verify symbol exists
3. Trust the auto-indentation - it matches your file's style
4. For typos, check error messages - they suggest corrections
"""

_SHORT_ULTIMATE_EDITOR_DESCRIPTION = """Structure-aware editor for 40+ languages (Python, JS, TS, Go, Rust, Java, C++, etc.)

Commands: edit_function, rename_symbol, find_symbol, replace_range, normalize_indent
- Edits by symbol name (function/class), not line numbers
- Auto-indents code to match file style
- Validates syntax before saving
- Suggests fixes for typos/errors
"""


def create_ultimate_editor_tool(use_short_description: bool = False) -> ChatCompletionToolParam:
    """Create the Ultimate Editor tool for the CodeAct agent.
    
    Args:
        use_short_description: Whether to use short or detailed description
        
    Returns:
        ChatCompletionToolParam with the Ultimate Editor configuration

    """
    description = (
        _SHORT_ULTIMATE_EDITOR_DESCRIPTION 
        if use_short_description 
        else _DETAILED_ULTIMATE_EDITOR_DESCRIPTION
    )
    
    return ChatCompletionToolParam(
        type="function",
        function=ChatCompletionToolParamFunctionChunk(
            name="ultimate_editor",
            description=description,
            parameters={
                "type": "object",
                "properties": {
                    "command": {
                        "description": "The command to execute",
                        "enum": [
                            "edit_function",
                            "rename_symbol",
                            "find_symbol",
                            "replace_range",
                            "normalize_indent"
                        ],
                        "type": "string",
                    },
                    "file_path": {
                        "description": "Absolute path to the file (e.g., '/workspace/file.py')",
                        "type": "string",
                    },
                    # edit_function parameters
                    "function_name": {
                        "description": "Name of the function to edit (for edit_function command)",
                        "type": "string",
                    },
                    "new_body": {
                        "description": "New function body (for edit_function command). Will be auto-indented.",
                        "type": "string",
                    },
                    # rename_symbol parameters
                    "old_name": {
                        "description": "Current symbol name (for rename_symbol command)",
                        "type": "string",
                    },
                    "new_name": {
                        "description": "New symbol name (for rename_symbol command)",
                        "type": "string",
                    },
                    # find_symbol parameters
                    "symbol_name": {
                        "description": "Symbol name to find (for find_symbol command). Supports dot notation like 'Class.method'",
                        "type": "string",
                    },
                    "symbol_type": {
                        "description": "Optional symbol type filter (for find_symbol command)",
                        "enum": ["function", "class", "method"],
                        "type": "string",
                    },
                    # replace_range parameters
                    "start_line": {
                        "description": "Start line number (1-indexed, for replace_range command)",
                        "type": "integer",
                    },
                    "end_line": {
                        "description": "End line number (1-indexed, inclusive, for replace_range command)",
                        "type": "integer",
                    },
                    "new_code": {
                        "description": "New code to insert (for replace_range command). Will be auto-indented.",
                        "type": "string",
                    },
                    # normalize_indent parameters
                    "style": {
                        "description": "Target indentation style (for normalize_indent command)",
                        "enum": ["spaces", "tabs"],
                        "type": "string",
                    },
                    "size": {
                        "description": "Indent size for spaces (2, 4, or 8, for normalize_indent command)",
                        "enum": [2, 4, 8],
                        "type": "integer",
                    },
                    # Security
                    "security_risk": {
                        "type": "string",
                        "description": SECURITY_RISK_DESC,
                        "enum": RISK_LEVELS
                    },
                },
                "required": ["command", "file_path", "security_risk"],
            },
        ),
    )

