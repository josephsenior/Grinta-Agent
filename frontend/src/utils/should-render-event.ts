import type { ForgeEvent } from "#/types/core/base";
import {
  isUserMessage,
  isErrorObservation,
  isAssistantMessage,
  isForgeObservation,
  isFinishAction,
  isRejectObservation,
  isMcpObservation,
  isTaskTrackingObservation,
  isFileWriteAction,
  isFileEditAction,
  isStreamingChunkAction,
  isForgeAction,
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
): args is { thought: string } =>
  "thought" in args && typeof args.thought === "string";

type RenderPredicate = (event: ForgeEvent) => boolean;

const ALWAYS_RENDER_PREDICATES: RenderPredicate[] = [
  (event) => isUserMessage(event) || isAssistantMessage(event),
  (event) => isStreamingChunkAction(event),
  (event) => isErrorObservation(event),
  (event) => isFileWriteAction(event) || isFileEditAction(event),
  eventHasImportantCommand,
  eventContainsAgentThought,
  (event) => isFinishAction(event),
  (event) => isRejectObservation(event),
  (event) => isMcpObservation(event) || isTaskTrackingObservation(event),
];

export function shouldRenderEvent(
  event: ForgeEvent,
  showTechnicalDetails: boolean,
): boolean {
  if (showTechnicalDetails) {
    return true;
  }

  return ALWAYS_RENDER_PREDICATES.some((predicate) => predicate(event));
}

function eventHasImportantCommand(event: ForgeEvent): boolean {
  if (!isForgeObservation(event)) {
    return false;
  }

  if (event.observation !== "run") {
    return false;
  }

  return isImportantCommand(event.extras?.command);
}

function eventContainsAgentThought(event: ForgeEvent): boolean {
  if (!isForgeAction(event)) {
    return false;
  }

  return event.action !== "think" && hasThoughtProperty(event.args);
}
