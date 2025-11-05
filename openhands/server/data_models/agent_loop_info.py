from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from openhands.core.schema.agent import AgentState
from openhands.storage.data_models.conversation_status import ConversationStatus

if TYPE_CHECKING:
    from openhands.events.event_store_abc import EventStoreABC
    from openhands.runtime.runtime_status import RuntimeStatus


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
