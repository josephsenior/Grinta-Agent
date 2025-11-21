"""Data structures describing running agent loops and their endpoints."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from forge.core.schemas import AgentState
from forge.storage.data_models.conversation_status import ConversationStatus

if TYPE_CHECKING:
    from forge.events.event_store_abc import EventStoreABC
    from forge.runtime.runtime_status import RuntimeStatus


@dataclass
class AgentLoopInfo:
    """Information about an agent loop - the URL on which to locate it and the event store."""

    conversation_id: str
    url: str | None
    session_api_key: str | None
    event_store: EventStoreABC | None
    status: ConversationStatus = field(default=ConversationStatus.RUNNING)
    runtime_status: RuntimeStatus | None = None
    agent_state: AgentState | None = None
