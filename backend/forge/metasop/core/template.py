from __future__ import annotations

from typing import TYPE_CHECKING, Any, Awaitable, Callable, Dict, Tuple

from forge.core.logger import forge_logger as logger

if TYPE_CHECKING:  # pragma: no cover
    from forge.metasop.models import Artifact, OrchestrationContext, RetryPolicy
    from forge.metasop.orchestrator import MetaSOPOrchestrator
    from forge.metasop.core.steps import SopStep


class TemplateToolkit:
    """Handles template-driven orchestration flows (sequential, parallel, async)."""

    def __init__(self, orchestrator: "MetaSOPOrchestrator") -> None:
        self._orch = orchestrator

    # ------------------------------------------------------------------
    # Synchronous orchestration
    # ------------------------------------------------------------------
    def process_orchestration_steps(
        self,
        ctx: "OrchestrationContext",
        done: Dict[str, "Artifact"],
        soft_budget: int,
        hard_budget: int,
        consumed_tokens: int,
        taxonomy_enabled: bool,
        retry_policy: "RetryPolicy",
        max_retries: int,
    ) -> Tuple[bool, Dict[str, "Artifact"]]:
        """Process orchestration steps with optional parallel execution."""

        orch = self._orch
        if orch.parallel_engine and getattr(
            orch.settings, "enable_parallel_execution", False
        ):
            return self.process_steps_parallel(
                ctx,
                done,
                soft_budget,
                hard_budget,
                consumed_tokens,
                taxonomy_enabled,
                retry_policy,
                max_retries,
            )

        return self.process_steps_sequential(
            ctx,
            done,
            soft_budget,
            hard_budget,
            consumed_tokens,
            taxonomy_enabled,
            retry_policy,
            max_retries,
        )

    def process_steps_parallel(
        self,
        ctx: "OrchestrationContext",
        done: Dict[str, "Artifact"],
        soft_budget: int,
        hard_budget: int,
        consumed_tokens: int,
        taxonomy_enabled: bool,
        retry_policy: "RetryPolicy",
        max_retries: int,
    ) -> Tuple[bool, Dict[str, "Artifact"]]:
        """Process orchestration steps using intelligent parallel execution."""

        orch = self._orch
        parallel_engine = orch.parallel_engine
        template = orch.template
        if parallel_engine is None or template is None:
            return self.process_steps_sequential(
                ctx,
                done,
                soft_budget,
                hard_budget,
                consumed_tokens,
                taxonomy_enabled,
                retry_policy,
                max_retries,
            )

        logger.info("Starting parallel execution of orchestration steps")

        try:
            parallel_groups = parallel_engine.identify_parallel_groups(template.steps, done)
            logger.info(f"Identified {len(parallel_groups)} parallel execution groups")

            process_single_step: Callable[..., Tuple[bool, Dict[str, "Artifact"]]] = (
                getattr(orch, "_process_single_step")
            )
            success, artifacts = parallel_engine.execute_parallel_groups(
                parallel_groups,
                process_single_step,
                (
                    ctx,
                    done,
                    soft_budget,
                    hard_budget,
                    consumed_tokens,
                    taxonomy_enabled,
                    retry_policy,
                    max_retries,
                ),
            )

            stats = parallel_engine.get_execution_stats()
            logger.info(f"Parallel execution completed: {stats}")

            emit_event = getattr(orch, "_emit_event", None)
            if callable(emit_event):
                emit_event(
                    {
                        "type": "parallel_execution_complete",
                        "stats": stats,
                        "groups_executed": len(parallel_groups),
                    }
                )

            return success, artifacts

        except Exception as exc:  # pragma: no cover - defensive fallback
            logger.error(f"Parallel execution failed, falling back to sequential: {exc}")
            return self.process_steps_sequential(
                ctx,
                done,
                soft_budget,
                hard_budget,
                consumed_tokens,
                taxonomy_enabled,
                retry_policy,
                max_retries,
            )

    def process_steps_sequential(
        self,
        ctx: "OrchestrationContext",
        done: Dict[str, "Artifact"],
        soft_budget: int,
        hard_budget: int,
        consumed_tokens: int,
        taxonomy_enabled: bool,
        retry_policy: "RetryPolicy",
        max_retries: int,
    ) -> Tuple[bool, Dict[str, "Artifact"]]:
        """Process orchestration steps sequentially."""

        template = self._orch.template
        if template is None:
            return False, {}

        artifacts: Dict[str, "Artifact"] = {}

        process_single_step: Callable[..., Tuple[bool, Dict[str, "Artifact"]]] = getattr(
            self._orch, "_process_single_step"
        )

        for step in template.steps:
            step_success, step_artifacts = process_single_step(
                step,
                ctx,
                done,
                soft_budget,
                hard_budget,
                consumed_tokens,
                taxonomy_enabled,
                retry_policy,
                max_retries,
            )

            if not step_success:
                return False, artifacts

            artifacts |= step_artifacts

        return True, artifacts

    # ------------------------------------------------------------------
    # Asynchronous orchestration
    # ------------------------------------------------------------------
    async def process_orchestration_steps_async(
        self,
        ctx: "OrchestrationContext",
        done: Dict[str, "Artifact"],
        soft_budget: int,
        hard_budget: int,
        consumed_tokens: int,
        taxonomy_enabled: bool,
        retry_policy: "RetryPolicy",
        max_retries: int,
    ) -> Tuple[bool, Dict[str, "Artifact"]]:
        """Process orchestration steps with async parallel execution where possible."""

        orch = self._orch
        template = orch.template
        if template is None:
            return False, {}

        try:
            execution_steps = await self._maybe_plan_execution_steps(orch, template, ctx)
            if self._can_execute_parallel_async(orch):
                return await self._execute_parallel_async(
                    orch,
                    ctx,
                    done,
                    soft_budget,
                    hard_budget,
                    consumed_tokens,
                    taxonomy_enabled,
                    retry_policy,
                    max_retries,
                    execution_steps,
                )
            return await self.process_steps_sequential_async(
                ctx,
                done,
                soft_budget,
                hard_budget,
                consumed_tokens,
                taxonomy_enabled,
                retry_policy,
                max_retries,
            )
        except Exception as exc:  # pragma: no cover - defensive logging
            logger.error(
                "Async execution failed, falling back to sequential async: %s",
                exc,
            )
            return await self.process_steps_sequential_async(
                ctx,
                done,
                soft_budget,
                hard_budget,
                consumed_tokens,
                taxonomy_enabled,
                retry_policy,
                max_retries,
            )

    async def _maybe_plan_execution_steps(
        self, orch, template, ctx
    ) -> list["SopStep"]:
        execution_steps = template.steps
        predictive_planner = orch.predictive_planner
        if predictive_planner and getattr(
            orch.settings, "enable_predictive_planning", False
        ):
            execution_steps = await self._run_predictive_planner(
                orch, predictive_planner, template, ctx
            )
        return execution_steps

    async def _run_predictive_planner(
        self, orch, predictive_planner, template, ctx
    ) -> list["SopStep"]:
        try:
            logger.info("🔮 Starting predictive execution planning...")
            execution_plan = await predictive_planner.analyze_execution_path(
                template.steps, ctx
            )
            confidence_threshold = getattr(
                orch.settings, "predictive_confidence_threshold", 0.7
            )
            if execution_plan.confidence_score >= confidence_threshold:
                self._log_predictive_plan(execution_plan)
                return execution_plan.optimized_steps
            logger.info(
                "🔮 Predictive plan confidence too low (%.2f < %.2f), using original execution order",
                execution_plan.confidence_score,
                confidence_threshold,
            )
        except Exception as exc:  # pragma: no cover - telemetry only
            logger.warning(
                "Predictive planning failed, using original execution: %s",
                exc,
            )
        return template.steps

    def _log_predictive_plan(self, execution_plan) -> None:
        logger.info(
            "🎯 Using predictive execution plan: %.1fx parallelization, %.0fms predicted time",
            execution_plan.parallelization_factor,
            execution_plan.predicted_total_time_ms,
        )
        if execution_plan.conflict_warnings:
            logger.warning(
                "⚠️ Predictive warnings: %s",
                ", ".join(execution_plan.conflict_warnings[:3]),
            )
        if execution_plan.optimization_opportunities:
            logger.info(
                "💡 Optimization opportunities: %s",
                ", ".join(execution_plan.optimization_opportunities[:3]),
            )

    def _can_execute_parallel_async(self, orch) -> bool:
        return (
            orch.parallel_engine
            and getattr(orch.settings, "enable_parallel_execution", False)
            and getattr(orch.settings, "enable_async_execution", False)
        )

    async def _execute_parallel_async(
        self,
        orch,
        ctx,
        done,
        soft_budget,
        hard_budget,
        consumed_tokens,
        taxonomy_enabled,
        retry_policy,
        max_retries,
        execution_steps,
    ):
        parallel_engine = orch.parallel_engine
        assert parallel_engine is not None
        parallel_groups = parallel_engine.identify_parallel_groups(execution_steps, done)
        logger.info(
            "Identified %d parallel execution groups for async execution",
            len(parallel_groups),
        )
        process_single_step_async: Callable[
            ...,
            Awaitable[Tuple[bool, Dict[str, "Artifact"]]],
        ] = getattr(orch, "_process_single_step_async")
        success, artifacts = await parallel_engine.execute_parallel_groups_async(
            parallel_groups,
            process_single_step_async,
            (
                ctx,
                done,
                soft_budget,
                hard_budget,
                consumed_tokens,
                taxonomy_enabled,
                retry_policy,
                max_retries,
            ),
        )
        stats = parallel_engine.get_execution_stats()
        logger.info(f"Async parallel execution completed: {stats}")
        emit_event = getattr(orch, "_emit_event", None)
        if callable(emit_event):
            emit_event(
                {
                    "type": "async_parallel_execution_complete",
                    "stats": stats,
                    "groups_executed": len(parallel_groups),
                    "execution_mode": "async_parallel",
                }
            )
        return success, artifacts

    async def process_steps_sequential_async(
        self,
        ctx: "OrchestrationContext",
        done: Dict[str, "Artifact"],
        soft_budget: int,
        hard_budget: int,
        consumed_tokens: int,
        taxonomy_enabled: bool,
        retry_policy: "RetryPolicy",
        max_retries: int,
    ) -> Tuple[bool, Dict[str, "Artifact"]]:
        """Process orchestration steps sequentially using async execution."""

        template = self._orch.template
        if template is None:
            return False, {}

        artifacts: Dict[str, "Artifact"] = {}

        process_single_step_async: Callable[
            ...,
            Awaitable[Tuple[bool, Dict[str, "Artifact"]]],
        ] = getattr(self._orch, "_process_single_step_async")

        for step in template.steps:
            step_success, step_artifacts = await process_single_step_async(
                step,
                ctx,
                done,
                soft_budget,
                hard_budget,
                consumed_tokens,
                taxonomy_enabled,
                retry_policy,
                max_retries,
            )

            if not step_success:
                return False, artifacts

            artifacts |= step_artifacts

        return True, artifacts


__all__ = ["TemplateToolkit"]
