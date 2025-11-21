from __future__ import annotations

import json
import logging
import types
from typing import Any, TYPE_CHECKING, cast

from forge.metasop.models import (
    Artifact,
    RoleProfile,
    SopStep,
    SopTemplate,
    StepOutputSpec,
    StepResult,
    StepTrace,
)
from forge.metasop.orchestrator import MetaSOPOrchestrator
from forge.metasop.strategies import BaseStepExecutor

if TYPE_CHECKING:
    from forge.core.config import ForgeConfig


class RotatingExecutor(BaseStepExecutor):
    def __init__(self) -> None:
        self.calls = 0

    def execute(
        self,
        step: SopStep,
        ctx: Any,
        role_profile: dict[str, Any],
        config: "ForgeConfig | None" = None,
    ) -> StepResult:
        ctx.extra.get(f"micro_prev_artifact::{step.id}")
        content_variant = self._select_variant(ctx)
        artifact = Artifact(
            step_id=step.id, role=step.role, content={"content": content_variant}
        )
        trace = StepTrace(
            step_id=step.id, role=step.role, total_tokens=0, model_name="dummy"
        )
        return StepResult(ok=True, artifact=artifact, trace=trace)

    def _select_variant(self, ctx: Any) -> str:
        variants = [
            "func a()\nprint('A')",
            "func b()\nprint('B B B B')",
            "func c()\nprint('C')",
        ]
        content_variant = variants[self.calls % len(variants)]
        ctx.extra["last_variant"] = content_variant
        self.calls += 1
        return content_variant


def main() -> None:
    logger = logging.getLogger(__name__)
    orch = _build_orchestrator()
    _run_orchestrator(orch, logger)
    logger.info("\n--- Invalid events captured by emitter.invalid_events ---")
    _log_invalid_events(orch, logger)
    logger.info("\n--- Emitted step events ---")
    _log_step_events(orch, logger)


def _build_orchestrator() -> MetaSOPOrchestrator:
    cfg: Any = types.SimpleNamespace(
        extended=types.SimpleNamespace(metasop={}), runtime=types.SimpleNamespace()
    )
    orch = MetaSOPOrchestrator(
        sop_name="feature_delivery", config=cast("ForgeConfig | None", cfg)
    )
    orch.template = SopTemplate(
        name="feature_delivery",
        steps=[
            SopStep(
                id="impl",
                role="engineer",
                task="impl task",
                outputs=StepOutputSpec(schema="dummy.json"),
            )
        ],
    )
    _configure_settings(orch)
    orch.step_executor = RotatingExecutor()
    if orch.profiles is None:
        orch.profiles = {}
    orch.profiles["engineer"] = RoleProfile(
        name="engineer",
        goal="Implement micro iteration candidate",
        capabilities=["implement"],
    )
    return orch


def _configure_settings(orch: MetaSOPOrchestrator) -> None:
    settings = orch.settings
    settings.metrics_prometheus_port = None
    settings.enabled = True
    settings.enable_micro_iterations = True
    settings.micro_iteration_max_loops = 3
    settings.micro_iteration_no_change_limit = 2
    settings.patch_scoring_enable = True
    settings.micro_iteration_candidate_count = 3


def _run_orchestrator(orch: MetaSOPOrchestrator, logger: logging.Logger) -> None:
    try:
        success, _ = orch.run(user_request="repro")
        logger.info("SUCCESS: %s", success)
    except Exception as exc:  # pragma: no cover - diagnostic tool
        logger.exception("RUN ERROR: %s", exc)


def _log_invalid_events(orch: MetaSOPOrchestrator, logger: logging.Logger) -> None:
    try:
        invalid_events = getattr(orch._emitter, "invalid_events", None)
        _print_json_with_fallback(invalid_events, logger)
    except Exception as exc:  # pragma: no cover - diagnostic tool
        logger.exception("Could not print invalid_events: %s", exc)


def _log_step_events(orch: MetaSOPOrchestrator, logger: logging.Logger) -> None:
    try:
        _print_json_with_fallback(orch.step_events, logger)
    except Exception as exc:  # pragma: no cover - diagnostic tool
        logger.exception("Could not print step_events: %s", exc)


def _print_json_with_fallback(data: Any, logger: logging.Logger) -> None:
    try:
        from forge.core.io import print_json_stdout
    except Exception:
        _log_json(data, logger)
        return

    try:
        print_json_stdout(data, pretty=True)
    except Exception:
        _log_json(data, logger)


def _log_json(data: Any, logger: logging.Logger) -> None:
    try:
        logger.info(json.dumps(data, default=str, indent=2, ensure_ascii=False))
    except Exception:
        logger.info(repr(data))


if __name__ == "__main__":
    main()
