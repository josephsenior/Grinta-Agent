import { ForgeEvent } from "#/types/core/base";

export function extractEventId(
  event: ForgeEvent,
  index: number,
): string | number {
  const rawId = (event as unknown as Record<string, unknown>)?.id;
  if (typeof rawId === "string" || typeof rawId === "number") {
    return rawId;
  }
  return `event-${index}`;
}

export function getEventKey(event: ForgeEvent, index: number): string | number {
  const rawId = (event as unknown as Record<string, unknown>)?.id;
  if (typeof rawId === "string" || typeof rawId === "number") {
    return rawId;
  }
  return `event-${index}`;
}
