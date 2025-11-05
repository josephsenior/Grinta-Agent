import { OpenHandsAction } from "./actions";
import { OpenHandsObservation } from "./observations";
import { OpenHandsVariance } from "./variances";

/**
 * Parsed events are the normal runtime events that come from the server
 * (actions and observations). Variances are non-standard payloads and are
 * exported separately.
 */
export type OpenHandsParsedEvent = OpenHandsAction | OpenHandsObservation;

export type { OpenHandsVariance };

// Re-export main types for convenience
export type { OpenHandsAction } from "./actions";
export type { OpenHandsObservation } from "./observations";
export type { OpenHandsEvent } from "./base";
