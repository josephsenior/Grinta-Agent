"""Production-grade diff generation utilities.

Provides advanced unified diff generation with proper formatting, context lines,
and intelligent hunk detection. Designed for production use in agent runtime environments.
"""

from __future__ import annotations

import difflib
import mimetypes
from typing import Optional


def get_diff(
    old: str,
    new: str,
    path: Optional[str] = None,
    context_lines: int = 3,
    ignore_whitespace: bool = False,
) -> str:
    r"""Generate a unified diff between two text strings.

    This is a production-grade implementation that provides:
    - Proper unified diff format (compatible with git, patch, etc.)
    - Configurable context lines
    - Intelligent hunk detection
    - Whitespace handling options
    - Proper file header formatting

    Args:
        old: The original text content
        new: The new text content
        path: Optional file path for the diff header (defaults to 'old'/'new')
        context_lines: Number of context lines to include around changes (default: 3)
        ignore_whitespace: If True, normalize whitespace before diffing (default: False)

    Returns:
        Unified diff string in standard format, or error message for binary files

    Example:
        >>> old = "def hello():\n    print('world')\n"
        >>> new = "def hello():\n    print('hello world')\n"
        >>> diff = get_diff(old, new, path="test.py")
        >>> print(diff)
        --- test.py
        +++ test.py
        @@ -1,2 +1,2 @@
         def hello():
        -    print('world')
        +    print('hello world')
    """
    # Detect binary files
    if path:
        mime_type, _ = mimetypes.guess_type(path)
        if mime_type and not mime_type.startswith(("text/", "application/json", "application/xml")):
            return f"Binary file {path} - diff not available\n"

    # Check for binary content
    if _is_binary(old) or _is_binary(new):
        return f"Binary content detected - diff not available for {path or 'file'}\n"

    # Normalize inputs
    old_lines = old.splitlines(keepends=True) if old else []
    new_lines = new.splitlines(keepends=True) if new else []

    # Handle whitespace normalization if requested
    if ignore_whitespace:
        old_lines = [_normalize_whitespace(line) for line in old_lines]
        new_lines = [_normalize_whitespace(line) for line in new_lines]

    # Generate unified diff
    diff_generator = difflib.unified_diff(
        old_lines,
        new_lines,
        fromfile=path or "old",
        tofile=path or "new",
        lineterm="",
        n=context_lines,
    )

    # Convert generator to list and filter out empty diffs
    diff_lines = list(diff_generator)

    # If no differences, return empty string
    if not diff_lines or len(diff_lines) <= 2:
        return ""

    # Join lines and ensure proper formatting
    diff_text = "\n".join(diff_lines)

    # Ensure trailing newline for proper formatting
    if not diff_text.endswith("\n"):
        diff_text += "\n"

    return diff_text


def _is_binary(content: str) -> bool:
    """Check if content appears to be binary.

    Args:
        content: Content string to check

    Returns:
        True if content appears to be binary, False otherwise
    """
    if not content:
        return False

    # Check for null bytes (strong indicator of binary)
    if "\x00" in content:
        return True

    # Check first 1000 bytes for high ratio of non-printable characters
    sample = content[:1000]
    if not sample:
        return False

    non_printable = sum(
        1 for c in sample
        if ord(c) < 32 and c not in "\n\r\t" and ord(c) != 0
    )
    ratio = non_printable / len(sample)

    # If more than 30% non-printable (excluding common whitespace), likely binary
    return ratio > 0.3


def _normalize_whitespace(line: str) -> str:
    """Normalize whitespace in a line for comparison.

    Preserves leading/trailing structure but normalizes internal whitespace.
    """
    # Preserve line ending
    has_newline = line.endswith("\n") or line.endswith("\r\n")
    line_content = line.rstrip("\n\r")

    # Normalize tabs to spaces and collapse multiple spaces
    normalized = " ".join(line_content.split())

    # Restore line ending
    return normalized + ("\n" if has_newline else "")


def get_diff_stats(diff_text: str) -> dict[str, int]:
    """Calculate statistics from a unified diff.

    Args:
        diff_text: Unified diff string

    Returns:
        Dictionary with statistics:
        - lines_added: Number of lines added
        - lines_removed: Number of lines removed
        - hunks: Number of change hunks
        - files_changed: Number of files in diff (usually 1)
    """
    if not diff_text:
        return {
            "lines_added": 0,
            "lines_removed": 0,
            "hunks": 0,
            "files_changed": 0,
        }

    lines = diff_text.splitlines()
    lines_added = sum(1 for line in lines if line.startswith("+") and not line.startswith("+++"))
    lines_removed = sum(1 for line in lines if line.startswith("-") and not line.startswith("---"))
    hunks = sum(1 for line in lines if line.startswith("@@"))
    files_changed = len(set(line for line in lines if line.startswith("---") or line.startswith("+++")))

    return {
        "lines_added": lines_added,
        "lines_removed": lines_removed,
        "hunks": hunks,
        "files_changed": files_changed,
    }

