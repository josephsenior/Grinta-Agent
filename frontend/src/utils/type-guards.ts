/**
 * Type guards for Forge event types
 */

import type {
  ForgeAction,
  ForgeObservation,
  ForgeParsedEvent,
} from "#/types/core";

/**
 * Type guard to check if an ForgeEvent is a valid ForgeParsedEvent
 * This helps TypeScript narrow the type from the generic ForgeEvent to the specific parsed types
 */
export function isForgeParsedEvent(event: unknown): event is ForgeParsedEvent {
  // Basic validation - the event should have required properties
  if (!event || typeof event !== "object") {
    return false;
  }

  // Check if it's an action event with valid structure
  if ("action" in event && "args" in event) {
    return true;
  }

  // Check if it's an observation event with valid structure
  if ("observation" in event && "content" in event) {
    return true;
  }

  return false;
}

/**
 * Safely cast an ForgeEvent to ForgeParsedEvent
 * Returns the event if it's valid, otherwise returns null
 */
export function asForgeParsedEvent(event: unknown): ForgeParsedEvent | null {
  if (isForgeParsedEvent(event)) {
    return event;
  }
  return null;
}

/**
 * Type guard to check if an event is an action
 */
export function isActionEvent(event: unknown): event is ForgeAction {
  return (
    typeof event === "object" &&
    event !== null &&
    "action" in event &&
    "args" in (event as Record<string, unknown>)
  );
}

/**
 * Type guard to check if an event is an observation
 */
export function isObservationEvent(event: unknown): event is ForgeObservation {
  return (
    typeof event === "object" &&
    event !== null &&
    "observation" in event &&
    "content" in (event as Record<string, unknown>)
  );
}

// Axios-oriented helpers used by error utilities
export const isAxiosErrorWithErrorField = (
  error: unknown,
): error is { response: { data: { error: string } } } => {
  if (typeof error !== "object" || error === null) return false;
  const err = error as Record<string, unknown>;
  return (
    typeof err.response === "object" &&
    err.response !== null &&
    typeof (err.response as Record<string, unknown>).data === "object" &&
    (err.response as Record<string, unknown>).data !== null &&
    typeof (
      (err.response as Record<string, unknown>).data as Record<string, unknown>
    ).error === "string"
  );
};

export const isAxiosErrorWithMessageField = (
  error: unknown,
): error is { response: { data: { message: string } } } => {
  if (typeof error !== "object" || error === null) return false;
  const err = error as Record<string, unknown>;
  return (
    typeof err.response === "object" &&
    err.response !== null &&
    typeof (err.response as Record<string, unknown>).data === "object" &&
    (err.response as Record<string, unknown>).data !== null &&
    typeof (
      (err.response as Record<string, unknown>).data as Record<string, unknown>
    ).message === "string"
  );
};
