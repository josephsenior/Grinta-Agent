import React from "react";
import { Check, Circle, AlertCircle, Loader2 } from "lucide-react";
import { cn } from "#/utils/utils";
import { TooltipButton } from "#/components/shared/buttons/tooltip-button";
import { OpenHandsEvent } from "#/types/core/base";
import { isErrorObservation } from "#/types/core/guards";

interface ActionSummaryProps {
  events: OpenHandsEvent[];
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
        const eventId = typeof rawId === "string" || typeof rawId === "number" ? rawId : undefined;
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

        const keyVal = typeof eventId === "string" || typeof eventId === "number" ? eventId : `event-${index}`;

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
                isLast && !isError && "animate-spin"
              )} 
            />
            <span className={cn(
              "text-xs font-medium",
              isError ? "text-danger" : "text-foreground-secondary"
            )}>
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
function getEventSummaryText(event: OpenHandsEvent): string | null {
  // Type guard to check if it's an action or observation
  const action = "action" in event ? event.action : undefined;
  const observation = "observation" in event ? event.observation : undefined;

  // Actions
  if (action === "run" && "args" in event) {
    const cmd = (event.args as { command?: string })?.command || "";
    // Extract key command parts (npm install, git clone, etc.)
    const parts = cmd.split(/\s+/);
    const primary = parts.slice(0, 2).join(" ");
    return primary.length > 0 ? `Run: ${primary}` : "Execute command";
  }

  if (action === "write" && "args" in event) {
    const path = (event.args?.path as string) || "";
    const filename = path.split("/").pop() || "file";
    return `Create ${filename}`;
  }

  if (action === "edit" && "args" in event) {
    const path = ((event.args?.path || event.args?.file_path) as string) || "";
    const filename = path.split("/").pop() || "file";
    return `Edit ${filename}`;
  }

  if (action === "browse" && "args" in event) {
    const url = (event.args?.url as string) || "";
    // Extract domain from URL
    try {
      const domain = new URL(url).hostname.replace("www.", "");
      return `Open ${domain}`;
    } catch {
      return "Open browser";
    }
  }

  if (action === "finish") {
    return "Complete task";
  }

  if (action === "read" && "args" in event) {
    const path = (event.args?.path as string) || "";
    const filename = path.split("/").pop() || "file";
    return `Read ${filename}`;
  }

  // Observations (usually don't show unless error)
  if (observation && isErrorObservation(event)) {
    return "Error occurred";
  }

  // Skip most observations (they're implementation details)
  return null;
}

