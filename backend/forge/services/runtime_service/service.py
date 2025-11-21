from __future__ import annotations

import asyncio
import json
import threading
import time
import uuid
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, AsyncIterator, Callable, Dict, Optional

from forge.events.action import MessageAction
from forge.events.event import EventSource
from forge.events.stream import EventStream
from forge.metasop.models import Artifact, SopStep

if TYPE_CHECKING:  # pragma: no cover
    from forge.metasop.orchestrator import MetaSOPOrchestrator

try:  # pragma: no cover - optional dependency
    from prometheus_client import Counter, Histogram
except Exception:  # pragma: no cover
    Counter = Histogram = None  # type: ignore


_RUNTIME_RPC_TOTAL = None
_RUNTIME_RPC_FAILURES = None
_RUNTIME_RPC_DURATION = None

if Counter is not None:  # pragma: no cover - registration only
    _RUNTIME_RPC_TOTAL = Counter(
        "metasop_runtime_rpc_total",
        "Total RuntimeService RPC invocations",
        labelnames=("rpc",),
    )
    _RUNTIME_RPC_FAILURES = Counter(
        "metasop_runtime_rpc_failures_total",
        "Failed RuntimeService RPC invocations",
        labelnames=("rpc",),
    )
    _RUNTIME_RPC_DURATION = Histogram(
        "metasop_runtime_rpc_duration_seconds",
        "RuntimeService RPC latency in seconds",
        labelnames=("rpc",),
        buckets=(0.05, 0.1, 0.25, 0.5, 1, 2.5, 5, 10, float("inf")),
    )


def _record_runtime_rpc(rpc: str, success: bool, duration: float) -> None:
    if (
        _RUNTIME_RPC_TOTAL is None
        or _RUNTIME_RPC_FAILURES is None
        or _RUNTIME_RPC_DURATION is None
    ):
        return
    _RUNTIME_RPC_TOTAL.labels(rpc=rpc).inc()
    if not success:
        _RUNTIME_RPC_FAILURES.labels(rpc=rpc).inc()
    _RUNTIME_RPC_DURATION.labels(rpc=rpc).observe(duration)


@dataclass
class RuntimeHandle:
    runtime_id: str
    session_id: str
    repository: Optional[str] = None
    branch: Optional[str] = None


@dataclass
class CreateRuntimeRequest:
    session_id: str
    repository: Optional[str] = None
    branch: Optional[str] = None
    repo_root: Optional[str] = None
    user_request: str = "runtime-service"


@dataclass
class CloseRuntimeRequest:
    runtime_id: str
    wait: bool = False


@dataclass
class RunStepRequest:
    runtime_id: str
    step: SopStep
    max_retries: int = 2
    trace_id: Optional[str] = None


@dataclass
class StepUpdate:
    runtime_id: str
    step_id: str
    update_type: str
    status: str
    metadata: Dict[str, str] = field(default_factory=dict)


@dataclass
class _RuntimeState:
    orchestrator: "MetaSOPOrchestrator"
    context: Optional[object]
    done: Dict[str, Artifact] = field(default_factory=dict)
    event_sink: Optional[Callable[[dict], None]] = None


