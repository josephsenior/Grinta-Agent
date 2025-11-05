"""
Whitespace Intelligence - Universal Indentation Handler

Handles indentation normalization and auto-correction for ALL languages.
Never breaks code due to tabs vs. spaces or indentation mismatches.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Tuple, Optional, List
from enum import Enum

from openhands.core.logger import openhands_logger as logger


class IndentStyle(Enum):
    """Indentation style."""
    SPACES = "spaces"
    TABS = "tabs"
    MIXED = "mixed"


@dataclass
class IndentConfig:
    """Indentation configuration for a file."""
    style: IndentStyle
    size: int  # Number of spaces per level (or 1 for tabs)
    line_ending: str  # \n or \r\n


class WhitespaceHandler:
    """
    Universal whitespace and indentation handler.
    
    Features:
    - Detects existing indentation style (tabs vs. spaces)
    - Normalizes inconsistent whitespace
    - Auto-indents new code blocks
    - Preserves intentional blank lines
    - Handles ALL languages
    """
    
    # Default indentation sizes by language
    DEFAULT_INDENT_SIZES = {
        'python': 4,
        'javascript': 2,
        'typescript': 2,
        'tsx': 2,
        'go': 1,  # Go uses tabs
        'rust': 4,
        'java': 4,
        'c': 4,
        'cpp': 4,
        'c_sharp': 4,
        'ruby': 2,
        'php': 4,
        'swift': 4,
        'kotlin': 4,
        'scala': 2,
        'json': 2,
        'yaml': 2,
        'html': 2,
        'css': 2,
    }
    
    @staticmethod
    def detect_indent(code: str, language: Optional[str] = None) -> IndentConfig:
        """
        Detect indentation style from existing code.
        
        Args:
            code: Source code content
            language: Optional language hint
            
        Returns:
            IndentConfig with detected settings
        """
        lines = code.split('\n')
        
        # Detect line ending
        if '\r\n' in code:
            line_ending = '\r\n'
        else:
            line_ending = '\n'
        
        # Count tabs vs. spaces at start of lines
        tab_count = 0
        space_count = 0
        space_sizes = []
        
        for line in lines:
            if not line or not line[0].isspace():
                continue
            
            # Count leading whitespace
            leading = len(line) - len(line.lstrip())
            
            if line[0] == '\t':
                tab_count += 1
            elif line[0] == ' ':
                space_count += 1
                space_sizes.append(leading)
        
        # Determine style
        if tab_count > space_count:
            style = IndentStyle.TABS
            size = 1
        elif space_count > 0:
            style = IndentStyle.SPACES
            # Find most common indentation size
            if space_sizes:
                size = WhitespaceHandler._find_indent_size(space_sizes)
            else:
                size = WhitespaceHandler.DEFAULT_INDENT_SIZES.get(language or '', 4)
        else:
            # No indented lines found, use language defaults
            style = IndentStyle.TABS if language == 'go' else IndentStyle.SPACES
            size = 1 if language == 'go' else WhitespaceHandler.DEFAULT_INDENT_SIZES.get(language or '', 4)
        
        return IndentConfig(style=style, size=size, line_ending=line_ending)
    
    @staticmethod
    def _find_indent_size(space_counts: List[int]) -> int:
        """Find the most likely indentation size from leading space counts."""
        if not space_counts:
            return 4
        
        # Calculate differences between consecutive indentation levels
        diffs = []
        for i in range(1, len(space_counts)):
            diff = abs(space_counts[i] - space_counts[i-1])
            if diff > 0:
                diffs.append(diff)
        
        if not diffs:
            # Fall back to most common space count
            from collections import Counter
            counts = Counter(space_counts)
            return counts.most_common(1)[0][0] if counts else 4
        
        # Find GCD of differences (most likely indent size)
        from math import gcd
        from functools import reduce
        result = reduce(gcd, diffs)
        
        # Validate result (should be 2, 4, or 8)
        if result in {2, 4, 8}:
            return result
        elif result == 1:
            return 4  # Default
        else:
            return result if result < 8 else 4
    
    @staticmethod
    def normalize_indent(
        code: str,
        target_config: Optional[IndentConfig] = None,
        language: Optional[str] = None
    ) -> str:
        """
        Normalize indentation to match target config.
        
        Args:
            code: Source code to normalize
            target_config: Target indentation config (detected if None)
            language: Language hint for defaults
            
        Returns:
            Code with normalized indentation
        """
        if not code:
            return code
        
        # Detect current indentation
        current_config = WhitespaceHandler.detect_indent(code, language)
        
        # Use detected config if no target specified
        if not target_config:
            target_config = current_config
        
        # If styles match, no conversion needed
        if current_config.style == target_config.style and current_config.size == target_config.size:
            # Just normalize line endings
            if current_config.line_ending != target_config.line_ending:
                return code.replace(current_config.line_ending, target_config.line_ending)
            return code
        
        # Convert indentation
        lines = code.split('\n')
        normalized_lines = []
        
        for line in lines:
            if not line or not line[0].isspace():
                normalized_lines.append(line)
                continue
            
            # Calculate current indent level
            leading_ws = len(line) - len(line.lstrip())
            content = line.lstrip()
            
            if current_config.style == IndentStyle.TABS:
                indent_level = leading_ws  # Each tab = 1 level
            else:
                indent_level = leading_ws // current_config.size
            
            # Apply target indentation
            if target_config.style == IndentStyle.TABS:
                new_indent = '\t' * indent_level
            else:
                new_indent = ' ' * (indent_level * target_config.size)
            
            normalized_lines.append(new_indent + content)
        
        result = '\n'.join(normalized_lines)
        
        # Normalize line endings
        if target_config.line_ending != '\n':
            result = result.replace('\n', target_config.line_ending)
        
        return result
    
    @staticmethod
    def auto_indent_block(
        code_block: str,
        base_indent: int,
        config: Optional[IndentConfig] = None,
        language: Optional[str] = None
    ) -> str:
        """
        Auto-indent a code block to a specific level.
        
        Args:
            code_block: Code to indent
            base_indent: Base indentation level
            config: Indentation config (detected if None)
            language: Language hint
            
        Returns:
            Indented code block
        """
        if not config:
            config = WhitespaceHandler.detect_indent(code_block, language)
            # If no indent detected, use language defaults
            if config.style == IndentStyle.SPACES and config.size == 4 and language:
                default_size = WhitespaceHandler.DEFAULT_INDENT_SIZES.get(language, 4)
                if language == 'go':
                    config = IndentConfig(style=IndentStyle.TABS, size=1, line_ending=config.line_ending)
                else:
                    config = IndentConfig(style=config.style, size=default_size, line_ending=config.line_ending)
        
        # Generate base indentation string
        if config.style == IndentStyle.TABS:
            base_indent_str = '\t' * base_indent
        else:
            base_indent_str = ' ' * (base_indent * config.size)
        
        # Split into lines and indent each
        lines = code_block.split('\n')
        indented_lines = []
        
        for line in lines:
            if line.strip():  # Only indent non-empty lines
                indented_lines.append(base_indent_str + line)
            else:
                indented_lines.append('')  # Keep blank lines blank
        
        return '\n'.join(indented_lines)
    
    @staticmethod
    def get_line_indent(line: str, config: IndentConfig) -> int:
        """
        Get the indentation level of a line.
        
        Args:
            line: Line of code
            config: Indentation config
            
        Returns:
            Indentation level (0 for no indent)
        """
        if not line or not line[0].isspace():
            return 0
        
        leading_ws = len(line) - len(line.lstrip())
        
        if config.style == IndentStyle.TABS:
            return leading_ws
        else:
            return leading_ws // config.size
    
    @staticmethod
    def preserve_relative_indent(
        code_block: str,
        new_base_indent: int,
        config: Optional[IndentConfig] = None,
        language: Optional[str] = None
    ) -> str:
        """
        Re-indent code block while preserving relative indentation.
        
        Useful when moving code to a new location with different base indent.
        
        Args:
            code_block: Code to re-indent
            new_base_indent: New base indentation level
            config: Indentation config (detected if None)
            language: Language hint
            
        Returns:
            Re-indented code with preserved relative structure
        """
        if not code_block:
            return code_block
        
        # Detect config if not provided
        if not config:
            config = WhitespaceHandler.detect_indent(code_block, language)
            if language == 'go' and config.style != IndentStyle.TABS:
                config = IndentConfig(style=IndentStyle.TABS, size=1, line_ending=config.line_ending)
        
        lines = code_block.split('\n')
        
        # Find minimum indentation (to dedent first)
        min_indent = float('inf')
        for line in lines:
            if line.strip():  # Ignore blank lines
                indent_level = WhitespaceHandler.get_line_indent(line, config)
                min_indent = min(min_indent, indent_level)
        
        if min_indent == float('inf'):
            min_indent = 0
        
        # Re-indent all lines
        result_lines = []
        for line in lines:
            if not line.strip():
                result_lines.append('')
                continue
            
            # Get current indent and dedent
            current_indent = WhitespaceHandler.get_line_indent(line, config)
            relative_indent = current_indent - min_indent
            
            # Apply new base indent + relative indent
            total_indent = new_base_indent + relative_indent
            
            if config.style == IndentStyle.TABS:
                new_indent_str = '\t' * total_indent
            else:
                new_indent_str = ' ' * (total_indent * config.size)
            
            result_lines.append(new_indent_str + line.lstrip())
        
        return '\n'.join(result_lines)
    
    @staticmethod
    def strip_trailing_whitespace(code: str) -> str:
        """Remove trailing whitespace from all lines."""
        lines = code.split('\n')
        return '\n'.join(line.rstrip() for line in lines)
    
    @staticmethod
    def ensure_final_newline(code: str) -> str:
        """Ensure file ends with exactly one newline."""
        code = code.rstrip('\n')
        return code + '\n'
    
    @staticmethod
    def clean_whitespace(
        code: str,
        config: Optional[IndentConfig] = None,
        language: Optional[str] = None
    ) -> str:
        """
        Comprehensive whitespace cleanup.
        
        Args:
            code: Source code
            config: Indentation config (detected if None)
            language: Language hint
            
        Returns:
            Cleaned code
        """
        if not config:
            config = WhitespaceHandler.detect_indent(code, language)
        
        # Normalize indentation
        code = WhitespaceHandler.normalize_indent(code, config, language)
        
        # Strip trailing whitespace
        code = WhitespaceHandler.strip_trailing_whitespace(code)
        
        # Ensure final newline
        code = WhitespaceHandler.ensure_final_newline(code)
        
        # Remove multiple consecutive blank lines (max 2)
        code = re.sub(r'\n{4,}', '\n\n\n', code)
        
        return code

