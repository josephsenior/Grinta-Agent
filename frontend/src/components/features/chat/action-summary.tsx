import React from "react";
import { Check, Circle, AlertCircle, Loader2 } from "lucide-react";
import { cn } from "#/utils/utils";
import { ForgeEvent } from "#/types/core/base";
import type { ForgeAction, ForgeObservation } from "#/types/core";
import { isErrorObservation } from "#/types/core/guards";

interface ActionSummaryProps {
  events: ForgeEvent[];
  onEventClick?: (eventId: number | string) => void;
}

/**
 * Displays a compact summary of actions taken by the agent
 * Similar to bolt.new / Cursor style - shows list of actions with status
 * Detailed info available on hover/click
 */
export const ActionSummary: React.FC<ActionSummaryProps> = ({
  events,
  onEventClick,
}) => {
  if (events.length === 0) return null;

  return (
    <div className="action-summary mt-2 space-y-0.5 text-sm">
      {events.map((event, index) => {
        // Safely extract `id` from the event union without assuming shape
        const rawId = (event as unknown as Record<string, unknown>)?.id;
        const eventId =
          typeof rawId === "string" || typeof rawId === "number"
            ? rawId
            : undefined;
        const isError = isErrorObservation(event);
        const isLast = index === events.length - 1;

        // Determine status icon
        let StatusIcon = Circle;
        let statusColor = "text-muted-foreground";

        if (isError) {
          StatusIcon = AlertCircle;
          statusColor = "text-danger";
        } else if (!isLast) {
          StatusIcon = Check;
          statusColor = "text-success-400";
        } else {
          StatusIcon = Loader2;
          statusColor = "text-violet-400";
        }

        // Get summary text
        const summary = getEventSummaryText(event);
        if (!summary) return null;

        const keyVal =
          typeof eventId === "string" || typeof eventId === "number"
            ? eventId
            : `event-${index}`;

        return (
          <div
            key={keyVal}
            className={cn(
              "flex items-center gap-2 py-0.5 px-2 rounded-md transition-all duration-200",
              "hover:bg-white/5 cursor-default",
              onEventClick && "cursor-pointer",
            )}
            onClick={() => {
              if (typeof eventId === "string" || typeof eventId === "number") {
                onEventClick?.(eventId as string | number);
              }
            }}
          >
            <StatusIcon
              className={cn(
                "w-3.5 h-3.5 shrink-0",
                statusColor,
                isLast && !isError && "animate-spin",
              )}
            />
            <span
              className={cn(
                "text-xs font-medium",
                isError ? "text-danger" : "text-foreground-secondary",
              )}
            >
              {summary}
            </span>
          </div>
        );
      })}
    </div>
  );
};

/**
 * Extracts human-readable summary from an event
 */
function getEventSummaryText(event: ForgeEvent): string | null {
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

type ActionSummaryHandler = (event: ForgeAction) => string | null;

const ACTION_SUMMARIZERS: Record<string, ActionSummaryHandler> = {
  run: summarizeRunAction,
  write: (event) => summarizeFileAction({ event, verb: "Create" }),
  edit: (event) => summarizeFileAction({ event, verb: "Edit" }),
  browse: summarizeBrowseAction,
  finish: () => "Complete task",
  read: (event) => summarizeFileAction({ event, verb: "Read" }),
};

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

function isActionEvent(event: ForgeEvent): event is ForgeAction {
  return typeof (event as ForgeAction).action === "string";
}

function isObservationEvent(event: ForgeEvent): event is ForgeObservation {
  return typeof (event as ForgeObservation).observation === "string";
}

function getEventArg(event: ForgeAction, key: string) {
  const { args } = event as unknown as { args?: Record<string, unknown> };
  if (!args || typeof args !== "object") {
    return undefined;
  }

  return (args as Record<string, unknown>)[key];
}

function extractFilename(path: string): string {
  return path.split("/").pop() || path;
}
