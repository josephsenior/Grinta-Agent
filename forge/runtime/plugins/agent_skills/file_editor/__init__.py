"""This file imports a global singleton of the `EditTool` class as well as raw functions that expose.

its __call__.

The implementation of the `EditTool` class can be found at: https://github.com/All-Hands-AI/Forge-aci/.
"""

try:
    from forge_aci.editor import file_editor  # type: ignore[import-not-found]

    __all__ = ["file_editor"]
except ImportError:
    # forge_aci not installed - provide stub for testing
    class FileEditorStub:
        """Stub file editor for when forge_aci is not installed."""

        def __call__(self, *args, **kwargs):
            """Simulate edit invocation and report that forge_aci is unavailable."""
            return {"success": False, "error": "forge_aci not installed"}

    file_editor = FileEditorStub()
    __all__ = ["file_editor"]
