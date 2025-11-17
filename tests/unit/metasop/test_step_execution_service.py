from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import MagicMock

from forge.metasop.step_execution_service import StepExecutionService


def _step():
    return SimpleNamespace(id="s1", role="builder")


def _ctx():
    return SimpleNamespace()


def test_execute_with_retries_success_path():
    orch = MagicMock()
    service = StepExecutionService(orch)
    orch._get_micro_iteration_config.return_value = {}
    service._execute_step_attempt = MagicMock(return_value="result")
    orch._is_step_execution_successful.return_value = True
    orch.retry_service.handle_success.return_value = (True, {"s1": "artifact"})

    success, artifacts = service.execute_with_retries(
        _step(),
        _ctx(),
        {},
        {},
        MagicMock(),
        max_retries=1,
        soft_budget=0,
        hard_budget=0,
        consumed_tokens=0,
        taxonomy_enabled=False,
    )

    assert success is True
    assert artifacts == {"s1": "artifact"}
    orch.retry_service.handle_success.assert_called_once()


def test_execute_with_retries_failure_path():
    orch = MagicMock()
    service = StepExecutionService(orch)
    orch._get_micro_iteration_config.return_value = {}
    service._execute_step_attempt = MagicMock(return_value="result")
    orch._is_step_execution_successful.return_value = False
    orch.retry_service.handle_failure.return_value = (False, {})

    success, _ = service.execute_with_retries(
        _step(),
        _ctx(),
        {},
        {},
        MagicMock(),
        max_retries=0,
        soft_budget=0,
        hard_budget=0,
        consumed_tokens=0,
        taxonomy_enabled=False,
    )

    assert success is False
    orch.retry_service.handle_failure.assert_called_once()


def test_execute_step_attempt_uses_micro_iterations_when_enabled():
    orch = MagicMock()
    service = StepExecutionService(orch)
    config = {"candidate_count": 2, "speculative_enabled": True, "patch_scoring_enabled": False}
    orch.candidate_service.generate_and_select.return_value = "micro"

    result = service._execute_step_attempt(
        _step(), _ctx(), {}, MagicMock(), config
    )

    assert result == "micro"
    orch.candidate_service.generate_and_select.assert_called_once()


def test_execute_step_attempt_falls_back_to_regular_retry():
    orch = MagicMock()
    service = StepExecutionService(orch)
    config = {"candidate_count": 1, "speculative_enabled": False, "patch_scoring_enabled": False}
    orch._attempt_execute_with_retry.return_value = "regular"

    result = service._execute_step_attempt(
        _step(), _ctx(), {}, MagicMock(), config
    )

    assert result == "regular"
    orch._attempt_execute_with_retry.assert_called_once()

