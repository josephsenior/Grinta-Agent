"""Debug helper: inspect SOP template and per-step gating logic.

Prints: template step order, role profiles loaded, and for each step:
 - depends_on
 - required_capabilities (if present in extras)
 - deps_satisfied with empty done
 - _evaluate_condition result
 - whether a role_profile exists
"""

import logging
from openhands.core.config.utils import load_openhands_config
from openhands.metasop.orchestrator import MetaSOPOrchestrator

logger = logging.getLogger(__name__)


def main():
    cfg = load_openhands_config(set_logging_levels=False)
    orch = MetaSOPOrchestrator(sop_name="feature_delivery_with_ui", config=cfg)
    logger.info("Loaded role profiles:")
    logger.info("%s", list(orch.profiles.keys()))
    logger.info("\nTemplate steps:")
    for s in orch.template.steps:
        logger.info("---")
        logger.info("id: %s", s.id)
        logger.info("role: %s", s.role)
        logger.info("depends_on: %s", getattr(s, "depends_on", None))
        rc = None
        try:
            rc = getattr(s, "required_capabilities", None)
        except Exception:
            rc = None
    logger.info("required_capabilities: %s", rc)
    logger.info("deps_satisfied(empty done): %s", orch._deps_satisfied({}, s))
    cond_ok, cond_warn, parse_err = orch._evaluate_condition({}, s)
    logger.info("condition -> ok: %s warn: %s parse_err: %s", cond_ok, cond_warn, parse_err)
    logger.info("role_profile_present: %s", s.role in orch.profiles)


if __name__ == "__main__":
    main()
