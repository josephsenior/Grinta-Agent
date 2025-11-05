import React from "react";
import { shouldRenderEvent } from "../event-content-helpers/should-render-event";
import type { OpenHandsAction } from "#/types/core/actions";
import type { OpenHandsObservation } from "#/types/core/observations";

/**
 * Custom hook to filter events based on technical details setting
 * Separates event filtering logic from UI components
 */
export function useFilteredEvents(
  parsedEvents: (OpenHandsAction | OpenHandsObservation)[],
  showTechnicalDetails: boolean
) {
  return React.useMemo(() => {
    const baseFiltered = parsedEvents.filter(shouldRenderEvent);
    
    // If showing all technical details, return everything
    if (showTechnicalDetails) {
      return baseFiltered;
    }
    
    // Otherwise, apply additional filtering (this logic should match EventMessage's filtering)
    // We keep the filtering in EventMessage for now to avoid duplication
    // The EventMessage component will return null for filtered events
    return baseFiltered;
  }, [parsedEvents, showTechnicalDetails]);
}
