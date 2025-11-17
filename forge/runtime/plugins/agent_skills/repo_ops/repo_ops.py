"""Repository exploration agent skills with optional forge_aci integrations."""

try:
    from forge_aci.indexing.locagent.tools import (  # type: ignore[import-not-found]
        explore_tree_structure,
        get_entity_contents,
        search_code_snippets,
    )
except ImportError:
    # Stubs for when forge_aci is not installed
    def explore_tree_structure(*args, **kwargs):
        """Fallback stub when optional forge_aci dependency is missing."""
        return {"error": "forge_aci not installed"}

    def get_entity_contents(*args, **kwargs):
        """Fallback stub when optional forge_aci dependency is missing."""
        return {"error": "forge_aci not installed"}

    def search_code_snippets(*args, **kwargs):
        """Fallback stub when optional forge_aci dependency is missing."""
        return {"error": "forge_aci not installed"}


__all__ = ["explore_tree_structure", "get_entity_contents", "search_code_snippets"]
