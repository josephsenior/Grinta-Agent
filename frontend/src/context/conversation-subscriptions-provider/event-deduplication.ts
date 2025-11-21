import type { ForgeEvent } from "#/types/core/base";
import { isForgeAction, isForgeObservation } from "#/types/core/guards";

export function isEventDuplicate(
  existingEvent: ForgeEvent,
  newEvent: ForgeEvent,
): boolean {
  if (existingEvent.id === newEvent.id) {
    return true;
  }

  if (isForgeAction(existingEvent) && isForgeAction(newEvent)) {
    return (
      existingEvent.source === newEvent.source &&
      existingEvent.action === newEvent.action &&
      JSON.stringify(existingEvent.args) === JSON.stringify(newEvent.args)
    );
  }

  if (isForgeObservation(existingEvent) && isForgeObservation(newEvent)) {
    return (
      existingEvent.source === newEvent.source &&
      existingEvent.observation === newEvent.observation &&
      JSON.stringify(existingEvent.extras) === JSON.stringify(newEvent.extras)
    );
  }

  return false;
}

export function shouldAddEvent(
  currentEvents: ForgeEvent[],
  newEvent: ForgeEvent,
): boolean {
  return !currentEvents.some((existingEvent) =>
    isEventDuplicate(existingEvent, newEvent),
  );
}
