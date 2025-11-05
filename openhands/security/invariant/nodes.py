from __future__ import annotations

from typing import TYPE_CHECKING, Any

from pydantic import BaseModel, Field
from pydantic.dataclasses import dataclass

if TYPE_CHECKING:
    from collections.abc import Iterable


@dataclass
class LLM:
    vendor: str
    model: str


class Event(BaseModel):
    metadata: dict[str, Any] | None = Field(
        default_factory=dict,
        description="Metadata associated with the event",
    )


class Function(BaseModel):
    name: str
    arguments: dict[str, Any]


class ToolCall(Event):
    id: str
    type: str
    function: Function


class Message(Event):
    role: str
    content: str | None
    tool_calls: list[ToolCall] | None = None

    def __rich_repr__(self) -> Iterable[Any | tuple[Any] | tuple[str, Any] | tuple[str, Any, Any]]:
        yield ("role", self.role)
        yield ("content", self.content)
        yield ("tool_calls", self.tool_calls)


class ToolOutput(Event):
    role: str
    content: str
    tool_call_id: str | None = None
    _tool_call: ToolCall | None = None
