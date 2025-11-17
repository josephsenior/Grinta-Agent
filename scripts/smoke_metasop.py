"""MetaSOP smoke test to exercise runtime/event adapters."""

from __future__ import annotations

import argparse
import asyncio
import logging
import os
from concurrent import futures
from contextlib import ExitStack, suppress
from dataclasses import dataclass
from typing import TYPE_CHECKING

import grpc

from forge.events.serialization.event import event_to_dict
from forge.events.stream import EventStreamSubscriber
from forge.metasop.models import SopStep, StepOutputSpec

if TYPE_CHECKING:  # pragma: no cover
    from forge.services.event_service.service import EventServiceServer
    from forge.services.runtime_service.service import RuntimeServiceServer


@dataclass
class GrpcServers:
    event_backend: "EventServiceServer"
    runtime_backend: "RuntimeServiceServer"
    event_server: grpc.Server
    runtime_server: grpc.Server
    event_endpoint: str
    runtime_endpoint: str


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="MetaSOP smoke test")
    parser.add_argument(
        "--grpc",
        action="store_true",
        help="Run adapters against in-process gRPC services instead of direct in-process mode.",
    )
    return parser.parse_args()


def start_inprocess_grpc_servers(shared_module) -> GrpcServers:
    from forge.services.event_service.grpc_server import EventServiceGrpcServicer
    from forge.services.event_service.service import EventServiceServer
    from forge.services.generated import event_service_pb2_grpc as event_grpc
    from forge.services.generated import runtime_service_pb2_grpc as runtime_grpc
    from forge.services.runtime_service.grpc_server import RuntimeServiceGrpcServicer
    from forge.services.runtime_service.service import RuntimeServiceServer

    file_store = shared_module.file_store

    event_backend = EventServiceServer(lambda _uid: file_store)
    event_server = grpc.server(futures.ThreadPoolExecutor(max_workers=4))
    event_grpc.add_EventServiceServicer_to_server(EventServiceGrpcServicer(event_backend), event_server)
    event_port = event_server.add_insecure_port("127.0.0.1:0")
    event_server.start()

    def event_stream_provider(session_id: str):
        return event_backend._get_stream(session_id)  # pragma: no cover - integration only

    runtime_backend = RuntimeServiceServer(
        shared_module._orchestrator_factory,  # type: ignore[attr-defined]
        event_stream_provider=event_stream_provider,
    )
    runtime_server = grpc.server(futures.ThreadPoolExecutor(max_workers=4))
    runtime_grpc.add_RuntimeServiceServicer_to_server(
        RuntimeServiceGrpcServicer(runtime_backend), runtime_server
    )
    runtime_port = runtime_server.add_insecure_port("127.0.0.1:0")
    runtime_server.start()

    return GrpcServers(
        event_backend=event_backend,
        runtime_backend=runtime_backend,
        event_server=event_server,
        runtime_server=runtime_server,
        event_endpoint=f"127.0.0.1:{event_port}",
        runtime_endpoint=f"127.0.0.1:{runtime_port}",
    )


def stop_inprocess_grpc_servers(servers: GrpcServers) -> None:
    servers.event_server.stop(0).wait()
    servers.runtime_server.stop(0).wait()


async def run_smoke_test(event_adapter, runtime_adapter, event_backend=None) -> None:
    conversation_id = "metasop-smoke"
    user_id = "smoke-user"

    session_info = event_adapter.start_session(
        session_id=conversation_id,
        user_id=user_id,
        labels={"test": "smoke"},
    )

    if event_backend is not None:
        stream = event_backend._get_stream(session_info["session_id"])  # pragma: no cover
    else:
        stream = event_adapter.get_event_stream(session_info["session_id"])

    events: list[dict] = []

    def callback(event) -> None:
        events.append(event_to_dict(event))

    stream.subscribe(EventStreamSubscriber.TEST, callback, "smoke-listener")

    runtime_id = None
    try:
        runtime_handle = runtime_adapter.create_runtime(
            session_id=conversation_id,
            repo_root=None,
            user_request="smoke test request",
        )
        runtime_id = runtime_handle["runtime_id"]

        step = SopStep(
            id="smoke-step",
            role="engineer",
            task="perform smoke test",
            outputs=StepOutputSpec(schema=""),
        )

        result = await runtime_adapter.run_step(
            runtime_id,
            step,
            max_retries=1,
        )
        logging.info("Run step result: %s", result)
        print("Run step result:", result)
    finally:
        if runtime_id:
            with suppress(Exception):
                runtime_adapter.close_runtime(runtime_id)
        stream.unsubscribe(EventStreamSubscriber.TEST, "smoke-listener")

    logging.info("Captured %d events", len(events))
    print("Captured events:", len(events))
    for evt in events:
        logging.debug("Event: %s", evt)
        print("Event:", evt)


def main() -> None:
    args = parse_args()
    logging.basicConfig(level=logging.INFO)

    if args.grpc:
        os.environ.setdefault("FORGE_EVENT_SERVICE_GRPC", "true")
        os.environ.setdefault("FORGE_RUNTIME_SERVICE_GRPC", "true")
        os.environ.setdefault("FORGE_EVENT_SERVICE_ENDPOINT", "localhost:0")
        os.environ.setdefault("FORGE_RUNTIME_SERVICE_ENDPOINT", "localhost:0")

    from forge.server import shared

    event_adapter = shared.get_event_service_adapter()
    runtime_adapter = shared.get_runtime_service_adapter()

    servers = None
    with ExitStack() as stack:
        if args.grpc:
            servers = start_inprocess_grpc_servers(shared)
            event_close = getattr(event_adapter, "close", None)
            if callable(event_close):
                event_close()
            runtime_close = getattr(runtime_adapter, "close", None)
            if callable(runtime_close):
                runtime_close()
            event_adapter._grpc_endpoint = servers.event_endpoint  # type: ignore[attr-defined]
            runtime_adapter._grpc_endpoint = servers.runtime_endpoint  # type: ignore[attr-defined]
            os.environ["FORGE_EVENT_SERVICE_ENDPOINT"] = servers.event_endpoint
            os.environ["FORGE_RUNTIME_SERVICE_ENDPOINT"] = servers.runtime_endpoint
            stack.callback(stop_inprocess_grpc_servers, servers)

        asyncio.run(
            run_smoke_test(
                event_adapter,
                runtime_adapter,
                event_backend=servers.event_backend if servers else None,
            )
        )


if __name__ == "__main__":
    main()