from __future__ import annotations

"Retrieval augmentation helpers wrapping the MemoryIndex.\n\nIsolating this logic reduces branching inside the orchestrator and keeps\nmemory lookups / shaping consistent.\n"
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .memory import MemoryIndex


def shape_retrieval(memory_index: MemoryIndex | None, query: str, step_id: str, user_request: str, k: int = 3):
    if not memory_index or memory_index.stats().get("records", 0) == 0:
        return None
    try:
        hits = memory_index.search(f"{query}\n{user_request}"[:500], k=k)
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
    except Exception:
        return None
