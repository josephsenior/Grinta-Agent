"""Contract tests for RuntimeServiceAdapter."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from forge.services.adapters.runtime_adapter import RuntimeServiceAdapter
from forge.services.generated import runtime_service_pb2 as runtime_pb2


@pytest.fixture
def mock_orchestrator_factory():
    """Mock MetaSOPOrchestrator factory."""
    mock_orch = MagicMock()
    mock_ctx = MagicMock()
    mock_orch.context_manager.initialize_orchestration_context.return_value = mock_ctx
    mock_orch.settings.token_budget_soft = 20_000
    mock_orch.settings.token_budget_hard = 50_000
    mock_orch.settings.enable_failure_taxonomy = False
    mock_orch.context_manager.setup_retry_policy.return_value = MagicMock()
    mock_orch.step_execution.execute_step.return_value = (True, {})
    factory = MagicMock(return_value=mock_orch)
    factory.mock_orch = mock_orch
    return factory


@pytest.fixture
def runtime_adapter(mock_orchestrator_factory):
    """Create RuntimeServiceAdapter instance."""
    return RuntimeServiceAdapter(mock_orchestrator_factory, use_grpc=False)


def test_create_runtime(runtime_adapter, mock_orchestrator_factory):
    """Test creating a new runtime."""
    handle = runtime_adapter.create_runtime(
        session_id="test-session",
        repository="test-repo",
        branch="main",
        repo_root="/tmp/test",
        user_request="test request",
    )
    assert "runtime_id" in handle
    assert handle["session_id"] == "test-session"
    assert handle["repository"] == "test-repo"
    assert handle["branch"] == "main"
    mock_orchestrator_factory.assert_called_once()


def test_create_runtime_grpc_mode(mock_orchestrator_factory):
    """Test creating runtime via gRPC stub."""
    adapter = RuntimeServiceAdapter(
        mock_orchestrator_factory,
        use_grpc=True,
        grpc_endpoint="localhost:60051",
    )
    stub = MagicMock()
    stub.CreateRuntime.return_value = runtime_pb2.RuntimeHandle(
        runtime_id="rt-123",
        session_id="test-session",
        repository="test-repo",
        branch="main",
    )
    adapter._require_grpc_stub = MagicMock(return_value=stub)  # type: ignore[attr-defined]

    handle = adapter.create_runtime(
        session_id="test-session",
        repository="test-repo",
        branch="main",
        repo_root="/tmp",
        user_request="req",
    )

    stub.CreateRuntime.assert_called_once()
    assert handle["runtime_id"] == "rt-123"


def test_close_runtime(runtime_adapter):
    """Test closing a runtime."""
    handle = runtime_adapter.create_runtime(session_id="test-session")
    runtime_id = handle["runtime_id"]
    # Should not raise
    runtime_adapter.close_runtime(runtime_id, wait=False)


def test_close_runtime_grpc_mode(mock_orchestrator_factory):
    """Test close_runtime via gRPC."""
    adapter = RuntimeServiceAdapter(
        mock_orchestrator_factory, use_grpc=True, grpc_endpoint="localhost:60051"
    )
    stub = MagicMock()
    adapter._require_grpc_stub = MagicMock(return_value=stub)  # type: ignore[attr-defined]
    adapter.close_runtime("test-runtime", wait=True)
    stub.CloseRuntime.assert_called_once()


def test_get_orchestrator(runtime_adapter, mock_orchestrator_factory):
    """Retrieve orchestrator for in-process runtime."""
    handle = runtime_adapter.create_runtime(session_id="test-session")
    orchestrator = runtime_adapter.get_orchestrator(handle["runtime_id"])
    assert orchestrator is mock_orchestrator_factory.mock_orch


@pytest.mark.asyncio
async def test_run_step(runtime_adapter, mock_orchestrator_factory):
    """Test executing a step."""
    from forge.metasop.models import SopStep, StepOutputSpec

    handle = runtime_adapter.create_runtime(session_id="test-session")
    runtime_id = handle["runtime_id"]
    step = SopStep(
        id="step-1",
        role="coder",
        task="test task",
        outputs=StepOutputSpec(schema="dummy.json"),
    )
    result = await runtime_adapter.run_step(runtime_id, step, max_retries=2)
    assert "status" in result
    assert "step_id" in result
    assert result["step_id"] == "step-1"


@pytest.mark.asyncio
async def test_run_step_grpc_mode(mock_orchestrator_factory):
    """Test that step execution fails in gRPC mode (not yet implemented)."""
    from forge.metasop.models import SopStep, StepOutputSpec

    adapter = RuntimeServiceAdapter(mock_orchestrator_factory, use_grpc=True)
    step = SopStep(
        id="step-1",
        role="coder",
        task="test task",
        outputs=StepOutputSpec(schema="dummy.json"),
    )
    stub = MagicMock()

    def _run_step(request_iter, *args, **kwargs):
        list(request_iter)
        return [
            runtime_pb2.StepUpdate(
                runtime_id="test-runtime",
                step_id="step-1",
                update_type="result",
                status="completed",
                metadata={"success": "true"},
            )
        ]

    stub.RunStep.side_effect = _run_step
    adapter._require_grpc_stub = MagicMock(return_value=stub)  # type: ignore[attr-defined]

    result = await adapter.run_step("test-runtime", step)
    assert result["runtime_id"] == "test-runtime"
    assert result["status"] == "completed"

