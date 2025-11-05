from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from openhands.server.data_models.conversation_info import ConversationInfo

if TYPE_CHECKING:
    pass


@dataclass
class ConversationInfoResultSet:
    results: list[ConversationInfo] = field(default_factory=list)
    next_page_id: str | None = None
