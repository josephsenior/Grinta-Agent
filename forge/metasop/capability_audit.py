"""Capability audit utilities for MetaSOP.

Scans role profiles and SOP templates to produce a report of:
  - steps_missing_capabilities: steps whose required_capabilities are not fully satisfied
  - unknown_capabilities: capability tokens referenced by steps but absent from any role profile
  - unused_capabilities: capabilities declared in profiles but never referenced as required
  - capability_usage: mapping capability -> count of steps requiring it

Assumptions:
  * SOP templates may include an 'extras' map or top-level per-step field `required_capabilities` (list of strings)
  * Role profiles loaded externally already contain `capabilities` list

Public API:
  audit_capabilities(profiles: dict[str, RoleProfile], sops_dir: Path) -> dict
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

import yaml

if TYPE_CHECKING:
    from pathlib import Path

    from .models import RoleProfile


def _extract_required_caps(step: dict) -> list[str]:
    caps = step.get("required_capabilities")
    if isinstance(caps, list):
        return [c for c in caps if isinstance(c, str)]
    extras = step.get("extras")
    if isinstance(extras, dict):
        ecaps = extras.get("required_capabilities")
        if isinstance(ecaps, list):
            return [c for c in ecaps if isinstance(c, str)]
    return []


def audit_capabilities(profiles: dict[str, RoleProfile], sops_dir: Path) -> dict[str, Any]:
    """Audit capabilities across role profiles and SOPs."""
    # Initialize audit state
    audit_state = _initialize_audit_state(profiles)

    # Process all SOP files
    _process_sop_files(sops_dir, profiles, audit_state)

    # Generate audit results
    return _generate_audit_results(audit_state, profiles, sops_dir)


def _initialize_audit_state(profiles: dict[str, RoleProfile]) -> dict:
    """Initialize the audit state with empty collections."""
    all_profile_caps = set()
    for rp in profiles.values():
        all_profile_caps.update(rp.capabilities)

    return {"steps_missing": [], "unknown_caps": set(), "capability_usage": {}, "all_profile_caps": all_profile_caps}


def _process_sop_files(sops_dir: Path, profiles: dict[str, RoleProfile], audit_state: dict) -> None:
    """Process all SOP files in the directory."""
    for sop_file in sops_dir.glob("*.yaml"):
        _process_single_sop_file(sop_file, profiles, audit_state)


def _process_single_sop_file(sop_file: Path, profiles: dict[str, RoleProfile], audit_state: dict) -> None:
    """Process a single SOP file."""
    try:
        with sop_file.open("r", encoding="utf-8") as fh:
            data = yaml.safe_load(fh)
    except Exception:
        return

    steps = (data or {}).get("steps") or []
    for step in steps:
        _process_single_step(step, data, profiles, audit_state)


def _process_single_step(step: dict, sop_data: dict, profiles: dict[str, RoleProfile], audit_state: dict) -> None:
    """Process a single step within a SOP."""
    if not isinstance(step, dict):
        return

    required = _extract_required_caps(step)
    if not required:
        return

    # Update capability usage and check for unknown capabilities
    _update_capability_usage(required, audit_state)

    # Check for missing capabilities
    _check_missing_capabilities(step, sop_data, required, profiles, audit_state)


def _update_capability_usage(required: list[str], audit_state: dict) -> None:
    """Update capability usage statistics and check for unknown capabilities."""
    for cap in required:
        audit_state["capability_usage"][cap] = audit_state["capability_usage"].get(cap, 0) + 1
        if cap not in audit_state["all_profile_caps"]:
            audit_state["unknown_caps"].add(cap)


def _check_missing_capabilities(
    step: dict,
    sop_data: dict,
    required: list[str],
    profiles: dict[str, RoleProfile],
    audit_state: dict,
) -> None:
    """Check for missing capabilities in the step's role."""
    role_field = step.get("role")
    if not isinstance(role_field, str):
        return
    role = role_field
    step_id = step.get("id")

    rp = profiles.get(role)
    role_caps = set(rp.capabilities) if rp else set()

    if missing := [c for c in required if c not in role_caps]:
        audit_state["steps_missing"].append(
            {"sop": sop_data.get("name"), "step_id": step_id, "role": role, "required": required, "missing": missing},
        )


def _generate_audit_results(audit_state: dict, profiles: dict[str, RoleProfile], sops_dir: Path) -> dict[str, Any]:
    """Generate the final audit results."""
    unused_caps = sorted([c for c in audit_state["all_profile_caps"] if c not in audit_state["capability_usage"]])

    return {
        "steps_missing_capabilities": audit_state["steps_missing"],
        "unknown_capabilities": sorted(audit_state["unknown_caps"]),
        "unused_capabilities": unused_caps,
        "capability_usage": audit_state["capability_usage"],
        "profiles_count": len(profiles),
        "sops_scanned": len(list(sops_dir.glob("*.yaml"))),
    }


__all__ = ["audit_capabilities"]
