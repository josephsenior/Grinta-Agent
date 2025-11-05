"""Context hashing utilities for MetaSOP.

Produces a deterministic hash summarizing the effective context of a step
attempt so that identical contexts can be recognized (enabling future
caching, replay fidelity checks, and drift analysis).

Context material includes (when available & enabled):
  - Step id, role
  - Retrieval hits (id, score, truncated excerpt)
  - Prior artifact hashes + type labels
  - Role capability list (sorted)
  - Environment signature (if present in orchestration context extras)
  - Optional model & executor strategy identifiers

Truncation is applied to large textual fields to keep hash input bounded.
"""

from __future__ import annotations

import hashlib
import json
from typing import Any


def _stable(obj: Any) -> Any:
    if isinstance(obj, dict):
        return {k: _stable(obj[k]) for k in sorted(obj)}
    return [_stable(i) for i in obj] if isinstance(obj, (list, tuple)) else obj


def _stable_json(data: Any) -> str:
    return json.dumps(_stable(data), separators=(",", ":"), ensure_ascii=False)


def compute_context_hash(
    *,
    step_id: str,
    role: str,
    retrieval_hits: list[dict[str, Any]] | None,
    prior_artifacts: list[dict[str, Any]] | None,
    role_capabilities: list[str] | None,
    env_signature: Any | None,
    model_name: str | None,
    executor_name: str | None,
    truncate_bytes: int = 4096,
) -> str:
    """Compute a stable hash for execution context.

    Args:
        step_id: Step identifier
        role: Role name
        retrieval_hits: Retrieved context items
        prior_artifacts: Previous artifacts
        role_capabilities: List of capabilities
        env_signature: Environment signature
        model_name: Model name
        executor_name: Executor name
        truncate_bytes: Max bytes for truncation

    Returns:
        SHA256 hash of context
    """

    def trunc(s: str | None) -> str | None:
        if s is None:
            return None
        return s[:truncate_bytes] if truncate_bytes and len(s) > truncate_bytes else s

    retrieval_serialized = _serialize_retrieval_hits(retrieval_hits or [], trunc)
    artifacts_serialized = _serialize_artifacts(prior_artifacts or [])

    payload = {
        "v": 1,
        "step": {"id": step_id, "role": role},
        "retrieval": retrieval_serialized,
        "prior_artifacts": artifacts_serialized,
        "capabilities": sorted(role_capabilities or []),
        "env_signature": env_signature or None,
        "model": model_name,
        "executor": executor_name,
    }
    encoded = _stable_json(payload).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _serialize_retrieval_hits(hits: list[dict[str, Any]], trunc_fn) -> list[dict]:
    """Serialize retrieval hits for hashing.

    Args:
        hits: List of retrieval hits
        trunc_fn: Truncation function

    Returns:
        Serialized hits
    """
    return [
        {
            "id": h.get("step_id") or h.get("id"),
            "score": h.get("score"),
            "excerpt": trunc_fn(h.get("excerpt") or h.get("rationale") or h.get("content") or ""),
        }
        for h in hits
    ]


def _serialize_artifacts(artifacts: list[dict[str, Any]]) -> list[dict]:
    """Serialize artifacts for hashing.

    Args:
        artifacts: List of artifacts

    Returns:
        Serialized artifacts
    """
    return [
        {
            "step_id": a.get("step_id"),
            "artifact_hash": a.get("artifact_hash") or a.get("hash"),
            "role": a.get("role"),
            "kind": a.get("kind"),
        }
        for a in artifacts
    ]


__all__ = ["compute_context_hash"]
