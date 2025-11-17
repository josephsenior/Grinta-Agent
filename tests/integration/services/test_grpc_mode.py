"""Integration tests exercising adapters against real gRPC services."""

from __future__ import annotations

from concurrent import futures
import tempfile
from unittest.mock import MagicMock

import grpc
import pytest

from forge.events.action import MessageAction
from forge.events.event import EventSource
from forge.events.serialization.event import event_to_dict
from forge.services.adapters.event_adapter import EventServiceAdapter
from forge.services.adapters.runtime_adapter import RuntimeServiceAdapter
from forge.services.event_service.grpc_server import EventServiceGrpcServicer
from forge.services.event_service.service import EventServiceServer, ReplayRequest
from forge.services.generated import event_service_pb2_grpc as event_grpc
from forge.services.generated import runtime_service_pb2_grpc as runtime_grpc
from forge.services.runtime_service.grpc_server import RuntimeServiceGrpcServicer
from forge.services.runtime_service.service import RuntimeServiceServer
from forge.storage.local import LocalFileStore

pytestmark = pytest.mark.integration


@pytest.fixture
def file_store_factory():
    with tempfile.TemporaryDirectory() as tmpdir:
        store = LocalFileStore(tmpdir)

        def _factory(_user_id: str | None = None):
            return store

        yield _factory


@pytest.fixture
async def event_service_endpoint(file_store_factory):
    backend = EventServiceServer(file_store_factory)
    server = grpc.server(futures.ThreadPoolExecutor(max_workers=4))
    event_grpc.add_EventServiceServicer_to_server(EventServiceGrpcServicer(backend), server)
    port = server.add_insecure_port("127.0.0.1:0")
    server.start()
    endpoint = f"127.0.0.1:{port}"
    try:
        yield backend, endpoint
    finally:
        server.stop(0)


@pytest.fixture
async def runtime_service_endpoint():
    orchestrator = MagicMock()
    orchestrator.context_manager.initialize_orchestration_context.return_value = MagicMock()
    orchestrator.settings.token_budget_soft = 10_000
    orchestrator.settings.token_budget_hard = 20_000
    orchestrator.settings.enable_failure_taxonomy = False
    orchestrator.context_manager.setup_retry_policy.return_value = MagicMock()
    orchestrator.step_execution.execute_step.return_value = (True, {})

    factory = MagicMock(return_value=orchestrator)
    backend = RuntimeServiceServer(factory)

    server = grpc.server(futures.ThreadPoolExecutor(max_workers=4))
    runtime_grpc.add_RuntimeServiceServicer_to_server(
        RuntimeServiceGrpcServicer(backend), server
    )
    port = server.add_insecure_port("127.0.0.1:0")
    server.start()
    endpoint = f"127.0.0.1:{port}"
    try:
        yield backend, endpoint, factory
    finally:
        server.stop(0)


@pytest.mark.asyncio
async def test_event_adapter_over_grpc(event_service_endpoint, file_store_factory):
    backend, endpoint = event_service_endpoint
    adapter = EventServiceAdapter(
        file_store_factory,
        use_grpc=True,
        grpc_endpoint=endpoint,
        grpc_timeout_seconds=5.0,
        client_id="test-client",
    )

    try:
        session_info = adapter.start_session(user_id="user-1")
        session_id = session_info["session_id"]

        action = MessageAction(content="hello", wait_for_response=False)
        action.source = EventSource.USER
        event_dict = event_to_dict(action)

        adapter.publish_event(session_id, event_dict)

        chunk = backend.replay(
            ReplayRequest(session_id=session_id, from_cursor=0, limit=10)
        )
        events = list(chunk.events)
        assert len(events) == 1
        assert events[0].session_id == session_id
    finally:
        adapter.close()


@pytest.mark.asyncio
async def test_runtime_adapter_over_grpc(runtime_service_endpoint):
    backend, endpoint, factory = runtime_service_endpoint
    adapter = RuntimeServiceAdapter(
        factory,
        use_grpc=True,
        grpc_endpoint=endpoint,
        grpc_timeout_seconds=5.0,
        client_id="test-client",
    )

    try:
        handle = adapter.create_runtime(session_id="session-1")
        from forge.metasop.models import SopStep, StepOutputSpec

        step = SopStep(
            id="step-1",
            role="coder",
            task="implement feature",
            outputs=StepOutputSpec(schema="out.json"),
        )

        result = await adapter.run_step(handle["runtime_id"], step, max_retries=1)
        assert result["status"] in {"completed", "failed"}
        assert result["runtime_id"] == handle["runtime_id"]
    finally:
        adapter.close_runtime(handle["runtime_id"])
        adapter.close()

