"""Server-side wrapper for conversations, linking runtimes and event streams."""

from __future__ import annotations

import asyncio
from typing import TYPE_CHECKING

from forge.llm.llm_registry import LLMRegistry
from forge.runtime import get_runtime_cls
from forge.utils.async_utils import call_sync_from_async
from forge.core.logger import forge_logger as logger
from forge.server.shared import event_service_adapter, get_event_service_adapter

if TYPE_CHECKING:
    from forge.core.config import ForgeConfig
    from forge.events.stream import EventStream
    from forge.runtime.base import Runtime
    from forge.storage.files import FileStore


class ServerConversation:
    """In-memory representation of a conversation session managed by server."""

    sid: str
    file_store: FileStore
    event_stream: EventStream
    runtime: Runtime
    user_id: str | None
    _attach_to_existing: bool = False

    def __init__(
        self,
        sid: str,
        file_store: FileStore,
        config: ForgeConfig,
        user_id: str | None,
        event_stream: EventStream | None = None,
        runtime: Runtime | None = None,
    ) -> None:
        """Initialize conversation state, optionally attaching to an existing runtime."""
        self.sid = sid
        self.config = config
        self.file_store = file_store
        self.user_id = user_id
        if event_stream is None:
            adapter = event_service_adapter or get_event_service_adapter()
            adapter.start_session(
                session_id=sid,
                user_id=user_id,
                labels={"source": "server_conversation"},
            )
            event_stream = adapter.get_event_stream(sid)
        self.event_stream = event_stream
        if runtime:
            self._attach_to_existing = True
        else:
            runtime_cls = get_runtime_cls(self.config.runtime)
            # Runtime can start WITHOUT valid LLM config
            # Agent (created later) is what actually needs LLM
            # This allows background runtime initialization for faster UX
            try:
                llm_registry = LLMRegistry(self.config)
            except Exception as e:
                # If LLM config invalid/missing, create empty registry
                # Runtime will work, agent creation will fail (expected)
                logger.warning(
                    f"LLM config not ready, runtime will start without agent capability: {e}"
                )
                llm_registry = LLMRegistry(self.config)  # Will use defaults

            runtime = runtime_cls(
                llm_registry=llm_registry,
                config=config,
                event_stream=self.event_stream,
                sid=self.sid,
                attach_to_existing=False,
                headless_mode=False,
            )
        self.runtime = runtime

    @property
    def security_analyzer(self):
        """Access security analyzer through runtime."""
        return self.runtime.security_analyzer

    async def connect(self) -> None:
        """Connect to runtime environment.

        Skipped if attaching to existing runtime.
        """
        if not self._attach_to_existing:
            await self.runtime.connect()

    async def disconnect(self) -> None:
        """Disconnect from runtime and clean up resources.

        Skipped if attached to existing runtime.
        """
        if self._attach_to_existing:
            return
        if self.event_stream:
            self.event_stream.close()
        asyncio.create_task(call_sync_from_async(self.runtime.close))
