import type { OpenHandsEvent } from "#/types/core/base";
import {
  isAssistantMessage,
  isStreamingChunkAction,
  isOpenHandsAction,
  isOpenHandsObservation,
} from "#/types/core/guards";

/**
 * Coalesces consecutive assistant messages into single messages
 * for a cleaner, less fragmented UX (bolt.new style)
 * 
 * Before: ["Let me help", "I'll do this", "And this"]
 * After:  ["Let me help\n\nI'll do this\n\nAnd this"]
 */
export function coalesceMessages(events: OpenHandsEvent[]): OpenHandsEvent[] {
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
  currentEvent: OpenHandsEvent,
  nextEvent?: OpenHandsEvent,
): string {
  if (!nextEvent) return "mb-0"; // Last event has no margin

  // Assistant message followed by thought/action → tight spacing
  if (isAssistantMessage(currentEvent)) {
    return "mb-1"; // 4px - keep them connected
  }

  // Technical events (actions/observations) → moderate spacing
  const isTechnical = (e: OpenHandsEvent) =>
    isOpenHandsAction(e) && !isAssistantMessage(e) && !isStreamingChunkAction(e);

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
  event: OpenHandsEvent,
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
export function getEventSummary(event: OpenHandsEvent): string {
  // Action summaries (narrow before property access)
  if (isOpenHandsAction(event)) {
    const action = event.action;

    if (action === "run") {
      const cmd = (event.args as any)?.command || "";
      return cmd.length > 40 ? `${cmd.slice(0, 40)}...` : cmd;
    }

    if (action === "write" || action === "edit") {
      const path = (event.args as any)?.path || (event.args as any)?.file_path || "";
      const filename = path.split("/").pop() || path;
      return `${action === "write" ? "Created" : "Edited"} ${filename}`;
    }

    if (action === "browse") {
      const url = (event.args as any)?.url || "";
      return `Opened ${url}`;
    }

    if (action === "finish") {
      return "Task completed";
    }
  }

  // Observation summaries
  if (isOpenHandsObservation(event)) {
    const observation = event.observation;

    if (observation === "run") {
      const exitCode = (event.extras as any)?.exit_code ?? (event as any).exit_code;
      return exitCode === 0 ? "Command succeeded" : `Command failed (exit ${exitCode})`;
    }

    if (observation === "read") {
      const path = (event.extras as any)?.path || "";
      const filename = path.split("/").pop() || path;
      return `Read ${filename}`;
    }

    if (observation === "browse") {
      return "Page loaded";
    }
  }

  // Default: use action/observation type or fallback label
  if (isOpenHandsAction(event)) return event.action || "Event";
  if (isOpenHandsObservation(event)) return event.observation || "Event";
  return "Event";
}

