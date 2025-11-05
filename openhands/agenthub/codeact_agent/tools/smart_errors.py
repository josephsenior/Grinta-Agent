"""
Smart Error Messages - Helpful Suggestions and Fuzzy Matching

Provides intelligent error messages when edits fail:
- Fuzzy matching for typos in symbol names
- Suggestions for similar symbols
- Context-aware error messages
- Auto-correction hints
"""

from __future__ import annotations

import difflib
from dataclasses import dataclass
from typing import List, Optional, Dict, Any

from openhands.core.logger import openhands_logger as logger


@dataclass
class ErrorSuggestion:
    """A suggestion for fixing an error."""
    message: str
    suggestions: List[str]
    confidence: float  # 0.0 to 1.0
    auto_fixable: bool = False
    fix_code: Optional[str] = None


class SmartErrorHandler:
    """
    Intelligent error handler that provides helpful suggestions.
    
    Features:
    - Fuzzy matching for typos ("functino" → "function")
    - Similar symbol suggestions
    - Context-aware error messages
    - Auto-fix recommendations
    """
    
    # Common typos and corrections
    COMMON_TYPOS = {
        'functino': 'function',
        'fucntion': 'function',
        'funciton': 'function',
        'calss': 'class',
        'classs': 'class',
        'clas': 'class',
        'defination': 'definition',
        'definiton': 'definition',
        'improt': 'import',
        'imoprt': 'import',
        'retrun': 'return',
        'reutrn': 'return',
        'variabel': 'variable',
        'variabl': 'variable',
    }
    
    @staticmethod
    def symbol_not_found(
        symbol_name: str,
        available_symbols: List[str],
        max_suggestions: int = 5
    ) -> ErrorSuggestion:
        """
        Generate error message when a symbol is not found.
        
        Args:
            symbol_name: The symbol that was not found
            available_symbols: List of available symbols
            max_suggestions: Maximum number of suggestions to return
            
        Returns:
            ErrorSuggestion with helpful hints
        """
        # Check for common typos
        if symbol_name.lower() in SmartErrorHandler.COMMON_TYPOS:
            correction = SmartErrorHandler.COMMON_TYPOS[symbol_name.lower()]
            return ErrorSuggestion(
                message=f"Symbol '{symbol_name}' not found. Did you mean '{correction}'?",
                suggestions=[correction],
                confidence=0.95,
                auto_fixable=True,
                fix_code=correction
            )
        
        # Fuzzy match against available symbols
        close_matches = difflib.get_close_matches(
            symbol_name,
            available_symbols,
            n=max_suggestions,
            cutoff=0.6  # 60% similarity threshold
        )
        
        if close_matches:
            # Calculate confidence based on similarity
            best_match = close_matches[0]
            similarity = difflib.SequenceMatcher(None, symbol_name, best_match).ratio()
            
            if similarity > 0.9:
                message = f"Symbol '{symbol_name}' not found. Did you mean '{best_match}'?"
                auto_fixable = True
            elif similarity > 0.7:
                message = f"Symbol '{symbol_name}' not found. Similar symbols: {', '.join(close_matches[:3])}"
                auto_fixable = False
            else:
                message = f"Symbol '{symbol_name}' not found. Possible matches: {', '.join(close_matches[:3])}"
                auto_fixable = False
            
            return ErrorSuggestion(
                message=message,
                suggestions=close_matches,
                confidence=similarity,
                auto_fixable=auto_fixable,
                fix_code=best_match if auto_fixable else None
            )
        
        # No close matches - provide helpful context
        if available_symbols:
            # Group symbols by type if possible
            functions = [s for s in available_symbols if not s[0].isupper()]
            classes = [s for s in available_symbols if s[0].isupper()]
            
            available_info = []
            if classes:
                available_info.append(f"{len(classes)} classes")
            if functions:
                available_info.append(f"{len(functions)} functions")
            
            context = f" ({', '.join(available_info)} available)" if available_info else ""
            message = f"Symbol '{symbol_name}' not found{context}. Available symbols:\n" + \
                     "\n".join(f"  - {s}" for s in available_symbols[:10])
            
            if len(available_symbols) > 10:
                message += f"\n  ... and {len(available_symbols) - 10} more"
        else:
            message = f"Symbol '{symbol_name}' not found and no symbols are available in this file."
        
        return ErrorSuggestion(
            message=message,
            suggestions=available_symbols[:max_suggestions],
            confidence=0.0
        )
    
    @staticmethod
    def syntax_error(
        error_message: str,
        line_number: Optional[int] = None,
        code_context: Optional[str] = None
    ) -> ErrorSuggestion:
        """
        Generate helpful message for syntax errors.
        
        Args:
            error_message: Original error message
            line_number: Line where error occurred
            code_context: Code surrounding the error
            
        Returns:
            ErrorSuggestion with context and hints
        """
        suggestions = []
        confidence = 0.5
        
        # Common syntax error patterns and hints
        error_lower = error_message.lower()
        
        if 'unexpected indent' in error_lower or 'indentation' in error_lower:
            suggestions.append("Check your indentation - Python requires consistent spacing")
            suggestions.append("Make sure you're using either tabs or spaces, not both")
            confidence = 0.8
        
        elif 'unterminated string' in error_lower:
            suggestions.append("You have an unclosed string - check for missing quotes")
            suggestions.append("Look for unescaped quotes inside your string")
            confidence = 0.9
        
        elif 'invalid syntax' in error_lower:
            if ':' in (code_context or ''):
                suggestions.append("Check for missing colons after if/for/def/class statements")
            if '(' in (code_context or '') and ')' not in (code_context or ''):
                suggestions.append("You might have unmatched parentheses")
            if '[' in (code_context or '') and ']' not in (code_context or ''):
                suggestions.append("You might have unmatched brackets")
            suggestions.append("Double-check your syntax against language documentation")
            confidence = 0.6
        
        elif 'unexpected eof' in error_lower or 'unexpected end' in error_lower:
            suggestions.append("File ends unexpectedly - check for unclosed brackets/braces")
            suggestions.append("Make sure all functions and classes are complete")
            confidence = 0.85
        
        elif 'undefined' in error_lower or 'not defined' in error_lower:
            suggestions.append("This symbol is used before being defined")
            suggestions.append("Check for typos in the variable/function name")
            confidence = 0.75
        
        # Format message
        message_parts = [f"Syntax Error: {error_message}"]
        
        if line_number:
            message_parts.append(f"at line {line_number}")
        
        if code_context:
            message_parts.append(f"\nContext:\n{code_context}")
        
        if suggestions:
            message_parts.append("\nSuggestions:")
            for i, suggestion in enumerate(suggestions, 1):
                message_parts.append(f"  {i}. {suggestion}")
        
        return ErrorSuggestion(
            message='\n'.join(message_parts),
            suggestions=suggestions,
            confidence=confidence
        )
    
    @staticmethod
    def file_not_found(
        file_path: str,
        similar_files: Optional[List[str]] = None
    ) -> ErrorSuggestion:
        """
        Generate error message when file is not found.
        
        Args:
            file_path: The file that was not found
            similar_files: List of similar file paths
            
        Returns:
            ErrorSuggestion with file suggestions
        """
        if not similar_files:
            return ErrorSuggestion(
                message=f"File not found: {file_path}",
                suggestions=[],
                confidence=0.0
            )
        
        # Fuzzy match file paths
        close_matches = difflib.get_close_matches(
            file_path,
            similar_files,
            n=5,
            cutoff=0.5
        )
        
        if close_matches:
            best_match = close_matches[0]
            similarity = difflib.SequenceMatcher(None, file_path, best_match).ratio()
            
            message = f"File not found: {file_path}\n\nDid you mean one of these?"
            for match in close_matches[:3]:
                message += f"\n  - {match}"
            
            return ErrorSuggestion(
                message=message,
                suggestions=close_matches,
                confidence=similarity,
                auto_fixable=similarity > 0.85,
                fix_code=best_match if similarity > 0.85 else None
            )
        
        return ErrorSuggestion(
            message=f"File not found: {file_path}\n\nNo similar files found.",
            suggestions=[],
            confidence=0.0
        )
    
    @staticmethod
    def whitespace_mismatch(
        expected_indent: str,
        actual_indent: str,
        line_number: int
    ) -> ErrorSuggestion:
        """
        Generate error for whitespace/indentation mismatches.
        
        Args:
            expected_indent: Expected indentation style
            actual_indent: Actual indentation found
            line_number: Line number with issue
            
        Returns:
            ErrorSuggestion with fix hints
        """
        expected_type = "tabs" if '\t' in expected_indent else "spaces"
        actual_type = "tabs" if '\t' in actual_indent else "spaces"
        
        if expected_type != actual_type:
            message = f"Indentation mismatch at line {line_number}:\n" \
                     f"  Expected: {expected_type}\n" \
                     f"  Found: {actual_type}\n\n" \
                     f"This file uses {expected_type} for indentation. " \
                     f"Please be consistent."
        else:
            expected_count = len(expected_indent)
            actual_count = len(actual_indent)
            message = f"Indentation error at line {line_number}:\n" \
                     f"  Expected: {expected_count} {expected_type}\n" \
                     f"  Found: {actual_count} {actual_type}\n\n" \
                     f"Check your editor's tab/space settings."
        
        return ErrorSuggestion(
            message=message,
            suggestions=[
                "Enable 'show whitespace' in your editor to see tabs vs. spaces",
                "Configure your editor to use consistent indentation",
                "Use an auto-formatter like Black (Python) or Prettier (JS)"
            ],
            confidence=1.0,
            auto_fixable=True
        )
    
    @staticmethod
    def suggest_similar(
        target: str,
        candidates: List[str],
        threshold: float = 0.6
    ) -> List[str]:
        """
        Find similar strings using fuzzy matching.
        
        Args:
            target: String to match
            candidates: List of candidate strings
            threshold: Minimum similarity ratio (0.0-1.0)
            
        Returns:
            List of similar strings, sorted by similarity
        """
        return difflib.get_close_matches(target, candidates, n=10, cutoff=threshold)
    
    @staticmethod
    def format_edit_conflict(
        file_path: str,
        your_edit: str,
        other_edit: str
    ) -> ErrorSuggestion:
        """
        Format message for edit conflicts in multi-file refactoring.
        
        Args:
            file_path: File with conflict
            your_edit: Description of your edit
            other_edit: Description of conflicting edit
            
        Returns:
            ErrorSuggestion explaining the conflict
        """
        message = f"Edit conflict in {file_path}:\n\n" \
                 f"Your edit: {your_edit}\n" \
                 f"Conflicts with: {other_edit}\n\n" \
                 f"These edits cannot be applied simultaneously."
        
        suggestions = [
            "Apply one edit at a time",
            "Merge the edits manually",
            "Use a different approach that doesn't conflict"
        ]
        
        return ErrorSuggestion(
            message=message,
            suggestions=suggestions,
            confidence=1.0
        )
    
    @staticmethod
    def validate_edit_result(
        original_code: str,
        new_code: str,
        expected_changes: Optional[Dict[str, Any]] = None
    ) -> Optional[ErrorSuggestion]:
        """
        Validate an edit result and suggest improvements if needed.
        
        Args:
            original_code: Original code before edit
            new_code: Code after edit
            expected_changes: Expected changes (optional)
            
        Returns:
            ErrorSuggestion if issues found, None if OK
        """
        # Check if edit actually changed something
        if original_code == new_code:
            return ErrorSuggestion(
                message="Edit did not change anything. Verify your target location.",
                suggestions=[
                    "Double-check the symbol name",
                    "Verify the file path",
                    "Check if the code is already in the desired state"
                ],
                confidence=0.9
            )
        
        # Check for dramatic size changes (might indicate error)
        original_lines = len(original_code.split('\n'))
        new_lines = len(new_code.split('\n'))
        
        if original_lines > 100 and new_lines < original_lines * 0.1:
            return ErrorSuggestion(
                message=f"Warning: File shrank dramatically ({original_lines} → {new_lines} lines). " \
                       f"This might indicate an error.",
                suggestions=[
                    "Review the changes carefully",
                    "Make sure you didn't accidentally delete important code",
                    "Consider rolling back if this wasn't intentional"
                ],
                confidence=0.7
            )
        
        return None

