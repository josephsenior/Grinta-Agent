"""Adapter for RuntimeService that bridges service contracts with MetaSOPOrchestrator."""

from __future__ import annotations

import asyncio
import logging
import os
from typing import TYPE_CHECKING, Any, Callable, Optional

import grpc

from .grpc_utils import create_insecure_channel
from forge.services.generated import runtime_service_pb2 as runtime_pb2
from forge.services.generated import runtime_service_pb2_grpc as runtime_grpc

if TYPE_CHECKING:
    from forge.events.stream import EventStream
    from forge.metasop.models import SopStep
    from forge.metasop.orchestrator import MetaSOPOrchestrator
    from forge.services.runtime_service.service import RuntimeServiceServer


class RuntimeServiceAdapter:
    """Adapter that wraps RuntimeServiceServer for use in monolith or as gRPC service.

    This adapter provides a thin layer that can switch between:
    - In-process: Direct MetaSOPOrchestrator access
    - gRPC: Network-based service calls (future)

    The adapter maintains compatibility with existing monolith code while
    enabling a gradual migration to service-based architecture.
    """

    def __init__(
        self,
        orchestrator_factory: Callable[[], "MetaSOPOrchestrator"],
        use_grpc: bool = False,
        grpc_endpoint: Optional[str] = None,
        event_stream_provider: Optional[Callable[[str], "EventStream"]] = None,
        *,
        grpc_timeout_seconds: float = 30.0,
        auth_token: Optional[str] = None,
        client_id: Optional[str] = None,
    ) -> None:
        """Initialize the runtime service adapter.

        Args:
            orchestrator_factory: Factory function that creates MetaSOPOrchestrator instances
            use_grpc: If True, use gRPC client (future). If False, use in-process server.
            grpc_endpoint: gRPC server endpoint (required if use_grpc=True)

        """
        self._use_grpc = use_grpc
        self._grpc_endpoint = grpc_endpoint
        self._orchestrator_factory = orchestrator_factory
        self._in_process_server: Optional["RuntimeServiceServer"] = None
        self._event_stream_getter = event_stream_provider
        self._grpc_channel: Optional[grpc.Channel] = None
        self._grpc_stub: Optional[runtime_grpc.RuntimeServiceStub] = None
        self._grpc_timeout = grpc_timeout_seconds
        self._logger = logging.getLogger(__name__)
        self._client_id = client_id or os.getenv("FORGE_SERVICE_CLIENT_ID", "forge-monolith")
        self._auth_token = auth_token or os.getenv("FORGE_RUNTIME_SERVICE_TOKEN")

        if not use_grpc:
            from forge.services.runtime_service import RuntimeServiceServer

            self._in_process_server = RuntimeServiceServer(
                orchestrator_factory,
                event_stream_provider=event_stream_provider,
            )

    # ------------------------------------------------------------------
    # Runtime lifecycle
    # ------------------------------------------------------------------
    def create_runtime(
        self,
        session_id: str,
        repository: Optional[str] = None,
        branch: Optional[str] = None,
        repo_root: Optional[str] = None,
        user_request: str = "runtime-service",
    ) -> dict[str, Any]:
        """Create a new runtime and return runtime handle.

        Args:
            session_id: Session ID
            repository: Optional repository name
            branch: Optional branch name
            repo_root: Optional repository root path
            user_request: User request string

        Returns:
            Dictionary with runtime_id and other metadata

        """
        if self._use_grpc:
            stub = self._require_grpc_stub()
            grpc_request = runtime_pb2.CreateRuntimeRequest(
                session_id=session_id,
                repository=repository or "",
                branch=branch or "",
                repo_root=repo_root or "",
                user_request=user_request or "",
            )
            metadata = self._build_metadata()
            self._logger.debug(
                "RuntimeService.CreateRuntime(session_id=%s, metadata=%s)", session_id, metadata
            )
            response = stub.CreateRuntime(
                grpc_request, timeout=self._grpc_timeout, metadata=metadata
            )
            return {
                "runtime_id": response.runtime_id,
                "session_id": response.session_id,
                "repository": response.repository,
                "branch": response.branch,
            }
        if self._in_process_server is None:
            raise RuntimeError("In-process server not initialized")
        from forge.services.runtime_service import CreateRuntimeRequest

        request = CreateRuntimeRequest(
            session_id=session_id,
            repository=repository,
            branch=branch,
            repo_root=repo_root,
            user_request=user_request,
        )
        handle = self._in_process_server.create_runtime(request)
        return {
            "runtime_id": handle.runtime_id,
            "session_id": handle.session_id,
            "repository": handle.repository,
            "branch": handle.branch,
        }

    def get_orchestrator(self, runtime_id: str) -> "MetaSOPOrchestrator":
        """Return the MetaSOP orchestrator for an in-process runtime."""

        if self._use_grpc:
            raise NotImplementedError("gRPC client not yet implemented")
        if self._in_process_server is None:
            raise RuntimeError("In-process server not initialized")
        state = self._in_process_server.get_runtime_state(runtime_id)
        return state.orchestrator

    def close_runtime(self, runtime_id: str, wait: bool = False) -> None:
        """Close a runtime.

        Args:
            runtime_id: Runtime ID
            wait: Whether to wait for cleanup

        """
        if self._use_grpc:
            stub = self._require_grpc_stub()
            grpc_request = runtime_pb2.CloseRuntimeRequest(runtime_id=runtime_id, wait=wait)
            metadata = self._build_metadata()
            self._logger.debug(
                "RuntimeService.CloseRuntime(runtime_id=%s, metadata=%s)", runtime_id, metadata
            )
            stub.CloseRuntime(grpc_request, timeout=self._grpc_timeout, metadata=metadata)
            return
        if self._in_process_server is None:
            raise RuntimeError("In-process server not initialized")
        from forge.services.runtime_service import CloseRuntimeRequest

        request = CloseRuntimeRequest(runtime_id=runtime_id, wait=wait)
        self._in_process_server.close_runtime(request)

    # ------------------------------------------------------------------
    # Step execution
    # ------------------------------------------------------------------
    async def run_step(
        self,
        runtime_id: str,
        step: "SopStep",
        max_retries: int = 2,
        trace_id: Optional[str] = None,
    ) -> dict[str, Any]:
        """Execute a step and return result.

        Args:
            runtime_id: Runtime ID
            step: SOP step to execute
            max_retries: Maximum number of retries
            trace_id: Optional trace ID

        Returns:
            Dictionary with step execution result

        """
        if self._use_grpc:
            stub = self._require_grpc_stub()
            proto_step = self._sop_step_to_proto(step)
            grpc_request = runtime_pb2.RunStepRequest(
                runtime_id=runtime_id,
                step=proto_step,
                max_retries=max_retries,
                trace_id=trace_id or "",
            )
            metadata = self._build_metadata(trace_id=trace_id)
            self._logger.debug(
                "RuntimeService.RunStep(runtime_id=%s, step_id=%s, metadata=%s)",
                runtime_id,
                step.id,
                metadata,
            )
            loop = asyncio.get_running_loop()
            updates = await loop.run_in_executor(
                None,
                self._invoke_run_step_stream,
                stub,
                grpc_request,
                metadata,
                self._grpc_timeout,
            )
            if not updates:
                return {"status": "failed", "error": "No updates received"}
            last_update = updates[-1]
            return {
                "runtime_id": last_update.runtime_id,
                "step_id": last_update.step_id,
                "update_type": last_update.update_type,
                "status": last_update.status,
                "metadata": dict(last_update.metadata),
            }
        if self._in_process_server is None:
            raise RuntimeError("In-process server not initialized")
        from forge.services.runtime_service import RunStepRequest

        request = RunStepRequest(
            runtime_id=runtime_id,
            step=step,
            max_retries=max_retries,
            trace_id=trace_id,
        )
        local_updates: list[Any] = []
        async for update in self._in_process_server.run_step(request):
            local_updates.append(update)
        if not local_updates:
            return {"status": "failed", "error": "No updates received"}
        last_update = local_updates[-1]
        return {
            "runtime_id": last_update.runtime_id,
            "step_id": last_update.step_id,
            "update_type": last_update.update_type,
            "status": last_update.status,
            "metadata": last_update.metadata,
        }

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------
    def _require_grpc_stub(self) -> runtime_grpc.RuntimeServiceStub:
        if not self._use_grpc:
            raise RuntimeError("gRPC stub requested while in in-process mode")
        if not self._grpc_endpoint:
            raise RuntimeError("gRPC endpoint not configured for RuntimeServiceAdapter")
        if self._grpc_stub is None:
            self._grpc_channel = create_insecure_channel(self._grpc_endpoint)
            self._grpc_stub = runtime_grpc.RuntimeServiceStub(self._grpc_channel)
        return self._grpc_stub

    def _build_metadata(self, trace_id: Optional[str] = None) -> list[tuple[str, str]]:
        metadata: list[tuple[str, str]] = []
        if self._auth_token:
            metadata.append(("authorization", f"Bearer {self._auth_token}"))
        if self._client_id:
            metadata.append(("x-client-id", self._client_id))
        if trace_id:
            metadata.append(("x-trace-id", trace_id))
        return metadata

    def close(self) -> None:
        """Close managed gRPC channel."""
        if self._grpc_channel is not None:
            self._grpc_channel.close()
            self._grpc_channel = None
            self._grpc_stub = None

    @staticmethod
    def _invoke_run_step_stream(
        stub: runtime_grpc.RuntimeServiceStub,
        request: runtime_pb2.RunStepRequest,
        metadata: list[tuple[str, str]],
        timeout: float,
    ) -> list[runtime_pb2.StepUpdate]:
        def _request_iter():
            yield request

        return list(stub.RunStep(_request_iter(), metadata=metadata, timeout=timeout))

    @staticmethod
    def _sop_step_to_proto(step: "SopStep") -> runtime_pb2.SopStepMessage:
        outputs = getattr(step, "outputs", None)
        schema: str = ""
        if outputs is not None:
            raw_schema = getattr(outputs, "schema", None)
            if not raw_schema and hasattr(outputs, "schema_file"):
                raw_schema = getattr(outputs, "schema_file")
            schema = str(raw_schema) if raw_schema else ""
        return runtime_pb2.SopStepMessage(
            id=step.id,
            role=step.role,
            task=step.task,
            outputs=runtime_pb2.StepOutputSpecMessage(schema=schema),
            depends_on=list(getattr(step, "depends_on", [])),
            condition=getattr(step, "condition", "") or "",
            lock=getattr(step, "lock", "") or "",
            priority=getattr(step, "priority", 0),
        )

