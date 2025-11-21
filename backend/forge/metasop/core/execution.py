from __future__ import annotations

from typing import TYPE_CHECKING, Any, Dict, Tuple

from forge.metasop.models import Artifact

if TYPE_CHECKING:  # pragma: no cover
    from forge.metasop.orchestrator import MetaSOPOrchestrator


class ExecutionCoordinator:
    """Coordinates MetaSOP orchestration runs for sync and async flows."""

    def __init__(self, orchestrator: "MetaSOPOrchestrator") -> None:
        self._orch: Any = orchestrator
        self._step_manager: Any = orchestrator.step_execution

    def run(
        self,
        user_request: str,
        repo_root: str | None = None,
        max_retries: int = 2,
    ) -> Tuple[bool, Dict[str, Artifact]]:
        """Synchronously execute an orchestration run."""
        if not (self._orch.settings.enabled):
            return False, {}

        setup_result = self._setup_orchestration(user_request, repo_root, max_retries)
        if not setup_result["success"]:
            return False, setup_result.get("done", {})

        return self._execute_orchestration_steps(
            setup_result["ctx"], setup_result["retry_policy"], repo_root
        )

    async def run_async(
        self,
        user_request: str,
        repo_root: str | None = None,
        max_retries: int = 2,
    ) -> Tuple[bool, Dict[str, Artifact]]:
        """Asynchronously execute an orchestration run."""
        if not (self._orch.settings.enabled):
            return False, {}

        setup_result = self._setup_orchestration(user_request, repo_root, max_retries)
        if not setup_result["success"]:
            return False, setup_result.get("done", {})

        return await self._execute_orchestration_steps_async(
            setup_result["ctx"], setup_result["retry_policy"], repo_root
        )

    # Internal helpers -------------------------------------------------
    def _setup_orchestration(self, user_request, repo_root, max_retries):
        orch = self._orch
        ctx = orch._initialize_orchestration_context(user_request, repo_root)
        if not ctx:
            return {"success": False, "done": {}}

        if not orch._setup_memory_and_models(ctx):
            return {"success": False, "done": {}}

        retry_policy = orch._setup_retry_policy(max_retries)
        return {"success": True, "ctx": ctx, "retry_policy": retry_policy}

    def _execute_orchestration_steps(self, ctx, retry_policy, repo_root):
        orch = self._orch
        done: Dict[str, Artifact] = {}
        template = orch.template
        if template is None:
            return False, done

        soft_budget = orch.settings.token_budget_soft or 20000
        hard_budget = orch.settings.token_budget_hard or 50000
        taxonomy_enabled = orch.settings.enable_failure_taxonomy
        max_retries = 2  # legacy default

        success, artifacts = orch.template_toolkit.process_orchestration_steps(
            ctx,
            done,
            soft_budget,
            hard_budget,
            0,  # consumed_tokens (legacy placeholder)
            taxonomy_enabled,
            retry_policy,
            max_retries,
        )
        done.update(artifacts)
        return success, done

    async def _execute_orchestration_steps_async(self, ctx, retry_policy, repo_root):
        orch = self._orch
        done: Dict[str, Artifact] = {}

        soft_budget = orch.settings.token_budget_soft or 20000
        hard_budget = orch.settings.token_budget_hard or 50000
        taxonomy_enabled = orch.settings.enable_failure_taxonomy
        max_retries = 2

        success, artifacts = await orch.template_toolkit.process_orchestration_steps_async(
            ctx,
            done,
            soft_budget,
            hard_budget,
            0,
            taxonomy_enabled,
            retry_policy,
            max_retries,
        )
        done.update(artifacts)
        return success, done


__all__ = ["ExecutionCoordinator"]
