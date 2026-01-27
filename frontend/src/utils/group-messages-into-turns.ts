import type { ForgeEvent } from "#/types/core/base";
import type { ForgeAction, ForgeObservation } from "#/types/core";
import {
  isUserMessage,
  isAssistantMessage,
  isStreamingChunkAction,
  isForgeAction,
  isForgeObservation,
} from "#/types/core/guards";

export interface MessageTurn {
  type: "user" | "agent";
  events: ForgeEvent[];
  startIndex: number;
  endIndex: number;
}

type ActionSummaryHandler = (event: ForgeAction) => string | null;
type ObservationSummaryHandler = (event: ForgeObservation) => string | null;

const toRecord = (value: unknown): Record<string, unknown> | undefined =>
  typeof value === "object" && value !== null
    ? (value as Record<string, unknown>)
    : undefined;

const extractFilename = (path: string): string => {
  if (!path) {
    return "";
  }
  const parts = path.split("/");
  return parts[parts.length - 1] || path;
};

const summarizeRunAction = (event: ForgeAction): string | null => {
  const args = toRecord(event.args);
  const command = typeof args?.command === "string" ? args.command.trim() : "";
  if (!command) {
    return "Command executed";
  }
  return command.length > 40 ? `${command.slice(0, 40)}...` : command;
};

const summarizeWriteOrEditAction = (
  verb: "Created" | "Edited",
  event: ForgeAction,
): string | null => {
  const args = toRecord(event.args);
  const path =
    (typeof args?.path === "string" && args.path) ||
    (typeof args?.file_path === "string" && args.file_path) ||
    "";
  const filename = extractFilename(path);
  if (!filename) {
    return `${verb} file`;
  }
  return `${verb} ${filename}`;
};

const summarizeRunObservation = (event: ForgeObservation): string | null => {
  const extras = toRecord(event.extras);
  const eventRecord = toRecord(event);
  const exitCodeFromExtras = extras?.exit_code;
  const exitCodeFromEvent = eventRecord?.exit_code;

  let exitCode: number | undefined;
  if (typeof exitCodeFromExtras === "number") {
    exitCode = exitCodeFromExtras;
  } else if (typeof exitCodeFromEvent === "number") {
    exitCode = exitCodeFromEvent;
  }

  if (exitCode === 0) {
    return "Command succeeded";
  }

  if (typeof exitCode === "number") {
    return `Command failed (exit ${exitCode})`;
  }

  return "Command finished";
};

const summarizeReadObservation = (event: ForgeObservation): string | null => {
  const extras = toRecord(event.extras);
  const path = typeof extras?.path === "string" ? extras.path : "";
  const filename = extractFilename(path);
  if (!filename) {
    return "Read file";
  }
  return `Read ${filename}`;
};

const ACTION_SUMMARIZERS: Record<string, ActionSummaryHandler> = {
  run: summarizeRunAction,
  write: (event) => summarizeWriteOrEditAction("Created", event),
  edit: (event) => summarizeWriteOrEditAction("Edited", event),
  finish: () => "Task completed",
};

const OBSERVATION_SUMMARIZERS: Record<string, ObservationSummaryHandler> = {
  run: summarizeRunObservation,
  read: summarizeReadObservation,
};

const summarizeActionEvent = (event: ForgeAction): string | null => {
  const actionKey = typeof event.action === "string" ? event.action : "";
  const handler = ACTION_SUMMARIZERS[actionKey];
  return handler ? handler(event) : null;
};

const summarizeObservationEvent = (event: ForgeObservation): string | null => {
  const observationKey =
    typeof event.observation === "string" ? event.observation : "";
  const handler = OBSERVATION_SUMMARIZERS[observationKey];
  return handler ? handler(event) : null;
};

const findLastAssistantMessage = (events: ForgeEvent[]): number => {
  for (let i = events.length - 1; i >= 0; i -= 1) {
    const candidate = events[i];
    if (
      isForgeAction(candidate) &&
      candidate.source === "agent" &&
      candidate.action === "message"
    ) {
      return i;
    }
  }
  return -1;
};

