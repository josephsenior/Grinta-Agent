"""Inspect MetaSOP templates using supported orchestration APIs.

The script prints:
 - Available role profiles
 - Each template step, its dependencies, and required capabilities
 - Capability matrix evaluation
 - Dependency + condition evaluation (via OrchestrationContextManager)
"""

from __future__ import annotations

import logging
from typing import Any

from forge.core.config.utils import load_FORGE_config
from forge.metasop.models import Artifact, SopStep
from forge.metasop.orchestrator import MetaSOPOrchestrator

logger = logging.getLogger(__name__)


def _require_template(orch: MetaSOPOrchestrator) -> list[SopStep]:
    template = getattr(orch, "template", None)
    if template is None or not getattr(template, "steps", None):
        raise RuntimeError("MetaSOP template is not available.")
    return list(template.steps)


def _required_capabilities(step: SopStep) -> list[str]:
    caps: list[str] = []
    extras: Any = getattr(step, "extras", None)
    if isinstance(extras, dict):
        value = extras.get("required_capabilities")
        if isinstance(value, list):
            caps = [str(v) for v in value]
    rc = getattr(step, "required_capabilities", None)
    if isinstance(rc, list):
        caps.extend(str(v) for v in rc)
    return caps


def _describe_step(orch: MetaSOPOrchestrator, step: SopStep) -> None:
    done: dict[str, Artifact] = {}
    profiles = orch.profile_manager.get_profiles()
    capability_ok = orch.profile_manager.check_capability_matrix(step, done)

    context_mgr = orch.context_manager
    deps_method = getattr(context_mgr, "_deps_satisfied", None)
    cond_method = getattr(context_mgr, "_evaluate_condition", None)

    deps_details = None
    if callable(deps_method):
        try:
            deps_details = deps_method(done, step)
        except Exception:  # pragma: no cover - diagnostic
            deps_details = None

    cond_details = None
    if callable(cond_method):
        try:
            cond_details = cond_method(done, step)
        except Exception:  # pragma: no cover - diagnostic
            cond_details = None

    deps_and_cond_ok = context_mgr.check_dependencies_and_conditions(step, done)

    logger.info("id: %s", step.id)
    logger.info("role: %s", step.role)
    logger.info("depends_on: %s", getattr(step, "depends_on", None))
    logger.info("required_capabilities: %s", _required_capabilities(step))
    logger.info("capability_ok: %s", capability_ok)
    logger.info("deps_ok (raw): %s", deps_details)
    if cond_details is not None:
        cond_ok, cond_warn, parse_err = cond_details
        logger.info(
            "condition -> ok=%s warn=%s parse_err=%s",
            cond_ok,
            cond_warn,
            parse_err,
        )
    logger.info("deps_and_conditions_ok: %s", deps_and_cond_ok)
    logger.info("role_profile_present: %s", step.role in profiles)
    logger.info("---")


def main() -> None:
    logging.basicConfig(level=logging.INFO)
    cfg = load_FORGE_config(set_logging_levels=False)
    orch = MetaSOPOrchestrator(sop_name="feature_delivery_with_ui", config=cfg)

    profiles = orch.profile_manager.get_profiles()
    logger.info("Loaded role profiles (%d): %s", len(profiles), list(profiles))

    steps = _require_template(orch)
    logger.info("Template contains %d steps", len(steps))
    for step in steps:
        _describe_step(orch, step)


if __name__ == "__main__":
    main()
