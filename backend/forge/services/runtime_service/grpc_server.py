"""gRPC servicer implementation for the RuntimeService."""

from __future__ import annotations

import asyncio
from typing import Iterable

from google.protobuf import empty_pb2

from forge.services.generated import runtime_service_pb2 as runtime_pb2
from forge.services.generated import runtime_service_pb2_grpc as runtime_grpc
from forge.services.runtime_service.service import (
    CloseRuntimeRequest,
    CreateRuntimeRequest,
    RuntimeHandle,
    RunStepRequest,
    RuntimeServiceServer,
    StepUpdate,
)


class RuntimeServiceGrpcServicer(runtime_grpc.RuntimeServiceServicer):
    """Bridge gRPC requests to the in-process RuntimeServiceServer."""

    def __init__(self, backend: RuntimeServiceServer) -> None:
        self._backend = backend

    def CreateRuntime(
        self, request: runtime_pb2.CreateRuntimeRequest, context
    ) -> runtime_pb2.RuntimeHandle:  # type: ignore[override]
        handle = self._backend.create_runtime(
            CreateRuntimeRequest(
                session_id=request.session_id,
                repository=request.repository or None,
                branch=request.branch or None,
                repo_root=request.repo_root or None,
                user_request=request.user_request or "runtime-service",
            )
        )
        return runtime_pb2.RuntimeHandle(
            runtime_id=handle.runtime_id,
            session_id=handle.session_id,
            repository=handle.repository or "",
            branch=handle.branch or "",
        )

    def RunStep(
        self,
        request_iterator: Iterable[runtime_pb2.RunStepRequest],
        context,
    ) -> Iterable[runtime_pb2.StepUpdate]:  # type: ignore[override]
        request = next(iter(request_iterator))
        backend_req = _to_backend_run_step(request)

        async def _collect():
            return [update async for update in self._backend.run_step(backend_req)]

        for update in asyncio.run(_collect()):
            yield _to_proto_step_update(update)

    def CloseRuntime(
        self, request: runtime_pb2.CloseRuntimeRequest, context
    ) -> empty_pb2.Empty:  # type: ignore[override]
        self._backend.close_runtime(
            CloseRuntimeRequest(runtime_id=request.runtime_id, wait=request.wait)
        )
        return empty_pb2.Empty()


def _to_backend_run_step(proto: runtime_pb2.RunStepRequest) -> RunStepRequest:
    step_proto = proto.step
    step = _proto_to_sop_step(step_proto)
    return RunStepRequest(
        runtime_id=proto.runtime_id,
        step=step,
        max_retries=proto.max_retries or 0,
        trace_id=proto.trace_id or None,
    )


def _proto_to_sop_step(proto: runtime_pb2.SopStepMessage):
    from forge.metasop.models import SopStep, StepOutputSpec

    outputs = StepOutputSpec(schema=proto.outputs.schema or "default.json")
    return SopStep(
        id=proto.id,
        role=proto.role,
        task=proto.task,
        outputs=outputs,
        depends_on=list(proto.depends_on),
        condition=proto.condition or None,
        lock=proto.lock or None,
        priority=proto.priority or 0,
    )


def _to_proto_step_update(update: StepUpdate) -> runtime_pb2.StepUpdate:
    proto = runtime_pb2.StepUpdate(
        runtime_id=update.runtime_id,
        step_id=update.step_id,
        update_type=update.update_type,
        status=update.status,
    )
    proto.metadata.update(update.metadata)
    return proto

