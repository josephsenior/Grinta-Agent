from __future__ import annotations

import json
from pathlib import Path

import yaml

from .discovery import SOPNotFoundError, list_sop_templates, suggest_similar
from .models import RoleProfile, SopTemplate

BASE_DIR = Path(__file__).parent
PROFILES_DIR = BASE_DIR / "profiles"
SOPS_DIR = BASE_DIR / "sops"
SCHEMAS_DIR = BASE_DIR / "templates" / "schemas"


def _infer_capabilities_from_goal(goal: str) -> list[str]:
    """Infer capabilities from role goal text.

    Args:
        goal: Role goal text

    Returns:
        List of inferred capabilities
    """
    goal_lower = goal.lower()

    capability_keywords = [
        (["design", "ui"], "design_ui"),
        (["test", "qa"], "run_tests"),
        (["implement", "code", "engineer"], "write_code"),
        (["plan", "spec", "product"], "write_spec"),
    ]

    return [capability for keywords, capability in capability_keywords if any(kw in goal_lower for kw in keywords)]


def _load_profile_from_file(filepath: Path) -> RoleProfile:
    """Load a single role profile from YAML file."""
    with filepath.open("r", encoding="utf-8") as fh:
        data = yaml.safe_load(fh)

    # Infer capabilities if not specified
    if data.get("capabilities") is None:
        goal = data.get("goal") or ""
        if inferred := _infer_capabilities_from_goal(goal):
            data["capabilities"] = inferred

    return RoleProfile(**data)


def load_role_profiles() -> dict[str, RoleProfile]:
    profiles: dict[str, RoleProfile] = {}
    if PROFILES_DIR.exists():
        for f in PROFILES_DIR.glob("*.yaml"):
            profile = _load_profile_from_file(f)
            profiles[profile.name] = profile
    return profiles


def load_sop_template(name: str) -> SopTemplate:
    path = SOPS_DIR / f"{name}.yaml"
    if not path.exists():
        available = [t.name for t in list_sop_templates()]
        suggestions = suggest_similar(name, available)
        raise SOPNotFoundError(name, available, suggestions)
    with path.open("r", encoding="utf-8") as fh:
        data = yaml.safe_load(fh)
    return SopTemplate(**data)


def load_schema(schema_name: str) -> dict:
    path = SCHEMAS_DIR / schema_name
    if not path.exists():
        msg = f"Schema not found: {path}"
        raise FileNotFoundError(msg)
    with path.open("r", encoding="utf-8") as fh:
        return json.load(fh)
