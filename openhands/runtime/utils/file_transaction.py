"""File transaction manager for atomic multi-file operations.

Provides rollback support for file operations to prevent partial state
when multi-file operations fail mid-way.
"""

from __future__ import annotations

import os
import shutil
import tempfile
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import TYPE_CHECKING

from openhands.core.logger import openhands_logger as logger

if TYPE_CHECKING:
    from openhands.runtime.base import Runtime


class FileOperationType(Enum):
    """Type of file operation in a transaction."""
    
    WRITE = "write"
    EDIT = "edit"
    DELETE = "delete"


@dataclass
class FileOperation:
    """Represents a single file operation in a transaction."""
    
    operation_type: FileOperationType
    file_path: str
    new_content: str | None = None
    old_content: str | None = None
    existed_before: bool = False


@dataclass
class FileTransaction:
    """Transaction manager for atomic file operations.
    
    Usage:
        async with FileTransaction(runtime) as txn:
            await txn.write_file("/workspace/file1.txt", "content1")
            await txn.write_file("/workspace/file2.txt", "content2")
            # If any operation fails, all changes are rolled back
    """
    
    runtime: Runtime
    operations: list[FileOperation] = field(default_factory=list)
    backup_dir: str | None = None
    committed: bool = False
    
    async def __aenter__(self) -> FileTransaction:
        """Enter transaction context."""
        # Create temporary backup directory
        self.backup_dir = tempfile.mkdtemp(prefix="forge_txn_")
        logger.info(f"Started file transaction with backup dir: {self.backup_dir}")
        return self
    
    async def __aexit__(self, exc_type, exc_value, traceback) -> None:
        """Exit transaction context, committing or rolling back."""
        if exc_type is not None:
            # Exception occurred - rollback all changes
            logger.error(f"File transaction failed: {exc_value}, rolling back {len(self.operations)} operations")
            await self.rollback()
        elif not self.committed:
            # No exception, but commit wasn't called explicitly - auto-commit
            logger.info(f"Auto-committing file transaction with {len(self.operations)} operations")
            self.committed = True
        
        # Cleanup backup directory
        if self.backup_dir and os.path.exists(self.backup_dir):
            try:
                shutil.rmtree(self.backup_dir)
                logger.debug(f"Cleaned up transaction backup dir: {self.backup_dir}")
            except Exception as e:
                logger.warning(f"Failed to cleanup transaction backup: {e}")
    
    async def write_file(self, file_path: str, content: str) -> None:
        """Write a file within the transaction.
        
        Args:
            file_path: Absolute path to the file
            content: File content to write
        """
        # Check if file exists and backup current content
        existed_before = os.path.exists(file_path)
        old_content = None
        
        if existed_before:
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    old_content = f.read()
                
                # Create backup
                if self.backup_dir:
                    backup_path = os.path.join(self.backup_dir, os.path.basename(file_path))
                    with open(backup_path, 'w', encoding='utf-8') as f:
                        f.write(old_content)
            except Exception as e:
                logger.warning(f"Failed to backup file {file_path}: {e}")
        
        # Record operation
        operation = FileOperation(
            operation_type=FileOperationType.WRITE,
            file_path=file_path,
            new_content=content,
            old_content=old_content,
            existed_before=existed_before,
        )
        self.operations.append(operation)
        
        # Execute write
        try:
            os.makedirs(os.path.dirname(file_path), exist_ok=True)
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)
            logger.debug(f"Wrote file in transaction: {file_path}")
        except Exception as e:
            logger.error(f"Failed to write file {file_path}: {e}")
            raise
    
    async def edit_file(self, file_path: str, new_content: str) -> None:
        """Edit an existing file within the transaction.
        
        Args:
            file_path: Absolute path to the file
            new_content: New file content
        """
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"Cannot edit non-existent file: {file_path}")
        
        # Backup current content
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                old_content = f.read()
            
            # Create backup
            if self.backup_dir:
                backup_path = os.path.join(self.backup_dir, os.path.basename(file_path))
                with open(backup_path, 'w', encoding='utf-8') as f:
                    f.write(old_content)
        except Exception as e:
            logger.error(f"Failed to backup file for edit {file_path}: {e}")
            raise
        
        # Record operation
        operation = FileOperation(
            operation_type=FileOperationType.EDIT,
            file_path=file_path,
            new_content=new_content,
            old_content=old_content,
            existed_before=True,
        )
        self.operations.append(operation)
        
        # Execute edit
        try:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(new_content)
            logger.debug(f"Edited file in transaction: {file_path}")
        except Exception as e:
            logger.error(f"Failed to edit file {file_path}: {e}")
            raise
    
    async def delete_file(self, file_path: str) -> None:
        """Delete a file within the transaction.
        
        Args:
            file_path: Absolute path to the file
        """
        if not os.path.exists(file_path):
            logger.warning(f"Cannot delete non-existent file: {file_path}")
            return
        
        # Backup current content before deletion
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                old_content = f.read()
            
            # Create backup
            if self.backup_dir:
                backup_path = os.path.join(self.backup_dir, os.path.basename(file_path))
                with open(backup_path, 'w', encoding='utf-8') as f:
                    f.write(old_content)
        except Exception as e:
            logger.warning(f"Failed to backup file for deletion {file_path}: {e}")
        
        # Record operation
        operation = FileOperation(
            operation_type=FileOperationType.DELETE,
            file_path=file_path,
            old_content=old_content,
            existed_before=True,
        )
        self.operations.append(operation)
        
        # Execute deletion
        try:
            os.remove(file_path)
            logger.debug(f"Deleted file in transaction: {file_path}")
        except Exception as e:
            logger.error(f"Failed to delete file {file_path}: {e}")
            raise
    
    async def commit(self) -> None:
        """Explicitly commit the transaction.
        
        This is optional - transactions auto-commit on success.
        """
        self.committed = True
        logger.info(f"Committed file transaction with {len(self.operations)} operations")
    
    async def rollback(self) -> None:
        """Rollback all file operations in reverse order."""
        logger.warning(f"Rolling back {len(self.operations)} file operations")
        
        # Rollback in reverse order (LIFO)
        for operation in reversed(self.operations):
            try:
                if operation.operation_type == FileOperationType.WRITE:
                    if operation.existed_before and operation.old_content is not None:
                        # Restore original content
                        with open(operation.file_path, 'w', encoding='utf-8') as f:
                            f.write(operation.old_content)
                        logger.debug(f"Restored original content: {operation.file_path}")
                    else:
                        # File didn't exist before - delete it
                        if os.path.exists(operation.file_path):
                            os.remove(operation.file_path)
                            logger.debug(f"Deleted newly created file: {operation.file_path}")
                
                elif operation.operation_type == FileOperationType.EDIT:
                    if operation.old_content is not None:
                        # Restore original content
                        with open(operation.file_path, 'w', encoding='utf-8') as f:
                            f.write(operation.old_content)
                        logger.debug(f"Restored edited file: {operation.file_path}")
                
                elif operation.operation_type == FileOperationType.DELETE:
                    if operation.old_content is not None:
                        # Restore deleted file
                        os.makedirs(os.path.dirname(operation.file_path), exist_ok=True)
                        with open(operation.file_path, 'w', encoding='utf-8') as f:
                            f.write(operation.old_content)
                        logger.debug(f"Restored deleted file: {operation.file_path}")
            
            except Exception as e:
                logger.error(f"Failed to rollback operation {operation.operation_type} on {operation.file_path}: {e}")
                # Continue rolling back other operations
        
        logger.info(f"Rollback completed for {len(self.operations)} operations")


# Example usage in agent code:
"""
async with FileTransaction(runtime) as txn:
    await txn.write_file("/workspace/Component.tsx", tsx_content)
    await txn.write_file("/workspace/Component.test.tsx", test_content)
    await txn.write_file("/workspace/Component.css", css_content)
    # If any write fails, all 3 files are rolled back
"""

