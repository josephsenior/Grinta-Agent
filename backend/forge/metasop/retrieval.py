"""Retrieval augmentation helpers wrapping MetaSOP's MemoryIndex."""

from __future__ import annotations
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from .memory import MemoryIndex


def shape_retrieval(response: dict[str, Any]) -> list[dict[str, Any]] | None:
    """Normalize retrieval response payload into consistent schema."""
    hits = response.get("hits") or []
    shaped = [
        {
            "step_id": h.get("step_id"),
            "role": h.get("role"),
            "score": h.get("score"),
            "rationale": (h.get("rationale") or "")[:300],
            "excerpt": (h.get("excerpt") or "")[:400],
        }
        for h in hits
    ]
    return shaped or None
