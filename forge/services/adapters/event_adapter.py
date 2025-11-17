"""Adapter for EventService that bridges service contracts with EventStream."""

from __future__ import annotations

import json
import logging
import os
from typing import TYPE_CHECKING, Any, Callable, Optional

import grpc

from .grpc_utils import create_insecure_channel
from forge.services.event_service import EventServiceServer
from forge.services.generated import event_service_pb2 as event_pb2
from forge.services.generated import event_service_pb2_grpc as event_grpc

if TYPE_CHECKING:
    from forge.events.stream import EventStream
    from forge.storage.files import FileStore as FileStoreType


class EventServiceAdapter:
    """Adapter that wraps EventServiceServer for use in monolith or as gRPC service.

    This adapter provides a thin layer that can switch between:
    - In-process: Direct EventStream access
    - gRPC: Network-based service calls (future)

    The adapter maintains compatibility with existing monolith code while
    enabling a gradual migration to service-based architecture.
    """

    def __init__(
        self,
        file_store_factory: Callable[[Optional[str]], "FileStoreType"],
        use_grpc: bool = False,
        grpc_endpoint: Optional[str] = None,
        *,
        grpc_timeout_seconds: float = 10.0,
        auth_token: Optional[str] = None,
        client_id: Optional[str] = None,
    ) -> None:
        """Initialize the event service adapter.

        Args:
            file_store_factory: Factory function that creates FileStore instances
            use_grpc: If True, use gRPC client (future). If False, use in-process server.
            grpc_endpoint: gRPC server endpoint (required if use_grpc=True)

        """
        self._use_grpc = use_grpc
        self._grpc_endpoint = grpc_endpoint
        self._file_store_factory = file_store_factory
        self._in_process_server: Optional[EventServiceServer] = None
        self._grpc_channel: Optional[grpc.Channel] = None
        self._grpc_stub: Optional[event_grpc.EventServiceStub] = None
        self._grpc_timeout = grpc_timeout_seconds
        self._logger = logging.getLogger(__name__)
        self._client_id = client_id or os.getenv("FORGE_SERVICE_CLIENT_ID", "forge-monolith")
        self._auth_token = auth_token or os.getenv("FORGE_EVENT_SERVICE_TOKEN")

        if not use_grpc:
            self._in_process_server = EventServiceServer(file_store_factory)

    # ------------------------------------------------------------------
    # Session management
    # ------------------------------------------------------------------
    def start_session(
        self,
        session_id: Optional[str] = None,
        user_id: Optional[str] = None,
        repository: Optional[str] = None,
        branch: Optional[str] = None,
        labels: Optional[dict[str, str]] = None,
    ) -> dict[str, Any]:
        """Start a new session and return session info.

        Args:
            user_id: Optional user ID
            repository: Optional repository name
            branch: Optional branch name
            labels: Optional session labels

        Returns:
            Dictionary with session_id and other metadata

        """
        if self._use_grpc:
            return self._start_session_grpc(
                session_id=session_id,
                user_id=user_id,
                repository=repository,
                branch=branch,
                labels=labels,
            )
        return self._start_session_in_process(
            session_id=session_id,
            user_id=user_id,
            repository=repository,
            branch=branch,
            labels=labels,
        )

    def _start_session_grpc(
        self,
        *,
        session_id: Optional[str],
        user_id: Optional[str],
        repository: Optional[str],
        branch: Optional[str],
        labels: Optional[dict[str, str]],
    ) -> dict[str, Any]:
        stub = self._require_grpc_stub()
        grpc_request = self._build_start_session_request(
            session_id=session_id,
            user_id=user_id,
            repository=repository,
            branch=branch,
            labels=labels,
        )
        metadata = self._build_metadata()
        self._logger.debug(
            "EventService.StartSession(session_id=%s, metadata=%s)", session_id, metadata
        )
        response = stub.StartSession(
            grpc_request, timeout=self._grpc_timeout, metadata=metadata
        )
        return self._serialize_grpc_session_response(response, labels)

    def _build_start_session_request(
        self,
        *,
        session_id: Optional[str],
        user_id: Optional[str],
        repository: Optional[str],
        branch: Optional[str],
        labels: Optional[dict[str, str]],
    ) -> event_pb2.StartSessionRequest:
        grpc_request = event_pb2.StartSessionRequest(
            user_id=user_id or "",
            repository=repository or "",
            branch=branch or "",
            session_id=session_id or "",
        )
        if labels:
            grpc_request.labels.update(labels)
        return grpc_request

    @staticmethod
    def _serialize_grpc_session_response(
        response: Any, labels: Optional[dict[str, str]]
    ) -> dict[str, Any]:
        response_labels = dict(response.labels)
        if not response_labels and labels:
            response_labels = dict(labels)
        return {
            "session_id": response.session_id,
            "user_id": response.user_id,
            "repository": response.repository,
            "branch": response.branch,
            "labels": response_labels,
        }

    def _start_session_in_process(
        self,
        *,
        session_id: Optional[str],
        user_id: Optional[str],
        repository: Optional[str],
        branch: Optional[str],
        labels: Optional[dict[str, str]],
    ) -> dict[str, Any]:
        if self._in_process_server is None:
            raise RuntimeError("In-process server not initialized")
        from forge.services.event_service import StartSessionRequest

        request = StartSessionRequest(
            session_id=session_id,
            user_id=user_id,
            repository=repository,
            branch=branch,
            labels=labels or {},
        )
        session_info = self._in_process_server.start_session(request)
        return {
            "session_id": session_info.session_id,
            "user_id": session_info.user_id,
            "repository": session_info.repository,
            "branch": session_info.branch,
            "labels": session_info.labels,
        }

    def get_session_info(self, session_id: str) -> dict[str, Any]:
        """Retrieve session metadata for the specified session.

        Args:
            session_id: Session identifier

        Returns:
            Dictionary representation of SessionInfo

        """
        if self._use_grpc:
            raise NotImplementedError("gRPC client not yet implemented")
        if self._in_process_server is None:
            raise RuntimeError("In-process server not initialized")
        info = self._in_process_server.get_session_info(session_id)
        return {
            "session_id": info.session_id,
            "user_id": info.user_id,
            "repository": info.repository,
            "branch": info.branch,
            "labels": info.labels,
        }

    def get_event_stream(self, session_id: str) -> "EventStream":
        """Get the EventStream instance for a session (in-process only).

        Args:
            session_id: Session ID

        Returns:
            EventStream instance

        Raises:
            RuntimeError: If using gRPC mode or session not found

        """
        if self._use_grpc:
            raise RuntimeError("EventStream access not available in gRPC mode")
        if self._in_process_server is None:
            raise RuntimeError("In-process server not initialized")
        return self._in_process_server._get_stream(session_id)

    # ------------------------------------------------------------------
    # Event publishing
    # ------------------------------------------------------------------
    def publish_event(self, session_id: str, event_dict: dict) -> None:
        """Publish an event to a session.

        Args:
            session_id: Session ID
            event_dict: Event dictionary (canonical event_to_dict format)

        """
        if self._use_grpc:
            self._publish_event_grpc(session_id, event_dict)
            return
        self._publish_event_in_process(session_id, event_dict)

    def _publish_event_grpc(self, session_id: str, event_dict: dict) -> None:
        stub = self._require_grpc_stub()
        payload = json.dumps(event_dict).encode("utf-8")
        event_type = self._extract_event_type(event_dict)
        grpc_envelope = self._build_grpc_envelope(
            session_id=session_id,
            event_dict=event_dict,
            event_type=event_type,
            payload=payload,
        )
        metadata_headers = self._build_metadata(
            trace_id=grpc_envelope.trace_id if grpc_envelope.trace_id else None
        )
        self._logger.debug(
            "EventService.PublishEvent(session_id=%s, event_type=%s, metadata=%s)",
            session_id,
            event_type,
            metadata_headers,
        )
        stub.PublishEvent(
            event_pb2.PublishEventRequest(event=grpc_envelope),
            timeout=self._grpc_timeout,
            metadata=metadata_headers,
        )

    def _build_grpc_envelope(
        self,
        *,
        session_id: str,
        event_dict: dict,
        event_type: str,
        payload: bytes,
    ) -> event_pb2.EventEnvelope:
        grpc_envelope = event_pb2.EventEnvelope(
            session_id=session_id,
            event_type=event_type,
            payload=payload,
        )
        self._apply_event_id(grpc_envelope, event_dict.get("id"))
        trace_id = event_dict.get("trace_id") or event_dict.get("metadata", {}).get("trace_id")
        if trace_id:
            grpc_envelope.trace_id = trace_id
        metadata = event_dict.get("metadata") or {}
        for key, value in metadata.items():
            if value is None:
                continue
            grpc_envelope.metadata[str(key)] = str(value)
        return grpc_envelope

    def _apply_event_id(
        self, grpc_envelope: event_pb2.EventEnvelope, event_id: int | str | None
    ) -> None:
        if isinstance(event_id, int):
            grpc_envelope.event_id = event_id
        elif isinstance(event_id, str):
            try:
                grpc_envelope.event_id = int(event_id)
            except ValueError:
                pass

    def _publish_event_in_process(self, session_id: str, event_dict: dict) -> None:
        if self._in_process_server is None:
            raise RuntimeError("In-process server not initialized")
        from forge.services.event_service import EventEnvelope, PublishEventRequest

        payload = json.dumps(event_dict).encode("utf-8")
        event_type = self._extract_event_type(event_dict)
        envelope = EventEnvelope(
            session_id=session_id,
            event_id=event_dict.get("id"),
            event_type=event_type,
            payload=payload,
            trace_id=event_dict.get("trace_id") or event_dict.get("metadata", {}).get("trace_id"),
        )
        request = PublishEventRequest(event=envelope)
        self._in_process_server.publish_event(request)

    @staticmethod
    def _extract_event_type(event_dict: dict) -> str:
        """Derive event type from canonical event dict irrespective of shape."""

        event_type = EventServiceAdapter._extract_type_from_field(
            event_dict, field_name="action"
        )
        if event_type:
            return event_type

        event_type = EventServiceAdapter._extract_type_from_field(
            event_dict, field_name="observation"
        )
        return event_type or "unknown"

    @staticmethod
    def _extract_type_from_field(event_dict: dict, *, field_name: str) -> str | None:
        field_value = event_dict.get(field_name)
        if isinstance(field_value, dict):
            event_type = field_value.get("type")
            if event_type:
                return str(event_type)
        if field_value is not None and hasattr(field_value, "value"):
            return str(field_value.value)
        if isinstance(field_value, str):
            return field_value
        return None

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------
    def _require_grpc_stub(self) -> event_grpc.EventServiceStub:
        if not self._use_grpc:
            raise RuntimeError("gRPC stub requested while in in-process mode")
        if not self._grpc_endpoint:
            raise RuntimeError("gRPC endpoint not configured for EventServiceAdapter")
        if self._grpc_stub is None:
            self._grpc_channel = create_insecure_channel(self._grpc_endpoint)
            self._grpc_stub = event_grpc.EventServiceStub(self._grpc_channel)
        return self._grpc_stub

    def _build_metadata(self, *, trace_id: Optional[str] = None) -> list[tuple[str, str]]:
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

