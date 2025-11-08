"""Replay harness for MetaSOP run manifests.

This module provides utilities to:
  * Load a previously exported run manifest (see MetaSOPOrchestrator.export_run_manifest)
  * Reconstruct key invariants (ordering, step hashes, artifact hashes, statuses)
  * Optionally assert deterministic fidelity (no diff) – useful for CI regression checks

Design goals:
  * Be side-effect free (read-only) – does not execute steps, only validates structure
  * Provide a concise diff summary for human review
  * Avoid raising on minor schema expansions: ignore unknown top-level keys

Public entry point:
  replay_manifest(manifest_path: str, assert_mode: bool = False) -> dict
    Returns a dict with keys:
      manifest_path, ok (bool), diffs (list[str]), summary (dict)
    If assert_mode and diffs exist: ok will be False.

Determinism Model (v1):
  We currently check:
    - Presence & order of steps (step_id sequence)
    - Monotonic provenance chain (first == steps[0].step_hash; final == steps[-1].step_hash)
    - Uniqueness of step_hash values
    - If attempts metadata present: attempt indices strictly increasing starting at 0
    - Optional: If verification_result exists ensure it has status

  Future extensions (not yet implemented):
    - Cross-validate artifact_hash content against a persisted artifact store
    - Time budget & latency envelope comparisons
    - Percentile drift thresholds
"""

from __future__ import annotations

import json
from pathlib import Path
from collections import Counter
from collections.abc import Sequence
from typing import Any, cast


class ReplayError(Exception):
    """Raised for hard replay failures (e.g., unreadable file)."""


def _load_manifest(path: str) -> dict[str, Any]:
    p = Path(path)
    if not p.exists():
        msg = f"manifest not found: {path}"
        raise ReplayError(msg)
    try:
        with p.open("r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        msg = f"failed to load manifest: {e}"
        raise ReplayError(msg) from e


def _diff_sequence(label: str, observed: Sequence[str | None]) -> list[str]:
    diffs: list[str] = []
    if not observed:
        diffs.append(f"{label}: empty sequence")
        return diffs

    non_str = [item for item in observed if not isinstance(item, str)]
    if non_str:
        diffs.append(
            f"{label}: non-string entries detected: {sorted({str(item) for item in non_str})}",
        )

    string_entries = [cast(str, item) for item in observed if isinstance(item, str)]
    counts = Counter(string_entries)
    duplicates = sorted({entry for entry, count in counts.items() if count > 1})
    if duplicates:
        diffs.append(f"{label}: duplicate entries detected: {duplicates}")
    return diffs


def _validate_attempts(step: dict[str, Any]) -> list[str]:
    diffs: list[str] = []
    attempts = step.get("attempts") or []
    if not attempts:
        return diffs
    indices = [a.get("attempt_index") for a in attempts if a is not None]
    if any(i is None for i in indices):
        diffs.append(f"step {step.get('step_id')}: missing attempt_index in attempts")
        return diffs
    for expected, actual in enumerate(indices):
        if actual != expected:
            diffs.append(
                f"step {
                    step.get('step_id')}: attempt_index sequence mismatch expected {expected} got {actual}",
            )
            break
    return diffs


def _validate_step_sequence(steps: list[dict[str, Any]]) -> list[str]:
    """Validate step sequence and return any differences found."""
    step_ids: list[str | None] = [s.get("step_id") for s in steps]
    return _diff_sequence("steps.step_id", step_ids)


def _validate_provenance_chain(steps: list[dict[str, Any]], prov: dict[str, Any]) -> list[str]:
    """Validate provenance chain consistency."""
    diffs: list[str] = []
    chain_root = prov.get("chain_root")
    final_hash = prov.get("final_step_hash")

    if not steps:
        return diffs

    first_hash = steps[0].get("step_hash")
    last_hash = steps[-1].get("step_hash")

    if chain_root and first_hash and (chain_root != first_hash):
        diffs.append(f"provenance.chain_root mismatch: manifest={chain_root} first_step={first_hash}")

    if final_hash and last_hash and (final_hash != last_hash):
        diffs.append(f"provenance.final_step_hash mismatch: manifest={final_hash} last_step={last_hash}")

    return diffs


def _validate_step_hash_uniqueness(steps: list[dict[str, Any]]) -> list[str]:
    """Validate that step hashes are unique."""
    diffs: list[str] = []
    hashes = [s.get("step_hash") for s in steps if s.get("step_hash")]

    if len(hashes) != len(set(hashes)):
        dupes = [h for h in hashes if hashes.count(h) > 1]
        diffs.append(f"duplicate step_hash values: {sorted({str(h) for h in dupes})}")

    return diffs


def _validate_step_details(steps: list[dict[str, Any]]) -> list[str]:
    """Validate individual step details."""
    diffs: list[str] = []

    for s in steps:
        # Validate attempts
        diffs.extend(_validate_attempts(s))

        # Validate verification result
        vr = s.get("verification_result")
        if vr and (not vr.get("status")):
            diffs.append(f"step {s.get('step_id')}: verification_result missing status")

    return diffs


def _build_validation_summary(steps: list[dict[str, Any]], diffs: list[str], prov: dict[str, Any]) -> dict[str, Any]:
    """Build validation summary."""
    return {
        "steps": len(steps),
        "diff_count": len(diffs),
        "chain_root": prov.get("chain_root"),
        "final_step_hash": prov.get("final_step_hash"),
    }


def _determine_validation_result(diffs: list[str], assert_mode: bool) -> bool:
    """Determine if validation passed."""
    ok = not diffs
    if assert_mode and not ok:
        ok = False
    return ok


def replay_manifest(manifest_path: str, assert_mode: bool = False) -> dict[str, Any]:
    """Replay and validate a manifest file.

    Args:
        manifest_path: Path to the manifest file to validate
        assert_mode: If True, validation will fail if any differences are found

    Returns:
        Dictionary containing validation results, differences, and summary

    """
    # Load manifest
    manifest = _load_manifest(manifest_path)
    diffs: list[str] = []

    # Extract steps and provenance
    steps: list[dict[str, Any]] = manifest.get("steps") or []
    prov = manifest.get("provenance") or {}

    # Validate various aspects
    diffs.extend(_validate_step_sequence(steps))
    diffs.extend(_validate_provenance_chain(steps, prov))
    diffs.extend(_validate_step_hash_uniqueness(steps))
    diffs.extend(_validate_step_details(steps))

    # Build results
    summary = _build_validation_summary(steps, diffs, prov)
    ok = _determine_validation_result(diffs, assert_mode)

    return {"manifest_path": manifest_path, "ok": ok, "diffs": diffs, "summary": summary}


__all__ = ["ReplayError", "replay_manifest"]