const extractAccumulatedContent = (
  streamingEvent: ForgeEvent,
): string | null => {
  if (!isStreamingChunkAction(streamingEvent)) {
    return null;
  }
  const streamingRecord = toRecord(streamingEvent);
  const streamingArgs = toRecord(streamingRecord?.args);
  const accumulated = streamingArgs?.accumulated;
  return typeof accumulated === "string" ? accumulated : null;
};

const mergeStreamingChunkIntoTurn = (
  turn: MessageTurn,
  streamingEvent: ForgeEvent,
): MessageTurn => {
  const lastAssistantIndex = findLastAssistantMessage(turn.events);
  if (lastAssistantIndex === -1) {
    return turn;
  }

  const lastAssistant = turn.events[lastAssistantIndex];
  if (!isForgeAction(lastAssistant) || lastAssistant.action !== "message") {
    return turn;
  }

  const accumulated = extractAccumulatedContent(streamingEvent);
  if (!accumulated) {
    return turn;
  }

  let updatedAssistant: ForgeAction = lastAssistant;

  if (isUserMessage(lastAssistant)) {
    updatedAssistant = {
      ...lastAssistant,
      args: {
        ...lastAssistant.args,
        content: accumulated,
      },
    };
  } else if (isAssistantMessage(lastAssistant)) {
    updatedAssistant = {
      ...lastAssistant,
      args: {
        ...lastAssistant.args,
        thought: accumulated,
      },
    };
  } else {
    return turn;
  }

  const updatedEvents = [...turn.events];
  updatedEvents.splice(lastAssistantIndex, 1, updatedAssistant);

  return { ...turn, events: updatedEvents };
};

const createAgentTurn = (event: ForgeEvent, index: number): MessageTurn => {
  const turn: MessageTurn = {
    type: "agent",
    events: [event],
    startIndex: index,
    endIndex: index,
  };

  if (isStreamingChunkAction(event)) {
    return mergeStreamingChunkIntoTurn(turn, event);
  }

  return turn;
};

const appendAgentEvent = ({
  currentTurn,
  event,
  index,
}: {
  currentTurn: MessageTurn | null;
  event: ForgeEvent;
  index: number;
}): MessageTurn => {
  if (!currentTurn || currentTurn.type !== "agent") {
    return createAgentTurn(event, index);
  }

  const updatedTurn: MessageTurn = {
    ...currentTurn,
    events: [...currentTurn.events, event],
    endIndex: index,
  };

  if (isStreamingChunkAction(event)) {
    return mergeStreamingChunkIntoTurn(updatedTurn, event);
  }

  return updatedTurn;
};

const pushUserTurn = (
  turns: MessageTurn[],
  event: ForgeEvent,
  index: number,
): void => {
  turns.push({
    type: "user",
    events: [event],
    startIndex: index,
    endIndex: index,
  });
};

const finalizeCurrentTurn = (
  turns: MessageTurn[],
  currentTurn: MessageTurn | null,
): MessageTurn | null => {
  if (currentTurn) {
    turns.push(currentTurn);
  }
  return null;
};

/**
 * Groups consecutive messages into "turns" for bolt.new-style rendering
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
  const streamingEvents = turn.events.filter((event) =>
    isStreamingChunkAction(event),
  );
  if (streamingEvents.length === 0) {
    return null;
  }

  const lastStreaming = streamingEvents[streamingEvents.length - 1];
  const streamingRecord = toRecord(lastStreaming);
  const args = toRecord(streamingRecord?.args);
  const accumulated = args?.accumulated;
  return typeof accumulated === "string" ? accumulated : null;
}

/**
 * Extracts a summary label from an event for compact display
 */
export function getEventSummary(event: ForgeEvent): string {
  if (isForgeAction(event)) {
    const summary = summarizeActionEvent(event);
    return summary ?? event.action ?? "Event";
  }

  if (isForgeObservation(event)) {
    const summary = summarizeObservationEvent(event);
    return summary ?? event.observation ?? "Event";
  }

  return "Event";
}
