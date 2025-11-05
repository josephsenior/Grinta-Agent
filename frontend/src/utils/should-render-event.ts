import type { OpenHandsEvent } from "#/types/core/base";
import {
  isUserMessage,
  isErrorObservation,
  isAssistantMessage,
  isOpenHandsObservation,
  isFinishAction,
  isRejectObservation,
  isMcpObservation,
  isTaskTrackingObservation,
  isFileWriteAction,
  isFileEditAction,
  isStreamingChunkAction,
  isOpenHandsAction,
} from "#/types/core/guards";

// Detect important commands that should be shown even when technical details are hidden
const isImportantCommand = (cmd?: string | null): boolean => {
  if (!cmd) return false;
  const command = String(cmd).toLowerCase();
  const importantPatterns = [
    /npm\s+(install|i|run|build|start|test)/,
    /yarn\s+(install|add|build|start|test)/,
    /pnpm\s+(install|add|build|start|test)/,
    /pip\s+install/,
    /docker\s+(build|run|compose)/,
    /git\s+(clone|pull|push|commit|checkout|branch)/,
    /pytest/,
    /cargo\s+(build|run|test)/,
    /make\s+(build|install|test)/,
    /cmake/,
    /deploy/,
    /build/,
  ];
  return importantPatterns.some((pattern) => pattern.test(command));
};

const hasThoughtProperty = (
  args: Record<string, unknown>,
): args is { thought: string } => {
  return "thought" in args && typeof args.thought === "string";
};

/**
 * Determines if an event should be rendered based on technical details visibility
 */
export function shouldRenderEvent(
  event: OpenHandsEvent,
  showTechnicalDetails: boolean,
): boolean {
  // Show everything when technical details are enabled
  if (showTechnicalDetails) {
    return true;
  }

  // Always show user and assistant messages
  if (isUserMessage(event) || isAssistantMessage(event)) {
    return true;
  }

  // Always show streaming chunks (real-time LLM responses)
  if (isStreamingChunkAction(event)) {
    return true;
  }

  // Always show errors
  if (isErrorObservation(event)) {
    return true;
  }

  // Always show file write/edit actions (code artifacts)
  if (isFileWriteAction(event) || isFileEditAction(event)) {
    return true;
  }

  // Show important commands via terminal
  if (
    isOpenHandsObservation(event) &&
    event.observation === "run" &&
    isImportantCommand(event.extras?.command)
  ) {
    return true;
  }

  // Show agent thoughts
  if (
    isOpenHandsAction(event) &&
    hasThoughtProperty(event.args) &&
    event.action !== "think"
  ) {
    return true;
  }

  // Show finish actions
  if (isFinishAction(event)) {
    return true;
  }

  // Show reject observations
  if (isRejectObservation(event)) {
    return true;
  }

  // Show MCP and task tracking observations
  if (isMcpObservation(event) || isTaskTrackingObservation(event)) {
    return true;
  }

  // Hide everything else (verbose technical events)
  return false;
}

