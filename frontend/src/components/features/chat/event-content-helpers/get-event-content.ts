import type {
  ForgeAction,
  ForgeObservation,
} from "#/types/core";
import { hasArgs, isForgeObservation } from "#/types/core/guards";

/**
 * Extract a friendly title/details pair from an event for rendering.
 * This is deliberately defensive and accepts both action and observation shapes.
 */
export function getEventContent(
  event: ForgeAction | ForgeObservation,
): { title: string; details: string } {
  if (isForgeObservation(event)) {
    return extractObservationContent(event);
  }

  return extractActionContent(event as ForgeAction);
}

function extractObservationContent(event: ForgeObservation): {
  title: string;
  details: string;
} {
  const record = toRecord(event);
  const title = getStringField(record, ["title"], "");
  const details =
    getStringField(record, ["content", "details"], "") ?? "";

  return { title, details };
}

function extractActionContent(action: ForgeAction): {
  title: string;
  details: string;
} {
  const args = hasArgs(action) ? toRecord(action.args) : undefined;

  const candidate =
    getStringField(args, ["content", "message", "thought"], undefined) ??
    (typeof action.message === "string" ? action.message : "");

  return { title: "", details: candidate ?? "" };
}

function toRecord(value: unknown): Record<string, unknown> {
  if (typeof value === "object" && value !== null) {
    return value as Record<string, unknown>;
  }
  return {};
}

function getStringField(
  record: Record<string, unknown> | undefined,
  keys: string[],
  fallback: string | undefined,
): string | undefined {
  if (!record) {
    return fallback;
  }

  for (const key of keys) {
    const value = record[key];
    if (typeof value === "string" && value.length > 0) {
      return value;
    }
  }

  return fallback;
}

export default getEventContent;
