"""File editor module - Production implementation.

Provides file editing capabilities using the production-grade FileEditor.
"""

from forge.runtime.utils.file_editor import FileEditor

# Create a singleton instance for backward compatibility
_file_editor_instance = FileEditor()


def file_editor(*args, **kwargs):
    """File editor function interface (backward compatibility).

    This function provides a callable interface to the FileEditor singleton.
    """
    return _file_editor_instance(*args, **kwargs)


__all__ = ["file_editor", "FileEditor"]
