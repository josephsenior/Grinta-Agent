"""Post-run verification helpers for MetaSOP step artifacts."""

from __future__ import annotations

from typing import Any

from .registry import load_schema, load_sop_template


def verify_run(sop_name: str, artifacts: dict[str, Any]) -> dict[str, Any]:
    """Post-run verification: ensure that for each step whose condition would pass, artifact present.

    NOTE: This re-loads the SOP; it does not re-evaluate dynamic conditions beyond presence of required keys.
    """
    template = load_sop_template(sop_name)
    report: dict[str, Any] = {"sop": sop_name, "steps": []}
    for step in template.steps:
        art = artifacts.get(step.id)
        step_entry: dict[str, Any] = {"id": step.id, "role": step.role}
        if art is None:
            step_entry["status"] = "missing"
        else:
            try:
                schema = load_schema(step.outputs.schema_file)
                missing: list[str] = []
                if isinstance(art.content, dict):
                    required_candidates = schema.get("required", [])
                    if isinstance(required_candidates, list):
                        missing.extend(
                            req for req in required_candidates if isinstance(req, str) and req not in art.content
                        )
                if missing:
                    step_entry["status"] = "incomplete"
                    step_entry["missing"] = missing
                else:
                    step_entry["status"] = "ok"
            except Exception as e:
                step_entry["status"] = "schema_load_error"
                step_entry["error"] = str(e)
        report["steps"].append(step_entry)
    return report