class RuntimeServiceServer:
    """In-process implementation of the RuntimeService contract."""

    def __init__(
        self,
        orchestrator_factory: Callable[[], "MetaSOPOrchestrator"],
        event_stream_provider: Optional[Callable[[str], EventStream]] = None,
    ) -> None:
        self._orchestrator_factory = orchestrator_factory
        self._event_stream_provider = event_stream_provider
        self._runtimes: Dict[str, _RuntimeState] = {}
        self._lock = threading.Lock()

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------
    def create_runtime(self, request: CreateRuntimeRequest) -> RuntimeHandle:
        start = time.perf_counter()
        success = False
        try:
            runtime_id = str(uuid.uuid4())
            orchestrator = self._orchestrator_factory()

            context = orchestrator.context_manager.initialize_orchestration_context(
                request.user_request, request.repo_root
            )

            event_sink = None
            if self._event_stream_provider:
                try:
                    stream = self._event_stream_provider(request.session_id)

                    def sink(event: dict[str, str]) -> None:
                        payload = json.dumps(event)
                        message = MessageAction(content=payload, wait_for_response=False)
                        stream.add_event(message, EventSource.ENVIRONMENT)

                    orchestrator.runtime_adapter.register_event_sink(sink)
                    event_sink = sink
                except Exception:
                    event_sink = None

            with self._lock:
                self._runtimes[runtime_id] = _RuntimeState(
                    orchestrator=orchestrator,
                    context=context,
                    done={},
                    event_sink=event_sink,
                )

            success = True
            return RuntimeHandle(
                runtime_id=runtime_id,
                session_id=request.session_id,
                repository=request.repository,
                branch=request.branch,
            )
        finally:
            duration = time.perf_counter() - start
            _record_runtime_rpc("CreateRuntime", success, duration)

    def close_runtime(self, request: CloseRuntimeRequest) -> None:
        start = time.perf_counter()
        success = False
        try:
            with self._lock:
                if request.runtime_id in self._runtimes:
                    state = self._runtimes.pop(request.runtime_id)
                    state.orchestrator.runtime_adapter.clear_event_sinks()
            success = True
        finally:
            duration = time.perf_counter() - start
            _record_runtime_rpc("CloseRuntime", success, duration)

    # ------------------------------------------------------------------
    # Step execution
    # ------------------------------------------------------------------
    async def run_step(self, request: RunStepRequest) -> AsyncIterator[StepUpdate]:
        start = time.perf_counter()
        success = False
        state = self._get_runtime(request.runtime_id)
        orchestrator = state.orchestrator
        ctx = state.context
        if ctx is None:
            raise RuntimeError("Runtime context not initialised")

        yield StepUpdate(
            runtime_id=request.runtime_id,
            step_id=request.step.id,
            update_type="progress",
            status="started",
        )

        try:
            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(  # type: ignore[arg-type]
                None,
                self._execute_sync_step,
                state,
                request,
            )

            yield result
            success = result.update_type != "error"
        except Exception:
            duration = time.perf_counter() - start
            _record_runtime_rpc("RunStep", False, duration)
            raise
        else:
            duration = time.perf_counter() - start
            _record_runtime_rpc("RunStep", success, duration)

    def _execute_sync_step(
        self,
        state: _RuntimeState,
        request: RunStepRequest,
    ) -> StepUpdate:
        orchestrator = state.orchestrator
        ctx = state.context
        if ctx is None:
            raise RuntimeError("Runtime context not initialised")

        soft_budget = orchestrator.settings.token_budget_soft or 20_000
        hard_budget = orchestrator.settings.token_budget_hard or 50_000
        taxonomy_enabled = orchestrator.settings.enable_failure_taxonomy

        success, artifacts = orchestrator.step_execution.execute_step(
            request.step,
            ctx,
            state.done,
            soft_budget,
            hard_budget,
            0,
            taxonomy_enabled,
            orchestrator.context_manager.setup_retry_policy(request.max_retries),
            request.max_retries,
        )

        state.done.update(artifacts)

        metadata = {
            "success": str(success),
            "artifact_count": str(len(artifacts)),
        }
        if artifacts:
            first_artifact = next(iter(artifacts.values()))
            try:
                metadata["artifact_preview"] = json_preview(first_artifact)
            except Exception:  # pragma: no cover - defensive
                pass

        return StepUpdate(
            runtime_id=request.runtime_id,
            step_id=request.step.id,
            update_type="result" if success else "error",
            status="completed" if success else "failed",
            metadata=metadata,
        )

    def _get_runtime(self, runtime_id: str) -> _RuntimeState:
        with self._lock:
            if runtime_id not in self._runtimes:
                raise KeyError(f"Unknown runtime_id: {runtime_id}")
            return self._runtimes[runtime_id]

    def get_runtime_state(self, runtime_id: str) -> _RuntimeState:
        """Retrieve runtime state for in-process integrations."""
        return self._get_runtime(runtime_id)


def json_preview(artifact: Artifact) -> str:
    """Generate a compact string preview of an artifact's content."""

    content = getattr(artifact, "content", None)
    if content is None:
        return ""
    text = str(content)
    return text if len(text) <= 256 else f"{text[:253]}..."
