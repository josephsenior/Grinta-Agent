import { ForgeAction } from "./actions";
import { ForgeObservation } from "./observations";
import { ForgeVariance } from "./variances";

/**
 * Parsed events are the normal runtime events that come from the server
 * (actions and observations). Variances are non-standard payloads and are
 * exported separately.
 */
export type ForgeParsedEvent = ForgeAction | ForgeObservation;

export type { ForgeVariance };

// Re-export main types for convenience
export type { ForgeAction } from "./actions";
export type { ForgeObservation } from "./observations";
export type { ForgeEvent } from "./base";
