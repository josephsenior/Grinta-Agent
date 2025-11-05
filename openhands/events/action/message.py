from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import openhands
from openhands.core.schema import ActionType
from openhands.events.action.action import Action, ActionSecurityRisk


@dataclass
class MessageAction(Action):
    content: str
    file_urls: list[str] | None = None
    image_urls: list[str] | None = None
    wait_for_response: bool = False
    action: str = ActionType.MESSAGE
    security_risk: ActionSecurityRisk = ActionSecurityRisk.UNKNOWN

    @property
    def message(self) -> str:
        return self.content

    @property
    def images_urls(self) -> list[str] | None:
        return self.image_urls

    @images_urls.setter
    def images_urls(self, value: list[str] | None) -> None:
        self.image_urls = value

    def __str__(self) -> str:
        ret = f"**MessageAction** (source={self.source})\n"
        ret += f"CONTENT: {self.content}"
        if self.image_urls:
            for url in self.image_urls:
                ret += f"\nIMAGE_URL: {url}"
        if self.file_urls:
            for url in self.file_urls:
                ret += f"\nFILE_URL: {url}"
        return ret

    __test__ = False


@dataclass
class SystemMessageAction(Action):
    """System message for agent with system prompt and tools.

    This should be the first message in the event stream.
    """

    content: str
    tools: list[Any] | None = None
    openhands_version: str | None = openhands.__version__
    agent_class: str | None = None
    action: ActionType = ActionType.SYSTEM

    @property
    def message(self) -> str:
        return self.content

    def __str__(self) -> str:
        ret = f"**SystemMessageAction** (source={self.source})\n"
        ret += f"CONTENT: {self.content}"
        if self.tools:
            ret += f"\nTOOLS: {len(self.tools)} tools available"
        if self.agent_class:
            ret += f"\nAGENT_CLASS: {self.agent_class}"
        return ret

    __test__ = False


@dataclass
class StreamingChunkAction(Action):
    """Streaming chunk from LLM for real-time token display.

    Emitted during LLM streaming to show tokens as they arrive,
    providing instant feedback (ChatGPT/Cursor style).
    """

    chunk: str = ""  # The new token/chunk text
    accumulated: str = ""  # All text accumulated so far
    is_final: bool = False  # True when streaming is complete
    action: str = ActionType.STREAMING_CHUNK
    runnable: bool = False  # Not executable, just informational

    def __str__(self) -> str:
        status = "FINAL" if self.is_final else "STREAMING"
        char_count = len(self.accumulated)
        return f"**StreamingChunkAction** ({status}) - {char_count} chars"

    __test__ = False
