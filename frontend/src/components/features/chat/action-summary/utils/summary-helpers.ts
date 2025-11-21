import type { ForgeAction, ForgeObservation } from "#/types/core";
import { ForgeEvent } from "#/types/core/base";
import { isErrorObservation } from "#/types/core/guards";

export function getEventArg(event: ForgeAction, key: string) {
  const { args } = event as unknown as { args?: Record<string, unknown> };
  if (!args || typeof args !== "object") {
    return undefined;
  }

  return (args as Record<string, unknown>)[key];
}

export function extractFilename(path: string): string {
  return path.split("/").pop() || path;
}

export function isActionEvent(event: ForgeEvent): event is ForgeAction {
  return typeof (event as ForgeAction).action === "string";
}

export function isObservationEvent(
  event: ForgeEvent,
): event is ForgeObservation {
  return typeof (event as ForgeObservation).observation === "string";
}

function summarizeRunAction(event: ForgeAction): string | null {
  const command = getEventArg(event, "command");
  if (typeof command !== "string" || command.trim().length === 0) {
    return "Execute command";
  }

  const primary = command.split(/\s+/).slice(0, 2).join(" ");
  return primary.length > 0 ? `Run: ${primary}` : "Execute command";
}

function summarizeFileAction({
  event,
  verb,
}: {
  event: ForgeAction;
  verb: string;
}): string | null {
  const path = getEventArg(event, "path") ?? getEventArg(event, "file_path");
  if (typeof path !== "string" || path.length === 0) {
    return `${verb} file`;
  }

  return `${verb} ${extractFilename(path)}`;
}

function summarizeBrowseAction(event: ForgeAction): string | null {
  const url = getEventArg(event, "url");
  if (typeof url !== "string" || url.length === 0) {
    return "Open browser";
  }

  try {
    const domain = new URL(url).hostname.replace("www.", "");
    return domain ? `Open ${domain}` : "Open browser";
  } catch {
    return "Open browser";
  }
}

function summarizeObservation(event: ForgeObservation): string | null {
  if (isErrorObservation(event)) {
    return "Error occurred";
  }

  return null;
}

type ActionSummaryHandler = (event: ForgeAction) => string | null;

const ACTION_SUMMARIZERS: Record<string, ActionSummaryHandler> = {
  run: summarizeRunAction,
  write: (event) => summarizeFileAction({ event, verb: "Create" }),
  edit: (event) => summarizeFileAction({ event, verb: "Edit" }),
  browse: summarizeBrowseAction,
  finish: () => "Complete task",
  read: (event) => summarizeFileAction({ event, verb: "Read" }),
};

/**
 * Extracts human-readable summary from an event
 */
export function getEventSummaryText(event: ForgeEvent): string | null {
  if (isActionEvent(event)) {
    const key = typeof event.action === "string" ? event.action : undefined;
    const handler = key ? ACTION_SUMMARIZERS[key] : undefined;
    if (handler) {
      return handler(event);
    }
  }

  if (isObservationEvent(event)) {
    return summarizeObservation(event);
  }

  return null;
}
