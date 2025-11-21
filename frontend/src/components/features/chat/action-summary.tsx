import React from "react";
import { ForgeEvent } from "#/types/core/base";
import { isErrorObservation } from "#/types/core/guards";
import { getEventSummaryText } from "./action-summary/utils/summary-helpers";
import { getEventKey } from "./action-summary/utils/event-helpers";
import { getStatusConfig } from "./action-summary/utils/status-helpers";
import { ActionSummaryItem } from "./action-summary/components/action-summary-item";

interface ActionSummaryProps {
  events: ForgeEvent[];
  onEventClick?: (eventId: number | string) => void;
}

// Re-export helper functions for backward compatibility
export {
  getEventArg,
  extractFilename,
  isActionEvent,
  isObservationEvent,
} from "./action-summary/utils/summary-helpers";

/**
 * Displays a compact summary of actions taken by the agent
 * Similar to bolt.new / Cursor style - shows list of actions with status
 * Detailed info available on hover/click
 */
export function ActionSummary({ events, onEventClick }: ActionSummaryProps) {
  if (events.length === 0) return null;

  return (
    <div className="action-summary mt-2 space-y-0.5 text-sm">
      {events.map((event, index) => {
        const eventId = getEventKey(event, index);
        const isError = isErrorObservation(event);
        const isLast = index === events.length - 1;
        const statusConfig = getStatusConfig(event, isLast);
        const summary = getEventSummaryText(event);

        if (!summary) return null;

        const handleClick = () => {
          const rawId = (event as unknown as Record<string, unknown>)?.id;
          if (typeof rawId === "string" || typeof rawId === "number") {
            onEventClick?.(rawId);
          }
        };

        return (
          <ActionSummaryItem
            key={eventId}
            summary={summary}
            StatusIcon={statusConfig.icon}
            statusColor={statusConfig.color}
            shouldAnimate={statusConfig.shouldAnimate}
            isError={isError}
            onClick={onEventClick ? handleClick : undefined}
          />
        );
      })}
    </div>
  );
}
