import type { ForgeEvent } from "#/types/core/base";
import type { ForgeAction, ForgeObservation } from "#/types/core";
import {
  isAssistantMessage,
  isStreamingChunkAction,
  isForgeAction,
  isForgeObservation,
} from "#/types/core/guards";

/**
 * Coalesces consecutive assistant messages into single messages
 * for a cleaner, less fragmented UX (bolt.new style)
 * 
 * Before: ["Let me help", "I'll do this", "And this"]
 * After:  ["Let me help\n\nI'll do this\n\nAnd this"]
 */
export function coalesceMessages(events: ForgeEvent[]): ForgeEvent[] {
  // 🚫 DISABLED: Coalescing prevents real-time streaming
  // For ChatGPT-style character-by-character streaming, we need EVERY message
  // to appear immediately without batching
  // 
  // Before fix: Messages batched → rendered all at once → bad UX
  // After fix: Each message streams immediately → smooth real-time updates
  return events;
}

/**
 * Determines the appropriate spacing between two consecutive events
 * for a smoother, more cohesive visual flow
 */
export function getEventSpacing(
  currentEvent: ForgeEvent,
  nextEvent?: ForgeEvent,
): string {
  if (!nextEvent) return "mb-0"; // Last event has no margin

  // Assistant message followed by thought/action → tight spacing
  if (isAssistantMessage(currentEvent)) {
    return "mb-1"; // 4px - keep them connected
  }

  // Technical events (actions/observations) → moderate spacing
  const isTechnical = (e: ForgeEvent) =>
    isForgeAction(e) && !isAssistantMessage(e) && !isStreamingChunkAction(e);

  if (isTechnical(currentEvent) && isTechnical(nextEvent)) {
    return "mb-1.5"; // 6px - related but distinct
  }

  // Default: comfortable separation
  return "mb-2"; // 8px
}

/**
 * Checks if an event should be auto-expanded by default
 * (important events shown, routine events collapsed)
 */
export function shouldAutoExpand(
  event: ForgeEvent,
  isLastInTurn: boolean,
  isError: boolean,
): boolean {
  // Always expand errors
  if (isError) return true;

  // Always expand last event
  if (isLastInTurn) return true;

  // Expand assistant messages
  if (isAssistantMessage(event)) return true;

  // Collapse technical details by default
  return false;
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

type ActionSummaryHandler = (event: ForgeAction) => string | null;
type ObservationSummaryHandler = (event: ForgeObservation) => string | null;

const ACTION_SUMMARIZERS: Record<string, ActionSummaryHandler> = {
  run: summarizeRunAction,
  write: (event) => summarizeWriteOrEditAction("Created", event),
  edit: (event) => summarizeWriteOrEditAction("Edited", event),
  browse: summarizeBrowseAction,
  finish: () => "Task completed",
};

const OBSERVATION_SUMMARIZERS: Record<string, ObservationSummaryHandler> = {
  run: summarizeRunObservation,
  read: summarizeReadObservation,
  browse: () => "Page loaded",
};

function summarizeActionEvent(event: ForgeAction): string | null {
  const actionKey = typeof event.action === "string" ? event.action : "";
  const handler = ACTION_SUMMARIZERS[actionKey];
  return handler ? handler(event) : null;
}

function summarizeObservationEvent(event: ForgeObservation): string | null {
  const observationKey =
    typeof event.observation === "string" ? event.observation : "";
  const handler = OBSERVATION_SUMMARIZERS[observationKey];
  return handler ? handler(event) : null;
}

function summarizeRunAction(event: ForgeAction): string | null {
  const args = toRecord(event.args);
  const command = typeof args?.command === "string" ? args.command.trim() : "";
  if (!command) {
    return "Command executed";
  }
  return command.length > 40 ? `${command.slice(0, 40)}...` : command;
}

function summarizeWriteOrEditAction(
  verb: "Created" | "Edited",
  event: ForgeAction,
): string | null {
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
}

function summarizeBrowseAction(event: ForgeAction): string | null {
  const args = toRecord(event.args);
  const url = typeof args?.url === "string" ? args.url : "";
  return url ? `Opened ${url}` : "Browsed page";
}

function summarizeRunObservation(event: ForgeObservation): string | null {
  const extras = toRecord(event.extras);
  const eventRecord = toRecord(event);
  const exitCodeFromExtras = extras?.exit_code;
  const exitCodeFromEvent = eventRecord?.exit_code;

  const exitCode =
    typeof exitCodeFromExtras === "number"
      ? exitCodeFromExtras
      : typeof exitCodeFromEvent === "number"
        ? exitCodeFromEvent
        : undefined;

  if (exitCode === 0) {
    return "Command succeeded";
  }

  if (typeof exitCode === "number") {
    return `Command failed (exit ${exitCode})`;
  }

  return "Command finished";
}

function summarizeReadObservation(event: ForgeObservation): string | null {
  const extras = toRecord(event.extras);
  const path = typeof extras?.path === "string" ? extras.path : "";
  const filename = extractFilename(path);
  if (!filename) {
    return "Read file";
  }
  return `Read ${filename}`;
}

function toRecord(value: unknown): Record<string, unknown> | undefined {
  if (typeof value === "object" && value !== null) {
    return value as Record<string, unknown>;
  }
  return undefined;
}

function extractFilename(path: string): string {
  if (!path) {
    return "";
  }
  const parts = path.split("/");
  return parts[parts.length - 1] || path;
}

