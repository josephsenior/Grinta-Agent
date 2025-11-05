from __future__ import annotations

import asyncio
from typing import TYPE_CHECKING

from openhands.events.stream import EventStream
from openhands.llm.llm_registry import LLMRegistry
from openhands.runtime import get_runtime_cls
from openhands.utils.async_utils import call_sync_from_async

if TYPE_CHECKING:
    from openhands.core.config import OpenHandsConfig
    from openhands.runtime.base import Runtime
    from openhands.storage.files import FileStore


class ServerConversation:
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
        config: OpenHandsConfig,
        user_id: str | None,
        event_stream: EventStream | None = None,
        runtime: Runtime | None = None,
    ) -> None:
        self.sid = sid
        self.config = config
        self.file_store = file_store
        self.user_id = user_id
        if event_stream is None:
            event_stream = EventStream(sid, file_store, user_id)
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
                logger.warning(f"LLM config not ready, runtime will start without agent capability: {e}")
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
        if not self._attach_to_existing:
            await self.runtime.connect()

    async def disconnect(self) -> None:
        if self._attach_to_existing:
            return
        if self.event_stream:
            self.event_stream.close()
        asyncio.create_task(call_sync_from_async(self.runtime.close))
