/**
 * Type guards for OpenHands event types
 */

import type {
  OpenHandsEvent,
  OpenHandsAction,
  OpenHandsObservation,
  OpenHandsParsedEvent,
} from "#/types/core";

/**
 * Type guard to check if an OpenHandsEvent is a valid OpenHandsParsedEvent
 * This helps TypeScript narrow the type from the generic OpenHandsEvent to the specific parsed types
 */
export function isOpenHandsParsedEvent(
  event: unknown
): event is OpenHandsParsedEvent {
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
 * Safely cast an OpenHandsEvent to OpenHandsParsedEvent
 * Returns the event if it's valid, otherwise returns null
 */
export function asOpenHandsParsedEvent(
  event: unknown
): OpenHandsParsedEvent | null {
  if (isOpenHandsParsedEvent(event)) {
    return event;
  }
  return null;
}

/**
 * Type guard to check if an event is an action
 */
export function isActionEvent(event: unknown): event is OpenHandsAction {
  return typeof event === "object" && event !== null && "action" in event && "args" in (event as any);
}

/**
 * Type guard to check if an event is an observation
 */
export function isObservationEvent(event: unknown): event is OpenHandsObservation {
  return typeof event === "object" && event !== null && "observation" in event && "content" in (event as any);
}

// Axios-oriented helpers used by error utilities
export const isAxiosErrorWithErrorField = (
  error: unknown,
): error is { response: { data: { error: string } } } =>
  typeof error === "object" &&
  error !== null &&
  (error as any).response &&
  (error as any).response.data &&
  typeof (error as any).response.data.error === "string";

export const isAxiosErrorWithMessageField = (
  error: unknown,
): error is { response: { data: { message: string } } } =>
  typeof error === "object" &&
  error !== null &&
  (error as any).response &&
  (error as any).response.data &&
  typeof (error as any).response.data.message === "string";

