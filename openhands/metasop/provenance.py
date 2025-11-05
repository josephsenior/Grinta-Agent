from __future__ import annotations

"Provenance hashing utilities for MetaSOP artifacts and steps."
import hashlib
import json
from typing import Any


def _hash_serializable(data: Any) -> str:
    try:
        encoded = json.dumps(data, sort_keys=True, separators=(",", ":")).encode("utf-8")
    except Exception:
        encoded = repr(data).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def compute_artifact_hash(step_id: str, role: str, content) -> str:
    base = {"step_id": step_id, "role": role, "content": content}
    return _hash_serializable(base)


def compute_step_hash(previous_step_hash: str | None, artifact_hash: str | None, rationale: str | None) -> str:
    material = {"prev": previous_step_hash, "artifact_hash": artifact_hash, "rationale": rationale}
    return _hash_serializable(material)
