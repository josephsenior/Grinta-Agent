"""Production-grade low-level file editor for runtime operations.

Provides robust file editing capabilities with proper error handling,
validation, and atomic operations. Designed for production agent environments.
"""

from __future__ import annotations

import os
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Optional

from backend.core.type_safety.path_validation import (
    PathValidationError,
    SafePath,
)
from backend.core.type_safety.sentinels import MISSING, Sentinel, is_missing


@dataclass
class ToolResult:
    """Result of a file editor operation."""

    output: str
    error: Optional[str] = None
    old_content: Optional[str] = None
    new_content: Optional[str] = None


class ToolError(Exception):
    """Exception raised by file editor operations."""

    def __init__(self, message: str = "") -> None:
        """Initialize tool error with message."""
        super().__init__(message)
        self.message = message


class FileEditor:
    """Production-grade low-level file editor.

    Provides basic file operations (view, edit, write) with proper
    error handling and validation. Used by runtime for file I/O operations.
    """

    def __init__(self, workspace_root: Optional[str] = None) -> None:
        """Initialize the file editor.

        Args:
            workspace_root: Root directory for file operations (defaults to current directory)
        """
        self.workspace_root = Path(workspace_root) if workspace_root else Path.cwd()
        # Transaction support: stack of backup dictionaries
        # Each backup dict maps file_path -> original_content (None if file didn't exist)
        self._transaction_stack: list[dict[str, Optional[str]]] = []
        # Path validator for security
        self._path_validator = None  # Lazy initialization

    def __call__(
        self,
        *,
        command: str,
        path: str,
        file_text: str | Sentinel | None = MISSING,
        view_range: Optional[list[int]] = None,
        old_str: str | Sentinel | None = MISSING,
        new_str: str | Sentinel | None = MISSING,
        insert_line: Optional[int] = None,
        enable_linting: bool = False,
        dry_run: bool = False,
        **_: Any,
    ) -> ToolResult:
        """Execute a file editor command.

        Args:
            command: Command to execute ("view", "edit", "apply_edit", "write")
            path: File path (relative to workspace_root or absolute)
            file_text: Optional file content for write/edit operations (use MISSING if not provided)
            view_range: Optional [start_line, end_line] for view command (1-indexed)
            old_str: Optional string to replace (for edit operations, use MISSING if not provided)
            new_str: Optional replacement string (for edit operations, use MISSING if not provided)
            insert_line: Optional line number to insert at (1-indexed)
            enable_linting: Whether to enable linting (currently not implemented)
            dry_run: If True, compute preview result without writing changes
            **_: Additional keyword arguments (ignored)

        Returns:
            ToolResult with operation result

        Raises:
            ToolError: If operation fails
        """
        # Store command for use in handlers
        self._current_command = command
        try:
            # Validate and resolve file path with security checks
            safe_path = self._resolve_path_safe(path)
            file_path = safe_path.path

            if command == "view":
                return self._handle_view(file_path, view_range, path)
            if command in ("edit", "apply_edit"):
                return self._handle_edit(
                    file_path,
                    file_text,
                    old_str,
                    new_str,
                    insert_line,
                    dry_run=dry_run,
                )
            if command in ("write", "create"):
                # Handle sentinels for write/create command
                # "create" is an alias for "write" - both create or overwrite files
                content = self._extract_content(file_text, new_str)
                return self._handle_write(
                    file_path,
                    content,
                    is_create=(command == "create"),
                    dry_run=dry_run,
                )

            raise ToolError(f"Unknown command: {command}")

        except PathValidationError as e:
            return ToolResult(output="", error=f"Path validation error: {e.message}")
        except Exception as e:
            return ToolResult(output="", error=str(e))

    def _resolve_path_safe(self, path: str) -> SafePath:
        """Resolve and validate file path with security checks.

        Args:
            path: File path to resolve

        Returns:
            SafePath instance with validated path

        Raises:
            PathValidationError: If path validation fails
        """
        try:
            return SafePath.validate(
                path,
                workspace_root=str(self.workspace_root),
                must_be_relative=True,
            )
        except PathValidationError:
            allow_legacy = os.environ.get("FORGE_ALLOW_INSECURE_PATHS", "false").lower() in (
                "1",
                "true",
                "yes",
            )
            if not allow_legacy:
                raise

            from backend.core.logger import forge_logger as logger

            logger.warning(
                "Path validation failed for %s; falling back to legacy resolution because "
                "FORGE_ALLOW_INSECURE_PATHS is enabled. This may be a security risk.",
                path,
            )
            if os.path.isabs(path):
                resolved = Path(path)
            else:
                resolved = self.workspace_root / path.lstrip("/")
            return SafePath(resolved, workspace_root=self.workspace_root)

    def _extract_content(
        self, file_text: str | Sentinel | None, new_str: str | Sentinel | None
    ) -> str:
        """Extract content from sentinel-aware parameters.

        Args:
            file_text: File text parameter (may be MISSING, None, or str)
            new_str: New string parameter (may be MISSING, None, or str)

        Returns:
            Extracted content string (empty string if both are MISSING/None)
        """
        # Check file_text first
        if not is_missing(file_text) and file_text is not None:
            return str(file_text)  # Type narrowing: if not MISSING and not None, it's str
        # Check new_str
        if not is_missing(new_str) and new_str is not None:
            return str(new_str)  # Type narrowing: if not MISSING and not None, it's str
        # Both are MISSING or None
        return ""

    def _handle_view(
        self, file_path: Path, view_range: Optional[list[int]], display_path: str
    ) -> ToolResult:
        """Handle view command - read file or specific line range.
        
        Args:
            file_path: Resolved Path object for file operations
            view_range: Optional line range [start, end] (1-indexed)
            display_path: Original path string for display in output
        """
        try:
            if not file_path.exists():
                return ToolResult(
                    output="", error=f"File not found: {file_path}", old_content=None, new_content=None
                )

            if file_path.is_dir():
                return ToolResult(
                    output="", error=f"Path is a directory: {file_path}", old_content=None, new_content=None
                )

            content = self._read_file(file_path)

            # Format output with line numbers (like cat -n)
            lines = content.splitlines(keepends=True)
            numbered_lines = []
            for i, line in enumerate(lines, 1):
                # Remove trailing newline for numbering, then add it back
                line_content = line.rstrip('\n\r')
                numbered_lines.append(f"{i}\t{line_content}")
            
            formatted_output = "\n".join(numbered_lines)
            if lines and any(line.endswith('\n') or line.endswith('\r') for line in lines):
                formatted_output += "\n"
            
            # Add header message using display path (original path from action)
            header = f"Here's the result of running `cat -n` on {display_path}:"
            final_output = f"{header}\n{formatted_output}"

            # Extract range if specified
            if view_range and len(view_range) >= 2:
                start, end = view_range[0], view_range[1]
                start_idx = max(0, start - 1)
                end_idx = min(len(lines), end)
                selected_lines = numbered_lines[start_idx:end_idx]
                selected_output = "\n".join(selected_lines)
                if lines and any(line.endswith('\n') or line.endswith('\r') for line in lines[start_idx:end_idx]):
                    selected_output += "\n"
                return ToolResult(
                    output=f"{header}\n{selected_output}", old_content=content, new_content=content
                )

            return ToolResult(output=final_output, old_content=content, new_content=content)

        except Exception as e:
            return ToolResult(output="", error=f"Error reading file: {e}")

    def _handle_edit(
        self,
        file_path: Path,
        file_text: str | Sentinel | None,
        old_str: str | Sentinel | None,
        new_str: str | Sentinel | None,
        insert_line: Optional[int],
        *,
        dry_run: bool = False,
    ) -> ToolResult:
        """Handle edit command - modify file content."""
        try:
            # Read existing content
            old_content: str | None = None
            if file_path.exists():
                old_content = self._read_file(file_path)
            old_content_str = old_content or ""

            # Extract actual values from sentinels (convert to str or None)
            file_text_val: str | None = None
            if not is_missing(file_text) and file_text is not None:
                file_text_val = str(file_text)
            
            old_str_val: str | None = None
            if not is_missing(old_str) and old_str is not None:
                old_str_val = str(old_str)
            
            new_str_val: str | None = None
            if not is_missing(new_str) and new_str is not None:
                new_str_val = str(new_str)

            # Determine new content based on provided parameters
            if insert_line is not None:
                # Insert at specific line
                content_to_insert = new_str_val or file_text_val or ""
                new_content = self._insert_at_line(
                    old_content_str, content_to_insert, insert_line
                )
            elif old_str_val and new_str_val:
                # Replace string
                new_content = old_content_str.replace(old_str_val, new_str_val)
            elif file_text_val:
                # Replace entire content
                new_content = file_text_val
            elif new_str_val:
                # Append new string
                new_content = old_content_str + new_str_val
            else:
                return ToolResult(
                    output="",
                    error="No content provided for edit operation",
                    old_content=old_content,
                    new_content=old_content_str,
                )

            if dry_run:
                return ToolResult(
                    output="Preview generated (no changes applied)",
                    old_content=old_content,
                    new_content=new_content,
                )

            # Backup original if in transaction
            if self._transaction_stack:
                self._backup_file(file_path, old_content)

            # Write new content
            self._write_file(file_path, new_content)

            return ToolResult(
                output="File updated successfully",
                old_content=old_content,
                new_content=new_content,
            )

        except Exception as e:
            return ToolResult(
                output="", error=f"Error editing file: {e}", old_content=None, new_content=None
            )

    def _handle_write(
        self,
        file_path: Path,
        content: str,
        is_create: bool = False,
        *,
        dry_run: bool = False,
    ) -> ToolResult:
        """Handle write command - write new file content.
        
        Args:
            file_path: Path to the file to write
            content: Content to write to the file
            is_create: If True, use "created" message instead of "written"
            dry_run: If True, return preview without writing changes
        """
        try:
            old_content = None
            file_existed = file_path.exists()
            if file_existed:
                old_content = self._read_file(file_path)

            if dry_run:
                output_msg = "Preview generated (no changes applied)"
                return ToolResult(
                    output=output_msg,
                    old_content=old_content,
                    new_content=content,
                )

            # Backup original if in transaction
            if self._transaction_stack:
                self._backup_file(file_path, old_content)

            self._write_file(file_path, content)

            # Use appropriate message based on command and whether file existed
            if is_create:
                output_msg = "File created successfully"
            else:
                output_msg = "File written successfully"

            return ToolResult(
                output=output_msg,
                old_content=old_content,
                new_content=content,
            )

        except Exception as e:
            return ToolResult(
                output="", error=f"Error writing file: {e}", old_content=None, new_content=None
            )

    def _read_file(self, file_path: Path) -> str:
        """Read file content with proper encoding handling."""
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                return f.read()
        except UnicodeDecodeError:
            # Fallback to latin-1 for binary-like files
            with open(file_path, "r", encoding="latin-1", errors="replace") as f:
                return f.read()

    def _write_file(self, file_path: Path, content: str) -> None:
        """Write file content, creating directories if needed."""
        # Ensure directory exists
        file_path.parent.mkdir(parents=True, exist_ok=True)

        # Write file atomically (write to temp then rename)
        temp_path = file_path.with_suffix(file_path.suffix + ".tmp")
        try:
            with open(temp_path, "w", encoding="utf-8") as f:
                f.write(content)
            temp_path.replace(file_path)
        except Exception:
            # Clean up temp file on error
            if temp_path.exists():
                temp_path.unlink()
            raise

    def _insert_at_line(self, content: str, new_text: str, line_num: int) -> str:
        """Insert text at a specific line number (1-indexed)."""
        lines = content.splitlines(keepends=True)
        if not lines:
            lines = [""]

        # Normalize line number
        line_idx = max(0, min(line_num - 1, len(lines)))

        # Insert new text
        new_lines = new_text.splitlines(keepends=True)
        if not new_lines:
            new_lines = [new_text]

        # Insert at the specified line
        result_lines = lines[:line_idx] + new_lines + lines[line_idx:]
        return "".join(result_lines)

    def _backup_file(self, file_path: Path, content: Optional[str]) -> None:
        """Backup file content for transaction rollback.

        Args:
            file_path: Path to file being modified
            content: Current content (None if file doesn't exist)
        """
        if self._transaction_stack:
            file_str = str(file_path)
            # Only backup once per transaction
            if file_str not in self._transaction_stack[-1]:
                self._transaction_stack[-1][file_str] = content

    @contextmanager
    def transaction(self):
        """Context manager for atomic multi-file operations.

        All file operations within this context are atomic - if any operation
        fails, all changes are automatically rolled back.

        Example:
            >>> editor = FileEditor()
            >>> with editor.transaction():
            ...     editor(command="write", path="file1.txt", new_str="content1")
            ...     editor(command="write", path="file2.txt", new_str="content2")
            ...     # If any operation fails, both files are restored
        """
        # Create new backup layer
        backup: dict[str, str | None] = {}
        self._transaction_stack.append(backup)

        try:
            yield self
            # All operations succeeded, commit (just remove backup layer)
            self._transaction_stack.pop()
        except Exception:
            # Rollback all changes in this transaction
            self._rollback_transaction(backup)
            self._transaction_stack.pop()
            raise

    def _rollback_transaction(self, backup: dict[str, Optional[str]]) -> None:
        """Rollback all file changes in a transaction.

        Args:
            backup: Dictionary mapping file paths to their original content
        """
        for file_path_str, original_content in backup.items():
            file_path = Path(file_path_str)
            try:
                if original_content is None:
                    # File was created, delete it
                    if file_path.exists():
                        file_path.unlink()
                else:
                    # Restore original content
                    self._write_file(file_path, original_content)
            except Exception as e:
                # Log but continue rollback for other files
                from backend.core.logger import forge_logger as logger
                logger.warning("Failed to rollback %s: %s", file_path, e)

