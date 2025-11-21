#!/usr/bin/env python3
"""Automated docstring generator for Forge codebase.

This script analyzes Python files and adds missing docstrings to functions,
methods, and classes based on their signatures and context.
"""

import ast
import os
import re
from pathlib import Path


class DocstringGenerator:
    """Generate docstrings for Python code elements."""

    def __init__(self):
        """Initialize docstring generator."""
        self.stats = {
            "functions_processed": 0,
            "docstrings_added": 0,
            "files_modified": 0,
        }

    def generate_function_docstring(
        self, node: ast.FunctionDef | ast.AsyncFunctionDef, source_lines: list[str]
    ) -> str:
        """Generate docstring for a function or method.

        Args:
            node: AST node for function/method
            source_lines: Source code lines

        Returns:
            Generated docstring text
        """
        # Extract function info
        is_async = isinstance(node, ast.AsyncFunctionDef)
        is_method = self._is_method(node)
        is_property = self._has_decorator(node, "property")
        is_private = node.name.startswith("_") and not node.name.startswith("__")

        # Generate brief description
        brief = self._generate_brief_description(
            node.name, is_async, is_method, is_property
        )

        # Build docstring parts
        parts = [f'"""{brief}']

        # Add Args section if has parameters
        if self._has_parameters(node):
            args_section = self._generate_args_section(node)
            if args_section:
                parts.append("")
                parts.extend(args_section)

        # Add Returns section if has return type
        if node.returns:
            returns_section = self._generate_returns_section(node)
            if returns_section:
                parts.append("")
                parts.append(returns_section)

        parts.append('"""')
        return "\n        ".join(parts) if is_method else "\n    ".join(parts)

    def _is_method(self, node: ast.FunctionDef | ast.AsyncFunctionDef) -> bool:
        """Check if function is a method."""
        return len(node.args.args) > 0 and node.args.args[0].arg in ("self", "cls")

    def _has_decorator(
        self, node: ast.FunctionDef | ast.AsyncFunctionDef, decorator_name: str
    ) -> bool:
        """Check if function has specific decorator."""
        for decorator in node.decorator_list:
            if isinstance(decorator, ast.Name) and decorator.id == decorator_name:
                return True
        return False

    def _has_parameters(self, node: ast.FunctionDef | ast.AsyncFunctionDef) -> bool:
        """Check if function has parameters (excluding self/cls)."""
        args = node.args.args
        if not args:
            return False
        # Exclude self/cls for methods
        if args[0].arg in ("self", "cls"):
            return len(args) > 1
        return len(args) > 0

    def _generate_brief_description(
        self, name: str, is_async: bool, is_method: bool, is_property: bool
    ) -> str:
        """Generate brief description from function name."""
        # Convert snake_case to words
        words = name.lstrip("_").replace("_", " ").split()

        # Capitalize first word
        if words:
            words[0] = words[0].capitalize()

        description = " ".join(words)

        # Add context
        if is_property:
            if name.startswith("is_") or name.startswith("has_"):
                return f"Check if {' '.join(words[1:])}."
            return f"Get {description}."
        elif is_async:
            return f"{description}."
        else:
            return f"{description}."

    def _generate_args_section(
        self, node: ast.FunctionDef | ast.AsyncFunctionDef
    ) -> list[str]:
        """Generate Args section for docstring."""
        args = node.args.args
        if not args:
            return []

        # Skip self/cls
        start_idx = 1 if args[0].arg in ("self", "cls") else 0
        relevant_args = args[start_idx:]

        if not relevant_args:
            return []

        lines = ["Args:"]
        for arg in relevant_args:
            arg_name = arg.arg
            # Try to infer description from name
            description = self._infer_arg_description(arg_name)
            lines.append(f"    {arg_name}: {description}")

        return lines

    def _infer_arg_description(self, arg_name: str) -> str:
        """Infer argument description from its name."""
        # Common patterns
        if arg_name == "config":
            return "Configuration object"
        elif arg_name in ("data", "value", "content"):
            return f"{arg_name.capitalize()} to process"
        elif arg_name.endswith("_id"):
            return f"{arg_name[:-3].replace('_', ' ').capitalize()} identifier"
        elif arg_name.endswith("_path"):
            return f"Path to {arg_name[:-5].replace('_', ' ')}"
        elif arg_name.endswith("_url"):
            return f"URL for {arg_name[:-4].replace('_', ' ')}"
        elif arg_name in ("request", "response", "event", "action", "observation"):
            return f"{arg_name.capitalize()} object"
        else:
            return arg_name.replace("_", " ").capitalize()

    def _generate_returns_section(
        self, node: ast.FunctionDef | ast.AsyncFunctionDef
    ) -> str:
        """Generate Returns section for docstring."""
        if node.returns:
            return_type = (
                ast.unparse(node.returns) if hasattr(ast, "unparse") else "Return value"
            )
            return f"Returns:\n    {return_type}"
        return ""

    def process_file(self, file_path: str) -> bool:
        """Process a single Python file and add missing docstrings.

        Args:
            file_path: Path to Python file

        Returns:
            True if file was modified
        """
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read()
                source_lines = content.split("\n")

            tree = ast.parse(content, filename=file_path)

            # Find all functions/methods without docstrings
            modifications = []
            for node in ast.walk(tree):
                if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    if not ast.get_docstring(node):
                        self.stats["functions_processed"] += 1
                        docstring = self.generate_function_docstring(node, source_lines)
                        modifications.append((node.lineno, node.col_offset, docstring))

            if modifications:
                # Apply modifications (working backwards to preserve line numbers)
                lines = source_lines.copy()
                for lineno, col_offset, docstring in reversed(modifications):
                    # Insert docstring after function definition
                    indent = " " * (col_offset + 4)
                    docstring_lines = [indent + line for line in docstring.split("\n")]
                    lines.insert(lineno, "\n".join(docstring_lines))

                # Write back
                with open(file_path, "w", encoding="utf-8") as f:
                    f.write("\n".join(lines))

                self.stats["docstrings_added"] += len(modifications)
                self.stats["files_modified"] += 1
                return True

            return False

        except Exception as e:
            print(f"Error processing {file_path}: {e}")
            return False

    def process_directory(self, directory: str = "forge") -> None:
        """Process all Python files in directory recursively.

        Args:
            directory: Root directory to scan
        """
        for root, dirs, files in os.walk(directory):
            # Skip hidden dirs and __pycache__
            dirs[:] = [d for d in dirs if not d.startswith(".") and d != "__pycache__"]

            for file in files:
                if file.endswith(".py"):
                    file_path = os.path.join(root, file)
                    print(f"Processing: {file_path}")
                    self.process_file(file_path)

        print("\n" + "=" * 50)
        print("DOCSTRING GENERATION COMPLETE")
        print("=" * 50)
        print(f"Functions processed: {self.stats['functions_processed']}")
        print(f"Docstrings added: {self.stats['docstrings_added']}")
        print(f"Files modified: {self.stats['files_modified']}")


if __name__ == "__main__":
    generator = DocstringGenerator()
    generator.process_directory("forge")
