"""Validation helpers for MetaSOP manifests & templates."""

from __future__ import annotations

import json
from pathlib import Path

from jsonschema import Draft7Validator

from .discovery import SOPNotFoundError
from .registry import load_sop_template

_MANIFEST_SCHEMA = None


def _load_manifest_schema():
    """Load the manifest schema from the schemas directory.

    Returns:
        dict: The loaded JSON schema for manifest validation.

    """
    global _MANIFEST_SCHEMA
    if _MANIFEST_SCHEMA is None:
        schema_path = Path(__file__).parent / "schemas" / "manifest_v1.json"
        _MANIFEST_SCHEMA = json.loads(schema_path.read_text(encoding="utf-8"))
    return _MANIFEST_SCHEMA


def validate_manifest_file(path: str) -> tuple[bool, list[str]]:
    """Validate a manifest JSON file against the v1 schema.

    Returns (ok, errors). Errors is a list of human-friendly messages.
    """
    p = Path(path)
    if not p.exists():
        return (False, [f"File not found: {path}"])
    try:
        data = json.loads(p.read_text(encoding="utf-8"))
    except Exception as e:
        return (False, [f"Invalid JSON: {e}"])
    schema = _load_manifest_schema()
    validator = Draft7Validator(schema)
    validation_errors = sorted(validator.iter_errors(data), key=lambda err: err.path)
    if validation_errors:
        msgs = []
        for err in validation_errors:
            loc = ".".join(str(x) for x in err.path) or "<root>"
            msgs.append(f"{loc}: {err.message}")
        return (False, msgs)
    try:
        mh = data.get("manifest_hash")
        tmp = dict(data)
        tmp.pop("manifest_hash", None)
        recomputed = (
            __import__("hashlib")
            .sha256(json.dumps(tmp, sort_keys=True, separators=(",", ":")).encode("utf-8"))
            .hexdigest()
        )
        if mh and mh != recomputed:
            return (False, [f"Manifest hash mismatch: stored={mh} recomputed={recomputed}"])
    except Exception:
        pass
    return (True, [])


def _validate_step(step, ids: list[str]) -> list[str]:
    """Validate a single step and return errors."""
    errors = []
    sid = step.get("id") if isinstance(step, dict) else None

    if not sid:
        errors.append("step missing id")
    else:
        if sid in ids:
            errors.append(f"duplicate step id: {sid}")
        ids.append(sid)

    if not step.get("role"):
        errors.append(f"step {sid or '?'} missing role")

    return errors


def _validate_yaml_template(path: Path) -> tuple[bool, list[str]]:
    """Validate YAML template structure."""
    import yaml

    raw = yaml.safe_load(path.read_text(encoding="utf-8"))
    steps = raw.get("steps") if isinstance(raw, dict) else None

    if not isinstance(steps, list):
        return (False, ["Missing or invalid 'steps' list"])

    ids: list[str] = []
    errors: list[str] = []
    for step in steps:
        step_errors = _validate_step(step, ids)
        errors.extend(step_errors)

    return (False, errors) if errors else (True, [])


def validate_template_file(path: str) -> tuple[bool, list[str]]:
    """Basic structural validation of a SOP template file.

    Uses existing loader + meta checks from orchestrator's pattern. Does not execute steps.
    """
    p = Path(path)
    if not p.exists():
        return (False, [f"File not found: {path}"])

    try:
        if p.is_file() and p.name.endswith(".yaml"):
            return _validate_yaml_template(p)
        load_sop_template(path)
        return (True, [])
    except SOPNotFoundError as e:
        return (False, [str(e)])
    except Exception as e:
        return (False, [f"Template validation error: {e}"])


__all__ = ["validate_manifest_file", "validate_template_file"]
