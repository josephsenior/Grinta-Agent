import pytest
from types import SimpleNamespace

from forge.metasop.core.execution import ExecutionCoordinator
from forge.metasop.models import Artifact, RetryPolicy


class StubOrchestrator:
    def __init__(
        self,
        *,
        enabled: bool = True,
        steps: int = 2,
        token_soft: int | None = 15000,
        token_hard: int | None = 60000,
        enable_parallel: bool = False,
        enable_async: bool = False,
    ) -> None:
        self.settings = SimpleNamespace(
            enabled=enabled,
            token_budget_soft=token_soft,
            token_budget_hard=token_hard,
            enable_failure_taxonomy=True,
            enable_parallel_execution=enable_parallel,
            enable_async_execution=enable_async,
        )
        self.parallel_engine = object() if enable_parallel and enable_async else None
        self.template = SimpleNamespace(
            steps=[SimpleNamespace(id=f"step{i+1}", role=f"role{i+1}") for i in range(steps)]
        )
        self.memory_result = True
        self.ctx = SimpleNamespace()
        self.retry_policy = RetryPolicy(max_attempts=4)

        self.init_calls = 0
        self.memory_calls = 0
        self.retry_calls: list[int] = []
        self.single_step_calls: list[dict] = []
        self.single_step_async_calls: list[dict] = []
        self.parallel_async_calls: list[dict] = []

    def _initialize_orchestration_context(self, user_request, repo_root):
        self.init_calls += 1
        return self.ctx

    def _setup_memory_and_models(self, ctx):
        self.memory_calls += 1
        return self.memory_result

    def _setup_retry_policy(self, max_retries):
        self.retry_calls.append(max_retries)
        return self.retry_policy

    def _process_single_step(
        self,
        step,
        ctx,
        done,
        soft_budget,
        hard_budget,
        consumed_tokens,
        taxonomy_enabled,
        retry_policy,
        max_retries,
    ):
        self.single_step_calls.append(
            {
                "step": step,
                "soft_budget": soft_budget,
                "hard_budget": hard_budget,
                "consumed_tokens": consumed_tokens,
                "taxonomy_enabled": taxonomy_enabled,
                "retry_policy": retry_policy,
                "max_retries": max_retries,
            }
        )
        return True, {step.id: Artifact(step_id=step.id, role=step.role, content={})}

    async def _process_single_step_async(
        self,
        step,
        ctx,
        done,
        soft_budget,
        hard_budget,
        consumed_tokens,
        taxonomy_enabled,
        retry_policy,
        max_retries,
    ):
        self.single_step_async_calls.append(
            {
                "step": step,
                "soft_budget": soft_budget,
                "hard_budget": hard_budget,
                "consumed_tokens": consumed_tokens,
                "taxonomy_enabled": taxonomy_enabled,
                "retry_policy": retry_policy,
                "max_retries": max_retries,
            }
        )
        return True, {step.id: Artifact(step_id=step.id, role=step.role, content={})}

    async def _process_orchestration_steps_async(
        self,
        ctx,
        done,
        soft_budget,
        hard_budget,
        consumed_tokens,
        taxonomy_enabled,
        retry_policy,
        max_retries,
    ):
        self.parallel_async_calls.append(
            {
                "soft_budget": soft_budget,
                "hard_budget": hard_budget,
                "consumed_tokens": consumed_tokens,
                "taxonomy_enabled": taxonomy_enabled,
                "retry_policy": retry_policy,
                "max_retries": max_retries,
            }
        )
        return True, {
            "parallel": Artifact(step_id="parallel", role="runner", content={})
        }


def test_run_disabled_short_circuits():
    orch = StubOrchestrator(enabled=False)
    coord = ExecutionCoordinator(orch)

    success, artifacts = coord.run("request")

    assert success is False
    assert artifacts == {}
    assert orch.init_calls == 0
    assert orch.memory_calls == 0


def test_run_success_aggregates_artifacts():
    orch = StubOrchestrator(token_soft=12345, token_hard=67890)
    coord = ExecutionCoordinator(orch)

    success, artifacts = coord.run("request")

    assert success is True
    assert set(artifacts.keys()) == {"step1", "step2"}
    assert orch.init_calls == 1
    assert orch.memory_calls == 1
    assert orch.retry_calls == [2]

    call = orch.single_step_calls[0]
    assert call["soft_budget"] == 12345
    assert call["hard_budget"] == 67890
    assert call["max_retries"] == 2
    assert call["retry_policy"] is orch.retry_policy


def test_run_setup_failure_returns_false():
    orch = StubOrchestrator()
    orch.memory_result = False
    coord = ExecutionCoordinator(orch)

    success, artifacts = coord.run("request")

    assert success is False
    assert artifacts == {}
    assert orch.memory_calls == 1
    assert orch.single_step_calls == []


def test_run_template_missing_returns_false():
    orch = StubOrchestrator()
    orch.template = None
    coord = ExecutionCoordinator(orch)

    success, artifacts = coord.run("request")

    assert success is False
    assert artifacts == {}
    assert orch.single_step_calls == []


@pytest.mark.asyncio
async def test_run_async_parallel_branch_prefers_parallel_engine():
    orch = StubOrchestrator(enable_parallel=True, enable_async=True)
    coord = ExecutionCoordinator(orch)

    success, artifacts = await coord.run_async("request")

    assert success is True
    assert set(artifacts.keys()) == {"parallel"}
    assert len(orch.parallel_async_calls) == 1
    assert orch.single_step_async_calls == []

    call = orch.parallel_async_calls[0]
    assert call["max_retries"] == 2
    assert call["retry_policy"] is orch.retry_policy


@pytest.mark.asyncio
async def test_run_async_sequential_fallback_executes_each_step():
    orch = StubOrchestrator(enable_parallel=False, enable_async=True)
    coord = ExecutionCoordinator(orch)

    success, artifacts = await coord.run_async("request")

    assert success is True
    assert set(artifacts.keys()) == {"step1", "step2"}
    assert orch.parallel_async_calls == []
    assert len(orch.single_step_async_calls) == 2
    first_call = orch.single_step_async_calls[0]
    assert first_call["max_retries"] == 2
    assert first_call["retry_policy"] is orch.retry_policy
