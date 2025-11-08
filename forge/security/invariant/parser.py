"""Utilities for converting Forge actions/observations into Invariant traces."""

from __future__ import annotations

from pydantic import BaseModel, Field

from forge.core.logger import forge_logger as logger
from forge.events.action import (
    Action,
    ChangeAgentStateAction,
    MessageAction,
    NullAction,
)
from forge.events.event import EventSource
from forge.events.observation import (
    AgentStateChangedObservation,
    NullObservation,
    Observation,
)
from forge.events.serialization.event import event_to_dict
from forge.security.invariant.nodes import Function, Message, ToolCall, ToolOutput

TraceElement = Message | ToolCall | ToolOutput | Function


def get_next_id(trace: list[TraceElement]) -> str:
    """Return smallest positive string ID not yet used by ToolCall elements."""
    used_ids = [el.id for el in trace if isinstance(el, ToolCall)]
    return next((str(i) for i in range(1, len(used_ids) + 2) if str(i) not in used_ids), "1")


def get_last_id(trace: list[TraceElement]) -> str | None:
    """Return most recent ToolCall id in trace (or None if absent)."""
    return next((el.id for el in reversed(trace) if isinstance(el, ToolCall)), None)


def parse_action(trace: list[TraceElement], action: Action) -> list[TraceElement]:
    """Convert Forge Action into invariant trace elements (messages/tool calls)."""
    next_id = get_next_id(trace)
    inv_trace: list[TraceElement] = []
    if isinstance(action, MessageAction):
        if action.source == EventSource.USER:
            inv_trace.append(Message(role="user", content=action.content))
        else:
            inv_trace.append(Message(role="assistant", content=action.content))
    elif isinstance(action, (NullAction, ChangeAgentStateAction)):
        pass
    elif hasattr(action, "action") and action.action is not None:
        event_dict = event_to_dict(action)
        args = event_dict.get("args", {})
        thought = args.pop("thought", None)
        function = Function(name=action.action, arguments=args)
        if thought is not None:
            inv_trace.append(Message(role="assistant", content=thought))
        inv_trace.append(ToolCall(id=next_id, type="function", function=function))
    else:
        logger.error("Unknown action type: %s", type(action))
    return inv_trace


def parse_observation(trace: list[TraceElement], obs: Observation) -> list[TraceElement]:
    """Parse an Observation into Invariant trace elements.
    
    Args:
        trace: Current trace elements
        obs: Observation to parse
        
    Returns:
        List of trace elements representing the observation

    """
    last_id = get_last_id(trace)
    if isinstance(obs, (NullObservation, AgentStateChangedObservation)):
        return []
    if hasattr(obs, "content") and obs.content is not None:
        return [ToolOutput(role="tool", content=obs.content, tool_call_id=last_id)]
    logger.error("Unknown observation type: %s", type(obs))
    return []


def parse_element(trace: list[TraceElement], element: Action | Observation) -> list[TraceElement]:
    """Parse an Action or Observation into trace elements.
    
    Args:
        trace: Current trace elements
        element: Action or Observation to parse
        
    Returns:
        List of trace elements

    """
    if isinstance(element, Action):
        return parse_action(trace, element)
    return parse_observation(trace, element)


def parse_trace(trace: list[tuple[Action, Observation]]) -> list[TraceElement]:
    """Parse a complete trace of action-observation pairs into Invariant format.
    
    Args:
        trace: List of (action, observation) tuples
        
    Returns:
        List of Invariant trace elements

    """
    inv_trace: list[TraceElement] = []
    for action, obs in trace:
        inv_trace.extend(parse_action(inv_trace, action))
        inv_trace.extend(parse_observation(inv_trace, obs))
    return inv_trace


class InvariantState(BaseModel):
    """State container for Invariant security analysis trace.
    
    Maintains a trace of events (messages, tool calls, tool outputs)
    for security policy evaluation.
    """
    trace: list[TraceElement] = Field(default_factory=list)

    def add_action(self, action: Action) -> None:
        """Add an action to the trace.
        
        Args:
            action: Action to add

        """
        self.trace.extend(parse_action(self.trace, action))

    def add_observation(self, obs: Observation) -> None:
        """Add an observation to the trace.
        
        Args:
            obs: Observation to add

        """
        self.trace.extend(parse_observation(self.trace, obs))

    def concatenate(self, other: InvariantState) -> None:
        """Concatenate another InvariantState's trace to this one.
        
        Args:
            other: InvariantState to concatenate

        """
        self.trace.extend(other.trace)
