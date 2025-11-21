import { ForgeAction, ForgeObservation } from "#/types/core";

const STRING_FIELDS: Array<keyof ForgeAction | keyof ForgeObservation> = [
  "message",
  "content",
  "observation",
];

export function extractStringField(
  message: ForgeAction | ForgeObservation,
): string | null {
  for (const field of STRING_FIELDS) {
    const messageRecord = message as unknown as Record<string, unknown>;
    if (field in message && typeof messageRecord[field] === "string") {
      return messageRecord[field] as string;
    }
  }
  return null;
}

export function extractArgsText(args: unknown): string | null {
  if (!args) {
    return null;
  }

  if (typeof args === "string") {
    return args;
  }

  if (
    typeof args === "object" &&
    "thought" in (args as Record<string, unknown>)
  ) {
    const { thought } = args as Record<string, unknown>;
    return thought != null ? String(thought) : "";
  }

  return null;
}

export function getMessageText(
  message: ForgeAction | ForgeObservation,
): string {
  const stringField = extractStringField(message);
  if (stringField !== null) {
    return stringField;
  }

  if ("args" in message) {
    const argsText = extractArgsText(message.args);
    if (argsText !== null) {
      return argsText;
    }
  }

  return JSON.stringify(message);
}
