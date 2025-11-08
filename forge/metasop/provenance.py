"""Provenance hashing utilities for MetaSOP artifacts and steps."""

from __future__ import annotations
import hashlib
import json
from typing import Any


def _hash_serializable(data: Any) -> str:
    """Compute SHA256 hash of serializable data with JSON fallback.
    
    Attempts to serialize data to JSON with sorted keys for deterministic hashing.
    Falls back to repr() if JSON serialization fails (for non-JSON-serializable objects).
    
    Args:
        data: Any Python object to be hashed (typically dict, list, or primitives)
    
    Returns:
        Hexadecimal SHA256 hash string (64 characters)
    
    Notes:
        - JSON serialization uses canonical form: sorted keys, compact separators
        - Ensures identical data produces identical hashes (deterministic)
        - repr() fallback handles complex objects but may vary between Python versions
        - Used for artifact and step provenance tracking in MetaSOP
    
    Example:
        >>> _hash_serializable({"b": 2, "a": 1})
        '...'  # Same as _hash_serializable({"a": 1, "b": 2})

    """
    try:
        encoded = json.dumps(data, sort_keys=True, separators=(",", ":")).encode("utf-8")
    except Exception:
        encoded = repr(data).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def compute_artifact_hash(step_id: str, role: str, content) -> str:
    """Compute SHA256 hash of an artifact for provenance tracking.
    
    Creates a stable hash that uniquely identifies an artifact by combining:
    - step_id: The orchestration step that produced it
    - role: The agent role that created it (e.g., 'user', 'assistant')
    - content: The artifact data/payload
    
    Args:
        step_id: Unique identifier of the orchestration step
        role: Role identifier for the artifact creator
        content: Artifact data (any serializable type)
    
    Returns:
        Hexadecimal SHA256 hash string
    
    Notes:
        - Deterministic: Same inputs produce same hash
        - Used to track artifact lineage and detect duplicate work
        - Combines step context with role and content for full artifact identity
        - Hash changes if any component (step, role, or content) changes
    
    Example:
        >>> hash1 = compute_artifact_hash("step_1", "assistant", "solution code")
        >>> hash2 = compute_artifact_hash("step_1", "assistant", "solution code")
        >>> hash1 == hash2
        True

    """
    base = {"step_id": step_id, "role": role, "content": content}
    return _hash_serializable(base)


def compute_step_hash(previous_step_hash: str | None, artifact_hash: str | None, rationale: str | None) -> str:
    """Compute SHA256 hash of a step in the orchestration DAG.
    
    Creates a stable hash that chains step execution context by including:
    - previous_step_hash: Hash of preceding step (for chain verification)
    - artifact_hash: Hash of the primary artifact produced
    - rationale: Step execution reason or decision rationale
    
    Args:
        previous_step_hash: SHA256 hash of the previous step (None for root step)
        artifact_hash: SHA256 hash of the step's primary artifact (None if no artifact)
        rationale: Text explanation of why this step was taken (None if not available)
    
    Returns:
        Hexadecimal SHA256 hash string
    
    Notes:
        - Deterministic: Same inputs produce same hash (chain verification)
        - Enables detecting step sequence replays or modifications
        - None values supported for missing context (root steps, no artifacts)
        - Chain: hash(step_n) includes hash(step_n-1), creating cryptographic chain
        - Used for MetaSOP execution trail verification and replay detection
    
    Example:
        >>> hash0 = compute_step_hash(None, None, "initialize")
        >>> hash1 = compute_step_hash(hash0, "artifact123", "execute task")
        >>> hash2 = compute_step_hash(hash1, "artifact456", "verify result")
        >>> # hash2 incorporates hash1, which incorporates hash0 (chain)

    """
    material = {"prev": previous_step_hash, "artifact_hash": artifact_hash, "rationale": rationale}
    return _hash_serializable(material)
