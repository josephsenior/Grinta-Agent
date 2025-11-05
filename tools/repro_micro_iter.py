import json
import logging
import types
from openhands.metasop.models import SopStep, SopTemplate, StepOutputSpec
from openhands.metasop.orchestrator import MetaSOPOrchestrator


class RotatingExecutor:

    def __init__(self):
        self.calls = 0

    def execute(self, step, ctx, role_profile, config=None):
        ctx.extra.get(f"micro_prev_artifact::{step.id}")
        variants = ["func a()\nprint('A')", "func b()\nprint('B B B B')", "func c()\nprint('C')"]
        content_variant = variants[self.calls % len(variants)]
        ctx.extra["last_variant"] = content_variant
        self.calls += 1
        return types.SimpleNamespace(
            ok=True,
            artifact=types.SimpleNamespace(step_id=step.id, role=step.role, content={"content": content_variant}),
            trace=types.SimpleNamespace(total_tokens=0, model_name="dummy"),
        )


def main():
    cfg = types.SimpleNamespace(extended=types.SimpleNamespace(metasop={}), runtime=types.SimpleNamespace())
    orch = MetaSOPOrchestrator(sop_name="feature_delivery", config=cfg)
    orch.template = SopTemplate(
        name="feature_delivery",
        steps=[SopStep(id="impl", role="engineer", task="impl task", outputs=StepOutputSpec(schema_file="dummy.json"))],
    )
    settings = orch.settings
    settings.metrics_prometheus_port = None
    settings.enabled = True
    settings.enable_micro_iterations = True
    settings.micro_iteration_max_loops = 3
    settings.micro_iteration_no_change_limit = 2
    settings.patch_scoring_enable = True
    settings.micro_iteration_candidate_count = 3
    orch.step_executor = RotatingExecutor()
    orch.profiles["engineer"] = types.SimpleNamespace(model_dump=lambda: {}, capabilities=["implement"])
    logger = logging.getLogger(__name__)
    try:
        success, done = orch.run(user_request="repro")
        logger.info("SUCCESS: %s", success)
    except Exception as e:
        logger.exception("RUN ERROR: %s", e)
    logger.info("\n--- Invalid events captured by emitter.invalid_events ---")
    try:
        inv = getattr(orch._emitter, "invalid_events", None)
        try:
            from openhands.core.io import print_json_stdout
        except Exception:
            try:
                logger.info(json.dumps(inv, default=str, indent=2, ensure_ascii=False))
            except Exception:
                logger.info(repr(inv))
        else:
            try:
                print_json_stdout(inv, pretty=True)
            except Exception:
                logger.info(json.dumps(inv, default=str, indent=2, ensure_ascii=False))
    except Exception as e:
        logger.exception("Could not print invalid_events: %s", e)
    logger.info("\n--- Emitted step events ---")
    try:
        try:
            from openhands.core.io import print_json_stdout
        except Exception:
            try:
                logger.info(json.dumps(orch.step_events, default=str, indent=2, ensure_ascii=False))
            except Exception:
                logger.info(repr(orch.step_events))
        else:
            try:
                print_json_stdout(orch.step_events, pretty=True)
            except Exception:
                logger.info(json.dumps(orch.step_events, default=str, indent=2, ensure_ascii=False))
    except Exception as e:
        logger.exception("Could not print step_events: %s", e)


if __name__ == "__main__":
    main()
