import type { ForgeEvent } from "#/types/core/base";
import {
  isUserMessage,
  isStreamingChunkAction,
  isForgeAction,
} from "#/types/core/guards";

export interface MessageTurn {
  type: "user" | "agent";
  events: ForgeEvent[];
  startIndex: number;
  endIndex: number;
}

/**
 * Groups consecutive messages into "turns" for bolt.new-style rendering
 * 
 * A "turn" is:
 * - User message (single event)
 * - Agent response (multiple consecutive agent events grouped together)
 * 
 * This creates the conversational flow where:
 * - User says something → one bubble
 * - Agent responds with multiple actions → ONE grouped visual unit
 * 
 * Special handling for StreamingChunkAction:
 * - Multiple streaming chunks update THE SAME turn (not create new turns)
 * - This gives real-time token-by-token updates within one message
 */
export function groupMessagesIntoTurns(messages: ForgeEvent[]): MessageTurn[] {
  const turns: MessageTurn[] = [];
  let currentTurn: MessageTurn | null = null;

  messages.forEach((event, index) => {
    if (isUserMessage(event)) {
      currentTurn = finalizeCurrentTurn(turns, currentTurn);
      pushUserTurn(turns, event, index);
      return;
    }

    currentTurn = appendAgentEvent({
      currentTurn,
      event,
      index,
    });
  });

  finalizeCurrentTurn(turns, currentTurn);

  return turns;
}

/**
 * Check if a turn contains streaming content (used for animations)
 */
export function turnHasStreaming(turn: MessageTurn): boolean {
  return turn.events.some((event) => isStreamingChunkAction(event));
}

/**
 * Get the latest streaming content from a turn
 */
export function getTurnStreamingContent(turn: MessageTurn): string | null {
  const streamingEvents = turn.events.filter((event) => isStreamingChunkAction(event));
  if (streamingEvents.length === 0) return null;
  
  const lastStreaming = streamingEvents[streamingEvents.length - 1];
    if (typeof lastStreaming === "object" && lastStreaming !== null) {
    const ls = lastStreaming as unknown as Record<string, unknown>;
    const args = ls.args as Record<string, unknown> | undefined;
    return (args?.accumulated as string) || null;
  }
  return null;
}

function finalizeCurrentTurn(turns: MessageTurn[], currentTurn: MessageTurn | null) {
  if (currentTurn) {
    turns.push(currentTurn);
  }
  return null;
}

function pushUserTurn(turns: MessageTurn[], event: ForgeEvent, index: number) {
  turns.push({
    type: "user",
    events: [event],
    startIndex: index,
    endIndex: index,
  });
}

function appendAgentEvent({
  currentTurn,
  event,
  index,
}: {
  currentTurn: MessageTurn | null;
  event: ForgeEvent;
  index: number;
}) {
  if (!currentTurn || currentTurn.type !== "agent") {
    return createAgentTurn(event, index);
  }

  currentTurn.events.push(event);
  currentTurn.endIndex = index;

  if (isStreamingChunkAction(event)) {
    mergeStreamingChunkIntoTurn(currentTurn, event);
  }

  return currentTurn;
}

function createAgentTurn(event: ForgeEvent, index: number): MessageTurn {
  const turn: MessageTurn = {
    type: "agent",
    events: [event],
    startIndex: index,
    endIndex: index,
  };

  if (isStreamingChunkAction(event)) {
    mergeStreamingChunkIntoTurn(turn, event);
  }

  return turn;
}

function mergeStreamingChunkIntoTurn(turn: MessageTurn, streamingEvent: ForgeEvent) {
  const lastAssistantIndex = findLastAssistantMessage(turn.events);
  if (lastAssistantIndex === -1) {
    return;
  }

  const lastAssistant = turn.events[lastAssistantIndex];
  if (!isForgeAction(lastAssistant) || lastAssistant.action !== "message") {
    return;
  }

  const newArgs = mergeStreamingArgs(lastAssistant.args, streamingEvent);
  try {
    const laRec = lastAssistant as unknown as Record<string, unknown>;
    laRec.args = newArgs;
    turn.events.pop();
  } catch {
    // ignore assignment failures
  }
}

function findLastAssistantMessage(events: ForgeEvent[]) {
  for (let i = events.length - 1; i >= 0; i -= 1) {
    const candidate = events[i];
    if (isForgeAction(candidate) && candidate.source === "agent" && candidate.action === "message") {
      return i;
    }
  }
  return -1;
}

function mergeStreamingArgs(previousArgs: unknown, streamingEvent: ForgeEvent) {
  const prevRecord = toRecord(previousArgs);
  const streamingRecord = toRecord(streamingEvent as unknown);
  const streamingArgs = streamingRecord?.args as Record<string, unknown> | undefined;

  return {
    ...prevRecord,
    content: (streamingArgs?.accumulated as string) || (prevRecord?.content as string | undefined),
  };
}

function toRecord(value: unknown): Record<string, unknown> | undefined {
  return typeof value === "object" && value !== null
    ? (value as Record<string, unknown>)
    : undefined;
}

