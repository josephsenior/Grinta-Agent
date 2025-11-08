"""Ultimate editor providing a unified interface for structure-aware editing.

High-level interface that intelligently routes operations to the best editor backend.
Provides simple, powerful API for all code editing operations.
"""

from __future__ import annotations

from typing import Optional, List, Dict, Any, Tuple
from dataclasses import dataclass
from pathlib import Path

from forge.core.logger import forge_logger as logger

from .universal_editor import UniversalEditor, EditResult, SymbolLocation
from .whitespace_handler import WhitespaceHandler, IndentConfig
from .atomic_refactor import AtomicRefactor, RefactorTransaction, RefactorResult
from .smart_errors import SmartErrorHandler, ErrorSuggestion


@dataclass
class EditorConfig:
    """Configuration for the ultimate editor."""

    auto_indent: bool = True
    validate_syntax: bool = True
    clean_whitespace: bool = True
    backup_enabled: bool = True
    dry_run_first: bool = False


class UltimateEditor:
    """The Ultimate File Editor - Structure-aware, language-agnostic, safe.
    
    Features:
    - Universal Tree-sitter parsing (40+ languages)
    - Symbol-based editing (edit by function/class name, not line numbers)
    - Intelligent whitespace handling (never breaks on tabs vs. spaces)
    - Atomic multi-file refactoring with rollback
    - Syntax validation before saving
    - Smart error messages with suggestions
    - Multi-file atomic operations
    
    Usage Examples:
    
    ```python
    editor = UltimateEditor()
    
    # Edit a function by name (no line numbers!)
    result = editor.edit_function(
        "myfile.py",
        "process_data",
        new_body="    return data.strip().lower()"
    )
    
    # Rename across the entire file
    result = editor.rename_symbol("myfile.py", "old_name", "new_name")
    
    # Multi-file refactoring (atomic - all succeed or all fail)
    with editor.begin_refactoring() as refactor:
        refactor.edit_file("file1.py", new_content="...")
        refactor.edit_file("file2.py", new_content="...")
        # Commits automatically, or rolls back on error
    ```
    """
    
    def __init__(self, config: Optional[EditorConfig] = None):
        """Initialize the ultimate editor.
        
        Args:
            config: Editor configuration

        """
        self.config = config or EditorConfig()
        
        # Initialize backends
        self.universal = UniversalEditor()
        self.whitespace = WhitespaceHandler()
        self.refactor = AtomicRefactor()
        self.errors = SmartErrorHandler()
        
        logger.info("🚀 Ultimate Editor initialized")
        logger.info(f"   - Tree-sitter: {len(self.universal.get_supported_languages())} languages")
        logger.info(f"   - Auto-indent: {self.config.auto_indent}")
        logger.info(f"   - Validation: {self.config.validate_syntax}")
    
    # ========================================================================
    # HIGH-LEVEL OPERATIONS
    # ========================================================================
    
    def edit_function(
        self,
        file_path: str,
        function_name: str,
        new_body: str
    ) -> EditResult:
        """Edit a function by name (works for ANY language).
        
        Args:
            file_path: Path to the file
            function_name: Name of the function to edit
            new_body: New function body
            
        Returns:
            EditResult with success status

        """
        logger.info(f"Editing function '{function_name}' in {file_path}")
        
        # Detect language
        language = self.universal.detect_language(file_path)
        if not language:
            return EditResult(
                success=False,
                message=f"Cannot detect language for {file_path}"
            )
        
        # Auto-indent new body if requested
        if self.config.auto_indent:
            try:
                # Read file to detect indentation
                with open(file_path, 'r', encoding='utf-8') as f:
                    original_content = f.read()
                
                indent_config = self.whitespace.detect_indent(original_content, language)
                
                # Auto-indent the new body (assume base indent level 1 for function body)
                new_body = self.whitespace.auto_indent_block(
                    new_body,
                    base_indent=1,
                    config=indent_config,
                    language=language
                )
            except Exception as e:
                logger.warning(f"Auto-indent failed: {e}")
        
        # Perform edit
        result = self.universal.edit_function(
            file_path,
            function_name,
            new_body,
            validate=self.config.validate_syntax
        )
        
        # Clean whitespace if successful and requested
        if result.success and self.config.clean_whitespace:
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                cleaned = self.whitespace.clean_whitespace(content, language=language)
                
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(cleaned)
            except Exception as e:
                logger.warning(f"Whitespace cleanup failed: {e}")
        
        # Provide smart error message if failed
        if not result.success and "not found" in result.message.lower():
            # Try to find similar symbols
            try:
                available_symbols = self._get_available_symbols(file_path, "function")
                suggestion = self.errors.symbol_not_found(
                    function_name,
                    available_symbols
                )
                result.message += f"\n\n{suggestion.message}"
            except:
                pass
        
        return result
    
    def rename_symbol(
        self,
        file_path: str,
        old_name: str,
        new_name: str
    ) -> EditResult:
        """Rename a symbol throughout a file.
        
        Args:
            file_path: Path to the file
            old_name: Current symbol name
            new_name: New symbol name
            
        Returns:
            EditResult with success status

        """
        logger.info(f"Renaming '{old_name}' → '{new_name}' in {file_path}")
        
        result = self.universal.rename_symbol(file_path, old_name, new_name)
        
        # Clean whitespace if successful
        if result.success and self.config.clean_whitespace:
            language = self.universal.detect_language(file_path)
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                cleaned = self.whitespace.clean_whitespace(content, language=language)
                
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(cleaned)
            except Exception as e:
                logger.warning(f"Whitespace cleanup failed: {e}")
        
        return result
    
    def find_symbol(
        self,
        file_path: str,
        symbol_name: str,
        symbol_type: Optional[str] = None
    ) -> Optional[SymbolLocation]:
        """Find a symbol in a file.
        
        Args:
            file_path: Path to the file
            symbol_name: Name of the symbol (supports "Class.method")
            symbol_type: Optional type filter ("function", "class", "method")
            
        Returns:
            SymbolLocation if found, None otherwise

        """
        result = self.universal.find_symbol(file_path, symbol_name, symbol_type)
        
        if not result:
            # Provide smart error
            try:
                available_symbols = self._get_available_symbols(file_path, symbol_type)
                suggestion = self.errors.symbol_not_found(symbol_name, available_symbols)
                logger.warning(suggestion.message)
            except:
                logger.warning(f"Symbol '{symbol_name}' not found in {file_path}")
        
        return result
    
    def _validate_line_range(self, start_line: int, end_line: int, total_lines: int) -> tuple[bool, str]:
        """Validate line range is valid.
        
        Args:
            start_line: Start line
            end_line: End line
            total_lines: Total lines in file
            
        Returns:
            Tuple of (is_valid, error_message)

        """
        if start_line < 1 or end_line > total_lines or start_line > end_line:
            return False, f"Invalid line range: {start_line}-{end_line} (file has {total_lines} lines)"
        return True, ""

    def _apply_auto_indent(
        self,
        new_code: str,
        lines: list[str],
        start_line: int,
        file_path: str
    ) -> str:
        """Apply auto-indentation to new code.
        
        Args:
            new_code: New code to indent
            lines: Original file lines
            start_line: Line to replace
            file_path: File path
            
        Returns:
            Indented code

        """
        if not self.config.auto_indent:
            return new_code
        
        language = self.universal.detect_language(file_path)
        original_content = ''.join(lines)
        indent_config = self.whitespace.detect_indent(original_content, language)
        
        if start_line <= len(lines):
            base_indent = self.whitespace.get_line_indent(
                lines[start_line - 1],
                indent_config
            )
            return self.whitespace.auto_indent_block(
                new_code,
                base_indent=base_indent,
                config=indent_config,
                language=language
            )
        return new_code

    def _validate_syntax_after_edit(
        self,
        new_content: str,
        original_lines: list[str],
        file_path: str
    ) -> tuple[bool, str]:
        """Validate syntax of edited content.
        
        Args:
            new_content: New content to validate
            original_lines: Original lines
            file_path: File path
            
        Returns:
            Tuple of (is_valid, error_message)

        """
        if not self.config.validate_syntax:
            return True, ""
        
        language = self.universal.detect_language(file_path)
        if language:
            validation = self.universal._validate_syntax(new_content, file_path, language)
            if not validation[0]:
                return False, f"Syntax error after edit: {validation[1]}"
        
        return True, ""

    def _write_and_clean_file(self, file_path: str, content: str) -> None:
        """Write content to file and optionally clean whitespace.
        
        Args:
            file_path: Path to file
            content: Content to write

        """
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(content)
        
        if self.config.clean_whitespace:
            language = self.universal.detect_language(file_path)
            cleaned = self.whitespace.clean_whitespace(content, language=language)
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(cleaned)

    def replace_code_range(
        self,
        file_path: str,
        start_line: int,
        end_line: int,
        new_code: str
    ) -> EditResult:
        """Replace a range of lines with new code.
        
        Args:
            file_path: Path to the file
            start_line: Start line (1-indexed)
            end_line: End line (1-indexed, inclusive)
            new_code: New code to insert
            
        Returns:
            EditResult with success status

        """
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                lines = f.readlines()
            
            is_valid, error_msg = self._validate_line_range(start_line, end_line, len(lines))
            if not is_valid:
                return EditResult(success=False, message=error_msg)
            
            new_code = self._apply_auto_indent(new_code, lines, start_line, file_path)
            
            new_lines = lines[:start_line-1] + [new_code + '\n'] + lines[end_line:]
            new_content = ''.join(new_lines)
            
            is_valid, error_msg = self._validate_syntax_after_edit(new_content, lines, file_path)
            if not is_valid:
                return EditResult(
                    success=False,
                    message=error_msg,
                    syntax_valid=False,
                    original_code=''.join(lines)
                )
            
            self._write_and_clean_file(file_path, new_content)
            
            return EditResult(
                success=True,
                message=f"Replaced lines {start_line}-{end_line}",
                modified_code=new_content,
                lines_changed=end_line - start_line + 1,
                original_code=''.join(lines)
            )
        
        except Exception as e:
            return EditResult(
                success=False,
                message=f"Error: {e}"
            )
    
    # ========================================================================
    # MULTI-FILE OPERATIONS
    # ========================================================================
    
    def begin_refactoring(self) -> RefactorTransaction:
        """Begin a multi-file atomic refactoring transaction.
        
        Usage:
            transaction = editor.begin_refactoring()
            transaction.add_edit(...) 
            result = editor.commit_refactoring(transaction)
        
        Or use context manager:
            with editor.begin_refactoring() as transaction:
                transaction.add_edit(...)
                # Auto-commits on success, rolls back on error
        
        Returns:
            RefactorTransaction

        """
        return self.refactor.begin_transaction()
    
    def commit_refactoring(self, transaction: RefactorTransaction) -> RefactorResult:
        """Commit a refactoring transaction.
        
        Args:
            transaction: Transaction to commit
            
        Returns:
            RefactorResult with success status

        """
        # Dry-run first if requested
        if self.config.dry_run_first:
            dry_result = self.refactor.dry_run(transaction)
            if not dry_result.success:
                logger.warning(f"Dry-run failed: {dry_result.message}")
                return dry_result
        
        # Commit
        result = self.refactor.commit(transaction, validate=self.config.validate_syntax)
        
        # Cleanup on success
        if result.success:
            self.refactor.cleanup_transaction(transaction)
        
        return result
    
    def rollback_refactoring(self, transaction: RefactorTransaction) -> RefactorResult:
        """Rollback a refactoring transaction.
        
        Args:
            transaction: Transaction to rollback
            
        Returns:
            RefactorResult

        """
        result = self.refactor.rollback(transaction)
        self.refactor.cleanup_transaction(transaction)
        return result
    
    # ========================================================================
    # HELPER METHODS
    # ========================================================================
    
    def _get_available_symbols(
        self,
        file_path: str,
        symbol_type: Optional[str] = None
    ) -> List[str]:
        """Get list of available symbols in a file."""
        try:
            parse_result = self.universal.parse_file(file_path)
            if not parse_result:
                return []
            
            tree, file_bytes, language = parse_result
            root = tree.root_node
            
            symbols = []
            
            def extract_symbols(node):
                """Recursively extract function and class symbols from AST node.
                
                Args:
                    node: Tree-sitter AST node to extract symbols from

                """
                # Functions
                if node.type in ['function_definition', 'function_declaration', 'method_definition']:
                    name_node = self.universal._get_name_node(node)
                    if name_node:
                        name = file_bytes[name_node.start_byte:name_node.end_byte].decode('utf-8')
                        if not symbol_type or symbol_type == "function":
                            symbols.append(name)
                
                # Classes
                elif node.type in ['class_definition', 'class_declaration']:
                    name_node = self.universal._get_name_node(node)
                    if name_node:
                        name = file_bytes[name_node.start_byte:name_node.end_byte].decode('utf-8')
                        if not symbol_type or symbol_type == "class":
                            symbols.append(name)
                
                # Recurse
                for child in node.children:
                    extract_symbols(child)
            
            extract_symbols(root)
            return symbols
        
        except Exception as e:
            logger.debug(f"Failed to extract symbols: {e}")
            return []
    
    def get_supported_languages(self) -> List[str]:
        """Get list of all supported languages."""
        return self.universal.get_supported_languages()
    
    def normalize_file_indent(
        self,
        file_path: str,
        target_style: Optional[str] = None,
        target_size: Optional[int] = None
    ) -> EditResult:
        """Normalize indentation in a file.
        
        Args:
            file_path: Path to the file
            target_style: Target style ("spaces" or "tabs", auto-detected if None)
            target_size: Target indent size (auto-detected if None)
            
        Returns:
            EditResult

        """
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                original = f.read()
            
            language = self.universal.detect_language(file_path)
            
            # Create target config
            if target_style or target_size:
                from .whitespace_handler import IndentStyle
                current = self.whitespace.detect_indent(original, language)
                style = IndentStyle.TABS if target_style == "tabs" else IndentStyle.SPACES
                size = target_size or current.size
                from .whitespace_handler import IndentConfig
                target_config = IndentConfig(style=style, size=size, line_ending=current.line_ending)
            else:
                target_config = None
            
            # Normalize
            normalized = self.whitespace.normalize_indent(original, target_config, language)
            
            # Write back
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(normalized)
            
            return EditResult(
                success=True,
                message=f"Normalized indentation in {file_path}",
                modified_code=normalized,
                original_code=original
            )
        
        except Exception as e:
            return EditResult(
                success=False,
                message=f"Failed to normalize indentation: {e}"
            )
    
    def clear_caches(self):
        """Clear all internal caches."""
        self.universal.clear_cache()
        logger.debug("Cleared editor caches")

