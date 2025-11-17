from __future__ import annotations

import copy
import uuid
from dataclasses import dataclass
from typing import Any, Callable, Optional

from forge.events.stream import EventStream, EventStreamSubscriber
from forge.events.event import Event
from forge.events import EventSource
from forge.runtime import runtime_orchestrator
from forge.utils.async_utils import call_async_from_sync, GENERAL_TIMEOUT
from forge.core.config import ForgeConfig


@dataclass
class DelegateRuntimeHandle:
    """Represents an acquired delegate runtime + stream bridge."""

    session_id: str
    acquire_result: Any
    event_stream: EventStream
    bridge: "DelegateEventBridge | None"
    released: bool = False

    def release(self) -> None:
        if self.released:
            return
        self.released = True
        if self.bridge:
            self.bridge.close()
        try:
            self.event_stream.close()
        finally:
            runtime_orchestrator.release(self.acquire_result)


class DelegateEventBridge:
    """Mirrors delegate event stream traffic onto the parent stream."""

    def __init__(
        self,
        parent_stream: EventStream,
        delegate_stream: EventStream,
        delegate_sid: str,
    ) -> None:
        self._parent = parent_stream
        self._delegate = delegate_stream
        self._delegate_sid = delegate_sid
        self._callback_id = f"delegate-bridge-{delegate_sid}"
        delegate_stream.subscribe(
            EventStreamSubscriber.SERVER,
            self._forward_event,
            self._callback_id,
        )

    def close(self) -> None:
        try:
            self._delegate.unsubscribe(
                EventStreamSubscriber.SERVER, self._callback_id
            )
        except Exception:
            pass

    def _forward_event(self, event: Event) -> None:
        cloned = copy.deepcopy(event)
        cloned.id = Event.INVALID_ID
        original_metadata = getattr(cloned, "metadata", None)
        metadata: dict[str, Any] = (
            dict(original_metadata) if isinstance(original_metadata, dict) else {}
        )
        metadata["delegate_sid"] = self._delegate_sid
        setattr(cloned, "metadata", metadata)
        source = getattr(cloned, "source", None) or EventSource.AGENT
        self._parent.add_event(cloned, source)


class DelegateRuntimeProvider:
    """Acquires dedicated runtimes + event streams for delegate controllers."""

    def __init__(
        self,
        *,
        config: ForgeConfig,
        llm_registry,
        file_store,
        parent_event_stream: EventStream,
        git_provider_tokens,
        env_vars: dict[str, str],
        user_id: str | None,
        selected_repository: str | None,
        selected_branch: str | None,
        base_session_id: str,
    ) -> None:
        self._config = config
        self._llm_registry = llm_registry
        self._file_store = file_store
        self._parent_stream = parent_event_stream
        self._git_provider_tokens = git_provider_tokens
        self._base_env_vars = env_vars
        self._user_id = user_id
        self._selected_repository = selected_repository
        self._selected_branch = selected_branch
        self._base_session_id = base_session_id

    def acquire(self, agent) -> DelegateRuntimeHandle:
        """Acquire a runtime + bridged event stream for a delegate agent."""

        session_id = f"{self._base_session_id}-dl-{uuid.uuid4().hex[:8]}"
        delegate_stream = EventStream(session_id, self._file_store, self._user_id)
        repo_initializer = self._build_repo_initializer()

        acquire_result = runtime_orchestrator.acquire(
            self._config,
            self._llm_registry,
            session_id=session_id,
            agent=agent,
            headless_mode=False,
            git_provider_tokens=self._git_provider_tokens,
            repo_initializer=repo_initializer,
            event_stream=delegate_stream,
            env_vars=dict(self._base_env_vars),
            user_id=self._user_id,
        )
        call_async_from_sync(acquire_result.runtime.connect, GENERAL_TIMEOUT)

        bridge = DelegateEventBridge(
            self._parent_stream, delegate_stream, session_id
        )

        return DelegateRuntimeHandle(
            session_id=session_id,
            acquire_result=acquire_result,
            event_stream=delegate_stream,
            bridge=bridge,
        )

    def _build_repo_initializer(self) -> Optional[Callable]:
        if not self._selected_repository:
            return None

        def _initializer(runtime) -> str | None:
            from forge.core.setup import initialize_repository_for_runtime

            return initialize_repository_for_runtime(
                runtime,
                immutable_provider_tokens=self._git_provider_tokens,
                selected_repository=self._selected_repository,
                selected_branch=self._selected_branch,
            )

        return _initializer

